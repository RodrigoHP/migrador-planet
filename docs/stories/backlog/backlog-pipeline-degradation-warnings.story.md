---
epic: TBD
story: TBD
title: "Observabilidade: Propagar warnings de degradação do pipeline via SSE ao frontend"
status: Done
executor: "@dev"
quality_gate: "@qa"
quality_gate_tools: [static_analysis, unit_test, manual_ux]
depends_on: []
source_rca: "rca-2026-03-31-spacy-xsd-warnings"
source_finding: "systemic"
priority: medium
---

# Story TBD: Propagar warnings de degradação do pipeline via SSE ao frontend

## Status
Draft

## Story
**As a** usuário que fez upload de PDF e XSD para análise,
**I want** ser informado quando o pipeline rodou em modo degradado (spaCy ausente, XSD não encontrado, Vision AI em fallback),
**so that** eu saiba que o resultado pode ter qualidade reduzida e possa agir (reenviar, verificar configuração, etc.).

## Contexto

Investigação `rca-2026-03-31-spacy-xsd-warnings` (2026-03-31) revelou gap sistêmico:
o pipeline emite `logger.warning()` internamente mas **nenhum mecanismo propaga esses
avisos até o frontend**. O usuário vê `pipeline_completed` com sucesso mesmo quando:

- spaCy não está disponível → NER layer desabilitado (Stage 3 em modo regex-only)
- XSD não foi encontrado → field_tree = None (Stage 4 sem mapeamento de campos)
- Vision AI indisponível → análise estrutural em fallback ~75% qualidade (AP-005)

O orquestrador só conhece dois estados: `completed` ou `failed`. Não existe estado
`degraded`. O `completion_event.summary` não carrega campo de warnings.

**Anti-pattern:** AP-005 (Silent Service Degradation).

**Impacto atual:** Usuário sobe XSD, pipeline ignora silenciosamente, resultado chega
sem mapeamento de campos — sem nenhum aviso na UI.

## Acceptance Criteria

1. **Backend — canal de warnings no context:**
   Cada stage pode escrever em `context["_pipeline_warnings"]` (list de dicts):
   ```python
   context.setdefault("_pipeline_warnings", [])
   context["_pipeline_warnings"].append({
       "code": "spacy_unavailable",
       "severity": "info",  # info | warning | error
       "message": "NER layer desabilitado — modelo spaCy não encontrado. Classificação usando regex-only.",
       "stage": 3,
   })
   ```

2. **Stage 3 — spaCy indisponível:**
   Quando `_get_nlp()` retorna `None`, além do `logger.warning()` existente,
   adicionar entry em `context["_pipeline_warnings"]` com `code: "spacy_unavailable"`.

3. **Stage 4 — XSD não encontrado:**
   Quando `xsd_path` está ausente/vazio, além do `logger.warning()` existente,
   adicionar entry em `context["_pipeline_warnings"]` com `code: "xsd_not_found"`.

4. **Orquestrador — propagação no completion_event:**
   O campo `summary` do `pipeline_completed` SSE event inclui:
   ```json
   {
     "layouts_detected": 3,
     "page_count": 5,
     "api_cost": 0.02,
     "warnings": [
       {"code": "spacy_unavailable", "severity": "info", "message": "..."},
       {"code": "xsd_not_found", "severity": "warning", "message": "..."}
     ]
   }
   ```
   Se sem warnings: `"warnings": []`.

5. **Frontend — banner de avisos na AnalyzingPage:**
   Quando `pipeline_completed` chega com `warnings.length > 0`:
   - Exibir banner não-bloqueante abaixo do resultado
   - Severity `warning` → ícone ⚠️ amarelo
   - Severity `info` → ícone ℹ️ azul
   - Cada warning mostra `message` legível
   - Banner é dispensável (botão fechar)

6. **Nenhuma regressão** — pipelines sem warnings continuam funcionando identicamente.

7. **Testes:**
   - `test_pipeline_orchestrator_v2.py`: mock de stage com `_pipeline_warnings` populado
     → verificar que `completion_event.summary["warnings"]` contém os items
   - `test_stage3_structural_analysis.py`: quando spaCy indisponível
     → `context["_pipeline_warnings"]` contém entry `spacy_unavailable`
   - `test_stage4_field_mapping.py`: quando `xsd_path` vazio
     → `context["_pipeline_warnings"]` contém entry `xsd_not_found`

## Scope

**IN:**
- `backend/services/pipeline_orchestrator_v2.py` — agregar `_pipeline_warnings` no `completion_event`
- `backend/services/stages/stage3_structural_analysis.py` — emitir warning quando spaCy ausente
- `backend/services/stages/stage4_field_mapping.py` — emitir warning quando xsd_path ausente
- `frontend/src/pages/AnalyzingPage.vue` — exibir banner de warnings
- Testes unitários dos três pontos acima

**OUT:**
- Não alterar outros stages (stage1, stage2, stage5) — nesta story
- Não criar novo endpoint — usar canal SSE existente
- Não bloquear pipeline — warnings são informativos, não fatais

## Dev Notes

**Padrão de escrita de warning (backend):**
```python
context.setdefault("_pipeline_warnings", [])
context["_pipeline_warnings"].append({
    "code": "spacy_unavailable",      # identificador machine-readable
    "severity": "info",               # info | warning | error
    "message": "NER layer desabilitado — modelo spaCy não encontrado. Análise usa regex-only.",
    "stage": 3,
})
```

**Padrão de leitura no orquestrador (pipeline_orchestrator_v2.py):**
```python
# Após loop de stages, antes de montar completion_event:
pipeline_warnings = context.get("_pipeline_warnings", [])

completion_event = make_sub_progress_event(
    ...
    summary={
        "layouts_detected": len(real_clusters),
        "page_count": total_pages,
        "api_cost": ...,
        "warnings": pipeline_warnings,   # ← adicionar
    },
)
```

**Severidades:**
- `info` — degradação menor, resultado provavelmente correto (ex: spaCy ausente)
- `warning` — degradação significativa, resultado pode ser incompleto (ex: XSD não encontrado)
- `error` — apenas para referência futura (não usar nesta story)

## Tasks / Subtasks

- [ ] **Backend — infraestrutura de warnings**
  - [ ] Adicionar helper `_add_pipeline_warning(context, code, severity, message, stage)` em `pipeline_orchestrator_v2.py`
  - [ ] Agregar `context["_pipeline_warnings"]` no `completion_event.summary`

- [ ] **Stage 3 — spaCy warning**
  - [ ] Em `_get_nlp()`: ao entrar no bloco de falha, chamar `_add_pipeline_warning()` com `code="spacy_unavailable"`
  - [ ] Nota: `emit_progress` não está disponível em `_get_nlp()` — gravar no context diretamente

- [ ] **Stage 4 — xsd_path warning**
  - [ ] Em `_step_4_1_xsd_parsing()`: quando `not xsd_path`, chamar `_add_pipeline_warning()` com `code="xsd_not_found"`

- [ ] **Frontend — banner AnalyzingPage**
  - [ ] Extrair `warnings` do event `pipeline_completed`
  - [ ] Componente de banner com ícone por severity e botão fechar
  - [ ] Estado reativo: `pipelineWarnings: ref([])`

- [ ] **Testes**
  - [ ] `test_pipeline_orchestrator_v2.py`: warnings propagados no completion_event
  - [ ] `test_stage3_structural_analysis.py`: warning `spacy_unavailable` no context
  - [ ] `test_stage4_field_mapping.py`: warning `xsd_not_found` no context

## Testing

```bash
# Backend
cd backend && python -m pytest tests/test_pipeline_orchestrator_v2.py tests/test_stage3_structural_analysis.py tests/test_stage4_field_mapping.py -v

# Frontend
cd frontend && npx vitest run
```

**Teste manual:**
1. Upload de PDF **sem** spaCy instalado → banner "NER layer desabilitado" aparece após análise
2. Upload de PDF **sem** XSD → banner "XSD não encontrado" aparece após análise
3. Upload com ambos disponíveis → sem banner

## Dev Agent Record
### File List
- `backend/services/pipeline_orchestrator_v2.py`
- `backend/services/stages/stage3_structural_analysis.py`
- `backend/services/stages/stage4_field_mapping.py`
- `frontend/src/pages/AnalyzingPage.vue`
- `backend/tests/test_pipeline_orchestrator_v2.py`
- `backend/tests/test_stage3_structural_analysis.py`
- `backend/tests/test_stage4_field_mapping.py`

### Change Log
| Data | Agente | Ação |
|---|---|---|
| 2026-03-31 | @qa (Quinn) | Story criada a partir de achado sistêmico em rca-2026-03-31-spacy-xsd-warnings |

## QA Results
<!-- @qa preenche durante review -->
