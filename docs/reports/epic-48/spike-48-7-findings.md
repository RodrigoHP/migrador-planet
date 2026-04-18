# Spike 48.7 — Findings: Validação E2E Pilar B

**Status:** `current`
**Data:** 2026-04-17
**Autor:** spike executado via Railway API (3× PosicaoConsolidada.pdf)
**Commit de referência:** `9c9f619`

---

## Contexto

Spike E2E para validar o pipeline completo (Stages 1→5) com 3 instâncias reais do mesmo template (`PosicaoConsolidada`). Objetivo: confirmar que Pilar B (Binding XSD) está funcionando end-to-end antes de atacar os gaps.

XSD usado: `backend/tests/fixtures/samples/relatorio/PosicaoConsolidada.xsd`
PDFs: 3 instâncias distintas do relatório PosicaoConsolidada.

---

## Resultados por Stage

| Stage | Resultado | Detalhe |
|-------|-----------|---------|
| Stage 1 — Clustering | **FAIL** | 3 layouts / 3 PDFs — clustering não agrupou |
| Stage 3 — Repeated sections | **PASS** | 22 nós `repeated_section` detectados |
| Stage 3.1 — Dinâmico/Estático | **PASS** | 100% recall (dynamic + static classificados) |
| Stage 4 — List bindings | **PASS** | 22 `ListBinding` gerados (via `coverage.lists`) |
| Stage 4 — Scalar coverage | **PARTIAL** | 63.2% dos campos mapeados (threshold: 80%) |
| Stage 5 — `<repeat>` presente | **PASS** | 22 elementos `<repeat>` no HTML |
| Stage 5 — `data-list` preenchido | **FAIL** | `data-list=""` vazio — **fix commitado** `82a1d56` |

---

## Gap 1 — Stage 1: Clustering não agrupa instâncias do mesmo template

### O que deveria acontecer

```
PDF1 (instância 1) ──┐
PDF2 (instância 2) ──┼──→ Layout A (1 cluster = 1 tipo de documento)
PDF3 (instância 3) ──┘
```

### O que aconteceu

```
PDF1 → Layout A  (cluster próprio)
PDF2 → Layout B  (cluster próprio)
PDF3 → Layout C  (cluster próprio)
```

### Root cause (hipótese)

O algoritmo de similaridade do Stage 1 está pesando demais o **conteúdo** (valores numéricos, nomes, datas — que mudam entre instâncias) em relação à **estrutura** (posição dos blocos, labels fixos, quantidade de seções — que são idênticas).

É como comparar dois boletos do mesmo banco e dizer que são documentos diferentes porque os valores de linha digitável são distintos.

### Impacto em cascata

- Stage 3 compara campos entre documentos do mesmo cluster para decidir o que é fixo vs dinâmico
- Com 1 PDF por cluster, não há comparação → Stage 3 não detecta variação → menos campos dinâmicos corretos
- Stage 4 tem menos material para mapear ao XSD → cobertura cai

### O que precisamos investigar para atacar

1. Qual métrica de similaridade o Stage 1 usa hoje? (cosine de embeddings? jaccard de texto? posições?)
2. Quais features entram na comparação? (texto bruto? só estrutura? bbox?)
3. Threshold de agrupamento: está muito conservador?

### Ataque proposto

Separar a similaridade em 2 componentes:
- **Similaridade estrutural** (posição dos blocos, quantidade de seções, labels fixos) — peso alto
- **Similaridade de conteúdo** (valores dos campos dinâmicos) — peso zero ou muito baixo

---

## Gap 2 — Stage 4: Cobertura escalares 63.2% (threshold: 80%)

### O que aconteceu

Stage 4 recebeu os campos dinâmicos detectados pelo Stage 3 e tentou mapear cada um para um nó do `PosicaoConsolidada.xsd`. Mapeou 63.2% — 36.8% ficaram sem binding XSD.

### Root causes possíveis

| Causa | Exemplo | Probabilidade |
|-------|---------|--------------|
| Nome do campo no PDF não casa com nó do XSD | PDF: `"Nome do Titular"` → XSD: `NomeCliente` | Alta |
| Campo existe no XSD mas algoritmo não atingiu confiança mínima | Gemini retorna `confidence < threshold` | Média |
| Campo não existe no XSD (gap de cobertura do XSD) | PDF tem campo que XSD não prevê | Baixa |
| Gap 1 em cascata: menos campos dinâmicos detectados → menos oportunidades de match | — | Alta |

### Relação com Gap 1

O Gap 1 piora o Gap 2. Com clustering correto (1 layout para 3 PDFs), Stage 3 detectaria mais campos como dinâmicos (pois vê variação cross-document). Mais campos dinâmicos = mais oportunidades para Stage 4 mapear = cobertura maior.

**Estimativa:** corrigir Gap 1 provavelmente eleva a cobertura para ~75-80% sem tocar Stage 4.

### Ataque proposto

1. **Corrigir Gap 1 primeiro** — medir impacto na cobertura
2. Se ainda < 80%: expandir matching do Stage 4 (sinônimos PT-BR, normalização de labels, prompt Gemini mais rico)

---

## Fix Já Aplicado — Stage 5: `data-list` vazio

### Problema

`_render_repeat_element()` em `html_tree.py` hardcodava `xsd_list_path = ""`. Stage 4 mapeava 22 `ListBinding` com `xsd_list_path` correto, mas Stage 5 não recebia essa informação.

Resultado: `<repeat data-list="" data-count="2" ...>` — `data-list` sempre vazio.

### Fix (commit `82a1d56`)

`_step_5_1_tree_driven_html()` agora recebe `list_bindings`, constrói dict `{section_id → xsd_list_path}` por layout e propaga pela árvore recursiva. `_render_repeat_element()` lookup o `section_id` do nó e preenche `data-list` corretamente.

Resultado esperado pós-deploy: `<repeat data-list="Propostas[]" data-count="3" ...>`

---

## Plano de Ataque

### Prioridade 1 — Gap 1 (Stage 1 clustering)

Antes de qualquer outra coisa. É o problema raiz que degrada Stage 3 e Stage 4.

**Passos:**
1. Ler código atual do Stage 1 — entender o algoritmo de similaridade
2. Instrumentar: logar as features e scores de similaridade para os 3 PDFs
3. Identificar onde os 3 PDFs divergem no score (o que está pesando errado)
4. Ajustar: dar peso apenas à estrutura (bboxes, labels fixos, contagem de blocos)
5. Revalidar spike: deve resultar em 1 layout para 3 PDFs

### Prioridade 2 — Gap 2 (cobertura escalares)

Só atacar após Gap 1 corrigido e spike revalidado.

**Passos:**
1. Rodar spike com clustering correto — medir nova cobertura
2. Se ainda < 80%: analisar quais campos ficaram sem binding e por quê
3. Criar ground truth manual dos campos que deveriam mapear
4. Ajustar matching (normalização, sinônimos, prompt Gemini)

---

## Artefatos Gerados

| Arquivo | Descrição |
|---------|-----------|
| `docs/reports/epic-48/ground-truth-posicaoconsolidada.json` | Ground truth manual dos campos do XSD |
| `docs/reports/epic-48/e2e-validation-posicao-consolidada.json` | Resultado bruto do spike via API |
| `backend/scripts/spike_48_validate_e2e.py` | Script de validação E2E Railway |
| `backend/tests/fixtures/samples/relatorio/PosicaoConsolidada.xsd` | XSD real do template |
