# /investigate — Root Cause Analysis v9.0 — Progressive Escalation

**VOCE DEVE EXECUTAR ESTE WORKFLOW AGORA.** O argumento do usuario eh o bug_report. Siga os passos abaixo imediatamente.

**Escopo:** Bugs (comportamento nao intencional), regressoes, e problemas de integridade de dados. NAO se aplica a feature requests ou melhorias.

**Separacao de responsabilidades:**
- **Modo interativo:** @qa investiga → gera fix_requirements → @dev implementa
- **Modo YOLO:** @qa investiga E implementa end-to-end (sem troca de agente)
- @architect REVISA (se escalation da barrier analysis)

---

## Principio

**Nunca aplique band-aid.** Todo problema eh investigado ate a origem. O fix DEVE ser na causa raiz.

---

## Como Usar

```
/investigate "bug"              → Comeca pelo FAST, escala se necessario
/investigate --deep "bug"       → Force DEEP pipeline (Complex/Chaotic)
/investigate --yolo "bug"       → Investigar + implementar fix + testar (zero paradas)
```

**Modo YOLO (recomendado para fluxo continuo):**
Combina `--yolo` com qualquer layer. Apos Origin Gate PASS, o workflow automaticamente:
1. Gera fix_requirements
2. Implementa o fix inline (papel @dev)
3. Roda testes
4. Reporta resultado final
Sem paradas, sem troca manual de agente, sem confirmacoes.

---

## Arquitetura: Progressive Escalation

```
Bug Report
  │
  └─ FAST: RECONHECER (~2 min, 0 subagents)
       Tecnica: Pattern match + Knowledge Check + leitura direta
       "Ja vi isso antes? Bate com pitfall/SOP conhecido?"
       │
       ├─ 70% → Reconheceu → SOP fast-track ou fix direto → Origin Gate → done
       │
       └─ 30% → Nao reconheceu → STANDARD: RASTREAR (+8 min, 1 subagent)
            Tecnica: Backward Trace + Git Forensics + Esperado vs Real
            "De onde vem o valor errado? Onde o dado corrompe?"
            │
            ├─ 25% → Rastreou corruption_point → Origin Gate → done
            │
            └─  5% → Incerteza/multiplas hipoteses → DEEP: PROVAR (+30 min, 11 subagents)
                 Tecnica: Adversarial Challenge + Barrier Analysis + Evidence Grading
                 "Consigo provar? Alguem refuta? Por que defesas falharam?"
                 Recebe: tudo do FAST+STANDARD (KC, trace, git, causal)
```

**Principio de escalacao:** Cada layer tem TECNICA PROPRIA. FAST reconhece, STANDARD rastreia, DEEP prova. Nenhum trabalho eh jogado fora — cada layer estende a anterior com tecnica mais poderosa.

---

## Execucao

### Passo 1: Receber Bug Report

Coletar do argumento: descricao, error message, screenshots, stack trace.
Armazenar como `bug_report`.

### Passo 2: Routing Decision

**SE `--deep` flag:** Ir direto para DEEP (Passo 5).
**SE `--yolo` flag:** Marcar `yolo_mode=true` (implementar fix automaticamente no Passo 7). Combina com qualquer layer.
**SE nao eh bug** (feature request, enhancement): PARAR — informar usuario.

**Default:** Iniciar pelo FAST (Passo 3). A escalacao para STANDARD/DEEP acontece naturalmente se o FAST nao resolver — nao eh preciso decidir antecipadamente.

**Unica excecao para skip FAST:** `--deep` flag explicito (bugs que sabidamente precisam de war room).

### Passo 3: FAST Layer (~2 min) — Tecnica: RECONHECIMENTO

**Para:** Bugs com causa obvia — erro claro, padrao conhecido, SOP disponivel.
**Abordagem:** Olhar do dev experiente. Ve o erro, reconhece o padrao, aplica fix conhecido.
**NAO faz:** Backward trace, git forensics, grafo causal — isso eh STANDARD/DEEP.

**Execucao inline (sem subagents):**

1. **Knowledge Check — Match contra padroes conhecidos:**
   SE `docs/qa/rca-knowledge/file-intelligence.yaml` existe:
   - Lookup pelo(s) arquivo(s) afetado(s) pelo erro
   - SE `risk: high` → ler `pitfalls` — o bug pode ser um padrao conhecido
   - SE `sops` listado → ler SOP em `docs/qa/rca-knowledge/sops/{sop}.yaml` — fast-track disponivel?
   - SE `temporal_coupling` listado → verificar se arquivo acoplado tambem precisa de fix
   SE `docs/qa/rca-knowledge/investigations.yaml` existe:
   - Match por error message substring nos `symptoms` de entries anteriores
   - SE match >80% (mesma mensagem + mesmo arquivo) → exibir investigacao anterior e fix usado

2. **Leitura direta — Olhar no ponto do erro:**
   - Grep/Read nos arquivos indicados pelo erro/stack trace
   - Ler o trecho de codigo onde o erro ocorre

3. **Pattern Match — Reconheco esse problema?**
   - **SIM + SOP existe** → SOP fast-track: seguir fix_steps do SOP → Origin Gate → done (~1 min)
   - **SIM sem SOP** → formular fix baseado no padrao reconhecido → Origin Gate → done
   - **NAO reconheco** → escalar para STANDARD

4. **Origin Gate** (Passo 6) — OBRIGATORIO antes de qualquer fix

**Escalation para STANDARD — criterios concretos:**
- [ ] Nao reconheco o padrao — nao bate com nenhum pitfall ou SOP
- [ ] Erro aponta para 3+ arquivos — nao sei qual eh a origem
- [ ] Duas explicacoes possiveis — preciso rastrear para decidir
- [ ] Recurrence detectada — fix anterior nao resolveu, preciso investigar mais fundo

SE nenhum marcado → Origin Gate → fix.
SE qualquer marcado → STANDARD (Passo 4). Passar: codigo lido + KC results + o que foi tentado.

```yaml
fast_result:
  layer: FAST
  root_cause: "descricao"
  matched_pattern: "pitfall ou SOP que bateu"
  fix_approach: "O QUE fazer"
  origin_gate: PASSED
  delegated_to: "@dev"
```

### Passo 4: STANDARD Layer (~10 min) — Tecnica: RASTREAMENTO

**Para:** Bugs que o FAST nao reconheceu — padrao desconhecido, multi-file, precisa rastrear.
**Abordagem:** Debugging metodico. Seguir o fluxo de dados para tras ate achar onde corrompe.
**Reutiliza do FAST:** Knowledge Check results + codigo ja lido. NAO repete.

#### 4.1 Classification (inline, ~1 min)

Classificar o bug:
- **Dominio Cynefin:** Clear / Complicated / Complex / Chaotic
- **Severidade:** critical / high / medium / low
- **Scope:** single-file / multi-file / cross-module / system-wide

SE dominio = Complex ou Chaotic → Escalar para DEEP (Passo 5).

#### 4.2 Esperado vs Real + Backward Trace (inline, ~4 min)

**Tecnica core do STANDARD — rastreamento sistematico:**

1. **Esperado vs Real:** Definir o contrato explicito: "Funcao X deveria retornar Y, mas retorna Z."
   SE git disponivel: "Antes do commit ABC retornava Y, depois retorna Z."

2. **Backward Trace:** Partir do valor errado (Z) e rastrear para tras pela cadeia de chamadas:
   - Quem chamou essa funcao? Com qual input?
   - Essa funcao recebeu input correto? SE sim → bug esta AQUI. SE nao → subir mais um nivel.
   - Repetir ate achar o **corruption_point** — onde o dado passa de correto para incorreto.
   - Maximo 5 saltos. SE nao achou em 5 → registrar os saltos feitos e escalar.

3. **Git Forensics:** Complementar o trace com contexto temporal:
   - `git log --oneline -20` nos arquivos do trace (+ temporal couplings do KC)
   - `git blame` nas linhas suspeitas — quem mudou e quando?
   - `git diff HEAD~5` — o que mudou recentemente nesses arquivos?

4. **Estado intermediario:** SE backward trace nao isolou o ponto em 5 saltos:
   - Adicionar logs/prints temporarios nos pontos intermediarios
   - Rodar e comparar estado real vs esperado
   - Isolar o salto exato onde o dado corrompe

Produzir: **corruption_point** (arquivo:linha) + **expected_vs_actual** + **top 3 suspects** com evidencia.

#### 4.3 Causal Analysis — segunda opiniao (subagent sonnet, ~4 min)

Spawnar 1 subagent para validar o trace e construir grafo causal:

```
Agent(model: sonnet, prompt: """
CRITICO — PATHS: Voce esta rodando em WINDOWS com Git Bash.
Use paths Windows nativos (C:\...). NUNCA use /mnt/c/ ou paths WSL.
Todos os comandos git e ferramentas usam paths Windows.
NAO faca cd — use paths absolutos ou rode no diretorio padrao.

Voce eh um analista causal. O investigador principal ja fez backward trace e identificou suspects.
Sua tarefa eh VALIDAR o trace e construir um grafo causal.

BUG: {inserir bug_report completo}

BACKWARD TRACE DO INVESTIGADOR:
  corruption_point: {arquivo:linha do passo 4.2}
  expected_vs_actual: {contraste do passo 4.2}
  suspects: {top 3 suspects com evidencia do passo 4.2}

EVIDENCE (git):
  {inserir git log + diffs + blame relevantes do passo 4.2}

CONHECIMENTO PREVIO (pitfalls e SOPs do Knowledge Check):
  {inserir pitfalls e SOPs relevantes do KC do FAST — passo 3.1}

INSTRUCOES:
1. VALIDAR o corruption_point: o trace esta correto? O dado realmente corrompe ali?
2. GRAFO CAUSAL: Construir grafo simples (max 5 nodes) conectando origem → corrupcao → sintoma
3. SE discordar do trace: propor corruption_point alternativo com evidencia

Retorne YAML:
  agrees_with_trace: true | false
  corruption_point: "arquivo:linha — onde o dado corrompe"
  confidence: 0.0-1.0
  expected_vs_actual: "funcao X deveria retornar Y mas retorna Z"
  causal_chain: ["origem → corrupcao → sintoma"]
  contributing_factors: ["fator1"]
  affected_files: ["file1"]
  fix_approach: "O QUE fazer — fix DEVE ser no corruption_point"
  alternative_hypothesis: null | "descricao se discordou"
""")
```

#### 4.4 Origin Gate (Passo 6) — OBRIGATORIO

**Escalation para DEEP — criterios concretos:**
- [ ] Subagent DISCORDOU do trace (agrees_with_trace: false) E confidence < 0.5 em ambos
- [ ] Bug envolve seguranca ou integridade de dados corrompidos
- [ ] Multiplas defesas ausentes — precisa barrier analysis para entender por que nada pegou
- [ ] Pattern match >80% com investigacao anterior que exigiu DEEP

SE nenhum marcado → Origin Gate → fix.
SE qualquer marcado → Escalar para DEEP (Passo 5). Passar como contexto:
```yaml
standard_handoff:
  kc_results: {pitfalls, SOPs, risk scores do FAST}
  corruption_point: "arquivo:linha"
  expected_vs_actual: "descricao"
  backward_trace: {saltos feitos}
  git_forensics: {log, blame, diff relevantes}
  causal_analysis: {resultado do subagent}
  confidence: 0.XX
```

```yaml
standard_result:
  layer: STANDARD
  escalated_from: FAST | null
  domain: "complicated"
  root_cause: "descricao"
  corruption_point: "arquivo:linha"
  confidence: 0.85
  expected_vs_actual: "funcao X deveria retornar Y mas retorna Z"
  causal_chain: ["..."]
  fix_approach: "O QUE fazer"
  affected_files: ["file1"]
  origin_gate: PASSED
  delegated_to: "@dev"
```

### Passo 5: DEEP Layer (~30 min) — Tecnica: VERIFICACAO

**Para:** Bugs sistemicos, Complex/Chaotic, hipoteses concorrentes, seguranca.
**Abordagem:** Provar a hipotese com multiplos especialistas que se desafiam.
**Reutiliza do STANDARD:** backward trace, corruption_point, git forensics, causal analysis.
**Tecnicas UNICAS (nao existem em outras layers):** Adversarial Challenge, Barrier Analysis, Evidence Grading.

**Execucao: pipeline de 11 fases via subagents.**

**CRITICO — Passar standard_handoff:** Ao montar os placeholders do deep-pipeline.md, incluir o `standard_handoff` (KC results, corruption_point, backward trace, git forensics, causal analysis) como contexto adicional em `{{bug_report}}`. As Fases 1-3 do DEEP APROFUNDAM a partir desses dados — nao recomeçam do zero.

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
Origin Gate: 5-point checkpoint (orquestrador)
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
| 4 | **Is Origin Fix?** O fix proposto eh na ORIGEM (nao no sintoma)? | is_band_aid=false para PASS |
| 5 | **Recurrence Guard:** O que previne este bug de voltar? | Teste ou validacao |

**Gate Decision:**
- **5/5 PASS** → Delegar fix para @dev
- **4/5 PASS** → Delegar com warning no campo faltante
- **3/5 ou menos** → BLOQUEAR. Refinar analise antes de delegar.
- **Pergunta 4 FAIL (is_band_aid=true)** → BLOQUEAR independente do score. Investigar mais fundo.

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

## Passo 7: Delegacao e Implementacao

Apos Origin Gate PASS, gerar fix_requirements:

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

### Modo YOLO (--yolo flag OU detectado automaticamente)

**Deteccao automatica de YOLO:** SE o usuario ja esta em modo yolo/auto-approve OU SE o contexto indica fluxo continuo (ex: veio de SDC, qa-loop, ou pipeline automatizado) → tratar como YOLO.

**Fluxo completo sem paradas:**

1. **Implementar fix diretamente** (assumir papel @dev):
   - Editar os `affected_files` conforme `fix_approach`
   - Aplicar fix NA ORIGEM (nao no sintoma — Origin Gate ja validou)
   - Adicionar/atualizar testes conforme `tests_required`

2. **Rodar testes:**
   - Executar suite de testes relevante
   - SE testes falham → ajustar fix e re-testar (max 3 tentativas)
   - SE falha persistente → PARAR e reportar ao usuario

3. **Reportar resultado:**
```yaml
fix_result:
  status: FIXED | FAILED
  fix_applied: "descricao do que foi feito"
  files_changed: ["arquivo1.py"]
  tests_added: ["test_xxx.py"]
  tests_passing: true
  origin_gate: {score: 5, decision: PASS}
  layer: FAST | STANDARD | DEEP
```

4. **Escalation check:** SE barrier analysis indicou falhas arquiteturais → recomendar revisao por @architect apos o fix.

### Modo Interativo (default sem --yolo)

1. Apresentar fix_requirements ao usuario
2. Perguntar: "Implementar agora (yolo) ou delegar para @dev?"
   - **SE usuario aceita:** Executar fluxo YOLO acima
   - **SE usuario delega:** Gerar handoff artifact em `.aios/handoffs/` para @dev

---

## Passo 8: Persistencia (OBRIGATORIO em TODAS as layers)

Persistir dados estruturados para que agentes AIOS aprendam entre investigacoes.
Roda SEMPRE, independente de modo YOLO ou interativo.
**3 artefatos obrigatorios** + **3 acoes condicionais**.

### 8.1 — Investigation Registry + Effectiveness Review + Acoes Condicionais

**Destino:** `docs/qa/rca-knowledge/investigations.yaml` (knowledge base central).
SE arquivo nao existe: criar com header `investigations:`.

#### 8.1a — Effectiveness Review (ANTES do append)

ANTES de registrar a nova investigacao, revisar entries anteriores:

1. Filtrar entries com `effectiveness: pending` E `date` ha mais de 7 dias
2. Para cada entry pending ha >7 dias:
   - `git log --since="7 days ago" --grep="{keyword dos symptoms}"` — recorreu?
   - Grep por `anti_patterns` search_pattern no codebase — guard presente?
   - Decidir:
     - Nenhuma recorrencia → `effectiveness: resolved`
     - Variante apareceu → `effectiveness: partial`
     - Mesmo bug recorreu → `effectiveness: ineffective`
   - Registrar `effectiveness_reviewed_at` com data de hoje
3. SE `effectiveness: ineffective` → incluir ALERTA no output
4. SE nenhuma pending ha >7 dias → prosseguir

**Por que aqui e nao em Phase 0:** Phase 0 so roda em DEEP (5% dos bugs).
Aqui roda em TODAS as layers — todo bug resolve effectiveness de anteriores.

#### 8.1b — Append Investigation Record

APPEND entrada com campos proporcionais a layer:

**FAST (schema minimo — mesma estrutura que STANDARD, menos campos):**
```yaml
- id: "rca-{date}-{slug}"
  date: "{YYYY-MM-DD}"
  layer: FAST
  symptoms: ["{sintoma}"]
  domain: "{clear|complicated}"
  severity: "{critical|high|medium|low}"
  scope: "{single-file|multi-file}"
  root_causes:
    - pattern: "{pattern_name}"
      location: "{arquivo:linha}"
      evidence_level: E1_confirmed
  fix_approach: "{O QUE}"
  files_affected: ["{arquivo}"]
  tags: ["{error_type}", "{root_cause_category}"]
  effectiveness: pending
  effectiveness_reviewed_at: null
  sop_generated: null
  sop_fast_track_used: false
  confidence_score: null
  dedup_status: new
  related_rcas: null
  report: null
  anti_patterns: null
  origin_gate: {score: 5, decision: PASS, is_band_aid: false}
```

**STANDARD (+ campos extras):**
```yaml
  contributing_factors: ["{fator}"]
  causal_chain: ["evento1 → evento2 → sintoma"]
  escalated_from: FAST | null
```

**DEEP:** Schema completo v9.0 (19+ campos) — gerido pela Fase 8a.

**VALIDACAO OBRIGATORIA antes do append** — todo entry DEVE ter:
```yaml
# Campos obrigatorios (todas as layers):
required_fields:
  - id          # "rca-{YYYY-MM-DD}-{slug}" — formato fixo
  - date        # "YYYY-MM-DD"
  - layer       # FAST | STANDARD | DEEP
  - symptoms    # lista nao vazia
  - fix_approach # string
  - files_affected # lista nao vazia
  - tags        # lista, seguir tag-taxonomy.yaml
  - effectiveness # pending (default para novo)

# Campos obrigatorios STANDARD+DEEP:
standard_fields:
  - domain      # clear | complicated | complex | chaotic
  - severity    # critical | high | medium | low
  - scope       # single-file | multi-file | cross-module | systemic
  - root_causes # lista de {pattern, location, evidence_level}

# Valores validos (NUNCA inventar fora destes):
enums:
  effectiveness: [pending, resolved, partial, ineffective]
  scope: [single-file, multi-file, cross-module, systemic]
  evidence_level: [E1_confirmed, E2_correlated, E3_hypothesized]
  dedup_status: [new, related, duplicate]
  layer: [FAST, STANDARD, DEEP]

# root_causes DEVE ser lista de objetos, NUNCA string:
#   CORRETO:  root_causes: [{pattern: "x", location: "y", evidence_level: E1_confirmed}]
#   ERRADO:   root_cause: "descricao string"
```
SE entry nao passar validacao → corrigir ANTES de salvar.

#### 8.1c — Acoes Condicionais (DEPOIS do append)

**SOP Auto-generation:** SE mesma `root_cause_category` tag aparece 2+ vezes em investigations.yaml
E nenhum SOP existe para essa tag:
- Gerar SOP em `docs/qa/rca-knowledge/sops/sop-{tag}.yaml`
- Campos: `fix_steps`, `times_applied: 0`, `effectiveness_rate: null`, `detection.search_pattern`

**QA MEMORY Update:** Verificar se `.aios-core/development/agents/qa/MEMORY.md` precisa de update:
- SE novo anti-pattern → adicionar em "Known Problem Areas"
- SE area com 2+ bugs (mesmo diretorio) → atualizar contagem
- SE padrao visto em 3+ contextos → mover para "Promotion Candidates"

**Handoff RCA→SDC:** SE collateral findings encontrados (problemas ALEM do bug original):
- Gerar handoff artifact em `.aios/handoffs/handoff-rca-to-sdc-{date}-{slug}.yaml`
- Marcar `consumed: false` para o proximo agente ativado

### 8.2 — File Intelligence Index (TODAS as layers)

**Destino:** `docs/qa/rca-knowledge/file-intelligence.yaml`

Regenerar o indice de inteligencia por arquivo a partir de investigations.yaml.
Este indice eh consumido por @dev (risk briefing), @qa (review proporcional), e /investigate (quick knowledge check).

Para cada arquivo em `files_affected` de todas as investigations:
```yaml
{arquivo}:
  risk: high | medium | low    # high=3+ bugs OU critical, medium=2, low=1
  bug_count: N
  last_incident: "{YYYY-MM-DD}"
  incidents: ["{rca-ids}"]
  patterns: ["{root_cause_categories}"]
  anti_patterns: ["{AP-IDs}"]
  sops: ["{sop-ids}"]           # SOPs aplicaveis a este arquivo
  pitfalls:                      # 1 frase por bug — O QUE deu errado
    - "{descricao curta e acionavel}"
  temporal_coupling: ["{arquivos que mudam junto}"]  # co-ocorrencia em 2+ bugs
```

**Risk scoring:**
- `high`: 3+ bugs OU qualquer bug severity=critical
- `medium`: 2 bugs
- `low`: 1 bug

**Temporal coupling:** Dois arquivos aparecem juntos em `files_affected` de 2+ investigations → sao temporally coupled. Mudar um sem checar o outro eh risco.

**IMPORTANTE:** Este arquivo eh auto-gerado. NAO editar manualmente. Sempre regenerar a partir de investigations.yaml.

### 8.3 — Investigation Artifact (STANDARD e DEEP)

**Destino:** `docs/qa/rca-knowledge/investigations/rca-{date}-{slug}.yaml`

Salvar o output estruturado da investigacao com origin_gate + fix_result:

```yaml
investigation:
  id: "rca-{date}-{slug}"
  layer: STANDARD | DEEP
  origin_gate:
    origin_point: "{arquivo:linha}"
    symptom_point: "{arquivo:linha}"
    test_at_origin: "{teste}"
    is_band_aid: false
    recurrence_guard: "{guard}"
    score: 5
    decision: PASS
  fix_requirements:
    root_cause: "{descricao}"
    fix_approach: "{O QUE}"
    affected_files: ["{arquivo}"]
    tests_required: ["{teste}"]
  fix_result:
    status: FIXED | DELEGATED
    fix_commit: "{hash}" | null
```

**FAST nao gera este artefato** — o registro em investigations.yaml + file-intelligence.yaml eh suficiente.

### Regra de Ouro

**Toda investigacao alimenta o sistema de 3 formas:**
1. `investigations.yaml` → registry central — recurrence detection, pattern matching, effectiveness tracking
2. `file-intelligence.yaml` → indice por arquivo — risk briefing para @dev, review proporcional para @qa, quick knowledge check para /investigate
3. `docs/qa/rca-knowledge/investigations/` → artefato com origin_gate + fix_result detalhados (STANDARD+DEEP)

**Fluxo do conhecimento:**
```
Bug investigado → investigations.yaml (registry)
                → file-intelligence.yaml (indice)
                → Proximo @dev recebe risk briefing ao tocar nos mesmos arquivos
                → Proximo @qa foca review nos arquivos de risco
                → Proximo /investigate consulta KB em 30 segundos (todas as layers)
```

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

## Artefatos e Paths (referencia)

**3 artefatos de persistencia (Passo 8):**

| Artefato | Path | Proposito | Layers |
|----------|------|-----------|--------|
| Investigation registry | `docs/qa/rca-knowledge/investigations.yaml` | Registry central para pattern matching, recurrence e effectiveness | TODAS |
| File intelligence index | `docs/qa/rca-knowledge/file-intelligence.yaml` | Indice por arquivo — risk, pitfalls, temporal coupling (auto-gerado) | TODAS |
| Investigation artifact | `docs/qa/rca-knowledge/investigations/rca-{date}-{slug}.yaml` | Origin gate + fix result detalhados | STANDARD+DEEP |

**Knowledge base (consumida pelo pipeline e por @dev/@qa):**

| Artefato | Path |
|----------|------|
| File intelligence | `docs/qa/rca-knowledge/file-intelligence.yaml` |
| Anti-patterns registry | `docs/qa/rca-knowledge/anti-patterns.yaml` |
| SOPs | `docs/qa/rca-knowledge/sops/` |
| Tag taxonomy | `docs/qa/rca-knowledge/tag-taxonomy.yaml` |
| QA Agent memory | `.aios-core/development/agents/qa/MEMORY.md` |

**Pipeline (definicao do workflow):**

| Artefato | Path |
|----------|------|
| Router v9.0 | `.claude/commands/investigate.md` |
| Deep pipeline | `.claude/commands/rca/deep-pipeline.md` |
| Phase briefings | `.claude/commands/rca/phase-*.md` |

**Nota sobre numeracao de fases DEEP:** Fases 0→0.5→1→2→3→4→5→6→6.5→8a→8b→9.
Fase 7 nao existe — foi absorvida em 6.5 (SDC Bridge). Fase 8 foi dividida em 8a+8b.
