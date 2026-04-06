# Investigation Engine v10 — AI-Native Design Document

> Design document para evolucao futura. Registra decisoes, trade-offs e filosofia.
> Source of truth para implementacao: `.claude/commands/investigate.md`

## Filosofia

```
v9.0: Pensado como dev humano senior faria
v10:  Pensado como AI-engine faria

A IA nao julga. Nao sente. Nao reconhece.
A IA executa tools → recebe outputs → outputs decidem.
```

## Arquitetura: 3 Estrategias Cognitivas de Busca

| Layer | Estrategia | Pergunta | Custo |
|-------|-----------|----------|-------|
| FAST | RETRIEVAL (lembrar) | "Sei a resposta?" | 0 subagents, ~2 min |
| STANDARD | REASONING (deduzir) | "Consigo deduzir?" | 1 subagent, ~10 min |
| DEEP | DELIBERATION (provar) | "Consigo provar?" | 11 subagents, ~30 min |

**Por que 3 layers:**
- RETRIEVAL: 70% dos bugs sao padroes conhecidos — lookup resolve
- REASONING: 25% precisam seguir cadeia causal — trace linear resolve
- DELIBERATION: 5% precisam provar entre hipoteses — multi-agent resolve
- Custo proporcional ao problema

**Escalacao = capacidade ausente:**
- FAST nao tem TRACE → se problema exige seguir dados → STANDARD
- STANDARD nao tem PROVA → se problema exige refutar hipoteses → DEEP
- A tecnica atinge seu limite natural → proxima tecnica

## 12 Tecnicas Nomeadas

### FAST (Retrieval)

| ID | Tecnica | O Que Faz | Produz |
|----|---------|-----------|--------|
| T1 | KC Lookup | grep investigations.yaml + lookup file-intelligence.yaml | EXACT/SIMILAR/PARTIAL/MISS |
| T2 | Leitura Direta | Read codigo no ponto do erro | codigo fonte visivel + file count |
| T3 | Pattern Match | Comparar com pitfalls/SOPs conhecidos | candidato a root cause |

### STANDARD (Reasoning)

| ID | Tecnica | O Que Faz | Produz |
|----|---------|-----------|--------|
| T4 | Expected vs Actual | Definir contrato explicito do desvio | "deveria Y, retorna Z" |
| T5 | Backward Trace | Seguir dados para tras hop a hop (max 5) | corruption_point OU bifurcacao |
| T6 | Git Forensics | git log, blame, diff nos arquivos do trace | contexto temporal |
| T7 | Segunda Opiniao | Subagent valida trace + constroi grafo causal | agrees (true/false) + alternativa |

### DEEP (Deliberation)

| ID | Tecnica | O Que Faz | Produz |
|----|---------|-----------|--------|
| T8 | Pattern Matching Amplo | Match contra TODA a KB | patterns + SOP confidence |
| T9 | Analise Causal (grafo) | Grafo completo de causalidade | multiplos caminhos |
| T10 | Adversarial Challenge | Tentar REFUTAR cada hipotese | hipoteses sobreviventes + refutadas |
| T11 | Barrier Analysis | Por que defesas nao pegaram | falhas sistemicas |
| T12 | Evidence Grading | Classificar achados E1-E4 | ranking por nivel de prova |

## 3 Checks de Validacao

Aplicados apos qualquer layer encontrar candidato a root cause.

| Check | Pergunta | Verificacao | Resultado |
|-------|----------|-------------|-----------|
| CHAIN | Existe caminho no codigo do candidato ate o sintoma? | Read cada funcao na cadeia | COMPLETE / BROKEN |
| SCOPE | Candidato explica TODOS os sintomas? | Contar sintomas explicados | FULL / PARTIAL |
| DEPTH | Linha do candidato GERA ou RECEBE o valor errado? | Read 1 linha de codigo | SOURCE / MIDDLE |

**Regra:** So COMPLETE + FULL + SOURCE = root cause confirmada. Qualquer outro = escalar.

**DEPTH eh o check mais poderoso** — pela primeira vez o sistema tem mecanismo mecanico para distinguir raiz de sintoma.

**Proporcionalidade:**
- FAST: usa CHAIN + SCOPE + DEPTH (nao tem trace)
- STANDARD: usa SCOPE + DEPTH + agrees (trace implica CHAIN)
- DEEP: usa adversarial + evidence grading (validacao propria)

## Escape Hatch

Apos checks passarem, 1 pergunta adicional:

```
"Os checks passaram. Algo no codigo contradiz essa conclusao?"
  SIM → investigar mais (modelo forte viu algo)
  NAO → confirmar root cause (modelo fraco segue protocolo)
```

- Modelo fraco: sempre diz NAO → protocolo funciona normal
- Modelo forte: pode sinalizar desconfianca → investiga mais
- **Preserva teto alto (Opus) sem baixar piso (Haiku)**

## Metricas de Decisao (14 sinais)

### FAST (6 sinais)

| Sinal | Tipo | Fonte |
|-------|------|-------|
| KC match level | EXACT/SIMILAR/PARTIAL/MISS | grep investigations.yaml |
| KC effectiveness | effective/ineffective | campo em investigations.yaml |
| File count | 1/2+/0 | stack trace ou grep |
| Check CHAIN | COMPLETE/BROKEN | Read cadeia de chamadas |
| Check SCOPE | FULL/PARTIAL | contar sintomas explicados |
| Check DEPTH | SOURCE/MIDDLE | Read 1 linha |

### STANDARD (6 sinais)

| Sinal | Tipo | Fonte |
|-------|------|-------|
| Cynefin deterministico | Complicated/Complex/Chaotic | contagens (arquivos, recurrence, coupling) |
| Trace result | converged/bifurcated/inconclusive | backward trace output |
| Hop count | <=5 / >5 | contagem de hops |
| Check SCOPE | FULL/PARTIAL | contar sintomas |
| Check DEPTH | SOURCE/MIDDLE | Read linha do corruption_point |
| Subagent agrees | true/false | campo YAML do subagent |

### DEEP (2 sinais)

| Sinal | Tipo | Fonte |
|-------|------|-------|
| Adversarial survived | yes/no | output do challenger |
| Evidence level | >=E1 / <E1 | output do evidence grader |

**Total: 14 sinais. Todos binarios/contaveis/enum. Zero self-assessment.**

## KC Granular (4 niveis)

| Nivel | Criterio | Acao |
|-------|----------|------|
| EXACT | Mesma error message + mesmo arquivo | SOP fast-track |
| SIMILAR | Mesmo arquivo aparece em KB | Direcao conhecida, FAST tenta |
| PARTIAL | Mesma tag de root_cause_category | Contexto util |
| MISS | Nenhum match | Sem conhecimento previo |

**Implementacao:** Tudo por substring match e lookup. Zero semantica.

## Cynefin Deterministico

Executado no inicio do STANDARD, antes do trace.

| Dominio | Sinais (contaveis) | Rota |
|---------|-------------------|------|
| Complicated | Nenhum threshold atingido | Continuar trace |
| Complex | 4+ arquivos afetados OU recurrence OU temporal_coupling >=3 | DEEP direto |
| Chaotic | Multiplos erros simultaneos OU testes falhando em cascata | DEEP + Phase 0.5 (stabilization) |

## Decisoes de Design e Trade-offs

### 1. Roteamento integrado no FAST

- **Decisao:** Eliminar fase de roteamento separada
- **Motivo:** T1+T2 do FAST ja fazem os mesmos lookups
- **Trade-off:** Nenhum. Duplicacao pura eliminada.

### 2. Validacao por 3 Checks

- **Decisao:** Adicionar CHAIN/SCOPE/DEPTH como verificacao mecanica
- **Motivo:** Origin Gate sozinho dependia de self-assessment do modelo
- **Trade-off:** ~30 seg extras por investigacao. Ganho: impede parar no sintoma.
- **Gap:** SCOPE fraco com bug reports vagos → FULL por default, nao atrapalha.

### 3. Escalacao por capacidade

- **Decisao:** Substituir checklist subjetivo por "tecnica produziu resultado?"
- **Motivo:** IA nao "decide" escalar — tecnica atinge limite → proxima tecnica
- **Trade-off:** Perde flexibilidade de modelo forte "sentir" que deveria escalar
- **Mitigacao:** Escape Hatch recupera intuicao sem quebrar determinismo

### 4. Cynefin deterministico

- **Decisao:** Manter Cynefin mas com sinais contaveis (4+ arquivos, recurrence, etc)
- **Motivo:** Chaotic precisa stabilization. Complex precisa pular trace enganos.
- **Trade-off:** Bug Complex com 2-3 arquivos escapa do shortcut
- **Mitigacao:** Trace bifurca → DEEP de qualquer forma. Raro.

### 5. Remocao de Confidence Scores

- **Decisao:** Substituir 0.0-1.0 por checks binarios
- **Motivo:** Self-assessment nao eh confiavel (modelo diz 0.9 em coisa errada)
- **Trade-off:** Perde comunicacao de incerteza ao usuario
- **Mitigacao:** Reportar checks que passaram ("CHAIN ok SCOPE ok DEPTH ok")

### 6. Validacao proporcional por layer

- **Decisao:** FAST usa 3 checks, STANDARD usa SCOPE+DEPTH+agrees, DEEP usa seus proprios
- **Motivo:** CHAIN redundante no STANDARD (trace ja eh chain verification)
- **Trade-off:** Nenhum real.

### 7. KC granular

- **Decisao:** 4 niveis (EXACT/SIMILAR/PARTIAL/MISS) em vez de binario
- **Motivo:** EXACT reutiliza fix, SIMILAR da direcao — mais inteligencia sem custo
- **Trade-off:** Nenhum — eh adicao, nao substituicao.

### 8. Escape Hatch

- **Decisao:** 1 pergunta apos checks passarem para modelo forte sinalizar desconfianca
- **Motivo:** Protocolo rigido limita teto de modelo forte
- **Trade-off:** Nenhum — modelo fraco ignora, modelo forte usa.

## Scorecard v9.0 vs v10

| Aspecto | v9.0 | v10 | Delta |
|---------|------|-----|-------|
| Piso (Haiku) | Baixo | Alto | ++ |
| Teto (Opus) | Alto | Alto | = (escape hatch) |
| Determinismo | Baixo | Alto | ++ |
| Root cause accuracy | Medio | Alto | + (DEPTH check) |
| Resiliencia a vies | Baixa | Media | + (checks + escape) |
| Comunicacao | Confidence | Checks | + (mais honesto) |
| Chaotic handling | Subjetivo | Contavel | ~ (trade-off raro) |
| Flexibilidade | Alta | Media | - (protocolo rigido) |

## Gaps Conhecidos e Evolucoes Futuras

### Gap: Vies compartilhado (modelo + subagent errados na mesma direcao)

**Situacao:** STANDARD acha candidato errado + subagent concorda → fix errado.
**Mitigacao atual:** YOLO mode testes falham → retry. Modo interativo → humano revisa.
**Evolucao futura:** Subagent investiga INDEPENDENTE (sem ver trace do investigador) em vez de validar. Mais poderoso contra vies.

### Gap: Triage adaptativo (gates que aprendem)

**Situacao:** Bugs em stage5 SEMPRE escalam de FAST. Sistema nao lembra disso.
**Evolucao futura:** `min_layer` em file-intelligence.yaml, auto-calculado de investigations.yaml.
**Quando:** Quando investigations.yaml tiver 50+ entries e 5+ arquivos com 3+ bugs cada.

### Gap: Complex com poucos arquivos

**Situacao:** Bug emergente em 2-3 arquivos escapa do Cynefin deterministico.
**Mitigacao:** Trace bifurca → DEEP de qualquer forma.
**Evolucao futura:** Adicionar sinal de "interacao entre componentes" como criterio de Complex.

## Changelog

| Versao | Data | Mudancas |
|--------|------|----------|
| v10.0 | 2026-04-02 | AI-native redesign: 12 tecnicas, 3 checks, escalacao por capacidade, Cynefin deterministico, KC granular, Escape Hatch |
| v9.2 | 2026-04-01 | Tecnicas distintas por layer (RECONHECER/RASTREAR/PROVAR), standard_handoff, WSL path fix |
| v9.0 | 2026-03-31 | Progressive Escalation (FAST/STANDARD/DEEP), Origin Gate |
