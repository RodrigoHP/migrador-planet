# Epic 21 — RCA v6.0: Intelligent Automation & Operational Rigor

**Status:** Done
**Branch:** feature/epic-21-rca-v6-intelligent-automation
**Data:** 2026-03-31
**Origem:** Analise de gaps do RCA v5.0 — lacuna entre design e execucao operacional
**Escopo:** Framework generico (.aios-core + .claude/commands/investigate.md) — nenhuma alteracao especifica de projeto

---

## Problema Central

O RCA v5.0 tem metodologia solida e closed-loop design, mas a execucao eh **majoritariamente manual e heuristica**. Confidence scores nao tem algoritmo definido, effectiveness review depende de alguem lembrar de chamar `*audit-patterns`, deduplicacao entre RCAs nao acontece na pratica, e SOPs nao rastreiam outcomes. O gap principal eh entre **design** e **operacao real**.

| Gap | Categoria | Impacto |
|-----|-----------|---------|
| Confidence scoring sem algoritmo | Automacao | Fast-track decisions sao heuristicas |
| Effectiveness review nunca roda | Automacao | Knowledge base fica stale |
| Dedup inexistente entre RCAs | Automacao | Bugs re-investigados |
| Test gap analysis vago | Inteligencia | Recomendacoes de teste genericas |
| Chaotic domain sem protocol | Metodologia | Sem guia para bugs caoticos |
| SOPs sem outcome tracking | Inteligencia | SOP ineficaz continua sendo oferecido |
| Anti-patterns incompletos | Consistencia | Registry fragil |
| Tags sem taxonomia | Consistencia | Pattern matching futuro fragil |
| Swiss Cheese sem scoring | Inteligencia | Nao indica qual barreira priorizar |
| Escalation sem criterios | Integracao | Problemas estruturais podem ser ignorados |
| Handoff RCA→SDC nao implementado | Integracao | Backlog items perdidos |

---

## Epic Goal

Evoluir o RCA v5.0 para v6.0 com automacao inteligente: algoritmo de confidence scoring formalizado, SOP outcome tracking, dedup check operacional, test gap analysis com metodologia concreta, stabilization protocol para dominio Chaotic, Swiss Cheese severity scoring, tag taxonomy controlada, e handoff operacional para SDC. Todas as alteracoes sao genericas e portaveis para qualquer projeto.

---

## Arquivos Afetados (Framework)

| Arquivo | Tipo |
|---------|------|
| `.claude/commands/investigate.md` | Skill (metodologia) |
| `.aios-core/development/workflows/rca-investigation.yaml` | Workflow AIOS |
| `.aios-core/development/tasks/rca-investigation.md` | Task wrapper |
| `.aios-core/development/tasks/audit-patterns.md` | Task (audit) |
| `docs/qa/rca-knowledge/investigations.yaml` | Schema (template) |
| `docs/qa/known-anti-patterns.md` | Schema (template) |
| `docs/qa/rca-knowledge/sops/*.yaml` | Schema (SOPs) |

---

## Stories

### Story 21.1: Algoritmo de Confidence Scoring Normalizado

**Descricao:** Formalizar o calculo de confidence score para SOP fast-track. Os pesos atuais (+3 sintomas, +2 mesmos arquivos, +1 dominio, +2 fix effective) sao heuristicas sem normalizacao. Definir algoritmo com pesos ponderados, normalizacao para 0-100%, e documentacao de como calcular.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** HIGH

---

### Story 21.2: Effectiveness Review — Enforcement Operacional

**Descricao:** O effectiveness review existe no design mas nunca roda porque depende de alguem chamar `*audit-patterns`. Criar mecanismo de enforcement: Fase 9 DEVE listar investigacoes pending >7d e propor review inline. O `*audit-patterns` DEVE incluir effectiveness check como step obrigatorio, nao opcional.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** HIGH

---

### Story 21.3: Dedup Check Operacional na Fase 0

**Descricao:** A Fase 0 (Classification) menciona dedup check mas nao define criterios. Implementar cross-reference concreto: buscar RCAs anteriores com mesmos sintomas/tags, PRs abertos com fix relacionado, e branches ativas. Definir janela temporal e acao quando duplicata encontrada.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** MEDIUM

---

### Story 21.4: Test Gap Analysis — Metodologia Step-by-Step

**Descricao:** A Fase 5 diz "buscar testes que passaram mas deveriam ter falhado" sem definir como. Criar metodologia concreta: (1) mapear funcao afetada → testes existentes, (2) para cada teste que passou, classificar causa (cenario nao coberto, mock incorreto, assertion fraca, dados insuficientes), (3) gerar recomendacao especifica de fix por teste.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** HIGH

---

### Story 21.5: Chaotic Domain — Fase 0.5 Stabilization Protocol

**Descricao:** "Stabilize first" aparece no texto do dominio Chaotic mas nao existe protocolo executavel. Criar Fase 0.5 com steps concretos: (1) contencao imediata (rollback, feature flag, hotfix), (2) observacao do sistema apos contencao, (3) criterios de estabilidade para prosseguir com investigacao completa.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** MEDIUM

---

### Story 21.6: SOP Outcome Tracking — Eficacia Agregada por SOP

**Descricao:** SOPs registram confidence mas nao rastreiam outcomes reais. Adicionar campos: `times_applied`, `times_effective`, `times_ineffective`, `effectiveness_rate`. Quando uma investigacao usa SOP fast-track, atualizar o outcome na SOP. Um SOP com effectiveness_rate baixo deve ter confidence reduzido automaticamente.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** HIGH

---

### Story 21.7: Anti-Pattern Registry Completeness

**Descricao:** Anti-patterns existentes (AP-001 a AP-003) estao incompletos segundo o schema v5.0. Adicionar campos obrigatorios faltantes: `recurrence` (count real), `status` (active/superseded), `sop_reference` (link para SOP associado). Validar consistencia entre anti-patterns e SOPs.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** QUICK WIN

---

### Story 21.8: Tag Taxonomy Controlada

**Descricao:** Cada RCA usa tags ad-hoc, tornando pattern matching futuro fragil. Criar vocabulario controlado de tags com definicoes claras. Categorias: error_type, root_cause_category, affected_layer, fix_type. Tags existentes devem ser migradas para o vocabulario.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** MEDIUM

---

### Story 21.9: Swiss Cheese Severity Scoring

**Descricao:** A barrier analysis lista barreiras como "failed/absent" sem quantificar impacto relativo. Implementar severity scoring: para cada barreira falhada, avaliar "se APENAS esta barreira estivesse presente, o bug teria sido prevenido?" (criticality). Gerar ranking de barreiras por impacto para priorizar fixes defensivos.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** MEDIUM

---

### Story 21.10: Escalation Criteria Codificados para @architect

**Descricao:** "Problema estrutural" nao tem definicao operacional. Codificar criterios: (1) bug afeta 3+ stages/modulos, (2) root cause eh design pattern incorreto, (3) fix requer mudanca de interface entre componentes, (4) barrier analysis mostra falha sistematica em 4+ camadas. Quando criterio atingido, gerar escalation prompt.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** LOW

---

### Story 21.11: Handoff RCA→SDC Operacional

**Descricao:** O workflow YAML preve `handoff-rca-to-sdc-{date}.yaml` mas nenhum RCA real gera esse artifact. Implementar geracao automatica do handoff na Fase 8 (Documentacao): quando backlog items sao criados, gerar handoff artifact consumivel pelo SDC com story references, prioridade, e contexto do RCA.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** MEDIUM

---

## Waves de Implementacao

```
Wave 1: Quick Wins (21.7)                        → Registry completeness
Wave 2: Core Intelligence (21.1 + 21.6)          → Confidence algorithm + SOP outcomes
Wave 3: Operational Rigor (21.2 + 21.3 + 21.11)  → Effectiveness enforcement + dedup + handoff
Wave 4: Deep Analysis (21.4 + 21.9)              → Test gaps + Swiss Cheese scoring
Wave 5: Methodology (21.5 + 21.8)                → Chaotic protocol + tag taxonomy
Wave 6: Integration (21.10)                       → Escalation criteria
```

**Dependencias:**
- Wave 1 eh independente (quick win)
- Wave 2: 21.6 depende de 21.7 (campos do registry)
- Wave 3: 21.2 beneficia de 21.6 (outcome tracking informa effectiveness)
- Wave 4: independente
- Wave 5: independente
- Wave 6: independente

---

## Criterios de Sucesso

| Metrica | Antes (v5.0) | Meta (v6.0) |
|---------|-------------|-------------|
| Confidence score | Heuristico (manual) | Algoritmo normalizado 0-100% |
| SOP outcome tracking | Nenhum | Aggregated effectiveness_rate |
| Effectiveness review | Manual (*audit-patterns) | Enforcement inline na Fase 9 |
| Dedup entre RCAs | Inexistente | Cross-reference na Fase 0 |
| Test gap methodology | Vago | Step-by-step com classificacao |
| Chaotic domain | "Stabilize first" (texto) | Fase 0.5 com protocol |
| Anti-pattern fields | Incompletos | 100% compliance com schema |
| Tag consistency | Ad-hoc | Vocabulario controlado |
| Swiss Cheese | Binary (failed/absent) | Severity scored + ranked |
| Escalation | Subjetivo | 4 criterios codificados |
| Handoff RCA→SDC | Nao implementado | Artifact auto-gerado |

---

## Notas

- **Portabilidade:** Todas as alteracoes sao no investigate.md (skill portavel) e em schemas/templates genericos. Nenhuma referencia a projeto especifico.
- **Backward compatible:** Projetos com v5.0 continuam funcionando. Campos novos sao opcionais.
- **Incremental:** Cada story eh independente e entrega valor isolado.
