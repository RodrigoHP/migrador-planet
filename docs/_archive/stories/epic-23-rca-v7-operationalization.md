# Epic 23 — RCA v7.0: Operationalization

**Status:** Done
**Branch:** feature/epic-23-rca-v7-operationalization
**Data:** 2026-03-31
**Origem:** Auditoria profunda do RCA v6.0 — gap entre especificacao e execucao real
**Escopo:** Framework generico (.aios-core + .claude/commands/investigate.md) — nenhuma alteracao especifica de projeto

---

## Problema Central

O RCA v6.0 tem design de nivel enterprise mas **execucao de nivel prototipo**. Features como confidence scoring, SOP outcome tracking, dedup check, barrier criticality, e handoff RCA→SDC estao **declaradas nos specs** mas **nunca foram executadas de verdade**. Os 2 RCAs existentes no projeto nao populam campos v6.0, nao executam Pattern Matcher, nao geram handoff artifacts, e nao fazem escalation assessment. O gap principal eh entre **spec** e **operacao real**.

### Evidencia Concreta

| Feature v6.0 | Status Real |
|---------------|-------------|
| Confidence scoring (0-100%) | Formula definida, campo ausente nos registros |
| SOP outcome tracking | `times_applied: 0`, nunca atualizado |
| Dedup check | 2 RCAs do mesmo bug nao foram cruzadas |
| Effectiveness review | Ambas RCAs com `effectiveness: pending`, nenhum review |
| Handoff RCA→SDC | Diretorio `.aios/handoffs/` nao existe |
| Escalation assessment | RCA atinge 4/4 criterios, ninguem avaliou |
| Pattern Matcher (Fase 2) | Nenhum relatorio contem esta secao |
| Barrier criticality scoring | Tabela basica sem contrafactual |
| Tag taxonomy enforcement | Tags fora do vocabulario sem rejeicao |
| Evidence grading completo | E1-E4 sem confidence/sources |
| Fast-track Clear domain | Declarado no workflow, sequencia sempre linear |

---

## Epic Goal

Fazer **funcionar de verdade** tudo que o v6.0 declarou. Zero features novos — 100% operacionalizacao. Cada story fecha um gap entre spec e execucao real, com exemplos concretos e validacao contra os RCAs existentes.

---

## Arquivos Afetados (Framework)

| Arquivo | Tipo |
|---------|------|
| `.claude/commands/investigate.md` | Skill (metodologia) |
| `.aios-core/development/workflows/rca-investigation.yaml` | Workflow AIOS |
| `.aios-core/development/tasks/rca-investigation.md` | Task wrapper |
| `.aios-core/development/tasks/audit-patterns.md` | Task (audit) |
| `docs/qa/rca-knowledge/investigations.yaml` | Registry (dados) |
| `docs/qa/rca-knowledge/sops/*.yaml` | SOPs (dados) |
| `docs/qa/known-anti-patterns.md` | Anti-patterns (dados) |
| `docs/qa/rca-knowledge/tag-taxonomy.yaml` | Taxonomia |
| `.claude/rules/rca-principle.md` | Regra constitucional |

---

## Stories

### Story 23.1: Migrar Registros Existentes para Schema v6.0 Real

**Descricao:** Os 2 registros em `investigations.yaml` nao tem campos v6.0 (`confidence_score`, `dedup_status`, `related_rcas`, `sop_fast_track_used`, `effectiveness_reviewed_at`). Popula-los retroativamente com dados reais derivados dos relatorios. Sem este fix, nenhuma automacao v6.0 funciona.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** CRITICAL

---

### Story 23.2: Validacao de Schema Obrigatoria no Registro

**Descricao:** Criar checklist de validacao na Fase 8 que REJEITA registro de investigacao se campos obrigatorios v6.0 estiverem ausentes. Hoje o schema eh declarativo — precisa ser enforcement. Incluir lista de campos obrigatorios e template pre-preenchido.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** HIGH

---

### Story 23.3: Pattern Matcher — Implementacao Real com Worked Example

**Descricao:** A Fase 2 nunca executou em nenhum RCA. O problema: nao ha instrucoes step-by-step suficientes para o agente saber O QUE fazer. Reescrever Fase 2 com: (1) query exata para investigations.yaml, (2) formula de scoring com pesos concretos e exemplo numerico, (3) template de output obrigatorio, (4) criterios de fast-track acceptance. Validar contra os 2 RCAs existentes.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** CRITICAL

---

### Story 23.4: Dedup Check — Cross-Reference Operacional

**Descricao:** 2 RCAs do mesmo bug (`'list' has no attribute 'get'`, Stage 5, AP-001) nao foram cruzadas. Problema: instrucoes de dedup sao genericas ("buscar por symptoms/tags") sem definir matching concreto. Implementar: (1) matching por error message (substring), (2) matching por file overlap (2+ arquivos), (3) matching por tag overlap (2+ tags), (4) output obrigatorio com dedup_status e related_rcas. Retroativamente cruzar os 2 RCAs existentes.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** HIGH

---

### Story 23.5: SOP Outcome Tracking — Fechar o Loop

**Descricao:** `sop-missing-isinstance-guard.yaml` tem counters zerados apesar de ter sido referenciado em RCA. Problema: nao ha instrucao clara de QUANDO e COMO atualizar os counters. Implementar: (1) na Fase 2, se SOP matched, incrementar `times_applied` IMEDIATAMENTE, (2) na Fase 9 effectiveness review, atualizar `times_effective` ou `times_ineffective`, (3) recalcular `effectiveness_rate`, (4) instrucoes explicitas com path do arquivo e campos a editar. Atualizar SOP existente retroativamente.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** HIGH

---

### Story 23.6: Effectiveness Review — Trigger Automatico

**Descricao:** Effectiveness review nunca roda porque depende de alguem lembrar. Problema: nao ha trigger. Implementar: (1) na Fase 0 de QUALQUER nova investigacao, checar registros com `effectiveness: pending` ha >7 dias, (2) mostrar lista e pedir decisao inline, (3) atualizar registro imediatamente, (4) se nao houver nova investigacao, documentar que `*audit-patterns` DEVE ser rodado semanalmente (adicionar ao guide do aios-master).

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** HIGH

---

### Story 23.7: Handoff RCA→SDC — Gerar Artifacts Reais

**Descricao:** Diretorio `.aios/handoffs/` nao existe e nenhum handoff foi gerado. Problema: instrucoes dizem "gerar artifact" mas nao dao path exato, template completo, nem trigger claro. Implementar: (1) criar diretorio `.aios/handoffs/` com .gitkeep, (2) template YAML completo na Fase 8, (3) trigger: SE `achados_colaterais` > 0 OU `backlog_items` > 0, (4) instrucao explicita de criar arquivo com nome `handoff-rca-to-sdc-{date}.yaml`.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** MEDIUM

---

### Story 23.8: Escalation Assessment — Avaliacao Obrigatoria

**Descricao:** RCA stage5 atinge 4/4 criterios de escalacao mas ninguem avaliou. Problema: avaliacao eh opcional na pratica. Implementar: (1) na Fase 5, APOS barrier analysis, OBRIGATORIAMENTE avaliar 4 criterios, (2) output obrigatorio com checklist preenchida, (3) SE qualquer criterio = true, gerar prompt de escalacao, (4) em modo YOLO, logar decisao mas nao skipar avaliacao.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** MEDIUM

---

### Story 23.9: Barrier Criticality — Contrafactual Real

**Descricao:** Barrier analysis produz tabela basica "failed/absent" sem criticality scoring. Problema: instrucoes dizem "pergunta contrafactual" mas nao forcam output estruturado. Implementar: (1) template obrigatorio com coluna Criticality (HIGH/MEDIUM/LOW), (2) para cada barreira, OBRIGAR resposta a "se APENAS esta barreira funcionasse, preveniria o bug?", (3) ranking "Fix This First" como output da Fase 5, (4) Fase 7 DEVE priorizar fixes pelo ranking.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** MEDIUM

---

### Story 23.10: Tag Taxonomy — Enforcement Real

**Descricao:** RCA usa tags fora do vocabulario (`guard`, `isinstance`, `wireframe`) sem rejeicao. Problema: taxonomia eh advisory, nao enforced. Implementar: (1) na Fase 8, antes de registrar, validar TODAS tags contra `tag-taxonomy.yaml`, (2) tags invalidas: sugerir equivalente do vocabulario, (3) se nenhum equivalente, exigir prefixo `custom:`, (4) retroativamente corrigir tags nos 2 registros existentes.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** LOW

---

### Story 23.11: Evidence Grading — Estrutura Completa

**Descricao:** Evidence grading aparece parcial (E1 label sem confidence/sources) ou ausente nos relatorios. Problema: template de relatorio nao forca estrutura completa. Implementar: (1) template de Evidence Summary com colunas obrigatorias (Claim, Level, Confidence 0-1, Sources), (2) lista fixa de sources validas (git_diff, git_bisect, test_reproduction, log_analysis, code_inspection, stack_trace), (3) na Fase 6, OBRIGAR preenchimento antes de prosseguir.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** LOW

---

### Story 23.12: Fast-Track Clear Domain — Implementar Branching Real

**Descricao:** Workflow declara `clear: phases [0,1,7,8,9]` mas sequencia eh sempre linear. Problema: nao ha instrucao condicional no investigate.md para skipar fases. Implementar: (1) na Fase 0, se domain=Clear, mostrar mensagem "Fast-track Clear: pulando Fases 2-6", (2) pular direto para Fase 7 (fix), (3) manter Fases 8-9 completas, (4) registrar no relatorio que fast-track foi usado.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** LOW

---

### Story 23.13: Anti-Pattern Recurrence — Auto-Incremento

**Descricao:** AP-001 tem `Recurrence: 4` mas ninguem sabe quem incrementou — eh manual. Problema: quando audit-patterns encontra instancia de anti-pattern, nao atualiza o contador. Implementar: (1) no audit-patterns, ao encontrar match de AP existente, incrementar `Recurrence` automaticamente, (2) logar data e contexto do incremento, (3) na Fase 8 de nova investigacao, se anti-pattern existente matched, incrementar tambem.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** LOW

---

### Story 23.14: Backlog Findings → Stories Materializados

**Descricao:** Achados colaterais (F-1, F-2, AC-01) sao listados nos relatorios mas nunca viram stories. Problema: Fase 8 diz "criar stories de backlog" mas nao define formato nem destino. Implementar: (1) na Fase 8, para cada achado colateral, gerar draft de story com titulo, descricao, prioridade, e referencia ao RCA, (2) salvar em `docs/stories/backlog/` como `backlog-{rca-slug}-{N}.md`, (3) handoff artifact DEVE referenciar estes drafts.

**Executor:** `@dev` | **Quality Gate:** `@qa` | **Prioridade:** LOW

---

## Waves de Implementacao

```
Wave 1: Data Foundation (23.1 + 23.2)           → Schema compliance + validation
Wave 2: Core Automation (23.3 + 23.4 + 23.5)    → Pattern Matcher + Dedup + SOP tracking
Wave 3: Feedback Loops (23.6 + 23.7 + 23.8)     → Effectiveness + Handoff + Escalation
Wave 4: Quality (23.9 + 23.10 + 23.11)          → Criticality + Tags + Evidence
Wave 5: Polish (23.12 + 23.13 + 23.14)          → Fast-track + Recurrence + Backlog
```

**Dependencias:**
- Wave 1 eh pre-requisito para Wave 2 (dados precisam estar corretos)
- Wave 2: 23.5 depende de 23.3 (SOP tracking depende de Pattern Matcher funcionar)
- Wave 3: 23.6 depende de 23.1 (effectiveness review precisa de campos populados)
- Wave 4: independente
- Wave 5: independente

---

## Criterios de Sucesso

| Metrica | Antes (v6.0) | Meta (v7.0) |
|---------|-------------|-------------|
| Campos v6.0 populados | 0/2 registros | 100% dos registros |
| Pattern Matcher executado | 0/2 RCAs | 100% dos RCAs |
| Dedup cross-reference | 0 (2 RCAs do mesmo bug sem link) | 100% cross-linked |
| SOP counters atualizados | 0 (counters zerados) | Atualizado em cada uso |
| Effectiveness review | 0 reviews feitos | Trigger automatico |
| Handoff artifacts gerados | 0 | 1 por RCA com backlog |
| Escalation assessment | 0/2 RCAs | 100% dos RCAs |
| Tags no vocabulario | ~33% compliance | 100% compliance |
| Evidence grading completo | 0/2 RCAs | 100% com confidence+sources |

---

## Notas

- **Zero features novos:** Este epic NAO adiciona capacidades novas. Faz funcionar o que v6.0 declarou.
- **Portabilidade:** Todas as alteracoes sao no framework generico. Nenhuma referencia a projeto especifico.
- **Backward compatible:** Projetos sem registros pre-existentes nao sao afetados.
- **Validavel:** Cada story pode ser validada contra os 2 RCAs existentes do projeto.
- **Honestidade:** Se algo nao funciona na pratica, o spec DEVE ser simplificado em vez de complicado.
