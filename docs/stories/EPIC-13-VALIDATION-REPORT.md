# Epic 13 — Validation Report (Product Owner)

**Validador:** @po (Pax)
**Data:** 2026-03-22
**Epic:** Epic 13 — Pipeline Redesign: 28 para 5 Estagios Substanciais
**Total de Stories:** 12

---

## Resumo Executivo

| Story | Titulo | Score | Decisao |
|-------|--------|-------|---------|
| 13.1 | Storage Gateway — Abstracao + Implementacoes | 10/10 | **GO** |
| 13.2 | Adaptar Codigo Existente para Storage Gateway | 9/10 | **GO** |
| 13.3 | Orquestrador v2 — SSE Sub-Progress + Checkpoint | 10/10 | **GO** |
| 13.4 | Stage 1 — Layout Clustering (Pool Unico + 3 Camadas) | 9/10 | **GO** |
| 13.5 | Stage 2 — Deep Extraction (So Representativas) | 10/10 | **GO** |
| 13.6 | Stage 1+2 Integration Tests + Performance Benchmark | 8/10 | **GO** |
| 13.7 | Stage 3 — Structural Analysis (NER + GPT-4o Vision + Hierarchy) | 9/10 | **GO** |
| 13.8 | Stage 4 — Field Mapping (Batch LLM + Two-Pass + Section Scoping) | 9/10 | **GO** |
| 13.9 | Stages 3+4 Integration Tests | 7/10 | **GO** |
| 13.10 | Stage 5 — Template Generation (Tree-Driven HTML + CSS-from-Extraction) | 10/10 | **GO** |
| 13.11 | Frontend — PipelineResult Type + Integracao Stores | 8/10 | **GO** |
| 13.12 | Pipeline E2E — Full Integration Test + Migration | 9/10 | **GO** |

**Resultado Global:** 12/12 GO — Epic aprovado para desenvolvimento.
**Score Medio:** 9.0/10

---

## Checklist de Validacao (10 pontos)

| # | Criterio |
|---|----------|
| 1 | Story statement (As a/I want/So that) claro e completo |
| 2 | Acceptance Criteria especificos, mensuraveis, testaveis |
| 3 | Tasks/Subtasks acionaveis e cobrem todos os ACs |
| 4 | Dev Notes fornecem contexto suficiente |
| 5 | Secao de Testing existe com expectativas claras |
| 6 | Dependencias documentadas |
| 7 | Executor e Quality Gate atribuidos e diferentes |
| 8 | Prioridade apropriada |
| 9 | Escopo apropriado (nao muito grande, nao muito pequeno) |
| 10 | Sem gaps entre AC e Tasks |

---

## Validacao Detalhada por Story

### Story 13.1 — Storage Gateway: Abstracao + Implementacoes Supabase/Local

**Score: 10/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | Claro: pipeline quer persistir artefatos via abstracao |
| 2 | ACs | OK | 8 ACs com metodos especificos, enum, factory, SQL, testes |
| 3 | Tasks | OK | 7 tasks cobrindo todos os 8 ACs com mapeamento explicito |
| 4 | Dev Notes | OK | Pseudocodigo com linhas de referencia, estrutura de diretorios, codigo existente |
| 5 | Testing | OK | Frameworks, localizacao, padroes, cobertura minima definidos |
| 6 | Dependencias | OK | Nenhuma dependencia externa (primeira story da wave) |
| 7 | Executor/QG | OK | @dev / @architect (diferentes) |
| 8 | Prioridade | OK | Critical — pre-requisito para tudo |
| 9 | Escopo | OK | Bem dimensionado: 1 ABC + 2 implementacoes + factory + migrations |
| 10 | Gaps AC/Tasks | OK | Sem gaps |

**Destaques positivos:** Story exemplar. ACs detalhados com assinaturas de metodos. Dev Notes com pseudocodigo completo e estrutura de diretorios. Regra cardinal documentada (sem fallback silencioso). Tasks com mapeamento explicito para ACs.

---

### Story 13.2 — Adaptar Codigo Existente para Storage Gateway

**Score: 9/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | Claro e objetivo |
| 2 | ACs | OK | 9 ACs cobrindo todos os 7 arquivos + regressao + testes |
| 3 | Tasks | OK | 8 tasks com mapeamento claro para ACs |
| 4 | Dev Notes | OK | Padrao de injecao, codigo antes/depois, endpoint novo |
| 5 | Testing | OK | Estrategia definida |
| 6 | Dependencias | OK | Story 13.1 documentada |
| 7 | Executor/QG | OK | @dev / @architect |
| 8 | Prioridade | OK | Critical |
| 9 | Escopo | ATENCAO | 7 arquivos backend + 1 frontend e um potencial endpoint novo. Escopo grande mas gerenciavel |
| 10 | Gaps AC/Tasks | OK | Sem gaps |

**Issues menores:**
- **Escopo amplo (7+1 arquivos):** Nao e bloqueante, mas o dev deve estar atento a que sao alteracoes em 8 arquivos distintos. Considerar dividir se a implementacao se mostrar complexa, mas como sao alteracoes mecanicas (substituir path por gateway), o escopo e aceitavel.

**Recomendacoes:**
- A Task 7 (session.ts) menciona "Ou: signed URL direta do Supabase se CORS permitir" — decidir a abordagem antes de implementar para evitar refactor.

---

### Story 13.3 — Orquestrador v2: SSE Sub-Progress + Checkpoint de Falha

**Score: 10/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | Persona "operador do sistema" adequada |
| 2 | ACs | OK | 10 ACs especificos: SSE format, endpoint, feature flag, timeout |
| 3 | Tasks | OK | 6 tasks cobrindo todos ACs |
| 4 | Dev Notes | OK | Referencia arquitetural, SSE formato JSON, stage names, replay buffer |
| 5 | Testing | OK | Testes de fluxo com stubs, handle_service_failure, feature flag |
| 6 | Dependencias | OK | Implicita (13.1 para storage) |
| 7 | Executor/QG | OK | @dev / @architect |
| 8 | Prioridade | OK | Critical |
| 9 | Escopo | OK | Bem delimitado: orquestrador + SSE + endpoint + feature flag |
| 10 | Gaps AC/Tasks | OK | Sem gaps |

**Destaques positivos:** AC8 (feature flag) e AC10 (timeout 300s com default action) sao decisoes de design muito boas documentadas na story. Nota do replay buffer SSE existente evita rewrite desnecessario.

---

### Story 13.4 — Stage 1: Layout Clustering (Pool Unico + 3 Camadas)

**Score: 9/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | Claro, com valor quantificado (~6 vs 100 paginas) |
| 2 | ACs | OK | 9 ACs detalhados com 16 sub-steps, metricas de performance |
| 3 | Tasks | OK | 6 tasks com mapeamento para ACs |
| 4 | Dev Notes | OK | Regex de abstracao, dependencias Python, codigo reutilizavel |
| 5 | Testing | OK | 6 cenarios de teste + benchmark |
| 6 | Dependencias | OK | networkx, imagehash, Pillow listados. spaCy mencionado como dep do Stage 3 |
| 7 | Executor/QG | OK | @dev / @architect |
| 8 | Prioridade | OK | Critical |
| 9 | Escopo | ATENCAO | Story grande: 16 sub-steps em 3 camadas. Porem, o codigo arquitetural tem pseudocodigo completo |
| 10 | Gaps AC/Tasks | OK | Sem gaps |

**Issues menores:**
- **Escopo ambicioso (16 sub-steps):** E a story mais densa do epic. O pseudocodigo completo na arquitetura mitiga o risco, mas o dev deve planejar incrementalmente.

**Recomendacoes:**
- Considerar que a Camada 2 (deteccao) com LLM pode ser skipped inicialmente se o clustering da Camada 1 for suficiente. A story ja preve isso via handle_service_failure, o que e bom.

---

### Story 13.5 — Stage 2: Deep Extraction (So Representativas)

**Score: 10/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | Valor claro: 20min para 10s |
| 2 | ACs | OK | 15 ACs extremamente detalhados, cada sub-step com comportamento esperado |
| 3 | Tasks | OK | 9 tasks com mapeamento preciso |
| 4 | Dev Notes | OK | Contrato de saida completo em Python, codigo reutilizavel listado, dependencias |
| 5 | Testing | OK | 8 cenarios + benchmark + verificacao de versao |
| 6 | Dependencias | OK | PyMuPDF >= 1.23.0, jenkspy, Pillow |
| 7 | Executor/QG | OK | @dev / @architect |
| 8 | Prioridade | OK | Critical |
| 9 | Escopo | OK | 9 sub-steps mas cada um tem codigo existente reutilizavel |
| 10 | Gaps AC/Tasks | OK | Sem gaps |

**Destaques positivos:** Contrato de saida 3.2 documentado inline com tipos Python. Cada sub-step tem correspondencia clara com codigo existente a reutilizar. AC15 (verificacao de versao) demonstra atencao a riscos praticos.

---

### Story 13.6 — Stage 1+2 Integration Tests + Performance Benchmark

**Score: 8/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | "equipe de desenvolvimento" como persona adequada para test story |
| 2 | ACs | OK | 7 ACs com JSON Schema, edge cases, benchmark |
| 3 | Tasks | OK | 5 tasks cobrindo todos ACs |
| 4 | Dev Notes | ATENCAO | Breves comparado com outras stories — falta detalhe sobre geracao de PDFs de teste |
| 5 | Testing | OK | E uma story de teste — testing e o core |
| 6 | Dependencias | OK | Stories 13.4 e 13.5 documentadas |
| 7 | Executor/QG | OK | @dev / @qa (correto para story de teste) |
| 8 | Prioridade | OK | High (nao critical — correto para testes) |
| 9 | Escopo | OK | Bem dimensionado |
| 10 | Gaps AC/Tasks | ATENCAO | AC4 (benchmark 100 paginas) pode ser dificil de atingir com PDFs gerados programaticamente vs PDFs reais |

**Issues:**
- **Dev Notes minimas:** Comparado com stories 13.1-13.5, as dev notes sao mais enxutas. Falta orientacao sobre como gerar PDFs de teste com multiplos layouts programaticamente.
- **Benchmark com PDFs sinteticos:** A performance com PDFs gerados pode nao refletir PDFs reais (tabelas complexas, muitas imagens).

**Recomendacoes:**
- Incluir pelo menos 1 PDF real como fixture alem dos PDFs gerados programaticamente.
- Documentar na dev notes como gerar PDFs de teste com PyMuPDF (ja mencionado brevemente, mas sem exemplo).

---

### Story 13.7 — Stage 3: Structural Analysis (NER + GPT-4o Vision + Hierarchy)

**Score: 9/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | Claro, com contexto do que Stage 4 precisa |
| 2 | ACs | OK | 9 ACs detalhados com 4 sub-steps |
| 3 | Tasks | OK | 6 tasks cobrindo todos ACs |
| 4 | Dev Notes | OK | Prompt GPT-4o descrito, codigo reutilizavel, dependencias |
| 5 | Testing | OK | 6 cenarios incluindo fallback sem GPT-4o |
| 6 | Dependencias | OK | spaCy, openai/openrouter, asyncio |
| 7 | Executor/QG | OK | @dev / @architect |
| 8 | Prioridade | OK | Critical |
| 9 | Escopo | ATENCAO | 4 sub-steps mas inclui integracao com servico externo (GPT-4o) |
| 10 | Gaps AC/Tasks | OK | Sem gaps |

**Issues menores:**
- **Custo GPT-4o Vision nao estimado:** O epic menciona custo total < $0.20, mas esta story nao explicita quanto do budget e consumido por ~6 chamadas Vision. Seria util ter o custo estimado para rastreamento.

**Recomendacoes:**
- Adicionar estimativa de custo por chamada Vision (~$0.01-0.03 por imagem) no AC ou Dev Notes para que o dev possa validar contra o budget total.

---

### Story 13.8 — Stage 4: Field Mapping (Batch LLM + Two-Pass + Section Scoping)

**Score: 9/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | Valor quantificado: 95% accuracy, $0.01/job |
| 2 | ACs | OK | 10 ACs detalhados com 7 sub-steps |
| 3 | Tasks | OK | 9 tasks com mapeamento preciso |
| 4 | Dev Notes | OK | Batch LLM prompt template, codigo reutilizavel |
| 5 | Testing | OK | 7 cenarios + benchmark |
| 6 | Dependencias | OK | Implicita (Stages 1-3) |
| 7 | Executor/QG | OK | @dev / @architect |
| 8 | Prioridade | OK | Critical |
| 9 | Escopo | OK | 7 sub-steps bem definidos |
| 10 | Gaps AC/Tasks | ATENCAO | AC9 (accuracy ~95%) e dificil de validar sem dataset anotado |

**Issues menores:**
- **Accuracy target sem baseline de validacao:** AC9 afirma "accuracy estimada ~95%" mas nao define como medir. Precisa de ground truth dataset ou pelo menos criterios de aceitacao praticos (e.g., "boleto Bradesco: 100% dos campos mapeados corretamente").

**Recomendacoes:**
- Definir pelo menos 1 caso de teste com ground truth para validar accuracy na story 13.9 ou 13.12.

---

### Story 13.9 — Stages 3+4 Integration Tests

**Score: 7/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | Adequado para story de teste |
| 2 | ACs | OK | 9 ACs cobrindo contratos, NER, matching, edge cases |
| 3 | Tasks | OK | 4 tasks cobrindo ACs |
| 4 | Dev Notes | ATENCAO | Minimas — falta orientacao sobre mock de LLM e GPT-4o para testes |
| 5 | Testing | OK | E uma story de teste |
| 6 | Dependencias | OK | Stories 13.7 e 13.8 documentadas |
| 7 | Executor/QG | OK | @dev / @qa |
| 8 | Prioridade | OK | High |
| 9 | Escopo | ATENCAO | Falta benchmark de performance (stories 13.7 e 13.8 definem targets de ~20s e ~6s) |
| 10 | Gaps AC/Tasks | ATENCAO | Sem benchmark de performance. Stories 13.7 e 13.8 definem targets mas esta story de integracao nao os valida |

**Issues:**
- **Sem benchmark de performance:** A story 13.6 (Stage 1+2) tem benchmark explicito. Esta story equivalente para Stage 3+4 nao tem. Targets existem (AC8 da 13.7: ~20s, AC10 da 13.8: ~6s) mas nao sao validados aqui.
- **Dev Notes escassas:** Falta orientacao sobre mocking de GPT-4o Vision e Gemini Flash batch para testes de integracao.
- **Sem accuracy benchmark:** AC da 13.8 menciona ~95% accuracy mas nenhum teste aqui valida isso com ground truth.

**Recomendacoes:**
- Adicionar AC de benchmark: "Stage 3 + Stage 4 combinados < 30s com LLM mock."
- Adicionar orientacao de mocking para LLM services nas Dev Notes.
- Considerar adicionar pelo menos 1 teste de accuracy com ground truth simples (e.g., boleto com 5 campos mapeados manualmente).

---

### Story 13.10 — Stage 5: Template Generation (Tree-Driven HTML + CSS-from-Extraction)

**Score: 10/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | Problema central do epic claramente enderecado |
| 2 | ACs | OK | 8 ACs detalhados com 7 sub-steps, cada um com comportamento especifico |
| 3 | Tasks | OK | 9 tasks com mapeamento preciso incluindo pseudocodigo |
| 4 | Dev Notes | OK | CSS pseudocodigo, codigo a substituir, gaps G18-G22 referenciados |
| 5 | Testing | OK | 7 cenarios validando o core (CSS nao hardcoded, HTML valido) |
| 6 | Dependencias | OK | Implicita (Stages 1-4) |
| 7 | Executor/QG | OK | @dev / @architect |
| 8 | Prioridade | OK | Critical |
| 9 | Escopo | OK | 7 sub-steps mas logica de geracao e bem definida |
| 10 | Gaps AC/Tasks | OK | Sem gaps |

**Destaques positivos:** Esta story resolve o "problema central" do pipeline v1 (CSS hardcoded). Os testes validam explicitamente que CSS NAO e hardcoded — cada teste verifica fontes reais, cores reais, etc. Pseudocodigo do CSS-from-Extraction e muito util. Referencia aos gaps G18-G22 mostra rastreabilidade.

---

### Story 13.11 — Frontend: PipelineResult Type + Integracao Stores

**Score: 8/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | Persona "editor de templates" adequada |
| 2 | ACs | OK | 9 ACs detalhados com types, signed URLs, layout switch, coverage, overlay |
| 3 | Tasks | OK | 9 tasks cobrindo todos ACs |
| 4 | Dev Notes | ATENCAO | Codigo existente mencionado com "verificar nome exato" — podia ser mais preciso |
| 5 | Testing | OK | 5 cenarios com Vitest |
| 6 | Dependencias | OK | Implicita (Stage 5 para PipelineResult) |
| 7 | Executor/QG | OK | @dev / @architect |
| 8 | Prioridade | OK | Critical |
| 9 | Escopo | ATENCAO | Amplo: types + session.ts + multiDocStore + templateStore + SSE + overlay. Toca muitos arquivos |
| 10 | Gaps AC/Tasks | OK | Sem gaps |

**Issues:**
- **Dev Notes com incertezas:** Varias mencoes a "verificar nome exato" e "verificar location" indicam que o SM nao confirmou os caminhos exatos. Isso pode causar atrito no desenvolvimento.
- **Escopo amplo:** 9 tasks tocando types, 3+ stores, SSE composable, e overlay rendering. E a story frontend mais ampla.

**Recomendacoes:**
- Antes do desenvolvimento, o dev deve fazer um spike de 15min para confirmar os caminhos exatos dos arquivos mencionados nas Dev Notes (multiDocStore, useSSE composable, etc.).
- Considerar se Task 7 (SSE) e Task 8 (overlay tabelas) poderiam ser stories separadas se o escopo se mostrar grande demais durante desenvolvimento.

---

### Story 13.12 — Pipeline E2E: Full Integration Test + Migration

**Score: 9/10 | GO**

| # | Criterio | OK? | Nota |
|---|----------|-----|------|
| 1 | Story statement | OK | Adequado: teste e2e + migration |
| 2 | ACs | OK | 10 ACs cobrindo e2e, PDF real, benchmark, feature flag, regressao, cleanup |
| 3 | Tasks | OK | 7 tasks cobrindo todos ACs |
| 4 | Dev Notes | OK | Fixture boleto Bradesco, mapping v1->v2 completo, frameworks |
| 5 | Testing | OK | E uma story de teste |
| 6 | Dependencias | OK | TODAS as 11 stories anteriores |
| 7 | Executor/QG | OK | @dev / @qa |
| 8 | Prioridade | OK | Critical (capstone story) |
| 9 | Escopo | OK | Bem dimensionado para uma story de integracao final |
| 10 | Gaps AC/Tasks | ATENCAO | AC4 (custo API < $0.20) e dificil de medir em teste automatizado |

**Issues menores:**
- **Medicao de custo API em teste:** AC4 exige "custo API < $0.20 por job" mas medir custo real requer chamadas LLM reais. Em testes com mock, isso nao pode ser validado. Precisa de esclarecimento: e um teste manual ou uma estimativa baseada em contagem de chamadas?

**Recomendacoes:**
- Clarificar AC4: "Custo estimado < $0.20 baseado em contagem de chamadas LLM x preco por token" (calculado, nao medido em teste automatizado).

---

## Analise Transversal

### Pontos Fortes do Epic

1. **Rastreabilidade:** Todas as stories referenciam secoes especificas do documento de arquitetura v3.18.
2. **Contratos entre stages:** Contratos 3.1-3.5 com JSON Schema garantem integracao correta.
3. **Feature flag:** Pipeline v1/v2 coexistem, permitindo rollback seguro.
4. **Regra de ouro:** "Sem fallback silencioso" documentada consistentemente.
5. **Testes intercalados:** Stories de teste (13.6, 13.9, 13.12) entre stories de implementacao — garante qualidade incremental.
6. **Dev Notes de alta qualidade:** Pseudocodigo, codigo existente reutilizavel, estrutura de diretorios.

### Riscos Identificados

| Risco | Severidade | Stories Afetadas | Mitigacao |
|-------|-----------|------------------|-----------|
| Story 13.4 muito densa (16 sub-steps) | Media | 13.4 | Pseudocodigo completo na arquitetura |
| Story 13.11 escopo amplo (frontend) | Media | 13.11 | Spike inicial de 15min |
| Accuracy target sem ground truth | Baixa | 13.8, 13.9 | Definir caso de teste com boleto Bradesco |
| Custo API nao mensuravel em testes | Baixa | 13.12 | Estimar por contagem de chamadas |
| Dev Notes incompletas em test stories | Baixa | 13.6, 13.9 | Referenciar docs de arquitetura |

### Dependencias entre Stories

```
Wave 1: 13.1 → 13.2 → 13.3
Wave 2: 13.4 → 13.5 → 13.6
Wave 3: 13.7 → 13.8 → 13.9
Wave 4: 13.10 → 13.11 → 13.12

Cross-wave: Wave 1 pre-requisito para todas.
            Wave 4 depende de Waves 2 e 3.
```

---

## Decisao Final

**EPIC 13: GO para desenvolvimento.**

Todas as 12 stories atingiram score >= 7/10. O epic demonstra excelente planejamento com:
- ACs detalhados e mensuraveis
- Tasks com mapeamento explicito para ACs
- Dev Notes com pseudocodigo e referencias arquiteturais
- Waves de implementacao com dependencias claras
- Feature flag para rollout seguro

As recomendacoes acima sao melhorias opcionais que podem ser aplicadas pelo @sm antes do desenvolvimento, mas nao bloqueiam o inicio.

---

*-- Pax, validando com rigor e pragmatismo*
