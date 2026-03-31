# Epic 25 — RCA v8.0: Multi-Model Investigation Pipeline

**Status:** Done
**Branch:** feature/epic-25-rca-v8-multi-model
**Data:** 2026-03-31
**Origem:** Analise de custo/qualidade do RCA v7.0 — todo o pipeline roda em Opus quando fases mecanicas poderiam usar modelos mais baratos
**Escopo:** Framework generico (.aios-core + .claude/commands/investigate.md) — nenhuma alteracao especifica de projeto

---

## Problema Central

O RCA v7.0 roda **100% em Opus** como conversa unica. Contexto acumula ate ~370K tokens. Cada fase herda todo o historico anterior, mesmo quando nao precisa. Resultado:

- **Custo:** ~$2.93 por investigacao (todo token processado pelo modelo mais caro)
- **Context bloat:** Fase 9 processa 55K de contexto onde 40K sao lixo das fases anteriores
- **Velocidade:** Opus eh o modelo mais lento, usado para tarefas mecanicas como ler git log
- **Role violation:** @qa investiga E implementa fixes — nao passa pelo SDC

### Analise de Custo-Beneficio

| Fase | Tarefa | Modelo ideal | Motivo |
|------|--------|-------------|--------|
| 0 | Classificar + dedup | Sonnet | Scoring estruturado, nao precisa raciocinio profundo |
| 1 | Ler arquivos, git log | Haiku | Leitura mecanica, zero raciocinio |
| 2 | Pattern match + scoring | Sonnet | Calcular scores com formula definida |
| 3 | Analise causal | Sonnet | Raciocinio medio, causal graph |
| 4 | Challenge de hipoteses | **Opus** | Raciocinio profundo, contrafactual |
| 5 | Barrier analysis | Sonnet | Analise estruturada por checklist |
| 6 | Evidence grading | **Opus** | Julgamento critico, classificar E1-E4 |
| 7 | Fix implementation | Via SDC | **Delegar para SDC** (nao fazer inline) |
| 8 | Relatorio | **Opus** | Sintese narrativa — deliverable principal |
| 9 | Meta-learning | Sonnet | Trends e data processing |

### Economia Projetada

```
Antes (v7.0):  ~$2.93/investigacao (tudo Opus, contexto acumulado)
Depois (v8.0): ~$1.40/investigacao (multi-model, contexto isolado)
Economia:      ~52% reducao de custo
Bonus:         Fix passa pelo SDC (quality gate real)
```

---

## Epic Goal

Transformar o investigate.md de guia monolitico para **orquestrador multi-model**: cada fase roda como subagent isolado com o modelo certo, contexto limpo, e input/output bem definido. Fase 7 (fix) delega para o SDC em vez de implementar inline. Zero mudanca na metodologia — mesmas fases, mesma logica, mesmo relatorio.

---

## Arquitetura

### Antes (v7.0): Monolito
```
/investigate → Opus faz tudo inline → contexto acumula 370K → relatorio
```

### Depois (v8.0): Orquestrador + Subagents
```
/investigate → Opus (orquestrador) le investigate.md
  → Agent(model: sonnet, prompt: briefing_fase_0)  → resultado_0
  → Agent(model: haiku,  prompt: briefing_fase_1)  → resultado_1
  → Agent(model: sonnet, prompt: briefing_fase_2)  → resultado_2
  → Agent(model: sonnet, prompt: briefing_fase_3)  → resultado_3
  → Agent(model: opus,   prompt: briefing_fase_4)  → resultado_4
  → Agent(model: sonnet, prompt: briefing_fase_5)  → resultado_5
  → Agent(model: opus,   prompt: briefing_fase_6)  → resultado_6
  → Gera story de fix → dispara SDC               → resultado_7
  → Agent(model: opus,   prompt: briefing_fase_8)  → resultado_8
  → Agent(model: sonnet, prompt: briefing_fase_9)  → resultado_9
  → Consolida relatorio final
```

### Beneficio Oculto: Context Isolation

Cada subagent recebe **so o que precisa**:
- Fase 4 (Challenge): hipoteses + evidencias = ~8K tokens limpos
- Fase 8 (Relatorio): todos os resultados estruturados = ~15K tokens limpos
- Sem 300K de historico acumulado poluindo o raciocinio

---

## Arquivos Afetados

| Arquivo | Tipo | Mudanca |
|---------|------|---------|
| `.claude/commands/investigate.md` | Skill | Reescrever como orquestrador |
| `.aios-core/development/workflows/rca-investigation.yaml` | Workflow | Model routing + phase contracts |
| `.aios-core/development/tasks/rca-investigation.md` | Task | Version bump v8.0 |
| `.claude/rules/rca-principle.md` | Regra | Adicionar regras multi-model |

---

## Stories

### Story 25.1: Phase Contracts — Input/Output de Cada Fase

**Descricao:** Definir contrato formal de input/output para cada fase. Hoje o output de uma fase "flui" pelo contexto acumulado — o agente da Fase 5 "sabe" o que a Fase 1 fez porque esta tudo no historico. Com subagents isolados, cada fase precisa receber um briefing estruturado e devolver um resultado estruturado.

**Design:**
```yaml
phase_contracts:
  fase_0:
    input:
      - bug_report: string (descricao do bug, error message, stack trace)
      - screenshots: list[path] (se houver)
      - investigations_yaml: string (conteudo para dedup check)
    output:
      domain: Clear | Complicated | Complex | Chaotic
      severity: Critical | High | Medium | Low
      scope: list[string] (arquivos/modulos afetados)
      dedup_status: new | related | duplicate
      dedup_score: number (0-100)
      related_rcas: list[string] | null
      strategy: string (fases a executar)
      effectiveness_reviews: list[object] | null (reviews feitos inline)

  fase_1:
    input:
      - bug_report: string
      - classification: object (output da fase_0)
    output:
      suspects: list[{file, function, change, confidence}] (top 5)
      timeline: list[{date, event}]
      blast_radius: list[string] (modulos afetados)
      dependency_changes: list[string]
      raw_evidence: list[{type, content}] (git diffs, logs, etc)

  fase_2:
    input:
      - suspects: list (da fase_1)
      - bug_report: string
      - investigations_yaml: string
      - known_anti_patterns: string
      - sops_dir: list[string] (conteudo dos SOPs)
    output:
      matches: list[{rca_id, score, classification}]
      confidence_score: number (0-100)
      fast_track: {accepted: bool, sop_id: string | null}
      anti_pattern_matches: list[{ap_id, score}]

  fase_3:
    input:
      - suspects: list (da fase_1)
      - matches: list (da fase_2)
      - raw_evidence: list (da fase_1)
      - bug_report: string
    output:
      causal_graph: string (markdown)
      root_causes: list[{description, type, confidence, evidence}]
      contributing_factors: list[string]

  fase_4:
    input:
      - root_causes: list (da fase_3)
      - raw_evidence: list (da fase_1)
      - affected_files: list[string]
    output:
      challenge_results: list[{hypothesis, verdict, counter_evidence, confidence}]
      final_ranking: list[{hypothesis, confidence}]
      design_concerns: list[string] | null

  fase_5:
    input:
      - root_causes: list (da fase_3, pos-challenge)
      - affected_files: list[string]
    output:
      barriers: list[{layer, barrier, status, criticality, contrafactual, nature}]
      fix_this_first: list[{barrier, action, priority}]
      escalation_assessment: {criteria_met: number, details: list}
      test_gaps: list[{test, classification, cause, recommendation}]

  fase_6:
    input:
      - root_causes: list (pos-challenge)
      - raw_evidence: list (da fase_1)
      - barriers: list (da fase_5)
    output:
      evidence_summary: list[{claim, level, confidence, sources}]
      e1_confirmed: bool
      fix_requirements: object (para SDC bridge)

  # fase_7: NAO tem subagent — gera story e dispara SDC
  
  fase_8:
    input:
      - ALL previous outputs (resultado_0 a resultado_6 + resultado_7_sdc)
      - bug_report: string (original)
    output:
      report: string (relatorio completo markdown)
      investigation_record: object (para investigations.yaml)
      anti_patterns: list[object] | null
      sops: list[object] | null
      handoff: object | null
      backlog_stories: list[object] | null

  fase_9:
    input:
      - investigation_record: object (da fase_8)
      - investigations_yaml: string (knowledge base completa)
      - sops_dir: list (todos os SOPs)
    output:
      effectiveness_updates: list[object]
      sop_updates: list[object]
      trend_analysis: string | null
      tag_promotions: list[string] | null
```

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** CRITICAL

---

### Story 25.2: Model Routing Config — Tabela Configuravel

**Descricao:** Criar configuracao de model routing no workflow YAML. Deve ser configuravel para que projetos possam ajustar (ex: tudo Opus se custo nao importa, ou tudo Sonnet se budget apertado). Default otimizado para balance custo/qualidade.

**Design:**
```yaml
# Em rca-investigation.yaml
model_routing:
  default_orchestrator: opus
  phases:
    fase_0:  { model: sonnet, reason: "scoring estruturado" }
    fase_1:  { model: haiku,  reason: "leitura mecanica" }
    fase_2:  { model: sonnet, reason: "pattern matching" }
    fase_3:  { model: sonnet, reason: "analise causal" }
    fase_4:  { model: opus,   reason: "raciocinio profundo" }
    fase_5:  { model: sonnet, reason: "analise estruturada" }
    fase_6:  { model: opus,   reason: "julgamento critico" }
    fase_7:  { model: null,   reason: "SDC bridge — nao usa subagent" }
    fase_8:  { model: opus,   reason: "sintese narrativa" }
    fase_9:  { model: sonnet, reason: "data processing" }
  
  presets:
    economy:
      # Maximo economia, aceita risco em fases analiticas
      fase_0: haiku
      fase_3: haiku
      fase_5: haiku
      fase_8: sonnet
      fase_9: haiku
    
    balanced:
      # Default — balance custo/qualidade
      # (usa config acima)
    
    quality:
      # Tudo no modelo mais capaz
      fase_0: opus
      fase_1: sonnet  # leitura mecanica nao precisa opus
      fase_2: opus
      fase_3: opus
      fase_4: opus
      fase_5: opus
      fase_6: opus
      fase_8: opus
      fase_9: opus
    
    single:
      # Modo legado — tudo inline sem subagents (v7.0 behavior)
      all: inherit
```

- Preset selecionavel via argumento: `/investigate --preset economy "bug X"`
- Default: `balanced`
- `single`: fallback para comportamento v7.0 (zero subagents)

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** HIGH

---

### Story 25.3: Phase Prompts — 10 Briefings Autossuficientes

**Descricao:** Cada fase precisa de um prompt completo que o subagent recebe. Deve ser autossuficiente: o subagent nao tem contexto anterior, so o briefing. Deve incluir: contexto do bug, dados das fases anteriores, instrucoes especificas, formato de output esperado.

**Design:**
Para cada fase, criar template de briefing no investigate.md:

```markdown
### Fase {N} — Briefing Template

**System:** Voce eh o {Agent Name}. Sua tarefa eh {objetivo da fase}.

**Contexto do Bug:**
{bug_report}

**Dados de Fases Anteriores:**
{outputs estruturados das fases anteriores}

**Instrucoes:**
{instrucoes especificas da fase — COPIADAS do investigate.md atual}

**Output Esperado (YAML):**
```yaml
{schema do output conforme phase_contracts}
```

**IMPORTANTE:** Retorne APENAS o output no formato especificado. Nao inclua explicacoes extras.
```

10 briefing templates (Fases 0-6, 8-9 + Fase 7 eh SDC bridge, nao tem briefing).

Cada briefing deve:
- Ser autossuficiente (subagent entende tudo so com o briefing)
- Incluir instrucoes da metodologia v7.0 (nao simplificar)
- Definir formato de output preciso (YAML)
- Incluir exemplos quando necessario (worked examples do v7.0)

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** CRITICAL

---

### Story 25.4: Orchestrator Rewrite — investigate.md como Pipeline

**Descricao:** Reescrever investigate.md de "guia para agente unico" para "script de orquestracao multi-model". O orquestrador (Opus, conversa principal) le as instrucoes e spawna subagents por fase, coleta resultados, monta briefings, e consolida o relatorio final.

**Design:**
Estrutura do novo investigate.md:

```markdown
# /investigate v8.0 — Multi-Model Investigation Pipeline

## Execucao

### Passo 1: Receber bug report
Coletar: descricao, error message, screenshots, stack trace.

### Passo 2: Determinar preset
Default: balanced. Aceita --preset {economy|balanced|quality|single}.
Se single: executar v7.0 inline (sem subagents).

### Passo 3: Executar pipeline
Para cada fase (0, 1, 2, 3, 4, 5, 6):
  1. Montar briefing usando template da fase + outputs anteriores
  2. Spawnar: Agent(model: routing[fase], prompt: briefing)
  3. Receber resultado
  4. Validar: todos campos obrigatorios presentes?
     - Se faltar campo: FALLBACK — orquestrador completa inline
  5. Armazenar resultado para proximas fases

### Passo 4: SDC Bridge (Fase 7)
  1. Gerar fix_requirements a partir de resultado_fase_6
  2. Criar story draft em docs/stories/backlog/
  3. Disparar SDC: *workflow story-development-cycle {story} --yolo
  4. Aguardar conclusao ou registrar como pendente

### Passo 5: Documentacao + Meta-Learning (Fases 8-9)
  1. Montar briefing da Fase 8 com TODOS outputs + resultado SDC
  2. Spawnar: Agent(model: routing[fase_8], prompt: briefing)
  3. Spawnar: Agent(model: routing[fase_9], prompt: briefing)
  4. Consolidar relatorio final

### Passo 6: Salvar
  - Relatorio em docs/qa/investigations/
  - Registro em investigations.yaml
  - Anti-patterns em known-anti-patterns.md
  - SOPs em sops/
  - Handoff em .aios/handoffs/

## Fallback
Se subagent falhar ou retornar incompleto:
  - Logar: "FALLBACK: Fase {N} executada inline pelo orquestrador"
  - Orquestrador completa a fase inline (comportamento v7.0)
  - Continuar pipeline normalmente

## Phase Contracts
{referencia para contratos da Story 25.1}

## Model Routing
{referencia para routing da Story 25.2}

## Briefing Templates
{10 templates da Story 25.3}

## Metodologia de Referencia
{manter toda metodologia v7.0 como referencia para os briefings}
```

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** CRITICAL

---

### Story 25.5: SDC Bridge — Fase 6.5 Gera Story e Dispara SDC

**Descricao:** Em vez de @qa implementar o fix inline (Fase 7 atual), o RCA gera uma story de fix com fix_requirements e dispara o SDC. O @dev implementa via SDC, com quality gate real. Apos SDC concluir, o RCA continua com Fases 8-9.

**Design:**
Nova Fase 6.5 (entre Evidence Grading e Documentacao):

```markdown
## Fase 6.5 — SDC Bridge

1. **Gerar fix_requirements** a partir do output da Fase 6:
   ```yaml
   fix_requirements:
     source_rca: "rca-{date}-{slug}"
     root_cause: "{descricao confirmada}"
     fix_approach: "{O QUE fazer, nao COMO}"
     tests_required:
       - "Teste que reproduz bug original"
       - "Teste de contrato na origem"  
       - "Testes de regressao"
     fix_this_first: ["{ranking da Fase 5}"]
     affected_files: ["{lista}"]
     constraints: ["{limitacoes}"]
     evidence_level: "E1_confirmed"
   ```

2. **Criar story draft:**
   - Salvar em `docs/stories/backlog/fix-rca-{date}-{slug}.md`
   - Formato compativel com story template do SDC
   - Status: Ready (ja validado pela investigacao)

3. **Decidir execucao:**
   - **Modo interativo:** Perguntar "Disparar SDC agora ou deixar no backlog?"
   - **Modo YOLO:** Disparar automaticamente
   - **Se nao disparar:** Registrar como pendente, continuar para Fase 8

4. **Se disparar SDC:**
   - `*workflow story-development-cycle {story-path} --yolo`
   - Aguardar conclusao
   - Coletar: commit hash, arquivos modificados, testes adicionados
   - Alimentar Fase 8 com resultado do SDC

5. **Se SDC falhar:**
   - Registrar falha no relatorio
   - NAO implementar inline (manter separation of concerns)
   - Story fica no backlog para implementacao posterior
```

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** HIGH

---

### Story 25.6: Fallback & Validation — Graceful Degradation

**Descricao:** Se um subagent falhar (timeout, resposta incompleta, erro), o orquestrador deve degradar gracefully: completar a fase inline e continuar. O pipeline NUNCA deve parar por causa de falha de subagent.

**Design:**
Para cada chamada Agent():

```markdown
## Fallback Protocol

1. **Validar resultado:**
   - Todos campos obrigatorios presentes?
   - Formato correto (YAML parseavel)?
   - Conteudo coerente (nao vazio, nao generico)?

2. **Se validacao falhar:**
   ```
   Log: "⚠️ FALLBACK: Fase {N} subagent retornou resultado incompleto"
   Log: "Campos faltando: {lista}"
   Log: "Executando inline pelo orquestrador"
   ```
   - Orquestrador executa fase inline usando instrucoes v7.0
   - Resultado inline substitui resultado do subagent
   - Pipeline continua normalmente

3. **Se subagent timeout:**
   - Timeout default: 120s por fase (configuravel)
   - Apos timeout: fallback inline automatico

4. **Se preset = single:**
   - Skip ALL subagents
   - Executar tudo inline (comportamento v7.0 exato)
   - Zero overhead de orquestracao

5. **Metricas de fallback (registrar no relatorio):**
   ```yaml
   pipeline_metrics:
     preset: balanced
     phases_via_subagent: [0, 1, 2, 3, 4, 5, 6, 8, 9]
     phases_via_fallback: []
     phases_via_sdc: [7]
     estimated_cost: $1.40
     estimated_cost_if_single: $2.93
   ```
```

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** MEDIUM

---

## Waves de Implementacao

```
Wave 1: Foundation (25.1 + 25.2)       → Contratos + Routing config
Wave 2: Prompts (25.3)                 → 10 briefings autossuficientes
Wave 3: Core (25.4 + 25.5)            → Orquestrador + SDC bridge
Wave 4: Safety (25.6)                  → Fallback + validation
```

**Dependencias:**
- Wave 1 eh pre-requisito para tudo (contratos definem o que cada fase espera)
- Wave 2 depende de Wave 1 (briefings usam contratos)
- Wave 3 depende de Wave 2 (orquestrador usa briefings)
- Wave 4 depende de Wave 3 (fallback protege o orquestrador)

---

## Criterios de Sucesso

| Metrica | Antes (v7.0) | Meta (v8.0) |
|---------|-------------|-------------|
| Custo por investigacao | ~$2.93 | ~$1.40 (-52%) |
| Tokens Opus consumidos | ~370K | ~45K (-88%) |
| Max context por fase | 316K (acumulado) | ~15K (isolado) |
| Fix passa pelo SDC | Nao (inline) | Sim (quality gate real) |
| Velocidade (fases mecanicas) | Opus speed | Haiku speed (~3x mais rapido) |
| Fallback se subagent falha | N/A | Inline automatico (v7.0) |
| Preset configuravel | Nao | Sim (economy/balanced/quality/single) |

---

## Notas

- **Zero mudanca na metodologia:** Mesmas fases, mesma logica, mesmos relatorios. Muda COMO executa, nao O QUE executa.
- **Backward compatible:** Preset `single` reproduz v7.0 exato. Zero subagents, zero overhead.
- **Portavel:** LLMs sem multi-model usam preset `single`. Briefing templates servem como checklists.
- **Incremental:** Pode adotar 1 wave por vez. Wave 1 sozinha ja documenta contratos uteis.
- **SDC Bridge:** Maior mudanca qualitativa — fix passa por quality gate real em vez de ser implementado pelo investigador.
