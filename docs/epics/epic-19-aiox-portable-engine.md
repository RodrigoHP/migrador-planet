# Epic 19 — AIOX Portable Engine: Engine como pacote reutilizável

## Epic Goal

Transformar o workflow engine yolo_continuous de um componente acoplado ao migrador-planet em um **pacote portável** que qualquer projeto pode usar com `aiox init`, sem copiar manualmente a estrutura `.aios-core/`.

## Epic Description

### Existing System Context

- **Funcionalidade atual:** Engine v5.0 (Epic 18) com 20+ features (timeout, retry adaptativo, confidence scoring, intelligence, parallel execution, post-mortem)
- **Problema:** Engine vive dentro de `migrador-planet` como pseudocode (2596 linhas em `run-workflow-engine.md`) + 38 módulos JS em `.aios-core/core/orchestration/`. Para usar em outro projeto, precisa copiar tudo.
- **AIOS → AIOX:** Framework renomeado para refletir a fase multi-projeto

### Enhancement Details

- **O que está sendo feito:** Extrair o engine core, criar bootstrapper, auto-detectar contexto do projeto, genericizar workflows
- **Diagnóstico:** 100% do investimento em engine (Epics 16, 18) está locked neste repo. Workflows assumem tech stack específico. project-context.yaml é manual.
- **Estratégia:** 3 waves — Extração → Bootstrapper → Auto-detection
- **Success criteria:** Novo projeto funcional com yolo_continuous em <5 minutos via `aiox init`

### Architectural Decision

**ADR-019: AIOX Portable Engine** (2026-03-30)
- Engine core extraído para `.aiox-engine/` (ou npm package futuro)
- `aiox init` cria estrutura mínima (.aios/, workflows, config)
- Project context auto-detectado de package.json, requirements.txt, pyproject.toml, etc
- Workflows genéricos sem tech-stack hardcoded
- Alternativas descartadas: monorepo (over-engineering), git submodule (friction alto)

---

## Escopo por Wave

### Wave 1 — Extração & Separação (~3-4 dias)
**Objetivo:** Engine core separado do projeto, config externalizada.

| Story | Item | Impacto | Executor | Estimativa |
|-------|------|---------|----------|------------|
| 19.1 | **Engine Core Extraction** — separar pseudocode engine de conteúdo project-specific em run-workflow-engine.md | Engine reutilizável sem lixo de projeto | @dev | L |
| 19.2 | **Config Externalization** — mover hardcoded values (timeouts, token limits, cost limits, retry counts) para `.aios/engine-config.yaml` | Cada projeto configura seus limites | @dev | M |
| 19.3 | **Generic Workflow Templates** — criar versões genéricas de SDC e RCA sem tech-stack assumptions | Workflows funcionam em qualquer projeto | @dev | M |

### Wave 2 — Bootstrapper (~2-3 dias)
**Objetivo:** Novo projeto funcional com um comando.

| Story | Item | Impacto | Executor | Estimativa |
|-------|------|---------|----------|------------|
| 19.4 | **`aiox init` Bootstrapper** — comando/task que cria estrutura mínima (.aios/, config, workflows, agents essenciais) | Setup de 30min vira 2min | @dev | L |
| 19.5 | **Project Context Auto-Detect** — detectar tech stack de package.json, requirements.txt, tsconfig, Dockerfile, etc | Elimina criação manual de project-context.yaml | @dev | M |
| 19.6 | **Minimal Agent Set** — definir quais agentes são essenciais (dev, qa, devops) vs opcionais (analyst, ux, data-engineer) | Projeto novo não precisa de 12 agentes | @dev | S |

### Wave 3 — Documentação & Validação (~1-2 dias)
**Objetivo:** Qualquer dev consegue usar sem ajuda.

| Story | Item | Impacto | Executor | Estimativa |
|-------|------|---------|----------|------------|
| 19.7 | **AIOX Getting Started Guide** — guia passo-a-passo: init, primeiro workflow, primeiro yolo run | Adoção sem fricção | @dev | M |
| 19.8 | **Engine Integration Tests** — test harness que valida engine em projeto clean (bootstrap → SDC → complete) | Garantia que portabilidade funciona | @dev | L |

---

## Dependências

### Internas
- 19.1 e 19.2 são independentes (podem ser paralelas)
- 19.3 depende de 19.1 (precisa do engine extraído)
- 19.4 depende de 19.1, 19.2, 19.3 (bootstrapper usa tudo)
- 19.5 depende de 19.4 (auto-detect é feature do bootstrapper)
- 19.6 pode ser paralela com 19.4-19.5
- 19.7 depende de 19.4 (documenta o bootstrapper)
- 19.8 depende de 19.4 (testa o bootstrapper)

### Externas
- Epic 18 (engine v5.0) — **DONE** — base do engine
- Renaming AIOS → AIOX — em andamento

---

## Riscos e Mitigação

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| Engine pseudocode tem referências implícitas ao migrador-planet | ALTO | Story 19.1 audita todas as referências |
| Auto-detect falha em projetos com stack não-convencional | MEDIO | Fallback para criação manual (como hoje) |
| 38 módulos JS têm dependências circulares | MEDIO | Story 19.1 mapeia dependências antes de extrair |
| Workflows genéricos perdem especificidade útil | BAIXO | Manter templates específicos como "presets" opcionais |

---

## Definition of Done

- [x] Engine core separado de conteúdo project-specific
- [x] Config externalizável em `.aios/engine-config.yaml`
- [x] `aiox init` funcional em projeto vazio
- [x] Project context auto-detectado para Node.js, Python, e projetos mistos
- [x] SDC workflow genérico funciona sem modificação em projeto novo
- [x] Guia de getting started testado por alguém que nunca usou AIOX
- [x] Integration test passa: init → SDC → yolo_continuous → complete
- [x] Zero regressão no migrador-planet

---

## Métricas de Sucesso

| Métrica | Baseline (hoje) | Target |
|---------|-----------------|--------|
| Tempo para setup em projeto novo | ~30-60min (copy-paste manual) | <5min (aiox init) |
| Arquivos necessários para copiar | ~100+ (.aios-core inteiro) | 0 (gerados pelo bootstrapper) |
| Configuração manual necessária | Alto (editar workflows, agents, config) | Mínimo (auto-detect + defaults) |
