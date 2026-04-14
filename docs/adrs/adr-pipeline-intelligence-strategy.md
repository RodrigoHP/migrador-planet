# ADR-031: Estratégia de Inteligência do Pipeline

**Status:** ⚠️ Revised — Partial (2026-04-10)
**Data:** 2026-04-10
**Autores:** @architect Aria
**Revisão:** v2 removeu propostas inválidas após releitura da documentação e descoberta de decisão de produto prévia

---

## Histórico da ADR

**v1 (descartada):** Propunha Document Fingerprinting + Template Library + Fast path para tipos conhecidos + redesign de Stage 5 com Gemini 2.0 Flash.

**Problemas da v1:**
- Desconhecia a decisão de produto documentada em `docs/audit/16-layout-types.md:49`: "Layout Fingerprint / Registry: **removido por decisão de produto** — cada template é independente, sem caso de uso para reutilização cross-job."
- Ignorava a decisão arquitetural explícita em `pipeline-redesign-v3.md` seção 8.10: "Stage 5 é 100% algorítmico. Zero chamadas LLM. Todo o trabalho de IA já foi feito nos Stages 1-4."
- Especulava sobre a causa do output errado no canvas sem investigar.
- O exemplo "boleto" foi interpretado como tipo reutilizável, quando na verdade é apenas um template específico entre ~200+ layouts únicos esperados.

**v2 (este documento):** Mantém apenas o que é válido independente da tese de reuso.

---

## Contexto do Produto (atualizado)

- ~200+ layouts diferentes esperados no ciclo de vida do produto
- Cada template é **independente** — não há reuso cross-job
- Pipeline processa do zero cada documento
- Stage 5 é **100% algorítmico por decisão arquitetural** (`pipeline-redesign-v3.md` v3.16)
- Usuário não-dev corrige no editor visual o que o pipeline não conseguir gerar

---

## Propostas Mantidas (ambas independentes do registry)

### Proposta 1 — Substituir GPT-4o por Gemini 2.0 Flash no Stage 3.2 Visual Analysis

**Contexto:** `backend/services/stages/stage3_structural/visual_analysis.py:270` usa `openai/gpt-4o` via OpenRouter para Visual Analysis (1 chamada por cluster representativo).

**Custo atual:** `ESTIMATED_COST_PER_VISION_CALL = $0.025` (conforme `openrouter_client.py:37`)

**Proposta:** Trocar para `google/gemini-2.0-flash-001` (mesmo modelo já usado no Stage 4 via `stage4_mapping/constants.py:8`).

**Custo estimado:** ~$0.002/chamada — **~92% de economia**

**Risco:** Baixo. Gemini 2.0 Flash suporta imagem via OpenRouter. Stage 3.2 já tem `handle_service_failure()` fallback. O resultado alimenta `visual_regions`/`drawn_elements` — não é caminho crítico para HTML.

**Trade-off:** Gemini Flash pode ter qualidade ligeiramente inferior a GPT-4o em tarefas de vision complexas. Para este caso (detectar regiões header/body/footer e consistency score), a diferença deve ser marginal. Testar empiricamente antes de ativar.

**Implementação:** 1 story, ~1-2 dias. Swap de model string + validação do formato de resposta + comparação A/B em job real.

---

### Proposta 2 — Injetar XML exemplo no prompt do Stage 4 Field Mapping

**Contexto:** Quando o usuário faz upload de PDF + XSD + XML exemplo, o XML contém a estrutura de dados **real** com valores de exemplo — é a informação mais valiosa para o field mapping. Atualmente o XML é ignorado pelo pipeline.

**Proposta:** Passar o XML para `stage4_mapping/section_matching.py:_llm_batch_match_scoped()` como contexto adicional no prompt do Gemini Flash. O modelo já está fazendo a chamada — adicionar payload extra tem custo marginal.

**Benefício esperado:** Ground truth de como os dados realmente aparecem ajuda o modelo a desambiguar XSD paths com nomes similares. Reduz falsos positivos no mapping.

**Risco:** Baixo. O prompt fica mais longo (custo de tokens aumenta ligeiramente — ~10-20% por chamada no Stage 4, ~$0.001-0.002/job). O XML é opcional — se não houver, o comportamento atual se mantém.

**Implementação:** 1 story, ~2 dias. Propagar XML no `context` desde o upload handler + injetar no prompt + testes.

---

## Propostas Descartadas (contaminadas pela v1)

### ❌ Document Fingerprinting

**Motivo:** Decisão de produto explícita (`docs/audit/16-layout-types.md:49`). Não há tipos conhecidos reutilizáveis. Cada um dos ~200+ layouts é único.

### ❌ Template Library / Fast path

**Motivo:** Consequência direta da ausência de registry. Sem tipos conhecidos não há fast path.

### ❌ Redesign de Stage 5 com Gemini 2.0 Flash

**Motivo:** Stage 5 é 100% algorítmico por decisão arquitetural explícita (pipeline-redesign-v3.md seção 8.10). Antes de propor LLM em Stage 5, preciso investigar **por que** o output determinístico está errado — pode ser bug no walker, bug no tree-building do Stage 3.4, bug no frontend overlay, ou outra coisa completamente diferente.

**Substituir por:** RCA formal (`@qa *investigate`) do bug "blue dots no canvas" — ver próximo passo.

---

## Próximo Passo Obrigatório — RCA do Bug Visual

O sintoma "blue dots no canvas + PDF de cabeça para baixo + elementos mal posicionados" é um **bug não investigado**. Não posso propor arquitetura sem saber a causa raiz.

**Ação:** Acionar `@qa *investigate "canvas mostra blue dots e elementos mal posicionados em vez de HTML semântico"` conforme `rca-principle.md`.

**Hipóteses a investigar (sem ordem de prioridade):**

| # | Hipótese | Onde verificar |
|---|----------|----------------|
| H1 | `document_trees` do Stage 3.4 chegam com hierarquia pobre/plana | Stage 3.4 Hierarchy Builder output + logs |
| H2 | `_tree_to_html` gera HTML absolute-positioned que é visualmente caótico | Inspecionar `template_draft.html` de um job real |
| H3 | `field_mappings` têm coverage muito baixo → maioria dos nós sem `data-bind`, aparecem como texto solto | Stage 4 coverage per-layout |
| H4 | `visual_analysis` consistency baixo → seções ficam vazias | Stage 3.2 output |
| H5 | "Blue dots" é o `CoverageOverlay.vue` mal-calibrado, não o HTML | Frontend overlay + `overlay_by_layout` |
| H6 | Bug separado: PDF invertido na SyncView é frontend (transformação de coordenadas) | `SyncView.vue` + coord flip |

**Dados necessários para RCA:**
1. Amostra do `template_draft.html` de um job recente (ex: Corporate.Boleto.Convenio)
2. `overlay_by_layout` do mesmo job
3. `document_trees` do Stage 3.4 do mesmo job
4. Screenshot do canvas com o bug visível (já temos)

---

## Plano de Execução (revisado)

### Fase 1 — RCA (bloqueia qualquer redesign)

- [ ] `@qa *investigate` do bug "blue dots no canvas"
- [ ] Relatório de investigação com causa raiz identificada
- [ ] Decidir se o fix é frontend, pipeline, ou ambos

### Fase 2 — Wins de custo/precisão independentes (seguros)

- [ ] Story: Trocar GPT-4o por Gemini 2.0 Flash no Stage 3.2 (~1-2 dias)
- [ ] Story: Injetar XML exemplo no prompt do Stage 4 (~2 dias)

### Fase 3 — Depois do RCA

- Definir se Stage 5 precisa de mudança (e qual)
- Definir se alguma outra decisão arquitetural precisa ser revisitada

---

## Referências

- Decisão de produto (registry descartado): `docs/audit/16-layout-types.md:49`
- Pipeline redesign v3: `docs/architecture/pipeline-redesign-v3.md` (Stage 5 seção 8.10)
- ADR-030: Editor Surface Strategy (`adr-editor-surface-strategy.md`)
- Constitutional rule: `.claude/rules/rca-principle.md` (obriga RCA antes de fix)
- Stage 3.2 Vision: `backend/services/stages/stage3_structural/visual_analysis.py`
- Stage 4 mapping: `backend/services/stages/stage4_mapping/section_matching.py`
- OpenRouter client: `backend/services/openrouter_client.py`
