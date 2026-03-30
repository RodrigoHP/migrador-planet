# RCA Investigation — AIOS Task Wrapper

```yaml
task: rcaInvestigation()
responsavel: Multi-agente (orquestrado por @aios-master)
responsavel_type: Workflow
atomic_layer: Strategy

inputs:
  - campo: error_evidence
    tipo: string | array
    origem: User Input
    obrigatorio: true
    descricao: "Screenshots, logs, stack traces, ou descricao do(s) erro(s)"
  - campo: scope
    tipo: string
    origem: User Input
    obrigatorio: false
    descricao: "Arquivo, modulo ou stage afetado (auto-detectado se nao informado)"

outputs:
  - campo: investigation_report
    tipo: file
    destino: "docs/qa/investigations/rca-{date}-{slug}.md"
    persistido: true
    descricao: "Relatorio completo com root cause, fixes, testes, achados colaterais"
  - campo: backlog_items
    tipo: array
    destino: "Handoff artifact em .aios/handoffs/ para SDC"
    descricao: "Lista de stories criadas + handoff para @sm/@po"
  - campo: architectural_findings
    tipo: array
    destino: "Escalacao para @architect (se aplicavel)"
    descricao: "Problemas estruturais que requerem decisao arquitetural"
```

---

## Metodologia

Executar `/investigate` (`.claude/commands/investigate.md`).
O skill contem a metodologia completa de 5 fases de investigacao.
Esta task adiciona orquestracao AIOS multi-agente sobre essa metodologia.

---

## Pre-Conditions

- Pelo menos 1 indicio de erro (screenshot, log, stack trace, descricao)
- Acesso ao codebase para leitura

## Post-Conditions

- Root cause identificada e documentada
- Bugs classificados (trivial | minor | significativo) e documentados como stories conforme threshold
- Fix aplicado na origem (nao apenas no sintoma)
- Testes automatizados cobrindo o cenario (OBRIGATORIO)
- Relatorio de investigacao gerado
- Anti-pattern registrado no registry
- Achados colaterais como stories de backlog + handoff para SDC
- PR criado para main

---

## Documentacao de Bugs — Abordagem Hibrida

| Classificacao | Criterio | Acao |
|--------------|----------|------|
| **Trivial** | 1 arquivo, 1 linha (typo, guard) | Sem story. Documentar no relatorio. |
| **Minor** | Fix comportamental, 1-2 arquivos | Fix no PR do RCA. Story retroativa status=Done na Fase 5. |
| **Significativo** | >2 arquivos, muda comportamento observavel | Story criada ANTES do fix (Fase 2). Se multiplos bugs significativos da mesma investigacao, 1 story umbrella com cada bug como AC. |

---

## Fases Operacionais — Multi-Agent v3.0

| Fase | Nome | Agente | Skill Phases | Steps do Workflow |
|------|------|--------|-------------|-------------------|
| 1 | Triagem & Root Cause | @qa | Skill Fases 1-3 | dedup, triage, clustering, root_cause, exploration, architect_review |
| 2 | Stories dos Bugs | @sm | Skill Fase 5 (parcial) | create_branch, create_bug_stories |
| 3 | Implementacao | @dev | Skill Fase 4 | implement_and_test |
| 4 | Documentacao & QA Gate | @qa | Skill Fase 5 (parcial) | documentation, anti_pattern, verify_tests, qa_gate |
| 5 | Backlog | @sm | Skill Fase 5 (parcial) | create_backlog_stories + handoff SDC |
| 6 | Entrega | @devops | — | push_and_pr (autoridade exclusiva) |

### Delegacao Multi-Agente

Cada agente executa sua especialidade. Transicoes geram handoff artifacts em `.aios/handoffs/`:

```
@qa (investiga) → @sm (stories) → @dev (implementa) → @qa (revisa) → @sm (backlog) → @devops (entrega)
```

Escalacoes opcionais:
- `@architect` — se problema estrutural identificado na Fase 1
- `@po` — via handoff SDC para validacao de stories de backlog

---

## Execution Modes

| Modo | Descricao | Quando usar |
|------|-----------|-------------|
| **YOLO** (default) | Execucao continua multi-agente, zero confirmacoes, decisoes logadas | Problemas com stack trace claro |
| **Interactive** | Perguntas ao usuario em pontos de duvida | Problemas complexos ou ambiguos |
| **Pre-Flight** | Todas as perguntas antes de iniciar | Problemas criticos em producao |

**YOLO directive:** Orquestrador spawna cada agente sequencialmente. NAO pedir confirmacao entre fases. So interromper em erro bloqueante ou QA gate REJECT.

---

## Requisito de Testes

Todo fix DEVE incluir pelo menos 1 teste automatizado. SE nao eh possivel testar (fix puramente visual), o relatorio DEVE documentar o motivo. A secao "Testes Criados" no relatorio eh obrigatoria.

---

## Failure Recovery

| Fase | Falha | Acao |
|------|-------|------|
| 1 (@qa) | Investigacao falha | ABORT — nenhum codigo foi alterado |
| 2 (@sm) | Story creation falha | SKIP — continuar sem stories |
| 3 (@dev) | Implementacao falha | RETRY ate 3x — depois ESCALATE |
| 4 (@qa) | QA gate REJECT | LOOP — @dev corrige conforme feedback |
| 5 (@sm) | Backlog creation falha | SKIP — documentar no relatorio |
| 6 (@devops) | Push falha | RETRY quality gates — corrigir e retry |

---

## Handoff SDC

Ao criar stories de backlog, o workflow gera automaticamente um handoff artifact em `.aios/handoffs/handoff-rca-to-sdc-{date}.yaml`. Na proxima ativacao de @sm ou @po, o sistema sugere o proximo passo do SDC. O RCA NAO auto-executa o SDC (respeitando priorizacao do PO).

---

## Invocacao

```bash
# Via @aios-master (recomendado)
*workflow rca-investigation

# Via @qa
*task rca-investigation

# Standalone (qualquer agente)
/investigate
```

## Integracao com Workflows

```
Bug reportado → *workflow rca-investigation → stories criadas → handoff → SDC normal
```
