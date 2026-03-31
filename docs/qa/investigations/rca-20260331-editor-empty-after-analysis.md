# RCA: Editor Vazio Após Análise Concluída

**ID:** rca-20260331-editor-empty-after-analysis
**Data:** 2026-03-31
**Investigador:** @qa (Quinn)
**Severidade:** High
**Status:** Resolvido — commit `4b6be4c`

---

## Sintoma

Análise pipeline v2 conclui com sucesso (30 campos mapeados, HTML gerado, 5319 bytes). Ao clicar em "Abrir no Editor":
- Aba **Estrutura:** "Nenhum documento carregado"
- Aba **Campos:** "de 0 campos mapeados" / "Nenhum campo disponível"

## Classificação

| Dimensão | Valor |
|----------|-------|
| Cynefin | Complicated |
| Severidade | High |
| Scope | Cross-module (backend orchestrator + frontend session store) |

## Root Cause (E1 — Confirmed)

`pipeline_orchestrator_v2.py` linhas 399-411 construía o resultado final como:

```python
result = {
    "stage_1": context.get("stage_1_result", {}),
    ...
    "stage_5": context.get("stage_5_result", {}),   # apenas summary
    "template_draft": ...,
}
```

O frontend (`session.loadFromPipelineResult`) esperava chaves flat: `layout_types`, `field_mappings`, `trees_by_layout`, `document_structure`, `confidence_scores`. Todas retornavam `undefined` → todos os `if (result.X)` no session store eram falsos → nenhum store era populado → editor vazio.

**Contributing factor:** Stage 5 (`_step_5_6_pipeline_result`) já construía corretamente o `result_json` com todas as chaves flat em `context["result_json"]`, mas o orquestrador ignorava esse objeto e usava apenas `stage_5_result` (subconjunto de summary).

## Fix

`pipeline_orchestrator_v2.py` — merge de `result_json` no retorno:

```python
result_json = context.get("result_json", {})
result = {
    **result_json,           # contrato flat do frontend
    "_debug_stages": {       # summaries por stage (introspection)
        "stage_1": context.get("stage_1_result", {}),
        ...
    },
}
```

## Barreiras Falhadas

| Camada | Status | Criticality |
|--------|--------|-------------|
| Tipo de retorno explícito em `run_pipeline_v2` | absent | HIGH |
| Teste de integração `fetchAndLoadResult → stores populados` | absent | HIGH |
| TypeScript tipando resposta da API | absent | MEDIUM |
| E2E "abrir editor após análise" | absent | LOW |

## Testes Criados

- `test_run_pipeline_v2_returns_flat_result_keys` — verifica que `layout_types`, `field_mappings`, `document_structure`, `template_draft` estão no nível raiz do resultado
- `test_run_pipeline_v2_result_json_merging` — inspeção de source confirma uso de `**result_json`
- `test_run_pipeline_v2_executes_all_stages` — atualizado para novo formato (`_debug_stages`)

## Anti-Pattern Registrado

**AP-004** — Contrato de retorno orquestrador não tipado (ver `docs/qa/known-anti-patterns.md`)

## Achados Colaterais (Backlog)

| ID | Tipo | Descrição |
|----|------|-----------|
| F-1 | Tech Debt | `stage_5_result` ser subconjunto de `result_json` não está documentado |
| F-2 | Missing Test | Nenhum teste de integração `análise → resultado → editor` |
| F-3 | Missing Test | Nenhum teste E2E de "Abrir no Editor" após análise |
