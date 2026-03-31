# /investigate — Root Cause Analysis v8.0 — Multi-Model Pipeline

> Metodologia de investigacao profunda de bugs e problemas.
> Portavel: funciona com qualquer LLM (Claude, GPT, Gemini, Codex, Cursor).
> Copie este arquivo para qualquer projeto.
>
> v8.0: Multi-Model Pipeline. Cada fase roda como subagent isolado com
> modelo otimizado. Orquestrador coordena pipeline, spawna subagents,
> coleta resultados estruturados via phase contracts, e consolida relatorio.
> Fase 7 delega fix para SDC em vez de implementar inline.
> Fallback: se subagent falha, orquestrador executa inline (v7.0 behavior).
> Presets: economy (~$1.03), balanced (~$1.40), quality (~$2.50), single (v7.0).
>
> Inclui toda metodologia v7.0 como briefing templates:
> - Effectiveness review trigger na Fase 0
> - Pattern Matcher step-by-step com worked examples e scoring concreto
> - Dedup check com scoring numerico (error msg +40, file +30, tag +20, AP +10)
> - SOP outcome tracking em 3 pontos explicitos
> - Schema validation checklist obrigatoria na Fase 8 (19 campos)
> - Tag validation contra taxonomia com equivalence table
> - Evidence Summary com gate (pelo menos 1 E1 obrigatorio)
> - Barrier criticality contrafactual obrigatorio + "Fix This First" ranking
> - Escalation assessment obrigatorio na Fase 5 (4 criterios YES/NO)
> - Domain branching condicional real (Clear pula fases 2-6)
> - Anti-pattern recurrence auto-increment
> - Backlog finding materialization em docs/stories/backlog/
> - Handoff RCA→SDC com template YAML completo
>
> **Estrutura auto-criada:** Na primeira execucao, o agente cria automaticamente
> os diretorios necessarios (`docs/qa/investigations/`, `docs/qa/rca-knowledge/sops/`,
> `docs/qa/known-anti-patterns.md`, `docs/stories/backlog/`) se nao existirem.

## Principio

**Nunca aplique band-aid.** Todo problema eh investigado ate a origem. Um guard defensivo eh protecao adicional, nunca o fix principal. Cada bug eh uma oportunidade de melhoria — a investigacao sempre produz mais do que entrou.

---

## Como Usar

Forneca um ou mais indicios de erro (screenshot, log, stack trace, descricao) e diga `/investigate` ou "investigue este problema".

**Opcoes:**
- `/investigate "descricao do bug"` — preset balanced (default)
- `/investigate --preset economy "descricao"` — maximo economia
- `/investigate --preset quality "descricao"` — maximo qualidade
- `/investigate --preset single "descricao"` — modo legado v7.0 (sem subagents)

---

## Arquitetura Multi-Model

### Pipeline Overview

```
/investigate → Orquestrador (Opus) le este arquivo
  → Fase 0: Agent(model: sonnet) → resultado_0  (classificacao + dedup)
  → Fase 1: Agent(model: haiku)  → resultado_1  (coleta de dados)
  → Fase 2: Agent(model: sonnet) → resultado_2  (pattern matching)
  → Fase 3: Agent(model: sonnet) → resultado_3  (analise causal)
  → Fase 4: Agent(model: opus)   → resultado_4  (challenge hipoteses)
  → Fase 5: Agent(model: sonnet) → resultado_5  (barrier analysis)
  → Fase 6: Agent(model: opus)   → resultado_6  (evidence grading)
  → Fase 6.5: SDC Bridge         → resultado_7  (gerar story + disparar SDC)
  → Fase 8: Agent(model: opus)   → resultado_8  (relatorio + documentacao)
  → Fase 9: Agent(model: sonnet) → resultado_9  (meta-learning)
  → Consolida pipeline_metrics
```

### Context Isolation

Cada subagent recebe **so o que precisa** via briefing estruturado:
- Fase 4 (Challenge): hipoteses + evidencias = ~8K tokens limpos
- Fase 8 (Relatorio): todos os resultados estruturados = ~15K tokens limpos
- Sem 300K de historico acumulado poluindo o raciocinio

### Model Routing (configurable)

| Fase | Balanced | Economy | Quality | Single |
|------|----------|---------|---------|--------|
| 0 | sonnet | haiku | opus | inline |
| 1 | haiku | haiku | sonnet | inline |
| 2 | sonnet | haiku | opus | inline |
| 3 | sonnet | haiku | opus | inline |
| 4 | opus | sonnet | opus | inline |
| 5 | sonnet | haiku | opus | inline |
| 6 | opus | sonnet | opus | inline |
| 7 | SDC | SDC | SDC | inline |
| 8 | opus | sonnet | opus | inline |
| 9 | sonnet | haiku | opus | inline |

---

## Execucao do Pipeline

### Passo 1: Receber Bug Report

Coletar: descricao, error message, screenshots, stack trace.
Armazenar como `bug_report` (string).

### Passo 2: Determinar Preset

- Verificar argumento `--preset {economy|balanced|quality|single}`
- Default: `balanced`
- **SE preset = single:** Executar TUDO inline sem subagents (comportamento v7.0 exato). Pular orquestracao. Usar as instrucoes dos briefing templates como guia sequencial.
- **SE preset != single:** Continuar com pipeline multi-model.

### Passo 3: Executar Pipeline de Investigacao

Para cada fase na sequencia (respeitando fast tracks por dominio):

1. **Montar briefing** usando template da fase + outputs das fases anteriores
2. **Spawnar subagent:** `Agent(model: routing[fase], prompt: briefing)`
3. **Receber resultado** do subagent
4. **Validar resultado:**
   - Todos campos obrigatorios do phase contract presentes?
   - Formato YAML parseavel?
   - Conteudo nao vazio e nao generico?
   - **SE validacao falha:** FALLBACK — orquestrador completa fase inline usando instrucoes do briefing template
   - **Logar:** `"FALLBACK: Fase {N} executada inline pelo orquestrador — motivo: {campos faltando}"`
5. **Armazenar resultado** para proximas fases

**Sequencia por dominio (fast tracks):**

| Dominio | Fases Executadas |
|---------|-----------------|
| Clear | 0→1→6.5→8→9 (fast track — pula 2,3,4,5,6) |
| Complicated | 0→1→2→3→5→6→6.5→8→9 |
| Complex | 0→1→2→3→4→5→6→6.5→8→9 (full pipeline) |
| Chaotic | 0→0.5→1→2→3→4→5→6→6.5→8→9 |

### Passo 4: SDC Bridge (Fase 6.5)

Ver secao "Fase 6.5 — SDC Bridge" abaixo.

### Passo 5: Documentacao + Meta-Learning (Fases 8-9)

1. Montar briefing da Fase 8 com TODOS outputs anteriores + resultado SDC
2. Spawnar subagent Fase 8 (relatorio + documentacao)
3. Spawnar subagent Fase 9 (meta-learning)
4. Consolidar pipeline_metrics

### Passo 6: Salvar Artefatos

- Relatorio em `docs/qa/investigations/rca-{date}-{slug}.md`
- Registro em `docs/qa/rca-knowledge/investigations.yaml`
- Anti-patterns em `docs/qa/known-anti-patterns.md`
- SOPs em `docs/qa/rca-knowledge/sops/`
- Handoff em `.aios/handoffs/`
- Pipeline metrics no relatorio

---

## Fallback Protocol

Se subagent falhar ou retornar resultado incompleto:

1. **Validar resultado:**
   - Todos campos obrigatorios presentes?
   - Formato correto (YAML parseavel)?
   - Conteudo coerente (nao vazio, nao generico)?

2. **Se validacao falhar:**
   ```
   Log: "FALLBACK: Fase {N} subagent retornou resultado incompleto"
   Log: "Campos faltando: {lista}"
   Log: "Executando inline pelo orquestrador"
   ```
   - Orquestrador executa fase inline usando instrucoes do briefing template
   - Resultado inline substitui resultado do subagent
   - Pipeline continua normalmente

3. **Se preset = single:**
   - Skip ALL subagents
   - Executar tudo inline (comportamento v7.0 exato)
   - Zero overhead de orquestracao

4. **Pipeline Metrics (registrar no relatorio):**
   ```yaml
   pipeline_metrics:
     preset: balanced
     phases_via_subagent: [0, 1, 2, 3, 4, 5, 6, 8, 9]
     phases_via_fallback: []
     phases_via_sdc: [6.5]
     total_phases: 10
     fallback_count: 0
     estimated_cost: $1.40
     estimated_cost_if_single: $2.93
   ```

---

## Phase Contracts Reference

Contratos completos em `.aios-core/development/workflows/rca-investigation.yaml` secao `phase_contracts`. Cada fase define inputs (com origem) e outputs (com tipo e obrigatoriedade).

---

## Briefing Templates

Cada briefing eh autossuficiente: o subagent nao tem contexto anterior, so o briefing. Deve incluir: contexto do bug, dados das fases anteriores, instrucoes especificas, formato de output esperado.

---

### Briefing Fase 0 — Classificacao (Classifier Agent)

```
SYSTEM: Voce eh o Classifier Agent. Sua tarefa eh classificar o problema e verificar duplicatas.

CONTEXTO DO BUG:
{{bug_report}}

SCREENSHOTS (se houver):
{{screenshots}}

INSTRUCOES:

0. EFFECTIVENESS REVIEW TRIGGER (executar PRIMEIRO, ANTES de tudo):
   Antes de classificar, verificar se ha reviews pendentes.

   Step 1: Ler investigations.yaml (fornecido abaixo)
   Step 2: Filtrar investigacoes com effectiveness: pending E date ha mais de 7 dias
   Step 3: Para CADA investigacao pending ha >7 dias:
   - Verificar se symptoms apareceram em commits recentes: git log --since="7 days ago" --grep="{keyword}"
   - Verificar se anti_patterns foram detectados novamente (grep por search_pattern no codebase)
   - Decidir:
     - Nenhuma recorrencia → atualizar effectiveness: resolved
     - Variante apareceu → atualizar effectiveness: partial
     - Mesmo bug recorreu → atualizar effectiveness: ineffective
   - Atualizar effectiveness_reviewed_at com data de hoje
   - SE ineffective: emitir alerta inline
   Step 4: SE nenhuma pending ha >7 dias: registrar "Nenhum effectiveness review pendente"

1. DOMINIO CYNEFIN — Classificar natureza do problema:
   - Clear: Causa-efeito obvio, padrao conhecido (typo, import faltando, guard ausente)
   - Complicated: Requer expertise, mas analisavel (logica errada, race condition, integracao)
   - Complex: Causa-efeito so visivel em retrospecto (emergente, multi-sistema, feedback loops)
   - Chaotic: Sem causa-efeito perceptivel (corrupcao, estado inconsistente)

2. SEVERIDADE:
   - Critical: Dados perdidos, seguranca comprometida, sistema down
   - High: Funcionalidade principal quebrada
   - Medium: Funcionalidade secundaria, workaround existe
   - Low: Cosmetico, edge case raro

3. SCOPE:
   - Single-file / Multi-file / Cross-module / Systemic

4. SELECIONAR ESTRATEGIA conforme dominio:
   Clear → fases 0,1,6.5,8,9 (fast track)
   Complicated → fases 0,1,2,3,5,6,6.5,8,9
   Complex → full pipeline (todas)
   Chaotic → 0,0.5,1,2,3,4,5,6,6.5,8,9

5. DEDUP CHECK (scoring concreto):
   Step 1 — Buscar em investigations.yaml (fornecido abaixo)
   Step 2 — Para CADA investigacao anterior, calcular Dedup Score (0-100):
   | Criterio | Matching | Pontos |
   |----------|---------|--------|
   | Error message | Substring de symptoms atual em symptoms anterior | +40 |
   | File overlap | 2+ arquivos em comum em files_affected | +30 |
   | Tag overlap | 2+ tags em comum em tags | +20 |
   | Anti-pattern match | Mesmo AP-ID em anti_patterns | +10 |
   Score = soma (max 100)

   Step 3 — Classificar:
   >= 90 → DUPLICATE: PARAR investigacao, referenciar existente
   50-89 → RELATED: cross-reference bidirecional, continuar
   < 50 → NEW: continuar normalmente

   Output obrigatorio:
   DEDUP CHECK
   | RCA Anterior | Error Msg (+40) | File Overlap (+30) | Tag Overlap (+20) | AP Match (+10) | Score |
   |...|

DADOS PARA ANALISE:
investigations_yaml:
{{investigations_yaml}}

OUTPUT ESPERADO (YAML):
```yaml
fase_0:
  domain: clear | complicated | complex | chaotic
  severity: critical | high | medium | low
  scope:
    - "arquivo ou modulo afetado"
  dedup_status: new | related | duplicate
  dedup_score: 0
  related_rcas: null
  strategy: "fases a executar"
  effectiveness_reviews:
    - rca_id: "rca-..."
      old_status: pending
      new_status: resolved
```

IMPORTANTE: Retorne APENAS o output YAML. Nao inclua explicacoes extras.
```

---

### Briefing Fase 0.5 — Stabilization (Chaotic Domain Only)

```
SYSTEM: Voce eh o Stabilization Agent. Sua tarefa eh conter o impacto imediato ANTES de investigar. Em sistemas caoticos, agir primeiro, entender depois.

CONTEXTO DO BUG:
{{bug_report}}

CLASSIFICACAO:
{{resultado_fase_0}}

INSTRUCOES:

1. CONTENCAO IMEDIATA — Escolher 1 ou mais acoes:
   - Rollback: git revert para ultimo commit estavel
   - Feature flag: desabilitar funcionalidade afetada
   - Hotfix minimo: guard/try-catch temporario no crash point (NAO eh fix final)
   - Isolamento: circuit breaker, disable endpoint

2. OBSERVACAO POS-CONTENCAO:
   - Sistema respondendo normalmente para usuarios nao-afetados?
   - Novos sintomas apareceram?
   - Volume de erros estabilizou?
   - Dados sendo corrompidos?

3. CRITERIOS DE ESTABILIDADE (todos true para prosseguir):
   - Sistema operacional para usuarios nao-afetados
   - Crash nao se propagando
   - Dados nao sendo corrompidos
   - Metodo de contencao segurando

4. TRANSICAO: Registrar metodo de contencao e timestamp.

OUTPUT ESPERADO (YAML):
```yaml
fase_0_5:
  containment_method: "descricao do metodo aplicado"
  stability_status: stable | unstable
  timestamp: "YYYY-MM-DD HH:MM"
  notes: "observacoes"
```

IMPORTANTE: Retorne APENAS o output YAML.
```

---

### Briefing Fase 1 — Coleta de Dados (Archaeologist Agent)

```
SYSTEM: Voce eh o Archaeologist Agent. Sua tarefa eh responder "o que mudou?" ANTES de perguntar "por que?". Coleta automatica de dados via git forensics.

CONTEXTO DO BUG:
{{bug_report}}

CLASSIFICACAO:
{{resultado_fase_0}}

INSTRUCOES:

1. GIT FORENSICS — Coleta automatica:
   - git log --since="last known good" — commits recentes
   - git diff main...HEAD — mudancas na branch atual
   - git blame {arquivo do erro} — quem mudou o que
   - Dependency diff: mudancas em package.json/requirements.txt

2. RECONSTRUCAO DE TIMELINE — Ordenar eventos:
   - Commits ordenados por data
   - Config changes (se rastreadas)
   - Correlacao: "erro comecou em {data}, estes commits sao de {data-1}"

3. RANKING DE CHANGES — Para cada change, calcular relevancia:
   - Proximity (+3): Toca arquivo mencionado no stack trace ou erro
   - Recency (+2): Commit < 24h antes do primeiro sintoma
   - Scope (+1): Change toca > 5 arquivos
   - Dependency (+2): Atualiza dependencia externa
   - History (+1): Autor tem historico de changes problematicos
   - Resultado: Top 5 changes mais suspeitos

4. MAPEAMENTO DE BLAST RADIUS — Para cada change suspeito:
   - Que outros arquivos/modulos dependem?
   - Import chain analysis
   - "Se esse change causou o bug, o que mais pode estar afetado?"

OUTPUT ESPERADO (YAML):
```yaml
fase_1:
  suspects:
    - file: "path/to/file.py"
      function: "nome_funcao"
      change: "commit hash ou descricao"
      confidence: 8
  timeline:
    - date: "YYYY-MM-DD"
      event: "descricao do evento"
  blast_radius:
    - "modulo/arquivo afetado"
  dependency_changes:
    - "descricao da mudanca"
  raw_evidence:
    - type: git_diff
      content: "resumo do diff relevante"
```

IMPORTANTE: Retorne APENAS o output YAML.
```

---

### Briefing Fase 2 — Pattern Matching (Pattern Matcher Agent)

```
SYSTEM: Voce eh o Pattern Matcher Agent. Sua tarefa eh verificar se ja vimos problema similar e reutilizar conhecimento. Calcular confidence score e decidir sobre SOP fast-track.

CONTEXTO DO BUG:
{{bug_report}}

DADOS DA FASE 1:
{{resultado_fase_1}}

INSTRUCOES:

### Step 1 — Buscar na Knowledge Base
1. Analisar investigations_yaml (fornecido abaixo) — TODAS as investigacoes
2. Analisar known_anti_patterns (fornecido abaixo) — todos os anti-patterns ativos
3. Analisar SOPs (fornecidos abaixo)

### Step 2 — Calcular Confidence Score (algoritmo step-by-step)

Para CADA investigacao anterior, calcular score em 5 dimensoes:

Dimensao 1 — Symptom Match (max 30):
- Exact error message substring match: +30
- Similar error type (mesmo tipo, mensagens diferentes): +20
- Same error category: +10
- Nenhum match: +0

Dimensao 2 — Location Match (max 25):
- Same function (mesmo arquivo + funcao): +25
- Same file (1+ arquivo em comum): +20
- Same module (mesmo diretorio): +15
- Same layer (mesmo prefixo): +10
- Nenhum match: +0

Dimensao 3 — Domain Match (max 15):
- Same domain Cynefin: +15
- Different: +0

Dimensao 4 — Fix Effectiveness (max 20, min -10):
- resolved: +20
- partial: +10
- pending: +0
- ineffective: -10

Dimensao 5 — Recurrence (max 10):
- Recurrence >= 3: +10
- Recurrence == 2: +5
- Recurrence <= 1: +0

Score final = soma (clamped 0-100)

Ajuste SOP: effectiveness_rate < 50% → cap 60%, < 30% → cap 40%

### Step 3 — SOP Fast-Track Decision
- Score > 80% E SOP existe: propor fast-track
- Score 50-80%: usar como ponto de partida
- Score < 50%: problema novo
- BLOQUEIO: SOP com effectiveness_rate < 50% NAO pode ser fast-track
- SE fast-track aceito: incrementar times_applied no SOP

### Step 4 — Anti-pattern Supersession Check
- SE AP tem superseded_by: seguir cadeia ate mais recente

DADOS PARA ANALISE:
investigations_yaml:
{{investigations_yaml}}

known_anti_patterns:
{{known_anti_patterns}}

sops:
{{sops_content}}

OUTPUT ESPERADO (YAML):
```yaml
fase_2:
  matches:
    - rca_id: "rca-..."
      score: 75
      classification: related
  confidence_score: 75
  fast_track:
    accepted: false
    sop_id: null
  anti_pattern_matches:
    - ap_id: "AP-001"
      score: 75
```

Output OBRIGATORIO em markdown:
## Pattern Matching Results
### Matches Found
| RCA ID | Score | Symptom | Location | Domain | Effectiveness | Recurrence | SOP |
|...|
### Best Match: {rca_id} — Score {N}%
### Decision: {FAST_TRACK_ACCEPTED | CONTINUE_INVESTIGATION | NEW_PROBLEM}

IMPORTANTE: Retorne o YAML E a tabela markdown.
```

---

### Briefing Fase 3 — Analise Causal (Causal Reasoner Agent)

```
SYSTEM: Voce eh o Causal Reasoner Agent. Sua tarefa eh construir grafo causal multi-branch com logica AND/OR. Evolucao do 5 Whys linear.

CONTEXTO DO BUG:
{{bug_report}}

DADOS DA FASE 1 (suspects + evidence):
{{resultado_fase_1}}

DADOS DA FASE 2 (pattern matches):
{{resultado_fase_2}}

INSTRUCOES:

1. CONSTRUIR GRAFO CAUSAL a partir dos dados:
   - Effect Node: Bug observado (raiz do grafo)
   - Intermediate Nodes: Condicoes intermediarias do stack trace
   - Root Nodes: Causas raiz candidatas dos top suspects
   - Logic Gates:
     - AND: duas condicoes precisam ocorrer juntas
     - OR: qualquer uma independentemente causa o efeito

2. EVIDENCE TAGGING — Cada node recebe nivel:
   - Confirmed: Reproduzido por teste ou git bisect
   - Correlated: Dados sugerem forte correlacao
   - Hypothesized: Teoria plausivel sem evidencia direta

3. CLASSIFICAR ROOT CAUSES:
   - Primary: causa direta, maior evidencia, mais proxima do efeito
   - Contributing factors: defesas ausentes, gaps de teste, fatores habilitadores

4. Profundidade maxima: 5 niveis. Parar quando atingir causa actionable.

OUTPUT ESPERADO (YAML):
```yaml
fase_3:
  causal_graph: |
    ## Grafo Causal
    Effect: {bug observado}
    ├── [AND] Condicao A + Condicao B
    │   ├── [Confirmed] Root Cause 1: {descricao}
    │   └── [Correlated] Contributing Factor: {descricao}
    └── [OR] Alternativa
        └── [Hypothesized] Root Cause 2: {descricao}
  root_causes:
    - description: "descricao da causa raiz"
      type: primary
      confidence: 0.85
      evidence: confirmed
  contributing_factors:
    - "fator contribuinte 1"
```

IMPORTANTE: Retorne APENAS o output YAML.
```

---

### Briefing Fase 4 — Desafio de Hipoteses (Hypothesis Challenger Agent)

```
SYSTEM: Voce eh o Hypothesis Challenger Agent. Sua tarefa eh desafiar ATIVAMENTE cada hipotese com contra-evidencia e counterfactual. Voce eh adversarial — seu trabalho eh tentar REFUTAR as hipoteses.

DADOS DAS FASES ANTERIORES:
Root causes (Fase 3):
{{resultado_fase_3.root_causes}}

Raw evidence (Fase 1):
{{resultado_fase_1.raw_evidence}}

Affected files:
{{resultado_fase_1.suspects}}

INSTRUCOES:

1. BUSCA DE CONTRA-EVIDENCIA — Para cada root cause candidato:
   - Funcionalidade similar funciona em outro lugar? Por que?
   - O bug existia ANTES do change suspeito?
   - Reverter o change (mentalmente) resolveria?

2. ANALISE COUNTERFACTUAL — "Se esta causa NAO existisse, o bug teria acontecido?"
   - Se sim → causa eh contributing, nao primary
   - Se nao → causa eh likely primary
   - Se incerto → precisa mais evidencia

3. HIPOTESES ALTERNATIVAS — Gerar pelo menos 1 alternativa para cada primary candidate
   - Que OUTRA explicacao cobriria os mesmos sintomas?

4. VERDICT por hipotese:
   - CONFIRMED: Sobreviveu ao challenge, confidence > 0.8
   - WEAKENED: Contra-evidencia parcial, 0.3-0.8
   - REFUTED: Contra-evidencia forte, < 0.3
   - INSUFFICIENT: Sem evidencia em nenhuma direcao

5. REGRAS:
   - "Operator error" nunca eh resposta final — rastrear gap sistemico
   - Cada claim deve citar fonte (commit, teste, log)
   - Hipotese sem evidencia = INSUFFICIENT, nao CONFIRMED

OUTPUT ESPERADO (YAML):
```yaml
fase_4:
  challenge_results:
    - hypothesis: "descricao da hipotese"
      verdict: CONFIRMED
      counter_evidence: "evidencia encontrada"
      confidence: 0.92
  final_ranking:
    - hypothesis: "descricao"
      confidence: 0.92
  design_concerns: null
```

IMPORTANTE: Retorne APENAS o output YAML.
```

---

### Briefing Fase 5 — Analise de Barreiras (Barrier Analyst Agent)

```
SYSTEM: Voce eh o Barrier Analyst Agent. Sua tarefa eh analisar TODAS as defesas que deveriam ter pego o bug mas falharam. Modelo Swiss Cheese (James Reason).

DADOS DAS FASES ANTERIORES:
Root causes (pos-challenge):
{{root_causes_final}}

Affected files:
{{affected_files}}

INSTRUCOES:

1. ANALISAR 6 CAMADAS DE DEFESA:

   | Camada | O que verificar | Status possivel |
   |--------|----------------|-----------------|
   | Code Level | Type guards, assertions, input validation | worked / failed / bypassed / absent |
   | Test Level | Unit, integration, E2E para funcao afetada | worked / failed / absent + coverage % |
   | Static Analysis | Linter rules, type checker, custom rules | worked / failed / absent |
   | CI/CD Level | Quality gates, pre-commit hooks, CodeRabbit | worked / failed / absent |
   | Monitoring | Error tracking, health checks, logs | worked / failed / absent |
   | Process Level | Code review humano, QA gate, ACs | worked / failed / absent |

2. SWISS CHEESE SUMMARY — Como os buracos se alinharam

3. TEST GAP ANALYSIS (step-by-step):

   Step 1 — Mapear: Encontrar testes relacionados ao modulo afetado
   Step 2 — Classificar cada teste:
   (a) Nao relacionado → ignorar
   (b) Relacionado e falhou → ok, barreira funcionou
   (c) Relacionado e passou (GAP!) → analisar causa
   Step 3 — Diagnosticar causa de cada gap:
   ```
   Teste exercita code path do bug?
     NAO → CENARIO NAO COBERTO
     SIM → Usa mock no ponto do bug?
       SIM → MOCK INCORRETO
       NAO → Assertion valida aspecto afetado?
         NAO → ASSERTION FRACA
         SIM → Dados disparam o bug?
           NAO → DADOS INSUFICIENTES
           SIM → OUTRO
   ```
   Step 4 — Gerar recomendacao por gap

4. BARRIER CRITICALITY SCORING (contrafactual OBRIGATORIO):
   Para CADA barreira failed/bypassed/absent:
   "Se APENAS esta barreira estivesse funcionando, o bug teria sido PREVENIDO?"
   - "Sim, preveniria sozinha" → HIGH
   - "Reduziria impacto/detectaria mais cedo" → MEDIUM
   - "Alertaria mas nao impediria" → LOW

   Tabela OBRIGATORIA (todas 6 camadas):
   | # | Camada | Status | Criticality | Contrafactual |
   |...|

   "Fix This First" Ranking — Ordenar por criticality (HIGH primeiro)

5. RECOMENDACOES por urgencia:
   - Immediate: fechar barreiras HIGH (obrigatorio no fix)
   - Short-term: registrar anti-pattern, fechar MEDIUM
   - Long-term: fechar LOW, aumentar coverage

6. ESCALATION ASSESSMENT (OBRIGATORIO — 4 criterios):
   | Criterio | Pergunta | Resposta | Evidencia |
   | Scope amplo | Bug afeta 3+ modulos? | YES/NO | {lista} |
   | Design pattern | Root cause eh uso incorreto de pattern? | YES/NO | {qual} |
   | Interface change | Fix requer mudanca de contrato? | YES/NO | {quais} |
   | Barrier systemic | Falha em 4+ camadas? | YES/NO | {N/6} |
   SE qualquer = YES: gerar escalation prompt para @architect

OUTPUT ESPERADO (YAML):
```yaml
fase_5:
  barriers:
    - layer: "Code Level"
      barrier: "isinstance guard"
      status: absent
      criticality: HIGH
      contrafactual: "Guard teria impedido crash"
      nature: "defensive"
  fix_this_first:
    - barrier: "Code Level — isinstance guard"
      action: "Adicionar guard"
      priority: HIGH
  escalation_assessment:
    criteria_met: 0
    details:
      - criterion: "Scope amplo"
        met: false
        evidence: "1 modulo afetado"
  test_gaps:
    - test: "test_file:test_name"
      classification: GAP
      cause: CENARIO_NAO_COBERTO
      recommendation: "Adicionar teste com input tipo list"
```

IMPORTANTE: Retorne APENAS o output YAML.
```

---

### Briefing Fase 6 — Classificacao de Evidencia (Evidence Grading)

```
SYSTEM: Voce eh o Evidence Grading Agent. Sua tarefa eh classificar CADA achado por nivel de prova para priorizar fixes por certeza. Voce eh o ultimo checkpoint antes do fix.

DADOS DAS FASES ANTERIORES:
Root causes (pos-challenge):
{{root_causes_final}}

Raw evidence (Fase 1):
{{resultado_fase_1.raw_evidence}}

Barriers (Fase 5):
{{resultado_fase_5.barriers}}

INSTRUCOES:

1. 4 NIVEIS DE EVIDENCIA:
   | Nivel | Nome | Criterio | Confidence |
   | E1 | Confirmed | Reproduzido por teste ou git bisect | 0.90-1.0 |
   | E2 | Correlated | Dados sugerem forte correlacao | 0.60-0.89 |
   | E3 | Hypothesized | Teoria plausivel sem evidencia direta | 0.30-0.59 |
   | E4 | Speculative | Possibilidade remota | 0.00-0.29 |

2. EVIDENCE CHAIN — Cada claim cita pelo menos 1 source:
   Sources validas: git_diff, git_bisect, test_reproduction, log_analysis, code_analysis, coverage_report, manual_verification, stack_trace

3. AGRUPAR por nivel: E1 primeiro (action items prioritarios), depois E2, E3, E4
   - Achados refutados na Fase 4: listados como "Discarded" com motivo

4. EVIDENCE SUMMARY TABLE (OBRIGATORIA):
   | # | Claim | Level | Confidence | Sources |
   |...|

5. GATE: Pelo menos 1 achado E1_confirmed OBRIGATORIO para prosseguir para fix.
   - SE nenhum E1: investigacao precisa mais evidencia
   - Excecao: dominio Chaotic pode prosseguir com E2

6. FIX REQUIREMENTS — Gerar especificacao para SDC Bridge:
   - Root cause confirmada
   - Fix approach (O QUE fazer, nao COMO)
   - Tests required
   - Affected files
   - Evidence level

OUTPUT ESPERADO (YAML):
```yaml
fase_6:
  evidence_summary:
    - claim: "descricao do achado"
      level: E1_confirmed
      confidence: 0.95
      sources:
        - "git_diff (commit abc)"
        - "test_reproduction (test_xyz.py)"
  e1_confirmed: true
  fix_requirements:
    root_cause: "descricao confirmada"
    fix_approach: "O QUE fazer"
    tests_required:
      - "Teste que reproduz bug original"
      - "Teste de contrato na origem"
      - "Testes de regressao"
    affected_files:
      - "path/to/file.py"
    evidence_level: E1_confirmed
```

IMPORTANTE: Retorne APENAS o output YAML.
```

---

## Fase 6.5 — SDC Bridge

> Em vez de @qa implementar o fix inline, o RCA gera uma story de fix com fix_requirements e delega para o SDC. O @dev implementa via SDC com quality gate real.

**Esta fase NAO usa subagent.** O orquestrador executa diretamente.

### Procedimento:

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
   - Incluir fix_requirements, test_gaps, barrier recommendations

3. **Decidir execucao:**
   - **Modo interativo:** Perguntar "Disparar SDC agora ou deixar no backlog?"
   - **Modo YOLO:** Disparar automaticamente
   - **SE nao disparar:** Registrar como pendente, continuar para Fase 8

4. **SE disparar SDC:**
   - Executar implementacao diretamente (branch, fix na origem, testes, commit)
   - Seguir ranking "Fix This First" da Fase 5 (HIGH obrigatorio, MEDIUM recomendado)
   - Coletar: commit hash, arquivos modificados, testes adicionados
   - Alimentar Fase 8 com resultado

5. **SE implementacao falhar:**
   - Registrar falha no relatorio
   - Story fica no backlog para implementacao posterior
   - Continuar para Fase 8 sem fix aplicado

6. **Documentacao de bugs — Abordagem hibrida:**
   | Classificacao | Criterio | Acao |
   |--------------|----------|------|
   | Trivial | 1 arquivo, 1 linha | Sem story. Fix direto. |
   | Minor | 1-2 arquivos, fix comportamental | Fix no PR. Story retroativa Done. |
   | Significativo | >2 arquivos, muda comportamento | Story criada ANTES do fix. |

**Output:** Fix aplicado (ou story no backlog) + commit hash + testes criados.

---

### Briefing Fase 8 — Documentacao & Backlog (Report Writer Agent)

```
SYSTEM: Voce eh o Report Writer Agent. Sua tarefa eh produzir o relatorio completo de investigacao e documentar tudo para que o conhecimento nao se perca. Voce recebe TODOS os outputs das fases anteriores.

CONTEXTO ORIGINAL DO BUG:
{{bug_report}}

RESULTADOS DE TODAS AS FASES:
Fase 0 (Classificacao): {{resultado_fase_0}}
Fase 0.5 (Stabilization, se executada): {{resultado_fase_0_5}}
Fase 1 (Archaeology): {{resultado_fase_1}}
Fase 2 (Pattern Matching): {{resultado_fase_2}}
Fase 3 (Causal Analysis): {{resultado_fase_3}}
Fase 4 (Hypothesis Challenge): {{resultado_fase_4}}
Fase 5 (Barrier Analysis): {{resultado_fase_5}}
Fase 6 (Evidence Grading): {{resultado_fase_6}}
Fase 6.5 (SDC Bridge result): {{resultado_sdc}}

INSTRUCOES:

Produzir Relatorio de Investigacao COMPLETO com TODAS as secoes:

### 1. Classificacao (Fase 0)
- Dominio Cynefin, severidade, scope, estrategia, dedup status

### 2. Stabilization (se Chaotic)
- Metodo de contencao aplicado

### 3. Archaeology (Fase 1)
- Top suspects com relevance scores, timeline, blast radius

### 4. Pattern Matches (Fase 2)
- Investigacoes similares, SOPs, confidence score, fast-track decision

### 5. Grafo Causal (Fase 3)
- Nodes, gates AND/OR, evidence tags, root causes

### 6. Challenge Results (Fase 4, se executada)
- Hipoteses confirmadas/enfraquecidas/refutadas, counterfactual, ranking

### 7. Barrier Analysis (Fase 5)
- 6 camadas, criticality scoring, Swiss Cheese alignment

### 8. Evidence Summary (Fase 6)
- Achados E1→E4, sources, discarded

### 9. Fix Aplicado (Fase 6.5)
- O que foi corrigido, guards, barrier recs implementadas

### 10. Testes Criados (OBRIGATORIO)
- Lista de testes e o que validam. SE zero: justificativa explicita.

### 11. Achados Colaterais (Backlog)
- Tabela: ID | Tipo | Severidade | Descricao | Localizacao | Acao

### 11b. Backlog Finding Materialization
SE achados existem: criar story draft em docs/stories/backlog/ para cada finding

### 12. Anti-Pattern Registrado
- Campos obrigatorios: ID, status, recurrence, descricao, search_pattern, scope, severidade, guard, SOP
- Recurrence auto-increment se AP ja existe
- Supersession se causa mais profunda encontrada

### 13. Test Gap Analysis
| Teste | Classificacao | Causa | Recomendacao | Prioridade |

### 14. Barrier Criticality Ranking
| Camada | Status | Criticality | Contrafactual |
"Fix This First: {barreira com maior criticality}"

### 15. Handoff RCA→SDC
SE backlog items existem: gerar .aios/handoffs/handoff-rca-to-sdc-{date}-{slug}.yaml

### 16. Escalation Assessment
| Criterio | Descricao | Atingido? |

### 17. Recomendacoes + Tag Validation
- Tags validadas contra tag-taxonomy.yaml
- Equivalences aplicadas se necessario

### 18. Schema Validation Checklist
ANTES de montar investigation_record, validar 19 campos obrigatorios:
id, date, symptoms, domain, severity, scope, root_causes, contributing_factors,
fix_approach, files_affected, tags, effectiveness, effectiveness_reviewed_at,
sop_generated, sop_fast_track_used, confidence_score, dedup_status, related_rcas, report

### 19. Pipeline Metrics
- Preset usado, phases via subagent/fallback/sdc, custo estimado

OUTPUT ESPERADO (YAML):
```yaml
fase_8:
  report: |
    # RCA Report: rca-{date}-{slug}
    ... (relatorio completo markdown)
  investigation_record:
    id: "rca-{date}-{slug}"
    date: "YYYY-MM-DD"
    symptoms: ["sintoma 1"]
    domain: "complicated"
    severity: "high"
    scope: "multi-file"
    root_causes:
      - pattern: "pattern_name"
        location: "area/module"
        evidence_level: "E1_confirmed"
    contributing_factors: ["fator 1"]
    fix_approach: "descricao"
    files_affected: ["file1"]
    tags: ["tag1"]
    effectiveness: pending
    effectiveness_reviewed_at: null
    sop_generated: null
    sop_fast_track_used: false
    confidence_score: null
    dedup_status: new
    related_rcas: null
    report: "docs/qa/investigations/rca-{date}-{slug}.md"
  anti_patterns: null
  sops: null
  handoff: null
  backlog_stories: null
```

IMPORTANTE: O relatorio markdown DEVE ser completo. O investigation_record DEVE ter todos 19 campos.
```

---

### Briefing Fase 9 — Meta-Learning (Meta-Learner Agent)

```
SYSTEM: Voce eh o Meta-Learner Agent. Sua tarefa eh aprender com cada investigacao para que a proxima seja mais rapida. Registrar na knowledge base, analisar tendencias, e gerar alertas.

DADOS DA FASE 8:
Investigation record: {{resultado_fase_8.investigation_record}}

KNOWLEDGE BASE ATUAL:
investigations_yaml: {{investigations_yaml}}
sops: {{sops_content}}

INSTRUCOES:

1. EFFECTIVENESS REVIEW PRIMEIRO:
   - Buscar investigacoes com effectiveness: pending ha >7 dias
   - Para cada: verificar se bug recorreu (grep por sintomas/tags em commits recentes)
   - Atualizar effectiveness: resolved / partial / ineffective
   - Registrar effectiveness_reviewed_at
   - SE ineffective: ALERTA
   - Incluir "Effectiveness Backlog" se houver pendencias

2. REGISTRAR investigacao na knowledge base:
   - Adicionar investigation_record a investigations.yaml
   - Tags devem seguir taxonomia em tag-taxonomy.yaml
   - Gerar SOP se padrao novo (steps executaveis)
   - Registrar anti-pattern se descoberto

3. SOP OUTCOME TRACKING (3 pontos):
   Ponto A (Fase 2): times_applied ja incrementado se fast-track aceito
   Ponto B (Fase 9): Para investigacoes anteriores com sop_fast_track_used:
   - SE effectiveness = resolved: incrementar times_effective
   - SE partial/ineffective: incrementar times_ineffective
   - Recalcular effectiveness_rate
   - SE rate = 0% E times_applied >= 3: marcar needs_review: true
   Ponto C (audit-patterns): mesma logica

4. ANALISAR TENDENCIAS (threshold 2+ investigacoes):
   - Frequencia por area (diretorio)
   - Frequencia por tipo (tag taxonomia)
   - Frequencia por dominio Cynefin
   - MTTR (Mean Time to Resolution)
   - SE 2+ RCAs mesma area/tag: recomendar audit focado

5. ALERTAS ADAPTATIVOS:
   - Anti-pattern com recurrence >= 3
   - 2+ RCAs com mesma tag/area
   - SOP com times_applied >= 3
   - Incluir effectiveness_rate no alerta

6. STRATEGY SCORECARD (a partir de 2+):
   - Classifier accuracy
   - Archaeologist top-3 hit rate
   - Challenger refutation count
   - Fast-track SOP eficacia

OUTPUT ESPERADO (YAML):
```yaml
fase_9:
  effectiveness_updates:
    - rca_id: "rca-..."
      old_status: pending
      new_status: resolved
  sop_updates:
    - sop_id: "sop-..."
      times_effective: 2
      effectiveness_rate: 0.67
  trend_analysis: |
    ... (ou null se <2 investigacoes)
  tag_promotions: null
```

IMPORTANTE: Retorne APENAS o output YAML. SALVE os arquivos atualizados.
```

---

## Comportamentos Obrigatorios

Estes comportamentos se aplicam durante TODA a investigacao (orquestrador + subagents):

- **PERGUNTE** quando falta informacao — nunca assuma
- **LEIA** o codigo antes de propor solucao — nunca adivinhe
- **BUSQUE** padroes similares no codebase — nunca trate como caso isolado sem verificar
- **DOCUMENTE** achados colaterais durante a exploracao — nunca descarte
- **TESTE** cada fix com teste automatizado — nunca confie em validacao manual
- **ESCALE** se encontrar problema estrutural/arquitetural — nunca ignore
- **CONSULTE** docs do projeto para convencoes existentes — nunca reinvente
- **CITE** fontes de evidencia para cada claim — nunca afirme sem prova
- **DESAFIE** suas proprias hipoteses — nunca aceite a primeira explicacao
- **APRENDA** registrando na knowledge base — nunca desperdice conhecimento

---

## Integracao AIOS (opcional)

> Ignore esta secao se nao estiver usando o framework AIOS.
> v8.0: Multi-model pipeline com subagents isolados por fase.

- O orquestrador roda o pipeline (classificacao → subagents → SDC bridge → docs → learn)
- Fast tracks por dominio Cynefin reduzem fases para problemas simples
- Knowledge base em `docs/qa/rca-knowledge/` cresce automaticamente
- Escalar problemas estruturais para `@architect` (somente se criterios atingidos na Fase 5)
- Criar stories de backlog + gerar handoff artifact para o SDC
- Usar `@devops *push` para push (unico agente autorizado para remote)
- Atualizar story file com resultados no Change Log
- Pipeline metrics registram custos e fallbacks
