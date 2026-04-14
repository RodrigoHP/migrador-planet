# Epic 20 — RCA v5.0: Closed-Loop Learning & Proactive Detection

**Status:** Done
**Branch:** feature/epic-20-rca-v5-closed-loop
**Data:** 2026-03-31
**Origem:** Analise de gaps do RCA v4.0 apos primeiras investigacoes em producao
**Escopo:** Framework generico (.aios-core + .claude/commands/investigate.md) — nenhuma alteracao especifica de projeto

---

## Problema Central

O RCA v4.0 eh uma metodologia robusta de investigacao, mas opera em **open loop**: investiga, documenta, e encerra. Nao ha feedback automatico sobre eficacia dos fixes, nao reutiliza SOPs gerados, e nao previne recorrencia proativamente.

| Gap | Impacto |
|-----|---------|
| `effectiveness` fica `pending` indefinidamente | Nao sabemos se fixes funcionaram |
| SOPs geradas mas nao consumidas no fast-track | Bugs conhecidos re-investigados do zero |
| Anti-patterns sem relacao de evolucao | Fix parcial tratado como definitivo |
| Threshold de alertas rigido (3+ RCAs) | Padroes recorrentes ignorados em projetos pequenos |
| Barrier Analysis superficial em testes | Nao identifica qual teste deveria ter falhado |
| Anti-patterns sem automacao de deteccao | Mesmos padroes reentram no codebase |

---

## Epic Goal

Evoluir o RCA v4.0 para v5.0 com closed-loop learning: SOPs consumidas automaticamente no fast-track, effectiveness review periodico, anti-patterns com evolucao rastreavel, alertas adaptativos, e integracao com test gap analysis. Todas as alteracoes sao genericas e portaveis para qualquer projeto.

---

## Arquivos Afetados (Framework)

| Arquivo | Tipo |
|---------|------|
| `.claude/commands/investigate.md` | Skill (metodologia) |
| `.aios-core/development/workflows/rca-investigation.yaml` | Workflow AIOS |
| `.aios-core/development/tasks/rca-investigation.md` | Task wrapper |
| `docs/qa/rca-knowledge/investigations.yaml` | Schema (template) |
| `docs/qa/known-anti-patterns.md` | Schema (template) |
| `.aios-core/development/agents/qa.md` | Agent (comandos novos) |

---

## Stories

### Story 20.1: SOP Fast-Track Assertivo na Fase 2

**Descricao:** Quando a Fase 2 (Pattern Matcher) encontra uma SOP com confidence >80% e sintomas compatíveis, DEVE propor fast-track explicitamente com o fix sugerido, em vez de apenas listar como match. O investigador pode aceitar (pula para Fase 7) ou rejeitar (continua pipeline normal).

**Executor:** `@dev` | **Quality Gate:** `@qa`

**Acceptance Criteria:**
- [ ] Fase 2 do investigate.md propoe fast-track quando SOP match confidence >80%
- [ ] Proposta inclui: SOP ID, fix sugerido, confidence score, opcao aceitar/rejeitar
- [ ] Aceitar fast-track pula direto para Fase 7 com fix da SOP como ponto de partida
- [ ] Rejeitar continua o pipeline normal a partir da Fase 3
- [ ] Workflow YAML atualizado com rota de fast-track via SOP
- [ ] Documentacao no investigate.md explica o mecanismo

**Arquivos:**
- `.claude/commands/investigate.md` (Fase 2)
- `.aios-core/development/workflows/rca-investigation.yaml`

---

### Story 20.2: Effectiveness Review Automatico

**Descricao:** Criar mecanismo para revisar a eficacia de fixes anteriores. Integrar no comando `*audit-patterns` uma verificacao: investigacoes com `effectiveness: pending` ha mais de 7 dias devem ser avaliadas (bug recorreu? fix resolveu?). Resultado atualiza o campo `effectiveness` na knowledge base.

**Executor:** `@dev` | **Quality Gate:** `@qa`

**Acceptance Criteria:**
- [ ] `*audit-patterns` inclui step de effectiveness review para investigacoes pending >7d
- [ ] Para cada investigacao pending, verifica: bug recorreu (grep por mesmo erro em logs/commits recentes)?
- [ ] Atualiza effectiveness para `resolved`, `partial`, ou `ineffective` baseado na evidencia
- [ ] Se `ineffective`: gera alerta recomendando nova investigacao
- [ ] Schema de investigations.yaml documenta o campo `effectiveness_reviewed_at`
- [ ] Fase 9 do investigate.md referencia o review automatico

**Arquivos:**
- `.claude/commands/investigate.md` (Fase 9)
- `.aios-core/development/tasks/audit-patterns.md` (ou criar se nao existir)
- Schema de `investigations.yaml`

---

### Story 20.3: Anti-Pattern Supersession — Evolucao de Padroes

**Descricao:** Adicionar campo `superseded_by` no schema de anti-patterns para rastrear evolucao. Quando uma investigacao descobre que um anti-pattern anterior era sintoma de algo mais profundo, o antigo deve ser marcado como superseded apontando para o novo. O Pattern Matcher (Fase 2) deve priorizar o anti-pattern mais recente na cadeia.

**Executor:** `@dev` | **Quality Gate:** `@qa`

**Acceptance Criteria:**
- [ ] Schema de `known-anti-patterns.md` inclui campo opcional `superseded_by: AP-XXX`
- [ ] Anti-pattern superseded eh marcado com status `superseded` (nao removido)
- [ ] Fase 2 (Pattern Matcher) prioriza anti-pattern mais recente na cadeia de supersession
- [ ] SOPs associados a anti-patterns superseded sao marcados como `deprecated` com referencia ao novo
- [ ] Documentacao no investigate.md explica o conceito de supersession

**Arquivos:**
- `.claude/commands/investigate.md` (Fase 2, Fase 8)
- Schema de `known-anti-patterns.md`
- Schema de SOPs

---

### Story 20.4: Alertas Adaptativos por Recurrence

**Descricao:** O threshold de alerta na Fase 9 (Meta-Learning) atualmente exige 3+ RCAs formais para detectar padroes. Evoluir para considerar o campo `recurrence` dos anti-patterns e SOPs: se um anti-pattern tem recurrence >= 3 (independente de quantas RCAs formais existem), disparar alerta imediato recomendando audit proativo.

**Executor:** `@dev` | **Quality Gate:** `@qa`

**Acceptance Criteria:**
- [ ] Fase 9 verifica `recurrence` de anti-patterns alem do count de RCAs
- [ ] Threshold adaptativo: alerta se recurrence >= 3 OU RCA count >= 2 para mesmo tag/area
- [ ] Alerta inclui: anti-pattern ID, recurrence count, sugestao de `*audit-patterns`
- [ ] Para projetos novos (0-2 RCAs), threshold mais baixo para nao ignorar padroes
- [ ] Documentacao atualizada no investigate.md (Fase 9)

**Arquivos:**
- `.claude/commands/investigate.md` (Fase 9)
- `.aios-core/development/workflows/rca-investigation.yaml` (step meta_learning)

---

### Story 20.5: Test Gap Analysis na Barrier Analysis

**Descricao:** Evoluir a Fase 5 (Barrier Analysis) para identificar nao apenas se testes existem ou nao, mas QUAIS testes especificos deveriam ter detectado o bug e por que falharam em detecta-lo. Isso transforma a barrier analysis de checklist binario (worked/absent) para analise causal de gaps no test suite.

**Executor:** `@dev` | **Quality Gate:** `@qa`

**Acceptance Criteria:**
- [ ] Fase 5 inclui step: buscar testes existentes que cobrem a funcao/modulo afetado
- [ ] Para cada teste encontrado que passou quando deveria ter falhado: analisar por que (cenario nao coberto? mock incorreto? assertion fraca?)
- [ ] Output inclui lista de test gaps com recomendacao de fix para cada
- [ ] Fase 7 (Solucao) recebe os test gaps como input obrigatorio para criar testes corretivos
- [ ] Documentacao atualizada no investigate.md (Fase 5)
- [ ] Template de relatorio (Fase 8) inclui secao "Test Gap Analysis"

**Arquivos:**
- `.claude/commands/investigate.md` (Fase 5, Fase 7, Fase 8)

---

### Story 20.6: Anti-Pattern Detection Rules (Linter Integration)

**Descricao:** Para cada anti-pattern registrado que tenha um `search_pattern` (regex), gerar automaticamente uma regra de deteccao que pode ser usada como pre-commit check ou integrada em `*audit-patterns`. O objetivo eh prevencao ativa: impedir que padroes conhecidos reentrem no codebase.

**Executor:** `@dev` | **Quality Gate:** `@qa`

**Acceptance Criteria:**
- [ ] `*audit-patterns` le `known-anti-patterns.md` e executa cada `search_pattern` no escopo definido
- [ ] Resultado: lista de matches atuais no codebase com localizacao (arquivo:linha)
- [ ] Para cada match, referencia o anti-pattern ID e severidade
- [ ] Output formatado como actionable (pode virar story ou fix imediato)
- [ ] Documentacao de como adicionar novos anti-patterns com search_pattern
- [ ] Fase 8 do investigate.md gera anti-pattern com search_pattern obrigatorio quando possivel

**Arquivos:**
- `.claude/commands/investigate.md` (Fase 8)
- `.aios-core/development/tasks/audit-patterns.md`
- Schema de `known-anti-patterns.md`

---

### Story 20.7: Trend Analysis com Threshold Adaptativo

**Descricao:** A Fase 9 (Meta-Learning) atualmente exige 3+ investigacoes para gerar trends. Reduzir para 2 investigacoes em projetos com historico curto. Adicionar analise de tendencias por: area (diretorio), tipo de erro (tag), dominio Cynefin, e MTTR estimado. Gerar recomendacoes proativas quando tendencia detectada.

**Executor:** `@dev` | **Quality Gate:** `@qa`

**Acceptance Criteria:**
- [ ] Trends gerados a partir de 2+ investigacoes (threshold adaptativo por tamanho do historico)
- [ ] Analise por 4 dimensoes: area, tipo de erro, dominio, MTTR
- [ ] Se 2+ RCAs apontam para mesma area/tag: recomendacao de audit focado
- [ ] MTTR tracking: tempo entre sintoma reportado e fix deployado (se dados disponiveis)
- [ ] Output integrado ao relatorio da Fase 9
- [ ] Strategy scorecard: classifier acertou dominio? archaeologist encontrou suspect no top 3?

**Arquivos:**
- `.claude/commands/investigate.md` (Fase 9)
- Schema de `investigations.yaml` (campos adicionais se necessario)

---

## Waves de Implementacao

```
Wave 1: Core Loop (20.1 + 20.2)           → SOP fast-track + effectiveness review
Wave 2: Knowledge Evolution (20.3 + 20.4) → supersession + alertas adaptativos
Wave 3: Deep Analysis (20.5 + 20.7)       → test gap analysis + trends
Wave 4: Prevention (20.6)                 → anti-pattern detection automation
```

**Dependencias:** Wave 1 eh independente. Wave 2 depende de Wave 1 (effectiveness informa supersession). Wave 3 eh independente. Wave 4 depende de 20.3 (schema de anti-patterns com supersession).

---

## Criterios de Sucesso

| Metrica | Antes (v4.0) | Meta (v5.0) |
|---------|-------------|-------------|
| Bugs conhecidos re-investigados do zero | Possivel | 0 (SOP fast-track) |
| Effectiveness de fixes avaliada | Nunca | Em ate 7 dias |
| Anti-patterns com cadeia de evolucao | Nao | Sim (superseded_by) |
| Alertas proativos disparados | Apenas com 3+ RCAs | Com recurrence >= 3 |
| Test gaps identificados por RCA | Nao | Sim (quais testes falharam em detectar) |
| Trends disponiveis apos | 3+ RCAs | 2+ RCAs |

---

## Notas

- **Portabilidade:** Todas as alteracoes sao no investigate.md (skill portavel) e em schemas/templates genericos. Nenhuma referencia a projeto especifico.
- **Backward compatible:** Projetos com v4.0 continuam funcionando. Campos novos sao opcionais.
- **Incremental:** Cada story eh independente e entrega valor isolado.
