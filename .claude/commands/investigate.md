# /investigate — Root Cause Analysis & Exploratory Investigation v7.0

> Metodologia de investigacao profunda de bugs e problemas.
> Portavel: funciona com qualquer LLM (Claude, GPT, Gemini, Codex, Cursor).
> Copie este arquivo para qualquer projeto.
>
> v7.0: Operationalization. Tudo do v6.0 MAIS: todas as features v6.0 agora
> REALMENTE executam em vez de apenas declaradas. Inclui:
> - Effectiveness review trigger automatico na Fase 0 (antes de classificar)
> - Pattern Matcher step-by-step com worked examples e scoring concreto
> - Dedup check com scoring numerico (error msg +40, file +30, tag +20, AP +10)
> - SOP outcome tracking em 3 pontos explicitos (Fase 2, Fase 9, audit-patterns)
> - Schema validation checklist obrigatoria na Fase 8 (19 campos)
> - Tag validation contra taxonomia com equivalence table
> - Evidence Summary com gate (pelo menos 1 E1 obrigatorio)
> - Barrier criticality contrafactual obrigatorio + "Fix This First" ranking
> - Escalation assessment obrigatorio na Fase 5 (4 criterios YES/NO)
> - Domain branching condicional real (Clear pula fases 2-6)
> - Anti-pattern recurrence auto-increment
> - Backlog finding materialization em docs/stories/backlog/
> - Handoff RCA→SDC com template YAML completo e trigger explicito
>
> **Estrutura auto-criada:** Na primeira execucao, o agente cria automaticamente
> os diretorios necessarios (`docs/qa/investigations/`, `docs/qa/rca-knowledge/sops/`,
> `docs/qa/known-anti-patterns.md`, `docs/stories/backlog/`) se nao existirem. Zero configuracao previa.

## Principio

**Nunca aplique band-aid.** Todo problema eh investigado ate a origem. Um guard defensivo eh protecao adicional, nunca o fix principal. Cada bug eh uma oportunidade de melhoria — a investigacao sempre produz mais do que entrou.

---

## Como Usar

Forneça um ou mais indicios de erro (screenshot, log, stack trace, descricao) e diga `/investigate` ou "investigue este problema".

---

## Fase 0 — Classificacao (Classifier Agent)

**Objetivo:** Classificar o problema ANTES de investigar para adaptar a estrategia.

0. **Effectiveness Review Trigger** (v7.0 — EXECUTA PRIMEIRO, ANTES de tudo):
   > Antes de classificar o problema novo, verificar se ha reviews pendentes.
   > Isso garante que a knowledge base esteja atualizada antes de qualquer Pattern Matching.

   **Step 1:** Ler `docs/qa/rca-knowledge/investigations.yaml`
   **Step 2:** Filtrar investigacoes com `effectiveness: pending` E `date` ha mais de 7 dias (comparar com data atual)
   **Step 3:** Para CADA investigacao pending ha >7 dias:
   - Verificar se os `symptoms` da investigacao apareceram em commits recentes: `git log --since="7 days ago" --grep="{keyword dos symptoms}"`
   - Verificar se `anti_patterns` da investigacao foram detectados novamente (grep por `search_pattern` do AP no codebase)
   - **Decidir:**
     - Nenhuma recorrencia encontrada → atualizar `effectiveness: resolved`
     - Variante do bug apareceu → atualizar `effectiveness: partial`
     - Mesmo bug recorreu → atualizar `effectiveness: ineffective`
   - Atualizar `effectiveness_reviewed_at: "{YYYY-MM-DD}"` com data de hoje
   - **SALVAR** `investigations.yaml` imediatamente
   - SE `ineffective`: emitir alerta inline:
     ```
     ALERTA: Fix ineficaz para {rca_id}!
     Sintomas recorrentes: {lista}
     Recomendacao: nova investigacao apos concluir esta
     ```

   **Step 4:** SE nenhuma investigacao pending ha >7 dias: registrar "Nenhum effectiveness review pendente" e prosseguir

   > **NOTA:** Effectiveness review tambem roda em `*audit-patterns` (Passo 1) e na Fase 9.
   > O trigger na Fase 0 garante que TODA nova investigacao comeca com knowledge base atualizada.

1. **Dominio Cynefin** — Classificar a natureza do problema:
   - **Clear:** Causa-efeito obvio, padrao conhecido (typo, import faltando, guard ausente)
   - **Complicated:** Requer expertise, mas analisavel (logica errada, race condition, integracao)
   - **Complex:** Causa-efeito so visivel em retrospecto (emergente, multi-sistema, feedback loops)
   - **Chaotic:** Sem causa-efeito perceptivel (corrupcao, estado inconsistente, dados conflitantes)

2. **Severidade** — Classificar o impacto:
   - **Critical:** Dados perdidos, seguranca comprometida, sistema down
   - **High:** Funcionalidade principal quebrada
   - **Medium:** Funcionalidade secundaria, workaround existe
   - **Low:** Cosmetico, edge case raro

3. **Scope** — Classificar a amplitude:
   - **Single-file:** 1 arquivo, causa localizada
   - **Multi-file:** 2-5 arquivos, mesmo modulo
   - **Cross-module:** Multiplos modulos/servicos
   - **Systemic:** Arquitetura, infraestrutura, processo

4. **Selecionar estrategia** conforme dominio (v7.0 — branching condicional REAL):

   | Dominio | Tecnicas | Fases Executadas |
   |---------|----------|-----------------|
   | Clear | Change Analysis + Quick Fix | 0→1→7→8→9 (fast track) |
   | Complicated | Change Analysis + FTA + Barrier | 0→1→2→3→5→6→7→8→9 |
   | Complex | Full pipeline (todas as tecnicas) | 0→1→2→3→4→5→6→7→8→9 |
   | Chaotic | Stabilize (0.5) + Full pipeline | 0→0.5→1→2→3→4→5→6→7→8→9 |

   **Instrucao condicional (EXECUTAR LITERALMENTE):**

   - **SE domain = Clear:**
     > **FAST-TRACK CLEAR:** Causa-efeito obvio. Pulando Fases 2, 3, 4, 5, 6.
     > Indo direto de Fase 1 (Archaeology) para Fase 7 (Solucao).
     - Completar Fase 0 (classificacao + dedup) → Fase 1 (coleta de dados)
     - **PULAR** Fases 2, 3, 4, 5, 6
     - Ir direto para Fase 7 (fix) → Fase 8 (documentacao) → Fase 9 (meta-learning)
     - Registrar no relatorio: "Domain: Clear — fast-track aplicado, fases 2-6 puladas"
     - Registrar no investigations.yaml: campo extra no relatorio indicando fast-track

   - **SE domain = Chaotic:**
     > **CHAOTIC PROTOCOL:** Estabilizar primeiro, depois full pipeline.
     > Aplicando Fase 0.5 (Stabilization) antes de prosseguir.
     - Adicionar +0.5 ao confidence scoring de cada match na Fase 2 (problemas caoticos sao menos previsiveis)
     - Completar TODAS as fases incluindo 0.5

   - **SE domain = Complicated ou Complex:** Seguir sequencia normal conforme tabela acima.

5. **Dedup Check** (v7.0 — scoring concreto) — ANTES de prosseguir, verificar se problema ja esta sendo tratado:

   **Step 1 — Buscar em 4 fontes:**
   - Ler `docs/qa/rca-knowledge/investigations.yaml` — TODAS as investigacoes
   - `git branch -a | grep -i fix/` — branches de fix ativas
   - `gh pr list --state open` — PRs abertos (se disponivel)
   - Ler `docs/stories/` — stories InProgress ou Done dos ultimos 30 dias

   **Step 2 — Para CADA investigacao anterior, calcular Dedup Score (0-100):**

   | Criterio | Matching | Pontos |
   |----------|---------|--------|
   | **Error message** | Substring do `symptoms` atual aparece em `symptoms` anterior | **+40** |
   | **File overlap** | 2+ arquivos em comum entre `files_affected` | **+30** |
   | **Tag overlap** | 2+ tags em comum entre `tags` | **+20** |
   | **Anti-pattern match** | Mesmo AP-ID em `anti_patterns` | **+10** |

   **Score = soma dos criterios que matched (max 100)**

   **Step 3 — Classificar e agir:**

   | Score | Classificacao | Acao |
   |-------|--------------|------|
   | **>= 90** | DUPLICATE | PARAR investigacao. Referenciar RCA existente. Nao criar novo registro. |
   | **50-89** | RELATED | Anotar cross-reference bidirecional. Continuar investigacao normalmente. |
   | **< 50** | NEW | Continuar normalmente. Nenhuma acao adicional. |

   **Step 4 — Cross-reference bidirecional (SE RELATED ou DUPLICATE):**
   1. Na investigacao NOVA: adicionar `related_rcas: ["{id_anterior}"]` e `dedup_status: related|duplicate`
   2. Na investigacao ANTERIOR: adicionar o ID da nova investigacao ao campo `related_rcas` em `investigations.yaml`
   3. **EDITAR o arquivo** `investigations.yaml` para adicionar a cross-reference na investigacao anterior

   **Em modo YOLO:** auto-selecionar "RELATED + continuar" se 50-89%, "PARAR" se >= 90%

   **Output obrigatorio:**
   ```
   DEDUP CHECK
   | RCA Anterior | Error Msg (+40) | File Overlap (+30) | Tag Overlap (+20) | AP Match (+10) | Score |
   |--------------|-----------------|--------------------|--------------------|----------------|-------|
   | {id}         | {sim/nao}       | {sim/nao} ({N})    | {sim/nao} ({N})    | {sim/nao}      | {N}%  |
   Resultado: {NEW | RELATED | DUPLICATE}
   ```

6. **Override manual** — O investigador pode reclassificar a qualquer momento se a classificacao inicial parece errada.

**Output da Fase 0:** Classificacao (domain, severity, scope) + estrategia selecionada + fases a executar + dedup status.

---

## Fase 0.5 — Stabilization Protocol (Chaotic Domain Only)

> Ativada APENAS quando dominio Cynefin = Chaotic. Pular para Fase 1 em todos os outros dominios.

**Objetivo:** Conter o impacto imediato ANTES de investigar. Em sistemas caoticos, agir primeiro, entender depois.

1. **Contencao imediata** — Escolher 1 ou mais acoes conforme contexto:
   - **Rollback:** `git revert` para ultimo commit estavel ou redeploy de versao anterior
   - **Feature flag:** Desabilitar funcionalidade afetada via flag (se disponivel)
   - **Hotfix minimo:** Guard/try-catch no ponto de crash (explicitamente temporario — NAO eh o fix final)
   - **Isolamento:** Desconectar componente afetado se possivel (circuit breaker, disable endpoint)

2. **Observacao pos-contencao** (5-15 minutos):
   - Sistema respondendo normalmente para usuarios nao-afetados?
   - Novos sintomas apareceram apos contencao?
   - Volume de erros estabilizou ou continua crescendo?
   - Dados estao sendo corrompidos?

3. **Criterios de estabilidade** — TODOS devem ser true para prosseguir:
   - [ ] Sistema operacional para usuarios nao-afetados
   - [ ] Crash/erro nao esta se propagando para outros modulos
   - [ ] Dados nao estao sendo corrompidos
   - [ ] Metodo de contencao esta segurando

4. **Transicao para Fase 1:**
   - Quando criterios de estabilidade atendidos → prosseguir
   - Registrar no relatorio: "CHAOTIC: contencao aplicada via {metodo} em {timestamp}"
   - O hotfix/workaround aplicado sera substituido pelo fix definitivo na Fase 7

**Output da Fase 0.5:** Metodo de contencao aplicado + status de estabilidade + timestamp.

---

## Fase 1 — Coleta de Dados (Archaeologist Agent)

**Objetivo:** Responder "o que mudou?" ANTES de perguntar "por que?".

1. **Git Forensics** — Coleta automatica:
   - `git log --since="last known good"` — commits recentes
   - `git diff main...HEAD` — mudancas na branch atual
   - `git blame {arquivo do erro}` — quem mudou o que
   - Dependency diff: mudancas em package.json/requirements.txt

2. **Reconstrucao de Timeline** — Ordenar eventos:
   - Commits ordenados por data
   - Config changes (se rastreadas)
   - Correlacao: "erro comecou em {data}, estes commits sao de {data-1}"

3. **Ranking de Changes** — Para cada change, calcular relevancia:
   - **Proximity (+3):** Toca arquivo mencionado no stack trace ou erro
   - **Recency (+2):** Commit < 24h antes do primeiro sintoma
   - **Scope (+1):** Change toca > 5 arquivos
   - **Dependency (+2):** Atualiza dependencia externa
   - **History (+1):** Autor tem historico de changes problematicos
   - Resultado: Top 5 changes mais suspeitos

4. **Mapeamento de Blast Radius** — Para cada change suspeito:
   - Que outros arquivos/modulos dependem?
   - Import chain analysis
   - "Se esse change causou o bug, o que mais pode estar afetado?"

**Output da Fase 1:** Top 5 suspects ranqueados + timeline + blast radius + dependency changes.

---

## Fase 2 — Pattern Matching (Pattern Matcher Agent)

**Objetivo:** Verificar se ja vimos problema similar e reutilizar conhecimento.

### Step 1 — Buscar na Knowledge Base (EXECUTAR LITERALMENTE)

1. **Ler** `docs/qa/rca-knowledge/investigations.yaml` — carregar TODAS as investigacoes
2. **Ler** `docs/qa/known-anti-patterns.md` — carregar todos os anti-patterns ativos
3. **Ler** `docs/qa/rca-knowledge/sops/*.yaml` — carregar todos os SOPs

Para CADA investigacao anterior, comparar com o problema atual e calcular score (Step 2).

### Step 2 — Calcular Confidence Score (v7.0 — Algoritmo Step-by-Step)

Para CADA investigacao anterior, calcular score em 5 dimensoes:

**Dimensao 1 — Symptom Match (max 30 pontos):**
- Comparar `symptoms` do problema atual com `symptoms` da investigacao anterior
- Exact error message substring match (ex: "'list' object has no attribute 'get'" aparece em ambos): **+30**
- Similar error type (ex: ambos sao TypeError mas mensagens diferentes): **+20**
- Same error category (ex: ambos sao AttributeError): **+10**
- Nenhum match: **+0**

**Dimensao 2 — Location Match (max 25 pontos):**
- Comparar `files_affected` do problema atual com `files_affected` da investigacao anterior
- Same function (mesmo arquivo + mesma funcao no stack trace): **+25**
- Same file (1+ arquivo em comum): **+20**
- Same module (mesmo diretorio, ex: `backend/services/stages/`): **+15**
- Same layer (mesmo prefixo, ex: `backend/`): **+10**
- Nenhum match: **+0**

**Dimensao 3 — Domain Match (max 15 pontos):**
- Comparar `domain` Cynefin do problema atual com `domain` da investigacao anterior
- Same domain: **+15**
- Different domain: **+0**

**Dimensao 4 — Fix Effectiveness (max 20 pontos, min -10):**
- Verificar `effectiveness` da investigacao anterior
- `resolved`: **+20** (fix comprovadamente funciona)
- `partial`: **+10** (fix funciona parcialmente)
- `pending`: **+0** (nao testado ainda)
- `ineffective`: **-10** (fix NAO funciona — cautela!)

**Dimensao 5 — Recurrence (max 10 pontos):**
- Verificar `anti_patterns` da investigacao anterior, buscar Recurrence em `known-anti-patterns.md`
- Recurrence >= 3: **+10**
- Recurrence == 2: **+5**
- Recurrence <= 1: **+0**

**Score final** = soma das 5 dimensoes (clamped 0-100)

**Ajuste por SOP outcome:** SE SOP da investigacao anterior tem `effectiveness_rate` calculado:
- effectiveness_rate < 50% → score capped em 60 (nao pode ser fast-track)
- effectiveness_rate < 30% → score capped em 40

### Worked Example (2 RCAs existentes)

**Cenario:** Novo bug com sintoma "'list' object has no attribute 'get'" em stage5.

Comparando com `rca-2026-03-29-analyzing-page`:
- Symptom: "'list' object has no attribute 'get'" = exact substring match → **+30**
- Location: stage5_template_generation.py em comum → **+20**
- Domain: ambos complicated → **+15**
- Effectiveness: pending → **+0**
- Recurrence: AP-001 com recurrence 4 → **+10**
- **Score = 75** → Ponto de partida, continuar investigacao

Comparando com `rca-2026-03-31-stage5-document-trees-contract`:
- Symptom: "'list' object has no attribute 'get'" = exact substring match → **+30**
- Location: stage5_template_generation.py + stage3 em comum → **+20**
- Domain: ambos complicated → **+15**
- Effectiveness: pending → **+0**
- Recurrence: AP-003 com recurrence 1 → **+0**
- **Score = 65** → Ponto de partida, continuar investigacao

### Step 3 — SOP Fast-Track Decision

Selecionar a investigacao com MAIOR score. Depois decidir:

- **Score > 80% E SOP existe:** propor fast-track (ver Step 4)
- **Score 50-80%:** usar como ponto de partida, continuar investigacao normalmente
- **Score < 50%:** registrar como "problema novo", continuar investigacao normal

### Step 4 — SOP Fast-Track (SE score > 80% E SOP existe)

**PROPOR fast-track explicitamente:**
```
SOP FAST-TRACK DISPONIVEL
SOP: {sop_id} — {sop_name}
Confidence: {score}%
Effectiveness rate: {rate}% (ou "N/A" se nunca aplicado)
Fix sugerido: {resumo do fix da SOP}
Opcoes:
  ACEITAR → Pular para Fase 7 usando SOP como ponto de partida
  REJEITAR → Continuar pipeline normal (Fase 3+)
```

- **Aceitar:** Carregar fix_steps da SOP, pular diretamente para Fase 7 (Solucao)
- **Rejeitar:** Continuar pipeline normalmente a partir da Fase 3
- **Em modo YOLO:** Auto-aceitar se confidence >= 90%, perguntar se 80-89%
- **BLOQUEIO:** SOP com effectiveness_rate < 50% NAO pode ser oferecido como fast-track

**SE fast-track aceito:** Incrementar `times_applied` no SOP IMEDIATAMENTE (ver Fase 9 SOP Outcome Tracking).

### Step 5 — Anti-pattern Supersession Check

- SE anti-pattern do match tem campo `superseded_by`: seguir cadeia ate o anti-pattern mais recente
- Priorizar SOP do anti-pattern mais recente na cadeia
- Alertar se SOP esta `deprecated` (associada a anti-pattern superseded)

### Output OBRIGATORIO da Fase 2

```markdown
## Pattern Matching Results

### Matches Found
| RCA ID | Score | Symptom | Location | Domain | Effectiveness | Recurrence | SOP |
|--------|-------|---------|----------|--------|---------------|------------|-----|
| {id}   | {N}%  | +{N}    | +{N}     | +{N}   | +{N}          | +{N}       | {sop_id or "none"} |

### Best Match: {rca_id} — Score {N}%
### Decision: {FAST_TRACK_ACCEPTED | FAST_TRACK_REJECTED | CONTINUE_INVESTIGATION | NEW_PROBLEM}
### SOP Fast-Track: {ACCEPTED: sop_id | REJECTED: reason | N/A}
```

**Nota:** Se nenhuma investigacao anterior existe (knowledge base vazia), registrar "Problema novo — nenhum match possivel" e seguir para Fase 3.

---

## Fase 3 — Analise Causal (Causal Reasoner Agent)

**Objetivo:** Construir grafo causal multi-branch com logica AND/OR.

> Evolucao do 5 Whys linear: em vez de 1 cadeia (A→B→C→raiz), explora
> multiplas cadeias em paralelo com logica formal.

1. **Construir grafo causal** a partir dos dados do Archaeologist:
   - **Effect Node:** Bug observado (raiz do grafo)
   - **Intermediate Nodes:** Condicoes intermediarias derivadas do stack trace
   - **Root Nodes:** Causas raiz candidatas derivadas dos top suspects
   - **Logic Gates:**
     - **AND:** Duas condicoes precisam ocorrer juntas para causar o efeito
     - **OR:** Qualquer uma das condicoes independentemente causa o efeito

2. **Evidence tagging** — Cada node recebe nivel de evidencia:
   - **Confirmed:** Reproduzido por teste ou git bisect
   - **Correlated:** Dados sugerem forte correlacao
   - **Hypothesized:** Teoria plausivel sem evidencia direta

3. **Classificar root causes:**
   - **Primary:** Causa direta, maior evidencia, mais proxima do efeito
   - **Contributing factors:** Defesas ausentes, gaps de teste, fatores habilitadores

4. **Profundidade maxima:** 5 niveis por default (extensivel). Parar quando atingir causa actionable.

**Output da Fase 3:** Grafo causal com nodes + AND/OR gates + evidence tags + root causes (primary + contributing).

---

## Fase 4 — Desafio de Hipoteses (Hypothesis Challenger Agent)

**Objetivo:** Desafiar ativamente cada hipotese com contra-evidencia e counterfactual.

> Ativada apenas para dominio Complex/Chaotic. Complicated usa challenge leve.

1. **Busca de contra-evidencia** — Para cada root cause candidato:
   - Funcionalidade similar funciona em outro lugar? Por que?
   - O bug existia ANTES do change suspeito?
   - Reverter o change (mentalmente) resolveria?

2. **Analise counterfactual** — "Se esta causa NAO existisse, o bug teria acontecido?"
   - Se sim → causa eh contributing, nao primary
   - Se nao → causa eh likely primary
   - Se incerto → precisa mais evidencia

3. **Hipoteses alternativas** — Gerar pelo menos 1 alternativa para cada primary candidate:
   - Que OUTRA explicacao cobriria os mesmos sintomas?
   - Comparar evidencia: qual hipotese tem mais suporte?

4. **Verdict** por hipotese:
   - **CONFIRMED:** Sobreviveu ao challenge, evidencia forte (confidence > 0.8)
   - **WEAKENED:** Contra-evidencia parcial, precisa investigar mais (0.3-0.8)
   - **REFUTED:** Contra-evidencia forte, descartar (< 0.3)
   - **INSUFFICIENT:** Nem evidencia nem contra-evidencia

5. **Regras de challenge:**
   - **"Operator error" nunca eh resposta final** — sempre rastrear gap sistemico
   - Cada claim deve citar fonte (commit, teste, log)
   - Hipotese sem evidencia = INSUFFICIENT, nao CONFIRMED

**Output da Fase 4:** Challenge results com verdicts + confidence scores + final ranking pos-challenge.

---

## Fase 5 — Analise de Barreiras (Barrier Analyst Agent)

**Objetivo:** Analisar TODAS as defesas que deveriam ter pego o bug mas falharam.

> Modelo Swiss Cheese (James Reason): incidentes acontecem quando os buracos
> de multiplas camadas de defesa se alinham.

1. **Analisar 6 camadas de defesa:**

   | Camada | O que verificar | Status possivel |
   |--------|----------------|-----------------|
   | Code Level | Type guards, assertions, input validation | worked / failed / bypassed / absent |
   | Test Level | Unit, integration, E2E para funcao afetada | worked / failed / absent + coverage % |
   | Static Analysis | Linter rules, type checker, custom rules | worked / failed / absent |
   | CI/CD Level | Quality gates, pre-commit hooks, CodeRabbit | worked / failed / absent |
   | Monitoring | Error tracking, health checks, logs | worked / failed / absent |
   | Process Level | Code review humano, QA gate, ACs | worked / failed / absent |

2. **Swiss Cheese Summary** — Mostrar como os buracos se alinharam:
   - "Code guard absent + test absent + no linter rule = bug reached production"

3. **Test Gap Analysis** (v6.0) — Metodologia step-by-step:

   **Step 1 — Mapear:** Encontrar testes relacionados a funcao/modulo afetado:
   - Grep por imports do modulo afetado em arquivos de teste (`*.spec.ts`, `*_test.py`, `test_*.py`)
   - Grep por nome da funcao/classe em `describe()`, `it()`, `test_*`, `def test_`
   - Verificar coverage reports se disponiveis
   - **Output:** Lista de testes que tocam o codigo afetado

   **Step 2 — Classificar cada teste:**
   - **(a) Nao relacionado:** Teste toca o modulo mas nao o code path do bug → ignorar
   - **(b) Relacionado e falhou:** Teste detectou o bug (ou falharia com dados do bug) → ok, barreira funcionou
   - **(c) Relacionado e passou (GAP!):** Teste deveria ter detectado o bug mas nao detectou → analisar causa

   **Step 3 — Diagnosticar causa** de cada gap usando decision tree:
   ```
   Teste exercita o code path do bug?
     NAO → Causa: CENARIO NAO COBERTO
     SIM → Teste usa mock no ponto onde o bug ocorre?
       SIM → Causa: MOCK INCORRETO (mock esconde comportamento real)
       NAO → Assertion valida o aspecto afetado pelo bug?
         NAO → Causa: ASSERTION FRACA (verifica resultado mas nao invariante)
         SIM → Dados de entrada disparam o bug?
           NAO → Causa: DADOS INSUFICIENTES (input nao cobre edge case)
           SIM → Causa: OUTRO (documentar especificamente)
   ```

   **Step 4 — Gerar recomendacao** por gap:
   ```
   TEST GAP: {test_file}:{test_name}
   Classificacao: GAP (passou quando deveria ter falhado)
   Causa: {cenario_nao_coberto | mock_incorreto | assertion_fraca | dados_insuficientes}
   Recomendacao: {descricao especifica do que adicionar/corrigir}
   Prioridade: {HIGH se cenario principal, MEDIUM se edge case}
   ```

   - **Passar test gaps como input obrigatorio** para Fase 7 — testes corretivos sao obrigatorios

4. **Barrier Criticality Scoring** (v7.0 — contrafactual OBRIGATORIO):

   Para CADA barreira com status `failed`, `bypassed`, ou `absent`, responder a pergunta contrafactual:

   > "Se APENAS esta barreira estivesse presente e funcionando corretamente, o bug teria sido PREVENIDO?"

   | Resposta | Criticality | Significado |
   |----------|-------------|-------------|
   | "Sim, preveniria sozinha" | **HIGH** | Esta barreira isolada teria impedido o bug → fix prioritario |
   | "Reduziria impacto/detectaria mais cedo" | **MEDIUM** | Teria limitado blast radius ou antecipado deteccao |
   | "Alertaria mas nao impediria" | **LOW** | Contribuiria mas nao seria suficiente sozinha |

   **Tabela OBRIGATORIA no relatorio (todas as 6 camadas):**

   ```
   | # | Camada          | Status  | Criticality | Contrafactual (resposta completa)           |
   |---|-----------------|---------|-------------|---------------------------------------------|
   | 1 | Code Level      | absent  | HIGH        | Guard isinstance teria impedido crash       |
   | 2 | Test Level      | absent  | HIGH        | Teste com list input teria detectado na CI  |
   | 3 | Static Analysis | absent  | LOW         | Linter alertaria mas nao bloquearia merge   |
   | 4 | CI/CD Level     | worked  | —           | N/A (barreira funcionou)                    |
   | 5 | Monitoring      | absent  | MEDIUM      | Error tracking teria alertado antes do user |
   | 6 | Process Level   | failed  | MEDIUM      | Code review deveria ter visto o gap         |
   ```

   **"Fix This First" Ranking** — Ordenar barreiras por criticality (HIGH primeiro):
   ```
   FIX THIS FIRST:
   1. [HIGH] Code Level — Adicionar isinstance guard (preveniria bug sozinha)
   2. [HIGH] Test Level — Adicionar teste com dados list (detectaria na CI)
   3. [MEDIUM] Monitoring — Configurar error tracking para stage crashes
   4. [MEDIUM] Process Level — Adicionar checklist de type safety no code review
   5. [LOW] Static Analysis — Avaliar regra de linter para .get() sem guard
   ```

   > **IMPORTANTE:** Fase 7 DEVE implementar fixes na ordem do ranking "Fix This First".
   > Barreiras HIGH sao obrigatorias. Barreiras MEDIUM sao recomendadas. Barreiras LOW sao opcionais.

5. **Gerar recomendacoes** por urgencia (priorizadas pelo ranking "Fix This First"):
   - **Immediate:** Fechar barreiras HIGH — obrigatorio na Fase 7
   - **Short-term:** Registrar anti-pattern, fechar barreiras MEDIUM
   - **Long-term:** Fechar barreiras LOW, aumentar coverage, adicionar ferramentas

6. **Escalation Assessment** (v7.0 — OBRIGATORIO, nao pode ser pulado):

   APOS completar barrier analysis, avaliar OBRIGATORIAMENTE os 4 criterios abaixo.
   Preencher a tabela com YES/NO e evidencia concreta para cada criterio.
   **NAO pular esta avaliacao** mesmo em modo YOLO.

   | Criterio | Pergunta | Resposta | Evidencia |
   |----------|----------|----------|-----------|
   | **Scope amplo** | Bug afeta 3+ modulos/stages? | YES/NO | {listar modulos afetados} |
   | **Design pattern** | Root cause eh uso incorreto de design pattern? | YES/NO | {qual pattern e como esta incorreto} |
   | **Interface change** | Fix requer mudanca de interface/contrato entre componentes? | YES/NO | {quais interfaces mudam} |
   | **Barrier systemic** | Barrier analysis mostra falha em 4+ camadas de defesa? | YES/NO | {quantas camadas falharam: N/6} |

   **SE qualquer criterio = YES:** Gerar escalation prompt no relatorio:
   ```
   ESCALACAO PARA @ARCHITECT RECOMENDADA
   Criterios atingidos: {lista dos criterios YES}
   Evidencia: {resumo da evidencia}
   Impacto estimado: {scope do problema}
   Sugestao: {acao recomendada}
   ```

   **SE todos criterios = NO:** Registrar no relatorio: "Escalation assessment: nenhum criterio atingido — escalacao nao necessaria."

   **Em modo YOLO:** Registrar a avaliacao no relatorio mas NAO escalar automaticamente. Deixar o prompt para o operador decidir na proxima interacao.

**Output da Fase 5:** Barreiras analisadas por camada + criticality scoring + Swiss Cheese alignment + test gaps + recomendacoes priorizadas + escalation assessment.

---

## Fase 6 — Classificacao de Evidencia (Evidence Grading)

**Objetivo:** Classificar cada achado por nivel de prova para priorizar fixes por certeza.

1. **4 niveis de evidencia:**

   | Nivel | Nome | Criterio | Confidence |
   |-------|------|----------|------------|
   | E1 | **Confirmed** | Reproduzido por teste ou git bisect | 0.90-1.0 |
   | E2 | **Correlated** | Dados sugerem forte correlacao | 0.60-0.89 |
   | E3 | **Hypothesized** | Teoria plausivel sem evidencia direta | 0.30-0.59 |
   | E4 | **Speculative** | Possibilidade remota | 0.00-0.29 |

2. **Evidence chain obrigatoria** — Cada claim cita pelo menos 1 source:
   - Source types: `git_diff`, `git_bisect`, `test_reproduction`, `log_analysis`, `code_analysis`, `coverage_report`, `manual_verification`

3. **Agrupar achados por nivel** no relatorio:
   - E1 (Confirmed) primeiro — action items prioritarios
   - E2 (Correlated) segundo — investigar mais ou fixar
   - E3 (Hypothesized) — registrar, investigar se tempo permitir
   - E4 (Speculative) — apenas registrar, sem action item
   - Achados refutados na fase de challenge: listados como "Discarded" com motivo

4. **Evidence Summary Table** (v7.0 — OBRIGATORIA):

   Produzir tabela com TODOS os achados da investigacao. Cada linha = 1 claim.

   ```
   ## Evidence Summary

   | # | Claim | Level | Confidence | Sources |
   |---|-------|-------|------------|---------|
   | 1 | {descricao do achado} | E1_confirmed | 0.95 | git_diff (commit abc), test_reproduction (test_xyz.py) |
   | 2 | {descricao do achado} | E2_correlated | 0.75 | code_analysis (file:line), log_analysis (error.log) |
   | 3 | {descricao do achado} | E3_hypothesized | 0.40 | code_analysis (file:line) |
   | 4 | {achado refutado} | Discarded | — | Refutado na Fase 4: {motivo} |
   ```

   **Sources validas:** `git_diff`, `git_bisect`, `test_reproduction`, `log_analysis`, `code_analysis`, `coverage_report`, `manual_verification`, `stack_trace`

   **Gate:** Pelo menos 1 achado com nivel E1_confirmed eh OBRIGATORIO para prosseguir para Fase 7.
   - SE nenhum E1 existe: investigacao precisa de mais evidencia — buscar teste reprodutor ou git bisect antes de prosseguir.
   - **Excecao:** Em dominio Chaotic (apos estabilizacao), pode-se prosseguir com E2 se E1 nao eh possivel — documentar motivo.

**Output da Fase 6:** Evidence Summary Table com todos os achados + confidence + sources. Pelo menos 1 E1 obrigatorio.

---

## Fase 7 — Solucao

**Objetivo:** Resolver na origem e proteger nos pontos de consumo.

1. **Fix principal** — Corrigir na ORIGEM do dado (onde eh gerado/transformado incorretamente).
2. **Guards defensivos** — Adicionar protecao nos consumidores como camada ADICIONAL (nunca como unico fix).
3. **Testes (OBRIGATORIO)** — Para CADA fix:
   - Teste que reproduz o bug original (DEVE existir, sem excecao)
   - Teste que valida o contrato na origem
   - Testes de regressao para cenarios relacionados
   - SE nao eh possivel testar automaticamente (ex: fix puramente visual), documentar o motivo no relatorio
4. **Corrigir test gaps** (v5.0) — Para CADA test gap identificado na Fase 5:
   - Corrigir o teste existente que deveria ter detectado o bug
   - Adicionar cenarios de teste ausentes
   - Remover/corrigir mocks que escondem comportamento real
   - Fortalecer assertions fracas
5. **Implementar recomendacoes immediate** seguindo o ranking "Fix This First" da Fase 5 (barreiras HIGH sao obrigatorias, MEDIUM recomendadas).
6. **Validar** — Rodar todos os testes existentes + novos. Zero regressao.

**IMPORTANTE:** Um fix sem teste nao esta completo. Testes sao parte da solucao, nao um passo separado.

**Output da Fase 7:** Codigo implementado + testes + validacao.

---

## Fase 8 — Documentacao & Backlog

**Objetivo:** Documentar tudo para que o conhecimento nao se perca.

### Documentacao de Bugs — Abordagem Hibrida

Antes de produzir o relatorio, classificar cada bug fixado:

| Classificacao | Criterio | Acao |
|--------------|----------|------|
| **Trivial** | 1 arquivo, 1 linha | Sem story. Documentar no relatorio. |
| **Minor** | 1-2 arquivos, fix comportamental | Story retroativa status=Done. |
| **Significativo** | >2 arquivos, muda comportamento | Story criada ANTES do fix (na Fase 7). |

Se multiplos bugs significativos da mesma investigacao: 1 story umbrella com cada bug como AC.

### Relatorio de Investigacao

Produzir um **Relatorio de Investigacao** com:

### 1. Classificacao (Fase 0)
- Dominio Cynefin, severidade, scope
- Estrategia selecionada

### 2. Archaeology (Fase 1)
- Top suspects com relevance scores
- Timeline reconstruida
- Blast radius

### 3. Pattern Matches (Fase 2)
- Investigacoes similares encontradas (ou "problema novo")
- SOPs sugeridos

### 4. Grafo Causal (Fase 3)
- Nodes, gates AND/OR, evidence tags
- Root causes: primary + contributing factors

### 5. Challenge Results (Fase 4, se executada)
- Hipoteses confirmadas, enfraquecidas, refutadas
- Counterfactual analysis
- Final ranking com confidence

### 6. Barrier Analysis (Fase 5)
- 6 camadas analisadas com status
- Swiss Cheese alignment
- Recomendacoes (immediate / short-term / long-term)

### 7. Evidence Summary (Fase 6)
- Achados agrupados por E1→E2→E3→Discarded
- Sources citadas para cada claim

### 8. Fix Aplicado (Fase 7)
- O que foi corrigido na origem
- Guards defensivos adicionados
- Recomendacoes immediate implementadas

### 9. Testes Criados (OBRIGATORIO)
Listar cada arquivo de teste criado e o que ele valida:
- `test_file.spec.ts` — Valida que {cenario}
- SE zero testes foram criados: justificativa explicita

### 10. Achados Colaterais (Backlog)
Para cada achado durante a exploracao:

| ID | Tipo | Severidade | Descricao | Localizacao | Acao Sugerida |
|----|------|-----------|-----------|-------------|---------------|
| F-1 | Bug | CRITICAL | ... | arquivo:linha | ... |

### 10b. Backlog Finding Materialization (v7.0)

**SE achados colaterais existem (tabela acima tem 1+ finding):** Para CADA achado, criar story draft em `docs/stories/backlog/`.

**Step 1:** Para cada finding F-{N}, criar arquivo `docs/stories/backlog/backlog-{rca-slug}-{N}.md`:

```markdown
---
id: backlog-{rca-slug}-{N}
title: "{acao sugerida do finding}"
type: {bug|improvement|tech-debt}
status: Draft
priority: {derivar da severidade: CRITICAL→critical, HIGH→high, MEDIUM→medium, LOW→low}
source_rca: "{rca-id}"
source_finding: "F-{N}"
---

# Backlog — {titulo}

## Origem
Achado colateral da investigacao [{rca-id}]({path do relatorio}).

## Descricao
{descricao do finding}

## Localizacao
{localizacao do finding}

## Acao Sugerida
{acao sugerida do finding}

## Prioridade
{severidade} — derivada do achado colateral.

## Notas
Este draft foi auto-gerado pela Fase 8 do `/investigate`.
Requer validacao por @po antes de entrar no backlog oficial.
```

**Step 2:** Referenciar os drafts criados no handoff artifact (secao 14):
- Para cada draft, adicionar `story_draft_path: "docs/stories/backlog/backlog-{rca-slug}-{N}.md"` no handoff

**SE nenhum achado colateral:** Pular esta secao.

### 11. Anti-Pattern Registrado
SE o arquivo `docs/qa/known-anti-patterns.md` existir no projeto, registrar o padrao encontrado.

**Campos obrigatorios do anti-pattern (v6.0):**
- ID (AP-XXX sequencial)
- Status (`active`)
- Recurrence (count de incidentes)
- Encontrado em (referencia a RCA)
- Descricao
- `search_pattern` (regex para deteccao automatica — **obrigatorio quando possivel**)
- Scope (quais arquivos/diretorios buscar)
- Severidade
- Guard esperado
- SOP (referencia ao SOP associado ou `null`)

**Recurrence Auto-Increment** (v7.0):
- **SE o anti-pattern JA EXISTE** (root cause matched um AP existente):
  1. Abrir `docs/qa/known-anti-patterns.md`
  2. Encontrar o AP-ID referenciado (ex: AP-001)
  3. Incrementar `Recurrence` (+1)
  4. Adicionar referencia desta RCA ao campo "Encontrado em" (append, nao substituir)
  5. **SALVAR o arquivo imediatamente**
  6. Registrar no relatorio: "AP-{ID} recurrence incrementado para {N} (nova instancia detectada)"

- **SE o anti-pattern eh NOVO:** Criar com Recurrence: 1 e todos os campos obrigatorios acima.

**Supersession (v5.0):**
- SE o anti-pattern encontrado eh uma evolucao de anti-pattern anterior (a causa raiz eh mais profunda):
  - Adicionar `superseded_by: AP-{novo}` no anti-pattern anterior
  - Marcar anti-pattern anterior como `status: superseded`
  - Marcar SOP associada ao anti-pattern anterior como `deprecated: true` com `replaced_by: sop-{novo}`
  - O anti-pattern superseded NAO eh removido (preservar historico)
  - Documentar no relatorio: "AP-{antigo} superseded por AP-{novo} — causa raiz mais profunda identificada"

### 12. Test Gap Analysis (v6.0)
Incluir tabela completa de test gaps da Fase 5:

| Teste | Classificacao | Causa | Recomendacao | Prioridade |
|-------|--------------|-------|--------------|------------|
| {test_file}:{test_name} | GAP | {causa} | {fix especifico} | HIGH/MEDIUM |

### 13. Barrier Criticality Ranking (v6.0)
Incluir ranking de barreiras por criticality da Fase 5:

| Camada | Status | Criticality | Contrafactual |
|--------|--------|-------------|---------------|
| ... | ... | HIGH/MEDIUM/LOW | ... |

"Fix This First: {barreira com maior criticality}"

### 14. Handoff RCA→SDC (v7.0 — artifact obrigatorio)

**Trigger:** SE a secao "10. Achados Colaterais (Backlog)" tem 1+ finding OU qualquer recomendacao de story de backlog.

**Step 1:** Verificar se diretorio `.aios/handoffs/` existe. Se nao, criar com `.gitkeep`.

**Step 2:** Criar arquivo `.aios/handoffs/handoff-rca-to-sdc-{YYYY-MM-DD}-{slug}.yaml` com template COMPLETO:

```yaml
# Handoff RCA→SDC — Auto-generated by /investigate Fase 8
# Consumer: @sm (story creation) or @aios-master (orchestration)
handoff:
  from_agent: "@qa"
  to_agent: "@sm"
  type: "rca-to-sdc"
  generated_at: "{YYYY-MM-DD}T{HH:MM:SS}"
  consumed: false
  consumed_by: null
  consumed_at: null

  investigation:
    id: "rca-{date}-{slug}"
    report: "docs/qa/investigations/rca-{date}-{slug}.md"
    domain: "{cynefin domain}"
    severity: "{severity}"

  backlog_items:
    - id: "F-1"
      title: "{titulo descritivo da story sugerida}"
      type: "bug | improvement | tech-debt"
      priority: "high | medium | low"
      context: "{resumo do achado em 1-2 frases}"
      source_finding: "F-1"
      suggested_scope: "{arquivos/modulos afetados}"
      story_draft_path: null  # populated by Story 23.14 if draft created

  architectural_findings: []  # populated if escalation criteria met

  notes: "{observacoes adicionais para o consumer}"
```

**Step 3:** Registrar no relatorio: "Handoff gerado: `.aios/handoffs/handoff-rca-to-sdc-{date}-{slug}.yaml`"

**SE nenhum backlog item:** NAO gerar handoff. Registrar no relatorio: "Nenhum achado colateral — handoff nao necessario."

### 15. Escalation Assessment (v6.0)
Avaliar se problema requer escalacao para @architect usando criterios codificados:

| Criterio | Descricao | Atingido? |
|----------|-----------|-----------|
| **Scope amplo** | Bug afeta 3+ modulos/stages | sim/nao |
| **Design pattern** | Root cause eh uso incorreto de design pattern | sim/nao |
| **Interface change** | Fix requer mudanca de interface/contrato entre componentes | sim/nao |
| **Barrier systemic** | Barrier analysis mostra falha em 4+ camadas de defesa | sim/nao |

SE qualquer criterio = sim: gerar escalation prompt:
```
ESCALACAO PARA @ARCHITECT
Criterio atingido: {criterio}
Evidencia: {resumo}
Impacto estimado: {scope do problema}
Sugestao: {acao recomendada}
```

### 16. Recomendacoes
- Contratos que deveriam ser formalizados
- Mudancas arquiteturais sugeridas (se aplicavel)
- Tags utilizadas (devem seguir taxonomia em `docs/qa/rca-knowledge/tag-taxonomy.yaml`)

### 16b. Tag Validation (v7.0 — OBRIGATORIA antes do registro)

**Step 1:** Ler `docs/qa/rca-knowledge/tag-taxonomy.yaml` e extrair todas as tags validas de todas as categorias.

**Step 2:** Para CADA tag que sera usada na investigacao, verificar:
- Tag existe em alguma categoria de `tag-taxonomy.yaml`? → VALIDA, usar como esta
- Tag NAO existe? → Verificar se ha equivalente no vocabulario:

  | Tag invalida | Tag valida equivalente |
  |-------------|----------------------|
  | `guard` | `guard_missing` (root_cause_category) |
  | `isinstance` | `guard_added` (fix_type) |
  | `wireframe` | `wireframe_divergence` (root_cause_category) |
  | `sse_summary` | `sse_payload` (root_cause_category) |
  | `shared_context` | `data_contract` (root_cause_category) |
  | `pipeline` | `backend_stage` (affected_layer) |

- SE equivalente existe → substituir pela tag valida
- SE nenhum equivalente → usar com prefixo `custom:` (ex: `custom:pdf_parsing`)
- SE tag custom ja usada 2+ vezes no historico → promover para taxonomia oficial (adicionar a `tag-taxonomy.yaml`)

**Step 3:** Listar tags finais no relatorio com categoria de cada uma.

### 17. Schema Validation Checklist (v7.0 — OBRIGATORIA)

**ANTES de registrar a investigacao em `investigations.yaml` (Fase 9),** validar que TODOS os campos obrigatorios v6.0 estao presentes. **REJEITAR registro se qualquer campo estiver ausente.**

| Campo | Tipo | Obrigatorio | Validacao |
|-------|------|-------------|-----------|
| `id` | string | SIM | Formato: `rca-{YYYY-MM-DD}-{slug}` |
| `date` | string | SIM | Formato: `YYYY-MM-DD` |
| `symptoms` | array | SIM | Pelo menos 1 item |
| `domain` | string | SIM | Um de: `clear`, `complicated`, `complex`, `chaotic` |
| `severity` | string | SIM | Um de: `critical`, `high`, `medium`, `low` |
| `scope` | string | SIM | Um de: `single-file`, `multi-file`, `cross-module`, `systemic` |
| `root_causes` | array | SIM | Pelo menos 1 item com `pattern`, `location`, `evidence_level` |
| `contributing_factors` | array | SIM | Pelo menos 1 item |
| `fix_approach` | string | SIM | Nao vazio |
| `files_affected` | array | SIM | Pelo menos 1 item |
| `tags` | array | SIM | Pelo menos 1 tag, todas validadas contra `tag-taxonomy.yaml` |
| `effectiveness` | string | SIM | Valor inicial: `pending` |
| `effectiveness_reviewed_at` | string/null | SIM | Valor inicial: `null` |
| `sop_generated` | string/null | SIM | Path ou `null` |
| `sop_fast_track_used` | boolean | SIM | `true` ou `false` |
| `confidence_score` | number/null | SIM | 0-100 ou `null` (se primeiro RCA) |
| `dedup_status` | string | SIM | Um de: `new`, `related`, `duplicate` |
| `related_rcas` | array/null | SIM | Lista de IDs ou `null` |
| `report` | string | SIM | Path do relatorio |

**Procedimento:**
1. Montar o registro completo usando o template acima
2. Verificar cada campo contra a tabela — campo ausente = PARAR e preencher
3. Validar tags contra `docs/qa/rca-knowledge/tag-taxonomy.yaml` (ver secao Tag Validation)
4. So entao adicionar ao `investigations.yaml`

**Template pre-preenchido para copiar:**
```yaml
- id: "rca-{date}-{slug}"
  date: "{YYYY-MM-DD}"
  symptoms:
    - "{sintoma 1}"
  domain: "{clear|complicated|complex|chaotic}"
  severity: "{critical|high|medium|low}"
  scope: "{single-file|multi-file|cross-module|systemic}"
  root_causes:
    - pattern: "{pattern_name}"
      location: "{area/module}"
      evidence_level: "{E1_confirmed|E2_correlated|E3_hypothesized}"
  contributing_factors:
    - "{fator 1}"
  fix_approach: "{descricao do fix}"
  files_affected:
    - "{file1}"
  tags:
    - "{tag1}"  # MUST be from tag-taxonomy.yaml or use custom: prefix
  effectiveness: pending
  effectiveness_reviewed_at: null
  sop_generated: null
  sop_fast_track_used: false
  confidence_score: null  # populate from Fase 2 Pattern Matcher
  dedup_status: new  # populate from Fase 0 Dedup Check
  related_rcas: null  # populate from Fase 0 Dedup Check
  report: "docs/qa/investigations/rca-{date}-{slug}.md"
```

---

## Fase 9 — Meta-Learning (Meta-Learner Agent)

**Objetivo:** Aprender com cada investigacao para que a proxima seja mais rapida.

1. **Effectiveness Review PRIMEIRO** (v6.0 — enforcement obrigatorio):
   > Antes de qualquer outro step, verificar fixes anteriores. Isso garante que o knowledge base
   > esteja atualizado ANTES de registrar a nova investigacao e analisar tendencias.
   - Buscar investigacoes com `effectiveness: pending` ha mais de **7 dias**
   - Para cada: verificar se bug recorreu:
     - Grep por mesmos sintomas/tags em commits recentes (ultimos 7 dias)
     - Verificar se mesmo anti-pattern foi detectado novamente
     - Consultar `*audit-patterns` se search_pattern disponivel
   - Atualizar campo `effectiveness`:
     - `resolved` — Nenhuma recorrencia detectada
     - `partial` — Recorrencia parcial (variante do bug)
     - `ineffective` — Mesmo bug recorreu
   - Registrar `effectiveness_reviewed_at` com data da revisao
   - SE `ineffective`: **ALERTA** — "Fix ineficaz detectado. Recomendacao: nova investigacao com `*investigate`"
   - **Incluir secao "Effectiveness Backlog"** no relatorio se houver pendencias revisadas
   - **Nota:** Review pode ser executado standalone via `*audit-patterns` (nao apenas durante RCA)

2. **Registrar investigacao** na knowledge base:
   - Investigation record com: date, symptoms, domain, root_causes, fix_approach, files_affected, tags, effectiveness, effectiveness_reviewed_at
   - **Tags devem seguir taxonomia** em `docs/qa/rca-knowledge/tag-taxonomy.yaml` (v6.0)
   - Gerar SOP se padrao novo detectado (steps executaveis para resolver problema similar)
   - Registrar anti-pattern se descoberto

3. **SOP Outcome Tracking** (v7.0 — 3 pontos de atualizacao explicitos):

   **Ponto A — Fase 2 (Pattern Matcher), ao aceitar fast-track:**
   - Abrir arquivo SOP em `docs/qa/rca-knowledge/sops/{sop_id}.yaml`
   - Incrementar `times_applied` (+1)
   - Atualizar `last_applied: "{YYYY-MM-DD}"` com data de hoje
   - Atualizar `last_investigation: "{rca-id}"` com ID da investigacao atual
   - **SALVAR o arquivo imediatamente** — nao esperar Fase 9

   **Ponto B — Fase 9 (Meta-Learner), ao revisar effectiveness de investigacao ANTERIOR que usou SOP:**
   - Para cada investigacao com `sop_fast_track_used: true` sendo revisada:
     - Identificar SOP usado via `sop_generated` ou pelo relatorio
     - Abrir `docs/qa/rca-knowledge/sops/{sop_id}.yaml`
     - SE effectiveness = `resolved`: incrementar `times_effective` (+1)
     - SE effectiveness = `partial` ou `ineffective`: incrementar `times_ineffective` (+1)
     - Recalcular: `effectiveness_rate = times_effective / times_applied` (arredondar 2 casas)
     - SE effectiveness_rate = 0% E times_applied >= 3: marcar `needs_review: true`
     - **SALVAR o arquivo**

   **Ponto C — audit-patterns (Passo 1), ao fazer effectiveness review:**
   - Mesma logica do Ponto B — se investigacao revisada usou SOP, atualizar counters
   - Verificar se algum SOP tem `needs_review: true` e reportar no audit

   **Auto-ajuste de confidence** (aplicado na proxima Fase 2):
   - effectiveness_rate < 50% → confidence capped em 60%
   - effectiveness_rate < 30% → confidence capped em 40%
   - effectiveness_rate = 0% apos 3+ aplicacoes → marcar SOP como `needs_review: true`

4. **Analisar tendencias** (threshold adaptativo):
   - **Threshold:** 2+ investigacoes (nao 3+) — projetos com historico curto merecem deteccao precoce
   - 4 dimensoes de analise:
     - Frequencia por **area** (diretorio): "backend/services/ teve 3 bugs no ultimo mes"
     - Frequencia por **tipo** (tag — usar taxonomia): "type_error eh 60% dos bugs"
     - Frequencia por **dominio Cynefin**: "80% dos bugs sao Complicated"
     - **MTTR** (Mean Time to Resolution): tempo entre sintoma e fix, por dominio
   - SE 2+ RCAs apontam para mesma area/tag: recomendacao de audit focado
   - MTTR tracking: registrar `reported_at` e `resolved_at` se dados disponiveis

5. **Detectar padroes recorrentes** (alertas adaptativos):
   - Threshold adaptativo — disparar alerta quando QUALQUER condicao atendida:
     - Anti-pattern com `recurrence >= 3` (campo no known-anti-patterns.md)
     - 2+ RCAs com mesma tag/area no historico
     - SOP com `times_applied >= 3` (v6.0)
   - Formato do alerta:
     ```
     PADRAO RECORRENTE DETECTADO
     Anti-pattern: {AP-ID} — {descricao}
     Recurrence: {count} incidentes
     SOP effectiveness_rate: {rate}%
     Recomendacao: rodar `*audit-patterns` para busca proativa no codebase
     ```
   - Sugerir `*audit-patterns` para busca proativa

6. **Strategy scorecard** (a partir de 2+ investigacoes):
   - Classifier estava correto? (domain classificado vs domain real pos-investigacao)
   - Archaeologist encontrou change suspeito no top 3?
   - Challenger refutou alguma hipotese que seria aceita?
   - Fast-track SOP foi utilizado? Se sim, foi eficaz? (agora rastreado via outcome tracking)

**Output da Fase 9:** Effectiveness review + knowledge base atualizada + SOP outcome update + trends + alerts + scorecard.

**Nota:** Na primeira investigacao, apenas faz effectiveness review de anteriores e registra.

---

## Comportamentos Obrigatorios

Estes comportamentos se aplicam durante TODA a investigacao:

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
> v5.0: Closed-loop learning com agentes especializados por fase.

- O executor roda todo o fluxo (classificacao → coleta → analise → fix → docs → learn)
- Fast tracks por dominio Cynefin reduzem fases para problemas simples
- Knowledge base em `docs/qa/rca-knowledge/` cresce automaticamente
- Escalar problemas estruturais para `@architect` (somente se problema de design identificado)
- Criar stories de backlog para achados colaterais + gerar handoff artifact para o SDC
- Usar `@devops *push` para push (unico agente autorizado para remote)
- Atualizar story file com resultados da investigacao no Change Log
