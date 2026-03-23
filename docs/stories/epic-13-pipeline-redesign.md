# Epic 13 — Pipeline Redesign: 28→5 Estágios Substanciais

**Status:** Draft
**Branch:** feature/epic-13-pipeline-redesign
**Data:** 2026-03-22
**Origem:** `docs/architecture/pipeline-redesign-v3.md` (v3.18)
**Arquitetura:** @architect (Aria) — Auditoria completa dos 5 Stages + Fase 0

---

## Problema Central

O pipeline atual tem **28 estágios granulares** com problemas críticos:

| Problema | Impacto |
|----------|---------|
| Deep extraction em **100 páginas** (todas, não só representativas) | ~20 min para 100 páginas |
| **~3000 chamadas LLM** individuais no Field Matching | ~$3-5 por job |
| CSS **hardcoded** (Arial, #000, #ccc borders) | Template gerado ignora 90% dos dados extraídos |
| Sem clustering por layout | Tabelas, fontes, cores descartadas |
| Storage em `/tmp` (volátil) | Dados perdidos em restart/deploy |
| Sem checkpoint de falha | Pipeline falha → recomeça do zero |

**Proposta v3.18:** Reorganizar em **5 estágios substanciais** + Fase 0 (Storage Gateway), reduzindo tempo de ~20 min para ~1.5 min e custo de ~$3-5 para ~$0.08-0.20.

---

## Epic Goal

Reimplementar o pipeline de migração PDF→HTML Template de 28 estágios granulares para 5 estágios substanciais com Storage Gateway, reduzindo tempo de processamento em 13x, custo de API em 25x, e aumentando accuracy de field mapping de ~85% para ~95%.

---

## Existing System Context

- **Technology stack:** Python 3.11 (FastAPI), Vue 3 (Pinia), PyMuPDF, OpenRouter (LLM), Supabase
- **Pipeline atual:** 28 estágios em `backend/services/stages/` (32 arquivos), orquestrado por `pipeline_orchestrator.py`
- **Frontend:** Editor com 3 painéis (structure/canvas/inspector), stores Pinia, SSE para progress
- **Integration points:** SSE events, PipelineResult type, session.ts, templateStore, multiDocStore

---

## Estratégia de Implementação

**Abordagem:** Refactor incremental, não rewrite. Código existente funciona — reorganizar em novos stages como sub-steps.

### Waves de Implementação

```
Wave 1: Infraestrutura (Fase 0 + Orquestrador)     → 3 stories
Wave 2: Stages 1-2 (Clustering + Extraction)        → 3 stories
Wave 3: Stages 3-4 (Analysis + Mapping)             → 3 stories
Wave 4: Stage 5 + Frontend (Generation + Integração)→ 3 stories
```

**Dependências entre waves:** Wave 1 é pré-requisito para todas. Waves 2-3 podem ter overlap mínimo. Wave 4 depende de 2 e 3.

---

## Stories

### Wave 1 — Infraestrutura

#### Story 13.1: Storage Gateway — Abstração + Implementações

**Descrição:** Criar `StorageGateway` (ABC), `SupabaseStorageGateway`, e `LocalStorageGateway`. Configurar buckets Supabase (jobs, templates). Tabelas `job_clusters` e `templates`. Factory com `STORAGE_MODE` explícito (sem fallback silencioso).

**Executor:** `@dev` | **Quality Gate:** `@architect`
**Quality Gate Tools:** `[architecture_review, pattern_validation, security_scan]`

**Acceptance Criteria:**
- [ ] `StorageGateway` ABC com 10 métodos (upload_pdf, upload_screenshot, upload_asset, upload_thumbnail, get_local_path, get_signed_url, save_result, save_clusters, cleanup_local, delete_job)
- [ ] `SupabaseStorageGateway` funcional com upload + download + signed URLs
- [ ] `LocalStorageGateway` encapsula comportamento atual de `/tmp`
- [ ] Factory `create_storage_gateway()` com `STORAGE_MODE` obrigatório (sem default)
- [ ] SQL migrations: `job_clusters`, `templates`, bucket policies
- [ ] Sem fallback silencioso — se cloud falha, usa checkpoint (Seção 12)
- [ ] Testes unitários para ambas implementações

**Arquivos novos:**
- `backend/services/storage/__init__.py`
- `backend/services/storage/gateway.py`
- `backend/services/storage/supabase_gateway.py`
- `backend/services/storage/local_gateway.py`

**Ref:** pipeline-redesign-v3.md Seção 10.1

---

#### Story 13.2: Adaptar Código Existente para Storage Gateway

**Descrição:** Migrar os 7 arquivos existentes que salvam em disco para usar `StorageGateway`. Upload via Storage, screenshots via signed URL, result_json via DB obrigatório.

**Executor:** `@dev` | **Quality Gate:** `@architect`
**Quality Gate Tools:** `[integration_review, backward_compatibility]`

**Acceptance Criteria:**
- [ ] `backend/routers/upload.py` → upload via StorageGateway + temp local
- [ ] `backend/routers/analyze.py` → download Storage → temp → cleanup
- [ ] `backend/routers/assets.py` → CRUD via StorageGateway
- [ ] `backend/services/stages/screenshot_generator.py` → save via gateway
- [ ] `backend/services/stages/image_extraction.py` → save via gateway
- [ ] `backend/services/stages/pipeline_result.py` → save DB obrigatório
- [ ] `frontend/src/stores/session.ts` → screenshots via signed URL
- [ ] Pipeline existente continua funcionando (regressão zero)
- [ ] Testes de integração validam ambos modos (local + supabase mock)

**Ref:** pipeline-redesign-v3.md Seção 10.1, FASE 0

---

#### Story 13.3: Orquestrador v2 + SSE Sub-Progress + Checkpoint

**Descrição:** Criar novo `pipeline_orchestrator_v2.py` que executa 5 stages sequenciais com sub-progress SSE, política de falhas (Seção 12 — nunca agir silenciosamente), e checkpoint humano condicional.

**Executor:** `@dev` | **Quality Gate:** `@architect`
**Quality Gate Tools:** `[architecture_review, error_handling_validation]`

**Acceptance Criteria:**
- [ ] Orquestrador aceita `pdf_documents[{id, path, name}]` + XSD como input
- [ ] SSE reporta: `{stage, stage_name, status, progress_pct, sub_step, sub_progress_pct, summary}`
- [ ] `handle_service_failure()` com checkpoint humano (never silent)
- [ ] Context dict passa entre stages (contratos 3.1→3.5)
- [ ] `pdf_id` como `str` desde a entrada (consistente em todo pipeline)
- [ ] Suporta `STORAGE_MODE` via StorageGateway injetado
- [ ] Frontend adapta barra de progresso para 5 estágios + sub-barra

**Ref:** pipeline-redesign-v3.md Seções 9, 12

---

### Wave 2 — Extração (Stages 1-2)

#### Story 13.4: Stage 1 — Layout Clustering (Pool Único + 3 Camadas)

**Descrição:** Implementar `stage1_layout_clustering.py` com pool único (todas as páginas de todos os PDFs), 3 camadas de defesa (prevenção, detecção, correção), Homogeneity Check, e checkpoint humano condicional.

**Executor:** `@dev` | **Quality Gate:** `@architect`
**Quality Gate Tools:** `[algorithm_review, performance_validation]`

**Acceptance Criteria:**
- [ ] Pool único — todas as páginas no mesmo clustering (com `pdf_id` preservado)
- [ ] **Camada 1 (Prevenção):** Page Classification (text/scanned/blank), Block Extraction, Normalization, Content Abstraction, Region Filtering Adaptativo, Tolerant Similarity Matrix, Graph Clustering, Consensus Check, Representative Selection
- [ ] **Camada 2 (Detecção):** Cluster Quality Score, pHash Cross-Check, Representative Validation, LLM Cluster Validation (Gemini Flash)
- [ ] **Camada 3 (Correção):** Auto-correction (merge/split/isolate), Confidence Score
- [ ] Homogeneity Check (`shared_ratio < 0.20` → template_mismatch)
- [ ] Checkpoint humano: triggers (low_confidence, auto_correction, template_mismatch, always_confirm)
- [ ] `_raw_text_blocks` preservado (texto real pré-abstração de todas as páginas)
- [ ] Output conforme contrato 3.1
- [ ] ~5.5s para 100 páginas
- [ ] Testes com datasets de 1, 2, e 5+ PDFs

**Dependências:** spacy + pt_core_news_lg (Stage 3), jenkspy (Stage 2)

**Ref:** pipeline-redesign-v3.md Seções 2, 3.1, 5 (completa), v3.7-v3.11

---

#### Story 13.5: Stage 2 — Deep Extraction (Só Representativas)

**Descrição:** Implementar `stage2_deep_extraction.py` que extrai dados APENAS de páginas representativas. PyMuPDF `find_tables()`, `get_drawings()`, `span["flags"]` para bold/italic, cor obrigatória, Jenks Natural Breaks para grid, Quality Check.

**Executor:** `@dev` | **Quality Gate:** `@architect`
**Quality Gate Tools:** `[algorithm_review, data_validation]`

**Acceptance Criteria:**
- [ ] Só processa `representative_pages` (não todas as 100)
- [ ] `get_text("dict")` + `page.rect` (width/height) + `span["flags"]` (bold/italic/mono)
- [ ] Text Reconstruction com threshold proporcional ao font_size + `sub_spans[]`
- [ ] Font→CSS: FONT_MAP expandido (~50 fontes) + span flags
- [ ] Image Extraction: filtrar masks, validar bbox, `bbox_valid`
- [ ] Screenshot: SÓ representativas, `alpha=False`
- [ ] Grid Detection: Jenks Natural Breaks (jenkspy), excluir header/footer zones
- [ ] Table Detection: PyMuPDF `find_tables()` (ruling lines + clustering built-in)
- [ ] Table Structuring: cells com bbox, multi-row header, `header_row_count`
- [ ] `get_drawings()` → `drawn_elements[]` (lines, rects, curves com fill/stroke color)
- [ ] `span["color"]` → `color` obrigatório em TextBlock (default 0 = preto)
- [ ] Extraction Quality Check (5 validações)
- [ ] Output conforme contrato 3.2
- [ ] ~10s para ~6 representativas
- [ ] Verificar PyMuPDF ≥ 1.23.0 para `find_tables()`

**Ref:** pipeline-redesign-v3.md Seções 2, 3.2, 6, v3.5-v3.6, v3.12

---

#### Story 13.6: Stage 1+2 Integration Tests + Performance Benchmark

**Descrição:** Testes de integração end-to-end para Stages 1→2, validando contratos, performance, e edge cases (single PDF, multi-PDF, template mismatch).

**Executor:** `@dev` | **Quality Gate:** `@qa`
**Quality Gate Tools:** `[test_coverage, performance_benchmark]`

**Acceptance Criteria:**
- [ ] Teste e2e: 1 PDF → clusters → extraction → contratos válidos
- [ ] Teste e2e: 3 PDFs mesmo template → pool único → clusters corretos
- [ ] Teste e2e: PDF de template diferente → Homogeneity Check detecta
- [ ] Benchmark: 100 páginas em < 16s (Stage 1 ~5.5s + Stage 2 ~10s)
- [ ] Contratos 3.1 e 3.2 validados com JSON Schema
- [ ] Edge cases: página em branco, PDF rotacionado, tabela sem ruling lines
- [ ] `_raw_text_blocks` preservado e acessível para Stage 3

---

### Wave 3 — Análise + Mapeamento (Stages 3-4)

#### Story 13.7: Stage 3 — Structural Analysis (NER + GPT-4o Vision + Hierarchy)

**Descrição:** Implementar `stage3_structural_analysis.py` com 4 sub-steps: Multi-Example Analysis (estatística + spaCy NER + regex), Visual Analysis (GPT-4o obrigatório, 1 chamada combinada), Semantic Classification (label-value pairing), Hierarchy Builder (4 sinais).

**Executor:** `@dev` | **Quality Gate:** `@architect`
**Quality Gate Tools:** `[algorithm_review, llm_prompt_review]`

**Acceptance Criteria:**
- [ ] **3.1 Multi-Example Analysis:** `_raw_text_blocks` → label/dynamic/stability classification. 3 camadas: estatística + regex (CPF, CNPJ, datas, moeda) + spaCy NER (`pt_core_news_lg`)
- [ ] **3.2 Visual Analysis:** GPT-4o 1 chamada combinada (segmentation + interpretation + self-check). OBRIGATÓRIO. Fallback: thresholds adaptativos
- [ ] **3.3 Semantic Classification:** classificar + parear label-value. Tipo semântico `likely_dynamic`. Threshold proporcional (3.5% altura)
- [ ] **3.4 Hierarchy Builder:** 4 sinais (visual_regions + drawn_elements + grid_info + gap proporcional). Imagens, charts, barcodes na árvore
- [ ] `document_trees` hierárquico por layout conforme contrato 3.3
- [ ] `intelligence` com `block_classifications` por `block_id`
- [ ] `visual_analysis` com `html_suggestion` por região
- [ ] 3.1 e 3.2 em paralelo (async)
- [ ] ~20s com Vision / ~5s sem
- [ ] Dependência: `spacy` + `pt_core_news_lg` (~50MB)

**Ref:** pipeline-redesign-v3.md Seções 2, 3.3, 7, v3.13-v3.14

---

#### Story 13.8: Stage 4 — Field Mapping (Batch LLM + Two-Pass + Section Scoping)

**Descrição:** Implementar `stage4_field_mapping.py` com 7 sub-steps. XSD Parsing (movido do Stage 2), Section↔XSD Matching (reduz search space), Batch LLM (1 chamada/layout), Two-pass, Confidence per-layout heurístico.

**Executor:** `@dev` | **Quality Gate:** `@architect`
**Quality Gate Tools:** `[algorithm_review, llm_prompt_review, accuracy_validation]`

**Acceptance Criteria:**
- [ ] **4.1 XSD Parsing:** lxml, `field_tree` com `flat_paths` (movido do Stage 2)
- [ ] **4.2 Pair Validation:** consumir `field_pair` do Stage 3.3, parear blocos soltos restantes
- [ ] **4.3 Format Pre-Detection:** regex ANTES do matching (date, cpf, currency, cnpj, cep, telefone)
- [ ] **4.4 Section↔XSD Matching:** seções da `document_trees` → nós XSD (~80 paths → ~3-5)
- [ ] **4.5 Field Matching:** Batch LLM (1 chamada Gemini Flash por layout). Two-pass. `block_id` + `layout_type_id` obrigatórios
- [ ] **4.6 Confidence Scoring:** heurísticas determinísticas, per-layout (sem Claude Sonnet)
- [ ] **4.7 Consistency Validation:** tipo↔formato, reverse mapping (XSD required sem mapping), orphans
- [ ] `field_mappings` por layout conforme contrato 3.4
- [ ] Accuracy estimada ~95% (era ~85%)
- [ ] Custo: ~$0.01 por job (1 batch call/layout)
- [ ] ~6s com LLM / ~2s sem

**Ref:** pipeline-redesign-v3.md Seções 2, 3.4, v3.15

---

#### Story 13.9: Stages 3+4 Integration Tests

**Descrição:** Testes de integração Stages 3→4. Validar document_trees, block_classifications, field_mappings. Accuracy benchmark com dados reais.

**Executor:** `@dev` | **Quality Gate:** `@qa`
**Quality Gate Tools:** `[test_coverage, accuracy_benchmark]`

**Acceptance Criteria:**
- [ ] Teste e2e: enriched_documents → Stage 3 → Stage 4 → field_mappings válidos
- [ ] Contratos 3.3 e 3.4 validados com JSON Schema
- [ ] NER classifica corretamente nomes, datas, CPFs, moedas
- [ ] Visual Analysis retorna `html_suggestion` por região
- [ ] Section↔XSD Matching reduz candidatos (verificar <10 por campo)
- [ ] Two-pass resolve ambiguidades (sem duplicatas de XSD path)
- [ ] Confidence per-layout (não global)
- [ ] Edge cases: XSD com nós opcionais, tabela dinâmica, campo sem match

---

### Wave 4 — Geração + Frontend

#### Story 13.10: Stage 5 — Template Generation (Tree-Driven HTML + CSS-from-Extraction)

**Descrição:** Implementar `stage5_template_generation.py` com 7 sub-steps. HTML hierárquico de `document_trees`, CSS gerado de dados extraídos (não hardcoded), coverage multidimensional, overlay per-layout, VariationMatrix, PipelineResult final.

**Executor:** `@dev` | **Quality Gate:** `@architect`
**Quality Gate Tools:** `[architecture_review, css_validation, output_validation]`

**Acceptance Criteria:**
- [ ] **5.1 Tree-Driven HTML:** walk `document_trees` → HTML hierárquico. `<table>` real com `<!-- ko foreach -->`. Condicionais com `<!-- ko if -->`
- [ ] **5.2 CSS-from-Extraction:** fonts de text_blocks, cores de text_blocks[].color, borders de drawn_elements[type=line], backgrounds de drawn_elements[type=rect, fill_color], zone heights de visual_regions, text-align de positional analysis, page dimensions de pages[].width/height
- [ ] **5.3 Coverage:** multidimensional — fields(60%) + tables(25%) + images(15%)
- [ ] **5.4 Overlay Items:** per-layout (filtrado `layout_type_id`)
- [ ] **5.5 VariationMatrix Assembly:** variant + present_in_pdfs → matrix + Detections
- [ ] **5.6 PipelineResult Assembly:** trees_by_layout, validation_result, intelligence, block_classifications_confirmed, multi_doc, confidence normalizada 0-100 (G18), layout_types[] pre-populado (G19), 8 campos novos no type (G20), template_draft monolítico (G21)
- [ ] **5.7 Persistência:** Supabase com Checkpoint (handle_service_failure)
- [ ] ~3s para ~6 representativas

**Ref:** pipeline-redesign-v3.md Seções 2, 3.5, 8, v3.16-v3.18

---

#### Story 13.11: Frontend — PipelineResult Type + Integração Stores

**Descrição:** Adaptar types TypeScript para novo PipelineResult. `loadFromPipelineResult` → multiDocStore. trees_by_layout no editor. Screenshots/assets via signed URLs. Coverage multidimensional.

**Executor:** `@dev` | **Quality Gate:** `@architect`
**Quality Gate Tools:** `[type_safety, integration_review]`

**Acceptance Criteria:**
- [ ] **PipelineResult type** atualizado com 8 campos novos: `trees_by_layout`, `validation_result`, `intelligence`, `block_classifications_confirmed`, `multi_doc`, `page_config`, `document_type_confidence`, `visual_analysis`
- [ ] **DocumentStructure** type novo (pages + layout_types + root + trees_by_layout)
- [ ] **PageConfig, ValidationResult** types novos
- [ ] Import de `PdfDocument/VariationMatrix/Detection` de multi-doc.types
- [ ] `session.ts` → screenshots/assets via signed URL (não paths locais)
- [ ] `session.ts` pre-popula TODOS os layouts (não só ativo) — layout switch funciona desde primeiro load (G19)
- [ ] `loadFromPipelineResult` → `multiDocStore.populateFromPipeline`
- [ ] `templateStore` recebe `trees_by_layout` do layout ativo
- [ ] Coverage multidimensional exibido no toolbar
- [ ] SSE adapta barra de progresso para 5 estágios + sub-barra
- [ ] Overlay de tabelas hierárquico: `table_container` + `table_cell` hover (G22)

**Ref:** pipeline-redesign-v3.md Seções 8.14, FASE 6

---

#### Story 13.13: AnalyzingPage Redesign — Stepper 5 Estágios + Detail Card + A11y

**Descrição:** Redesign completo da `AnalyzingPage.vue` baseado no wireframe v2 aprovado. Stepper horizontal 5 estágios, detail card do estágio ativo, 5 estados (initializing/processing/checkpoint/error/completed), accordions, checkpoint UI com timer, error UI com 3 opções, completed summary com coverage multidimensional. A11y WCAG AA completa.

**Executor:** `@dev` | **Quality Gate:** `@architect`
**Quality Gate Tools:** `[ux_review, a11y_validation, integration_review]`
**Dependências:** 13.3, 13.11

**Acceptance Criteria:**
- [ ] Stepper horizontal 5 estágios com circles (done/active/pending/error/warning) + connectors
- [ ] Detail card do estágio ativo (label, título, sub-step, progress bar, métricas)
- [ ] 5 estados com transição automática via SSE (initializing → processing → checkpoint → error → completed)
- [ ] Accordions expandíveis para estágios concluídos
- [ ] Completed summary: métricas + coverage multidimensional + botão "Abrir no Editor"
- [ ] Checkpoint card: thumbnails + sugestão + timer 300s + integração handle-failure
- [ ] Error card: "O que aconteceu" + 3 opções (retry/fallback/abort) + integração handle-failure
- [ ] SSE v2 parsing com backward compat para SSE v1
- [ ] A11y WCAG AA: contraste ≥ 4.5:1, ARIA roles, keyboard nav, focus visible, semântica
- [ ] Topbar com breadcrumb + botão cancelar

**Ref:** wireframe-progress-screen-v2.html, UX proposal aprovada

---

#### Story 13.12: Pipeline E2E — Full Integration Test + Migration

**Descrição:** Teste end-to-end completo do pipeline novo (Stages 1→5). Validar que o editor recebe e renderiza corretamente. Migrar orquestrador v1→v2 com feature flag. Benchmark de performance.

**Executor:** `@dev` | **Quality Gate:** `@qa`
**Quality Gate Tools:** `[e2e_test, performance_benchmark, regression_test]`

**Acceptance Criteria:**
- [ ] Teste e2e: PDF upload → 5 stages → PipelineResult → editor renderiza
- [ ] Teste com PDF real (boleto bancário): Stage 5 gera CSS com fontes, cores, bordas do PDF original
- [ ] Benchmark: 100 páginas em < 60s (vs ~20 min atual)
- [ ] Custo API: < $0.20 por job (vs ~$3-5 atual)
- [ ] Feature flag `PIPELINE_VERSION=v2` para rollout gradual
- [ ] Pipeline v1 continua funcionando com flag `v1`
- [ ] Regressão: testes existentes passam com pipeline v2
- [ ] Cleanup: remover stages obsoletos quando v2 estável

---

## Compatibility Requirements

- [ ] Pipeline v1 (28 estágios) continua operacional via feature flag durante transição
- [ ] APIs existentes (`/api/analyze`, `/api/upload`) mantêm contrato
- [ ] SSE events compatíveis (novo formato inclui sub-progress, antigo continua)
- [ ] Frontend funciona com ambos pipelines (v1 e v2) durante transição

## Risk Mitigation

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| GPT-4o Vision indisponível | Baixa | Alto | Fallback: thresholds adaptativos (sem Vision) |
| PyMuPDF `find_tables()` requer ≥ 1.23.0 | Média | Médio | Verificar versão no startup, upgrade se necessário |
| spaCy `pt_core_news_lg` download em CI | Baixa | Baixo | Incluir no Dockerfile / setup script |
| Supabase Storage indisponível | Baixa | Alto | Checkpoint (Seção 12) — nunca fallback silencioso |
| Regressão no pipeline existente | Média | Alto | Feature flag `PIPELINE_VERSION` permite rollback |
| Batch LLM prompt muito grande | Baixa | Médio | Limitar campos por batch, split se > 4K tokens |
| Clustering incorreto (single PDF) | Média | Alto | 3 camadas de defesa + checkpoint humano |

## Quality Assurance Strategy

- **Pre-Commit:** CodeRabbit para cada PR — foco em segurança, patterns, performance
- **Per-Stage:** Contratos JSON Schema entre stages (3.1→3.5) validados em testes
- **E2E:** PDF real (boleto Bradesco) como fixture de integração
- **Benchmark:** Tempo e custo medidos e comparados com baseline (pipeline v1)
- **Feature Flag:** Rollout gradual — 1 job manual → batch → default

## Definition of Done

- [ ] Todos os 5 stages implementados e testados
- [ ] Storage Gateway operacional (Supabase + Local)
- [ ] Contratos entre stages validados com JSON Schema
- [ ] Pipeline v2 processa PDF real com fidelidade visual (CSS não hardcoded)
- [ ] Performance: < 60s para 100 páginas
- [ ] Custo API: < $0.20 por job
- [ ] Feature flag permite rollback para pipeline v1
- [ ] Frontend renderiza PipelineResult v2 corretamente
- [ ] Documentação atualizada

---

## Story Manager Handoff

"Please develop detailed user stories for this pipeline redesign epic. Key considerations:

- This is a major refactor of an existing pipeline running Python 3.11 (FastAPI) + Vue 3 (Pinia)
- Integration points: SSE events, PipelineResult type, session.ts, templateStore, multiDocStore, StorageGateway
- Existing patterns to follow: stage registry, context dict passing, checkpoint humano
- Critical compatibility requirements: feature flag for v1/v2, SSE backward compat, API contract preservation
- Each story must include verification that existing functionality remains intact
- Architecture document: `docs/architecture/pipeline-redesign-v3.md` v3.18

The epic should maintain system integrity while delivering a 13x faster pipeline with 25x lower API cost and 95% field mapping accuracy."

---

*— Morgan, planejando o futuro 📊*
