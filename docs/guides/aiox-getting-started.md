# AIOX Getting Started Guide

> Bootstrap AIOX framework em qualquer projeto e execute seu primeiro workflow em menos de 30 minutos.

---

## Pre-requisitos

- [Claude Code](https://claude.ai/code) instalado e configurado
- Um projeto existente (com ou sem git)
- Terminal com acesso ao diretorio do projeto

---

## 1. Quick Start (5 min)

### 1.1 Inicializar AIOX

No diretorio raiz do seu projeto:

```bash
# Ativar o agente master
@aios-master

# Bootstrap com tier core (default — 3 agents: dev, qa, devops)
*aiox-init
```

Para projetos com processo estruturado:

```bash
*aiox-init --tier extended    # +architect, pm, sm, po (7 agents)
```

Para projetos enterprise:

```bash
*aiox-init --tier full        # Todos os 10 agents
```

### 1.2 Verificar estrutura

Apos o init, seu projeto tera:

```
projeto/
├── .aios/
│   ├── engine-config.yaml          # Configuracao do engine
│   ├── project-context.yaml        # Tech stack auto-detectado
│   ├── agents.yaml                 # Manifest dos agents instalados
│   ├── handoffs/                   # Runtime (gitignored)
│   └── state/                      # Engine state persistence
├── .aios-core/
│   └── development/
│       ├── tasks/
│       │   └── run-workflow-engine.md   # Engine core
│       ├── workflows/
│       │   ├── story-development-cycle.yaml
│       │   └── rca-investigation.yaml
│       ├── agents/
│       │   ├── dev.md
│       │   ├── qa.md
│       │   └── devops.md            # (+ mais se extended/full)
│       └── templates/
│           └── subagent-step-prompt.md
└── .claude/
    ├── CLAUDE.md                    # Instrucoes do projeto
    └── rules/                       # Regras de operacao
```

### 1.3 Hello World — verificar que funciona

```bash
@aios-master
*status
```

Voce deve ver o agente ativo com a estrutura AIOX detectada.

---

## 2. Configuracao (10 min)

### 2.1 Revisar project-context.yaml

O `aiox init` auto-detecta seu tech stack. Revise e ajuste se necessario:

**Exemplo Node.js/TypeScript:**

```yaml
# .aios/project-context.yaml
project:
  name: "meu-app-react"
  type: "fullstack"

  languages:
    primary: "typescript"
    secondary: ["python"]

  frontend:
    framework: "react"
    version: "18.x"
    test_runner: "vitest"
    build_tool: "vite"

  backend:
    framework: "express"
    language: "typescript"
    test_runner: "jest"

  database:
    type: "prisma"
    orm: "prisma"

  infrastructure:
    containerized: true
    ci_cd: "github-actions"
```

**Exemplo Python:**

```yaml
# .aios/project-context.yaml
project:
  name: "minha-api"
  type: "api"

  languages:
    primary: "python"
    secondary: []

  frontend: null

  backend:
    framework: "fastapi"
    language: "python"
    test_runner: "pytest"

  database:
    type: "postgres"
    orm: "sqlalchemy"

  infrastructure:
    containerized: true
    ci_cd: "github-actions"
```

### 2.2 Ajustar engine-config.yaml (opcional)

Os defaults funcionam para a maioria dos projetos. Ajuste se necessario:

```yaml
# .aios/engine-config.yaml — valores que voce pode querer mudar

cost:
  max_per_workflow_usd: 10.0    # Aumente para workflows complexos
  warn_at_percent: 80

timeouts:
  default_step_seconds: 300     # 5 min por step (aumente para testes lentos)

execution:
  max_loops_per_target: 4       # Retries por step
```

### 2.3 Editar CLAUDE.md

Adicione uma descricao do seu projeto:

```markdown
# Meu Projeto

Descricao breve do que o projeto faz.

## Tech Stack
- Frontend: React 18 + TypeScript + Vite
- Backend: Express + Prisma
- Database: PostgreSQL

## Convencoes
- Commits: Conventional Commits
- Branches: feature/{epic}-{descricao}
```

---

## 3. Primeiro Workflow (10 min)

### 3.1 Criar uma story

Com tier extended (que inclui @sm e @po):

```bash
@sm
*draft
# Siga o fluxo interativo para criar sua primeira story
```

Com tier core (sem @sm), crie manualmente:

```bash
# Criar docs/stories/1.1.minha-feature.story.md
```

Exemplo de story minima:

```markdown
---
id: 1.1
title: "Adicionar endpoint de health check"
type: feature
status: Ready
executor: "@dev"
quality_gate: "@qa"
---

# Story 1.1 — Health Check Endpoint

## Story
**Como** operador do sistema,
**Quero** um endpoint /health que retorne o status da aplicacao,
**Para** que o load balancer possa verificar a disponibilidade.

## Acceptance Criteria
- [ ] AC1: GET /health retorna 200 com { status: "ok" }
- [ ] AC2: Endpoint responde em < 100ms
- [ ] AC3: Teste unitario cobrindo o endpoint

## File List
- [ ] src/routes/health.ts
- [ ] tests/health.test.ts
```

### 3.2 Executar SDC (Story Development Cycle)

```bash
@aios-master
*workflow story-development-cycle
```

O engine executa as 7 fases automaticamente:
1. **Create** — Story ja criada
2. **Validate** — Checklist de qualidade
3. **Implement** — @dev implementa o codigo
4. **Self-Heal** — CodeRabbit review (se habilitado)
5. **QA Gate** — @qa revisa qualidade
6. **Push & PR** — @devops cria PR
7. **Checkpoint** — Decisao go/no-go

---

## 4. Primeiro YOLO Run (5 min)

O modo `yolo_continuous` executa o ciclo completo sem parar para confirmacoes:

```bash
@aios-master
*workflow story-development-cycle yolo_continuous
```

O engine:
- Executa todos os steps sequencialmente
- Toma decisoes automaticamente (GO em checkpoints)
- Gera state file em `.aios/{instance}-engine-state.yaml`
- Para apenas em caso de erro critico

### Monitorar execucao

Durante o run, o state file e atualizado em tempo real. Apos completar:

```bash
*workflow-analytics    # Ver metricas agregadas de todos os runs
```

---

## 5. Workflows Disponiveis

| Workflow | Comando | Descricao |
|----------|---------|-----------|
| Story Development Cycle | `*workflow story-development-cycle` | Ciclo completo de desenvolvimento |
| RCA Investigation | `*workflow rca-investigation` | Root Cause Analysis de bugs/incidentes |

---

## 6. Tiers de Agents

| Tier | Agents | Quando Usar |
|------|--------|-------------|
| **core** | @dev, @qa, @devops | Solo dev, MVPs, projetos simples |
| **extended** | +@architect, @pm, @sm, @po | Times medios, processo estruturado |
| **full** | +@analyst, @data-engineer, @ux | Times grandes, enterprise |

### Upgrade de tier

```bash
*aiox-init --tier extended    # Adiciona agents faltantes, preserva config existente
```

---

## 7. Troubleshooting

### Problema: "Workflow not found"

**Causa:** Workflow YAML nao existe no path esperado.

**Solucao:**
```bash
ls .aios-core/development/workflows/
# Verificar que story-development-cycle.yaml existe
```

### Problema: "No project context available"

**Causa:** `project-context.yaml` nao foi criado ou nao existe.

**Solucao:**
```bash
# Re-executar auto-deteccao
*detect-context
# Ou criar manualmente em .aios/project-context.yaml
```

### Problema: Engine para com "max_loops_per_target reached"

**Causa:** Um step falhou mais vezes que o limite de retries (default: 4).

**Solucao:**
```bash
# Ver o erro no state file
cat .aios/*-engine-state.yaml
# Aumentar limite se necessario:
# .aios/engine-config.yaml → execution.max_loops_per_target: 6
```

### Problema: "Budget limit exceeded"

**Causa:** Workflow excedeu o custo maximo configurado (default: $10).

**Solucao:**
```bash
# Aumentar em .aios/engine-config.yaml:
# cost.max_per_workflow_usd: 20.0
```

### Problema: Agent nao reconhecido em tier core

**Causa:** Tentando usar @architect, @pm, etc. sem tier extended.

**Solucao:**
```bash
*aiox-init --tier extended    # Instalar agents adicionais
```

---

## Proximos Passos

1. **Explorar comandos:** `@aios-master *help` para ver todos os comandos
2. **Customizar workflows:** Editar YAML em `.aios-core/development/workflows/`
3. **Adicionar agents:** `*aiox-init --tier extended` quando precisar de mais processo
4. **Ver metricas:** `*workflow-analytics` apos alguns runs

---

> Guia criado como parte do Epic 19 — AIOX Portable Engine.
