# RCA Investigation — Guia Completo

> Root Cause Analysis & Exploratory Investigation
> Versao: 3.0

## Filosofia

**Cada bug eh uma oportunidade de melhoria.** Nunca aplicar band-aid. Todo problema eh investigado ate a origem. A investigacao sempre produz mais do que entrou: alem do fix, documenta achados colaterais, cria testes e alimenta um registro de anti-patterns que previne bugs futuros.

Baseado em praticas de mercado:
- **5 Whys** (Toyota) — perguntar "por que?" ate chegar na raiz
- **Bug Clustering** (Microsoft SDL) — um bug indica um padrao de bugs relacionados
- **Kaizen** (Lean) — melhoria continua a partir de cada defeito
- **Blameless Postmortem** (Google SRE) — investigacao profunda sem culpa

---

## Artefatos

| # | Artefato | Caminho | Source of Truth Para |
|---|----------|---------|---------------------|
| 1 | Skill | `.claude/commands/investigate.md` | Metodologia (portavel, qualquer LLM) |
| 2 | Rule | `.claude/rules/rca-principle.md` | Trigger always-on (~5 linhas) |
| 3 | Task | `.aios-core/development/tasks/rca-investigation.md` | Wrapper AIOS (metadata, escalacoes) |
| 4 | Task Audit | `.aios-core/development/tasks/audit-patterns.md` | Busca proativa de anti-patterns |
| 5 | Workflow | `.aios-core/development/workflows/rca-investigation.yaml` | Pipeline operacional (sequencia de steps) |
| 6 | Anti-patterns | `docs/qa/known-anti-patterns.md` | Registry que cresce com cada RCA |
| 7 | Este guia | `docs/guides/rca-investigation-guide.md` | Documentacao e portabilidade |

**Principio de nao-duplicacao:** O skill contem a metodologia. A task referencia o skill e adiciona apenas metadata AIOS. O workflow define a sequencia operacional com delegacao multi-agente. Nenhum conteudo metodologico eh duplicado entre artefatos.

---

## Modelo Multi-Agente v3.0

Cada agente executa sua especialidade. Transicoes entre agentes geram handoff artifacts em `.aios/handoffs/` que preservam contexto (max 500 tokens).

```
@qa (investiga) → @sm (stories) → @dev (implementa) → @qa (revisa) → @sm (backlog) → @devops (entrega)
```

### Mapeamento de Fases

O skill (portavel) usa 5 fases pedagogicas. O workflow (operacional) usa 6 fases com agentes dedicados:

| Skill (portavel) | Workflow (operacional) | Agente |
|-------------------|----------------------|--------|
| Fase 1: Triagem & Compreensao | Fase 1: Triagem & Root Cause | @qa |
| Fase 2: Root Cause (5 Whys) | Fase 1: Triagem & Root Cause | @qa |
| Fase 3: Exploracao Proativa | Fase 1: Triagem & Root Cause | @qa |
| — | Fase 2: Stories dos Bugs | @sm |
| Fase 4: Solucao (fix + testes) | Fase 3: Implementacao | @dev |
| Fase 5: Documentacao & Backlog | Fase 4: Documentacao & QA Gate | @qa |
| Fase 5: Documentacao & Backlog | Fase 5: Backlog | @sm |
| — | Fase 6: Entrega | @devops |

Diferenca principal: no skill, tudo eh executado por quem invocou. No workflow, cada fase eh delegada ao agente especializado com handoff entre transicoes.

---

## Documentacao de Bugs — Abordagem Hibrida

Bugs encontrados durante o RCA sao documentados como stories conforme um threshold de complexidade:

| Classificacao | Criterio | Acao | Quando a Story eh Criada |
|--------------|----------|------|--------------------------|
| **Trivial** | 1 arquivo, 1 linha (typo, guard) | Sem story. Documentar no relatorio. | — |
| **Minor** | Fix comportamental, 1-2 arquivos | Story retroativa status=Done | Fase 5 (apos fix e QA) |
| **Significativo** | >2 arquivos, muda comportamento observavel | Story ANTES do fix | Fase 2 (antes do fix) |

**Se multiplos bugs significativos** da mesma investigacao: 1 story umbrella com cada bug como AC eh aceitavel.

**Exemplo:** Uma investigacao encontra 3 bugs que tocam 6 arquivos e mudam comportamento observavel → classificacao SIGNIFICATIVO → 1 story umbrella com cada bug como AC, criada antes do fix.

**Nota:** Achados colaterais (problemas encontrados mas NAO fixados no RCA) sempre viram stories de backlog separadas na Fase 5, independente do threshold.

---

## Como Utilizar

### Cenario 1: Bug reportado — workflow automatico

```bash
@aios-master
*workflow rca-investigation
# Colar screenshot/log/descricao do erro
# Roda em YOLO: zero confirmacoes, delegacao multi-agente
```

**O que acontece automaticamente (6 fases):**

```
FASE 1 — Triagem & Root Cause (@qa)
  → Dedup Check — ja existe branch/PR?
  → Triagem — entender o erro, mapear fluxo de dados
  → Bug Clustering — agrupar se multiplos bugs
  → Root Cause (5 Whys) — rastrear ate a origem
  → Exploracao Proativa — buscar irmaos + classificar bugs
  → Escalacao @architect — se problema estrutural (condicional)

  Handoff: @qa → @sm (root cause, classificacao, achados)

FASE 2 — Stories dos Bugs (@sm)
  → Criar Branch fix/{slug} a partir de main
  → Criar Stories para bugs significativos (antes do fix)
  → Anotar bugs minor para story retroativa

  Handoff: @sm → @dev (branch, stories, root cause, evidencia)

FASE 3 — Implementacao (@dev)
  → Fix na Origem + Guards + Testes (tudo junto)
  → Suite completa passando, zero regressao

  Handoff: @dev → @qa (fixes, testes, notas)

FASE 4 — Documentacao & QA Gate (@qa)
  → Relatorio de investigacao completo
  → Registrar Anti-Pattern
  → Verificar Testes (accountability)
  → QA Gate — code review dos fixes
    → PASS: continuar | REJECT: volta para @dev

  Handoff: @qa → @sm (verdict, backlog items)

FASE 5 — Backlog (@sm, condicional)
  → Stories Retroativas para bugs minor (status=Done)
  → Stories de Backlog para achados colaterais
  → Handoff SDC (artifact em .aios/handoffs/)

  Handoff: @sm → @devops (branch, verdict, context)

FASE 6 — Entrega (@devops)
  → Quality Gates (lint, typecheck, test, build)
  → Push + PR para main
```

**Resultado:**
- Branch com fix + testes
- PR para main
- Relatorio em `docs/qa/investigations/`
- Anti-pattern registrado
- Stories de bugs (conforme threshold)
- Stories de backlog + handoff artifact para SDC
- Proxima ativacao de @sm/@po sugere continuar o SDC

### Cenario 2: Investigacao manual

```bash
/investigate
# Colar screenshot/log/descricao do erro
# Voce pilota, Claude segue a metodologia
```

Util quando quer controlar cada passo ou esta em outro projeto/LLM.

### Cenario 3: Prevencao proativa

```bash
@qa
*audit-patterns              # codebase inteiro
*audit-patterns backend/     # escopo especifico
```

Le `docs/qa/known-anti-patterns.md`, grep cada padrao no codebase, reporta codigo vulneravel ANTES de crashar.

**Quando rodar:**
- Antes de releases
- Depois de adicionar novos anti-patterns
- Periodicamente (a cada sprint)
- Ao entrar em area pouco conhecida do codebase

---

## Configuracao Padrao

| Setting | Valor | Onde muda |
|---------|-------|-----------|
| Modo de execucao | YOLO (multi-agente, zero paradas) | `rca-investigation.yaml` → execution_modes |
| Background | Sim | `rca-investigation.yaml` → metadata.run_in_background |
| Elicit | Nao (`false`) | `rca-investigation.yaml` → metadata.elicit |
| Delegacao | Multi-agente com handoffs | `rca-investigation.yaml` → sequence (agent por step) |
| Branch naming | `fix/{slug}` | `rca-investigation.yaml` → step create_branch |
| Push | Sempre via PR, nunca direto na main | `rca-investigation.yaml` → step push_and_pr (@devops) |
| Testes | Obrigatorios para cada fix | `rca-investigation.yaml` → step implement_and_test |
| Handoff SDC | Gera artifact em `.aios/handoffs/` | `rca-investigation.yaml` → step create_backlog_stories |

---

## Ciclo Virtuoso

```
REATIVO                              PROATIVO
   │                                    │
   ▼                                    ▼
Bug acontece                    *audit-patterns
   │                                    │
   ▼                                    ▼
*workflow rca-investigation     Encontra codigo vulneravel
   │                                    │
   ▼                                    ▼
Fix + Testes (multi-agente)     Stories preventivas
   │                                    │
   ▼                                    ▼
Registra anti-pattern ──────► known-anti-patterns.md
   │                                    ▲
   ▼                                    │
Handoff SDC ──► Stories          ◄──────┘
               entram no backlog
```

---

## Licoes do v2.0 (primeiro uso real)

O primeiro RCA real expôs 9 gaps entre o design e a execucao. Todos corrigidos no v3.0:

| # | Gap | O que aconteceu | Fix v3.0 |
|---|-----|----------------|----------|
| 1 | Fases desalinhadas | Task tinha 5 fases, workflow tinha 5 com nomes diferentes | 6 fases alinhadas com agentes especializados |
| 2 | Single-agent ficticio | 1 agente executou tudo apesar do design multi-agent | Multi-agent real com handoffs documentados |
| 3 | Testes nao criados | Step `create_tests` existia mas foi pulado | Merge com implement em 1 step + verify_tests |
| 4 | QA Gate nunca executado | Gate de 7 pontos nunca rodou | QA gate real por @qa na Fase 4 |
| 5 | Dedup check pulado | Fase 0 separada era facil de ignorar | Movido para dentro da Fase 1 |
| 6 | Conteudo duplicado | Task e skill tinham a mesma metodologia copiada | Task vira wrapper fino que referencia skill |
| 7 | Stories sem handoff | Stories criadas ficaram em Draft sem proximo passo | Handoff artifact para SDC |
| 8 | YOLO pedia confirmacao | `elicit: true` contradizia YOLO; usuario falou "seguir" varias vezes | `elicit: false` + `yolo_behavior` por step |
| 9 | Bugs nao documentados como stories | Bugs fixados nao geravam stories no SDC | Threshold hibrido (trivial/minor/significativo) |

---

## Instalacao

> Copie esta secao inteira e cole na LLM do projeto destino com o comando:
> "Instale o sistema RCA Investigation neste projeto seguindo as instrucoes abaixo."

### Nivel 1: Qualquer LLM (minimo — 1 arquivo)

**Quando usar:** Projetos sem Claude Code, ou quando quer usar com ChatGPT/Gemini/Codex/Cursor.

| Destino | Instrucao para a LLM |
|---------|---------------------|
| Claude Code | "Crie o arquivo `.claude/commands/investigate.md` com o conteudo abaixo" |
| Cursor | "Crie o arquivo `.cursor/rules/investigate.md` com o conteudo abaixo" |
| Codex CLI | "Adicione a secao abaixo no `AGENTS.md`" |
| ChatGPT/Gemini | Cole como Custom Instructions ou system prompt |

**Arquivo a criar:** Copiar `.claude/commands/investigate.md` do projeto fonte.

---

### Nivel 2: Claude Code (recomendado — 2 arquivos)

**Quando usar:** Projetos com Claude Code, sem AIOS.

1. `.claude/commands/investigate.md` — Skill (copiar do projeto fonte)
2. `.claude/rules/rca-principle.md` — Rule:

~~~markdown
---
paths:
  - "**/*"
---

# Root Cause Analysis — Principio Constitucional

Quando um bug ou erro for reportado, SEMPRE sugira `/investigate` antes de aplicar qualquer fix. Nunca aplique guards, workarounds ou band-aids como solucao principal sem antes investigar a origem do problema. Cada bug eh uma oportunidade de melhoria — a investigacao deve produzir mais do que entrou.
~~~

**Resultado:** `/investigate` disponivel como comando. Rule lembra de usar quando bug aparece.

---

### Nivel 3: Claude Code + AIOS (completo — 7 arquivos)

**Quando usar:** Projetos com AIOS framework.

Arquivos a criar:
1. `.claude/commands/investigate.md` — Skill (source of truth da metodologia)
2. `.claude/rules/rca-principle.md` — Rule always-on
3. `.aios-core/development/tasks/rca-investigation.md` — Task wrapper AIOS (metadata + delegacao multi-agente, SEM metodologia duplicada)
4. `.aios-core/development/tasks/audit-patterns.md` — Task de auditoria proativa
5. `.aios-core/development/workflows/rca-investigation.yaml` — Workflow v3.0 (6 fases, multi-agente com handoffs)
6. `docs/qa/known-anti-patterns.md` — Registry vazio (template abaixo)
7. `docs/guides/rca-investigation-guide.md` — Este guia

**Template para `known-anti-patterns.md` vazio:**

~~~markdown
# Known Anti-Patterns Registry

> Cada RCA adiciona o padrao problematico encontrado a esta lista.
> Use `*audit-patterns` para buscar esses padroes no codebase.

## Como Usar

1. Depois de cada investigacao RCA, registre o padrao aqui
2. Periodicamente (ou antes de releases), rode `*audit-patterns`
3. Cada achado vira story ANTES de causar crash

---

## Padroes Registrados

(Nenhum padrao registrado ainda. O primeiro sera adicionado automaticamente pela proxima RCA.)
~~~

**Apos criar os arquivos**, registrar nos agentes:
- Adicionar `rca-investigation.md` e `audit-patterns.md` como tasks no @qa e @aios-master
- Adicionar `rca-investigation.yaml` como workflow no @aios-master

### Verificacao pos-instalacao

| Nivel | Teste | Esperado |
|-------|-------|----------|
| 1 | Pedir "investigue este bug: TypeError null" | LLM segue as 5 fases |
| 2 | Digitar `/investigate` no Claude Code | Comando reconhecido |
| 2 | Reportar um bug qualquer | Claude sugere usar `/investigate` |
| 3 | `*workflow rca-investigation` | Workflow inicia com delegacao multi-agente |
| 3 | `*audit-patterns` | Le registry e busca no codebase |

### Portabilidade do Anti-Patterns Registry

O `known-anti-patterns.md` eh **especifico por projeto**. Comece vazio em projetos novos.

Excecao: padroes UNIVERSAIS (como `.get()` sem isinstance guard) podem ser copiados entre projetos da mesma stack.

---

## Como Evoluir

### Feito no v3.0 (era "melhorias futuras" no v2.0)

| Melhoria | Status |
|----------|--------|
| Multi-agent real com handoffs documentados | Feito v3.0 |
| Testes obrigatorios (merge com implementacao) | Feito v3.0 |
| YOLO verdadeiro sem confirmacoes | Feito v3.0 |
| Handoff automatico para SDC | Feito v3.0 |
| Eliminacao de duplicacao skill/task | Feito v3.0 |
| Bug stories com threshold hibrido | Feito v3.0 |
| QA gate real por @qa | Feito v3.0 |
| Engine mode yolo_continuous (Story 16.1) | Feito v3.0 |

### Melhorias de curto prazo

| Melhoria | Esforco | Impacto |
|----------|---------|---------|
| Adicionar anti-patterns da stack (Python, Vue, etc.) | Baixo | Medio |
| Integrar `*audit-patterns` no CI/CD | Medio | Alto |
| Metricas RCA (area, tipo, frequencia) | Baixo | Medio |

### Melhorias de medio prazo

| Melhoria | Esforco | Impacto |
|----------|---------|---------|
| Anti-patterns com auto-fix | Medio | Alto |
| Post-merge health check | Medio | Medio |
| Dashboard de saude do codebase | Alto | Alto |

### Melhorias de longo prazo

| Melhoria | Esforco | Impacto |
|----------|---------|---------|
| Anti-patterns como linter rules (custom ESLint/Ruff) | Alto | Muito alto |
| Cross-project anti-patterns (registry compartilhado) | Medio | Alto |

---

## Referencia Rapida

```bash
# Bug reportado → automatico (YOLO, multi-agente)
@aios-master → *workflow rca-investigation

# Bug reportado → manual
/investigate

# Prevencao proativa
@qa → *audit-patterns

# Adicionar anti-pattern manualmente
Editar docs/qa/known-anti-patterns.md
```
