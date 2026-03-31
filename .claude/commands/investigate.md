# /investigate — Root Cause Analysis & Exploratory Investigation v6.0

> Metodologia de investigacao profunda de bugs e problemas.
> Portavel: funciona com qualquer LLM (Claude, GPT, Gemini, Codex, Cursor).
> Copie este arquivo para qualquer projeto.
>
> v6.0: Intelligent Automation. Tudo do v5.0 (closed-loop learning, SOP fast-track,
> effectiveness review, anti-pattern supersession, alertas adaptativos, test gap
> analysis, trend analysis) MAIS: confidence scoring algorithm normalizado,
> SOP outcome tracking, dedup check operacional, test gap methodology step-by-step,
> Chaotic domain stabilization protocol (Fase 0.5), Swiss Cheese severity scoring,
> tag taxonomy controlada, escalation criteria codificados, handoff RCA→SDC operacional.
>
> **Estrutura auto-criada:** Na primeira execucao, o agente cria automaticamente
> os diretorios necessarios (`docs/qa/investigations/`, `docs/qa/rca-knowledge/sops/`,
> `docs/qa/known-anti-patterns.md`) se nao existirem. Zero configuracao previa.

## Principio

**Nunca aplique band-aid.** Todo problema eh investigado ate a origem. Um guard defensivo eh protecao adicional, nunca o fix principal. Cada bug eh uma oportunidade de melhoria — a investigacao sempre produz mais do que entrou.

---

## Como Usar

Forneça um ou mais indicios de erro (screenshot, log, stack trace, descricao) e diga `/investigate` ou "investigue este problema".

---

## Fase 0 — Classificacao (Classifier Agent)

**Objetivo:** Classificar o problema ANTES de investigar para adaptar a estrategia.

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

4. **Selecionar estrategia** conforme dominio:

   | Dominio | Tecnicas | Fases Executadas |
   |---------|----------|-----------------|
   | Clear | Change Analysis + Quick Fix | 0→1→7→8→9 (fast track) |
   | Complicated | Change Analysis + FTA + Barrier | 0→1→2→3→5→6→7→8→9 |
   | Complex | Full pipeline (todas as tecnicas) | 0→1→2→3→4→5→6→7→8→9 |
   | Chaotic | Stabilize (0.5) + Full pipeline | 0→0.5→1→2→3→4→5→6→7→8→9 |

5. **Dedup Check** (v6.0) — ANTES de prosseguir, verificar se problema ja esta sendo tratado:
   - **4 fontes de busca:**
     - `docs/qa/rca-knowledge/investigations.yaml` — RCAs anteriores
     - `git branch -a | grep -i fix/` — branches de fix ativas
     - `gh pr list --state open` — PRs abertos (se disponivel)
     - `docs/stories/` — stories InProgress ou Done recentes
   - **Criterios de match:**
     - Mesma mensagem de erro (exact ou substring)
     - Mesmos arquivos afetados (2+ overlap)
     - Mesmas tags (2+ overlap)
   - **Janela temporal:** ultimos 30 dias (configuravel)
   - **Acao quando match encontrado:**
     - **Match >90%:** DUPLICATA — parar e referenciar RCA existente
     - **Match 50-90%:** RELACIONADO — anotar cross-reference, continuar investigacao
     - **Match <50%:** NOVO — continuar normalmente
   - **Em modo YOLO:** auto-selecionar "RELACIONADO + continuar" se match parcial, "PARAR" se >90%
   - **Cross-reference bidirecional:** RCA nova referencia antiga E antiga recebe nota de referencia

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

1. **Buscar na Knowledge Base** — Verificar investigacoes anteriores:
   - Similarity de sintomas (mesmo tipo de erro, mesma area)
   - Tag matching (type_error, guard, traversal, etc.)
   - File overlap (mesmos arquivos afetados)
   - Anti-pattern registry match (`docs/qa/known-anti-patterns.md`)

2. **Calcular Confidence Score** (v6.0) — Algoritmo normalizado 0-100%:

   | Dimensao | Criterio | Pontos |
   |----------|----------|--------|
   | **Symptom match** (max 30) | Exact error type match: +30 / Similar error: +20 / Same category: +10 | 0-30 |
   | **Location match** (max 25) | Same function: +25 / Same file: +20 / Same module: +15 / Same layer: +10 | 0-25 |
   | **Domain match** (max 15) | Same Cynefin domain: +15 | 0-15 |
   | **Fix effectiveness** (max 20) | Previous fix resolved: +20 / Partial: +10 / Untested: +0 / Ineffective: -10 | -10 to 20 |
   | **Recurrence** (max 10) | 3+ occurrences: +10 / 2: +5 / 1: +0 | 0-10 |

   **Score final** = soma das dimensoes (max 100, min 0)

   **Ajuste por SOP outcome** (v6.0): SE SOP tem `effectiveness_rate`:
   - effectiveness_rate < 50% → confidence capped em 60% (nao pode ser fast-track)
   - effectiveness_rate < 30% → confidence capped em 40%

   **Exemplos:**
   - Score 92: exact error + same file + same domain + fix resolved + recurrence 3 → **fast-track auto-aceito**
   - Score 75: similar error + same module + different domain + untested → **ponto de partida, continuar**
   - Score 35: same category + same layer + no effectiveness data → **registrar, investigar normalmente**

3. **Sugerir SOP** baseado no score:
   - **Score > 80% E SOP existe:** propor fast-track (ver item 4)
   - **Score 50-80%:** usar como ponto de partida, continuar investigacao
   - **Score < 50%:** registrar como "problema novo", continuar investigacao normal

4. **SOP Fast-Track** (v5.0) — SE confianca alta (>80%) E SOP existe:
   - **PROPOR fast-track explicitamente** ao investigador:
     ```
     SOP FAST-TRACK DISPONIVEL
     SOP: {sop_id} — {sop_name}
     Confidence: {score}%
     Fix sugerido: {resumo do fix da SOP}
     Opcoes:
       ACEITAR → Pular para Fase 7 usando SOP como ponto de partida
       REJEITAR → Continuar pipeline normal (Fase 3+)
     ```
   - **Aceitar:** Carregar fix_steps da SOP, pular diretamente para Fase 7 (Solucao)
   - **Rejeitar:** Continuar pipeline normalmente a partir da Fase 3
   - **Em modo YOLO:** Auto-aceitar se confidence >= 90%, perguntar se 80-89%

5. **Anti-pattern supersession check** (v5.0):
   - SE anti-pattern do match tem campo `superseded_by`: seguir cadeia ate o anti-pattern mais recente
   - Priorizar SOP do anti-pattern mais recente na cadeia
   - Alertar se SOP esta `deprecated` (associada a anti-pattern superseded)

**Output da Fase 2:** Similar investigations + suggested SOPs + confidence scores + fast-track decision.

**Nota:** Se primeira investigacao no projeto, esta fase retorna "problema novo" e segue normalmente.

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

4. **Barrier Criticality Scoring** (v6.0) — Para cada barreira falhada/ausente:
   - Pergunta contrafactual: "Se APENAS esta barreira estivesse presente e funcionando, o bug teria sido prevenido?"
     - **HIGH** (preveniria sozinha): Esta barreira isolada teria impedido o bug → fix prioritario
     - **MEDIUM** (reduziria impacto): Teria detectado mais cedo ou limitado blast radius
     - **LOW** (contribuiria): Teria alertado mas nao impedido sozinha
   - **Ranking de barreiras** por criticality: apresentar como "Fix This First"
   - **Tabela no relatorio:**
     ```
     | Camada          | Status  | Criticality | Contrafactual                        |
     |-----------------|---------|-------------|--------------------------------------|
     | Code Level      | absent  | HIGH        | Guard teria impedido crash           |
     | Test Level      | absent  | HIGH        | Teste teria detectado na CI          |
     | Static Analysis | absent  | LOW         | Linter alertaria mas nao bloquearia  |
     ```

5. **Gerar recomendacoes** por urgencia (priorizadas por criticality):
   - **Immediate:** Fechar barreiras HIGH que causaram este bug
   - **Short-term:** Registrar anti-pattern, fechar barreiras MEDIUM
   - **Long-term:** Fechar barreiras LOW, aumentar coverage, adicionar ferramentas

**Output da Fase 5:** Barreiras analisadas por camada + criticality scoring + Swiss Cheese alignment + test gaps + recomendacoes priorizadas.

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

**Output da Fase 6:** Todos os achados com evidence level + confidence score + sources citadas.

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
5. **Implementar recomendacoes immediate** da Barrier Analysis (Fase 5).
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

### 14. Handoff RCA→SDC (v6.0)
SE backlog items foram identificados:
- Gerar handoff artifact em `.aios/handoffs/handoff-rca-to-sdc-{date}.yaml`:
  ```yaml
  from_agent: "@qa"
  investigation_id: "rca-{date}-{slug}"
  consumed: false
  backlog_items:
    - title: "{titulo da story sugerida}"
      priority: high | medium | low
      context: "{resumo do achado}"
      source_finding: "F-{N}"
  ```
- Handoff segue formato do agent-handoff protocol existente
- @sm ou @aios-master consome ao iniciar SDC

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

3. **SOP Outcome Tracking** (v6.0) — SE esta investigacao usou SOP fast-track:
   - Incrementar `times_applied` no SOP utilizado
   - Registrar `last_applied: {date}` e `last_investigation: {rca-id}`
   - **Apos effectiveness review** (quando effectiveness da ESTA investigacao for avaliada):
     - SE `resolved`: incrementar `times_effective`
     - SE `partial` ou `ineffective`: incrementar `times_ineffective`
     - Recalcular `effectiveness_rate = times_effective / times_applied`
   - **Auto-ajuste de confidence** (aplicado na proxima Fase 2):
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
