# Epic 48 — Pilar A (gap) + Pilar B: Repeated Sections, List Binding e Loop Rendering

## Status: Ready

## Objetivo

Fechar o gap remanescente do Pilar A (Stage 3 não detecta seções repetidas) e implementar + validar o Pilar B completo: binding de listas para XSD com `maxOccurs > 1` e renderização de loops no template HTML.

## Contexto

O Epic 47 validou que o pipeline detecta corretamente **campos escalares** em todos os tipos de documento Planet Express. Mas existe um gap não coberto no Pilar A:

> **Stage 3 não detecta seções repetidas.** Um bloco que aparece N vezes numa página (lista de segurados, tabela de beneficiários, itens de extrato) não é "N campos dinâmicos isolados" — é **uma seção que se repete**, e o template precisa de um loop, não de campos numerados.

Isso impacta diretamente o Pilar B:

| Stage | O que precisa | Status antes deste epic |
|-------|--------------|------------------------|
| Stage 3 | Detectar "este bloco é uma lista" | ❌ Não implementado (Pilar A gap) |
| Stage 4 | `seção repetida → XSD nó com maxOccurs > 1` | ❌ Só binding escalar existe |
| Stage 5 | `<repeat data-list="Segurado[]">` em vez de campos estáticos | ❌ Só renderização escalar existe |

**Pré-requisito (não story — responsabilidade do usuário):**
Adquirir **3+ PDFs do mesmo template** para pelo menos 2 tipos de documento com listas (ex.: relatório PosicaoConsolidada com lista de segurados, extrato com lista de movimentações).

## Stories

| Story | Título | Status | Prioridade | Esforço | Dep |
|-------|--------|--------|-----------|---------|-----|
| 48.1 | DevOps: Corrigir Railway — pt_core_news_sm + Redis + MISTRAL_API_KEY | Ready | P0 | 2h | — |
| 48.2 | Defensive: Corrigir crash Stage 1 com PDFs de templates misturados | Ready | P1 | 2h | — |
| 48.3 | SPIKE: Ground truth — dynamic/static + repeated sections por tipo | Ready | P0 | 4h | — |
| 48.4 | Stage 3: implementar detecção de seções repetidas (Pilar A gap) | Ready | P0 | 6h | 48.3 |
| 48.5 | Stage 4: list binding — seção repetida → XSD maxOccurs > 1 | Ready | P0 | 6h | 48.1 + 48.4 |
| 48.6 | Stage 5: loop rendering — `<repeat data-list="...">` no template HTML | Ready | P0 | 4h | 48.5 |
| 48.7 | SPIKE: Validação end-to-end multi-sample com lista — Stage 1→5 via Railway | Ready | P0 | 6h | 48.1 + 48.5 + 48.6 |
| 48.8 | Consolidação: declarar Pilar B completo ou abrir backlog de gaps | Ready | P0 | 2h | 48.7 |
| 48.9 | SPIKE: Calibração empírica dos thresholds Stage 1 ensemble voting | **Done** | P0 | 4h | fixtures |
| 48.10 | Stage 1: Ensemble voting signals — pHash + Font + Struct + MD | **Done** | P0 | 8h | 48.9 |
| 48.11 | Stage 1: 4º sinal ensemble — Markdown Fingerprint (pymupdf4llm) | **Done** | P0 | 2h | 48.10 |

**Total estimado:** ~32h originais + ~14h Stage 1 fix (48.9/48.10/48.11) = ~46h

## Waves de Execução

```
Wave 0 (Stage 1 fix — pré-requisito descoberto em 48.7 spike):  ✅ DONE
  48.9  Calibração thresholds ensemble Stage 1
  48.10 Ensemble voting signals (pHash + Font + Struct)
  48.11 4º sinal: Markdown Fingerprint (pymupdf4llm)
  → Gap 1 Stage 1 corrigido: PosicaoConsolidada×4 cluster único (era 4 clusters separados)

Wave 1 (paralelo — sem deps):
  48.1 DevOps Railway fix
  48.2 Crash fix Stage 1
  48.3 Ground truth multi-sample

Wave 2 (Pilar A gap):
  48.4 Stage 3 repeated sections detection    ← dep: 48.3

Wave 3 (Pilar B — paralelo quando possível):
  48.5 Stage 4 list binding                   ← dep: 48.1 + 48.4
  48.6 Stage 5 loop rendering                 ← dep: 48.5

Wave 4 (validação e fechamento):
  48.7 Validação E2E multi-sample com lista   ← dep: 48.1 + 48.5 + 48.6
  48.8 Consolidação Pilar B                   ← dep: 48.7
```

## Critério de Conclusão do Epic

- Railway funcional: spaCy `pt_core_news_sm`, Redis, MISTRAL_API_KEY ✓
- Crash defensivo corrigido: pipeline retorna erro amigável em vez de crash ✓
- Stage 3 detecta seções repetidas: `section_type: "repeated"` + `list_item_count: N` no document tree ✓
- Stage 4 gera binding de lista: `seção repetida → XSD nó com maxOccurs > 1` no `field_mappings[]` ✓
- Stage 5 renderiza loop: `<repeat data-list="...">` presente no template HTML gerado ✓
- Validação E2E: pipeline processa 3+ PDFs do mesmo template com lista, template gerado é funcionalmente correto ✓
- Story 48.8 produz decisão formal: **PILAR B COMPLETO** ou **GAPS DOCUMENTADOS**

## Arquivos Relevantes

- `backend/services/stages/stage3_structural/` — Stage 3 (implementar repeated sections em 48.4)
- `backend/services/stages/stage4_mapping/` — Stage 4 (implementar list binding em 48.5)
- `backend/services/stages/stage5_template/` — Stage 5 (implementar loop render em 48.6)
- `backend/tests/fixtures/samples/` — fixtures multi-sample (gitignored)
- `docs/reports/epic-48/` — relatórios dos spikes

## Change Log

| Date | Agent | Action |
|------|-------|--------|
| 2026-04-14 | @pm | Epic criado — 6 stories (Opção A inicial) |
| 2026-04-14 | @pm | Revisado para 8 stories (Opção A expandida) — inclui Stage 3 repeated sections (Pilar A gap), Stage 4 list binding e Stage 5 loop rendering |
| 2026-04-18 | @dev (YOLO) | Wave 0 concluída: stories 48.9/48.10/48.11 implementadas. Stage 1 Gap 1 corrigido via ensemble voting 4-signal (pHash+Font+Struct+MD). 7/7 casos de validação local passam. |
