# /investigate — Root Cause Analysis v9.0 — Progressive Escalation

**VOCE DEVE EXECUTAR ESTE WORKFLOW AGORA.** O argumento do usuario eh o bug_report. Siga os passos abaixo imediatamente.

**Separacao de responsabilidades:** @qa INVESTIGA. @dev IMPLEMENTA. @architect REVISA (se escalation). @qa NUNCA implementa fixes.

---

## Principio

**Nunca aplique band-aid.** Todo problema eh investigado ate a origem. O fix DEVE ser na causa raiz.

---

## Como Usar

```
/investigate "bug"              → Progressive (auto-selects FAST/STANDARD/DEEP)
/investigate --deep "bug"       → Force DEEP pipeline (Complex/Chaotic)
/investigate --fast "bug"       → Force FAST (skip classification)
```

---

## Arquitetura: Progressive Escalation

```
Bug Report
  │
  ├─ 70% → FAST    (~2 min)  — Clear domain, single-file, pattern known
  │         grep → read → fix hypothesis → Origin Gate → done
  │
  ├─ 25% → STANDARD (~10 min) — Complicated, multi-file, unknown pattern
  │         classification → archaeology → causal analysis → Origin Gate → done
  │
  └─  5% → DEEP    (~30 min) — Complex/Chaotic, systemic, 3+ causal branches
            full 11-phase pipeline via rca/deep-pipeline.md
```

**Auto-escalation:** FAST escala para STANDARD se nao resolve. STANDARD escala para DEEP se complexidade emerge.

---

## Execucao

### Passo 1: Receber Bug Report

Coletar do argumento: descricao, error message, screenshots, stack trace.
Armazenar como `bug_report`.

### Passo 2: Routing Decision

**SE `--deep` flag:** Ir direto para DEEP (Passo 5).
**SE `--fast` flag:** Ir direto para FAST (Passo 3).

**SENAO — Progressive auto-routing:**

Avaliar rapidamente (30 segundos, sem subagent):

| Sinal | Aponta para |
|-------|-------------|
| Error message claro + 1 arquivo obvio | FAST |
| Stack trace aponta para 1 local | FAST |
| Sintoma vago, sem stack trace | STANDARD |
| Multiplos arquivos mencionados | STANDARD |
| Bug intermitente / race condition | DEEP |
| Seguranca / dados corrompidos | DEEP |
| Ja investigado antes (recurrence) | STANDARD+ |

**Quick recurrence check:** Verificar se `docs/qa/rca-knowledge/investigations.yaml` existe.
SE sim: buscar por similaridade (error message, arquivos afetados).
SE match com confidence >70%: mencionar investigacao anterior e SOP existente.

### Passo 3: FAST Layer (~2 min)

**Para:** Bugs com causa obvvia — erro claro, 1-2 arquivos, padrao conhecido.

**Execucao inline (sem subagents):**

1. **Localizar:** Grep/Read nos arquivos indicados pelo erro
2. **Diagnosticar:** Identificar a causa raiz no codigo
3. **Hipotese:** Formular fix hypothesis (1 frase)
4. **Verificar recurrence:** Checar se padrao ja apareceu antes (investigations.yaml)
5. **Origin Gate** (Passo 6) — OBRIGATORIO antes de qualquer fix

**Auto-escalation FAST → STANDARD:**
- [ ] Causa raiz NAO encontrada em 2 minutos de busca
- [ ] Bug envolve 3+ arquivos
- [ ] Padrao nao reconhecido
- [ ] Recurrence detectada (mesmo bug voltou)

SE qualquer checkbox marcado → Escalar para STANDARD (Passo 4).

**SE Origin Gate passa:** Gerar fix_requirements e delegar para @dev.

```yaml
fast_result:
  layer: FAST
  root_cause: "descricao"
  location: "arquivo:linha"
  fix_approach: "O QUE fazer"
  origin_gate: PASSED
  delegated_to: "@dev"
```

### Passo 4: STANDARD Layer (~10 min)

**Para:** Bugs com multiplas possibilidades, multi-file, padrao desconhecido.

**Execucao: inline + 1 subagent opcional para analise pesada.**

#### 4.1 Classification (inline, ~1 min)

Classificar rapidamente:
- **Dominio Cynefin:** Clear / Complicated / Complex / Chaotic
- **Severidade:** critical / high / medium / low
- **Scope:** single-file / multi-file / cross-module / system-wide

SE dominio = Complex ou Chaotic → Escalar para DEEP (Passo 5).

#### 4.2 Archaeology (inline, ~3 min)

Coleta de dados focada:
- `git log --oneline -20` nos arquivos suspeitos
- `git diff HEAD~5` para mudancas recentes
- Leitura dos arquivos relevantes
- Stack trace analysis

Produzir lista de **top 3 suspects** com evidencia.

#### 4.3 Causal Analysis (subagent sonnet, ~4 min)

Spawnar 1 subagent para analise causal:

```
Agent(model: sonnet, prompt: """
PLATAFORMA: {{platform}}
WORKING DIRECTORY: {{cwd}}
SHELL: bash com paths nativos — NAO converter para /mnt/c/ ou WSL.

Voce eh um analista causal. Dado o bug report e os suspects abaixo,
construa um grafo causal simples (max 5 nodes) identificando a root cause.

BUG: {{bug_report}}
SUSPECTS: {{suspects}}
EVIDENCE: {{evidence}}

Retorne YAML:
  root_cause: "descricao"
  confidence: 0.0-1.0
  causal_chain: ["evento1 → evento2 → sintoma"]
  contributing_factors: ["fator1"]
  affected_files: ["file1"]
  fix_approach: "O QUE fazer"
""")
```

#### 4.4 Origin Gate (Passo 6) — OBRIGATORIO

**Auto-escalation STANDARD → DEEP:**
- [ ] 3+ branches causais identificadas
- [ ] Confidence da analise causal < 0.5
- [ ] Bug envolve seguranca ou integridade de dados
- [ ] 4+ barreiras de defesa falharam
- [ ] Pattern match >80% com investigacao anterior que exigiu DEEP

SE qualquer checkbox marcado → Escalar para DEEP (Passo 5).

**SE Origin Gate passa:** Gerar fix_requirements e delegar para @dev.

```yaml
standard_result:
  layer: STANDARD
  escalated_from: FAST | null
  domain: "complicated"
  root_cause: "descricao"
  confidence: 0.85
  causal_chain: ["..."]
  fix_approach: "O QUE fazer"
  affected_files: ["file1"]
  origin_gate: PASSED
  delegated_to: "@dev"
```

### Passo 5: DEEP Layer (~30 min)

**Para:** Bugs sistemicos, Complex/Chaotic, 3+ causas, seguranca.

**Execucao: pipeline completo de 11 fases via subagents.**

**Carregar e executar:** Ler `.claude/commands/rca/deep-pipeline.md` e seguir as instrucoes de orquestracao la definidas. O deep-pipeline.md referencia os briefings individuais em `.claude/commands/rca/phase-*.md`.

**Pipeline resumido:**
```
Fase 0: classificacao + dedup
Fase 0.5: stabilization (Chaotic only)
Fase 1: git forensics + timeline
Fase 2∥3: pattern matching ∥ causal analysis (PARALELO)
Fase 4: adversarial challenge (opus)
Fase 5: barrier analysis (Swiss Cheese)
Fase 6: evidence grading E1-E4 (opus)
Fase 6.5: SDC Bridge → fix_requirements → @dev
Fase 8a: relatorio completo + investigation_record
Fase 8b: anti-patterns + SOPs + handoff
Fase 9: meta-learning + trends
```

```yaml
deep_result:
  layer: DEEP
  escalated_from: STANDARD | FAST | null
  # ... (resultado completo das 11 fases, ver deep-pipeline.md)
```

---

## Passo 6: Origin Gate (OBRIGATORIO em TODAS as layers)

**Checkpoint antes de QUALQUER fix ser delegado.** 5 perguntas:

| # | Pergunta | Criterio |
|---|----------|----------|
| 1 | **Origin Point:** Onde EXATAMENTE o problema comeca? | Arquivo + linha especificos |
| 2 | **Symptom Point:** Onde o sintoma aparece? | Deve ser DIFERENTE do origin |
| 3 | **Test at Origin:** Existe teste que valida a correcao NA ORIGEM? | Sim ou propor teste |
| 4 | **Is Band-Aid?** O fix proposto eh no sintoma ou na origem? | DEVE ser na origem |
| 5 | **Recurrence Guard:** O que previne este bug de voltar? | Teste ou validacao |

**Gate Decision:**
- **5/5 PASS** → Delegar fix para @dev
- **4/5 PASS** → Delegar com warning no campo faltante
- **3/5 ou menos** → BLOQUEAR. Refinar analise antes de delegar.
- **Pergunta 4 FAIL (band-aid)** → BLOQUEAR independente do score. Investigar mais fundo.

```yaml
origin_gate:
  origin_point: "arquivo:linha — descricao"
  symptom_point: "arquivo:linha — descricao"
  test_at_origin: "teste proposto ou existente"
  is_band_aid: false
  recurrence_guard: "teste/validacao que previne"
  score: 5
  decision: PASS
```

---

## Passo 7: Delegacao para @dev

Apos Origin Gate PASS:

1. **Gerar fix_requirements:**
```yaml
fix_requirements:
  root_cause: "descricao confirmada"
  fix_approach: "O QUE fazer (nao COMO)"
  affected_files: ["arquivo1.py"]
  tests_required:
    - "Teste que reproduz bug original"
    - "Teste na origem (nao no sintoma)"
  origin_gate: {score: 5, decision: PASS}
  layer: FAST | STANDARD | DEEP
```

2. **Detectar AIOS:** Verificar se `.aios-core/` existe no projeto.
   - **SE AIOS ativo:** Informar que fix_requirements devem ser passados para @dev via handoff
   - **SE AIOS inativo:** Apresentar fix_requirements ao usuario para implementacao

3. **Escalation check (STANDARD/DEEP):**
   SE barrier analysis indicou falhas arquiteturais → Recomendar revisao por @architect

---

## Pipeline Metrics (registrar no output final)

```yaml
pipeline_metrics:
  version: "v9.0"
  layer: FAST | STANDARD | DEEP
  escalation_path: [FAST, STANDARD] | [STANDARD, DEEP] | [DEEP] | [FAST]
  duration_estimate: "~2min | ~10min | ~30min"
  subagents_used: 0 | 1 | 11
  origin_gate: {score: 5, decision: PASS}
```

---

## Knowledge Base (referencia)

| Artefato | Path |
|----------|------|
| Investigacoes | `docs/qa/rca-knowledge/investigations.yaml` |
| SOPs | `docs/qa/rca-knowledge/sops/` |
| Anti-patterns | `docs/qa/rca-knowledge/anti-patterns/` |
| Tag taxonomy | `docs/qa/rca-knowledge/tag-taxonomy.yaml` |
| Phase briefings | `.claude/commands/rca/phase-*.md` |
| Deep pipeline | `.claude/commands/rca/deep-pipeline.md` |
