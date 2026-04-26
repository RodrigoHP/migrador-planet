# Análise Profunda — Stage 4 Field Mapping: Algoritmo, Bugs, Limites e Caminhos

**Data:** 2026-04-26  
**Contexto:** Epic 48 — Pilar B Binding XSD  
**Estado:** scalar_coverage = 0.76 (19/25) após RC-I  
**Propósito:** Documento de referência completo para repensar a abordagem com base em evidências acumuladas

---

## 1. O Problema Real

O Stage 4 resolve uma pergunta: **dado um par (label, value) extraído do PDF, qual campo do XSD ele representa?**

Exemplo:
```
label = "TELEFONE"
value = "(19) 98189-4732"
→ Propostas.Propostas.ClienteTelefone ✅
```

O XSD do PosicaoConsolidada tem ~68 paths. O PDF tem ~25 pares dinâmicos a mapear. Parece simples. Na prática, é cheio de armadilhas que levaram a 9 root causes em uma única epic.

---

## 2. Arquitetura Atual do Algoritmo

### Fluxo de 7 sub-steps

```
4.1 XSD Parsing
     ↓ field_tree (paths, types, children)
4.2 Pair Validation
     ↓ validated_pairs[layout_id] = [pair{label, value, block_id, ...}]
4.3 Format Pre-Detection
     ↓ enriquece pares com detected_format (phone, cpf, email, currency, cep...)
4.4 Section-XSD Matching
     ↓ section_xsd_map[layout][section] = {xsd_node, child_paths}
4.5 Batch Field Matching (LLM Gemini Flash)
     ↓ field_mappings[pair] = {xsd_field_path, confidence, candidates}
4.5b List Binding
     ↓ list_bindings (repeated sections → XSD list paths)
4.6 Confidence Scoring + 4.7 Consistency Validation
     ↓ output final
```

### Sub-step crítico: 4.5 Batch Field Matching

Este é o coração do problema. O que acontece:

```
Para cada layout:
  Para cada seção (group de pares):
    1. _is_body_text_pair() → exclui texto corrido (RC-I)
    2. Monta pairs_json [{index: _llm_pos, label, value, detected_format}]
    3. Pega child_paths da seção (ou flat_paths se sem match XSD)
    4. 1 chamada LLM (Gemini Flash) com pairs_json + scoped_paths
    5. _local_idx_map remap: posição LLM → original_index (RC-G)
    6. all_results.update(batch)

PASS 1: score ≥ 0.7 → aceitar, adicionar a used_paths (cross-layout dedup, RC-C)
PASS 2: re-rankear os demais excluindo used_paths
Threshold final: score ≥ 0.4 → mapear; < 0.4 → unmapped
```

### Constantes atuais

| Constante | Valor | Significado |
|-----------|-------|-------------|
| `HIGH_CONFIDENCE_THRESHOLD` | 0.7 | Pass 1 → aceitar sem re-rank |
| `MINIMUM_MATCH_THRESHOLD` | 0.4 | Floor: score abaixo → unmapped |
| `AMBIGUITY_THRESHOLD` | 0.1 | Diferença top-1 vs top-2 → ambíguo |
| `SECTION_MATCH_MIN_SCORE` | 0.65 | Threshold fuzzy seção→XSD (RC-H) |
| `GEMINI_FLASH_MODEL` | gemini-2.0-flash-001 | LLM via OpenRouter |

---

## 3. Histórico Completo de Bugs (RC-A → RC-I)

### RC-A (corpo de texto)
**Sintoma:** "0800 771 5472" e fragmentos de parágrafo mapeavam para ClienteTelefone/ClienteEmail  
**Causa:** `_is_body_text_pair()` existia mas era **dead code** — definida mas nunca chamada  
**Fix (Story 48.21 / RC-I):** ativada no loop de pairs_json com contador `_llm_pos`  
**Refinamento:** "PLANO: 2800 - WHOLE LIFE..." era filtrado incorretamente → check `first_word.endswith(":")`

### RC-B (section scoping espúrio)
**Sintoma:** 5 campos com `dbg_scoped_count=4` — Gemini recebia 4 paths errados em vez de 68  
**Causa:** `SECTION_MATCH_MIN_SCORE=0.3` → "Seção Dados do cliente" (4 campos) matchava `DadosParcelasAVencer` (4 filhos) via count_score  
**Fix (Story 48.20):** `SECTION_MATCH_MIN_SCORE = 0.30 → 0.65`  
**Efeito:** seções sem match de nome caem para flat_paths(68), Gemini acha os campos

### RC-C (cross-layout dedup bug)
**Sintoma:** mesmo path XSD atribuído em múltiplos layouts  
**Causa:** `used_paths: set = set()` inicializado **dentro** do loop `for layout_id`  
**Fix (Story 48.13):** movido para **fora** do loop → dedup genuíno cross-layout

### RC-D (inline field extraction)
**Sintoma:** campos inline (INSCRIÇÃO, TELEFONE, etc.) chegavam sem label_text separado  
**Causa:** Stage 4 lia `block_classifications.field_pair` mas Stage 3 gerava `tree.field/label/value nodes`  
**Fix (Story 48.17):** Stage 4 passou a ler tree nodes (label = filho label, value = filho value)

### RC-E / RC-F (wrapper expansion)
**Sintoma:** seção matchava nó wrapper `Propostas` → child_paths = `["Propostas.Propostas"]` (não folha) → Gemini recebia 1 path complexo → candidates=[]  
**Causa:** `_section_xsd_similarity` fazia match com wrapper node, filhos diretos são complexos  
**Fix (Story 48.18):** `_expand_child_paths()` expande wrappers até folhas reais

### RC-G (pair_index collision entre seções)
**Sintoma:** scalar_coverage=0.32 — candidatos de seções anteriores eram apagados  
**Causa:** LLM retornava `pair_index` como posição local (0,1,2 dentro da seção). `all_results.update(batch)` sobrescrevia keys 0,1,2 da seção anterior. Pass 1 fazia `all_results.get(i)` com `i` = original_index → nunca encontrava  
**Fix (Story 48.19):** `_local_idx_map[_llm_pos] = _p["original_index"]`; remap antes de `all_results.update()`

### RC-H (threshold de seção baixo)
**Sintoma:** scalar_coverage=0.64 após RC-G — 5 campos ainda com `dbg_scoped_count=4`  
**Causa:** SECTION_MATCH_MIN_SCORE=0.3 permitia count_score elevar score de seções sem relação  
**Fix (Story 48.20):** 0.3 → 0.65 (mesmo fix que RC-B, revelado em iteração diferente)

### RC-I (false positives de precisão)
**Sintoma:** 3 mapeamentos incorretos nos 21 mapeados (0.84):  
- body text "(demais localidades)" → ClienteTelefone  
- INSCRIÇÃO (ID subscrição) → ClienteCpf  
- 368,95 (reserva?) → ValorIOF  
**Causa:** `_is_body_text_pair()` dead code + prompt sem constraints semânticas  
**Fix (Story 48.21):** ativação + restrições ClienteCpf/ValorIOF no prompt  
**Custo:** scalar_coverage 0.84 → 0.76

---

## 4. Estado Atual — Campo a Campo

**Run:** job `3b57c785`, 2026-04-26 19:09, scalar_coverage = 0.76 (19/25)

### Unmapped (6) — todos corretos

| Idx | Label | Valor | Por quê unmapped |
|-----|-------|-------|-----------------|
| [00] | "Um abraço," | "Equipe MAG Seguros" | Texto de fechamento, score=0.0 |
| [01] | — | "Conforme seu pedido..." | Body text filtrado (RC-I) |
| [02] | — | "pessoais e planos..." | Body text filtrado |
| [03] | — | "de contato disponíveis..." | Body text filtrado |
| [05] | — | "(demais localidades) e 0800..." | Body text filtrado (RC-I corrigiu) |
| [06] | "Posição Consolidada de Planos" | "Rio de Janeiro, 5 de março de 2026" | Valor composto data+cidade, score=0.3 |

### Mapped (19) — validação

| Idx | Label | Valor | XSD | Score | Veredicto |
|-----|-------|-------|-----|-------|-----------|
| [04] | — | 13271-608 | CEP | 0.8 | ✅ CEP válido |
| [07] | (R$) | 591,70 | DS.ValorPremioContricuicao | 0.5 | ✅ Contribuição seguro |
| [08][09][10][16] | Certificado/ | 11246695428001... | DS.NumeroCertificado | 0.7 | ✅ 4× lista, correto |
| [11] | Benefício | 608.882,69 | DS.ValorBeneficio | 0.8 | ✅ Clara |
| [12] | ENDEREÇO DE RELACIONAMENTO: | RUA DR ERALDO... | PP.ClienteEndereco | 0.8 | ✅ Clara |
| [13] | (R$) | 368,95 | DS.ValorPremioLiquido | 0.6 | ⚠️ Pode ser DPP.ValorReservaAcumulada |
| [14] | (R$) | 591,70  27/11/2023 | DS.DataFimVigencia | 0.4 | ❌ Composto: (R$) sugere moeda, não data |
| [15] | (R$) | 591,70 | DS.ValorPremioContricuicao | 0.5 | ✅ Outra instância de lista |
| [17] | Contribuição | 591,70 | DS.ValorPremioContricuicao | 0.7 | ✅ Label explícito |
| [18] | TELEFONE | (19) 98189-4732 | PP.ClienteTelefone | 0.7 | ✅ RC-I corrigiu (era body text) |
| [19] | INSCRIÇÃO | 1124669542800 | PP.PropostaNumero | 0.4 | ❌ Sem campo XSD correto (não existe ClienteInscricao) |
| [20] | — | PLANO: 2800 - WHOLE LIFE... | PP.Plano | 0.4 | ✅ Correto |
| [21] | Dados dos seguros: | E-MAIL: TELMATSANCHES... | PP.ClienteEmail | 0.7 | ✅ Email correto (label é header seção) |
| [22] | FORMA DE PAGAMENTO | CARTÃO DE CRÉDITO | PP.FormaPagamento | 0.7 | ✅ Clara |
| [23][24] | Apólice | 26 | PP.PropostaNumero | 0.7 | ✅ 2 layouts |

### Campos XSD presentes no documento mas ausentes dos 25 pares

Estes campos **não aparecem** nos validated_pairs — Stage 3 os classificou como estáticos:

| Campo XSD | Observação |
|-----------|-----------|
| `NomeCliente` | Nome do cliente no cabeçalho — Stage 3 classificou como estático |
| `ClienteCpf` | CPF do cliente — Stage 3 classificou como estático |
| `ClienteDataNascimento` | Mesma razão |
| `Vencimento` | Oscila entre runs (às vezes aparece) |
| `DiaAtual / MesAtual / AnoAtual` | Data do relatório — static |

**Conclusão:** parte da "cobertura perdida" não é falha do Stage 4 — é decisão do Stage 3.

---

## 5. Problemas Fundamentais Não Resolvidos

### P1 — Não-Determinismo do LLM

**Evidência:** scalar_coverage variou entre 0.72 e 0.84 em 4 runs com os MESMOS PDFs.

| Run | Coverage | Observação |
|-----|----------|-----------|
| Job `3d5f77e0` (pré-RC-I, RC-G+RC-H) | 0.84 | Máximo histórico |
| Job `c7938fff` (pré-RC-I, mesmo código) | 0.80 | Variância LLM |
| Job `3de440f2` (RC-I v1) | 0.72 | Regressão PLANO descoberta |
| Job `3b57c785` (RC-I v2) | 0.76 | Após fix refinamento |

**Consequência:** o gate ≥0.80 é atingido ou não dependendo do humor do Gemini. Isso não é um sistema confiável para um produto.

### P2 — O Prompt Não Tem Contexto Estrutural

O LLM recebe:
```json
{"index": 0, "label": "(R$)", "value": "368,95", "detected_format": null}
```

E tem que decidir entre: `ValorPremioContricuicao`, `ValorPremioLiquido`, `ValorIOF`, `ValorBeneficio`, `ValorReservaAcumulada`, `ValorContricuicao`, `ValorTotal`...

**O que o LLM não sabe:**
- Posição da célula na tabela
- Outros campos na mesma linha/coluna
- Contexto visual (cor de cabeçalho, alinhamento)
- Qual seção do PDF este campo pertence (a section_context é o nome da seção, não o conteúdo)

### P3 — Label "(R$)" é um Non-Label

Vários campos têm `label = "(R$)"` — é apenas a unidade monetária, não uma label semântica. Com isso, o LLM recebe 4-5 pares com `label = "(R$)"` e diferentes valores monetários e tem que distingui-los sem informação adicional. É adivinhação.

**Campos afetados neste documento:** [07], [13], [14], [15]

### P4 — Blocos Compostos não Separados

Campo [14] = `"591,70  27/11/2023"` — um bloco com dois dados distintos (valor + data).

Stage 3 extraiu como um único pair. Stage 4 tem que mapear o bloco inteiro para um único XSD path. O Gemini escolheu `DataFimVigencia` (para a data), perdendo o valor monetário. O correto seria separar em dois campos: um para `ValorPremioContricuicao` e outro para `Vencimento`.

**Causa raiz:** Stage 3 não faz separação de blocos compostos. Isso é um problema de Stage 3 que se manifesta em Stage 4.

### P5 — INSCRIÇÃO sem Campo XSD

O campo INSCRIÇÃO (número de subscrição do cliente) não tem correspondente no XSD. O sistema mapeia para `PropostaNumero` (mais próximo disponível) mas é semanticamente errado.

Duas possibilidades:
1. O XSD está incompleto (falta `ClienteInscricao`)
2. INSCRIÇÃO é o mesmo que `PropostaNumero` no domínio MAG Seguros (confirmar com cliente)

### P6 — Section Scoping é Binário e Frágil

Quando `SECTION_MATCH_MIN_SCORE = 0.65`, uma seção ou tem match (recebe 4-15 child_paths) ou não tem match (recebe flat_paths=68). Não existe meio-termo. Se uma seção tem score=0.64 por diferença marginal de nome, recebe 68 paths — o Gemini tem muito espaço para errar.

Exemplo do RC-H: score=0.6564 seria "sem match" → flat_paths. Score=0.6501 seria "sem match". A threshold é um corte duro em uma distribuição contínua.

### P7 — Cross-Layout Dedup é Muito Agressivo

Se Layout A (4 páginas) mapeia `ClienteTelefone`, Layout B (11 páginas) não pode mais mapear `ClienteTelefone`. Mas os dois layouts representam **o mesmo cliente** — faz sentido ter o telefone em ambos os layouts.

Para o template, isso significa que uma instância do campo tem binding, outra não. O resultado HTML vai ter `{{ClienteTelefone}}` em um layout e `{{}}` em outro.

---

## 6. Análise Crítica da Abordagem Atual

### O que a abordagem atual pressupõe (mas não é sempre verdade)

| Pressuposto | Realidade |
|-------------|-----------|
| Label + valor é suficiente para identificar o campo XSD | Para `(R$) + valor monetário`, o label não discrimina |
| Seção do PDF tem nome similar ao nó XSD | Nomes do negócio ≠ nomes técnicos XSD |
| Gemini é determinístico o suficiente | Varia ±2-3 campos entre runs |
| Cada campo ocorre uma vez por layout | Campos em listas repetem — 4× `NumeroCertificado` |
| Scoped paths ajudam o Gemini | Se o scope estiver errado, atrapalha mais do que ajuda |

### Por que o número 0.80 é frágil

O gate de 80% foi atingido (0.84) num run e perdido (0.76) no próximo. Ambos os runs usam o mesmo código, mesmos PDFs, mesmo XSD. A diferença é puramente não-determinismo do LLM.

Para um produto de template authoring, o resultado precisa ser **estável e reprodutível**. Subir de 0.76 para 0.82 cortando um pouco mais aqui e adicionando uma restrição de prompt ali é trabalho de Sísifo — a pedra rola de volta a cada run.

---

## 7. Ideias para Repensar a Abordagem

### Ideia A — Regras Determinísticas Primeiro, LLM Só para Ambíguos

Para campos com `detected_format` claro, mapear por regra, sem LLM:

| detected_format | → XSD path | Confiança |
|-----------------|------------|-----------|
| `cep` | `CEP` | 100% determinístico |
| `phone` | `PP.ClienteTelefone` | 100% |
| `email` | `PP.ClienteEmail` | 100% |
| `cpf` | `PP.ClienteCpf` | 100% |
| `currency_brl` com label "Benefício" | `DS.ValorBeneficio` | Alta |
| `currency_brl` com label "Contribuição" | `DS.ValorPremioContricuicao` | Alta |
| `date_numeric`/`date_extenso` com label "Vencimento" | `PP.Vencimento` | Alta |

Resultado: 8-10 campos mapeados determinísticamente (CEP, telefone, email, CPF, etc.). LLM só é chamado para os campos ambíguos sem formato claro.

**Prós:** elimina variância LLM para campos fáceis; mais rápido; menos custo  
**Contras:** não escala para XSDs com muitos campos de mesmo tipo

### Ideia B — Abordagem Inversa: XSD → PDF (Pull em vez de Push)

Em vez de "para cada par do PDF, qual campo XSD?", fazer "para cada campo XSD esperado, onde no PDF está?".

```
Para NomeCliente:
  - Buscar no PDF blocos próximos a label com keyword "nome"/"cliente"/"titular"
  - Ou usar NER (o projeto já tem spaCy pt_core_news_sm) para detectar nome próprio em posição de cabeçalho
  
Para ClienteCpf:
  - Buscar blocos com regex CPF (###.###.###-##) — determinístico
  
Para ValorBeneficio:
  - Buscar blocos com label "Benefício" + valor monetário na mesma linha/célula
```

Esta abordagem é mais **targeted** e menos sensível a como Stage 3 organizou os dados.

**Prós:** cada campo tem critério específico; determinístico para campos estruturados  
**Contras:** requer conhecimento por campo XSD; menos genérico

### Ideia C — Prompt com Few-Shot Examples (Ground Truth como Contexto)

O arquivo `ground-truth-posicaoconsolidada.json` existe. Usar os mapeamentos conhecidos como exemplos no prompt:

```
Você já mapeou documentos como este antes. Exemplos:
- label="TELEFONE", value="(xx) xxxxx-xxxx" → ClienteTelefone
- label="Certificado/", value="número" → DadosSeguros.NumeroCertificado
- label="(R$)" na seção DadosSeguros → ValorPremioContricuicao ou ValorPremioLiquido dependendo da posição
```

**Prós:** LLM aprende o padrão do domínio MAG; reduz erros em campos conhecidos  
**Contras:** específico por tipo de documento; não generaliza automaticamente

### Ideia D — Votação com Múltiplos Runs (Ensemble)

Fazer N=3 chamadas independentes ao LLM para cada seção. Aceitar somente mapeamentos em que 2/3 runs concordam.

```
Run 1: 368,95 → ValorPremioLiquido
Run 2: 368,95 → ValorReservaAcumulada  
Run 3: 368,95 → ValorPremioLiquido
→ Votação: ValorPremioLiquido (2/3) ✅
```

**Prós:** elimina outliers não-determinísticos; score de confiança = proporção de votos  
**Contras:** 3× custo e latência de LLM; pode não resolver ambiguidade real

### Ideia E — Usar Posição Espacial como Âncora

Para documentos gerados por motor (Planet Express), a posição de cada campo é determinística entre instâncias. Um campo na coluna 3, linha 2 de uma tabela é SEMPRE o mesmo campo XSD.

Approach:
1. Usar bboxes dos campos (já disponíveis em `value_bbox`)
2. Normalizar posição relativa dentro da seção
3. Se posição X,Y relativa matchou com um mapeamento conhecido → reusar

Isso seria um tipo de **template learning** — após mapear uma vez corretamente, reusar baseado em posição para runs futuros.

**Prós:** totalmente determinístico após aprendizagem; explora a natureza vetorial dos PDFs Planet  
**Contras:** requer run inicial correto; falha se layout muda (mas PDFs Planet Express têm layout fixo)

### Ideia F — Hierarquia XSD como Contexto Estrutural

O sistema atual passa uma lista plana de XSD paths para o Gemini. Não passa a hierarquia. O Gemini não sabe que:
- `ValorPremioContricuicao` está em `DadosSeguros.DadosSeguros[]` (seguro de vida)
- `ValorReservaAcumulada` está em `DadosPlanoPrevidencia.DadosPlanoPrevidencia[]` (plano de previdência)

Mudar o prompt para:
```
Seção: "Certificado/" com campos [NumeroCertificado, ValorBeneficio, ValorPremioContricuicao, ...]
Contexto: estes campos pertencem a DadosSeguros (apólice de seguro de vida).
Para campos de PREVIDÊNCIA, use DadosPlanoPrevidencia.

Não use DadosPlanoPrevidencia.ValorReservaAcumulada para campos na seção de seguro.
```

**Prós:** resolve a ambiguidade entre campos monetários de diferentes subárvores  
**Contras:** requer que o section-XSD matching esteja funcionando (se cair para flat_paths, o contexto se perde)

### Ideia G — Re-classificar o Pipeline

O problema atual é que Stage 4 faz TWO jobs que deveriam ser separados:

1. **Classificação semântica do campo** (o que é este campo?) — "é um telefone", "é uma data de vencimento", "é um valor de benefício"
2. **Mapeamento para XSD** (qual path XSD?) — "PP.ClienteTelefone", "PP.Vencimento", "DS.ValorBeneficio"

Atualmente o LLM faz os dois em uma chamada. Separar:
- Passo 1: classificar com regras + formato detectado + LLM especializado em classificação
- Passo 2: lookup determinístico: tipo_semântico → XSD_path (tabela fixa por XSD)

---

## 8. O que os Dados Nos Dizem

### Campos que o sistema mapeia bem (determinísticos na prática)

Estes campos têm labels explícitas, formatos detectáveis, ou sinal forte — o LLM não erra:

- **CEP** (formato cep detectável) ✅ todos os runs
- **ClienteTelefone** (label "TELEFONE", formato phone) ✅ todos os runs pós-RC-I
- **ClienteEmail** (label "E-MAIL", formato email) ✅ todos os runs
- **ClienteEndereco** (label "ENDEREÇO DE RELACIONAMENTO") ✅ todos os runs
- **FormaPagamento** (label "FORMA DE PAGAMENTO") ✅ todos os runs
- **NumeroCertificado** (label "Certificado/") ✅ todos os runs
- **ValorBeneficio** (label "Benefício") ✅ todos os runs
- **PropostaNumero** (label "Apólice") ✅ todos os runs
- **Plano** (valor "PLANO: ...") ✅ após fix RC-I refinement

### Campos que o sistema erra sistematicamente ou é inconsistente

- **368,95** → varia entre ValorIOF, ValorPremioLiquido, ValorReservaAcumulada (runs diferentes)
- **591,70  27/11/2023** → varia entre Vencimento, DataFimVigencia, unmapped
- **INSCRIÇÃO** → sem campo XSD correto; mapeia para o mais próximo disponível
- **Rio de Janeiro, 5 de março de 2026** → compound; Cidade, unmapped, ou Vencimento dependendo do run

### Conclusão dos dados

**9 campos têm mapeamento robusto e determinístico** — esses nunca erram.  
**4-5 campos são ambíguos estruturalmente** — o sistema não tem informação suficiente para decidir corretamente.  
**2 campos são problemas de Stage 3** (compound blocks, classificação static/dynamic).

Subir de 0.76 para 0.84 estável é possível. Subir de 0.84 para 0.95+ requer mudar a abordagem para os campos ambíguos.

---

## 9. Diagnóstico Raiz: O Que Está Errado no Design

O algoritmo atual é um **matcher genérico** que tenta resolver com LLM o que deveria ser resolvido com **conhecimento de domínio estruturado**.

O domínio (documentos Planet Express, XSD MAG Seguros) é **completamente conhecido e fixo**. O XSD não muda. O layout dos PDFs não muda entre instâncias. Os campos têm tipos semânticos claros.

A abordagem LLM-first foi escolhida para generalizar para qualquer XSD/documento. Mas:
1. O produto serve ~200 templates distintos, não milhões
2. Cada tipo de documento é processado uma vez para criação de template
3. Alta fidelidade importa mais do que generalização

**A pergunta errada:** "Consigo mapear qualquer documento para qualquer XSD automaticamente com LLM?"  
**A pergunta certa:** "Consigo dar ao usuário um sistema de binding que ele possa REVISAR e CORRIGIR facilmente?"

---

## 10. Recomendação para o Próximo Passo

### Caminho A — Incremental (menor risco)

Implementar **Ideia A** (regras determinísticas + LLM só para ambíguos):

1. Criar `deterministic_mapping.py` com tabela `detected_format → XSD_path`
2. Para campos com formato detectado: mapear sem LLM (0 variância)
3. Para campos com label semântica conhecida: mapear por keyword match
4. LLM apenas para os ~5 campos realmente ambíguos

Ganho esperado: cobertura estável ≥0.80 para os 14 campos com sinal claro; os ambíguos ficam como "needs_review" para o usuário corrigir no editor (Pilar C).

### Caminho B — Estrutural (maior impacto)

Implementar **Ideia E + G** (posição espacial + classificação em dois passos):

1. Stage 4 passa a ser um processo de dois passos: classificar semanticamente → lookup tabela
2. Adicionar `value_bbox` como sinal de agrupamento (campos na mesma linha/coluna de tabela)
3. Após primeiro template mapeado corretamente, salvar `{position_signature → xsd_path}` como cache reutilizável

Este caminho é mais trabalho mas resolve o problema estruturalmente e permite que o sistema "aprenda" com correções do usuário no Editor (Pilar C).

### Não Recomendado

Continuar iterando sobre thresholds e constraints no prompt Gemini. A taxa de retorno está diminuindo (cada RC conserta 1-2 campos enquanto introduz 1 nova regressão) e a variância LLM impede estabilidade.

---

## 11. Index de Arquivos Relevantes

| Arquivo | Relevância |
|---------|-----------|
| `backend/services/stages/stage4_mapping/section_matching.py` | Algoritmo principal (4.4 + 4.5) |
| `backend/services/stages/stage4_mapping/constants.py` | Thresholds + prompt Gemini |
| `backend/services/stages/stage4_mapping/stage4_field_mapping.py` | Orquestrador 7 sub-steps |
| `backend/tests/fixtures/samples/relatorio/PosicaoConsolidada.xsd` | XSD do documento testado |
| `backend/tests/fixtures/samples/relatorio/ground-truth-posicaoconsolidada.json` | Mapeamentos esperados |
| `backend/scripts/spike_48_validate_e2e.py` | Script de validação E2E |
| `backend/scripts/_precision_check.py` | Script de auditoria de precisão |
| `docs/reports/epic-48/e2e-validation-posicao-consolidada.json` | Resultados do último run |
| `docs/stories/epics/epic-48-pilar-b-binding-xsd/48.19-48.21.story.md` | Histórico RC-G, RC-H, RC-I |

---

*Documento gerado em 2026-04-26 para planejamento de Epic 49+ e revisão de arquitetura do Pilar B.*
