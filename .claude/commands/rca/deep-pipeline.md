# RCA Deep Pipeline — Orquestração Multi-Model

> Pipeline completo para bugs Complex/Chaotic ou escalados de STANDARD.
> Briefings de cada fase estao em arquivos separados: `.claude/commands/rca/phase-*.md`
> Este arquivo contem APENAS a logica de orquestracao.

**EXECUTE AGORA — este eh um workflow executavel.**

## Pipeline Overview

```
Fase 0: Agent(sonnet)        → classificacao + dedup
Fase 0.5: Agent(sonnet)      → stabilization (Chaotic only)
Fase 1: Agent(sonnet)        → coleta de dados (git forensics)
Fase 2∥3: PARALELO
  ├─ Fase 2: Agent(sonnet)   → pattern matching (knowledge base)
  └─ Fase 3: Agent(sonnet)   → analise causal (grafo)
Fase 4: Agent(opus)          → challenge hipoteses (adversarial)
Fase 5: Agent(sonnet)        → barrier analysis (Swiss Cheese)
Fase 6: Agent(opus)          → evidence grading (E1-E4)
Fase 6.5: Orquestrador       → gerar fix_requirements + delegar @dev
Fase 8a: Agent(sonnet)       → relatorio + investigation_record
Fase 8b: Agent(sonnet)       → anti-patterns + SOPs + handoff
Fase 9: Agent(sonnet)        → meta-learning + trends
```

## Contexto de Plataforma (OBRIGATORIO)

Incluir no TOPO de cada briefing:
```
PLATAFORMA: {{platform}}
WORKING DIRECTORY: {{cwd}}
SHELL: bash WINDOWS (Git Bash). CRITICO: paths Windows (C:\...). NUNCA /mnt/c/. NUNCA cd — use paths absolutos.
```

## Sequencia por Dominio

| Dominio | Fases |
|---------|-------|
| Complex | 0→1→2∥3→4→5→6→6.5→8a→8b→9 |
| Chaotic | 0→0.5→1→2∥3→4→5→6→6.5→8a→8b→9 |

## Execucao

Para cada fase:

1. **Carregar briefing:** Ler `.claude/commands/rca/phase-{N}-{name}.md`
2. **Montar prompt:** Substituir placeholders ({{bug_report}}, {{resultado_fase_N}}, etc.) com dados reais
3. **Spawnar subagent:** `Agent(model: sonnet/opus conforme tabela, prompt: briefing montado)`
4. **Validar resultado:**
   - Campos obrigatorios presentes?
   - YAML parseavel?
   - Conteudo nao vazio?
5. **SE validacao falha → RETRY 1x** com feedback dos campos faltantes
6. **SE retry falha → FALLBACK inline** (orquestrador executa usando briefing como guia)
7. **Armazenar resultado** para proximas fases

### Placeholder Mapping (responsabilidade do orquestrador)

| Placeholder | Fonte | Fallback se null |
|-------------|-------|------------------|
| `{{bug_report}}` | Input do usuario + `standard_handoff` se escalado | OBRIGATORIO |
| `{{standard_handoff}}` | Contexto acumulado do FAST+STANDARD (KC, trace, git, causal) | `null` (primeira vez no DEEP, sem escalacao) |
| `{{resultado_fase_N}}` | Output da Fase N | "Fase N nao executada ou falhou" |
| `{{root_causes_final}}` | `resultado_fase_4.final_ranking` (pos-challenge) | `resultado_fase_3.root_causes` (pre-challenge) |
| `{{investigations_yaml}}` | Ler `docs/qa/rca-knowledge/investigations.yaml` | `investigations: []` (YAML vazio valido) |
| `{{known_anti_patterns}}` | Ler `docs/qa/rca-knowledge/anti-patterns.yaml` | `anti_patterns: []` (YAML vazio valido) |
| `{{sops_content}}` | Ler `docs/qa/rca-knowledge/sops/*.yaml` | `sops: []` (YAML vazio valido) |
| `{{tag_taxonomy}}` | Ler `docs/qa/rca-knowledge/tag-taxonomy.yaml` | Usar categorias default do phase-8b |
| `{{resultado_fase_0_5}}` | Output da Fase 0.5 | "Fase 0.5 nao executada (dominio nao Chaotic)" |
| `{{resultado_sdc}}` | Output da Fase 6.5 | OBRIGATORIO (orquestrador gera) |

**IMPORTANTE:** Se arquivo da knowledge base nao existir, usar fallback YAML valido (lista vazia). NUNCA usar string descritiva como fallback — subagents parseiam o conteudo como YAML.

**STANDARD HANDOFF:** Quando DEEP eh escalado de STANDARD, o `standard_handoff` contem:
- KC results (pitfalls, SOPs, risk scores)
- corruption_point + expected_vs_actual (backward trace)
- git forensics (log, blame, diff)
- causal analysis do subagent STANDARD
Incluir no `{{bug_report}}` como secao "CONTEXTO PREVIO (FAST+STANDARD)". As Fases 1-3 APROFUNDAM a partir desses dados — NAO recomeçam do zero.

**Paralelismo (Fase 2 ∥ 3):**
Spawnar ambas em paralelo. SE uma falha e outra sucede: continuar com parcial.

## Origin Gate (Orquestrador executa ANTES da Fase 6.5)

Checkpoint obrigatorio entre Fase 6 e 6.5. Usar os dados de Fase 6 (evidence grading) + Fase 5 (barriers):

| # | Pergunta | Criterio |
|---|----------|----------|
| 1 | **Origin Point:** Onde EXATAMENTE o problema comeca? | Arquivo + linha especificos |
| 2 | **Symptom Point:** Onde o sintoma aparece? | DIFERENTE do origin |
| 3 | **Test at Origin:** Existe teste que valida a correcao NA ORIGEM? | Sim ou propor teste |
| 4 | **Is Band-Aid?** O fix proposto eh no sintoma ou na origem? | DEVE ser na origem |
| 5 | **Recurrence Guard:** O que previne este bug de voltar? | Teste ou validacao |

**Gate Decision:**
- 5/5 PASS → Prosseguir para Fase 6.5
- 4/5 PASS → Prosseguir com warning
- 3/5 ou menos → BLOQUEAR. Voltar para Fase 4 (re-challenge) ou coletar mais evidencia.
- Pergunta 4 FAIL (band-aid) → BLOQUEAR independente do score.

```yaml
origin_gate:
  origin_point: "arquivo:linha — descricao"
  symptom_point: "arquivo:linha — descricao"
  test_at_origin: "teste proposto ou existente"
  is_band_aid: false
  recurrence_guard: "teste/validacao"
  score: 5
  decision: PASS | WARN | BLOCK
```

## Fase 6.5 — SDC Bridge (Orquestrador executa diretamente)

**Pre-requisito:** Origin Gate PASS ou WARN (nunca BLOCK).

1. Gerar fix_requirements a partir de Fase 6 + Origin Gate:
```yaml
resultado_sdc:
  fix_requirements:
    root_cause: "descricao confirmada da Fase 6"
    fix_approach: "O QUE fazer (nao COMO)"
    affected_files: ["arquivo1.py"]
    tests_required: ["teste1", "teste2"]
    evidence_level: "E1_confirmed"
    origin_gate: {score: 5, decision: PASS}
  story_draft_path: "docs/stories/backlog/fix-rca-{date}-{slug}.md"
  escalated_to_architect: false
  delegated_to: "@dev"
```
2. Criar story draft em `docs/stories/backlog/fix-rca-{date}-{slug}.md`
3. **Verificar escalation:** Contar quantos criterios YES na `resultado_fase_5.escalation_assessment`:
   SE 1+ criterios atingidos:
   - Escalar para @architect
   - Story fica no backlog para @architect → @dev
4. **SE 0 criterios atingidos — Delegar para @dev:**
   - Apresentar fix_requirements ao usuario
   - Instruir delegacao para @dev
5. **Modo interativo:** @qa delega fix para @dev. **Modo YOLO:** @qa implementa end-to-end.

## Salvar Artefatos (RESPONSABILIDADE DO ORQUESTRADOR)

Subagents NUNCA escrevem arquivos. O orquestrador salva:

- Fase 0 → `investigations.yaml` (effectiveness reviews)
- Fase 2 → SOP `times_applied` (se fast-track aceito)
- Fase 6.5 → story draft em `docs/stories/backlog/`
- Fase 8a → relatorio em `docs/qa/investigations/rca-{date}-{slug}.md`
- Fase 8b → `anti-patterns.yaml`, handoff em `.aios/handoffs/`, backlog stories
- Fase 9 → `investigations.yaml`, SOPs, tag promotions
- **Consolidate** → `file-intelligence.yaml` (regenerado de investigations.yaml — Passo 8.2)

## Pipeline Metrics (registrar no relatorio)

```yaml
pipeline_metrics:
  layer: DEEP
  phases_via_subagent: [0, 1, 2, 3, 4, 5, 6, 8a, 8b, 9]
  phases_via_fallback: []
  phases_parallel: [[2, 3]]
  escalated_from: STANDARD | null
  escalation_reason: "motivo"
```
