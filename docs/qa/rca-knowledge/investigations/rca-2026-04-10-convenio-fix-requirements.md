# Fix Requirements — RCA `rca-2026-04-10-convenio-mojibake-anchors-vision`

**Gerado por:** @qa via /investigate --deep  
**Data:** 2026-04-10  
**Origin Gate:** 5/5 PASS para todos os 3 fixes  
**Para @dev:** Implementar cada fix de forma independente, testando após cada um.

---

## Contexto

Job Convênio `e5d36138-fd0c-43a6-ab3e-7762ae23c0e0` exibindo:
- Mojibake em todo o document_structure (`Seção de Convênio` → `Se\ufffdcao de Conv\ufffdnio`)
- Anchors do SyncView mostrando valores dinâmicos (`30/03/2026`) em vez de labels semânticos
- `vision_agreement=90` enquanto `visual_regions={}` — contradição silenciosa
- 27 campos XSD required sem mapping (bloco SACADO inteiro: NOME, CPF_CNPJ, ENDERECO, CEP, CIDADE, BAIRRO, UF)

---

## FIX 1 — R2: Encoding em Stage 2 text extraction

**Origin:** `backend/services/stages/stage2_extraction/text_extraction.py` linha 124  
**Arquivo suspeito:** Chamada `page.get_text("dict")` sem parâmetros de encoding

**O que fazer:**

1. Localizar a chamada `page.get_text("dict")` no arquivo acima.
2. Após a extração dos spans, adicionar normalização de caracteres de replacement:
   - Verificar se o texto contém `\ufffd` (U+FFFD — caractere replacement unicode)
   - Se sim, tentar reextrair com `page.get_text("rawdict")` para obter bytes brutos
   - Decodificar bytes brutos com `bytes.decode("cp1252", errors="replace")` como fallback
   - Alternativa mais simples: usar a biblioteca `ftfy` (`pip install ftfy`) — `ftfy.fix_text(span_text)` corrige a maioria dos casos de mojibake
3. Se usar ftfy, adicionar ao `requirements.txt`

**Teste de aceitação:**
```python
# Rodar extração no PDF do Convênio e verificar que o texto "Seção de Convênio" aparece corretamente
# sem \ufffd ou caracteres quebrados
pdf_path = "C:/tmp/rca-convenio/e5d36138-fd0c-43a6-ab3e-7762ae23c0e0/input.pdf"
# Verificar: "Seção" contém ã e ç sem replacement chars
```

**Impacto do fix:** Propaga para todo o pipeline — document_structure, anchors, overlay_items, template_draft.html, e o Knockout template gerado. Fix de alto retorno.

**Estimativa:** 1-2h

---

## FIX 2 — R4: Coverage overlay usando valor dinâmico como label de anchor

**Origin:** `backend/services/stages/stage5_template/coverage_overlay.py` linha ~257  
**Arquivo:** Função `_generate_anchors()` (ou equivalente)

**O que fazer:**

1. Localizar a linha onde o anchor `label` é atribuído a `item.get("label")`.
2. Verificar qual campo da field_mapping contém o label estático/semântico do campo.
   - Em `field_mappings`, o campo `label_text` contém o texto do label estático do PDF ("Data do Documento", "Nosso Número", etc.)
   - O campo `name` ou `pdf_text` contém o valor dinâmico ("30/03/2026", "23793.36908...")
3. Trocar a lógica para usar `label_text` como label do anchor:
   ```python
   # ANTES (errado — usa valor dinâmico como label):
   label = item.get("label") or item.get("xsd_path") or item.get("node_id")
   
   # DEPOIS (correto — usa label semântico do campo):
   label = item.get("label_text") or item.get("xsd_path") or item.get("node_id")
   ```
4. Verificar se `label_text` é propagado corretamente dos field_mappings para os overlay_items. Se não for, adicionar esse campo no contrato.

**Teste de aceitação:**
- Anchor para o campo data deve mostrar "Data Vencimento" ou similar, não "30/03/2026"
- Anchor para linha digitável deve mostrar "Linha Digitável", não "23793.36908 52020..."

**Impacto do fix:** Melhora UX do SyncView e cobertura visual. Não afeta o pipeline de análise.

**Estimativa:** 2-3h

---

## FIX 3 — R5: Vision agreement mascarando falha silenciosa de Stage 3.2

**Origin:** `backend/services/stages/stage4_mapping/scoring_validation.py` linha ~69  
**Arquivo:** Função que calcula `vision_agreement` no confidence_score

**O que fazer:**

1. Localizar o cálculo de `vision_agreement` no arquivo acima.
2. Adicionar verificação: se `visual_analysis.visual_regions` está vazio ou None:
   ```python
   # ANTES (retorna 0.5 fallback silencioso):
   vision_score = 0.5  # fallback quando visual_analysis não disponível
   
   # DEPOIS:
   visual_regions = visual_analysis.get("visual_regions") or {}
   if not visual_regions:
       logger.warning(
           "vision_agreement: visual_regions vazio para layout %s — "
           "Stage 3.2 Visual Analysis pode ter falhado silenciosamente. "
           "Usando vision_agreement=0.",
           layout_id
       )
       vision_score = 0.0  # zero, não 0.5 — reflete falha real
   ```
3. Com `vision_agreement=0`, o confidence_score geral do layout B cairá de 41 para ~26 → status correto: `human_review_required` com indicação de falha na análise visual.
4. Adicionar log de warning quando Stage 3.2 retorna `visual_regions={}` para que seja detectável nos logs do servidor.

**Teste de aceitação:**
- Quando `visual_analysis.visual_regions={}`, `confidence_scores.*.vision_agreement` deve ser 0 (não 90)
- Log de warning deve aparecer nos logs quando isso ocorrer

**Estimativa:** 1h

---

## Nota sobre R6 (SACADO unmapped) — não é fix independente

O R6 (27 required XSD fields sem mapping) é **consequência de R4+R5**:
- Stage 3.3 `_find_adjacent_value()` usa proximidade espacial — mas em tabelas de boleto os labels podem estar em linhas acima dos valores (não ao lado), o que o algoritmo não detecta
- Layout B (ficha de compensação, onde o bloco SACADO tipicamente aparece) tem `anchor_detection=25` consequência da Visual Analysis vazia (R5)

O R6 NÃO deve ser corrigido com um fix isolado. Após aplicar FIX 1 (encoding) e FIX 3 (vision_agreement), reprocessar o job do Convênio e verificar se o coverage do SACADO melhora. Se ainda permanecer abaixo de 70%, abrir investigação separada para `_find_adjacent_value()` com foco em tabelas de boleto.

---

## Ordem de implementação sugerida

1. **FIX 3** primeiro (1h) — mais simples, melhora diagnóstico
2. **FIX 1** segundo (1-2h) — alto impacto, propaga melhoria por todo o pipeline
3. Reprocessar job do Convênio e medir novo coverage
4. **FIX 2** terceiro (2-3h) — melhora UX/SyncView
5. Verificar R6 (SACADO) após reprocessamento

---

## Validação final (4 success checks do Convênio)

Após os 3 fixes e reprocessamento:

| Check | Esperado após fixes |
|---|---|
| **1.** Canvas mostra algo reconhecível | FIX 1 resolve mojibake, canvas mostra texto correto |
| **2.** Estrutura tem blocos principais | FIX 3 melhora layout B, SACADO deve aparecer |
| **3.** Campos XSD linked | Avaliar R6 após reprocessamento |
| **4.** Export ZIP roda no MAG | Requer "Generate Template" no editor com mappings ajustados → `TemplateGenerator` produz Planet format |

**Nota check #4:** O export usa `TemplateGenerator` (não Stage 5). O `TemplateGenerator` já gera o formato correto (`<body data-bind="with: ...">`, `##TEMPLATE_DATA##`, `base.js`). O problema é que ele precisa de bons `field_mappings` — o que melhora com FIX 1+3.

---

## Arquivos a alterar (resumo)

| Fix | Arquivo | Alteração |
|---|---|---|
| FIX 1 | `backend/services/stages/stage2_extraction/text_extraction.py` | Encoding fallback no `get_text()` |
| FIX 2 | `backend/services/stages/stage5_template/coverage_overlay.py` | `label_text` em vez de `label` para anchors |
| FIX 3 | `backend/services/stages/stage4_mapping/scoring_validation.py` | `vision_agreement=0` quando `visual_regions={}` |

**Temporal coupling (atualizar juntos se tocar):**
- `stage3_structural_analysis.py` ↔ `stage5_template_generation.py` ↔ `stage4_field_mapping.py`
