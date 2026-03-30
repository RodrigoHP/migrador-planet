# Epic 19 — AIOX Portable Engine: Engine agnostico para qualquer projeto

## Epic Goal

Tornar o `.aios-core/` e `.claude/` agnosticos — copiar para qualquer projeto e funcionar sem limpeza manual.

## Epic Description

### Existing System Context

- **Funcionalidade atual:** Engine v5.0 (Epic 18) com 20+ features (timeout, retry adaptativo, confidence scoring, intelligence, parallel execution, post-mortem)
- **Problema:** Engine tinha referencias ao migrador-planet (Vue, FastAPI, Supabase) hardcoded. Config values hardcoded no pseudocode.
- **AIOS → AIOX:** Framework renomeado para refletir a fase multi-projeto

### O que foi feito

1. **Auditoria completa** das ~2596 linhas de `run-workflow-engine.md` — removidas todas as referencias project-specific
2. **Config externalizada** — todos os hardcoded values (timeouts, token limits, retry counts, cost limits) movidos para `.aios/engine-config.yaml` com `DEFAULT_ENGINE_CONFIG` como fallback
3. **Workflows confirmados genericos** — SDC e RCA nao tinham referencias a tech stack

### Como usar em outro projeto

```
1. Copiar .aios-core/ para o projeto novo
2. Copiar .claude/ para o projeto novo
3. (Opcional) Criar .aios/engine-config.yaml para customizar defaults
4. (Opcional) Criar .aios/project-context.yaml com tech stack do projeto
5. Ativar agente e rodar workflow
```

O engine cria `.aios/` e state files conforme necessario. Config e project-context sao opcionais — o engine tem fallbacks para tudo.

---

## Stories (3/3 Done)

| Story | Item | Status |
|-------|------|--------|
| 19.1 | **Engine Core Extraction** — auditoria e remoção de refs ao migrador-planet | Done |
| 19.2 | **Config Externalization** — `load_engine_config()` + `DEFAULT_ENGINE_CONFIG` + `.aios/engine-config.yaml` | Done |
| 19.3 | **Generic Workflow Templates** — SDC e RCA confirmados genéricos, sem tech-stack refs | Done |

---

## Definition of Done

- [x] Engine core sem referencias ao migrador-planet
- [x] Config externalizavel em `.aios/engine-config.yaml` com defaults sensatos
- [x] Workflows genericos funcionam sem modificacao em projeto novo
- [x] Zero regressao no migrador-planet

---

## Métricas de Sucesso

| Métrica | Baseline (antes) | Resultado |
|---------|-----------------|-----------|
| Refs project-specific no engine | ~12 hardcoded | 0 |
| Config hardcoded no pseudocode | ~15 constantes | 0 (tudo em config) |
| Passos para usar em projeto novo | Copiar + limpar refs | Copiar e pronto |
