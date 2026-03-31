# /investigate — Root Cause Analysis & Exploratory Investigation v5.0

> Metodologia de investigacao profunda de bugs e problemas.
> Portavel: funciona com qualquer LLM (Claude, GPT, Gemini, Codex, Cursor).
> Copie este arquivo para qualquer projeto.
>
> v5.0: Closed-loop learning. Tudo do v4.0 (Cynefin, grafos causais, hypothesis
> challenge, Swiss Cheese, evidence grading, knowledge base, SOPs, meta-learning)
> MAIS: SOP fast-track assertivo, effectiveness review automatico, anti-pattern
> supersession, alertas adaptativos por recurrence, test gap analysis, trend
> analysis com threshold adaptativo.
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
   | Chaotic | Stabilize + Full pipeline | Estabilizar primeiro, depois todas |

5. **Override manual** — O investigador pode reclassificar a qualquer momento se a classificacao inicial parece errada.

**Output da Fase 0:** Classificacao (domain, severity, scope) + estrategia selecionada + fases a executar.

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

2. **Ranquear resultados** por relevancia:
   - Sintomas similares (+3)
   - Mesmos arquivos (+2)
   - Mesmo dominio Cynefin (+1)
   - Fix anterior foi effective (+2)

3. **Sugerir SOP** se match encontrado:
   - Investigacao similar + fix que funcionou + confianca do match
   - SE confianca media (50-80%): usar como ponto de partida, continuar investigacao
   - SE sem match: registrar como "problema novo", continuar investigacao normal

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

3. **Test Gap Analysis** (v5.0) — Analise profunda da camada Test Level:
   - **Buscar testes existentes** que cobrem a funcao/modulo afetado pelo bug
   - Para cada teste que **passou mas deveria ter falhado**, analisar a causa:
     - **Cenario nao coberto:** Teste existe mas nao testa o cenario especifico do bug
     - **Mock incorreto:** Teste usa mock que esconde o comportamento real
     - **Assertion fraca:** Teste verifica resultado mas nao valida pre-condicoes/invariantes
     - **Dados de teste insuficientes:** Teste usa dados que nao disparam o bug
   - **Gerar lista de test gaps** com recomendacao de fix para cada:
     ```
     TEST GAP: {test_file}:{test_name}
     Status: Passou quando deveria ter falhado
     Causa: {cenario_nao_coberto | mock_incorreto | assertion_fraca | dados_insuficientes}
     Fix: {descricao do que adicionar/corrigir no teste}
     ```
   - **Passar test gaps como input** para Fase 7 — testes corretivos sao obrigatorios

4. **Gerar recomendacoes** por urgencia:
   - **Immediate:** Fechar buracos que causaram este bug
   - **Short-term:** Registrar anti-pattern, adicionar regras
   - **Long-term:** Aumentar coverage, adicionar ferramentas

**Output da Fase 5:** Barreiras analisadas por camada + Swiss Cheese alignment + test gaps + recomendacoes categorizadas.

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

**Campos obrigatorios do anti-pattern:**
- ID (AP-XXX sequencial)
- Encontrado em (referencia a RCA)
- Descricao
- `search_pattern` (regex para deteccao automatica — **obrigatorio quando possivel**)
- Scope (quais arquivos/diretorios buscar)
- Severidade
- Guard esperado

**Supersession (v5.0):**
- SE o anti-pattern encontrado eh uma evolucao de anti-pattern anterior (a causa raiz eh mais profunda):
  - Adicionar `superseded_by: AP-{novo}` no anti-pattern anterior
  - Marcar anti-pattern anterior como `status: superseded`
  - Marcar SOP associada ao anti-pattern anterior como `deprecated: true` com `replaced_by: sop-{novo}`
  - O anti-pattern superseded NAO eh removido (preservar historico)
  - Documentar no relatorio: "AP-{antigo} superseded por AP-{novo} — causa raiz mais profunda identificada"

### 12. Test Gap Analysis (v5.0)
Incluir secao no relatorio com test gaps identificados na Fase 5:
- Testes que existiam mas nao detectaram o bug (e por que)
- Cenarios de teste ausentes que teriam detectado
- Recomendacoes de fix para cada test gap

### 13. Recomendacoes
- Contratos que deveriam ser formalizados
- Mudancas arquiteturais sugeridas (se aplicavel)

---

## Fase 9 — Meta-Learning (Meta-Learner Agent)

**Objetivo:** Aprender com cada investigacao para que a proxima seja mais rapida.

1. **Registrar investigacao** na knowledge base:
   - Investigation record com: date, symptoms, domain, root_causes, fix_approach, files_affected, tags, effectiveness, effectiveness_reviewed_at
   - Gerar SOP se padrao novo detectado (steps executaveis para resolver problema similar)
   - Registrar anti-pattern se descoberto

2. **Effectiveness Review** (v5.0) — Avaliar fixes anteriores:
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
   - **Nota:** Review pode ser executado standalone via `*audit-patterns` (nao apenas durante RCA)

3. **Analisar tendencias** (threshold adaptativo v5.0):
   - **Threshold:** 2+ investigacoes (nao 3+) — projetos com historico curto merecem deteccao precoce
   - 4 dimensoes de analise:
     - Frequencia por **area** (diretorio): "backend/services/ teve 3 bugs no ultimo mes"
     - Frequencia por **tipo** (tag): "TypeError eh 60% dos bugs"
     - Frequencia por **dominio Cynefin**: "80% dos bugs sao Complicated"
     - **MTTR** (Mean Time to Resolution): tempo entre sintoma e fix, por dominio
   - SE 2+ RCAs apontam para mesma area/tag: recomendacao de audit focado
   - MTTR tracking: registrar `reported_at` e `resolved_at` se dados disponiveis

4. **Detectar padroes recorrentes** (alertas adaptativos v5.0):
   - Threshold adaptativo — disparar alerta quando QUALQUER condicao atendida:
     - Anti-pattern com `recurrence >= 3` (campo no known-anti-patterns.md)
     - 2+ RCAs com mesma tag/area no historico
     - SOP com `recurrence >= 3`
   - Formato do alerta:
     ```
     PADRAO RECORRENTE DETECTADO
     Anti-pattern: {AP-ID} — {descricao}
     Recurrence: {count} incidentes
     Recomendacao: rodar `*audit-patterns` para busca proativa no codebase
     ```
   - Sugerir `*audit-patterns` para busca proativa

5. **Strategy scorecard** (a partir de 2+ investigacoes):
   - Classifier estava correto? (domain classificado vs domain real pos-investigacao)
   - Archaeologist encontrou change suspeito no top 3?
   - Challenger refutou alguma hipotese que seria aceita?
   - Fast-track SOP foi utilizado? Se sim, foi eficaz?

**Output da Fase 9:** Knowledge base atualizada + effectiveness review + trends + alerts + SOP gerado + scorecard.

**Nota:** Na primeira investigacao, apenas registra e faz effectiveness review de investigacoes anteriores.

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
