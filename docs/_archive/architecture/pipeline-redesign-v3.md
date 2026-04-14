# Pipeline Redesign v3.1 — Arquitetura Proposta

**Versão:** 3.18
**Data:** 2026-03-21
**Autor:** @architect (Aria)
**Base:** Análise do pipeline AS-IS + spec externo Stage 1 Layout Clustering
**Status:** Proposta para avaliação

### Change Log

| Versão | Data | Descrição |
|--------|------|-----------|
| 3.0 | 2026-03-20 | Redesign inicial — 5 estágios substanciais |
| 3.1 | 2026-03-20 | Stage 1 reforçado — 3 camadas de defesa (prevenção, detecção, correção), LLM cluster validation, spatial bitmap, consensus clustering, feedback loop downstream, checkpoint humano com SSE/endpoint/timeout, diagrama de sequência frontend↔backend↔LLM |
| 3.2 | 2026-03-20 | Stage 1 multi-PDF — clustering em 2 fases (intra-PDF isolado + cross-PDF merge) para resolver header/footer detection, escala O(n²), e ruído DBSCAN |
| 3.3 | 2026-03-20 | Fase 0: Storage Gateway — Supabase Storage + DB como pré-requisito. StorageGateway abstrato, SupabaseStorageGateway, LocalStorageGateway (dev/testes), SQL schemas, bucket policies, adaptação 7 arquivos existentes |
| 3.4 | 2026-03-20 | Storage: sem fallback silencioso — STORAGE_MODE explícito (supabase|local), se cloud falha usa checkpoint (Seção 12), não degrada para disco |
| 3.5 | 2026-03-20 | Stage 2 auditado — 5 gaps (page dimensions, bold/italic, quality check, cell bbox, ruling lines), 3 riscos (merge tabular, grid pollution, screenshots todas). Upgrade: PyMuPDF `find_tables()` substitui table detection custom, `span["flags"]` para bold/italic, Jenks Natural Breaks para grid, novo sub-step 2.10 Extraction Quality Check |
| 3.6 | 2026-03-20 | Stage 2 gaps adicionais: (1) Questão em aberto — dado para Multi-Example Analysis (Stage 2 extrai só representativas mas Stage 3.2 precisa comparar texto real de múltiplas páginas), 3 opções documentadas, decisão pendente. (2) Elementos visuais desenhados (lines/rects) capturados via `get_drawings()`. (3) Cor do texto promovida de opcional para obrigatório |
| 3.7 | 2026-03-21 | Stage 1 auditado — 15 gaps válidos (G1-S1 a G15-S1 + G17-S1; G16 e G18 removidos — seções condicionais e multi-page não são Stage 1). Destaque: G17 ordem incorreta abstraction/header-footer (bug design), G7 conteúdo variável (0.45 peso afetado). Categorias: entrada (3), header/footer (3), similarity (4), clustering (3), meta (2), design (1). Todos pendentes |
| 3.8 | 2026-03-21 | Tolerant Clustering — refinamento baseado em tolerance spec. Region filtering adaptativo (substitui header/footer removal), geometry_similarity com block matching tolerante (±0.05), regional weighting (distingue conteúdo variável de estrutura diferente), density na body region, spatial bitmap removido, pHash mantido como cross-check. **6 gaps resolvidos** (G4, G7, G8, G9, G12, G17), 9 pendentes. Orquestrador atualizado, core_blocks/all_blocks no contrato |
| 3.9 | 2026-03-21 | **Todos os 15 gaps Stage 1 resolvidos.** Page classification (text/scanned/blank) com pHash fallback (G1,G3). Rotation normalization via `page.rotation` (G2). Regex expandido com ISO dates, moedas, meses PT (G5). Grid detection removido do Stage 1 → Stage 2 (G6). Complete-linkage substitui Union-Find para cross-PDF merge (G10). G11 aceito como risco conhecido mitigado por 3 sinais. Representative selection via weighted degree (G13). ClusteringConfig centralizado com rationale (G14). Contrato atualizado com `page_type` + `is_processable` (G15) |
| 3.10 | 2026-03-21 | **G8 Stage 2 resolvido — Opção A.** Stage 1 preserva `_raw_text_blocks` (texto real pré-abstração de todas as páginas, ~50KB/100pgs). Stage 3 consome para Multi-Example Analysis (label vs dynamic, ~95% accuracy), Stability Classification e Variant Detection. Stage 2 não muda. Cada estágio mantém sua responsabilidade: Stage 1 preserva (não descarta), Stage 3 analisa (compara e classifica). Contrato 3.1 atualizado com `_raw_text_blocks`. Código de consumo em Stage 3.2 (`analyze_block_variability`) documentado com exemplos |
| 3.11 | 2026-03-21 | **Pool Único + Homogeneity Check.** Clustering em 2 fases (Phase A + Phase B) substituído por **pool único** — todas as páginas de todos os PDFs no mesmo pool (com `pdf_id` preservado). Premissa: todos os PDFs de um job são do MESMO template. Phase B inteira removida (5.16-5.20). LLM Cluster Validation **movida para Camada 2** (step 1.13). **Homogeneity Check** adicionado (step 1.16) — detecta PDF de template diferente enviado por engano (`shared_ratio < 0.20`). Checkpoint humano ganha trigger `template_mismatch` ("Documento incompatível detectado"). Confidence Score simplificado (sem `cross_similarity`). Contrato 3.1: removidos `source_clusters` e `is_cross_pdf_merge`. G10 (complete-linkage) perde relevância sem merge cross-PDF |
| 3.12 | 2026-03-21 | **Auditoria completa Stage 2 pós-v3.11.** 12 gaps avaliados (G9-G17-S2 + G12 descartado). Correções: screenshot rendering (extrair de clusters), R1 cross-column (drawn_elements hint), `source_clusters` removido, `suspects`→`outliers`, G8 marcado resolvido, `sub_spans[]` no contrato 3.2, header detection multi-row (`_detect_header_rows` + `header_row_count`), Quality Check 5 (validação tabelas), table fallback aceito (PDFs gerados), font subset prefix strip (`_normalize_pdf_font_name`), integração pipeline↔editor para fonts documentada. **XSD Parsing movido de Stage 2 (2.9) para Stage 4 (4.1)** — pertence ao Field Mapping, não à extração de PDF. Stage 2 renumerado: 2.9=Quality Check. OCR descartado (PDFs nunca scanned). LLM: NÃO usado no Stage 2 — correto |
| 3.14 | 2026-03-21 | **Stage 3 — NER + regex para classificação label/dynamic.** Gap crítico: classificação estatística falha com single-PDF ou amostras sem variação (tudo vira "label"). Solução: 3 camadas em cascata — (1) estatística (comparação entre PDFs), (2) regex (datas, moeda, CPF, CNPJ, CEP, telefone), (3) spaCy NER pt_core_news_lg (nomes, locais, organizações). Campos não resolvidos → Stage 4 decide via XSD (fonte de verdade). Novo tipo semântico `likely_dynamic`. Threshold label-value "abaixo" proporcional (3.5% altura, era 30pts fixo). Dependência: spacy + pt_core_news_lg (~50MB, ~1ms/bloco). 7 gaps resolvidos (G10-G16-S3). `classification_quality` no contrato. Imagens, charts e barcodes incluídos na `document_trees` (G13-G16). Prompt Visual Analysis enriquecido: `barcode_area` + `chart_type` + `barcode_format` + `confidence` por elemento (zero chamadas extras). Nó `barcode` separado de `chart`. **5 Pontos de Atenção (PA1-PA2, PA4-PA6)** para Stage 4/5 |
| 3.15 | 2026-03-21 | **Auditoria completa Stage 4 (Field Mapping).** 16 gaps + 3 melhorias estruturais. **Melhoria 1 — Section↔XSD Matching:** document_trees (Stage 3) cruzadas com XSD hierárquico — matching em 2 níveis (seção→nó complexo, campo→filho) reduz search space de ~80 para ~3-5 candidatos. **Melhoria 2 — Format hints:** Format Detection movido para ANTES do Field Matching — formato detectado (date, cpf, currency) enriquece prompt LLM. **Melhoria 3 — Two-pass:** pass 1 aceita matches ≥0.7, pass 2 elimina XSD paths já usados para resolver ambiguidades ($0 extra). Redesign: 6→7 sub-steps. **Batch LLM** (1 chamada/layout, ~$0.01). **Claude Sonnet removido** → heurísticas ($0). PA1-PA5 resolvidos. Confidence per-layout. Validação tipo↔formato. Reverse mapping. `block_id` + `layout_type_id` obrigatórios. Accuracy estimada ~95% (era ~85%) |
| 3.18 | 2026-03-21 | **5 novos gaps Stage 5 (G18-G22) — integração Pipeline↔Frontend.** G18: confidence normalizada 0-100 todos fatores. G19 (ALTO): layout_types[] pre-populado com documentTree/confidence/coverage — layout switch funciona desde primeiro load. G20 (ALTO): PipelineResult type atualizado com 8 campos novos. G21 (ALTO): template_draft monolítico + árvores em trees_by_layout. G22: overlay de tabelas hierárquico (container + cells hover). Pseudocódigo 5.6 reescrito incorporando G18/G19/G21. Seção 8.14 com soluções detalhadas |
| 3.17 | 2026-03-21 | **3 gaps cross-stage resolvidos + 3 gaps editor identificados.** Cross-stage: (1) `pdf_id` consistente — orquestrador recebe `pdf_documents[{id: str, path, name}]`, ID é str desde a entrada. (2) `role` base/variation data-driven — cluster coverage. (3) Homogeneity Check — purga no checkpoint, garantia no contrato 3.1. Editor: **Gap A** (ALTA) — pre-export não valida `<!-- ko if/foreach -->`, silent failure em runtime. **Gap B** (MÉDIA) — VisibilityControl desconectado do multiDocStore, sem "Marcar como variação". **Gap C** (BAIXA) — AutoFix limite 3→5 configurável. Seção 14 nova: Gaps do Editor + Matriz de Mitigação Pipeline↔Editor. Riscos atualizados (7 riscos Stage 5 com mitigações do editor) |
| 3.16 | 2026-03-21 | **Auditoria completa Stage 5 (Template Generation).** 17 gaps + 3 melhorias estruturais. **Melhoria 1 — Tree-Driven HTML:** HTML gerado por walk de `document_trees` (Stage 3), não de `field_mappings` flat — seções, label-value pairs, condicionais e `<table>` real preservados na hierarquia. **Melhoria 2 — CSS-from-Extraction:** CSS gerado a partir de fonts, cores e drawn_elements extraídos dos Stages 2-3, não hardcoded. Zonas header/footer de visual_regions. **Melhoria 3 — Multi-Doc Pipeline Connection:** `result_json.multi_doc` com VariationMatrix + Detections + pdfs montado de block_classifications. `loadFromPipelineResult` conectado ao multiDocStore. 7 sub-steps (5.1-5.7). Coverage multidimensional (fields 60% + tables 25% + images 15%). Overlay items filtrado por layout. `trees_by_layout` implementado. `validation_result`, `intelligence`, `block_classifications_confirmed` no contrato. Persistência com Checkpoint (sem fallback silencioso). PA6 resolvido |
| 3.13 | 2026-03-21 | **Auditoria completa Stage 3.** 9 gaps avaliados (G1-G9-S3). Redesign: 7 sub-steps → **4 sub-steps**. **Reordenação**: Multi-Example Analysis primeiro (resolve dependência circular), Visual Analysis segundo (obrigatório, alimenta Hierarchy Builder). **Visual Analysis obrigatório** com 1 chamada GPT-4o combinada (era 3 chamadas opcionais). **Semantic Classification enriquecido** com label-value pairing (movido do Stage 4.2). **Document Type Detection REMOVIDO** — keyword matching existente em `pipeline_result.py` já resolve para display, LLM sem valor adicional. `structural_hints` removido. **Hierarchy Builder** usa 4 sinais em cascata (visual regions + drawn_elements + grid_info + gap proporcional). Contrato 3.3 reescrito: `intelligence` com `block_classifications` por block_id (elimina `stability_map`), `conditional_sections` vivem na árvore (nós com `variant`), `visual_analysis` com `html_suggestion` por região. Stage 4.2 renomeado para Pair Validation. LLM fallback: 1 retry automático → checkpoint (sem cadeia de modelos). Layout Alignment cross-cluster descartado (Stage 4 resolve via XSD). **LLM no Stage 3: apenas GPT-4o Vision (~6 chamadas/job)** |

---

## 1. Filosofia

Cada estágio responde **uma pergunta específica**. Internamente pode ter muitos sub-steps, mas do ponto de vista do pipeline é **uma unidade com input claro e output claro**.

O pipeline atual tem 28 estágios granulares. A proposta é reorganizar em **estágios que resolvem problemas completos**, mantendo o código existente como sub-steps internos quando possível.

---

## 2. Pipeline Proposto — 5 Estágios

```
pdf_documents[{id, path, name}] + XSD
    │
    ▼
┌─ STAGE 1: Layout Clustering ───────────────────────────────┐
│  PERGUNTA: "Quais páginas são iguais entre si?"             │
│                                                              │
│  Input:  pdf_documents[] (id: str vem de Fase 0)            │
│  Output: clusters[] com representative_pages                 │
│                                                              │
│  PREMISSA: Todos os PDFs de um job são do MESMO template.    │
│  Múltiplos PDFs = mais exemplos (detectar condicionais,      │
│  show/hide, variação de cor). NÃO são templates diferentes.  │
│                                                              │
│  POOL ÚNICO (todas as páginas de todos os PDFs juntas):      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ CAMADA 1 — PREVENÇÃO (reduzir chance de erro):          │  │
│  │  1.1  Page Extraction + Classification                  │  │
│  │       (text/scanned/blank) + atribuir pdf_id            │  │
│  │  1.2  Block Extraction — get_text("blocks")             │  │
│  │       + preservar _raw_text_blocks (pré-abstração)      │  │
│  │  1.3  Normalization (rotation + coords normalizadas)    │  │
│  │  1.4  Content Abstraction (DATE/NUMBER/TEXT_S/TEXT_L)    │  │
│  │  1.5  Region Filtering Adaptativo                       │  │
│  │  1.6  Tolerant Similarity Matrix (geo 0.8 + den 0.2)   │  │
│  │  1.7  Graph Clustering (threshold 0.85)                 │  │
│  │  1.8  Consensus Check                                   │  │
│  │  1.9  Representative Selection (weighted degree)        │  │
│  │                                                         │  │
│  │ CAMADA 2 — DETECÇÃO (identificar quando errou):         │  │
│  │  1.10 Cluster Quality Score                             │  │
│  │  1.11 pHash Cross-Check                                 │  │
│  │  1.12 Representative Validation                         │  │
│  │  1.13 LLM Cluster Validation (Gemini Flash ~$0.003)     │  │
│  │                                                         │  │
│  │ CAMADA 3 — CORREÇÃO (corrigir erros detectados):        │  │
│  │  1.14 Auto-correction (merge/split/isolate)             │  │
│  │  1.15 Confidence Score                                  │  │
│  │                                                         │  │
│  │ VALIDAÇÃO:                                              │  │
│  │  1.16 Document Homogeneity Check                        │  │
│  │       (detecta documento de template diferente          │  │
│  │        enviado por engano — shared_ratio < 0.20)        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  CHECKPOINT HUMANO (condicional):                            │
│   triggers: low confidence | auto-correction |               │
│             template_mismatch | always_confirm                 │
│   → SSE event + UI de confirmação para o operador            │
└──────────────────────────────────────────────────────────────┘
    │
    │  clusters: [{cluster_id, pages[], representative_page, page_count}]
    │  (pages contém pdf_id — downstream sabe de qual PDF veio cada página)
    ▼
┌─ STAGE 2: Deep Extraction ──────────────────────────────────┐
│  PERGUNTA: "O que tem em cada página representativa?"        │
│                                                              │
│  Input:  representative_pages + PDFs                         │
│  Output: enriched_documents (completo — texto, fontes,       │
│          imagens, screenshots, tabelas, grid)                │
│                                                              │
│  Sub-steps:                                                  │
│   2.1  Full Text Extraction — get_text("dict") + page.rect   │
│        + span["flags"] (bold/italic/serif/mono)              │
│   2.2  Text Reconstruction — merge spans fragmentados        │
│        (threshold proporcional ao font_size)                 │
│   2.3  Font → CSS — FONT_MAP expandido + span flags          │
│   2.4  Image Extraction — extrair, filtrar masks, validar    │
│        bbox, salvar via StorageGateway                       │
│   2.5  Screenshot Rendering — PNG 150 DPI, SÓ representativas│
│        alpha=False (fundo branco garantido)                  │
│   2.6  Grid Detection — Jenks Natural Breaks (1D), excluindo │
│        header/footer zones                                   │
│   2.7  Table Detection — PyMuPDF find_tables() (ruling lines │
│        + clustering built-in), multi-tabela por página       │
│   2.8  Table Structuring — headers, cells com bbox, merge    │
│        multi-page (% da page height, não hardcoded)          │
│   2.9  Extraction Quality Check — validar text_blocks,       │
│        encoding, duplicatas OCR, páginas vazias, tabelas     │
└──────────────────────────────────────────────────────────────┘
    │
    │  enriched_documents: [{pages: [{text_blocks (com color),
    │    images, fonts, grid_info, screenshot_path, tables (com cell bbox),
    │    drawn_elements, width, height}]}]
    │  extraction_warnings: [{page, type, message}]
    ▼
┌─ STAGE 3: Structural Analysis ──────────────────────────────┐
│  PERGUNTA: "O que é cada coisa e como se organiza?"          │
│                                                              │
│  Input:  enriched_documents + clusters + _raw_text_blocks    │
│  Output: document_trees (hierárquico, por layout)            │
│          + intelligence + visual_analysis                    │
│                                                              │
│  Sub-steps:                                                  │
│   3.1  Multi-Example Analysis — label/dynamic/stability      │
│        (algorítmico + spaCy NER, usa _raw_text_blocks)       │
│   3.2  Visual Analysis — GPT-4o (1 chamada combinada)        │
│        OBRIGATÓRIO — regiões + html_suggestion + self-check  │
│   3.3  Semantic Classification — classificar + parear L/V    │
│        (algorítmico, enriquecido por 3.1 + 3.2)             │
│   3.4  Hierarchy Builder — visual regions + drawn_elements   │
│        + grid_info + gap proporcional + images + charts      │
│                                                              │
│  document_type: keyword matching existente (pipeline_result) │
└──────────────────────────────────────────────────────────────┘
    │
    │  document_trees: {layout_id → TreeNode hierárquico}
    │  intelligence: {layout_id → {block_classifications, ...}}
    │  visual_analysis: {page_key → {regions, consistency_score}}
    ▼
┌─ STAGE 4: Field Mapping ────────────────────────────────────┐
│  PERGUNTA: "Como cada campo do PDF se conecta ao XSD?"       │
│                                                              │
│  Input:  block_classifications + document_trees + XSD        │
│  Output: field_mappings (por layout_type) + formats          │
│                                                              │
│  Sub-steps:                                                  │
│   4.1  XSD Parsing — field_tree com flat_paths (lxml)        │
│   4.2  Pair Validation — validar field_pair do Stage 3.3     │
│   4.3  Format Pre-Detection — regex ANTES do matching        │
│        (hints de formato enriquecem prompt LLM)              │
│   4.4  Section↔XSD Matching — seções da tree → nós XSD      │
│        (reduz search space de ~80 para ~3-5 por campo)       │
│   4.5  Field Matching — Batch LLM (1/layout) com hints      │
│        + two-pass (pass 2 elimina paths já usados)           │
│        + PA4 (XSD confirma likely_dynamic → dynamic)         │
│   4.6  Confidence Scoring — 5 fatores heurísticos (sem LLM)  │
│        + smart_signals (PA1) + per-layout (não global)       │
│   4.7  Consistency Validation — orphans, unmapped, reverse   │
│        + tipo↔formato + reverse mapping (XSD required)       │
└──────────────────────────────────────────────────────────────┘
    │
    │  field_mappings: [{xsd_path, confidence, layout_type_id, block_id, smart_signals, ...}]
    │  format_functions: {name → js_function}
    │  confidence_scores: {layout_id → factors}  (per-layout, não global)
    │  validation_result: {warnings, errors, type_format_mismatches}
    ▼
┌─ STAGE 5: Template Generation ──────────────────────────────┐
│  PERGUNTA: "Como isso vira HTML para o editor?"              │
│                                                              │
│  Input:  tudo dos stages anteriores                          │
│  Output: PipelineResult (contrato final para o frontend)     │
│                                                              │
│  Sub-steps:                                                  │
│   5.1  Tree-Driven HTML — walk document_trees → HTML         │
│        hierárquico com <table> real + condicionais           │
│   5.2  CSS-from-Extraction — fonts, cores, backgrounds       │
│        drawn_elements + visual_regions (zonas)               │
│   5.3  Coverage Calculation — multidimensional               │
│        fields(60%) + tables(25%) + images(15%)               │
│   5.4  Overlay Items — per-layout (filtrado layout_type_id)  │
│   5.5  VariationMatrix Assembly — variant + present_in_pdfs  │
│        → VariationMatrix + Detections (PA6)                  │
│   5.6  PipelineResult Assembly — contrato final              │
│        trees_by_layout + validation_result + intelligence    │
│   5.7  Persistence — Supabase com Checkpoint                 │
└──────────────────────────────────────────────────────────────┘
    │
    ▼
  PipelineResult → Frontend Editor
```

---

## 3. Contratos Entre Estágios

### 3.1 Stage 1 Output → Stage 2 Input

```python
# Stage 1 escreve:
context["clusters"] = [
    {
        "cluster_id": str,            # "A", "B", ...
        "pages": [
            {"pdf_id": str, "page_index": int}  # pdf_id preservado — downstream sabe a origem
        ],
        "representative_page": {"pdf_id": str, "page_index": int},
        "page_count": int,
        "confidence": {               # score de confiança do clustering
            "confidence": float,      # 0.0-1.0
            "level": str,             # "high" | "medium" | "low"
            "factors": dict           # detalhamento por fator (quality, pHash, consensus, LLM)
        }
    }
]

# Dados internos do pipeline (prefixo _ = não exposto ao frontend):
context["_raw_text_blocks"] = {          # NOVO (G8) — texto real pré-abstração de TODAS as páginas
    "{pdf_id}:{page_index}": [           # Preservado no step 1.2, antes do step 1.5 (abstração)
        {
            "text": str,                 # texto REAL ("Cliente: João Silva")
            "bbox_norm": [x0,y0,x1,y1], # posição normalizada [0,1]
            "x_center": float,
            "y_center": float,
            "type": int                  # 0=texto (só tipo 0 preservado)
        }
    ]
}
# Custo: ~50KB para 100 páginas (~500 bytes/página)
# Consumido por: Stage 3.2 (Multi-Example), 3.3 (Stability), 3.4 (Variant Detection)

context["_light_blocks"] = {            # blocos leves por página (descartável)
    "{pdf_id}:{page_index}": [
        {"text_abstract": str, "bbox_norm": [x0,y0,x1,y1]}
    ]
}
context["_header_footer_blocks"] = {    # blocos removidos POR PDF (para debug)
    "{pdf_id}": [...]
}
```

**Garantias:**
- Todo cluster tem exatamente 1 `representative_page`
- Toda página de todos os PDFs está em exatamente 1 cluster
- `cluster_id` é único
- `pdf_id` é `str` (UUID de Fase 0 ou `str(index)` em dev) — consistente em todo o pipeline
- `pdf_id` preservado em cada page — downstream rastreia origem
- Para multi-PDF: páginas de múltiplos PDFs caem naturalmente nos mesmos clusters (pool único), essencial para Stage 3 label/dynamic detection
- `confidence` sempre presente — downstream adapta comportamento
- `_raw_text_blocks` contém texto real de TODAS as páginas (pré-abstração) — Stage 3 consome para Multi-Example Analysis (estatística + NER/regex), Stability Classification e Variant Detection
- **Clusters já limpos**: se o operador removeu PDFs incompatíveis no checkpoint (Homogeneity Check), as páginas e raw_text_blocks desses PDFs já foram purgados. Downstream nunca vê PDFs removidos

### 3.2 Stage 2 Output → Stage 3 Input

```python
context["enriched_documents"] = [
    {
        "pdf_id": str,
        "pdf_name": str,
        "pages": [
            {
                "page_index": int,
                "cluster_id": str,          # de qual cluster vem
                "is_representative": bool,
                "width": float,             # PDF points (de page.rect)
                "height": float,            # PDF points (de page.rect)
                "text_blocks": [
                    {
                        "id": str,          # UUID
                        "text": str,
                        "bbox": [x0, y0, x1, y1],  # PDF points
                        "font_name": str,   # font dominante do bloco
                        "font_size": float, # font_size dominante do bloco
                        "is_bold": bool,    # de span["flags"] bit 4 (dominante)
                        "is_italic": bool,  # de span["flags"] bit 1 (dominante)
                        "is_mono": bool,    # de span["flags"] bit 3 (dominante)
                        "color": int,       # RGB int de span["color"] (default: 0 = preto)
                        "sub_spans": [      # NOVO v3.12 — preserva rich text inline
                            {
                                "text": str,
                                "offset": int,      # posição no text do bloco
                                "length": int,
                                "font_name": str,
                                "font_size": float,
                                "is_bold": bool,
                                "is_italic": bool,
                                "color": int
                            }
                        ] | null            # null se bloco tem estilo uniforme (1 span)
                    }
                ],
                "images": [
                    {
                        "path": str,
                        "bbox": [x0, y0, x1, y1],
                        "bbox_valid": bool, # False se bbox = (0,0,0,0) e precisa estimativa
                        "format": str
                    }
                ],
                "fonts": [
                    {
                        "font_family": str,     # CSS (FONT_MAP expandido)
                        "font_size": float,
                        "font_weight": str,
                        "font_style": str
                    }
                ],
                "grid_info": {
                    "columns": int,
                    "rows": int,
                    "column_positions": [float],
                    "row_positions": [float]
                } | null,
                "screenshot_path": str | null,
                "tables": [
                    {
                        "table_id": str,
                        "bbox": [x0, y0, x1, y1],         # bbox da tabela inteira
                        "headers": [[{"text": str, "bbox": [x0, y0, x1, y1], "column_index": int}]],  # v3.12: lista de rows (multi-row header)
                        "rows": [[{"text": str, "bbox": [x0, y0, x1, y1], "column_index": int}]],
                        "header_row_count": int,           # v3.12: quantas linhas são header (0, 1, 2+)
                        "columns": int,
                        "column_widths": [float],
                        "confidence": float,
                        "detection_method": str,           # "ruling_lines" | "clustering" | "combined"
                        "has_ruling_lines": bool,          # True se detectado via linhas vetoriais
                        "is_multi_page": bool
                    }
                ],
                "drawn_elements": [             # NOVO v3.6 — linhas/retângulos vetoriais
                    {
                        "type": str,            # "line" | "rect" | "curve"
                        "bbox": [x0, y0, x1, y1],
                        "orientation": str | null, # "horizontal" | "vertical" | "diagonal" | null
                        "fill_color": int | null,  # RGB int se preenchido
                        "stroke_color": int | null,# RGB int se contorno
                        "width": float             # stroke width (pts)
                    }
                ] | null
            }
        ]
    }
]

context["extraction_warnings"] = [             # NOVO — resultado do Quality Check (2.9)
    {
        "page_key": str,                       # "{pdf_id}:{page_index}"
        "type": str,                           # "empty_page" | "encoding_issue" | "duplicate_text" | "no_images"
        "message": str,
        "severity": str                        # "warning" | "error"
    }
]

context["clusters"] = [...]  # passthrough do Stage 1
```

**Garantias:**
- Só páginas representativas têm dados completos (text_blocks, images, fonts, etc.)
- Cada página tem `cluster_id` indicando a qual cluster pertence
- `width` e `height` sempre presentes (de `page.rect`)
- `is_bold` e `is_italic` vêm de `span["flags"]` (confiável), não de parsing de nome de fonte
- `color` sempre presente (default 0 = preto). Usado para fidelidade visual do template
- `tables` têm cells com `bbox` individual — downstream pode posicionar cada célula
- `tables` com `has_ruling_lines` = True → confiança alta (bordas vetoriais detectadas)
- `images` com `bbox_valid` = False → downstream sabe que posição é estimativa
- `drawn_elements` contém separadores visuais e backgrounds (para Hierarchy Builder e Template Generation)
- `extraction_warnings` lista problemas detectados pelo Quality Check (2.10)
- **v3.12:** `field_tree` movido para Stage 4 (onde é consumido). XSD parsing não pertence ao Stage 2
- **✅ RESOLVIDO (G8):** Stage 1 preserva `_raw_text_blocks` (texto real pré-abstração de todas as páginas). Stage 3 consome para Multi-Example Analysis, Stability Classification e Variant Detection. Ver Seção 6.4

### 3.3 Stage 3 Output → Stage 4 Input

```python
context["document_trees"] = {
    "layout-A": {
        "id": "root-A",
        "type": "document",
        "children": [
            {
                "type": "page",
                "children": [
                    {
                        "type": "header",
                        "source": "visual",              # como a zona foi detectada (visual | threshold | drawn)
                        "children": [
                            {"type": "field", "variant": "required", "children": [
                                {"type": "label", "block_id": "uuid-1", "text": "Empresa"},
                                {"type": "image", "image_path": "img-001.png", "bbox": [10,10,100,80], "bbox_valid": true}  # v3.14
                            ]}
                        ]
                    },
                    {
                        "type": "flow",
                        "children": [
                            {
                                "type": "section",
                                "name": "Dados do Cliente",    # inferido ou de structural_hints
                                "variant": "required",
                                "children": [
                                    {"type": "field", "variant": "required", "children": [
                                        {"type": "label", "block_id": "uuid-3", "text": "Nome:"},
                                        {"type": "value", "block_id": "uuid-4", "text": "João Silva"}
                                    ]},
                                    {"type": "field", "variant": "optional", "children": [
                                        {"type": "label", "block_id": "uuid-5", "text": "Cônjuge:"},
                                        {"type": "value", "block_id": "uuid-6", "text": "Maria"}
                                    ]}
                                ]
                            },
                            {
                                "type": "section",
                                "variant": "conditional",
                                "present_in_pdfs": ["0", "2"],
                                "children": [...]         # seção inteira aparece/desaparece
                            },
                            {
                                "type": "table",
                                "table_id": "tbl-uuid-1",
                                "children": [
                                    {"type": "header_row", "children": [...]},
                                    {"type": "data_row", "children": [...]}
                                ]
                            },
                            {                                                    # v3.14: chart detectado pelo Visual Analysis
                                "type": "chart",
                                "bbox": [50, 400, 750, 600],
                                "chart_type": "bar",                             # bar|line|pie|doughnut|polarArea
                                "confidence": 85,
                                "description": "Gráfico de barras com valores mensais",
                                "source": "visual_analysis"
                            },
                            {                                                    # v3.14: barcode detectado pelo Visual Analysis
                                "type": "barcode",
                                "bbox": [100, 750, 400, 800],
                                "barcode_format": "CODE128",                     # CODE128|CODE39|EAN13|EAN8|UPC|ITF|MSI
                                "confidence": 90,
                                "description": "Código de barras horizontal",
                                "source": "visual_analysis"
                            },
                            {                                                    # v3.14: imagem extraída pelo Stage 2
                                "type": "image",
                                "image_path": "img-002.png",
                                "bbox": [300, 620, 500, 720],
                                "bbox_valid": true,
                                "format": "png"
                            }
                        ]
                    },
                    {"type": "footer", "source": "visual", "children": [...]}
                ]
            }
        ]
    }
}

# document_type NÃO é produzido pelo Stage 3 — vem do keyword matching
# existente em pipeline_result.py (_get_document_type). Sem LLM.
# v3.13: removido 3.4 Document Type Detection (era Gemini Flash) — complexidade
# sem retorno. Keywords já resolvem para display no TopToolbar.

context["intelligence"] = {
    "A": {                                            # cluster_id
        "block_classifications": {                    # v3.13 — por block_id (substitui stability_map)
            "uuid-3": {
                "semantic": "label",                  # label | dynamic | semi_dynamic | likely_dynamic (v3.14)
                "stability": "stable",                # stable | variable | rare
                "variant": "required",                # required | optional | conditional
                "presence_ratio": 1.0,                # 0.0-1.0 (% de páginas com este bloco)
                "pdf_coverage": 1.0,                  # 0.0-1.0 (% de PDFs com este bloco)
                "confidence": 1.0,
                "field_pair": "uuid-4",               # v3.13 — block_id do par (label↔value)
                "smart_signals": null                  # v3.14 — sinais NER/regex se houve override (ex: ["regex_date", "ner_PER"])
            },
            "uuid-4": {
                "semantic": "dynamic",
                "stability": "stable",
                "variant": "required",
                "presence_ratio": 1.0,
                "pdf_coverage": 1.0,
                "confidence": 0.95,
                "field_pair": "uuid-3"
            }
        },
        # Views derivadas (conveniência — filtros de block_classifications)
        "labels": ["uuid-3", "uuid-5"],               # block_ids com semantic=label
        "dynamic_fields": ["uuid-4", "uuid-6"],        # block_ids com semantic=dynamic|semi_dynamic|likely_dynamic
        "optional_fields": ["uuid-5", "uuid-6"],       # block_ids com variant=optional
        "conditional_fields": [],                       # block_ids com variant=conditional

        # v3.14 — Qualidade da classificação (Stage 4.5 consome para field_variability)
        "classification_quality": {
            "total_pdfs": 1,                            # quantos PDFs alimentaram este cluster
            "total_pages_in_cluster": 3,                # quantas páginas neste cluster
            "statistical_strength": "none",             # none (1 PDF) | weak (multi-PDF sem variação) | strong (multi-PDF com variação)
            "smart_override_count": 4,                  # quantos blocos tiveram override NER/regex
            "uncertain_count": 2                        # quantos blocos ficaram com confidence < 0.70
        }
    }
}

context["visual_analysis"] = {                         # v3.13 — OBRIGATÓRIO (era opcional)
    "0:0": {                                           # page_key
        "regions": [
            {
                "type": "header",                      # header|body|footer|sidebar|table_area|chart_area|barcode_area|image_area
                "bbox": [0, 0, 800, 120],              # pixels relativos à imagem
                "description": "Logo + nome da empresa",
                "html_suggestion": "<header>...</header>",  # v3.13 — integrado (era separado em Stage 21)
                "chart_type": null,                     # v3.14 — só para chart_area (bar|line|pie|doughnut|polarArea)
                "barcode_format": null,                 # v3.14 — só para barcode_area (CODE128|CODE39|EAN13|EAN8|UPC|ITF|MSI)
                "confidence": null                      # v3.14 — só para chart_area e barcode_area (0-100)
            }
        ],
        "consistency_score": 85,                       # 0-100 (self-check integrado)
        "consistency_level": "consistent"              # consistent (≥80) | partial (50-79) | inconsistent (<50)
    }
}

# Passthrough:
context["enriched_documents"]       # do Stage 2, enriquecido com semantic_label + field_pair
context["xsd_path"]                 # path do XSD original (Stage 4 faz parsing)
context["clusters"]                 # do Stage 1
```

**Garantias:**
- Cada layout tem sua própria árvore hierárquica em `document_trees`
- Cada TextBlock nos enriched_documents tem `semantic_label` preenchido
- Label-value pairs vinculados por `field_pair` (referência cruzada de block_ids)
- Nós da árvore têm `variant` (required/optional/conditional) — alinha com templateStore frontend
- Zonas (header/footer) têm `source` indicando como foram detectadas
- `document_type` produzido pelo `pipeline_result.py` (keyword matching), não pelo Stage 3
- Intelligence tem dados mesmo para single-PDF (com confidence reduzida, sem pdf_coverage cross-PDF)
- `visual_analysis` sempre presente (obrigatório v3.13). Se GPT-4o falhou e operador continuou sem Vision: null com warning em extraction_warnings

### 3.4 Stage 4 Output → Stage 5 Input

```python
context["field_mappings"] = [
    {
        "block_id": str,                    # v3.15 — ID do bloco original (rastreabilidade)
        "layout_type_id": str,              # "layout-A" — v3.15 obrigatório
        "pdf_text": str,
        "label_text": str,
        "bbox": [x0, y0, x1, y1] | null,
        "xsd_field_path": str,              # "cliente.nome" ou "" se unmapped
        "xsd_type": str | null,             # v3.15 — "date", "decimal", "string" do XSD
        "confidence": float,                # 0.0-1.0
        "is_ambiguous": bool,
        "candidates": [{"path": str, "score": float}],
        "page_number": int,
        "pdf_id": str,                  # v3.17 — renomeado de pdf_index (str, consistente)
        "is_table_cell": bool,
        "from_table": bool,
        "detected_format": str | null,      # "currency_brl", "cpf", etc.
        "smart_signals": list | null,       # v3.15 (PA5) — sinais NER/regex do Stage 3
        "semantic_confirmed": str | null,   # v3.15 (PA4) — "dynamic" se XSD confirmou likely_dynamic
        # Frontend-compatible:
        "name": str,
        "path": str,
        "type": str,
        "status": str,                      # "mapped"|"unmapped"|"ambiguous"|"optional"
        "isOptional": bool
    }
]

context["format_functions"] = {
    "currency_brl": "function(value) { ... }",
    "cpf": "function(value) { ... }"
}

# v3.15: per-layout (não global). Cada layout_type tem seus fatores.
context["confidence_scores"] = {
    "layout-A": {
        "layout_stability": float,
        "anchor_detection": float,
        "grid_quality": float,
        "field_variability": float,         # v3.15 (PA1): ajustado por smart_signals + classification_quality
        "vision_agreement": float,          # PA2: consistency_score / 100
        "overall": int,
        "status": str                       # "approved"|"review_recommended"|"human_review_required"
    }
}

context["validation_result"] = {
    "warnings": [str],
    "errors": [str],
    "orphan_count": int,
    "unmapped_xsd_fields": [str],
    "unmapped_required_xsd_fields": [str],  # v3.15 — campos XSD required sem mapping (reverse)
    "type_format_mismatches": [             # v3.15 — XSD type vs detected_format incompatíveis
        {"block_id": str, "xsd_type": str, "detected_format": str, "xsd_path": str}
    ]
}

context["ambiguous_fields"] = [str]

# v3.15 (PA4): block_classifications atualizados com confirmação XSD
context["block_classifications_confirmed"] = {
    "uuid-3": {
        "original_semantic": "likely_dynamic",   # Stage 3 disse
        "confirmed_semantic": "dynamic",         # Stage 4 confirmou via XSD
        "xsd_path": "cliente.nome",
        "xsd_confidence": 0.92
    }
}

# Passthrough:
context["document_trees"]
context["document_type"]
context["document_type_confidence"]
context["intelligence"]
context["visual_analysis"]
context["enriched_documents"]
context["field_tree"]
context["clusters"]
```

### 3.5 Stage 5 Output → Frontend

```python
context["result_json"] = {
    "document_structure": {
        "pages": [SimplifiedPage],
        "layout_types": [LayoutType],
        "root": TreeNode,                       # backward compat — árvore do primeiro layout
        "trees_by_layout": {                    # v3.16 — árvore hierárquica POR LAYOUT
            "layout-A": TreeNode,               # do document_trees (Stage 3.4), não de parsed_documents
            "layout-B": TreeNode
        }
    },
    "field_mappings": [FieldMappingEntry],       # com layout_type_id
    "confidence_scores": {
        "layout-A": ConfidenceFactors
    },
    "coverage": {
        "layout-A": {
            "fields": {"mapped": int, "total": int},
            "tables": {"mapped": int, "total": int},   # v3.16 — contagem real
            "images": {"mapped": int, "total": int},   # v3.16 — contagem real
            "charts": {"mapped": int, "total": int},
            "percentage": int                           # v3.16 — weighted: fields*0.6+tables*0.25+images*0.15
        }
    },
    "layout_types": [LayoutType],
    "template_draft": {                          # POR LAYOUT
        "layout-A": {"html": str, "css": str},
        "layout-B": {"html": str, "css": str}
    },
    "ambiguous_fields": [AmbiguousField],
    "format_functions": {name: js_function},
    "overlay_items": {
        "layout-A": [BackendOverlayItem]         # v3.16 — filtrado por layout_type_id
    },
    "document_type": str,
    "document_type_confidence": float,
    "visual_analysis": {...},                    # v3.13 — obrigatório (null só se operador continuou sem Vision)
    "intelligence": {...},                       # v3.16 — block_classifications por block_id
    "validation_result": {                       # v3.16 — do Stage 4
        "warnings": [str],
        "errors": [str],
        "orphan_count": int,
        "unmapped_required_xsd_fields": [str],
        "type_format_mismatches": [...]
    },
    "block_classifications_confirmed": {...},    # v3.16 (PA4) — confirmações XSD
    "multi_doc": {                               # v3.16 (PA6) — para multiDocStore
        "pdfs": [PdfDocument],                   # {id, name, role, sizeKB, pages, uploadedAt}
        "matrix": VariationMatrix,               # {layoutIds, variationIds, cells}
        "detections": [Detection]                # inferidos de variant + present_in_pdfs
    },
    "page_config": {                             # v3.16 (G17-S5) — para usePagination
        "size": str,                             # "A4" | "letter" | "custom"
        "orientation": str,                      # "portrait" | "landscape"
        "header_height_px": int,                 # do visual_analysis ou fallback 15%
        "footer_height_px": int,                 # do visual_analysis ou fallback 10%
        "margins": {"top": int, "bottom": int, "left": int, "right": int}
    }
}
```

---

## 4. Mapeamento: Estágios Atuais → Novos Sub-steps

| Stage Atual | # | Vai para | Sub-step | Mudanças |
|-------------|---|----------|----------|----------|
| XSD Parser | 29 | **Stage 4** | 4.1 | **MOVIDO v3.12**: de Stage 2 para Stage 4 — XSD é consumido pelo Field Mapping, não pela extração de PDF |
| Text Extraction | 2 | **Stage 1** (leve) + **Stage 2** (profundo) | 1.2 + 2.1 | Stage 1 usa `get_text("blocks")`. Stage 2 usa `get_text("dict")` + `page.rect` + `span["flags"]` só nas representativas |
| Text Reconstruction | 3 | **Stage 2** | 2.2 | **MELHORADO**: threshold proporcional ao font_size, preserva sub_spans |
| Font Extraction | 4 | **Stage 2** | 2.3 | **MELHORADO**: FONT_MAP expandido (~50 fontes), bold/italic de span flags |
| Image Extraction | 5 | **Stage 2** | 2.4 | **MELHORADO**: filtrar masks, validar bbox, marcar bbox_valid |
| Grid Detection | 6 | **Stage 1** (DBSCAN) + **Stage 2** (refinado) | 1.6 + 2.6 | Stage 1: DBSCAN eps=0.02. Stage 2: **MUDOU** Jenks Natural Breaks, excluir header/footer zones |
| Screenshot Generator | 2b | **Stage 2** | 2.5 | **MELHORADO**: SÓ representativas, alpha=False (fundo branco) |
| Skeleton Builder | 7 | **Stage 1** | 1.7 (parte do fingerprint) | Absorvido no fingerprint construction |
| Page Clustering | 8 | **Stage 1** | 1.8 + 1.9 | **REESCRITO**: Graph clustering + weighted similarity substitui KMeans |
| Representative Selection | 9 | **Stage 1** | 1.10 | **MUDOU**: Highest degree no grafo em vez de distância ao centróide |
| Fingerprint Generation | 10 | **Stage 1** | 1.7 | **MUDOU**: Fingerprint ANTES do clustering como input da similarity |
| Registry Lookup | 11 | **Stage 2** | (sub-step opcional) | Pode rodar depois do fingerprint, antes da deep extraction |
| Layout Alignment | 12 | **Stage 3** | 3.1 (parte) | **v3.13**: absorvido no Multi-Example Analysis. Cross-cluster descartado (Stage 4 resolve via XSD) |
| Multi-Example Analysis | 13 | **Stage 3** | 3.1 | **v3.13**: reordenado para primeiro sub-step. Produz label/dynamic + stability + variants |
| Stability Classification | 14 | **Stage 3** | 3.1 (parte) | **v3.13**: consolidado em 3.1 (mesma passada sobre _raw_text_blocks) |
| Variant Detection | 15 | **Stage 3** | 3.1 (parte) | **v3.13**: consolidado em 3.1 (mesma passada sobre _raw_text_blocks) |
| Intelligence Normalization | 16 | **Stage 3** | 3.3 (parte) | **v3.13**: absorvido no Semantic Classification (block_classifications por block_id) |
| Table Detection | 17 | **Stage 2** | 2.7 | **REESCRITO**: PyMuPDF `find_tables()` com ruling lines + clustering built-in, multi-tabela por página |
| Table Structuring | 18 | **Stage 2** | 2.8 | **REESCRITO**: cells com bbox preservado, multi-page % height (não hardcoded 700pts) |
| Semantic Analysis | 19 | **Stage 3** | 3.3 | **v3.13 MELHORADO**: enriquecido com sinais de 3.1 (intelligence) + 3.2 (visual regions) + cor + font_size. Inclui label-value pairing (movido do Stage 4.2) |
| Visual Segmentation | 20 | **Stage 3** | 3.2 | **v3.13 REESCRITO**: obrigatório, movido de 3.7 para 3.2. Combinado com Stages 21+22 em 1 chamada GPT-4o |
| Visual Interpretation | 21 | **Stage 3** | 3.2 | **v3.13**: consolidado na chamada única do 3.2 (html_suggestion por região) |
| Vision Self-Check | 22 | **Stage 3** | 3.2 | **v3.13**: consolidado na chamada única do 3.2 (consistency_score integrado) |
| Field Matching | 23 | **Stage 4** | 4.5 | **v3.15 REESCRITO**: batch LLM (1/layout) com hints (seção XSD + formato), two-pass, PA4 (XSD confirma likely_dynamic) |
| Format Detection | 24 | **Stage 4** | 4.3 | **v3.15 REORDENADO**: movido para ANTES do Field Matching — formato enriquece prompt LLM |
| Confidence Scoring | 25 | **Stage 4** | 4.6 | **v3.15 REESCRITO**: per-layout (não global), heurísticas (sem Claude Sonnet), PA1 (smart_signals → field_variability) |
| Layout Consistency | 26 | **Stage 4** | 4.7 | **v3.15 MELHORADO**: consome document_trees + block_classifications, reverse mapping, tipo↔formato |
| Template Draft | 27 | **Stage 5** | 5.1 + 5.2 | **v3.16 REESCRITO**: Tree-Driven HTML (walk document_trees), `<table>` real, condicionais, CSS-from-Extraction (fonts/cores/backgrounds) |
| Pipeline Result | 28 | **Stage 5** | 5.6 | **v3.16 REESCRITO**: trees_by_layout, coverage multidimensional, overlay per-layout, VariationMatrix (PA6), validation_result, intelligence |

### Novos sub-steps (não existem hoje)

| Sub-step | Stage | O que faz |
|----------|-------|-----------|
| 1.3 Normalization | 1 | **NOVO**: Normaliza bbox por page_width/height (0-1 range) |
| 1.4 Header/Footer Removal | 1 | **NOVO**: Remove blocos em >80% das páginas antes de comparar |
| 1.5 Content Abstraction | 1 | **NOVO**: Transforma texto em categorias (DATE, NUMBER, TEXT_SHORT, TEXT_LONG) |
| 1.7 Spatial Bitmap | 1 | **NOVO**: Grade 10×14 de ocupação — captura forma visual do layout |
| 1.11 Consensus Check | 1 | **NOVO**: Hierarchical clustering valida graph clustering |
| 1.10 Cluster Quality Score | 1 | **NOVO**: Mede coesão intra-cluster, identifica membros suspeitos |
| 1.11 pHash Cross-Check | 1 | **NOVO**: Segundo sinal independente — compara pixels, não texto |
| 1.12 Representative Validation | 1 | **NOVO**: Verifica representante contra amostra do cluster |
| 1.13 LLM Cluster Validation | 1 | **NOVO v3.11**: Gemini Flash valida clusters via thumbnails (~$0.003) |
| 1.14 Auto-correction | 1 | Merge/split/isolate baseado em evidências da Camada 2 |
| 1.15 Confidence Score | 1 | Score 0-1 por cluster (quality + pHash + consensus + LLM) |
| 1.16 Document Homogeneity Check | 1 | **NOVO v3.11**: Detecta PDFs de template diferente no pool (`shared_ratio < 0.20` = suspeito). Trigger do checkpoint humano |
| 3.4 Hierarchy Builder | 3 | **NOVO v3.13 MELHORADO**: 4 sinais em cascata (visual regions + drawn_elements + grid_info + gap proporcional). Label-value pairs como nós `field`. Seções condicionais como nós com `variant`. document_type vem do keyword matching existente (pipeline_result.py) |
| 2.10 Extraction Quality Check | 2 | **NOVO**: Valida text_blocks (vazio, encoding, duplicatas OCR), gera extraction_warnings |
| 5.3 Coverage Calculation | 5 | **NOVO**: Contabiliza fields + tables + images + charts |
| — Feedback Loop | 4 | **NOVO**: Detecta inconsistências no cluster via field_mappings, emite warnings |

---

## 5. Stage 1 — Detalhamento Técnico Completo

### Princípio: Se Stage 1 erra, todo o pipeline erra

O clustering é **irreversível downstream**. Nenhum estágio posterior questiona ou corrige as decisões do Stage 1. Por isso, Stage 1 tem **3 camadas de defesa + validação** com **16 sub-steps** internos em **pool único**.

### Arquitetura Multi-PDF: Pool Único + Homogeneity Check

**Premissa fundamental:** Todos os PDFs de um job são do **MESMO template**. Subir vários PDFs serve para dar mais exemplos ao motor — detectar condicionais (show/hide), variação de cor, campos opcionais. O sistema constrói **um template por vez**, não vários simultaneamente.

**Por que pool único (e não 2 fases):**

Os 3 argumentos originais para clustering em 2 fases (intra-PDF + cross-PDF merge) caíram com as resoluções v3.8/v3.9:

1. ~~"Header/footer detection quebra no pool"~~ → v3.8 substituiu header/footer removal por **region filtering adaptativo** (não usa threshold de presença)
2. ~~"O(n²) comparações inúteis cross-PDF"~~ → Se todos são o mesmo template, comparações cross-PDF são **ÚTEIS** (mais dados = clustering mais robusto)
3. ~~"DBSCAN mistura grids"~~ → v3.9 removeu grid detection do Stage 1 (movido para Stage 2)

**Abordagem:** Todas as páginas de todos os PDFs entram no **mesmo pool** de clustering. Cada página preserva `pdf_id` — downstream sabe a origem. A simplicidade do pool único elimina a complexidade de Phase B (5 sub-steps de merge) e garante que páginas equivalentes de PDFs diferentes caiam naturalmente no mesmo cluster.

**Proteção contra erro humano — Homogeneity Check (step 1.16):**

Se alguém enviar por engano um PDF de template diferente, o **Document Homogeneity Check** detecta:
- Para cada PDF, calcula `shared_ratio` = % de páginas em clusters que têm contribuição de outros PDFs
- Se `shared_ratio < 0.20` → documento de template diferente detectado (suas páginas formaram clusters exclusivos)
- Trigger do checkpoint humano com opção de remover o documento incompatível

**Impacto em downstream (Stages 2-5):**

| Feature downstream | Requisito | Pool único garante? |
|-------------------|-----------|---------------------|
| Multi-Example Analysis (Stage 3.2) | Páginas de múltiplos PDFs no mesmo cluster | ✓ Pool único agrupa naturalmente (mesmo template) |
| Stability Classification (Stage 3.3) | Comparar presença/ausência entre PDFs | ✓ Cluster contém pages de todos os PDFs com `pdf_id` |
| Variant Detection (Stage 3.4) | `optional_field`, `conditional_section` | ✓ Funciona idêntico — lê `pdf_id` das pages |
| Diff no Editor (diffStore) | VariationMatrix por `pdfId` | ✓ Frontend usa `document_id`, não `cluster_id` — agnóstico |
| Single-PDF | Homogeneity Check = no-op | ✓ Degrada gracefully |
| PDF errado enviado | Detectar e avisar operador | ✓ Homogeneity Check + checkpoint humano |

| Camada | Propósito | Sub-steps | Custo |
|--------|-----------|-----------|-------|
| Prevenção | Reduzir a chance de errar | 1.1–1.9 | ~2s para 100 páginas |
| Detecção | Identificar quando errou | 1.10–1.13 | ~3s + ~$0.003 (LLM) |
| Correção | Corrigir erros detectados | 1.14–1.15 | ~0.5s |
| Validação | Detectar documento de template diferente | 1.16 | ~0.1s |

---

### Orquestrador Stage 1

```python
async def stage_1_layout_clustering(pdf_documents: list[dict], context: dict, job: dict):
    """Stage 1 orquestrador — pool único com homogeneity check.

    Premissa: todos os PDFs são do MESMO template.
    Todas as páginas entram no mesmo pool com pdf_id preservado.
    Homogeneity check detecta PDF de template diferente enviado por engano.

    Args:
        pdf_documents: [{id: str, path: str, name: str}]
            - id vem da Fase 0 (Storage Gateway) = UUID do Supabase
            - Em dev/testes sem Fase 0: id = str(index)
            - O pipeline NUNCA gera IDs — recebe de quem chamou
    """

    # ═══════════════════════════════════════════
    # CAMADA 1 — PREVENÇÃO (steps 1.1–1.9)
    # ═══════════════════════════════════════════
    all_pages = []
    raw_text_blocks = {}  # preservar para Stage 3 (G8)

    for i, pdf_doc in enumerate(pdf_documents):
        pdf_id = pdf_doc["id"]    # str — UUID ou str(index)
        pdf_path = pdf_doc["path"]
        await emit_progress({"stage": "clustering", "step": "extraction",
                             "pdf": i + 1, "total_pdfs": len(pdf_documents)})

        # Step 1.1 — Page Extraction + Classification
        pages = extract_and_classify_pages(pdf_path, pdf_id)  # text/scanned/blank
        all_pages.extend(pages)

        # Step 1.2 — Block Extraction + preservar _raw_text_blocks
        blocks = extract_blocks(pages)
        for page in pages:
            page_key = f"{pdf_id}:{page['page_index']}"
            raw_text_blocks[page_key] = [
                {"text": b["text"], "bbox_norm": b["bbox_norm"],
                 "x_center": b["x_center"], "y_center": b["y_center"], "type": b["type"]}
                for b in blocks[page["page_index"]] if b["type"] == 0
            ]

    # Step 1.3 — Normalization (rotation + coords)
    blocks_norm = normalize_blocks(all_pages)

    # Step 1.4 — Content Abstraction
    blocks_abstract = abstract_content(blocks_norm)

    # Step 1.5 — Region Filtering Adaptativo
    blocks_filtered = region_filter(blocks_abstract)

    # Step 1.6 — Tolerant Similarity Matrix (geo 0.8 + den 0.2)
    sim_matrix = compute_tolerant_similarity_matrix(blocks_filtered)

    # Step 1.7 — Graph Clustering
    clusters, disagreements = consensus_clustering(sim_matrix)

    # Step 1.8 — Consensus Check
    # (integrado no consensus_clustering acima)

    # Step 1.9 — Representative Selection (weighted degree)
    representatives = select_representatives_weighted(clusters, sim_matrix)

    # ═══════════════════════════════════════════
    # CAMADA 2 — DETECÇÃO (steps 1.10–1.13)
    # ═══════════════════════════════════════════
    # Step 1.10 — Cluster Quality Score
    quality = {c: cluster_quality(c, sim_matrix) for c in clusters}

    # Step 1.11 — pHash Cross-Check
    visual_hashes = compute_visual_hashes(all_pages)
    visual_warnings = cross_check_visual(clusters, visual_hashes, sim_matrix)

    # Step 1.12 — Representative Validation
    rep_validations = {c: validate_representative(r, c, sim_matrix)
                       for c, r in representatives.items()}

    # Step 1.13 — LLM Cluster Validation (Gemini Flash ~$0.003)
    llm_result = await llm_validate_clusters(clusters, all_pages, vision_client)

    # ═══════════════════════════════════════════
    # CAMADA 3 — CORREÇÃO (steps 1.14–1.15)
    # ═══════════════════════════════════════════
    # Step 1.14 — Auto-correction
    corrected, corrections = auto_correct_clusters(
        clusters, quality, visual_warnings, llm_result, sim_matrix)

    # Step 1.15 — Confidence Score
    final_clusters = []
    for c in corrected:
        c["confidence"] = compute_confidence(
            c, quality[c["cluster_id"]], visual_warnings, disagreements, llm_result)
        final_clusters.append(c)

    # ═══════════════════════════════════════════
    # VALIDAÇÃO — Homogeneity Check (step 1.16)
    # ═══════════════════════════════════════════
    pdf_ids = [doc["id"] for doc in pdf_documents]  # str[] — IDs reais
    mismatched_pdfs = check_document_homogeneity(final_clusters, pdf_ids)

    # ═══════════════════════════════════════════
    # CHECKPOINT HUMANO (condicional)
    # ═══════════════════════════════════════════
    low_confidence = [c for c in final_clusters if c["confidence"]["level"] == "low"]
    needs_checkpoint = (
        bool(low_confidence) or
        bool(corrections) or
        bool(mismatched_pdfs) or
        job.get("config", {}).get("cluster_confirmation") == "always"
    )

    if needs_checkpoint:
        response = await emit_cluster_checkpoint(
            final_clusters, job, mismatched_pdfs=mismatched_pdfs)

        # Se operador removeu PDFs incompatíveis, purgar dos clusters
        removed_pdf_ids = set(response.get("removed_pdf_ids", []))
        if removed_pdf_ids:
            for cluster in final_clusters:
                cluster["pages"] = [
                    p for p in cluster["pages"]
                    if p["pdf_id"] not in removed_pdf_ids
                ]
            # Remover clusters vazios após purga
            final_clusters = [c for c in final_clusters if c["pages"]]
            # Limpar raw_text_blocks das páginas removidas
            raw_text_blocks = {
                k: v for k, v in raw_text_blocks.items()
                if k.split(":")[0] not in removed_pdf_ids
            }

    # Escrever no contexto — clusters já limpos (sem PDFs removidos)
    context["clusters"] = final_clusters
    context["_raw_text_blocks"] = raw_text_blocks
```

---

### CAMADA 1 — PREVENÇÃO

#### 5.1 Block Extraction: `get_text("blocks")` vs `get_text("dict")`

| Aspecto | `get_text("blocks")` (Stage 1) | `get_text("dict")` (Stage 2) |
|---------|-------------------------------|------------------------------|
| Output | `(x0, y0, x1, y1, text, block_no, type)` | blocks → lines → spans com font_name, font_size |
| Informação | Posição + texto. **Sem fontes.** | Tudo: posição, texto, fontes, estilos |
| Velocidade | ~0.3s para 100 páginas | ~1s para 100 páginas |
| Propósito | Comparar geometria de páginas | Extrair conteúdo completo |

Stage 1 **não precisa** de fontes para comparar layouts. A posição dos blocos e o tipo de conteúdo (após abstração) são suficientes.

### 5.2 Content Abstraction

```python
import re

def abstract_content(text: str) -> str:
    text = text.strip()
    if re.match(r'\d{2}[/.-]\d{2}[/.-]\d{2,4}', text):
        return "DATE"
    if re.match(r'^R?\$?\s*[\d.,]+$', text):
        return "NUMBER"
    if len(text) <= 30:
        return "TEXT_SHORT"
    return "TEXT_LONG"
```

Duas páginas com "R$ 1.234,56" vs "R$ 789,00" na mesma posição → ambas "NUMBER" → reconhecidas como mesmo template.

### 5.3 Grid Detection com DBSCAN

```python
from sklearn.cluster import DBSCAN
import numpy as np

def detect_grid(blocks, page_width):
    x_coords = np.array([b["bbox_norm"][0] for b in blocks]).reshape(-1, 1)
    clustering = DBSCAN(eps=0.02, min_samples=2).fit(x_coords)
    # eps=0.02 = 2% da largura da página normalizada
    column_centers = []
    for label in set(clustering.labels_):
        if label == -1: continue  # noise
        mask = clustering.labels_ == label
        column_centers.append(float(np.mean(x_coords[mask])))
    return sorted(column_centers)
```

**Vantagem sobre KMeans:** DBSCAN não precisa de k pré-definido. Descobre clusters naturalmente com eps como threshold de distância.

### 5.4 Similarity Matrix

```python
def compute_similarity(fp_a, fp_b):
    # Pesos do spec externo
    w_structure = 0.3
    w_table = 0.3
    w_alignment = 0.2
    w_density = 0.2

    s_structure = 1.0 - abs(fp_a["column_count"] - fp_b["column_count"]) / max(fp_a["column_count"], fp_b["column_count"], 1)
    s_table = 1.0 if fp_a["has_header"] == fp_b["has_header"] and fp_a["has_footer"] == fp_b["has_footer"] else 0.5
    s_alignment = _alignment_score(fp_a, fp_b)  # IoU das posições de colunas
    s_density = 1.0 - abs(fp_a["density"] - fp_b["density"])

    return w_structure * s_structure + w_table * s_table + w_alignment * s_alignment + w_density * s_density
```

### 5.5 Graph Clustering

```python
import networkx as nx

def cluster_pages(fingerprints, threshold=0.85):
    G = nx.Graph()
    for i, fp_i in enumerate(fingerprints):
        G.add_node(i)
        for j in range(i + 1, len(fingerprints)):
            sim = compute_similarity(fp_i, fingerprints[j])
            if sim >= threshold:
                G.add_edge(i, j, weight=sim)

    clusters = list(nx.connected_components(G))
    return clusters

def select_representative(G, cluster):
    # Highest degree = mais conexões = mais "típica"
    degrees = {n: G.degree(n) for n in cluster}
    return max(degrees, key=degrees.get)
```

### 5.6 Header/Footer Removal (histórico — substituído por Region Filtering)

> **NOTA (v3.11):** Esta função foi substituída por **Region Filtering Adaptativo** (v3.8).
> No pool único, region filtering não depende de threshold de presença — filtra por posição
> geométrica (header zone / footer zone), funcionando corretamente independente da quantidade de PDFs.

```python
def remove_common_blocks(single_pdf_pages_blocks, threshold=0.80):
    """Remove blocos que aparecem em >80% das páginas DE UM ÚNICO PDF."""
    n_pages = len(single_pdf_pages_blocks)
    block_freq = {}  # text_abstract + bbox_norm_rounded → count

    for page_blocks in single_pdf_pages_blocks:
        seen = set()
        for b in page_blocks:
            key = (b["text_abstract"], tuple(round(x, 2) for x in b["bbox_norm"]))
            if key not in seen:
                block_freq[key] = block_freq.get(key, 0) + 1
                seen.add(key)

    common_keys = {k for k, v in block_freq.items() if v / n_pages >= threshold}

    for page_blocks in single_pdf_pages_blocks:
        page_blocks[:] = [
            b for b in page_blocks
            if (b["text_abstract"], tuple(round(x, 2) for x in b["bbox_norm"])) not in common_keys
        ]

    return common_keys  # para debug/log
```

### 5.7 Spatial Bitmap (NOVO)

Divide a página normalizada em grade 10×14 e marca quais células têm conteúdo. Captura a **forma visual** do layout, não apenas métricas resumidas.

```python
def spatial_bitmap(blocks_normalized, cols=10, rows=14):
    """Cria bitmap de ocupação da página — 140 bits."""
    bitmap = [[0] * cols for _ in range(rows)]
    for b in blocks_normalized:
        x_center = (b["bbox_norm"][0] + b["bbox_norm"][2]) / 2
        y_center = (b["bbox_norm"][1] + b["bbox_norm"][3]) / 2
        col = min(int(x_center * cols), cols - 1)
        row = min(int(y_center * rows), rows - 1)
        bitmap[row][col] = 1
    return bitmap

def bitmap_similarity(bm_a, bm_b):
    """Jaccard similarity entre dois bitmaps."""
    union = intersection = 0
    for r in range(len(bm_a)):
        for c in range(len(bm_a[0])):
            if bm_a[r][c] or bm_b[r][c]:
                union += 1
            if bm_a[r][c] and bm_b[r][c]:
                intersection += 1
    return intersection / union if union > 0 else 1.0
```

**Exemplo visual:**
```
Boleto:            Extrato:
██░░░░░░██         ██████████
██████████         ░░░░░░░░░░
░░░░░░░░░░         ██░██░██░█
██░░░░██░░         ██░██░██░█
██░░░░██░░         ██░██░██░█
░░░░░░░░░░         ██░██░██░█
██████████         ██░██░██░█
░░██████░░         ░░░░░░░░░░
```

Fingerprints abstratos poderiam ser iguais (mesma densidade, mesmas colunas). Bitmaps são **claramente diferentes**.

### 5.8 Similarity Matrix (atualizada com bitmap)

A similarity matrix agora usa **6 fatores** em vez de 4:

```python
def compute_similarity(fp_a, fp_b):
    w_structure  = 0.20   # column_count
    w_table      = 0.20   # has_header, has_footer
    w_alignment  = 0.15   # IoU das posições de colunas
    w_density    = 0.10   # densidade de texto
    w_bitmap     = 0.25   # spatial bitmap similarity (NOVO)
    w_block_count = 0.10  # número de blocos similar (NOVO)

    s_structure = 1.0 - abs(fp_a["column_count"] - fp_b["column_count"]) / max(fp_a["column_count"], fp_b["column_count"], 1)
    s_table = 1.0 if fp_a["has_header"] == fp_b["has_header"] and fp_a["has_footer"] == fp_b["has_footer"] else 0.5
    s_alignment = _column_iou(fp_a["column_positions"], fp_b["column_positions"])
    s_density = 1.0 - abs(fp_a["density"] - fp_b["density"])
    s_bitmap = bitmap_similarity(fp_a["bitmap"], fp_b["bitmap"])
    s_blocks = 1.0 - abs(fp_a["block_count"] - fp_b["block_count"]) / max(fp_a["block_count"], fp_b["block_count"], 1)

    return (w_structure * s_structure + w_table * s_table + w_alignment * s_alignment +
            w_density * s_density + w_bitmap * s_bitmap + w_block_count * s_blocks)
```

**Bitmap tem o maior peso (0.25)** porque é o sinal mais discriminativo — captura a forma real do layout.

### 5.9 Consensus Check (NOVO)

Roda **dois algoritmos** de clustering independentes e compara:

```python
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

def consensus_clustering(sim_matrix, threshold_graph=0.85):
    # Approach A: Graph (NetworkX)
    clusters_graph = graph_cluster(sim_matrix, threshold=threshold_graph)

    # Approach B: Hierarchical (SciPy — average linkage)
    dist_matrix = 1.0 - sim_matrix
    Z = linkage(squareform(dist_matrix), method='average')
    labels_hier = fcluster(Z, t=1.0 - threshold_graph, criterion='distance')
    clusters_hier = _labels_to_sets(labels_hier)

    # Consensus: só agrupa se AMBOS concordam
    consensus = _intersect_clusterings(clusters_graph, clusters_hier)

    # Divergências viram clusters separados (conservador)
    disagreements = _find_disagreements(clusters_graph, clusters_hier)

    return consensus, disagreements
```

Se os dois concordam → alta confiança. Se discordam → mantém separado (conservador) e flagga na Camada 2.

---

### CAMADA 2 — DETECÇÃO

#### 5.10 Cluster Quality Score (NOVO)

Após clustering, mede a coesão interna de cada cluster:

```python
def cluster_quality(cluster_pages, sim_matrix):
    """Retorna quality score e identifica membros outliers (baixa similaridade)."""
    if len(cluster_pages) <= 1:
        return {"score": 1.0, "outliers": []}

    pair_scores = []
    for i, j in combinations(cluster_pages, 2):
        pair_scores.append(sim_matrix[i][j])

    min_sim = min(pair_scores)
    avg_sim = sum(pair_scores) / len(pair_scores)

    outliers = []
    if min_sim < 0.75:
        # Encontrar o membro que mais destoa
        for page in cluster_pages:
            page_avg = mean([sim_matrix[page][other] for other in cluster_pages if other != page])
            if page_avg < 0.78:
                outliers.append({"page": page, "avg_similarity": page_avg})

    return {
        "score": avg_sim,
        "min_similarity": min_sim,
        "outliers": outliers,
        "status": "OUTLIER" if min_sim < 0.75 else "OK"
    }
```

#### 5.11 Visual Hash — pHash (NOVO)

Segundo sinal completamente independente da extração de texto:

```python
import imagehash
from PIL import Image
import fitz

def compute_visual_hash(pdf_page, size=128):
    """Renderiza thumbnail e calcula perceptual hash."""
    scale = size / max(pdf_page.rect.width, pdf_page.rect.height)
    pix = pdf_page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return imagehash.phash(img)

def visual_hash_agrees(hash_a, hash_b, max_distance=10):
    """Dois hashes com diferença ≤ 10 bits → visualmente similares."""
    distance = hash_a - hash_b  # Hamming distance (0-64)
    similarity = 1.0 - distance / 64.0
    return {
        "agrees": distance <= max_distance,
        "distance": distance,
        "similarity": similarity
    }
```

**Cross-check:** Se o clustering de texto diz "mesma cluster" mas pHash diz "visualmente diferentes" → **ALERTA**.

```python
def cross_check_visual(clusters, visual_hashes, sim_matrix):
    """Verifica se clusters visuais concordam com clusters de texto."""
    warnings = []
    for cluster_id, pages in clusters.items():
        rep = pages[0]  # representante
        for member in pages[1:]:
            text_sim = sim_matrix[rep][member]
            visual = visual_hash_agrees(visual_hashes[rep], visual_hashes[member])
            if text_sim >= 0.85 and not visual["agrees"]:
                warnings.append({
                    "type": "text_visual_disagreement",
                    "cluster_id": cluster_id,
                    "pages": [rep, member],
                    "text_similarity": text_sim,
                    "visual_similarity": visual["similarity"],
                    "message": f"Text says same cluster but visually different (hash distance={visual['distance']})"
                })
    return warnings
```

#### 5.12 Representative Validation (NOVO)

Após escolher o representante, verifica contra amostra aleatória:

```python
def validate_representative(representative, cluster_members, sim_matrix, sample_size=3):
    """O representante realmente representa o cluster?"""
    sample = random.sample(cluster_members, min(sample_size, len(cluster_members)))
    for member in sample:
        sim = sim_matrix[representative][member]
        if sim < 0.80:
            return {
                "valid": False,
                "outlier": member,
                "similarity": sim,
                "suggestion": "Consider different representative or split cluster"
            }
    return {"valid": True}
```

> **Nota (v3.11):** LLM Cluster Validation está na **Camada 2** (step 1.13). Valida os clusters do pool único —
> confirma que os clusters representam layouts realmente diferentes. Custo: ~$0.003 para 3 clusters (Gemini Flash).
> Sem Phase B, o LLM valida o resultado final diretamente, simplificando o fluxo.

---

### CAMADA 3 — CORREÇÃO

#### 5.14 Auto-correction

Baseado nos resultados da Camada 2 (incluindo LLM), aplica correções automáticas:

```python
def auto_correct_clusters(clusters, quality_scores, visual_warnings, llm_result, sim_matrix):
    """Corrige clusters baseado em evidências da Camada 2.

    Usa quality score, pHash, consensus e resultado LLM para decidir
    split/merge/isolate.
    """
    corrections = []

    # 1. Visual hash disagreement → isolate o membro que destoa
    for warning in visual_warnings:
        if warning["type"] == "text_visual_disagreement":
            corrections.append({"action": "isolate", "page": warning["pages"][1],
                                 "from_cluster": warning["cluster_id"],
                                 "reason": f"Visual hash disagrees (distance={warning['visual_similarity']:.2f})"})

    # 2. Quality score SUSPECT → sub-divide com threshold mais alto
    for cluster_id, quality in quality_scores.items():
        if quality["status"] == "SUSPECT" and cluster_id not in [c.get("cluster") for c in corrections]:
            corrections.append({"action": "re-cluster", "cluster": cluster_id,
                                 "threshold": 0.92,  # mais restritivo
                                 "reason": "Low quality score"})

    # Aplicar correções
    corrected_clusters = apply_corrections(clusters, corrections)
    return corrected_clusters, corrections
```

**Regra de ouro:** Split quando pelo menos **uma** fonte algorítmica identifica problema. Na dúvida, manter separado (conservador).

#### 5.15 Confidence Score

Cada cluster sai com um score de confiança final:

```python
def compute_confidence(cluster, quality, visual_check, consensus_agreed, llm_result):
    """Confiança do cluster — 0.0 a 1.0.
    Combina quality, pHash, consensus e LLM (4 fatores).
    """
    factors = {
        "quality_score": quality["score"],                          # 0-1
        "visual_agreement": 1.0 if not visual_check.get("warnings") else 0.5,
        "consensus": 1.0 if consensus_agreed else 0.6,
        "llm_validated": llm_result.get("confidence", 0.5) if llm_result else 0.5,
    }

    weights = {"quality_score": 0.35, "visual_agreement": 0.25,
               "consensus": 0.20, "llm_validated": 0.20}
    confidence = sum(weights[k] * factors[k] for k in weights)

    return {
        "confidence": round(confidence, 3),
        "factors": factors,
        "level": "high" if confidence >= 0.85 else "medium" if confidence >= 0.70 else "low"
    }
```

---

### ~~FASE B — REMOVIDA (v3.11)~~

> **v3.11:** Phase B (cross-PDF merge) foi removida. Com pool único, todas as páginas
> já são clusterizadas juntas. Merge cross-PDF não é mais necessário porque todos os
> PDFs de um job são do mesmo template. As seções 5.16-5.20 originais foram substituídas
> pelo Document Homogeneity Check (step 1.16) e LLM movido para Camada 2 (step 1.13).

#### 5.16 Document Homogeneity Check (NOVO — v3.11)

Após a Camada 3 (auto-correction + confidence score), verifica se todos os PDFs do job são realmente do mesmo template:

```python
def check_document_homogeneity(clusters, pdf_ids):
    """Detecta PDFs que parecem ser de template diferente.

    Para cada PDF, calcula a proporção de suas páginas que caíram em
    clusters compartilhados (que contêm páginas de outros PDFs).
    Se a maioria das páginas de um PDF ficou em clusters exclusivos,
    provavelmente é um template diferente.

    Threshold: shared_ratio < 0.20 = documento de template diferente.
    """
    cluster_pdfs = {}
    for cluster in clusters:
        contributing = {p["pdf_id"] for p in cluster["pages"]}
        cluster_pdfs[cluster["cluster_id"]] = contributing

    mismatched_pdfs = []
    for pdf_id in pdf_ids:
        pdf_pages = []
        for cluster in clusters:
            for page in cluster["pages"]:
                if page["pdf_id"] == pdf_id:
                    pdf_pages.append(cluster["cluster_id"])

        total = len(pdf_pages)
        shared = sum(1 for cid in pdf_pages if len(cluster_pdfs[cid]) > 1)
        shared_ratio = shared / total if total > 0 else 0

        if shared_ratio < 0.20:
            mismatched_pdfs.append({
                "pdf_id": pdf_id,
                "shared_ratio": shared_ratio,
                "total_pages": total,
                "exclusive_clusters": [
                    cid for cid in set(pdf_pages) if len(cluster_pdfs[cid]) == 1
                ]
            })
    return mismatched_pdfs
```

**Comportamento:**
- Se `shared_ratio >= 0.20` → PDF normal (maioria das páginas compartilha clusters com outros PDFs)
- Se `shared_ratio < 0.20` → documento de template diferente → trigger do checkpoint humano
- Single-PDF jobs → skip (sem comparação possível)

**Checkpoint humano atualizado (v3.11):**

| Trigger | Condição | Ação UI |
|---------|----------|---------|
| Low confidence | Algum cluster com confidence < 0.70 | Mostra clusters com thumbnails para revisão |
| Auto-correction | Pipeline corrigiu clusters automaticamente | Mostra correções para confirmação |
| **template_mismatch** (NOVO) | Homogeneity check detectou `shared_ratio < 0.20` | **Documento incompatível detectado — opção de remover** |
| Always confirm | Job config `cluster_confirmation: "always"` | Sempre mostra para revisão |

**Tela do checkpoint (quando documento incompatível):**
- Clusters com thumbnails (já existia)
- **NOVO:** Mensagem: _"O documento **{nome_pdf}** parece ser de um template diferente dos demais. Apenas {shared_ratio}% das suas páginas são compatíveis com os outros documentos."_
- Ações: `[Remover e continuar]` (primária) `[Manter mesmo assim]` (secundária) `[Cancelar processo]` (terciária)

#### 5.13 LLM Cluster Validation (Camada 2 — v3.11)

Validação via LLM Vision dos clusters resultantes do pool único. Confirma que os clusters representam layouts realmente diferentes:

```python
async def llm_validate_clusters(clusters, all_pages, vision_client):
    """Envia thumbnails dos representativos para LLM Vision (Gemini Flash).

    Posição: Camada 2 (step 1.13) — após quality/pHash/representative validation.
    Custo: ~$0.003 para 3 clusters — pago UMA vez.
    """
    if len(clusters) <= 1:
        return {"all_different": True, "confidence": 1.0}  # 1 cluster = nada a validar

    thumbnails = []
    for cluster in clusters:
        rep = cluster["representative_page"]
        page = get_page(all_pages, rep["pdf_id"], rep["page_index"])
        pix = page.get_pixmap(matrix=fitz.Matrix(128/page.rect.width, 128/page.rect.height))
        img_b64 = base64.b64encode(pix.tobytes("png")).decode()

        pdf_sources = list({p["pdf_id"] for p in cluster["pages"]})
        thumbnails.append({
            "cluster_id": cluster["cluster_id"],
            "page_count": cluster["page_count"],
            "pdf_count": len(pdf_sources),
            "image_b64": img_b64
        })

    response = await vision_client.chat.completions.create(
        model="google/gemini-2.0-flash-001",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": CLUSTER_VALIDATION_PROMPT.format(n=len(thumbnails))},
                *[{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{t['image_b64']}"}}
                  for t in thumbnails]
            ]
        }],
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)
```

**Como downstream usa confidence score:**

| Confidence | Stage 2 comportamento |
|------------|----------------------|
| **high** (≥0.85) | Extrai 1 primary + 2 secondary representativas (normal) |
| **medium** (0.70-0.85) | Extrai 1 primary + **4** secondary (mais cobertura) |
| **low** (<0.70) | Extrai **todas** as páginas do cluster (não confia no clustering) |

> Para multi-PDF, Stage 2 prioriza extrair representativas de **PDFs diferentes**
> para maximizar a detecção de label vs dynamic no Stage 3.

---

### CAMADA EXTRA — FEEDBACK LOOP (downstream → upstream)

#### 5.21 Downstream Inconsistency Detection

Se o Stage 4 (Field Mapping) encontra inconsistências **dentro de um cluster**, isso indica que o clustering pode ter errado:

```python
# No Stage 4, após field matching:
def detect_cluster_inconsistencies(field_mappings, clusters):
    """Detecta se páginas do mesmo cluster têm estruturas diferentes."""
    warnings = []
    for cluster in clusters:
        pages_in_cluster = [m for m in field_mappings if m["layout_type_id"] == cluster["cluster_id"]]

        # Verificar: todas as páginas têm os mesmos campos?
        fields_per_page = {}
        for m in pages_in_cluster:
            page_key = f"{m['pdf_id']}:{m['page_number']}"
            fields_per_page.setdefault(page_key, set()).add(m["xsd_field_path"])

        if len(fields_per_page) > 1:
            all_field_sets = list(fields_per_page.values())
            common = set.intersection(*all_field_sets)
            total = set.union(*all_field_sets)
            overlap_ratio = len(common) / len(total) if total else 1.0

            if overlap_ratio < 0.70:
                warnings.append({
                    "cluster_id": cluster["cluster_id"],
                    "type": "field_structure_mismatch",
                    "overlap_ratio": overlap_ratio,
                    "message": f"Pages in cluster share only {overlap_ratio:.0%} of fields — possible clustering error",
                    "suggestion": "Consider re-running Stage 1 with stricter threshold"
                })

    return warnings
```

Esses warnings são incluídos no `PipelineResult` para que o usuário saiba:

```python
context["result_json"]["cluster_warnings"] = warnings
```

---

### CORREÇÃO DE CLUSTERS — Safety Net (v3.11)

> **Princípio:** O pipeline confia em si mesmo (3 camadas + LLM + checkpoint).
> Mas se mesmo assim errar, o operador precisa **conseguir corrigir sem reprocessar tudo**.

#### Decisão arquitetural (FECHADA)

| Aspecto | Decisão |
|---------|---------|
| **O quê** | O operador pode reorganizar clusters manualmente (mover páginas, merge, split) |
| **Quando** | Após o pipeline completar, se o operador perceber erro ou Stage 4 emitir warnings |
| **Backend** | `PATCH /jobs/{id}/clusters` — re-pipeline parcial (Stages 2-5 só nos clusters afetados) |
| **Frequência esperada** | Rara — 3 camadas + LLM + checkpoint devem resolver a vasta maioria dos casos |

#### Como o operador descobre que precisa corrigir

1. **Stage 4 avisa automaticamente** — `cluster_warnings` com `overlap_ratio < 0.70` indica que páginas no mesmo cluster têm estruturas diferentes. O warning aparece visível para o operador (não só em logs).
2. **Operador percebe sozinho** — template renderizado não bate com uma das páginas do cluster.

#### Capacidades necessárias na UI

O operador precisa conseguir:
- **Ver** os clusters com thumbnails das páginas agrupadas
- **Mover** página de um cluster para outro
- **Merge** de 2 clusters (juntar)
- **Split** de 1 cluster (separar)
- **Confirmar** mudanças → trigger re-pipeline parcial

#### Backend — Re-pipeline parcial

```python
# PATCH /jobs/{id}/clusters
# Body: {"changes": [{"page": {"pdf_id": "abc-123", "page_index": 4}, "from": "B", "to": "A"}]}

async def apply_cluster_corrections(job_id: str, changes: list[dict]):
    """Aplica correções manuais de clustering e re-processa clusters afetados.

    Só re-executa Stages 2-5 para os clusters que mudaram.
    Clusters inalterados mantêm seus resultados.
    """
    affected_cluster_ids = set()
    for change in changes:
        affected_cluster_ids.add(change["from"])
        affected_cluster_ids.add(change["to"])

    # Atualizar clusters no contexto
    updated_clusters = apply_page_moves(context["clusters"], changes)
    context["clusters"] = updated_clusters

    # Re-pipeline parcial — SÓ clusters afetados
    for cluster_id in affected_cluster_ids:
        cluster = get_cluster(updated_clusters, cluster_id)
        if not cluster["pages"]:
            remove_cluster(updated_clusters, cluster_id)
            continue

        cluster["representative_page"] = select_representative(cluster)
        await stage_2_deep_extraction(cluster, context)
        await stage_3_intelligence(cluster, context)
        await stage_4_field_mapping(cluster, context)
        await stage_5_html_generation(cluster, context)

    context["result_json"]["manual_corrections"] = changes
```

#### Regras de design

1. **Re-pipeline parcial** — só clusters afetados são reprocessados, não o job inteiro
2. **Stage 4 warnings são o guia** — quando existem, direcionar o operador ao cluster com problema
3. **Rastreabilidade** — correções manuais ficam registradas em `manual_corrections`
4. **Raro por design** — com 3 camadas + LLM + checkpoint, a expectativa é que isso quase nunca seja necessário

#### Pendência UX — Onde na interface? (ABERTA)

A decisão de **onde** na interface essa funcionalidade vive está **pendente de validação com @ux-design-expert**. Três opções identificadas:

| Opção | Descrição | Prós | Contras |
|-------|-----------|------|---------|
| **A — Tela intermediária** | Tela "Revisão de Clusters" entre progresso e editor. Fluxo: Upload → Progresso → **Revisão** → Editor | Responsabilidade clara. Não polui o editor. Pode ser pulada com 1 clique quando tudo OK | Mais uma tela no fluxo. Operador pode achar burocrático |
| **B — Painel no editor** | Aba ou painel lateral dentro do editor | Operador já está ali. Sem navegação extra | Mistura responsabilidades (editor = template, não clusters) |
| **C — Na tela de progresso** | Expandir a tela de progresso para incluir revisão pós-pipeline | Reutiliza infraestrutura existente (thumbnails do checkpoint) | Semântica estranha — "progresso" implica que algo está rodando |

**Recomendação do @architect para o @ux-design-expert avaliar:**

A opção **A (tela intermediária)** parece a mais limpa. O fluxo seria:

```
Upload → Progresso → [Revisão de Clusters] → Editor
                      │
                      ├── Mostra clusters com thumbnails + warnings
                      ├── Operador pode ajustar ou [Confirmar e continuar]
                      └── Acessível depois via link no editor ("Revisar clusters")
```

**Perguntas para o @ux-design-expert:**

1. A tela intermediária deve aparecer **sempre** (para confirmar) ou **só quando há warnings**?
2. Se o operador já está no editor e descobre um problema, como volta para a revisão? Link? Modal? Painel que abre?
3. O drag-and-drop de páginas entre clusters é a melhor interação? Ou selecionar + dropdown "Mover para cluster X"?
4. Como mostrar visualmente o impacto de uma mudança antes de confirmar? (ex: preview de como ficaria)
5. A mensagem de warning do Stage 4 precisa ser acionável (link direto para a revisão) ou informativa?

---

### CHECKPOINT HUMANO — Fallback para baixa confiança

#### Quando ativa

O checkpoint humano é **opcional** e **não-bloqueante por padrão**. Só ativa quando:

1. Algum cluster com `confidence < 0.70`, **OU**
2. A auto-correction fez alterações (merge/split), **OU**
3. Homogeneity check detectou `template_mismatch`, **OU**
4. O usuário configurou `always_confirm_clusters: true` no job

```python
HUMAN_CHECKPOINT_THRESHOLD = 0.70

def should_request_human_review(clusters, corrections, mismatched_pdfs, job_config):
    """Decide se pede confirmação humana."""
    if job_config.get("always_confirm_clusters"):
        return True
    if any(c["confidence"]["level"] == "low" for c in clusters):
        return True
    if corrections and len(corrections) > 0:
        return True
    if mismatched_pdfs:
        return True
    return False
```

#### Fluxo SSE — Evento de Checkpoint

O Stage 1 emite um evento SSE especial `type: "cluster_checkpoint"`:

```python
# No Stage 1, após Camada 3:
if should_request_human_review(llm_result, corrections, job_config):
    checkpoint_data = {
        "type": "cluster_checkpoint",
        "clusters": [
            {
                "cluster_id": "A",
                "page_count": 45,
                "confidence": 0.92,
                "confidence_level": "high",
                "thumbnail_b64": render_thumbnail_b64(representative_page_A),
                "sample_pages": [1, 3, 5],  # páginas exemplo deste cluster
                "corrections_applied": [],   # correções que já foram feitas
            },
            {
                "cluster_id": "B",
                "page_count": 52,
                "confidence": 0.65,
                "confidence_level": "low",
                "thumbnail_b64": render_thumbnail_b64(representative_page_B),
                "sample_pages": [2, 4, 6],
                "corrections_applied": [
                    {"action": "split", "reason": "LLM + quality score agree on split"}
                ],
            },
            {
                "cluster_id": "C",
                "page_count": 3,
                "confidence": 0.88,
                "confidence_level": "high",
                "thumbnail_b64": render_thumbnail_b64(representative_page_C),
                "sample_pages": [9],
                "corrections_applied": [],
            }
        ],
        "auto_corrections": corrections,  # o que a Camada 3 já fez
        "llm_analysis": {
            "merge_suggestions": [["A", "C"]],
            "split_suggestions": ["B"],
            "confidence": 0.65
        },
        "timeout_seconds": 300,            # 5 min — depois continua automaticamente
        "message": "Clustering com baixa confiança. Confirme ou corrija antes de continuar."
    }

    await emit_progress({
        "stage": 1,
        "stage_name": "Layout Clustering",
        "status": "awaiting_confirmation",
        "checkpoint": checkpoint_data
    })
```

#### Backend — Endpoint de Confirmação

```python
# backend/routers/analyze.py

@router.post("/jobs/{job_id}/confirm-clusters")
async def confirm_clusters(job_id: str, body: ClusterConfirmation):
    """Recebe confirmação ou correção humana do clustering."""
    job = get_job(job_id)
    if not job or job["status"] != "awaiting_confirmation":
        raise HTTPException(404, "Job not found or not awaiting confirmation")

    if body.action == "confirm":
        # Aceita clusters como estão
        job["cluster_confirmation"] = {"action": "confirm", "by": "human"}

    elif body.action == "correct":
        # Aplica correções humanas
        job["cluster_confirmation"] = {
            "action": "correct",
            "by": "human",
            "corrections": body.corrections
            # corrections: [
            #   {"action": "merge", "clusters": ["A", "C"]},
            #   {"action": "split", "cluster": "B", "pages_to_move": [4, 6]},
            #   {"action": "rename", "cluster": "A", "new_name": "Boleto"}
            # ]
        }

    elif body.action == "skip":
        # Continua sem confirmação (mesmo que auto)
        job["cluster_confirmation"] = {"action": "skip", "by": "human"}

    # Sinaliza para o pipeline continuar
    job["confirmation_event"].set()
    return {"status": "accepted"}


# Pydantic models
class ClusterCorrection(BaseModel):
    action: Literal["merge", "split", "rename", "move_page"]
    clusters: list[str] | None = None       # para merge
    cluster: str | None = None              # para split/rename
    pages_to_move: list[int] | None = None  # para split — quais páginas separar
    target_cluster: str | None = None       # para move_page
    new_name: str | None = None             # para rename

class ClusterConfirmation(BaseModel):
    action: Literal["confirm", "correct", "skip"]
    corrections: list[ClusterCorrection] | None = None
```

#### Backend — Pipeline aguarda confirmação

```python
# No Stage 1, após emitir checkpoint:
async def wait_for_confirmation(job, timeout=300):
    """Aguarda confirmação humana com timeout."""
    confirmation_event = job["confirmation_event"]  # asyncio.Event

    try:
        await asyncio.wait_for(confirmation_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        # Timeout — continua automaticamente com os clusters da auto-correction
        return {"action": "timeout", "by": "system"}

    return job.get("cluster_confirmation", {"action": "timeout", "by": "system"})


# Uso no Stage 1:
if should_request_human_review(llm_result, corrections, job_config):
    job["confirmation_event"] = asyncio.Event()
    job["status"] = "awaiting_confirmation"

    await emit_checkpoint(checkpoint_data)

    confirmation = await wait_for_confirmation(job, timeout=300)

    if confirmation["action"] == "correct":
        clusters = apply_human_corrections(clusters, confirmation["corrections"])
        # Re-computar confidence scores após correção humana
        for cluster in clusters:
            cluster["confidence"]["level"] = "high"  # humano validou
            cluster["confidence"]["factors"]["human_validated"] = True

    job["status"] = "running"
    # Pipeline continua com Stage 2
```

#### Frontend — Tela de Confirmação

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠ Clustering com baixa confiança — Confirme antes de continuar │
│                                                                  │
│  O sistema identificou 3 tipos de página diferentes.             │
│  Correções automáticas já aplicadas: 1 split                     │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │  [thumbnail] │ │  [thumbnail] │ │  [thumbnail] │             │
│  │              │ │              │ │              │             │
│  │  Tipo A      │ │  Tipo B      │ │  Tipo C      │             │
│  │  45 páginas  │ │  52 páginas  │ │  3 páginas   │             │
│  │  ✅ Conf: 92% │ │  ⚠ Conf: 65% │ │  ✅ Conf: 88% │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                  │
│  Sugestão do LLM: "Tipo A e Tipo C parecem o mesmo documento"   │
│                                                                  │
│  Ações disponíveis:                                              │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │ [🔗 Merge A+C]  [✂️ Split B]  [📝 Renomear]            │     │
│  │ [↔️ Mover página entre tipos]                           │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                  │
│  Páginas do Tipo B (confiança baixa):                            │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐  ... +47                   │
│  │ p2 │ │ p4 │ │ p6 │ │ p8 │ │p10 │                             │
│  └────┘ └────┘ └────┘ └────┘ └────┘                             │
│  (clique para ver em tamanho maior)                              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ ✅ Confirmar  │  │ ▶ Pular      │  │ ⏱ Auto em 4:32      │   │
│  │  (como está) │  │  (continuar) │  │  (timeout 5 min)    │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### Frontend — Componente Vue

```typescript
// frontend/src/components/ClusterCheckpoint.vue — interface esperada

interface ClusterCheckpointData {
  clusters: Array<{
    cluster_id: string
    page_count: number
    confidence: number
    confidence_level: 'high' | 'medium' | 'low'
    thumbnail_b64: string
    sample_pages: number[]
    corrections_applied: Array<{action: string; reason: string}>
  }>
  auto_corrections: Array<{action: string; clusters?: string[]; cluster?: string; reason: string}>
  llm_analysis: {
    merge_suggestions: string[][]
    split_suggestions: string[]
    confidence: number
  }
  timeout_seconds: number
  message: string
}

// Ações que o usuário pode tomar:
interface ClusterCorrection {
  action: 'merge' | 'split' | 'rename' | 'move_page'
  clusters?: string[]          // merge: quais clusters juntar
  cluster?: string             // split/rename: qual cluster
  pages_to_move?: number[]     // split: quais páginas separar
  target_cluster?: string      // move_page: destino
  new_name?: string            // rename: novo nome
}

// POST /jobs/{job_id}/confirm-clusters
interface ClusterConfirmationRequest {
  action: 'confirm' | 'correct' | 'skip'
  corrections?: ClusterCorrection[]
}
```

#### Fluxo Completo — Diagrama de Sequência

```
Frontend                    Backend (Stage 1)              LLM (Gemini)
   │                              │                            │
   │   POST /analyze (PDF+XSD)    │                            │
   │──────────────────────────────>│                            │
   │                              │                            │
   │   SSE: stage 1 running       │                            │
   │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│                            │
   │                              │                            │
   │                              │── Camada 1 (prevenção) ──> │
   │                              │── Camada 2 (detecção) ──>  │
   │                              │                            │
   │                              │   thumbnails + prompt      │
   │                              │───────────────────────────>│
   │                              │   {merge: [A,C], conf: 0.6}│
   │                              │<───────────────────────────│
   │                              │                            │
   │                              │── Camada 3 (correção) ──>  │
   │                              │                            │
   │                              │── should_request_human? ──>│
   │                              │   YES (LLM conf < 0.70)    │
   │                              │                            │
   │   SSE: cluster_checkpoint    │                            │
   │   (thumbnails, suggestions)  │                            │
   │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│                            │
   │                              │                            │
   │   Mostra tela de confirmação │                            │
   │   Usuário: merge A+C         │                            │
   │                              │                            │
   │   POST /confirm-clusters     │                            │
   │   {action: "correct",        │                            │
   │    corrections: [{merge}]}   │                            │
   │──────────────────────────────>│                            │
   │                              │                            │
   │                              │── Aplica merge A+C         │
   │                              │── Confidence = "high"      │
   │                              │   (humano validou)         │
   │                              │                            │
   │   SSE: stage 1 completed     │                            │
   │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│                            │
   │                              │                            │
   │   SSE: stage 2 running       │                            │
   │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│── Stage 2 continua ──>    │
   │                              │                            │

  TIMEOUT (se usuário não responde em 5 min):

   │                              │                            │
   │                              │── asyncio.TimeoutError     │
   │                              │── Continua com clusters    │
   │                              │   da auto-correction       │
   │   SSE: stage 1 completed     │                            │
   │   (status: "auto_continued") │                            │
   │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─│                            │
```

#### Configuração do Job

O checkpoint pode ser controlado por job:

```python
# POST /analyze — body opcional
{
    "pdfs": [...],
    "xsd": "...",
    "config": {
        "cluster_confirmation": "auto",     # "auto" | "always" | "never"
        # "auto" = só pede quando LLM conf < 0.70 ou auto-correction fez mudanças
        # "always" = sempre pede confirmação
        # "never" = nunca pede, usa auto-correction ou segue sem
        "cluster_timeout": 300              # segundos até timeout (default: 300)
    }
}
```

#### Edge Cases

| Cenário | Comportamento |
|---------|---------------|
| Usuário fecha o browser durante checkpoint | Timeout → continua automaticamente |
| Múltiplos clients SSE conectados | Todos recebem o checkpoint, primeiro POST vence |
| Checkpoint + job cancelado | `cancel_flag` verificado junto com `confirmation_event` |
| PDF com 1 página | Skip checkpoint — 1 cluster com confiança 1.0 |
| PDF com 500+ páginas | Thumbnails de representantes (não 500 imagens) |
| LLM Vision indisponível | Sem LLM confidence → usa quality_score + visual_hash. Se ambos OK → não pede humano |

---

### Stage 1 — Resumo Completo

```
PDF(s) (todos do MESMO template)
  │
  ▼
POOL ÚNICO (todas as páginas juntas, pdf_id preservado)
  │
  ▼
CAMADA 1 — PREVENÇÃO (~2s para 100 páginas)
  │
  1.1  Page Extraction + Classification (text/scanned/blank)
  1.2  Block Extraction + preservar _raw_text_blocks
  1.3  Normalization (rotation + coords normalizadas)
  1.4  Content Abstraction (DATE/NUMBER/TEXT_S/TEXT_L)
  1.5  Region Filtering Adaptativo
  1.6  Tolerant Similarity Matrix (geo 0.8 + den 0.2)
  1.7  Graph Clustering (threshold 0.85)
  1.8  Consensus Check
  1.9  Representative Selection (weighted degree)
  │
  ▼
CAMADA 2 — DETECÇÃO (~3s + ~$0.003 LLM)
  │
  1.10 Cluster Quality Score
  1.11 pHash Cross-Check
  1.12 Representative Validation
  1.13 LLM Cluster Validation (Gemini Flash ~$0.003)
  │
  ▼
CAMADA 3 — CORREÇÃO (~0.5s)
  │
  1.14 Auto-correction (merge/split/isolate)
  1.15 Confidence Score (quality + pHash + consensus + LLM)
  │
  ▼
VALIDAÇÃO
  │
  1.16 Document Homogeneity Check (template_mismatch se shared_ratio < 0.20)
  │
  ▼
CHECKPOINT HUMANO (condicional)
  │
  triggers: low confidence | auto-correction | template_mismatch | always_confirm
  │
  ├── SSE: cluster_checkpoint (thumbnails, suggestions, timeout)
  ├── Frontend: mostra tela de confirmação
  ├── NOVO: "Documento incompatível detectado" com [Remover e continuar] [Manter] [Cancelar processo]
  ├── POST /jobs/{id}/confirm-clusters (confirm | correct | skip | remove_pdf)
  ├── Timeout 5 min → continua automaticamente
  └── Se humano corrige → re-aplica + confidence = "high"
  │
  ▼
clusters[] com confidence + _raw_text_blocks → Stage 2
                                                → Stage 3
                                                → Stage 4
                                                → Stage 5

FEEDBACK (Stage 4 → Editor)
  │
  └── cluster_warnings no resultado
      → Editor mostra: "⚠ Cluster B: páginas com estrutura diferente"

CORREÇÃO NO EDITOR (safety net — raro)
  │
  ├── Operador vê clusters com thumbnails (painel lateral)
  ├── Pode: arrastar página, merge clusters, split cluster
  ├── PATCH /jobs/{id}/clusters → re-pipeline parcial
  └── Só clusters afetados reprocessam (Stages 2-5)
```

**Total Stage 1:** ~5.5s + ~$0.003 para 100 páginas. 16 sub-steps + checkpoint humano condicional.

**Fluxo de defesa completo:**
```
Prevenção (9 steps) → Detecção (4 steps) → Correção automática (2 steps)
  → Homogeneity Check → Checkpoint humano (condicional)
    → Pipeline roda → Stage 4 warnings → Editor (correção manual se necessário)
```

---

### 5.21 Gaps Identificados no Design do Stage 1

| Gap | Problema | Impacto | Resolução |
|-----|----------|---------|-----------|
| **G1-S1: Páginas escaneadas (image-only)** | `get_text("blocks")` retorna vazio para páginas que são imagens escaneadas (type=1). Todas teriam fingerprint idêntica (vazia) e clusterizariam juntas, mesmo sendo layouts completamente diferentes. | Clusters incorretos — mistura layouts distintos num cluster "vazio" | ✅ **RESOLVIDO v3.9** — Detecção automática (`classify_page`) + fallback pHash para clustering visual. Ver 5.23.1 |
| **G2-S1: Rotação/orientação** | Normalização em step 1.3 divide bbox por `(page_width, page_height)` assumindo orientação consistente. Páginas landscape (rotação 90°/270°) teriam width > height, invertendo as coordenadas normalizadas. | Fingerprints incomparáveis entre landscape e portrait — páginas iguais pareceriam diferentes | ✅ **RESOLVIDO v3.9** — Normalização verifica `page.rotation` e corrige para portrait. Ver 5.23.2 |
| **G3-S1: Páginas em branco** | Sem filtragem explícita de páginas totalmente em branco antes do clustering. `get_text("blocks")` retorna lista vazia, gerando fingerprint zerada. | Poluem clusters (atrapalham quality score) ou criam cluster "fantasma" sem conteúdo | ✅ **RESOLVIDO v3.9** — Detecção via `classify_page` + cluster especial `_blank` com `is_processable: False`. Ver 5.23.3 |
| **G4-S1: PDFs curtos (2-3 páginas)** | Header/footer removal (step 1.4) usa threshold de 80%. Num PDF de 3 páginas, um header que aparece em 2/3 = 66.7% → **não removido**. Num PDF de 2 páginas, precisa 100% (ambas). | Headers/footers não detectados em PDFs pequenos → poluem fingerprints e similaridade | ✅ **RESOLVIDO v3.8** — Region filtering adaptativo substitui header removal. Não precisa de threshold de presença |
| **G5-S1: Content Abstraction limitada** | Regex de DATE: `\d{2}[/.-]\d{2}[/.-]\d{2,4}` não captura ISO `2024-03-20`, "20 de março de 2024", "March 20, 2024". Regex de NUMBER: `^R?\$?\s*[\d.,]+$` captura falsos positivos como IPs "192.168.1.1" ou versões "2.3.4". | Abstração incorreta → fingerprints divergem para páginas que são do mesmo template → over-splitting | ✅ **RESOLVIDO v3.9** — Patterns expandidos (ISO date, mês por extenso, moeda, %) + filtro de falsos positivos (IPs, versões). Impacto reduzido: v3.8 usa geometry (posição), não conteúdo abstraído. Ver 5.23.4 |
| **G6-S1: DBSCAN eps fixo** | `eps=0.02` (2% da largura normalizada) é fixo. PDFs com grids muito apertados (tabelas com 10+ colunas finas) teriam colunas a <2% de distância → DBSCAN funde colunas distintas. PDFs com poucos blocos espaçados podem não atingir `min_samples=2`. | Over-merging ou under-splitting de colunas dependendo do layout → grid detection incorreto → fingerprints erradas | ✅ **RESOLVIDO v3.9** — Grid detection **removido do Stage 1**. Em v3.8, similarity usa geometry+density (não usa grid). Grid detection movido para Stage 2 (Jenks). Ver 5.23.5 |
| **G7-S1: Conteúdo de tamanho variável** | Mesmo template com tabela de 5 linhas vs 50 linhas produz spatial bitmaps muito diferentes (5 células ocupadas vs 50), block_count diverge (s_blocks cai), text_density diverge (s_density cai). Peso combinado bitmap(0.25) + block_count(0.10) + density(0.10) = **0.45** — quase metade da similaridade é afetada. | Over-splitting — páginas do **mesmo template** com diferentes quantidades de dados caem em clusters separados. Problema real: extratos bancários com 3 transações vs 30 transações | ✅ **RESOLVIDO v3.8** — Regional weighting distingue conteúdo variável (same Y region) de diferença estrutural. Usa `min_blocks` como denominador quando sem diff estrutural. Geometry domina com 0.8 peso |
| **G8-S1: Image blocks em headers/footers** | `get_text("blocks")` retorna blocos type=0 (texto) e type=1 (imagem). Mas content abstraction (step 1.5) e header/footer removal (step 1.4) só processam texto. Logos em headers (type=1) **não são abstraídos nem removidos**. | Logo de cabeçalho aparece na fingerprint como bloco extra → duas páginas idênticas exceto pelo logo parecem diferentes. PDFs de empresas diferentes com mesmo template mas logos diferentes → over-splitting | ✅ **RESOLVIDO v3.8** — Region filtering ignora toda a região de header/footer (texto E imagens). Logos ficam fora da body region |
| **G9-S1: Tolerância posicional no header/footer** | Header/footer removal usa `round(x, 2)` em coords normalizadas como chave. Tolerância = ±0.005, que para A4 (842pt) = ±4.2pt ≈ ±1.5mm. Em PDFs reais, o mesmo header pode ter variação de 2-5pt entre páginas por diferenças de rendering/margens. | Headers com variação posicional >1.5mm **não casam** → não são removidos → poluem fingerprints | ✅ **RESOLVIDO v3.8** — Region filtering elimina o problema (não tenta casar headers). Block matching usa ±0.05 (10x mais tolerante) para body region |
| **G10-S1: Transitividade no merge cross-PDF** | Merge Decision (step 1.19) usa Union-Find: se cluster_A ≈ cluster_B e cluster_B ≈ cluster_C, automaticamente A+B+C viram 1 cluster. Mas A e C podem ser layouts diferentes que por acaso são ambos similares a B (layout intermediário). LLM (step 1.20) valida depois, mas se LLM indisponível (edge case documentado), merge transitivo fica sem verificação. | Clusters incorretamente fundidos por transitividade. Exemplo: "Boleto simples" ≈ "Boleto com tabela" ≈ "Extrato com tabela" → os três fundidos, quando Boleto simples ≠ Extrato | ✅ **RESOLVIDO v3.9** — Union-Find substituído por complete-linkage (scipy). Merge só se TODOS os pares ≥ threshold. Ver 5.23.6 |
| **G11-S1: Consensus não é independente** | Consensus check (step 1.11) roda NetworkX graph clustering e scipy hierarchical sobre a **mesma similarity matrix**. São dois algoritmos sobre os mesmos dados, não sinais verdadeiramente independentes. Se a similarity matrix está enviesada (ex: fingerprint ruim), ambos produzem resultado ruim, dando falsa sensação de consenso. Apenas pHash (step 1.14) é sinal realmente independente. | Falsa confiança quando consensus = True mas o dado de entrada está errado. O "conservador" (separar quando discordam) ajuda, mas quando concordam não significa que estão certos | ✅ **ACEITO v3.9** — Risco conhecido, mitigado por 3 sinais independentes: pHash (Camada 2), LLM Vision (Camada 2, step 1.13), checkpoint humano. Ver 5.23.7 |
| **G12-S1: Spatial bitmap usa só centro do bloco** | `spatial_bitmap()` marca apenas a célula do **centro** do bbox (`x_center, y_center`). Um bloco grande que cobre 3×2 células na grade (ex: título largo) marca apenas 1 célula. Dois layouts com blocos de tamanhos muito diferentes mas mesmos centros → bitmap idêntico → false positive. Inversamente, um bloco que cruza a fronteira entre duas células mas cujo centro está numa → a outra célula fica vazia → false negative. | Bitmap perde informação de **extensão** dos blocos. Layout com 1 título grande vs 3 labels pequenos na mesma região → bitmaps idênticos quando são estruturalmente diferentes. Peso do bitmap = 0.25 (maior peso individual) | ✅ **RESOLVIDO v3.8** — Spatial bitmap removido. Substituído por geometry_similarity que opera diretamente sobre posições dos blocos com tolerância |
| **G13-S1: Representative selection ignora força da conexão** | `select_representative()` usa `G.degree(n)` — conta apenas QUANTAS conexões, não a FORÇA (weight/similarity). Uma página com 10 conexões fracas (sim=0.86, mal acima do threshold 0.85) vence uma página com 5 conexões fortes (sim=0.99). O representativo deveria ser o membro mais "típico" (central), não o mais "conectado". | Stage 2 extrai dados completos da página representativa. Se o representativo é um outlier conectado a muitos vizinhos fracos em vez do membro mais central, a extração pode não representar fielmente o cluster. Impacto direto na qualidade dos enriched_documents | ✅ **RESOLVIDO v3.9** — Weighted degree (soma de similarities) substitui degree simples. Closeness como desempate. Ver 5.23.8 |
| **G14-S1: Thresholds hardcoded sem validação** | 9+ thresholds hardcoded no design sem análise de sensibilidade: `0.85` (graph clustering), `0.80` (header/footer), `0.75` (quality suspect), `0.78` (page avg suspect), `0.02` (DBSCAN eps), `10` (pHash distance), `0.70` (checkpoint humano), `0.85` (cross-PDF merge), `10×14` (bitmap resolução). Nenhum foi testado contra PDFs reais do domínio (Planet Express). | Um threshold incorreto afeta **todos** os documentos processados. Sem dados reais, não sabemos se 0.85 é restritivo demais (over-splitting) ou permissivo demais (under-splitting) para os PDFs específicos deste sistema | ✅ **RESOLVIDO v3.9** — `ClusteringConfig` dataclass centraliza todos os thresholds com rationale documentada. Sobrescrita por job via `from_job_config()`. v3.8/v3.9 eliminaram 3 thresholds (bitmap, header removal, DBSCAN). Ver 5.23.9 |
| **G15-S1: Garantia contratual vs filtragem de páginas** | Contrato 3.1 garante "toda página de todos os PDFs está em exatamente 1 cluster". Mas se resolvermos G3-S1 (filtrar páginas em branco) ou G1-S1 (páginas escaneadas sem texto), essas páginas filtradas **quebram a garantia**. Stages downstream (Stage 2, 3) podem assumir que `sum(cluster.page_count) == total_pages` e falhar se isso não for verdade. | Necessidade de decidir: (a) páginas filtradas vão para um cluster especial `_filtered`, (b) a garantia é relaxada, ou (c) páginas filtradas são mantidas no cluster mais próximo com flag `is_filtered: true`. Cada opção tem trade-offs para downstream | ✅ **RESOLVIDO v3.9** — Garantia preservada: todas as páginas em clusters, com `page_type` (text/scanned/blank) e `is_processable`. Stage 2 adapta comportamento por tipo. Ver 5.23.10 |
| ~~**G16-S1: REMOVIDO**~~ | Seções condicionais/opcionais **não é gap do Stage 1**. Páginas com/sem seção extra são estruturalmente diferentes — Stage 1 está correto ao separá-las. Identificar que são "variantes do mesmo template" é responsabilidade do **Stage 3.4 (Variant Detection)**, que deve operar cross-cluster. | — | N/A |
| **G17-S1: Ordem incorreta — abstraction vs header/footer** | O **orquestrador** (pseudocódigo) chama `remove_common_blocks(blocks_norm)` ANTES de `abstract_content(blocks_norm)`. Mas a função `remove_common_blocks()` usa `b["text_abstract"]` como chave de comparação. Se abstraction não rodou, `text_abstract` **não existe** nos blocos. Sem abstração: "Page 1" ≠ "Page 2" (texto diferente) → header com número de página **não é removido**. Com abstração: ambos = "TEXT_SHORT" → corretamente identificado como header. A **ordem correta** é: 1.5 (abstract) → 1.4 (remove_common), mas o documento define 1.4 antes de 1.5. | Headers/footers com conteúdo variável (números de página, datas dinâmicas) não são detectados → permanecem nos blocos → poluem fingerprint → clustering incorreto. A inconsistência entre a numeração dos steps e o pseudocódigo indica bug de design | ✅ **RESOLVIDO v3.8** — Header/footer removal substituído por region filtering. Abstraction roda primeiro no novo fluxo. Bug de ordem eliminado |
| ~~**G18-S1: REMOVIDO**~~ | Detecção de documento multi-página **não é responsabilidade do Stage 1**. A pergunta é "quais páginas são iguais?" — sequência de documento é problema do Stage 3 (hierarchy builder). Stage 3 pode inferir de `pages[].pdf_id + page_index`. | — | N/A |

---

### 5.22 Refinamento: Tolerant Clustering (v3.8)

> **Regra de ouro:** "Layouts don't need to be identical, only similar enough."

Baseado no spec de tolerância, o Stage 1 adota uma abordagem tolerante para lidar com variações reais de PDFs (headers ausentes, tabelas parciais, shifts de posição). A seguir, os 6 refinamentos aplicados sobre o design original.

---

#### 5.22.1 Region Filtering Adaptativo (substitui Header/Footer Removal)

**Problema com o design original (step 1.4):** Header/footer removal tentava detectar e remover blocos comuns, com threshold fixo de 80%, bugs de ordem com abstraction (G17), e problemas com PDFs curtos (G4) e image blocks (G8).

**Nova abordagem:** Em vez de detectar e remover, **ignorar regiões instáveis** para clustering. Mas com limites **adaptativos** por PDF, não fixos.

```python
def detect_body_region(pages_blocks_norm, min_header=0.08, max_header=0.30,
                        min_footer=0.75, max_footer=0.95, presence_threshold=0.70):
    """Detecta onde header termina e footer começa, adaptativo por PDF.

    Estratégia: blocos que aparecem na mesma posição Y em >70% das páginas
    nas regiões de topo/fundo são header/footer. O último Y "estável" no topo
    define header_end; o primeiro Y "estável" no fundo define footer_start.

    Fallback: 0.12 / 0.88 se nenhum padrão detectado.
    """
    n_pages = len(pages_blocks_norm)
    if n_pages == 0:
        return 0.12, 0.88

    # Coletar Y centers de todos os blocos, por página
    y_frequency = {}  # y_rounded → count de páginas onde aparece
    for page_blocks in pages_blocks_norm:
        seen_y = set()
        for b in page_blocks:
            y_center = round((b["bbox_norm"][1] + b["bbox_norm"][3]) / 2, 2)
            if y_center not in seen_y:
                y_frequency[y_center] = y_frequency.get(y_center, 0) + 1
                seen_y.add(y_center)

    # Y positions que aparecem em >70% das páginas = estáveis
    stable_ys = {y for y, count in y_frequency.items()
                 if count / n_pages >= presence_threshold}

    # Header: último Y estável no topo (limitado a max_header)
    header_candidates = sorted(y for y in stable_ys if y <= max_header)
    header_end = header_candidates[-1] + 0.02 if header_candidates else min_header

    # Footer: primeiro Y estável no fundo (limitado a min_footer)
    footer_candidates = sorted(y for y in stable_ys if y >= min_footer)
    footer_start = footer_candidates[0] - 0.02 if footer_candidates else max_footer

    # Clamp: header não pode ser maior que 30%, footer não pode começar antes de 75%
    header_end = max(min_header, min(header_end, max_header))
    footer_start = max(min_footer, min(footer_start, max_footer))

    return header_end, footer_start


def filter_to_body(blocks_norm, header_end, footer_start):
    """Retorna apenas blocos na body region — para clustering."""
    return [
        b for b in blocks_norm
        if header_end <= (b["bbox_norm"][1] + b["bbox_norm"][3]) / 2 <= footer_start
    ]
```

**Vantagens sobre o design original:**

| Aspecto | Header/Footer Removal (original) | Region Filtering Adaptativo |
|---------|----------------------------------|----------------------------|
| PDFs curtos (2-3 pgs) | Falha (threshold 80%) | Funciona (adapta ao PDF) |
| Image blocks (logos) | Não detecta (type=1) | Ignora automaticamente (região) |
| Tolerância posicional | ±1.5mm (`round(x,2)`) | N/A — não tenta casar, ignora |
| Ordem com abstraction | Bug (G17) | Independente — filtra por Y, não por conteúdo |
| Headers dinâmicos (nº página) | Precisa abstraction antes | N/A — ignora a região inteira |

**Regra importante:** Os blocos filtrados **não são removidos permanentemente**. Stage 1 mantém dois conjuntos:

```python
context["_core_blocks"] = {           # body region → usado para clustering
    "{pdf_id}:{page_index}": [...]
}
context["_all_blocks"] = {            # tudo → preservado para Stage 2
    "{pdf_id}:{page_index}": [...]
}
```

---

#### 5.22.2 Geometry Similarity com Block Matching Tolerante

**Problema com o design original (step 5.8):** 6 fatores com pesos que penalizam conteúdo variável (bitmap 0.25 + block_count 0.10 + density 0.10 = **0.45** sensível a volume de dados).

**Nova abordagem:** Geometry-dominant similarity com matching de blocos tolerante.

```python
def geometry_similarity(core_a, core_b, tolerance=0.05):
    """Match blocos entre duas páginas com tolerância posicional.

    Greedy nearest-neighbor: para cada bloco de A, encontrar o bloco
    mais próximo em B dentro da tolerância. O(n × m) — aceitável
    porque opera sobre core_blocks (~10-30 blocos por página).

    Args:
        core_a, core_b: blocos da body region (já filtrados)
        tolerance: máx diferença em coords normalizadas (5% da página)

    Returns:
        score: float 0.0-1.0 (matched_blocks / max_blocks)
    """
    if not core_a and not core_b:
        return 1.0
    if not core_a or not core_b:
        return 0.0

    max_blocks = max(len(core_a), len(core_b))
    matched = 0
    unmatched_a = []
    used_b = set()

    # Ordenar A por posição (top-to-bottom, left-to-right) para matching estável
    sorted_a = sorted(core_a, key=lambda b: (b["y_center"], b["x_center"]))

    for a in sorted_a:
        best_dist = float('inf')
        best_j = -1
        for j, b in enumerate(core_b):
            if j in used_b:
                continue
            dx = abs(a["x_center"] - b["x_center"])
            dy = abs(a["y_center"] - b["y_center"])
            if dx <= tolerance and dy <= tolerance:
                dist = dx + dy  # Manhattan distance
                if dist < best_dist:
                    best_dist = dist
                    best_j = j
        if best_j >= 0:
            matched += 1
            used_b.add(best_j)
        else:
            unmatched_a.append(a)

    return matched / max_blocks
```

**Porquê ±0.05 (5%)?** Para uma página A4 (595 × 842 pts), 5% = ~30pt horizontal, ~42pt vertical. Suficiente para absorver variações de rendering/margem, mas não tanto que confunda layouts diferentes.

---

#### 5.22.3 Regional Weighting — Distinguir Conteúdo Variável de Estrutura Diferente

**Problema:** Partial matching (`matched / max_blocks`) trata todos os blocos não-pareados igualmente. Mas há uma diferença importante:

- **Blocos faltando na mesma Y region** → provavelmente conteúdo variável (tabela com mais/menos linhas) → OK, mesmo template
- **Blocos faltando em Y region diferente** → provavelmente estrutura diferente (seção que existe em um layout mas não no outro) → NÃO OK, template diferente

```python
def weighted_geometry_similarity(core_a, core_b, tolerance=0.05, region_tolerance=0.10):
    """Geometry similarity com penalização estrutural.

    Blocos não-pareados em regiões SEM correspondência no outro lado
    indicam diferença estrutural → penalização extra.
    Blocos não-pareados em regiões COM correspondência → conteúdo variável → ok.
    """
    if not core_a and not core_b:
        return 1.0
    if not core_a or not core_b:
        return 0.0

    max_blocks = max(len(core_a), len(core_b))

    # Fase 1: Greedy nearest-neighbor matching (mesmo que geometry_similarity)
    matched = 0
    used_b = set()
    unmatched_a = []

    for a in sorted(core_a, key=lambda b: (b["y_center"], b["x_center"])):
        best_dist = float('inf')
        best_j = -1
        for j, b in enumerate(core_b):
            if j in used_b:
                continue
            dx = abs(a["x_center"] - b["x_center"])
            dy = abs(a["y_center"] - b["y_center"])
            if dx <= tolerance and dy <= tolerance:
                dist = dx + dy
                if dist < best_dist:
                    best_dist = dist
                    best_j = j
        if best_j >= 0:
            matched += 1
            used_b.add(best_j)
        else:
            unmatched_a.append(a)

    unmatched_b = [b for j, b in enumerate(core_b) if j not in used_b]

    # Fase 2: Classificar unmatched como "content variation" vs "structural diff"
    structural_diffs = 0
    for ua in unmatched_a:
        # Existe algum bloco não-pareado em B na mesma faixa Y?
        has_nearby = any(
            abs(ua["y_center"] - ub["y_center"]) < region_tolerance
            for ub in unmatched_b
        )
        if not has_nearby:
            # Bloco em A sem nada na mesma região em B → diferença estrutural
            structural_diffs += 1

    for ub in unmatched_b:
        has_nearby = any(
            abs(ub["y_center"] - ua["y_center"]) < region_tolerance
            for ua in unmatched_a
        )
        if not has_nearby:
            structural_diffs += 1

    # Score: base de matching - penalização por diferenças estruturais
    base_score = matched / max_blocks
    structural_penalty = (structural_diffs / max_blocks) * 0.3  # penaliza 30% por diff estrutural

    return max(0.0, base_score - structural_penalty)
```

**Exemplo prático:**

```
Página A: Extrato com 5 transações        Página B: Extrato com 30 transações
┌──────────────────┐                       ┌──────────────────┐
│ [header ignorado] │                       │ [header ignorado] │
├──────────────────┤ ← header_end          ├──────────────────┤
│ Nome: ___        │ ✓ match               │ Nome: ___        │ ✓ match
│ Conta: ___       │ ✓ match               │ Conta: ___       │ ✓ match
│ ┌──────────────┐ │ ✓ match (header tab)  │ ┌──────────────┐ │ ✓ match
│ │ Data │ Valor │ │                       │ │ Data │ Valor │ │
│ │──────│───────│ │                       │ │──────│───────│ │
│ │ row1 │  100  │ │ ✓ match               │ │ row1 │  100  │ │ ✓ match
│ │ row2 │  200  │ │ ✓ match               │ │ row2 │  200  │ │ ✓ match
│ │ row3 │  300  │ │ unmatched_a           │ │ ...  │  ...  │ │ 25 unmatched_b
│ │ row4 │  400  │ │ (has_nearby=True →    │ │ row28│ 2800  │ │ (has_nearby=True →
│ │ row5 │  500  │ │  content variation)   │ │ row29│ 2900  │ │  content variation)
│ └──────────────┘ │                       │ │ row30│ 3000  │ │
│                  │                       │ └──────────────┘ │
│ Total: ___       │ ✓ match               │ Total: ___       │ ✓ match
├──────────────────┤ ← footer_start        ├──────────────────┤
│ [footer ignorado] │                       │ [footer ignorado] │
└──────────────────┘                       └──────────────────┘

matched = 7, max_blocks = 35, unmatched in same Y region → structural_diffs = 0
base_score = 7/35 = 0.20 ← PROBLEMA: ratio muito baixo por causa do volume
```

**Problema identificado:** Mesmo com regional weighting, o ratio `matched / max_blocks` é muito penalizado por conteúdo variável quando a diferença de volume é grande (5 vs 30 linhas).

**Solução: Usar `matched / min_blocks` como alternativa quando os blocos não-pareados são "content variation":**

```python
    # Se não há diferenças estruturais, usar min_blocks como denominador
    # (penaliza menos a variação de volume)
    if structural_diffs == 0:
        denominator = min(len(core_a), len(core_b))
        if denominator == 0:
            return 1.0
        return matched / denominator
    else:
        # Com diferenças estruturais, usar max_blocks (penaliza mais)
        return max(0.0, (matched / max_blocks) - structural_penalty)
```

**Com esta correção:**
```
matched = 7, min_blocks = 10 (page A), structural_diffs = 0
score = 7/10 = 0.70 → com geometry weight 0.80 → contribuição = 0.56
```

---

#### 5.22.4 Density na Body Region

**Problema:** Calcular density na página inteira inclui header/footer e é sensível a volume de dados (G7).

**Correção:** Density calculada **apenas na body region**, normalizando pela área da body region.

```python
def body_density_similarity(core_a, core_b, body_height):
    """Densidade de texto apenas na body region.

    Args:
        core_a, core_b: blocos filtrados (body region only)
        body_height: footer_start - header_end (fração normalizada)
    """
    def compute_density(blocks):
        if not blocks or body_height <= 0:
            return 0.0
        total_area = sum(
            (b["bbox_norm"][2] - b["bbox_norm"][0]) *
            (b["bbox_norm"][3] - b["bbox_norm"][1])
            for b in blocks
        )
        # Normalizar pela área da body region (width=1.0 normalizada)
        return total_area / body_height

    d_a = compute_density(core_a)
    d_b = compute_density(core_b)

    if max(d_a, d_b) == 0:
        return 1.0
    return 1.0 - abs(d_a - d_b) / max(d_a, d_b)
```

---

#### 5.22.5 Similarity Final Tolerante

```python
def compute_tolerant_similarity(page_a, page_b, header_end, footer_start):
    """Similarity tolerante — geometry dominante (0.8) + density body (0.2).

    Substitui a similarity de 6 fatores do design original.
    """
    core_a = filter_to_body(page_a["blocks_norm"], header_end, footer_start)
    core_b = filter_to_body(page_b["blocks_norm"], header_end, footer_start)

    geo = weighted_geometry_similarity(core_a, core_b, tolerance=0.05)
    den = body_density_similarity(core_a, core_b, body_height=footer_start - header_end)

    return 0.8 * geo + 0.2 * den
```

**Comparação com o design original:**

| Aspecto | Original (6 fatores) | Tolerante (2 fatores) |
|---------|---------------------|----------------------|
| Pesos sensíveis a volume | 0.45 (bitmap+blocks+density) | 0.20 (density body-only) |
| Region filtering | Não (usa header removal) | Sim (adaptativo) |
| Position tolerance | ±0.005 | ±0.05 (10x mais) |
| Partial matching | Não (compara métricas agregadas) | Sim (block-level matching) |
| Diferença estrutural vs volume | Não distingue | Sim (regional weighting) |
| Complexidade | O(1) por par (métricas pré-computadas) | O(n×m) por par (~10-30 blocos = <1ms) |
| Spatial bitmap | Sim (140 bits, peso 0.25) | Não necessário (geometry direto) |

---

#### 5.22.6 pHash como Cross-Check Independente (mantido)

O tolerance spec não menciona pHash, mas **mantemos** como sinal independente na Camada 2 (detecção). É o único sinal que não depende de `get_text("blocks")`.

```python
# Camada 2 — pHash cross-check (inalterado do design original)
# Se geometry_similarity diz "mesmo cluster" mas pHash diz "visualmente diferentes" → ALERTA
```

**Justificativa:** Se `get_text("blocks")` falha parcialmente (encoding, blocos fantasma), a geometry similarity pode dar resultado incorreto. pHash opera sobre pixels renderizados — completamente independente da extração de texto.

---

#### 5.22.7 Orquestrador Atualizado

```python
# Antes (v3.7):
pages = extract_pages(pdf_path, pdf_id)
blocks = extract_blocks(pages)                    # get_text("blocks")
blocks_norm = normalize_blocks(blocks, pages)
common = remove_common_blocks(blocks_norm)        # ← REMOVIDO
blocks_abstract = abstract_content(blocks_norm)   # ← REORDENADO
grids = detect_grid(blocks_abstract)
bitmaps = compute_spatial_bitmaps(blocks_abstract) # ← REMOVIDO
fps = compute_fingerprints(blocks_abstract, grids, bitmaps)
sim_matrix = compute_similarity_matrix(fps)

# Depois (v3.8 — tolerant clustering):
pages = extract_pages(pdf_path, pdf_id)
blocks = extract_blocks(pages)                    # get_text("blocks")
blocks_norm = normalize_blocks(blocks, pages)
blocks_abstract = abstract_content(blocks_norm)   # abstraction primeiro
header_end, footer_start = detect_body_region(blocks_abstract)  # adaptativo
core_blocks = filter_to_body(blocks_abstract, header_end, footer_start)
grids = detect_grid(core_blocks)                  # grid SÓ na body region
sim_matrix = compute_tolerant_similarity_matrix(core_blocks, header_end, footer_start)
clusters, disagreements = consensus_clustering(sim_matrix)
representatives = select_representatives(clusters, sim_matrix)

# Preservar ambos para downstream
context["_core_blocks"][pdf_id] = core_blocks     # body → clustering
context["_all_blocks"][pdf_id] = blocks_abstract  # tudo → Stage 2
context["_body_region"][pdf_id] = (header_end, footer_start)
```

**Mudanças no fluxo:**

| Step | v3.7 | v3.8 | Impacto |
|------|------|------|---------|
| 1.4 | Header/Footer Removal (threshold 80%) | **Region Filtering Adaptativo** | Resolve G4, G8, G9, G17 |
| 1.5 | Content Abstraction (depois de 1.4) | Content Abstraction (**antes** de region filter) | Fix ordem |
| 1.6 | Grid Detection (todos os blocos) | Grid Detection (**só core_blocks**) | Grid mais limpo |
| 1.7 | Spatial Bitmap (10×14) | **Removido** — geometry_similarity substitui | Resolve G12 |
| 1.8 | Fingerprint 6-dimensional | **Simplificado** — geometry + density | Mais robusto |
| 1.9 | Similarity Matrix (6 fatores ponderados) | **Tolerant Similarity** (0.8 geo + 0.2 den) | Resolve G7 |

---

#### 5.22.8 Impacto nos Gaps

| Gap | Status v3.8 | Como resolvido |
|-----|-------------|----------------|
| **G4** PDFs curtos | ✅ **RESOLVIDO** | Region filtering adaptativo — não precisa de threshold 80% |
| **G7** Conteúdo variável | ✅ **RESOLVIDO** | Regional weighting + min_blocks denominator quando sem diff estrutural |
| **G8** Image blocks headers | ✅ **RESOLVIDO** | Region filtering ignora header/footer inteiro (texto E imagens) |
| **G9** Tolerância posicional | ✅ **RESOLVIDO** | ±0.05 (5%) em vez de ±0.005 (0.5%) |
| **G12** Bitmap centro-only | ✅ **RESOLVIDO** | Spatial bitmap removido — geometry_similarity opera direto nos blocos |
| **G17** Ordem abstract/header | ✅ **RESOLVIDO** | Abstraction roda antes; region filter não depende de text_abstract |
| **G1** Escaneadas | ✅ **RESOLVIDO v3.9** | Detecção automática + fallback pHash. Ver 5.23.1 |
| **G2** Rotação | ✅ **RESOLVIDO v3.9** | Normalização corrige orientação via `page.rotation`. Ver 5.23.2 |
| **G3** Branco | ✅ **RESOLVIDO v3.9** | Detecção + cluster especial `_blank`. Ver 5.23.3 |
| **G5** Regex | ✅ **RESOLVIDO v3.9** | Patterns expandidos + fallback catch-all. Ver 5.23.4 |
| **G6** DBSCAN eps | ✅ **RESOLVIDO v3.9** | Grid detection removido do Stage 1 (movido para Stage 2). Ver 5.23.5 |
| **G10** Transitividade | ✅ **OBSOLETO v3.11** | Pool único elimina merge cross-PDF. Complete-linkage (5.23.6) não mais necessário |
| **G11** Consensus | ✅ **ACEITO v3.9** | Risco conhecido e mitigado — 3 sinais independentes no total. Ver 5.23.7 |
| **G13** Representative | ✅ **RESOLVIDO v3.9** | Weighted degree substitui degree simples. Ver 5.23.8 |
| **G14** Thresholds | ✅ **RESOLVIDO v3.9** | Config centralizada + rationale documentada. Ver 5.23.9 |
| **G15** Contrato | ✅ **RESOLVIDO v3.9** | `page_type` no contrato + garantia preservada. Ver 5.23.10 |

**Resultado: todos os 15 gaps resolvidos (v3.8 + v3.9). 1 aceito como risco conhecido (G11).**

---

### 5.23 Resolução dos Gaps Pendentes (v3.9)

---

#### 5.23.1 G1 — Páginas Escaneadas (image-only)

**Problema:** `get_text("blocks")` retorna vazio para páginas escaneadas. Todas clusterizam juntas.

**Resolução:** Detectar páginas escaneadas no step 1.1 e usar **pHash** como fallback para clustering.

```python
def classify_page(page, blocks):
    """Classifica página como text, scanned ou blank."""
    has_text = len([b for b in blocks if b["type"] == 0]) > 0
    has_images = len([b for b in blocks if b["type"] == 1]) > 0

    if has_text:
        return "text"
    elif has_images:
        return "scanned"
    else:
        return "blank"


def cluster_scanned_pages(scanned_pages, pdf_doc):
    """Clusteriza páginas escaneadas usando pHash (visual similarity).

    Sem texto para geometry_similarity, o sinal visual é o único disponível.
    """
    if len(scanned_pages) <= 1:
        return [{"pages": scanned_pages}]

    # Computar pHash para cada página escaneada
    hashes = {}
    for page_info in scanned_pages:
        page = pdf_doc[page_info["page_index"]]
        scale = 128 / max(page.rect.width, page.rect.height)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        hashes[page_info["page_index"]] = imagehash.phash(img)

    # Similarity matrix baseada em Hamming distance
    pages_list = list(scanned_pages)
    n = len(pages_list)
    sim_matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i, n):
            h_i = hashes[pages_list[i]["page_index"]]
            h_j = hashes[pages_list[j]["page_index"]]
            sim = 1.0 - (h_i - h_j) / 64.0  # Hamming → similarity
            sim_matrix[i][j] = sim_matrix[j][i] = sim

    # Usar mesmo graph clustering com threshold 0.85
    return graph_cluster(sim_matrix, threshold=0.85)
```

**Fluxo atualizado:**
```
1.1 Page Extraction + Classification
    ├── text pages    → geometry_similarity pipeline (normal)
    ├── scanned pages → pHash clustering (fallback)
    └── blank pages   → cluster "_blank" (G3)
```

---

#### 5.23.2 G2 — Rotação/Orientação

**Problema:** Normalização assume orientação consistente.

**Resolução:** Verificar `page.rotation` e normalizar para portrait antes de dividir por dimensões.

```python
def normalize_blocks(blocks, page):
    """Normaliza bbox para [0,1] × [0,1], corrigindo rotação."""
    rotation = page.rotation  # 0, 90, 180, 270

    # page.rect já considera rotação na maioria dos casos,
    # mas width/height podem estar trocados
    w = page.rect.width
    h = page.rect.height

    # Se landscape (width > height), tratar como rotação
    if rotation in (90, 270) or (rotation == 0 and w > h * 1.2):
        # Swap para normalizar como portrait
        w, h = h, w
        for b in blocks:
            x0, y0, x1, y1 = b["bbox"]
            if rotation == 90:
                b["bbox"] = (y0, w - x1, y1, w - x0)
            elif rotation == 270:
                b["bbox"] = (h - y1, x0, h - y0, x1)
            else:
                # Landscape sem rotation flag — swap coordenadas
                b["bbox"] = (y0, x0, y1, x1)

    for b in blocks:
        x0, y0, x1, y1 = b["bbox"]
        b["bbox_norm"] = [x0 / w, y0 / h, x1 / w, y1 / h]
        b["x_center"] = (x0 / w + x1 / w) / 2
        b["y_center"] = (y0 / h + y1 / h) / 2

    return blocks
```

---

#### 5.23.3 G3 — Páginas em Branco

**Problema:** Fingerprint zerada, cluster fantasma.

**Resolução:** Detectar em step 1.1 (via `classify_page`), atribuir a cluster especial `_blank`.

```python
# No orquestrador, após classify_page:
blank_pages = [p for p in pages if p["page_type"] == "blank"]
text_pages = [p for p in pages if p["page_type"] == "text"]
scanned_pages = [p for p in pages if p["page_type"] == "scanned"]

# Blank pages → cluster especial (não entram na similarity matrix)
if blank_pages:
    clusters.append({
        "cluster_id": "_blank",
        "pages": blank_pages,
        "page_count": len(blank_pages),
        "representative_page": blank_pages[0],
        "confidence": {"confidence": 1.0, "level": "high",
                       "factors": {"reason": "all_blank"}},
        "is_processable": False  # Stage 2 ignora
    })
```

**Ligação com G15:** Páginas em branco continuam no contrato (garantia preservada) mas com `is_processable: False`.

---

#### 5.23.4 G5 — Content Abstraction Expandida

**Problema:** Regex limitada para DATE e NUMBER.

**Resolução:** Expandir patterns e adicionar catch-all para dados variáveis.

```python
import re

# Patterns ordenados: mais específicos primeiro
_DATE_PATTERNS = [
    r'\d{4}-\d{2}-\d{2}',                              # ISO: 2024-03-20
    r'\d{2}[/.-]\d{2}[/.-]\d{2,4}',                    # BR/EU: 20/03/2024
    r'\d{1,2}\s+de\s+\w+(\s+de\s+\d{4})?',             # PT: 20 de março de 2024
]

_NUMBER_PATTERNS = [
    r'^[R$€£USD\s]*[\d.,]+[%]?$',                       # Moeda/percentual
]

# Filtro de falsos positivos: IPs, versões
_FALSE_POSITIVE = re.compile(r'^\d{1,3}(\.\d{1,3}){2,}$')  # 1.2.3 ou 192.168.1.1

def abstract_content(text: str) -> str:
    text = text.strip()
    if not text:
        return "EMPTY"

    # Datas
    for pattern in _DATE_PATTERNS:
        if re.match(pattern, text, re.IGNORECASE):
            return "DATE"

    # Falsos positivos antes de NUMBER
    if _FALSE_POSITIVE.match(text):
        return "TEXT_SHORT"  # IPs, versões → tratar como texto

    # Números/moeda
    for pattern in _NUMBER_PATTERNS:
        if re.match(pattern, text):
            return "NUMBER"

    # Texto por tamanho
    if len(text) <= 30:
        return "TEXT_SHORT"
    return "TEXT_LONG"
```

**Impacto no tolerant clustering:** Com v3.8, a abstração é usada para region filtering adaptativo (detectar blocos estáveis), mas a **similarity function** opera sobre posições geométricas, não sobre conteúdo abstraído. Isso reduz o impacto de falhas na abstração — mesmo que um bloco seja mal abstraído, a posição geométrica está correta.

---

#### 5.23.5 G6 — DBSCAN eps fixo → Grid Detection Removido do Stage 1

**Problema:** DBSCAN com eps=0.02 fixo pode fundir ou separar colunas.

**Resolução:** Em v3.8, a similarity function usa `geometry_similarity + density`, **não usa grid detection**. Grid detection era parte do fingerprint de 6 fatores (original), que foi substituído. Portanto:

- **Grid detection é removido do Stage 1** — não é mais input da similarity
- **Grid detection permanece no Stage 2** (step 2.6) com Jenks Natural Breaks (já projetado em v3.5)
- DBSCAN e o problema do eps fixo **deixam de existir** no Stage 1

**Orquestrador v3.9 (atualizado):**
```python
# v3.8:
grids = detect_grid(core_blocks)  # ← REMOVIDO em v3.9

# v3.9:
# Grid detection NÃO roda no Stage 1
# Stage 2 faz grid detection com Jenks nas páginas representativas
```

---

#### 5.23.6 G10 — Transitividade → Complete-Linkage (OBSOLETO v3.11)

> **v3.11:** Com pool único, não há mais merge cross-PDF. Esta seção é mantida como registro
> histórico da resolução original. O código abaixo não é mais utilizado no pipeline.

**Problema:** Union-Find cria merges transitivos (A≈B, B≈C → A+C merged mesmo se A≠C).

**Resolução (histórica):** Substituir Union-Find por **complete-linkage** — só merge se TODOS os pares no grupo merged atendem o threshold.

```python
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

def merge_cross_pdf_clusters_safe(clusters_by_pdf, fingerprints, threshold=0.85):
    """Merge cross-PDF com complete-linkage (sem transitividade).

    Complete-linkage: dois clusters só são merged se a MENOR similarity
    entre qualquer par de membros >= threshold.
    Isso impede: A≈B, B≈C, A≉C → não merge.
    """
    # Coletar representativos de cada cluster
    all_reps = []
    for pdf_id, clusters in clusters_by_pdf.items():
        for cluster in clusters:
            rep_key = f"{pdf_id}:{cluster['representative_page']['page_index']}"
            all_reps.append({
                "pdf_id": pdf_id,
                "cluster": cluster,
                "rep_key": rep_key,
                "fingerprint": fingerprints[rep_key]
            })

    if len(all_reps) <= 1:
        return [r["cluster"] for r in all_reps]

    # Similarity matrix entre representativos de PDFs DIFERENTES
    n = len(all_reps)
    sim_matrix = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if all_reps[i]["pdf_id"] == all_reps[j]["pdf_id"]:
                sim_matrix[i][j] = sim_matrix[j][i] = 0.0  # mesmo PDF → não merge
            else:
                sim = compute_tolerant_similarity(
                    all_reps[i]["fingerprint"],
                    all_reps[j]["fingerprint"],
                    header_end=0.12, footer_start=0.88  # fallback
                )
                sim_matrix[i][j] = sim_matrix[j][i] = sim

    # Complete-linkage: converte similarity → distance
    dist_matrix = [[1.0 - s for s in row] for row in sim_matrix]
    condensed = squareform(dist_matrix)
    Z = linkage(condensed, method='complete')  # complete = min similarity
    labels = fcluster(Z, t=1.0 - threshold, criterion='distance')

    # Agrupar por label
    groups = {}
    for idx, label in enumerate(labels):
        groups.setdefault(label, []).append(all_reps[idx]["cluster"])

    # Montar clusters finais
    # NOTA: source_clusters foi REMOVIDO do contrato 3.1 na v3.11 (pool único).
    # Este código é histórico — ver nota OBSOLETO acima.
    final_clusters = []
    for group_id, group in enumerate(groups.values()):
        all_pages = []
        for cluster in group:
            all_pages.extend(cluster["pages"])
        final_clusters.append({
            "cluster_id": chr(65 + group_id),
            "pages": all_pages,
            "page_count": len(all_pages),
        })

    return final_clusters
```

**Comparação:**

| Aspecto | Union-Find (v3.7) | Complete-Linkage (v3.9) |
|---------|-------------------|------------------------|
| Transitividade | A≈B, B≈C → A+C merged ❌ | A+C merged SÓ se A≈C ✅ |
| Complexidade | O(n) | O(n² log n) — aceitável (n = clusters, não páginas) |
| Biblioteca | Implementação manual | scipy (robusto, testado) |

---

#### 5.23.7 G11 — Consensus Não Independente (ACEITO)

**Problema:** Graph e hierarchical clustering usam a mesma similarity matrix.

**Decisão: ACEITO como risco conhecido**, com 3 mitigações:

1. **pHash (Camada 2)** — Sinal completamente independente (pixels, não text blocks)
2. **LLM Vision (Camada 2, step 1.13)** — Sinal completamente independente (análise visual por IA)
3. **O próprio consensus é útil** — mesmo sobre os mesmos dados, graph (connected_components) e hierarchical (average-linkage) tratam empates e fronteiras de forma diferente. O consensus pega os **casos fáceis** onde ambos concordam; os ambíguos ficam separados (conservador).

**Risco residual:** Se a similarity matrix está **sistematicamente enviesada** (ex: abstraction quebrada), ambos concordam no resultado errado. Mitigação: pHash detecta, Camada 2 flagga.

---

#### 5.23.8 G13 — Representative Selection com Weighted Degree

**Problema:** `G.degree(n)` conta conexões, ignora força.

**Resolução:** Usar **weighted degree** (soma dos pesos/similarity das conexões).

```python
def select_representative(G, cluster):
    """Seleciona o membro mais 'típico' — maior soma de similarities.

    Weighted degree = soma dos edge weights para vizinhos dentro do cluster.
    Página com 5 conexões a sim=0.99 (weighted=4.95) vence
    página com 10 conexões a sim=0.86 (weighted=8.60)... mas isso é
    correto — 10 conexões forte tem weighted degree maior.

    Para desempate: closeness (média das similarities).
    """
    if len(cluster) == 1:
        return list(cluster)[0]

    scores = {}
    for node in cluster:
        neighbors_in_cluster = [n for n in G.neighbors(node) if n in cluster]
        if not neighbors_in_cluster:
            scores[node] = 0.0
            continue

        weighted_degree = sum(G[node][n]['weight'] for n in neighbors_in_cluster)
        closeness = weighted_degree / len(neighbors_in_cluster)  # média

        # Score final: weighted_degree como primário, closeness como desempate
        scores[node] = (weighted_degree, closeness)

    return max(scores, key=scores.get)
```

---

#### 5.23.9 G14 — Thresholds Centralizados e Documentados

**Problema:** 9+ thresholds hardcoded sem validação.

**Resolução:** Centralizar em dataclass configurável com rationale documentada.

```python
from dataclasses import dataclass

@dataclass
class ClusteringConfig:
    """Configuração centralizada dos thresholds do Stage 1.

    Cada threshold tem valor default, rationale, e pode ser
    sobrescrito por job_config.
    """
    # --- Similarity & Clustering ---
    clustering_threshold: float = 0.85
    # Rationale: 85% = "claramente similar". Testado em benchmarks de
    # document layout similarity (Yang et al. 2017). Abaixo de 0.80,
    # falsos positivos sobem significativamente.

    position_tolerance: float = 0.05
    # Rationale: 5% da dimensão normalizada. Para A4 (595×842pt),
    # equivale a ~30pt horizontal, ~42pt vertical. Absorve variações
    # de rendering/margens sem confundir layouts diferentes.

    # --- Region Filtering ---
    region_presence_threshold: float = 0.70
    # Rationale: bloco em >70% das páginas = provavelmente header/footer.
    # Mais permissivo que os 80% originais (funciona com 3+ páginas).

    region_header_max: float = 0.30
    # Rationale: header não pode ocupar mais de 30% da página.

    region_footer_min: float = 0.75
    # Rationale: footer começa no mínimo a 75% da página.

    # --- Detection (Camada 2) ---
    phash_max_distance: int = 10
    # Rationale: pHash tem 64 bits. Distance 10 = ~84% similarity.
    # Empírico: layouts "claramente iguais" têm distance <5,
    # "claramente diferentes" têm distance >20. 10 é conservador.

    quality_outlier_threshold: float = 0.75
    # Rationale: min_similarity dentro de um cluster abaixo de 0.75
    # indica membro outlier que destoa significativamente.

    # --- Homogeneity Check (v3.11) ---
    homogeneity_mismatch_threshold: float = 0.20
    # Rationale: se menos de 20% das páginas de um PDF caem em clusters
    # compartilhados com outros PDFs, é documento de template diferente.

    # --- Human Checkpoint ---
    checkpoint_confidence_threshold: float = 0.70
    # Rationale: abaixo de 70%, o resultado não é confiável o suficiente
    # para prosseguir sem validação humana.

    checkpoint_timeout_seconds: int = 300
    # Rationale: 5 minutos — suficiente para revisar, não bloqueia o pipeline.

    # --- Regional Weighting ---
    structural_region_tolerance: float = 0.10
    # Rationale: blocos não-pareados na mesma faixa Y de ±10% são
    # "conteúdo variável" (ok). Fora disso = diferença estrutural.

    @classmethod
    def from_job_config(cls, job_config: dict) -> "ClusteringConfig":
        """Permite sobrescrever qualquer threshold via job config."""
        config = cls()
        overrides = job_config.get("clustering_config", {})
        for key, value in overrides.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config
```

**Uso no orquestrador:**
```python
config = ClusteringConfig.from_job_config(job.get("config", {}))
sim_matrix = compute_tolerant_similarity_matrix(core_blocks, config)
clusters = consensus_clustering(sim_matrix, threshold=config.clustering_threshold)
```

**Validação futura:** Após implementação, rodar com PDFs reais do Planet Express e ajustar defaults com base nos resultados. Logar `config` + `cluster_results` para análise de sensibilidade.

---

#### 5.23.10 G15 — Garantia Contratual Preservada com `page_type`

**Problema:** Filtrar páginas em branco/escaneadas quebra a garantia "toda página em 1 cluster".

**Resolução:** Manter a garantia adicionando `page_type` ao contrato. Todas as páginas estão em exatamente 1 cluster, mas o tipo indica como processá-las.

**Contrato 3.1 atualizado:**

```python
context["clusters"] = [
    {
        "cluster_id": str,           # "A", "B", ... ou "_blank"
        "pages": [
            {
                "pdf_id": str,
                "page_index": int,
                "page_type": str     # "text" | "scanned" | "blank" ← NOVO
            }
        ],
        "representative_page": {"pdf_id": str, "page_index": int},
        "page_count": int,
        "is_processable": bool,      # NOVO — False para _blank
        "confidence": { ... },
    }
]
```

**Garantias atualizadas:**
- ✅ Toda página de todos os PDFs está em exatamente 1 cluster (inalterado)
- ✅ `page_type` indica como Stage 2 deve tratar a página
- ✅ Clusters com `is_processable: False` são ignorados pelo Stage 2
- ✅ `sum(cluster.page_count) == total_pages` continua verdadeiro
- 🆕 Páginas `scanned` podem estar em clusters text-based (se pHash agrupou) ou em cluster separado

**Comportamento de Stage 2 por `page_type`:**

| page_type | Stage 2 behavior |
|-----------|-----------------|
| `text` | Extração completa normal (get_text("dict"), fontes, imagens, etc.) |
| `scanned` | Screenshot rendering + flag para possível OCR futuro |
| `blank` | Skip — nada para extrair |

---

## 6. Stage 2 — Detalhamento Técnico Completo

### Princípio: Extrair tudo que o pipeline precisa, sem perder geometria

Stage 2 é o **único momento** em que o pipeline lê os PDFs com profundidade. Se informação não é capturada aqui, ela é perdida para sempre — nenhum stage downstream reabre o PDF. Por isso, cada sub-step deve extrair o máximo com a melhor ferramenta disponível.

Stage 2 roda **SÓ nas páginas representativas** do Stage 1 (~6 páginas para 100 páginas/2 templates). Isso torna o custo computacional baixo, permitindo extração mais rica.

### 6.1 Avaliação de Bibliotecas e Melhores Práticas

#### 2.1 Full Text Extraction — `get_text("dict")` + `page.rect` + `span["flags"]`

**Biblioteca: PyMuPDF (fitz)** — Melhor opção para extração de texto com coordenadas.

| Alternativa | Avaliação |
|-------------|-----------|
| `pdfplumber` | ~10x mais lento, API alto nível mas menos controle |
| `pdfminer.six` | Mais lento, mais controle de encoding |
| `pymupdf4llm` | Wrapper para LLMs, não dá acesso a spans/fontes |

**Mudanças v3.5 (vs implementação atual):**

```python
# ANTES (atual) — perde 3 informações críticas:
for span in line.get("spans", []):
    blocks.append(TextBlock(
        text=span["text"],
        bbox=span["bbox"],
        font_name=span.get("font", ""),
        font_size=float(span.get("size", 0.0)),
        page_number=page_num,
        pdf_id=pdf_id,
    ))

# DEPOIS (v3.5) — captura tudo que o PDF oferece:
page = doc[page_num]
page_width = page.rect.width    # NOVO — dimensões da página
page_height = page.rect.height  # NOVO

for span in line.get("spans", []):
    flags = span.get("flags", 0)  # NOVO — bitmask confiável
    blocks.append(TextBlock(
        text=span["text"],
        bbox=span["bbox"],
        font_name=span.get("font", ""),
        font_size=float(span.get("size", 0.0)),
        is_bold=bool(flags & 16),     # NOVO — bit 4
        is_italic=bool(flags & 2),    # NOVO — bit 1
        is_mono=bool(flags & 8),      # NOVO — bit 3
        color=span.get("color"),      # NOVO — RGB int (opcional)
        page_number=page_num,
        pdf_id=pdf_id,
    ))
```

**Por que `span["flags"]` em vez de parsing do font_name:**
- Font name "ABCDEF+CustomFont" não contém "bold" → parsing falha
- Font name "HelveticaNeue-Medium" não é "bold" mas não é "normal" → ambíguo
- `span["flags"]` é definido pelo PDF engine — confiável independente do nome

**Por que `page.rect`:**
- Semantic Analysis precisa saber top 15% / bottom 10% → requer `height`
- Layout Alignment normaliza coordenadas → requer `width` e `height`
- Template Generation posiciona no canvas → requer dimensões
- Sem isso, hardcodes (como 700pts para bottom de tabela multi-page) quebram para Letter/custom

**Risco de encoding:** PDFs com CIDFont sem ToUnicode map retornam `\x00` ou garbled text. Validado pelo sub-step 2.10 (Quality Check).

**Fix de robustez:** Usar context manager (`with fitz.open(...) as doc:`) em vez de `doc.close()` manual para evitar file handle leak em exceções.

#### 2.2 Text Reconstruction — threshold proporcional + sub_spans

**Biblioteca: Custom** — Correto manter algoritmo próprio. `pdfplumber.extract_words()` faz reconstrução mas perde controle fino.

**Mudanças v3.5:**

| Aspecto | Antes | Depois | Por quê |
|---------|-------|--------|---------|
| Y_THRESHOLD | 3.0px fixo | `min(font_size * 0.3, 5.0)` | Fontes grandes (24pt+) têm baseline shift > 3px; fontes pequenas (6pt) precisam threshold menor |
| Font merge | Merge se mesma font family | Merge se mesma font family, mas preservar `sub_spans[]` com atributos originais | Evitar perder rich text inline ("Nome:" regular + "**João**" bold = 1 bloco mas com 2 sub_spans) |
| Cross-column | Não protegido | Respeitar `grid_info` — se 2 spans estão em colunas diferentes do grid, NÃO mergear | Evitar fundir "Total" (col A) + "150,00" (col B) em tabelas com gap pequeno |

**Risco mitigado (atualizado v3.12):** Text Reconstruction roda ANTES de Grid/Table Detection (2.6). Duas opções de proteção contra merge cross-column:
1. **`drawn_elements`** (linhas verticais de `get_drawings()`) — se disponíveis, são evidência forte de separação de coluna. Extrair no step 2.1b antes de reconstruction.
2. **Reordenar**: rodar Grid Detection (2.6) ANTES de Text Reconstruction (2.2), usando coordenadas brutas dos spans. Grid info protege o merge.

**Decisão:** Opção 1 (drawn_elements como hint) é preferível — linhas vetoriais são rápidas de extrair e não dependem de Jenks. Se a página não tem linhas vetoriais, o merge cross-column continua sendo risco aceito (mitigado por find_tables em 2.7 que re-estrutura).

#### 2.3 Font → CSS — FONT_MAP expandido + span flags

**Biblioteca: Custom** — Mapeamento estático é a abordagem padrão. Nenhuma biblioteca resolve isso melhor.

**Mudanças v3.5:**

```python
# v3.12 — Strip de prefixo de subset ANTES do lookup
def _normalize_pdf_font_name(raw_name: str) -> str:
    """Remove prefixo de subset (ex: 'ABCDEF+ArialMT' → 'ArialMT').

    PDFs com fontes embedadas usam prefixo de 6 letras + '+' para identificar
    subsets. Sem strip, o FONT_MAP nunca casa com fontes embedadas.
    Também remove sufixos comuns: -Regular, -Roman, PSMat, PSMT.
    """
    # Strip subset prefix: 'ABCDEF+FontName' → 'FontName'
    if "+" in raw_name:
        raw_name = raw_name.split("+", 1)[1]
    # Strip common suffixes
    for suffix in ["-Regular", "-Roman", "PSMT", "PSMat"]:
        if raw_name.endswith(suffix):
            raw_name = raw_name[:-len(suffix)]
    return raw_name

# FONT_MAP expandido de 14 → ~50 fontes mais comuns em PDFs
FONT_MAP = {
    # Standard 14 (mantidos)
    "Helvetica": "Arial", "Times-Roman": "Times New Roman", "Courier": "Courier New",
    # Comuns em PDFs corporativos
    "ArialMT": "Arial", "ArialNarrow": "Arial Narrow",
    "Calibri": "Calibri", "Cambria": "Cambria",
    "Verdana": "Verdana", "Tahoma": "Tahoma", "Georgia": "Georgia",
    "TrebuchetMS": "Trebuchet MS", "LucidaConsole": "Lucida Console",
    "SegoeUI": "Segoe UI", "OpenSans": "Open Sans", "Roboto": "Roboto",
    "Lato": "Lato", "SourceSansPro": "Source Sans Pro",
    "NotoSans": "Noto Sans", "DejaVuSans": "DejaVu Sans",
    # Serif
    "Garamond": "Garamond", "BookAntiqua": "Book Antiqua",
    "Palatino": "Palatino Linotype", "CenturyGothic": "Century Gothic",
    # Mono
    "ConsolasRegular": "Consolas", "LucidaSansTypewriter": "Lucida Sans Typewriter",
    # ... extensível
}

# Resolução: normalizar → FONT_MAP → fallback por flags
normalized = _normalize_pdf_font_name(span.get("font", ""))
css_family = FONT_MAP.get(normalized)

# Fallback inteligente usando span flags:
if css_family is None:
    flags = span.get("flags", 0)
    if flags & 8:    # monospace
        css_family = "Courier New, monospace"
    elif flags & 4:  # serif
        css_family = "Times New Roman, serif"
    else:
        css_family = "Arial, sans-serif"
```

**Bold/italic agora vem de `is_bold`/`is_italic` do TextBlock (span flags), não re-derivado do font_name.** Elimina duplicação e parsing frágil.

**v3.12 — Integração pipeline ↔ editor para fonts:**
O TextBlock preserva `font_name` (nome interno PDF, já normalizado sem subset prefix). Downstream:
1. Pipeline FONT_MAP resolve ~90% das fonts para CSS
2. Editor `useFontCascade` tenta resolver o restante (normalização + bibliotecas IndexedDB + IA)
3. Se não encontra → `FontWarning` aparece → operador pode subir a font (`.ttf`/`.otf`/`.woff`/`.woff2`)
4. Font fica no IndexedDB → cascade re-resolve → status `found`

#### 2.4 Image Extraction — filtro de masks + validação de bbox

**Biblioteca: PyMuPDF** — Melhor opção. `pdfplumber` não extrai imagens embarcadas. `pdf2image` converte páginas inteiras.

**Mudanças v3.5:**

```python
# NOVO — filtrar soft masks (componentes internos, não imagens visíveis)
for img_info in image_list:
    xref = img_info[0]
    smask = img_info[1]    # soft mask xref
    if smask != 0:
        # Esta imagem É uma mask usada por outra — skip
        # (a imagem "real" referencia esta mask internamente)
        continue

# NOVO — validar bbox
bbox = _get_image_bbox(page, xref)
bbox_valid = bbox != (0.0, 0.0, 0.0, 0.0)
if not bbox_valid:
    logger.warning("Image xref=%d sem bbox — posição será estimada", xref)

images.append(ParsedImage(
    path=str(file_path),
    format=ext,
    bbox=bbox,
    bbox_valid=bbox_valid,  # NOVO — downstream sabe se posição é real
    page_number=page_num,
    pdf_id=pdf_id,
))
```

**Imagens vetoriais (logos SVG, charts):** Não são capturadas por `get_page_images()` — existem como paths/drawings. Para capturá-las: renderizar a região como PNG via `page.get_pixmap(clip=rect)`. Isso é melhoria futura — requer detecção automática de regiões vetoriais.

#### 2.5 Screenshot Rendering — SÓ representativas + alpha=False

**Biblioteca: PyMuPDF `page.get_pixmap()`** — Melhor opção. Self-contained, alta qualidade (MuPDF engine). `pdf2image` requer Poppler system dependency.

**Mudanças v3.5:**

```python
# ANTES (atual) — renderiza TODAS as páginas (100 PNGs para 100 páginas)
for page_num in range(len(doc)):
    pixmap = page.get_pixmap(matrix=matrix)

# DEPOIS (v3.5 / corrigido v3.12) — SÓ representativas (~6 PNGs)
# Extrair representatives dos clusters (não existe key separada "representative_pages")
representative_pages = [c["representative_page"] for c in context["clusters"]]
for rep in representative_pages:
    pdf_doc = pdf_docs[rep["pdf_id"]]  # abrir PDF correto pelo pdf_id
    page = pdf_doc[rep["page_index"]]
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)  # fundo branco garantido
```

**DPI = 150:** Equilíbrio correto. 72 DPI pixelado, 300 DPI pesado sem ganho para análise estrutural. Mantido.

**Formato PNG:** Para ~6 representativas, PNG (~200-500KB cada) é aceitável. WebP seria 30-50% menor mas adiciona dependency. Melhoria futura não-prioritária.

#### 2.6 Grid Detection — Jenks Natural Breaks

**Biblioteca atual: scikit-learn KMeans** — Subótimo para clustering 1D de coordenadas.

| Alternativa | Avaliação |
|-------------|-----------|
| **KMeans** (atual) | Precisa saber K, assume clusters esféricos, sensível a outliers |
| **DBSCAN** | Não precisa K, lida com ruído, mas eps é sensível ao scale |
| **Jenks Natural Breaks** | Desenhado especificamente para "natural breaks" em dados 1D — exatamente nosso caso |
| **Gap-based** (fallback atual) | Simples mas frágil com espaçamento irregular |

**Decisão: Jenks Natural Breaks (`jenkspy`)** como método primário, DBSCAN como validação cruzada.

**Mudança adicional — excluir header/footer zones:**

```python
# ANTES — grid calculado com TODOS os text_blocks (polui com títulos centralizados)
x_coords = [b.bbox[0] for b in text_blocks]

# DEPOIS — excluir header (top 15%) e footer (bottom 10%) da detecção de grid
content_blocks = [
    b for b in text_blocks
    if b.bbox[1] > page_height * 0.15 and b.bbox[3] < page_height * 0.90
]
x_coords = [b.bbox[0] for b in content_blocks]
```

Isso evita que títulos centralizados ou footers com "Página 1/2" puxem centróides para posições falsas.

#### 2.7 Table Detection — PyMuPDF `find_tables()`

**Biblioteca atual: Custom 3-evidências** — Funcional mas **significativamente inferior** às alternativas.

| Alternativa | Ruling Lines | Multi-table | Cell bbox | Dependency |
|-------------|-------------|-------------|-----------|------------|
| **Custom atual** | Não | Não (1/página) | Não | Nenhuma |
| **PyMuPDF `find_tables()`** | **Sim** | **Sim** | **Sim** | Nenhuma (já usa PyMuPDF) |
| **camelot-py** | Sim (lattice mode) | Sim | Sim | Ghostscript |
| **tabula-py** | Sim | Sim | Sim | Java Runtime |

**Decisão: PyMuPDF `page.find_tables()`** — disponível desde PyMuPDF 1.23.0. Zero dependencies adicionais.

```python
# ANTES — 3 evidências indiretas, sem ruling lines, 1 tabela por página
grid_score = _score_grid(page.grid_info)
align_score = _score_alignment(blocks)
pattern_score = _score_pattern(blocks)
combined = grid_score * 0.45 + align_score * 0.35 + pattern_score * 0.20

# DEPOIS — PyMuPDF find_tables() com ruling lines + clustering built-in
import fitz
page = doc[page_num]
tabs = page.find_tables()  # retorna TableFinder com lista de Table objects

for table in tabs.tables:
    cells = []
    for row_idx, row in enumerate(table.extract()):
        row_cells = []
        for col_idx, cell_text in enumerate(row):
            cell_bbox = table.cells[row_idx * table.col_count + col_idx]  # (x0, y0, x1, y1)
            row_cells.append({
                "text": cell_text or "",
                "bbox": list(cell_bbox),
                "column_index": col_idx,
            })
        cells.append(row_cells)

    # v3.12 — Header detection melhorado (não assume cells[0] sempre)
    header_row_count = _detect_header_rows(table, cells)
    headers = cells[:header_row_count] if header_row_count > 0 else []
    data_rows = cells[header_row_count:] if header_row_count > 0 else cells

    detected_table = {
        "table_id": str(uuid.uuid4()),
        "bbox": list(table.bbox),
        "headers": headers,               # v3.12: lista de rows (suporta multi-row header)
        "rows": data_rows,
        "columns": table.col_count,
        "header_row_count": header_row_count,  # v3.12: quantas linhas são header
        "confidence": 0.95 if table.header.external else 0.80,
        "detection_method": "ruling_lines" if _has_ruling_lines(page, table.bbox) else "clustering",
        "has_ruling_lines": _has_ruling_lines(page, table.bbox),
        "is_multi_page": False,  # resolvido em 2.8
    }

# v3.12 — Detectar quantas linhas são header
def _detect_header_rows(table, cells):
    """Identifica header por 3 sinais: bold, background, ruling line inferior.

    Retorna número de linhas de header (0 = sem header, 1 = comum, 2+ = multi-row).
    """
    if not cells:
        return 0

    # Sinal 1: PyMuPDF header detection (table.header)
    if hasattr(table, 'header') and table.header.external:
        return 1  # PyMuPDF detectou header externo

    # Sinal 2: Primeira linha com estilo diferente (bold, cor, font_size)
    # Implementação: comparar atributos de cells[0] vs cells[1] quando disponíveis
    # (requer acesso aos text_blocks originais — cross-reference por bbox)

    # Sinal 3: Ruling line horizontal separando row 1 de row 2
    # (requer drawn_elements — cross-reference por posição Y)

    # Default conservador: assumir 1 linha de header
    return 1
```

**Vantagens sobre o custom atual:**
1. **Ruling lines** — detecta bordas vetoriais do PDF (evidência #1 para tabelas)
2. **Multi-tabela por página** — retorna todas as tabelas, não só a dominante
3. **Cells com bbox** — cada célula tem coordenadas → Stage 4/5 posiciona corretamente
4. **Menos código** — elimina ~300 linhas de heurísticas (3 evidence scores, alignment, pattern)
5. **Testado em milhares de PDFs** pelo time do PyMuPDF

**Fallback (v3.12 — ACEITO SEM FALLBACK):** PDFs do Planet Express são sempre gerados por motor — tabelas sempre têm estrutura vetorial (ruling lines ou alinhamento claro). `find_tables()` cobre ambos os modos (ruling lines + clustering). O algoritmo custom de 3 evidence scores **não é necessário como fallback**. Se `find_tables()` não detectar, o Quality Check (2.10 CHECK 5) sinaliza a anomalia. Risco aceito.

#### 2.8 Table Structuring — cells com bbox + multi-page % height

**Biblioteca: Custom** — Correto. Com `find_tables()` fazendo o grosso, o structuring fica mais simples.

**Mudanças v3.5:**

```python
# ANTES — headers e rows são List[str] e List[List[str]] (SEM geometria)
table.headers = ["Descrição", "Qtd", "Valor"]
table.rows = [["Produto A", "2", "100,00"], ...]

# DEPOIS — headers e rows preservam bbox de cada célula
table.headers = [
    {"text": "Descrição", "bbox": [72, 200, 250, 215], "column_index": 0},
    {"text": "Qtd",       "bbox": [255, 200, 310, 215], "column_index": 1},
    {"text": "Valor",     "bbox": [315, 200, 400, 215], "column_index": 2},
]
table.rows = [[
    {"text": "Produto A", "bbox": [72, 220, 250, 235], "column_index": 0},
    {"text": "2",         "bbox": [255, 220, 310, 235], "column_index": 1},
    {"text": "100,00",    "bbox": [315, 220, 400, 235], "column_index": 2},
], ...]

# ANTES — multi-page hardcoded 700pts (assume A4 842pts)
if tbl.bbox[3] < 700.0:  # ← HARDCODE
    continue

# DEPOIS — percentual da page height
if tbl.bbox[3] < page_height * 0.83:
    continue
```

**O modelo `TableCell` com bbox JÁ EXISTE** (`backend/models/detected_table.py`) mas não é usado. Na v3.5, passa a ser o formato padrão.

#### ~~2.9 XSD Parsing~~ — MOVIDO para Stage 4.1 (v3.12)

> **v3.12:** XSD Parsing não pertence ao Stage 2. O Stage 2 responde "o que tem na página?" — o XSD não é uma página. Quem consome o `field_tree` é o Stage 4 (Field Mapping: "como cada campo se conecta ao XSD?"). Stage 3 não usa.
>
> Detalhamento técnico (lxml, gaps de xs:import/xs:group/xs:attribute) movido para documentação do Stage 4.

#### 2.9 Extraction Quality Check — NOVO (renumerado de 2.10)

**Sub-step novo** — não existe no pipeline atual. Garante que o output do Stage 2 é confiável antes de alimentar Stage 3.

```python
async def extraction_quality_check(context: Dict[str, Any]) -> List[Dict]:
    """2.10 — Validar qualidade da extração antes de passar para Stage 3."""
    warnings = []
    enriched = context.get("enriched_documents", [])

    for doc in enriched:
        for page in doc.get("pages", []):
            if not page.get("is_representative"):
                continue

            page_key = f"{doc['pdf_id']}:{page['page_index']}"
            blocks = page.get("text_blocks", [])

            # CHECK 1: Página representativa sem text_blocks
            # (provável PDF scanned sem OCR)
            if len(blocks) == 0:
                warnings.append({
                    "page_key": page_key,
                    "type": "empty_page",
                    "message": "Página representativa sem texto — possível PDF scanned sem OCR",
                    "severity": "error",
                })
                continue

            # CHECK 2: Proporção alta de caracteres non-printable
            # (encoding quebrado, CIDFont sem ToUnicode)
            all_text = " ".join(b["text"] for b in blocks)
            non_printable = sum(1 for c in all_text if not c.isprintable() and c not in "\n\t\r")
            if len(all_text) > 0 and non_printable / len(all_text) > 0.10:
                warnings.append({
                    "page_key": page_key,
                    "type": "encoding_issue",
                    "message": f"~{non_printable} caracteres non-printable ({non_printable/len(all_text):.0%}) — encoding provav. quebrado",
                    "severity": "warning",
                })

            # CHECK 3: Text blocks com bboxes sobrepostas > 80%
            # (OCR ghost — texto invisível sobreposto ao texto real)
            duplicate_count = _count_overlapping_blocks(blocks, overlap_threshold=0.80)
            if duplicate_count > len(blocks) * 0.20:
                warnings.append({
                    "page_key": page_key,
                    "type": "duplicate_text",
                    "message": f"{duplicate_count} blocos com sobreposição >80% — possível OCR ghost",
                    "severity": "warning",
                })

            # CHECK 4: Proporção texto vs área da página muito baixa
            # (possível PDF com conteúdo predominantemente visual)
            page_area = page.get("width", 1) * page.get("height", 1)
            text_area = sum(
                (b["bbox"][2] - b["bbox"][0]) * (b["bbox"][3] - b["bbox"][1])
                for b in blocks
            )
            if page_area > 0 and text_area / page_area < 0.05:
                warnings.append({
                    "page_key": page_key,
                    "type": "low_text_density",
                    "message": "Densidade de texto < 5% da página — conteúdo pode ser predominantemente visual",
                    "severity": "warning",
                })

            # CHECK 5 (v3.12): Tabelas com problemas estruturais
            tables = page.get("tables", [])
            for tbl in tables:
                all_rows = (tbl.get("headers", []) or []) + (tbl.get("rows", []) or [])

                # 5a: Tabela detectada com 0 rows (falso positivo do find_tables)
                if len(all_rows) == 0:
                    warnings.append({
                        "page_key": page_key,
                        "type": "empty_table",
                        "message": f"Tabela {tbl['table_id'][:8]} detectada mas sem rows — possível falso positivo",
                        "severity": "warning",
                    })

                # 5b: Tabela com todas as cells vazias (estrutura sem conteúdo)
                elif all(
                    all(cell.get("text", "").strip() == "" for cell in row)
                    for row in all_rows
                ):
                    warnings.append({
                        "page_key": page_key,
                        "type": "empty_table_content",
                        "message": f"Tabela {tbl['table_id'][:8]} tem estrutura mas todas as células vazias",
                        "severity": "warning",
                    })

                # 5c: Tabela com confidence baixa (< 0.60)
                elif tbl.get("confidence", 1.0) < 0.60:
                    warnings.append({
                        "page_key": page_key,
                        "type": "low_confidence_table",
                        "message": f"Tabela {tbl['table_id'][:8]} com confidence {tbl['confidence']:.2f} — detecção incerta",
                        "severity": "warning",
                    })

    context["extraction_warnings"] = warnings

    # Se algum warning tem severity=error → checkpoint para o operador
    errors = [w for w in warnings if w["severity"] == "error"]
    if errors:
        # Usar handle_service_failure da Seção 12
        # Operador decide: fornecer OCR externo / continuar mesmo assim / cancelar
        pass

    return warnings
```

**Por que é necessário:**
- Stage 1 tem 3 camadas de defesa. Stage 2 atual tem **zero validação**
- Se texto é lixo (encoding, OCR ghost, scanned sem OCR), todo Stage 3+ produz resultados incorretos
- Melhor falhar cedo e avisar o operador do que produzir template com campos inválidos

### 6.2 Gaps Identificados e Resolvidos

| # | Gap | Severidade | Resolução v3.5 |
|---|-----|-----------|-----------------|
| G1 | `width`/`height` da página não capturados | ALTA | `page.rect` capturado em 2.1, adicionado ao contrato |
| G2 | `is_bold`/`is_italic` não no TextBlock | MÉDIA | `span["flags"]` extraído em 2.1, propagado ao TextBlock |
| G3 | Zero validação da extração | ALTA | Novo sub-step 2.10: Extraction Quality Check |
| G4 | Tabelas perdem `bbox` das células | MÉDIA-ALTA | `find_tables()` retorna cells com bbox, contrato atualizado |
| G5 | Linhas vetoriais do PDF ignoradas | MÉDIA | `find_tables()` usa ruling lines nativamente |

### 6.3 Riscos Identificados e Mitigações

| # | Risco | Prob. | Mitigação |
|---|-------|-------|-----------|
| R1 | Text Reconstruction funde colunas de tabela | Média | **v3.12:** Usar `drawn_elements` (linhas verticais) como hint de coluna antes do merge. Fallback: `find_tables()` (2.7) re-estrutura depois |
| R2 | Grid Detection polui com blocos fora de tabela | Média | Excluir header (top 15%) e footer (bottom 10%) zones antes de clusterizar |
| R3 | Screenshots renderiza todas as páginas | Baixa | **v3.12:** Extrair representatives de `context["clusters"]` (corrigido — key `representative_pages` não existe) |

### 6.4 Dado para Multi-Example Analysis — RESOLVIDO (Opção A)

#### O Problema

Stage 2 extrai profundamente **só páginas representativas** (~1 por cluster). Mas o Stage 3.2 (Multi-Example Analysis) precisa comparar **texto real** de **múltiplas páginas** do mesmo cluster para distinguir label de dynamic:

```
Cluster A (template "fatura") — 50 páginas de 3 PDFs:

  Representativa (deep extracted):
    Posição (72, 200): "Cliente: João Silva"

  Sem outros exemplos, Stage 3.2 não sabe:
    "Cliente:" é label?     → Precisa ver outra página com "Cliente:" na mesma posição
    "João Silva" é dynamic? → Precisa ver "Maria Santos" na mesma posição em outro PDF
```

**Se Stage 3.2 recebe só 1 página por cluster**, cai no fallback de heurística single-PDF:
- "termina com `:` → label" (funciona para "Nome:", falha para "Ref: 12345")
- "numérico/data → dynamic" (funciona para "123.456", falha para "Lote A")
- Accuracy estimada sem NER/regex: **~60%** (vs **~95%** com comparação real multi-PDF)
- **v3.14:** Com NER + regex a accuracy sobe para **~70-80%** em single-PDF. Campos não resolvidos → Stage 4 decide via XSD

O Stability Classification (Stage 3.3) tem o mesmo problema — sem múltiplos exemplos, tudo é classificado como "unknown" com score 1.0 (não sabe o que é stable/variable/absent).

#### Decisão: Opção A — Stage 1 preserva `_raw_text_blocks`

**Princípio:** Cada estágio responde SUA pergunta. Stage 1 agrupa páginas (já lê todos os blocos no step 1.2). Stage 3 classifica e compara (precisa de dados de múltiplas páginas). A solução é Stage 1 **não descartar** o texto que já leu — preservando-o para Stage 3 consumir.

Stage 1 não ganha responsabilidade nova. Ele já lê o texto no step 1.2 (`get_text("blocks")`). Hoje ele descarta o texto real após a abstração (step 1.5). A mudança é: **preservar antes de abstrair**.

Stage 2 não muda — continua extraindo profundamente só representativas.

Stage 3 recebe dados de todas as páginas (texto + posição) e FAZ a análise de variação — que é literalmente seu trabalho (3.2 Multi-Example, 3.3 Stability, 3.4 Variant Detection).

#### Implementação

**Stage 1 — step 1.2 (Block Extraction), após extrair e ANTES de abstrair:**

```python
# Step 1.2: extract_blocks() — já existe
blocks = extract_blocks(pages)  # get_text("blocks") de todas as páginas

# NOVO — preservar texto real + posição normalizada ANTES da abstração
raw_text_blocks = {}
for page_key, page_blocks in blocks.items():
    raw_text_blocks[page_key] = [
        {
            "text": b["text"],                    # texto REAL (pré-abstração)
            "bbox_norm": b["bbox_norm"],           # posição normalizada [x0,y0,x1,y1]
            "x_center": b["x_center"],
            "y_center": b["y_center"],
            "type": b["type"],                     # 0=texto, 1=imagem
        }
        for b in page_blocks
        if b["type"] == 0  # só texto — imagens não têm texto para comparar
    ]

context["_raw_text_blocks"] = raw_text_blocks

# Step 1.5 continua normalmente — abstrai para clustering
blocks_abstract = abstract_content(blocks)  # "Cliente:" → "TEXT_S"
```

**Custo:**
- Computacional: **zero** — dado já computado no step 1.2
- Memória: **~50KB para 100 páginas** (~500 bytes/página × 100)
- O dado é tag `_` (prefixo underscore) = interno do pipeline, não exposto ao frontend

#### Como Stage 3 consome

```python
# Stage 3.1 — Multi-Example Analysis (v3.13: renumerado de 3.2)
def analyze_block_variability(cluster, raw_text_blocks):
    """Compara blocos na mesma posição entre todas as páginas do cluster.

    Para cada posição normalizada, analisa:
    - Quantas páginas têm bloco nessa posição (presença)
    - Se o texto varia entre páginas (label vs dynamic)
    - De quais PDFs vem (para detecção cross-PDF)
    """
    position_map = {}  # (x_rounded, y_rounded) → {texts: [], pages: [], pdf_ids: set()}

    for page_info in cluster["pages"]:
        page_key = f"{page_info['pdf_id']}:{page_info['page_index']}"
        page_blocks = raw_text_blocks.get(page_key, [])

        for block in page_blocks:
            # Agrupar blocos por posição (com tolerância de ±0.03)
            pos_key = (round(block["x_center"], 2), round(block["y_center"], 2))
            if pos_key not in position_map:
                position_map[pos_key] = {"texts": [], "pages": [], "pdf_ids": set()}

            position_map[pos_key]["texts"].append(block["text"])
            position_map[pos_key]["pages"].append(page_key)
            position_map[pos_key]["pdf_ids"].add(page_info["pdf_id"])

    # Classificar cada posição
    total_pages = len(cluster["pages"])
    total_pdfs = len({p["pdf_id"] for p in cluster["pages"]})
    results = []

    for pos_key, info in position_map.items():
        presence_ratio = len(info["pages"]) / total_pages
        unique_texts = set(info["texts"])
        pdf_coverage = len(info["pdf_ids"]) / total_pdfs if total_pdfs > 0 else 1.0

        classification = {
            "position": pos_key,
            "presence_ratio": presence_ratio,
            "pdf_coverage": pdf_coverage,
            "sample_texts": list(unique_texts)[:5],  # primeiros 5 únicos
        }

        # Stability (v3.13: consolidado em 3.1)
        if presence_ratio >= 0.90:
            classification["stability"] = "stable"
        elif presence_ratio >= 0.10:
            classification["stability"] = "variable"
        else:
            classification["stability"] = "rare"

        # Label vs Dynamic (v3.13: consolidado em 3.1)
        if len(unique_texts) == 1:
            classification["semantic"] = "label"       # mesmo texto sempre → label
            classification["confidence"] = 1.0
        elif len(unique_texts) == len(info["pages"]):
            classification["semantic"] = "dynamic"     # texto diferente em cada → dynamic
            classification["confidence"] = 0.95
        else:
            classification["semantic"] = "semi_dynamic" # mix — ex: enum com poucos valores
            classification["confidence"] = 0.80

        # Variant Detection (v3.13: consolidado em 3.1)
        if presence_ratio < 0.90 and pdf_coverage < 1.0:
            # Presente em alguns PDFs mas não todos → condicional
            classification["variant"] = "conditional"
            classification["present_in_pdfs"] = list(info["pdf_ids"])
        elif presence_ratio < 0.90:
            classification["variant"] = "optional"
        else:
            classification["variant"] = "required"

        results.append(classification)

    return results
```

**Exemplos de output:**

```python
# Posição (0.10, 0.25): "Cliente:" em 50/50 páginas, 3/3 PDFs
{
    "position": (0.10, 0.25),
    "stability": "stable",       # presente em 100% das páginas
    "semantic": "label",          # mesmo texto sempre
    "variant": "required",        # em todos os PDFs
    "confidence": 1.0
}

# Posição (0.35, 0.25): "João", "Maria", "Pedro" — 50/50 pgs, 3/3 PDFs
{
    "position": (0.35, 0.25),
    "stability": "stable",       # presente em 100%
    "semantic": "dynamic",        # texto muda
    "variant": "required",        # em todos os PDFs
    "confidence": 0.95
}

# Posição (0.10, 0.80): "Cônjuge: Maria" — 30/50 pgs, 2/3 PDFs
{
    "position": (0.10, 0.80),
    "stability": "variable",     # presente em 60%
    "semantic": "label",          # texto "Cônjuge:" é fixo quando presente
    "variant": "conditional",     # falta no PDF 2
    "present_in_pdfs": ["0", "2"],
    "confidence": 0.95
}
```

#### Impacto downstream

```
Com _raw_text_blocks (Opção A):
  Stage 3.1: "confirmed" — label/dynamic com ~95% accuracy (v3.13: renumerado)
  Stage 3.1: stable/variable/absent com presence_ratio real
  Stage 3.1: optional_field e conditional_section detectados com pdf_coverage
  Stage 4.2: Pair Validation com pares já detectados → menos ambiguidade (v3.13: renomeado)
  Stage 5:   Template sabe o que é fixo vs placeholder
  Frontend:  VariationMatrix populada com dados reais → diff view funcional
```

#### Fallback single-PDF

Se o job tem apenas 1 PDF, `_raw_text_blocks` ainda é útil — Stage 3 compara entre páginas do mesmo PDF (menos poderoso que cross-PDF, mas melhor que 0 comparação):

```python
# Single-PDF: label vs dynamic detectado por variação entre páginas
# "Cliente:" aparece idêntico em 50 páginas → label (confidence: 0.90)
# "João Silva" varia entre páginas → dynamic (confidence: 0.85)
# Campos condicionais cross-PDF: não detectáveis → "unknown" (confidence: 0.50)
```

#### Opções descartadas

| Opção | Por que descartada |
|-------|-------------------|
| **B. Stage 2 re-extrai páginas extras** | Duplica trabalho que Stage 1 já fez. Stage 2 reabriria PDFs já lidos. Custo desnecessário |
| **C. Heurística single-PDF** | Accuracy ~60%. Inaceitável — o motivo de subir múltiplos PDFs é justamente detectar variações com alta confiança |
| **D. Subproduto do clustering** | Stage 1 computaria variabilidade, respondendo à pergunta do Stage 3. Mistura responsabilidades — "quais páginas são iguais" ≠ "o que varia entre elas" |

---

### 6.5 Gaps Adicionais v3.6: Elementos Visuais e Cor

#### Gap G6: Elementos visuais desenhados (linhas, retângulos, backgrounds)

**Problema:** PDFs contêm elementos desenhados via `page.get_drawings()` que carregam significado estrutural:

| Elemento | Significado | Quem precisa |
|----------|------------|-------------|
| Linhas horizontais | Separadores de seção | Stage 3.6 Hierarchy Builder |
| Linhas verticais | Separadores de coluna | Stage 2.6 Grid Detection |
| Retângulos preenchidos | Backgrounds de header, alternating row colors | Stage 5 Template Generation |
| Ruling lines (grid completo) | Bordas de tabela | Stage 2.7 Table Detection (já coberto por `find_tables()`) |

**Situação atual:** `find_tables()` (v3.5) captura ruling lines para detecção de tabelas. Mas linhas e retângulos **fora de tabelas** são completamente ignorados. O Hierarchy Builder (Stage 3.5, v3.13) usa drawn_elements como sinal prioritário para detecção de seções — linhas horizontais são separadores fortes.

**Proposta:** Novo campo no contrato do Stage 2:

```python
# Dentro de cada page em enriched_documents:
"drawn_elements": [
    {
        "type": "line",             # "line" | "rect" | "curve"
        "points": [(x0, y0), (x1, y1)],  # para lines
        "bbox": [x0, y0, x1, y1],  # para rects
        "orientation": "horizontal" | "vertical" | "diagonal" | null,
        "fill_color": int | null,   # RGB int se preenchido
        "stroke_color": int | null, # RGB int se contorno
        "width": float,             # stroke width
    }
] | null
```

**Implementação:**

```python
# Sub-step dentro de 2.1 ou novo 2.1b:
drawings = page.get_drawings()
drawn_elements = []
for d in drawings:
    for item in d["items"]:
        kind = item[0]  # "l" (line), "re" (rect), "c" (curve), "qu" (quad)
        if kind == "l":
            p1, p2 = item[1], item[2]
            dx, dy = abs(p2.x - p1.x), abs(p2.y - p1.y)
            orientation = "horizontal" if dy < 2 else ("vertical" if dx < 2 else "diagonal")
            drawn_elements.append({
                "type": "line",
                "points": [(p1.x, p1.y), (p2.x, p2.y)],
                "bbox": [min(p1.x, p2.x), min(p1.y, p2.y), max(p1.x, p2.x), max(p1.y, p2.y)],
                "orientation": orientation,
                "fill_color": d.get("fill"),
                "stroke_color": d.get("color"),
                "width": d.get("width", 1.0),
            })
        elif kind == "re":
            rect = item[1]
            drawn_elements.append({
                "type": "rect",
                "points": [],
                "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                "orientation": None,
                "fill_color": d.get("fill"),
                "stroke_color": d.get("color"),
                "width": d.get("width", 1.0),
            })
```

**Impacto downstream:**
- Hierarchy Builder (3.5): linhas horizontais com `width > 0.5` e `orientation = "horizontal"` → sinal 2 (separador forte de seção)
- Grid Detection (2.6): linhas verticais → evidência de coluna (reforça Jenks)
- Template Generation (5.1): retângulos preenchidos → backgrounds para sections/headers no HTML/CSS

**Severidade: MÉDIA** — melhora a qualidade da hierarquia e fidelidade visual do template.

#### Gap G7: Cor do texto — de opcional para obrigatório

**Problema:** Na v3.5, `span["color"]` foi marcado como "opcional". Mas a cor do texto carrega informação semântica e visual:

| Cenário | Exemplo | Se perde cor |
|---------|---------|-------------|
| Labels vs valores | Labels em azul (#003399), valores em preto (#000000) | Template perde distinção visual |
| Campos obrigatórios | Texto em vermelho indica obrigatoriedade | Operador perde sinal visual |
| Placeholders/exemplos | Texto em cinza claro (#999999) = placeholder | Template trata como conteúdo real |
| Links | Texto em azul sublinhado = URL | Template não sabe que é link |
| Headers/footers | Texto em cor diferente do body | Template perde hierarquia visual |

**Decisão v3.6:** `color` promovido de "opcional" para campo padrão no TextBlock.

```python
# TextBlock no contrato:
{
    "text": str,
    "bbox": [x0, y0, x1, y1],
    "font_name": str,
    "font_size": float,
    "is_bold": bool,
    "is_italic": bool,
    "is_mono": bool,
    "color": int,       # ← OBRIGATÓRIO (era opcional). RGB int de span["color"]
                        # Valor padrão: 0 (preto) se não disponível
}
```

**Impacto:**
- Stage 3.3 (Semantic Classification, v3.13): cor como sinal adicional para classificação (header blue, footer gray)
- Stage 5 (Template Generation): CSS `color: #{hex}` preserva aparência original
- Editor frontend: preview fiel ao PDF original

**Severidade: MÉDIA** — afeta fidelidade visual do template.

### 6.6 Resumo Consolidado de Gaps (v3.12)

| # | Gap | Severidade | Status | Resolução |
|---|-----|-----------|--------|-----------|
| G1 | `width`/`height` da página | ALTA | ✅ Resolvido v3.5 | `page.rect` em 2.1 |
| G2 | `is_bold`/`is_italic` frágil | MÉDIA | ✅ Resolvido v3.5 | `span["flags"]` em 2.1 |
| G3 | Zero validação da extração | ALTA | ✅ Resolvido v3.5 | Novo 2.10 Quality Check |
| G4 | Tabelas perdem `bbox` células | MÉDIA-ALTA | ✅ Resolvido v3.5 | `find_tables()` retorna cells com bbox |
| G5 | Ruling lines ignoradas | MÉDIA | ✅ Resolvido v3.5 | `find_tables()` usa nativamente |
| G6 | Elementos visuais desenhados | MÉDIA | ✅ Resolvido v3.6 | `get_drawings()` → `drawn_elements[]` |
| G7 | Cor do texto opcional | MÉDIA | ✅ Resolvido v3.6 | `color` obrigatório no TextBlock |
| G8 | Dado para Multi-Example Analysis | **ALTA** | ✅ **RESOLVIDO v3.10** | Opção A: Stage 1 preserva `_raw_text_blocks`. Stage 3 consome. Accuracy ~95% |
| G9-S2 | Screenshot usa key `representative_pages` inexistente | MÉDIA | ✅ **RESOLVIDO v3.12** | Extrair de `context["clusters"]` via list comprehension |
| G10-S2 | R1 cross-column referencia DBSCAN grid removido | MÉDIA | ✅ **RESOLVIDO v3.12** | `drawn_elements` (linhas verticais) como hint. DBSCAN não existe mais |
| G11-S2 | Terminologia `suspects` confunde com `template_mismatch` | BAIXA | ✅ **RESOLVIDO v3.12** | Renomeado para `outliers` / `quality_outlier_threshold` |
| G12-S2 | Form fields (AcroForm/XFA) não extraídos | N/A | ❌ **DESCARTADO** | PDFs Planet Express são gerados por motor, nunca contêm form fields |
| G13-S2 | `sub_spans` ausente do contrato 3.2 | MÉDIA | ✅ **RESOLVIDO v3.12** | `sub_spans[]` adicionado ao TextBlock (null se estilo uniforme) |
| G14-S2 | Fallback table detection não implementado | MÉDIA | ✅ **ACEITO v3.12** | PDFs gerados sempre têm estrutura vetorial. `find_tables()` cobre ruling lines + clustering. Sem fallback necessário. Quality Check 5 sinaliza anomalias |
| G15-S2 | Header tabela sempre `cells[0]` | MÉDIA | ✅ **RESOLVIDO v3.12** | `_detect_header_rows()` com 3 sinais (PyMuPDF header, estilo, ruling line). `headers` agora lista de rows. `header_row_count` no contrato |
| G16-S2 | Quality Check não valida tabelas | MÉDIA | ✅ **RESOLVIDO v3.12** | CHECK 5 adicionado: empty table, empty content, low confidence |
| G17-S2 | Subset prefix impede match no FONT_MAP | MÉDIA | ✅ **RESOLVIDO v3.12** | `_normalize_pdf_font_name()` strip prefix (`ABCDEF+`) e sufixos (`-Regular`, `PSMT`). Integração pipeline↔editor documentada |
| G1-S3 | Dependência circular 3.1↔3.2 (Semantic quer intelligence que Multi-Example não produziu) | ALTA | ✅ **RESOLVIDO v3.13** | Reordenação: Multi-Example Analysis primeiro (3.1), Semantic Classification depois (3.3) |
| G2-S3 | Layout Alignment cross-cluster não detalhado | MÉDIA | ❌ **DESCARTADO v3.13** | Stage 4 resolve via XSD paths. Cross-cluster alignment é over-engineering |
| G3-S3 | `stability_map` no contrato sem estrutura definida | MÉDIA | ✅ **RESOLVIDO v3.13** | Substituído por `block_classifications` indexado por block_id. stability_map eliminado |
| G4-S3 | `conditional_sections` — quem agrega blocos condicionais em seções? | MÉDIA | ✅ **RESOLVIDO v3.13** | Hierarchy Builder (3.5) agrega. Nós na árvore com `variant: "conditional"` + `present_in_pdfs` |
| G5-S3 | Document Type Detection sem algoritmo definido | BAIXA | ✅ **RESOLVIDO v3.13** | Sub-step removido — document_type já existe via keyword matching em `pipeline_result.py`. Sem valor adicional de LLM para metadata de display |
| G6-S3 | Hierarchy Builder não usa `drawn_elements` (contradiz seção 6.5) | ALTA | ✅ **RESOLVIDO v3.13** | drawn_elements como sinal 2 (linhas horizontais = separador forte). Integrado no algoritmo |
| G7-S3 | Thresholds de zona header/footer fixos (15%/90%) | BAIXA | ✅ **RESOLVIDO v3.13** | Visual regions substituem thresholds. Fallback: thresholds adaptativos (15%/85%) |
| G8-S3 | Gap de seção 20px fixo (não proporcional) | BAIXA | ✅ **RESOLVIDO v3.13** | Gap proporcional: 2.5% da altura da página |
| G9-S3 | `html_suggestion` referenciado mas ausente do contrato visual_analysis | MÉDIA | ✅ **RESOLVIDO v3.13** | Integrado na estrutura de cada região em visual_analysis |
| G10-S3 | Classificação label/dynamic falha com single-PDF ou amostras sem variação | **CRÍTICA** | ✅ **RESOLVIDO v3.14** | 3 camadas em cascata: estatística + regex + spaCy NER. Campos não resolvidos → Stage 4 decide via XSD |
| G11-S3 | Threshold fixo 30pts no label-value pairing "abaixo" | BAIXA | ✅ **RESOLVIDO v3.14** | Proporcional: 3.5% da altura da página (consistente com G8-S3) |
| G12-S3 | Stage 3 não sinaliza qualidade da classificação (single-PDF = mesma confiança que multi-PDF) | MÉDIA | ✅ **RESOLVIDO v3.14** | `classification_quality` no contrato com `statistical_strength` (none/weak/strong), `smart_override_count`, `uncertain_count`. Stage 4.5 consome direto |
| G13-S3 | Imagens do Stage 2 não entram na `document_trees` — `coverage.images.total` sempre 0 | **ALTA** | ✅ **RESOLVIDO v3.14** | Hierarchy Builder distribui imagens nas seções por bbox overlap. Nó `image` com path, bbox, bbox_valid, format |
| G14-S3 | Charts (detectados pelo Visual Analysis como `chart_area`) não entram na `document_trees` | MÉDIA | ✅ **RESOLVIDO v3.14** | Hierarchy Builder converte regiões `chart_area` do GPT-4o em nós `chart` nas seções correspondentes |
| G15-S3 | Visual Analysis não distingue chart vs barcode, nem detecta chart_type ou barcode_format | **ALTA** | ✅ **RESOLVIDO v3.14** | Prompt enriquecido: `barcode_area` como tipo de região, `chart_type` (bar/line/pie/doughnut/polarArea), `barcode_format` (CODE128/EAN13/etc), `confidence` por elemento. Zero chamadas extras |
| G16-S3 | Barcodes não entram na `document_trees` como tipo separado de chart | MÉDIA | ✅ **RESOLVIDO v3.14** | Hierarchy Builder cria nós `barcode` separados de `chart` com `barcode_format`. Editor já tem BarcodeInspector que espera esse tipo |

#### Gaps Stage 4 — Field Mapping (v3.15)

| # | Gap | Severidade | Resolução |
|---|-----|-----------|-----------|
| G1-S4 | Field Matching lê `parsed_documents.semantic_label` (AS-IS) em vez de `block_classifications.semantic` (v3) | **CRÍTICA** | ✅ **RESOLVIDO v3.15** | Stage 4.3 consome `block_classifications` por layout_id. `parsed_documents.semantic_label` não é mais usado |
| G2-S4 | Field Matching re-descobre labels por adjacência, ignorando `field_pair` do Stage 3.3 | ALTA | ✅ **RESOLVIDO v3.15** | Stage 4.2 (Pair Validation) consome `field_pair` do Stage 3.3. Só blocos sem par usam adjacência |
| G3-S4 | Sem `layout_type_id` nos field_mappings | ALTA | ✅ **RESOLVIDO v3.15** | Obrigatório em todo field_mapping. Processamento por cluster |
| G4-S4 | Processa TODOS os documentos em vez de só representativas | ALTA | ✅ **RESOLVIDO v3.15** | Itera por `clusters` (representativas), não por `parsed_documents` |
| G5-S4 | PA4: XSD não confirma `likely_dynamic` → `dynamic` | ALTA | ✅ **RESOLVIDO v3.15** | Se `semantic == "likely_dynamic"` e XSD confidence ≥ 0.7 → confirma `dynamic`. Label com match → warning |
| G6-S4 | PA1: `smart_signals` ignorados no Confidence Scoring | MÉDIA | ✅ **RESOLVIDO v3.15** | Heurísticas: `smart_override_count > 0` → -0.10 field_variability. `statistical_strength == "none"` → -0.15 |
| G7-S4 | PA5: `smart_signals` não passados nos field_mappings | MÉDIA | ✅ **RESOLVIDO v3.15** | `smart_signals` propagado em cada field_mapping. FieldDetailPanel exibe |
| G8-S4 | Confidence Scoring produz score global flat, não per-layout | ALTA | ✅ **RESOLVIDO v3.15** | `confidence_scores` agora `{layout_id → {factors + overall + status}}`. Alinhado com frontend `ConfidenceByLayout` |
| G9-S4 | Claude Sonnet no Confidence Scoring é custo desnecessário | MÉDIA | ✅ **RESOLVIDO v3.15** | Removido. Substituído por 3 heurísticas determinísticas ($0, testável) |
| G10-S4 | Patterns do Format Detection duplicam Stage 3.1 com divergências | BAIXA | ✅ **ACEITO v3.15** | Duplicação aceitável — Stage 3.1 classifica (label vs dynamic), Stage 4.4 detecta formato para JS. Responsabilidades distintas |
| G11-S4 | Layout Consistency conta `value` blocks de `parsed_documents` | ALTA | ✅ **RESOLVIDO v3.15** | Stage 4.6 consome `block_classifications` (dynamic count) e `document_trees` |
| G12-S4 | Sem `block_id` nos field_mappings | ALTA | ✅ **RESOLVIDO v3.15** | `block_id` obrigatório em todo field_mapping (rastreabilidade para overlay) |
| G13-S4 | Sem `is_table_cell`/`from_table` nos field_mappings | MÉDIA | ✅ **RESOLVIDO v3.15** | Propagado de `block_classifications` para cada field_mapping |
| G14-S4 | Stage 4.2 (Pair Validation) não existe como step separado | MÉDIA | ✅ **RESOLVIDO v3.15** | Sub-step 4.2 criado: valida pares Stage 3.3 + pareia soltos |
| G15-S4 | Sem checkpoint/service failure real | BAIXA | ✅ **ACEITO v3.15** | Service failure handling do batch LLM segue padrão existente (seção 12). Confidence Scoring agora local ($0), sem ponto de falha |
| G16-S4 | PA2 parcialmente implementado (consistency_score já lido) | INFO | ✅ **CONFIRMADO v3.15** | `_get_vision_agreement` já implementa `consistency_score / 100`. Nenhuma mudança necessária |
| G17-S4 | Field Matching ignora document_trees (Stage 3 gastou GPT-4o para construir hierarquia) | **ALTA** | ✅ **RESOLVIDO v3.15** | Section↔XSD Matching (4.4): seções da tree → nós XSD complexos. Reduz search space de ~80 para ~3-5 candidatos por campo |
| G18-S4 | Format Detection vem DEPOIS do Field Matching (formato seria hint valioso para o LLM) | MÉDIA | ✅ **RESOLVIDO v3.15** | Format Pre-Detection (4.3) movido para ANTES do matching. Formato (date, cpf, currency) enriquece prompt LLM |
| G19-S4 | Ambiguidades resolvíveis não são resolvidas (paths já usados por matches de alta confiança) | MÉDIA | ✅ **RESOLVIDO v3.15** | Two-pass: pass 1 aceita ≥0.7, pass 2 elimina paths já usados e re-ranqueia. Reduz ambiguidades ~50-70% |

#### Pontos de Atenção para Auditoria Stage 4 (originados no Stage 3)

| # | Ponto | Impacto | Onde resolver | Detalhe |
|---|-------|---------|---------------|---------|
| ~~PA1-S4~~ | ~~Stage 4.5 deve consumir `likely_dynamic` e `smart_signals` do Stage 3~~ | — | ✅ **RESOLVIDO v3.15 (G6-S4)** | Heurísticas no Confidence Scoring: se `smart_override_count > 0` → penalizar `field_variability` em 0.1; se `statistical_strength == "none"` → penalizar 0.15. Substituiu Claude Sonnet ($0 vs $0.02) |
| ~~PA2-S4~~ | ~~Stage 4.5 deve usar `consistency_score` do Stage 3.2 como input de `vision_agreement`~~ | — | ✅ **CONFIRMADO v3.15 (G16-S4)** | Código existente já implementa: `_get_vision_agreement` lê `consistency_score / 100`. Nenhuma mudança necessária |
| ~~PA3-S4~~ | ~~Stage 4.5 deve considerar número de PDFs~~ | — | ✅ **RESOLVIDO no Stage 3 (G12-S3)** | `classification_quality.statistical_strength` já informa none/weak/strong. Stage 4.5 consome direto sem precisar contar PDFs |
| ~~PA4-S4~~ | ~~Stage 4.3 (Field Matching via XSD) é a fonte de verdade para label/dynamic~~ | — | ✅ **RESOLVIDO v3.15 (G5-S4)** | Se `semantic == "likely_dynamic"` e XSD match confidence ≥ 0.7 → confirma `dynamic`. Se `semantic == "label"` com XSD match → warning (não override). `block_classifications_confirmed` no contrato |
| ~~PA5-S4~~ | ~~Operador não vê motivo da classificação (smart_signals)~~ | — | ✅ **RESOLVIDO v3.15 (G7-S4)** | `smart_signals` propagado nos field_mappings. Frontend FieldDetailPanel exibe como "Classificação automática" com sinais formatados. Zero custo (dados já existem no Stage 3) |
| ~~PA6-S5~~ | ~~VariationMatrix não é produzida — editor espera `matrix: {layoutId → docId → present}`~~ | — | ✅ **RESOLVIDO v3.16 (G5-S5)** | Sub-step 5.5 transforma `block_classifications[].variant` + `present_in_pdfs` em VariationMatrix + Detections. `result_json.multi_doc` alimenta `multiDocStore.populateFromPipeline()`. Frontend `loadFromPipelineResult` conectado |

---

### 6.7 Ordem de Execução Interna

```
2.1 Full Text Extraction ──► page.rect + span["flags"] + text_blocks
    │
    ├── 2.2 Text Reconstruction ──► merge spans (threshold proporcional)
    │       │
    │       └── 2.3 Font → CSS ──► CSSFont com FONT_MAP expandido
    │
    ├── 2.4 Image Extraction ──► imagens filtradas (sem masks) + bbox validado
    │
    ├── 2.5 Screenshot Rendering ──► PNG SÓ representativas, alpha=False
    │
    ├── 2.6 Grid Detection ──► Jenks Natural Breaks (excluindo header/footer)
    │       │
    │       └── 2.7 Table Detection ──► find_tables() com ruling lines
    │               │
    │               └── 2.8 Table Structuring ──► cells com bbox, multi-page merge
    │
    └── (2.9 XSD Parsing MOVIDO para Stage 4.1 — v3.12)

2.9 Extraction Quality Check ──► validar output (text + tabelas), gerar warnings
```

**Paralelismo possível:** 2.4 (Image) e 2.5 (Screenshot) são independentes entre si e de 2.2/2.3. Podem rodar em paralelo com 2.2→2.3.

---

## 7. Stage 3 — Detalhamento Técnico Completo (v3.14)

### Princípio: Se Stage 3 classifica errado, o template sai errado

O Stage 3 transforma dados brutos em **compreensão semântica**. Labels errados → campos invertidos no template. Hierarquia errada → seções misturadas. Document type errado → structural_hints inapplicáveis.

### Redesign v3.14: 7 sub-steps → 4 sub-steps

A auditoria identificou **9 gaps** no design original:
- Dependência circular entre 3.1 e 3.2 (G1-S3)
- Visual Analysis opcional no final em vez de obrigatório no início (G6-S3, G7-S3, G9-S3)
- 3 sub-steps (3.2, 3.3, 3.4) que são uma única passada no código (G3-S3)
- Document Type sem algoritmo definido (G5-S3)
- Label-value pairing ausente (G4-S3)
- Hierarchy Builder com thresholds fixos (G7-S3, G8-S3)

### 7.1 Sub-step 3.1 — Multi-Example Analysis (algorítmico + NER)

**Pergunta:** "O que é label, o que é dynamic, o que é estável, o que é variante?"

Consolida os antigos Stages 12 (Layout Alignment), 13 (Multi-Example Analysis), 14 (Stability Classification) e 15 (Variant Detection) em **uma única passada** sobre `_raw_text_blocks`.

**v3.14:** Adicionada camada de NER (spaCy) + regex para detectar campos dinâmicos que a análise estatística não consegue distinguir — como datas, valores, CPF/CNPJ que são idênticos entre amostras, ou cenários single-PDF onde não há variação para comparar.

#### 3 camadas de detecção (em cascata)

| Camada | Método | Custo | Forte quando... | Fraco quando... |
|--------|--------|-------|-----------------|-----------------|
| 1. Estatística | Comparação de textos entre páginas/PDFs | Zero | Multi-PDF com variação nos valores | Valores iguais entre amostras ou single-PDF |
| 2. Regex | Patterns de data, moeda, CPF, CNPJ, CEP, telefone | Zero | Dados estruturados (numéricos, formatados) | Nomes próprios, cidades, endereços |
| 3. spaCy NER | Named Entity Recognition (PER, LOC, ORG) | ~1ms/bloco | Nomes de pessoas, locais, organizações | Termos técnicos, códigos internos |

**Accuracy combinada:**

| Cenário | Só estatística | + Regex + NER | + Stage 4 (XSD) |
|---------|:-:|:-:|:-:|
| Multi-PDF com variação | ~95% | ~98% | ~99% |
| Multi-PDF sem variação | ~60% | ~85% | ~99% |
| Single-PDF | ~0% | ~70-80% | ~99% |

```python
import re
import spacy

nlp = spacy.load("pt_core_news_lg")  # modelo português, ~50MB, carregado 1x

# === CAMADA 2: Regex patterns para dados estruturados ===
_DYNAMIC_PATTERNS = [
    (r'\d{2}[/.-]\d{2}[/.-]\d{4}', "date", 0.8),
    (r'R\$\s*[\d.,]+', "currency", 0.9),
    (r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', "cnpj", 0.95),
    (r'\d{3}\.\d{3}\.\d{3}-\d{2}', "cpf", 0.95),
    (r'\d{5}-?\d{3}', "cep", 0.85),
    (r'\(\d{2}\)\s*\d{4,5}-\d{4}', "phone", 0.9),
    (r'\d+[.,]\d{2}$', "decimal", 0.7),
]

# === CAMADA 2+3: Classificação inteligente por conteúdo ===
def _smart_classify(text):
    """Analisa o conteúdo do texto para detectar se parece dinâmico.

    Retorna (is_likely_dynamic: bool, confidence_adjustment: float, signals: list)
    """
    signals = []

    # Sinais de LABEL (negativos = empurra para label)
    if text.rstrip().endswith(":"):
        signals.append(("ends_colon", -0.4))
    if len(text.strip()) < 20 and not any(c.isdigit() for c in text):
        signals.append(("short_no_digits", -0.2))

    # CAMADA 2: Regex — detecta dados estruturados
    for pattern, name, weight in _DYNAMIC_PATTERNS:
        if re.search(pattern, text):
            signals.append((f"regex_{name}", weight))

    # CAMADA 3: spaCy NER — detecta entidades nomeadas
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ("PER", "LOC", "ORG"):
            signals.append((f"ner_{ent.label_}", 0.7))
        elif ent.label_ == "MISC":
            signals.append((f"ner_misc", 0.4))

    # Score: base 0.5 (incerto), sinais empurram para label (0) ou dynamic (1)
    score = 0.5
    for _, weight in signals:
        score += weight
    score = max(0.0, min(1.0, score))

    if score >= 0.7:
        return True, score, signals    # likely_dynamic
    elif score <= 0.3:
        return False, score, signals   # label
    else:
        return None, score, signals    # incerto — Stage 4 decide via XSD


def stage_3_1_multi_example_analysis(clusters, raw_text_blocks):
    """3.1 — Classifica cada posição: label/dynamic + stable/variable + required/optional/conditional.

    3 camadas em cascata:
    1. Estatística — comparação de textos entre páginas/PDFs
    2. Regex — patterns de data, moeda, CPF, CNPJ, CEP, telefone
    3. spaCy NER — nomes de pessoas, locais, organizações

    Sem LLM. spaCy roda local (~1ms/bloco, ~50ms para doc de 50 blocos).
    """
    all_classifications = {}  # cluster_id → [classification]

    for cluster in clusters:
        position_map = {}

        for page_info in cluster["pages"]:
            page_key = f"{page_info['pdf_id']}:{page_info['page_index']}"
            page_blocks = raw_text_blocks.get(page_key, [])

            for block in page_blocks:
                pos_key = (round(block["x_center"], 2), round(block["y_center"], 2))
                if pos_key not in position_map:
                    position_map[pos_key] = {"texts": [], "pages": [], "pdf_ids": set()}

                position_map[pos_key]["texts"].append(block["text"])
                position_map[pos_key]["pages"].append(page_key)
                position_map[pos_key]["pdf_ids"].add(page_info["pdf_id"])

        total_pages = len(cluster["pages"])
        total_pdfs = len({p["pdf_id"] for p in cluster["pages"]})
        classifications = []

        for pos_key, info in position_map.items():
            presence_ratio = len(info["pages"]) / total_pages
            unique_texts = set(info["texts"])
            pdf_coverage = len(info["pdf_ids"]) / total_pdfs if total_pdfs > 0 else 1.0
            representative_text = info["texts"][0]  # texto da primeira ocorrência

            c = {
                "position": pos_key,
                "presence_ratio": presence_ratio,
                "pdf_coverage": pdf_coverage,
                "sample_texts": list(unique_texts)[:5],
            }

            # === CAMADA 1: Estatística ===
            if len(unique_texts) == 1:
                c["semantic"] = "label"
                c["confidence"] = 1.0
            elif len(unique_texts) == len(info["pages"]):
                c["semantic"] = "dynamic"
                c["confidence"] = 0.95
            else:
                c["semantic"] = "semi_dynamic"
                c["confidence"] = 0.80

            # === CAMADA 2+3: Smart override (NER + regex) ===
            # Se estatística disse "label" mas conteúdo parece dinâmico → rebaixar
            if c["semantic"] == "label":
                is_dynamic, smart_score, signals = _smart_classify(representative_text)
                if is_dynamic:
                    c["semantic"] = "likely_dynamic"
                    c["confidence"] = smart_score
                    c["smart_signals"] = [s[0] for s in signals]
                elif is_dynamic is None:  # incerto
                    c["confidence"] = 0.50  # rebaixar confiança — Stage 4 decide
                    c["smart_signals"] = [s[0] for s in signals]

            # Stability
            if presence_ratio >= 0.90:
                c["stability"] = "stable"
            elif presence_ratio >= 0.10:
                c["stability"] = "variable"
            else:
                c["stability"] = "rare"

            # Variant
            if presence_ratio < 0.90 and pdf_coverage < 1.0:
                c["variant"] = "conditional"
                c["present_in_pdfs"] = list(info["pdf_ids"])
            elif presence_ratio < 0.90:
                c["variant"] = "optional"
            else:
                c["variant"] = "required"

            classifications.append(c)

        # === classification_quality — meta sobre a força da classificação ===
        has_variation = any(len(set(info["texts"])) > 1 for info in position_map.values())
        if total_pdfs == 1:
            strength = "none"
        elif has_variation:
            strength = "strong"
        else:
            strength = "weak"

        smart_count = sum(1 for c in classifications if c.get("smart_signals"))
        uncertain_count = sum(1 for c in classifications if c.get("confidence", 1.0) < 0.70)

        all_classifications[cluster["cluster_id"]] = {
            "classifications": classifications,
            "classification_quality": {
                "total_pdfs": total_pdfs,
                "total_pages_in_cluster": total_pages,
                "statistical_strength": strength,
                "smart_override_count": smart_count,
                "uncertain_count": uncertain_count,
            }
        }

    return all_classifications
```

**Exemplo de override NER/regex:**
```python
# Cenário: 3 boletos do mesmo dia, mesma empresa
# Estatística vê textos iguais → classifica como "label"
# Smart override corrige:

"Banco XYZ"    → spaCy detecta ORG   → likely_dynamic (0.70)
"15/03/2026"   → regex detecta date  → likely_dynamic (0.80)
"R$ 150,00"    → regex detecta currency → likely_dynamic (0.90)
"12.345.678/0001-90" → regex detecta CNPJ → likely_dynamic (0.95)
"Nome:"        → ends_colon (-0.4)   → label (0.10) ✅ mantém

# Single-PDF: estatística é cega (tudo "label"), NER/regex salva ~70-80%
# O que sobra incerto → Stage 4 resolve via XSD (fonte de verdade)
```

**Dependência:** `spacy` + modelo `pt_core_news_lg` (~50MB). Carregado 1x na inicialização do pipeline. Custo por documento: ~50ms (50 blocos × ~1ms).

### 7.2 Sub-step 3.2 — Visual Analysis (GPT-4o, obrigatório)

**Pergunta:** "Como a IA visual interpreta esta página?"

Consolida os antigos Stages 20 (Visual Segmentation), 21 (Visual Interpretation) e 22 (Vision Self-Check) em **1 chamada GPT-4o por página representativa** (era 3 chamadas separadas).

```python
_VISUAL_ANALYSIS_PROMPT = """\
Analyze this document page image. Return ONLY valid JSON with:

1. "regions": visual regions with bbox and type
2. For each region: "html_suggestion" (representative HTML snippet)
3. For chart_area: identify "chart_type" (bar|line|pie|doughnut|polarArea) and "confidence" (0-100)
4. For barcode_area: identify "barcode_format" (CODE128|CODE39|EAN13|EAN8|UPC|ITF|MSI) and "confidence" (0-100)
5. Compare your visual analysis against this programmatic extraction:
   {extraction_summary}

   Provide a "consistency_score" (0-100).

JSON structure:
{
  "regions": [
    {
      "type": "header|body|footer|sidebar|table_area|chart_area|barcode_area|image_area",
      "bbox": [x0, y0, x1, y1],
      "description": "brief description of content",
      "html_suggestion": "<suggested HTML for this region>",
      "chart_type": "bar",           // only for chart_area
      "barcode_format": "CODE128",   // only for barcode_area
      "confidence": 85               // only for chart_area and barcode_area
    }
  ],
  "consistency_score": 85,
  "consistency_notes": "brief notes on discrepancies"
}
"""

async def stage_3_2_visual_analysis(enriched_documents, clusters, vision_client):
    """3.2 — Visual Analysis. 1 chamada GPT-4o por representativa.

    OBRIGATÓRIO. Se falha: 1 retry automático → checkpoint operador.
    """
    visual_analysis = {}

    for cluster in clusters:
        rep = cluster["representative_page"]
        page_key = f"{rep['pdf_id']}:{rep['page_index']}"
        page_data = _get_page_data(enriched_documents, rep)

        if not page_data or not page_data.get("screenshot_path"):
            continue

        extraction_summary = _summarize_extraction(page_data)
        screenshot_b64 = _load_screenshot_b64(page_data["screenshot_path"])

        prompt = _VISUAL_ANALYSIS_PROMPT.replace("{extraction_summary}", extraction_summary)

        try:
            response = await vision_client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_b64}"}}
                    ]
                }],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            score = result.get("consistency_score", 0)

            visual_analysis[page_key] = {
                "regions": result.get("regions", []),
                "consistency_score": score,
                "consistency_level": "consistent" if score >= 80 else ("partial" if score >= 50 else "inconsistent")
            }
        except Exception as e:
            # 1 retry automático
            # Se falha de novo → checkpoint (operador: retry / continuar sem Vision / cancelar)
            raise VisionCheckpointError(page_key, str(e))

    return visual_analysis
```

**Se operador continua sem Vision:**
- `visual_analysis` = null
- Warning em `extraction_warnings`
- Hierarchy Builder (3.5) usa fallback: thresholds adaptativos (header 0-15%, footer 85-100%) + drawn_elements + gap proporcional
- Document Type Detection (3.4) funciona sem visual (usa texto + labels)
- Stage 5 gera template sem html_suggestion (só extração programática)
- **Qualidade estimada: ~75%** (vs ~95% com Vision)

### 7.3 Sub-step 3.3 — Semantic Classification + Label-Value Pairing (algorítmico)

**Pergunta:** "Qual é o papel semântico de cada bloco e quais blocos formam pares?"

Combina Semantic Analysis (antigo Stage 19) com Intelligence Normalization (antigo Stage 16). Enriquecido com sinais de 3.1 e 3.2.

```python
def stage_3_3_semantic_classification(enriched_documents, position_classifications, visual_analysis):
    """3.3 — Classifica blocos e pareia label+value.

    Algorítmico. Sem LLM.

    Sinais usados (em ordem de confiança):
    1. intelligence de 3.1 (label/dynamic com ~95% accuracy multi-PDF)
    2. visual_regions de 3.2 (header/footer/body zones)
    3. Cor do texto (header blue, footer gray)
    4. Font size (maior → title, menor → footer)
    5. Posição vertical (top → header, bottom → footer)
    """
    block_classifications = {}

    for doc in enriched_documents:
        for page in doc["pages"]:
            if not page.get("is_representative"):
                continue

            for block in page["text_blocks"]:
                block_id = block["id"]

                # 1. Mapear posição → classification do 3.1
                pos_class = _find_position_match(
                    block["bbox"], page["width"], page["height"],
                    position_classifications
                )

                # 2. Determinar zona via visual_regions (se disponível)
                page_key = f"{doc['pdf_id']}:{page['page_index']}"
                zone = _get_visual_zone(block["bbox"], visual_analysis, page_key)
                if zone is None:
                    zone = _get_zone_by_threshold(block["bbox"], page["height"])

                # 3. Classificar semantic_label (header/footer/title/label/value/paragraph)
                semantic_label = _classify_block(block, pos_class, zone)
                block["semantic_label"] = semantic_label

                # 4. Construir block_classification
                block_classifications[block_id] = {
                    "semantic": pos_class["semantic"] if pos_class else "unknown",
                    "stability": pos_class["stability"] if pos_class else "unknown",
                    "variant": pos_class["variant"] if pos_class else "required",
                    "presence_ratio": pos_class["presence_ratio"] if pos_class else 1.0,
                    "pdf_coverage": pos_class["pdf_coverage"] if pos_class else 1.0,
                    "confidence": pos_class["confidence"] if pos_class else 0.50,
                    "field_pair": None  # preenchido abaixo
                }

            # 5. Label-Value Pairing — para cada label, encontrar o value adjacente
            labels = [b for b in page["text_blocks"] if block_classifications.get(b["id"], {}).get("semantic") == "label"]
            dynamics = [b for b in page["text_blocks"] if block_classifications.get(b["id"], {}).get("semantic") in ("dynamic", "semi_dynamic", "likely_dynamic")]

            for label_block in labels:
                pair = _find_adjacent_value(label_block, dynamics, page["width"], page["height"])
                if pair:
                    block_classifications[label_block["id"]]["field_pair"] = pair["id"]
                    block_classifications[pair["id"]]["field_pair"] = label_block["id"]
                    label_block["field_pair"] = pair["id"]
                    pair["field_pair"] = label_block["id"]

    return block_classifications

def _find_adjacent_value(label_block, dynamics, page_width, page_height):
    """Encontra o value mais próximo ao label.

    Prioridade:
    1. À direita do label (mesma linha Y, ±5pts)
    2. Abaixo do label (mesmo X, ±10pts)

    v3.14: threshold "abaixo" proporcional (3.5% da altura) em vez de 30pts fixo.
    """
    lx0, ly0, lx1, ly1 = label_block["bbox"]
    below_threshold = page_height * 0.035  # 3.5% da altura (era 30pts fixo)
    best = None
    best_dist = float('inf')

    for d in dynamics:
        if d.get("field_pair"):  # já pareado
            continue
        dx0, dy0, dx1, dy1 = d["bbox"]

        # À direita: mesmo Y (±5pts), X logo depois do label
        if abs(dy0 - ly0) < 5 and dx0 > lx1 and dx0 - lx1 < page_width * 0.4:
            dist = dx0 - lx1
            if dist < best_dist:
                best, best_dist = d, dist

        # Abaixo: mesmo X (±10pts), Y logo abaixo do label
        elif abs(dx0 - lx0) < 10 and dy0 > ly1 and dy0 - ly1 < below_threshold:
            dist = dy0 - ly1 + 1000  # penalizar para preferir "à direita"
            if dist < best_dist:
                best, best_dist = d, dist

    return best
```

**Impacto no Stage 4.2 (Pair Validation):**
O Stage 4.2 muda de "descobrir pares por adjacência" para "validar pares que Stage 3 já detectou + parear os que sobraram". Complexidade reduzida, menos erros.

### 7.4 Sub-step 3.4 — Hierarchy Builder (algorítmico)

**Pergunta:** "Como os blocos se organizam em árvore?"

```python
def stage_3_4_hierarchy_builder(enriched_documents, block_classifications, visual_analysis,
                                 clusters):
    """3.4 — Constrói árvore hierárquica: document > page > zones > sections > fields.

    Algorítmico. Sem LLM.

    4 sinais em cascata para definir zonas e seções:
    1. Visual regions (GPT-4o) — bbox real de header/body/footer
    2. drawn_elements — linhas horizontais como separadores de seção
    3. grid_info — column_positions para multi-coluna
    4. Gap proporcional — fallback: gap > 2.5% da altura = nova seção
    """
    document_trees = {}

    for cluster in clusters:
        rep = cluster["representative_page"]
        page_key = f"{rep['pdf_id']}:{rep['page_index']}"
        page_data = _get_page_data(enriched_documents, rep)
        page_height = page_data["height"]

        # === PASSO 1: Determinar zonas ===
        va = visual_analysis.get(page_key) if visual_analysis else None

        if va and va.get("regions"):
            # Sinal 1: Visual regions (melhor)
            zones = _zones_from_visual_regions(va["regions"], page_data)
        else:
            # Fallback: thresholds adaptativos
            zones = _zones_from_thresholds(page_data, header_pct=0.15, footer_pct=0.85)

        # === PASSO 2: Separar seções dentro de cada zona ===
        for zone in zones:
            blocks_in_zone = zone["blocks"]

            # Sinal 2: drawn_elements (linhas horizontais = separador forte)
            h_lines = _get_horizontal_separators(page_data.get("drawn_elements", []), zone["bbox"])

            if h_lines:
                sections = _split_by_drawn_lines(blocks_in_zone, h_lines)
            else:
                # Sinal 4: Gap proporcional (fallback)
                gap_threshold = page_height * 0.025  # 2.5% da altura
                sections = _split_by_gap(blocks_in_zone, gap_threshold)

            # Sinal 3: Multi-coluna
            grid_info = page_data.get("grid_info")
            if grid_info and grid_info["columns"] > 1:
                sections = _apply_column_split(sections, grid_info["column_positions"])

            zone["sections"] = sections

        # === PASSO 3: Distribuir imagens e charts nas seções (v3.14) ===
        _assign_images_to_sections(zones, page_data.get("images", []))
        _assign_visual_elements_to_sections(zones, visual_analysis, page_key)

        # === PASSO 4: Construir árvore ===
        tree = _build_tree(cluster["cluster_id"], zones, block_classifications, page_data)
        document_trees[cluster["cluster_id"]] = tree

    return document_trees

def _build_tree(cluster_id, zones, block_classifications, page_data):
    """Constrói TreeNode hierárquico a partir de zonas e seções."""
    root = {
        "id": f"root-{cluster_id}",
        "type": "document",
        "children": [{
            "type": "page",
            "children": []
        }]
    }
    page_node = root["children"][0]

    for zone in zones:
        zone_node = {
            "type": zone["type"],  # header | flow | footer
            "source": zone["source"],  # visual | threshold | drawn
            "children": []
        }

        for section in zone["sections"]:
            section_node = {
                "type": "section",
                "name": section.get("name"),
                "variant": _section_variant(section["blocks"], block_classifications),
                "children": []
            }

            # Agrupar blocos: label+value pareados → nó field com 2 filhos
            for block in section["blocks"]:
                bc = block_classifications.get(block["id"], {})

                if bc.get("field_pair") and bc["semantic"] == "label":
                    # Label com par → criar nó field com label + value
                    pair_block = _find_block(page_data, bc["field_pair"])
                    field_node = {
                        "type": "field",
                        "variant": bc["variant"],
                        "children": [
                            {"type": "label", "block_id": block["id"], "text": block["text"]},
                            {"type": "value", "block_id": pair_block["id"], "text": pair_block["text"]}
                        ]
                    }
                    section_node["children"].append(field_node)
                elif bc.get("field_pair") and bc["semantic"] != "label":
                    continue  # value já incluído via seu label pair
                else:
                    # Bloco solto (sem par) — incluir diretamente
                    section_node["children"].append({
                        "type": bc.get("semantic", "unknown"),
                        "block_id": block["id"],
                        "text": block["text"],
                        "variant": bc.get("variant", "required")
                    })

            # Tabelas → nó table
            for table in section.get("tables", []):
                section_node["children"].append({
                    "type": "table",
                    "table_id": table["table_id"],
                    "children": [
                        {"type": "header_row", "children": _table_header_nodes(table)},
                        {"type": "data_row", "children": _table_data_nodes(table)}
                    ]
                })

            # v3.14: Imagens → nó image (Stage 2 extrai com bbox)
            for img in section.get("images", []):
                section_node["children"].append({
                    "type": "image",
                    "image_path": img["path"],
                    "bbox": img["bbox"],
                    "bbox_valid": img.get("bbox_valid", True),
                    "format": img.get("format", "unknown")
                })

            # v3.14: Charts → nó chart (Visual Analysis detecta como chart_area)
            for chart in section.get("charts", []):
                section_node["children"].append({
                    "type": "chart",
                    "bbox": chart["bbox"],
                    "description": chart.get("description", ""),
                    "chart_type": chart.get("chart_type", "bar"),     # bar|line|pie|doughnut|polarArea
                    "confidence": chart.get("confidence", 50),
                    "source": "visual_analysis"
                })

            # v3.14: Barcodes → nó barcode (Visual Analysis detecta como barcode_area)
            for barcode in section.get("barcodes", []):
                section_node["children"].append({
                    "type": "barcode",
                    "bbox": barcode["bbox"],
                    "description": barcode.get("description", ""),
                    "barcode_format": barcode.get("barcode_format", "CODE128"),  # CODE128|EAN13|etc
                    "confidence": barcode.get("confidence", 50),
                    "source": "visual_analysis"
                })

            # Seção condicional: se TODOS os filhos são conditional, seção inteira é conditional
            if section_node["variant"] == "conditional":
                section_node["present_in_pdfs"] = _get_conditional_pdfs(section["blocks"], block_classifications)

            zone_node["children"].append(section_node)

        page_node["children"].append(zone_node)

    return root

def _section_variant(blocks, block_classifications):
    """Determina variant da seção baseado nos filhos.

    Se todos são conditional → seção conditional
    Se algum é optional → seção tem optional
    Senão → required
    """
    variants = [block_classifications.get(b["id"], {}).get("variant", "required") for b in blocks]
    if all(v == "conditional" for v in variants):
        return "conditional"
    elif any(v in ("optional", "conditional") for v in variants):
        return "optional"
    return "required"

def _assign_images_to_sections(zones, images):
    """v3.14: Distribui imagens do Stage 2 nas seções por posição (bbox).

    Cada imagem vai para a seção cuja bbox mais se sobrepõe.
    Se nenhuma seção cobre a imagem, vai para a seção mais próxima.
    """
    for img in images:
        ix0, iy0, ix1, iy1 = img["bbox"]
        img_cy = (iy0 + iy1) / 2
        best_section = None
        best_overlap = 0

        for zone in zones:
            for section in zone.get("sections", []):
                if not section.get("blocks"):
                    continue
                sy0 = min(b["bbox"][1] for b in section["blocks"])
                sy1 = max(b["bbox"][3] for b in section["blocks"])
                overlap = max(0, min(iy1, sy1) - max(iy0, sy0))
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_section = section

        if best_section is None:
            # Fallback: primeira seção da zona que contém o centro Y da imagem
            for zone in zones:
                zx0, zy0, zx1, zy1 = zone["bbox"]
                if zy0 <= img_cy <= zy1 and zone.get("sections"):
                    best_section = zone["sections"][0]
                    break

        if best_section:
            best_section.setdefault("images", []).append(img)

def _assign_visual_elements_to_sections(zones, visual_analysis, page_key):
    """v3.14: Converte regiões visuais do GPT-4o em charts e barcodes para as seções.

    GPT-4o detecta:
    - chart_area → nó chart com chart_type (bar/line/pie/doughnut/polarArea)
    - barcode_area → nó barcode com barcode_format (CODE128/EAN13/etc)
    """
    va = visual_analysis.get(page_key) if visual_analysis else None
    if not va or not va.get("regions"):
        return

    visual_elements = [r for r in va["regions"] if r.get("type") in ("chart_area", "barcode_area")]
    for region in visual_elements:
        rx0, ry0, rx1, ry1 = region["bbox"]
        region_cy = (ry0 + ry1) / 2

        for zone in zones:
            zx0, zy0, zx1, zy1 = zone["bbox"]
            if zy0 <= region_cy <= zy1:
                for section in zone.get("sections", []):
                    if region["type"] == "chart_area":
                        section.setdefault("charts", []).append({
                            "bbox": region["bbox"],
                            "description": region.get("description", ""),
                            "chart_type": region.get("chart_type", "bar"),
                            "confidence": region.get("confidence", 50),
                        })
                    elif region["type"] == "barcode_area":
                        section.setdefault("barcodes", []).append({
                            "bbox": region["bbox"],
                            "description": region.get("description", ""),
                            "barcode_format": region.get("barcode_format", "CODE128"),
                            "confidence": region.get("confidence", 50),
                        })
                    break  # primeira seção da zona
                break
```

### 7.5 Ordem de Execução Stage 3

```
3.1 Multi-Example Analysis ──► position_classifications (por cluster)
    │                            (estatística + regex + spaCy NER)
    │
    ├── 3.2 Visual Analysis ──► visual_analysis {regions, html_suggestion, consistency_score}
    │                            (GPT-4o, 1 chamada por representativa, ~6 chamadas)
    │
    └──► 3.3 Semantic Classification ──► block_classifications + label-value pairs
             │                            (algorítmico, consome 3.1 + 3.2)
             │
             └──► 3.4 Hierarchy Builder ──► document_trees (por layout)
                                            (algorítmico, consome tudo acima)
```

**Paralelismo possível:** 3.1 e 3.2 são independentes (3.1 usa _raw_text_blocks, 3.2 usa screenshots). Podem rodar em paralelo. 3.3 depende de ambos. 3.4 depende de 3.3.

**document_type:** Produzido pelo `pipeline_result.py` existente via keyword matching (boleto, nota-fiscal, recibo, documento-geral). Não é sub-step do Stage 3.

### 7.6 Fallback sem Visual Analysis

Se o operador escolheu continuar sem Vision (GPT-4o indisponível):

| Componente | Com Vision | Sem Vision (fallback) |
|------------|-----------|----------------------|
| Zonas | Visual regions (bbox real) | Thresholds adaptativos (header 0-15%, footer 85-100%) |
| Seções | Visual + drawn_elements + gap | drawn_elements + gap proporcional |
| html_suggestion | Disponível por região | Indisponível |
| consistency_score | Validação cruzada | Sem validação |
| **Qualidade estimada** | **~95%** | **~75%** |

### 7.7 LLM Usage — Controle e Custo

| Sub-step | LLM | Modelo | Chamadas/job | Custo/job | Fallback |
|----------|-----|--------|:---:|---:|---|
| 3.1 | Não (spaCy local) | pt_core_news_lg | 0 API | $0 | Sem NER: só estatística (~60% single-PDF) |
| 3.2 | **Sim** | GPT-4o Vision | ~6 | ~$0.06-0.18 | 1 retry → checkpoint (sem Vision) |
| 3.3 | Não | — | 0 | $0 | — |
| 3.4 | Não | — | 0 | $0 | — |
| **Total** | | | **~6** | **~$0.06-0.18** | |

**Regra: LLM mais barata que resolve o problema.** GPT-4o SÓ onde precisa ver imagem. Algorítmico quando possível. Document type = keyword matching (zero LLM).

---

## 7b. Stage 4 — Implementação Detalhada (v3.15)

### 7b.1 Sub-step 4.1 — XSD Parsing (lxml)

**Sem mudança funcional.** `xsd_parser.py` existente está correto. Renumerar de Stage 29 para sub-step 4.1.

### 7b.2 Sub-step 4.2 — Pair Validation (algorítmico)

**Pergunta:** "Os pares label-value do Stage 3.3 estão corretos? Sobrou alguém sem par?"

```python
def stage_4_2_pair_validation(block_classifications, enriched_documents, clusters):
    """4.2 — Valida pares do Stage 3.3 e pareia blocos soltos restantes.

    NÃO re-descobre labels do zero. Consome field_pair do Stage 3.3.

    Passos:
    1. Validar pares existentes (label + value adjacentes?)
    2. Identificar blocos sem par (dynamic/likely_dynamic/semi_dynamic sem field_pair)
    3. Tentar parear blocos soltos por adjacência (mesma lógica do Stage 3.3)
    4. Retornar lista de pares validados por layout
    """
    validated_pairs = {}  # layout_type_id → [pairs]

    for cluster in clusters:
        layout_id = cluster["cluster_id"]
        pairs = []
        unpaired_dynamics = []

        for block_id, bc in block_classifications.get(layout_id, {}).items():
            if bc.get("field_pair"):
                # Par já detectado pelo Stage 3.3 — validar adjacência
                pair_id = bc["field_pair"]
                pair_bc = block_classifications[layout_id].get(pair_id, {})

                # Validação: um deve ser label/semi_dynamic, outro dynamic/likely_dynamic
                is_valid = (
                    bc["semantic"] in ("label",) and
                    pair_bc.get("semantic") in ("dynamic", "semi_dynamic", "likely_dynamic")
                ) or (
                    bc["semantic"] in ("dynamic", "semi_dynamic", "likely_dynamic") and
                    pair_bc.get("semantic") in ("label",)
                )

                if is_valid and bc["semantic"] == "label":
                    pairs.append({
                        "label_block_id": block_id,
                        "value_block_id": pair_id,
                        "label_text": _get_block_text(enriched_documents, block_id),
                        "value_text": _get_block_text(enriched_documents, pair_id),
                        "source": "stage_3",
                        "label_bbox": _get_block_bbox(enriched_documents, block_id),
                        "value_bbox": _get_block_bbox(enriched_documents, pair_id),
                    })
            elif bc.get("semantic") in ("dynamic", "semi_dynamic", "likely_dynamic"):
                unpaired_dynamics.append(block_id)

        # Tentar parear blocos soltos (adjacência simples)
        for block_id in unpaired_dynamics:
            adjacent_label = _find_nearest_label_block(
                block_id, block_classifications[layout_id], enriched_documents
            )
            if adjacent_label:
                pairs.append({
                    "label_block_id": adjacent_label,
                    "value_block_id": block_id,
                    "label_text": _get_block_text(enriched_documents, adjacent_label),
                    "value_text": _get_block_text(enriched_documents, block_id),
                    "source": "stage_4_adjacency",
                    "label_bbox": _get_block_bbox(enriched_documents, adjacent_label),
                    "value_bbox": _get_block_bbox(enriched_documents, block_id),
                })
            else:
                # Bloco dinâmico sem label → incluir como solo (sem label_text)
                pairs.append({
                    "label_block_id": None,
                    "value_block_id": block_id,
                    "label_text": "",
                    "value_text": _get_block_text(enriched_documents, block_id),
                    "source": "stage_4_solo",
                    "label_bbox": None,
                    "value_bbox": _get_block_bbox(enriched_documents, block_id),
                })

        validated_pairs[layout_id] = pairs

    return validated_pairs
```

### 7b.3 Sub-step 4.3 — Format Pre-Detection (algorítmico, REORDENADO)

**Pergunta:** "Qual o formato de cada valor ANTES de tentar mapear?"

```python
# Mesmos patterns do Stage 24 existente. Movido para ANTES do Field Matching
# para que o formato enriqueça o prompt LLM.
#
# Input: validated_pairs (do 4.2)
# Output: validated_pairs enriquecidos com detected_format + format_functions

def stage_4_3_format_pre_detection(validated_pairs):
    """4.3 — Detecta formato do value ANTES do Field Matching.

    O formato é um hint poderoso para o LLM:
    - "15/03/2026" (date_numeric) → campo XSD tipo date
    - "R$ 1.234,56" (currency_brl) → campo XSD tipo decimal
    - "123.456.789-01" (cpf) → campo com nome "cpf"

    Sem LLM. Regex puro.
    """
    format_functions = {}

    for layout_id, pairs in validated_pairs.items():
        for pair in pairs:
            fmt = detect_format(pair["value_text"])
            pair["detected_format"] = fmt
            if fmt and fmt not in format_functions:
                format_functions[fmt] = _JS_FUNCTIONS[fmt]

    return validated_pairs, format_functions
```

### 7b.4 Sub-step 4.4 — Section↔XSD Matching (algorítmico, NOVO)

**Pergunta:** "Qual nó complexo do XSD corresponde a cada seção da document_tree?"

```python
def stage_4_4_section_xsd_matching(document_trees, field_tree):
    """4.4 — Cruza seções do document_trees com nós complexos do XSD.

    Sem LLM. Algorítmico: difflib + heurísticas.

    Estratégia em cascata:
    1. Nome da seção vs nome do nó XSD (difflib similarity)
    2. Contagem de filhos compatível (seção com 3 campos ↔ nó XSD com 3+ filhos)
    3. Formato dos filhos (seção com campo CPF → nó XSD com filho tipo "cpf")

    Output: mapa {section_name → xsd_node_path} + candidatos XSD por seção.
    """
    xsd_complex_nodes = _get_complex_nodes(field_tree)
    section_xsd_map = {}  # layout_id → {section_name → {"xsd_node": path, "child_paths": [...]}}

    for layout_id, tree in document_trees.items():
        section_map = {}

        for section in _extract_sections(tree):
            section_name = section.get("name", "")
            section_fields = [c for c in section.get("children", [])
                              if c.get("type") in ("field", "label", "dynamic")]

            best_node = None
            best_score = 0.0

            for xsd_node in xsd_complex_nodes:
                score = _section_xsd_similarity(section, xsd_node)
                if score > best_score:
                    best_score = score
                    best_node = xsd_node

            if best_node and best_score >= 0.3:
                # Seção mapeada → campos desta seção só competem com filhos deste nó
                section_map[section_name] = {
                    "xsd_node": best_node["path"],
                    "xsd_score": best_score,
                    "child_paths": [c["path"] for c in best_node.get("children", [])],
                }
            else:
                # Seção sem match → campos competem contra TODOS os XSD paths (fallback)
                section_map[section_name] = {
                    "xsd_node": None,
                    "xsd_score": 0.0,
                    "child_paths": field_tree.get("flat_paths", []),
                }

        section_xsd_map[layout_id] = section_map

    return section_xsd_map


def _section_xsd_similarity(section, xsd_node):
    """Score de similaridade entre seção do documento e nó complexo do XSD.

    3 sinais ponderados:
    1. Nome (0.5): difflib entre nome da seção e nome do nó XSD
    2. Contagem de filhos (0.3): proporção filhos seção vs filhos XSD
    3. Formato match (0.2): filhos com formato detectado compatível com tipo XSD
    """
    import difflib

    # Sinal 1: Nome
    section_name = (section.get("name") or "").lower().replace(" ", "").replace("_", "")
    xsd_name = xsd_node["name"].lower().replace("_", "")
    name_score = difflib.SequenceMatcher(None, section_name, xsd_name).ratio()

    # Sinal 2: Contagem de filhos
    section_count = len([c for c in section.get("children", [])
                         if c.get("type") in ("field", "label", "dynamic")])
    xsd_count = len(xsd_node.get("children", []))
    if xsd_count > 0 and section_count > 0:
        count_score = min(section_count, xsd_count) / max(section_count, xsd_count)
    else:
        count_score = 0.0

    # Sinal 3: Formato match (se seção tem CPF e nó XSD tem filho "cpf")
    section_formats = {c.get("detected_format") for c in section.get("children", [])
                       if c.get("detected_format")}
    xsd_child_names = {c["name"].lower() for c in xsd_node.get("children", [])}
    format_overlap = len(section_formats & xsd_child_names) / max(1, len(section_formats))
    format_score = format_overlap

    return name_score * 0.5 + count_score * 0.3 + format_score * 0.2


def _get_complex_nodes(field_tree):
    """Extrai nós complexos (que têm filhos) do FieldTree."""
    if not field_tree:
        return []
    result = []
    def _walk(nodes):
        for node in nodes:
            if node.get("children"):
                result.append(node)
            _walk(node.get("children", []))
    _walk(field_tree.get("root_nodes", []))
    return result
```

### 7b.5 Sub-step 4.5 — Field Matching (Batch LLM + Two-Pass)

**Pergunta:** "Qual campo XSD corresponde a cada par label-value?"

```python
GEMINI_FLASH_MODEL = "google/gemini-2.0-flash-001"
AMBIGUITY_THRESHOLD = 0.1

# v3.15: Prompt enriquecido com seção XSD + formato detectado
_BATCH_MATCH_PROMPT = """\
You are an XSD field mapper for document extraction.

Below are label-value pairs extracted from a document section.
{section_context}

Map each pair to the best matching XSD field path from the candidates below.

Pairs:
{pairs_json}

Available XSD fields (scoped to this section):
{xsd_paths}

Return a JSON object with key 'mappings': a list of objects, each with:
- 'pair_index' (int): index of the pair (0-based)
- 'candidates': list of up to 3 objects with 'path' (XSD field) and 'score' (float 0-1)
Return only valid JSON.
"""

async def stage_4_5_field_matching(validated_pairs, field_tree, block_classifications,
                                    section_xsd_map, openrouter_client):
    """4.5 — Batch Field Matching com Section Scoping + Two-Pass.

    v3.15 Melhorias estruturais:
    1. Section↔XSD: cada campo só compete com filhos do nó XSD mapeado à sua seção
    2. Format hints: prompt LLM inclui formato detectado (date, cpf, currency)
    3. Two-pass: pass 1 aceita ≥0.7, pass 2 re-ranqueia ambíguos sem paths já usados

    PA4: Se likely_dynamic + XSD match confidence ≥ 0.7 → confirma dynamic.
    """
    flat_paths = field_tree.get("flat_paths", []) if field_tree else []
    field_mappings = []
    ambiguous_fields = []
    confirmations = {}

    for layout_id, pairs in validated_pairs.items():
        if not pairs or not flat_paths:
            for pair in pairs:
                field_mappings.append(_make_mapping_v315(
                    block_id=pair["value_block_id"], layout_type_id=layout_id,
                    pdf_text=pair["value_text"], label_text=pair["label_text"],
                    xsd_field_path="", confidence=0.0, is_ambiguous=False,
                    candidates=[], bbox=pair["value_bbox"],
                ))
            continue

        layout_section_map = section_xsd_map.get(layout_id, {})

        # === BATCH LLM por seção: prompt scoped com hints ===
        # Agrupar pares por seção para enviar prompts menores e mais precisos
        section_groups = _group_pairs_by_section(pairs, layout_section_map)

        all_results = {}  # pair_index → candidates

        for section_name, group in section_groups.items():
            scoped_paths = layout_section_map.get(section_name, {}).get("child_paths", flat_paths)
            xsd_node = layout_section_map.get(section_name, {}).get("xsd_node")

            section_context = (
                f"This section is mapped to XSD node '{xsd_node}'. "
                f"Focus on its children."
            ) if xsd_node else "No section mapping available. Use all XSD fields."

            # Enriquecer com formato detectado (Melhoria 2)
            pairs_json = [
                {
                    "index": p["original_index"],
                    "label": p["label_text"],
                    "value": p["value_text"],
                    "detected_format": p.get("detected_format"),  # hint do 4.3
                }
                for p in group
            ]

            if openrouter_client:
                batch = await _llm_batch_match_scoped(
                    pairs_json, scoped_paths, section_context, openrouter_client
                )
            else:
                batch = _fuzzy_batch_match(pairs_json, scoped_paths)

            all_results.update(batch)

        # === PASS 1: Aceitar matches de alta confiança ===
        used_paths = set()
        pass1_mappings = []

        for i, pair in enumerate(pairs):
            candidates = all_results.get(i, [])
            best = candidates[0] if candidates else None

            if best and best["score"] >= 0.7:
                used_paths.add(best["path"])
                pass1_mappings.append((i, pair, candidates, False))  # not ambiguous
            else:
                pass1_mappings.append((i, pair, candidates, True))   # needs pass 2

        # === PASS 2: Re-ranquear ambíguos sem paths já usados ===
        for i, pair, candidates, needs_pass2 in pass1_mappings:
            if needs_pass2 and candidates:
                # Filtrar candidatos já usados por matches de alta confiança
                filtered = [c for c in candidates if c["path"] not in used_paths]
                if filtered:
                    candidates = filtered

            best = candidates[0] if candidates else None
            is_ambiguous = False
            if best and len(candidates) >= 2:
                if candidates[0]["score"] - candidates[1]["score"] < AMBIGUITY_THRESHOLD:
                    is_ambiguous = True
                    ambiguous_fields.append(best["path"])

            xsd_path = best["path"] if best else ""
            confidence = best["score"] if best else 0.0

            # --- PA4: XSD confirma likely_dynamic → dynamic ---
            bc = block_classifications.get(layout_id, {}).get(pair["value_block_id"], {})
            smart_signals = bc.get("smart_signals")
            semantic_confirmed = None

            if bc.get("semantic") == "likely_dynamic" and confidence >= 0.7:
                semantic_confirmed = "dynamic"
                confirmations[pair["value_block_id"]] = {
                    "original_semantic": "likely_dynamic",
                    "confirmed_semantic": "dynamic",
                    "xsd_path": xsd_path,
                    "xsd_confidence": confidence,
                }
            elif bc.get("semantic") == "label" and confidence >= 0.7:
                semantic_confirmed = None  # warning, não override

            xsd_type = _get_xsd_type(field_tree, xsd_path) if xsd_path else None

            field_mappings.append(_make_mapping_v315(
                block_id=pair["value_block_id"],
                layout_type_id=layout_id,
                pdf_text=pair["value_text"],
                label_text=pair["label_text"],
                xsd_field_path=xsd_path,
                xsd_type=xsd_type,
                confidence=confidence,
                is_ambiguous=is_ambiguous,
                candidates=candidates,
                bbox=pair["value_bbox"],
                is_table_cell=bc.get("is_table_cell", False),
                from_table=bc.get("from_table", False),
                smart_signals=smart_signals,
                semantic_confirmed=semantic_confirmed,
                detected_format=pair.get("detected_format"),
            ))

    return field_mappings, ambiguous_fields, confirmations


async def _llm_batch_match_scoped(pairs_json, scoped_paths, section_context, openrouter_client):
    """1 chamada LLM para pares de uma seção, com paths scoped e format hints."""
    paths_str = "\n".join(f"- {p}" for p in scoped_paths[:40])
    prompt = _BATCH_MATCH_PROMPT.format(
        section_context=section_context,
        pairs_json=json.dumps(pairs_json, ensure_ascii=False),
        xsd_paths=paths_str,
    )
    messages = [{"role": "user", "content": prompt}]

    completion = await _call_with_retry(openrouter_client, messages=messages,
                                         model=GEMINI_FLASH_MODEL,
                                         response_format={"type": "json_object"})
    raw = completion.choices[0].message.content or "{}"
    data = json.loads(strip_markdown_fences(raw))

    result = {}
    for m in data.get("mappings", []):
        idx = m.get("pair_index", -1)
        candidates = [{"path": c["path"], "score": float(c["score"])}
                      for c in m.get("candidates", []) if "path" in c]
        result[idx] = candidates
    return result
```

### 7b.6 Sub-step 4.7 — Consistency Validation: Tipo↔Formato (algorítmico)

**Validação tipo↔formato movida para 4.7 (Consistency Validation).** Adição v3.15:

```python
# v3.15: Compatibilidade XSD type ↔ detected_format
_TYPE_FORMAT_COMPAT = {
    "date":    {"date_numeric", "date_extenso"},
    "decimal": {"currency_brl", "percentage"},
    "integer": {"percentage"},
    "string":  {"cpf", "cnpj", "phone", "currency_brl", "date_numeric",
                "date_extenso", "percentage"},  # string aceita tudo
    "boolean": set(),  # boolean não tem formato detectável
}

def _validate_type_format(field_mappings, warnings):
    """v3.15: Cruzar XSD type com detected_format. Warning se incompatível."""
    mismatches = []
    for m in field_mappings:
        xsd_type = m.get("xsd_type")
        fmt = m.get("detected_format")
        if not xsd_type or not fmt:
            continue
        compatible = _TYPE_FORMAT_COMPAT.get(xsd_type, {"string"})
        if fmt not in compatible:
            mismatches.append({
                "block_id": m["block_id"],
                "xsd_type": xsd_type,
                "detected_format": fmt,
                "xsd_path": m["xsd_field_path"],
            })
            warnings.append(
                f"type_format_mismatch: '{m['xsd_field_path']}' é {xsd_type} no XSD "
                f"mas detected_format é {fmt}"
            )
    return mismatches
```

### 7b.7 Sub-step 4.6 — Confidence Scoring (heurísticas, sem LLM)

**Pergunta:** "Quanto confiamos no mapeamento deste layout?"

```python
WEIGHTS = {
    "layout_stability": 0.25,
    "anchor_detection": 0.25,
    "grid_quality": 0.20,
    "field_variability": 0.15,
    "vision_agreement": 0.15,
}

def stage_4_6_confidence_scoring(field_mappings, intelligence, visual_analysis,
                                  classification_quality, clusters):
    """4.6 — Confidence Scoring per-layout. Heurísticas determinísticas.

    v3.15: Claude Sonnet REMOVIDO. Substituído por regras heurísticas.
    PA1: smart_signals + classification_quality ajustam field_variability.
    PA2: consistency_score → vision_agreement (já implementado).
    """
    confidence_scores = {}

    for cluster in clusters:
        layout_id = cluster["cluster_id"]
        layout_mappings = [m for m in field_mappings if m["layout_type_id"] == layout_id]

        # --- Fatores base ---
        factors = {
            "layout_stability": _get_layout_stability(intelligence, layout_id),
            "anchor_detection": _get_anchor_detection(layout_mappings),
            "grid_quality": _get_grid_quality_for_layout(cluster),
            "field_variability": _get_field_variability(intelligence, layout_id),
            "vision_agreement": _get_vision_agreement(visual_analysis, cluster),
        }

        # --- HEURÍSTICA 1: Tabular + low anchor → não penalizar ---
        # Boletos/tabelas têm poucos labels mas grid forte
        if factors["anchor_detection"] < 0.4 and factors["grid_quality"] >= 0.7:
            factors["anchor_detection"] = max(factors["anchor_detection"], 0.6)

        # --- HEURÍSTICA 2 (PA1): smart_signals → ajustar field_variability ---
        cq = classification_quality.get(layout_id, {})
        if cq.get("smart_override_count", 0) > 0:
            # Classificação teve overrides NER/regex → menos certeza
            factors["field_variability"] = max(0.0, factors["field_variability"] - 0.10)
        if cq.get("statistical_strength") == "none":
            # Single-PDF → penalizar (não tem comparação estatística)
            factors["field_variability"] = max(0.0, factors["field_variability"] - 0.15)
        elif cq.get("statistical_strength") == "strong":
            # Multi-PDF com variação → mais confiança
            factors["field_variability"] = min(1.0, factors["field_variability"] + 0.10)

        # --- HEURÍSTICA 3: Muitos ambíguos → penalizar ---
        ambiguous_ratio = sum(1 for m in layout_mappings if m["is_ambiguous"]) / max(1, len(layout_mappings))
        if ambiguous_ratio > 0.3:
            factors["anchor_detection"] = max(0.0, factors["anchor_detection"] - 0.1)

        # --- Weighted average ---
        overall = sum(WEIGHTS[k] * factors[k] for k in WEIGHTS)
        overall = round(overall, 4)

        # --- Status ---
        if overall >= 0.95:
            status = "approved"
        elif overall >= 0.80:
            status = "review_recommended"
        else:
            status = "human_review_required"

        confidence_scores[layout_id] = {
            **factors,
            "overall": round(overall * 100),
            "status": status,
        }

    return confidence_scores
```

### 7b.8 Sub-step 4.7 — Consistency Validation + Reverse Mapping (algorítmico)

```python
def stage_4_7_consistency_validation(field_mappings, field_tree, document_trees,
                                      block_classifications, type_format_mismatches):
    """4.7 — Validação de consistência. Consome document_trees (v3.15).

    Checks:
    1. Skeleton vs result: blocos dynamic no block_classifications devem ter mapping
    2. XSD coverage: todos os flat_paths devem ser mapeados ou reportados
    3. Orphan mappings: xsd_field_path deve existir em flat_paths
    4. v3.15 NOVO: Reverse mapping — campos XSD required sem mapping
    5. v3.15 NOVO: type_format_mismatches do 4.4
    """
    flat_paths = field_tree.get("flat_paths", []) if field_tree else []
    flat_paths_set = set(p for p in flat_paths if p)

    warnings = []
    errors = []

    # 1. Skeleton vs result — usando block_classifications (não parsed_documents)
    dynamic_count = sum(
        1 for layout_bc in block_classifications.values()
        for bc in layout_bc.values()
        if bc.get("semantic") in ("dynamic", "semi_dynamic", "likely_dynamic")
    )
    mapped_count = len([m for m in field_mappings if m["xsd_field_path"]])
    if dynamic_count > 0 and mapped_count < dynamic_count:
        warnings.append(
            f"skeleton_vs_result: {dynamic_count - mapped_count} bloco(s) dinâmico(s) "
            f"sem field_mapping ({mapped_count}/{dynamic_count} mapeados)"
        )

    # 2. XSD coverage
    mapped_paths = {m["xsd_field_path"] for m in field_mappings if m["xsd_field_path"]}
    unmapped_xsd = [p for p in flat_paths if p not in mapped_paths]
    if unmapped_xsd:
        warnings.append(
            f"xsd_coverage: {len(unmapped_xsd)} campo(s) XSD sem mapping: "
            + ", ".join(unmapped_xsd[:10])
        )

    # 3. Orphan mappings
    orphan_count = 0
    for m in field_mappings:
        path = m.get("xsd_field_path", "")
        if path and path not in flat_paths_set:
            orphan_count += 1
            errors.append(f"orphan_mapping: '{path}' não existe no field_tree")

    # 4. v3.15: Reverse mapping — campos XSD REQUIRED sem mapping
    required_paths = _get_required_paths(field_tree)
    unmapped_required = [p for p in required_paths if p not in mapped_paths]
    if unmapped_required:
        warnings.append(
            f"required_unmapped: {len(unmapped_required)} campo(s) XSD obrigatório(s) "
            f"sem mapping: " + ", ".join(unmapped_required[:10])
        )

    # 5. v3.15: Incorporar type_format_mismatches
    for mismatch in type_format_mismatches:
        warnings.append(
            f"type_format_mismatch: '{mismatch['xsd_path']}' "
            f"XSD={mismatch['xsd_type']} vs format={mismatch['detected_format']}"
        )

    return {
        "warnings": warnings,
        "errors": errors,
        "orphan_count": orphan_count,
        "unmapped_xsd_fields": unmapped_xsd,
        "unmapped_required_xsd_fields": unmapped_required,
        "type_format_mismatches": type_format_mismatches,
    }


def _get_required_paths(field_tree):
    """Extrai flat_paths de campos com required=True no FieldTree."""
    if not field_tree:
        return []
    required = []
    def _walk(nodes):
        for node in nodes:
            if node.get("required", True):
                required.append(node["path"])
            _walk(node.get("children", []))
    _walk(field_tree.get("root_nodes", []))
    return required
```

### 7b.9 Ordem de Execução Stage 4

```
4.1 XSD Parsing ──► field_tree (flat_paths + root_nodes + complex_nodes)
    │
    └──► 4.2 Pair Validation ──► validated_pairs (por layout)
              │                   consome field_pair do Stage 3.3
              │
              ├── 4.3 Format Pre-Detection ──► pairs + detected_format (hints)
              │                                 regex ANTES do matching
              │
              └── 4.4 Section↔XSD Matching ──► section_xsd_map
                       │                        seções da tree → nós XSD complexos
                       │                        reduz search space (~80 → ~3-5)
                       │
                       └──► 4.5 Field Matching ──► field_mappings + confirmations
                                 │                  batch LLM scoped (seção + formato)
                                 │                  two-pass (elimina paths usados)
                                 │                  PA4 (likely_dynamic → dynamic)
                                 │
                                 ├── 4.6 Confidence Scoring ──► confidence_scores (per-layout)
                                 │                               heurísticas (PA1)
                                 │
                                 └── 4.7 Consistency Validation ──► validation_result
                                                                     tipo↔formato + reverse
```

**Paralelismo:** 4.3 e 4.4 podem rodar em paralelo (ambos dependem de 4.2, são independentes). 4.5 depende de ambos. 4.6 e 4.7 podem rodar em paralelo (ambos dependem de 4.5).

### 7b.10 LLM Usage — Stage 4

| Sub-step | LLM | Modelo | Chamadas/job | Custo/job | Fallback |
|----------|-----|--------|:---:|---:|---|
| 4.1 | Não | lxml | 0 | $0 | — |
| 4.2 | Não | — | 0 | $0 | — |
| 4.3 | Não | regex | 0 | $0 | — |
| 4.4 | Não | difflib | 0 | $0 | — |
| 4.5 | **Sim** | Gemini 2.0 Flash | ~4 (1/layout, scoped) | ~$0.01 | Similaridade de texto (qualidade ~60%) |
| 4.6 | **Não** (v3.15) | heurísticas | 0 | $0 | ~~Claude Sonnet~~ removido |
| 4.7 | Não | — | 0 | $0 | — |
| **Total** | | | **~4** | **~$0.01** | |

**Redução vs AS-IS:** ~60 chamadas → ~4 (93% menos). Custo: ~$0.30 → ~$0.01.
**Section scoping:** prompts menores (3-5 paths vs 80) = tokens menores = custo menor.
**Claude Sonnet removido:** weighted average + heurísticas determinísticas ($0, testável).
**Two-pass:** reduz ambiguidades em ~50-70%, $0 extra (algorítmico).

---

## 8. Stage 5 — Template Generation (v3.16 Auditado)

### 8.1 Sub-step 5.1 — Tree-Driven HTML Generation

**Mudança estrutural:** Em vez de iterar `field_mappings[]` flat e gerar `<span>` por campo,
o HTML é gerado por **walk recursivo** de `document_trees` (Stage 3.4).

A árvore já contém: seções → label-value pairs → campos → variantes condicionais → tabelas.

**Problema no código AS-IS:**
```python
# template_draft.py:303 — DESCARTA tabelas silenciosamente
if mapping.get("is_table_cell") or mapping.get("from_table"):
    continue  # ← 100% do conteúdo tabular perdido

# Conditional sections vazias:
lines.append(f"    <!-- ko if: {condition} -->")
lines.append(f"    <!-- /ko -->")  # ← nada dentro

# Todos os fields em todas as páginas (sem filtro por layout):
for mapping in field_mappings:  # ← não filtra por layout_type_id
```

**Proposta v3.16:** Walk recursivo de `document_trees`:

```python
def stage_5_1_tree_driven_html(document_trees, field_mappings, field_tree,
                                 layout_types):
    """5.1 — Gera HTML hierárquico por walk de document_trees.

    document_trees já tem seções, label-value pairs, condicionais, tabelas.
    field_mappings enriquece com xsd_field_path e data-bind.
    """
    template_draft = {}  # layout_id → {"html": str, "css": str}

    for layout in layout_types:
        layout_id = layout["id"]
        tree = document_trees.get(layout_id)
        if not tree:
            continue

        # Filtrar mappings deste layout
        layout_mappings = [m for m in field_mappings
                           if m.get("layout_type_id") == layout_id]
        mapping_by_block = {m["block_id"]: m for m in layout_mappings if m.get("block_id")}

        html = _walk_tree_to_html(tree, mapping_by_block, field_tree, layout)
        template_draft[layout_id] = {"html": html}

    return template_draft


def _walk_tree_to_html(node, mapping_by_block, field_tree, layout):
    """Recursão: cada tipo de nó gera HTML diferente."""
    node_type = node.get("type")

    if node_type == "document":
        page_height = float(layout.get("page_height_pts", 842.0))
        children_html = "\n".join(
            _walk_tree_to_html(child, mapping_by_block, field_tree, layout)
            for child in node.get("children", [])
        )
        name = layout.get("name", "default").lower().replace(" ", "_")
        return f'<div class="page page-{name}" data-layout-type="{layout["name"]}">\n{children_html}\n</div>'

    elif node_type == "section":
        variant = node.get("variant", "required")
        children_html = "\n".join(
            _walk_tree_to_html(child, mapping_by_block, field_tree, layout)
            for child in node.get("children", [])
        )
        section_name = node.get("name", "")

        if variant == "conditional":
            # Knockout.js conditional section COM conteúdo dentro
            binding = section_name.lower().replace(" ", "_")
            return f'<!-- ko if: {binding} -->\n<div class="section" data-section="{section_name}">\n{children_html}\n</div>\n<!-- /ko -->'

        return f'<div class="section" data-section="{section_name}">\n{children_html}\n</div>'

    elif node_type == "table":
        return _generate_table_html(node, mapping_by_block, field_tree)

    elif node_type == "field":
        block_id = node.get("id", "").replace("block-", "")
        mapping = mapping_by_block.get(block_id, {})
        return _generate_field_element(mapping, field_tree, node)

    elif node_type in ("image", "chart", "barcode"):
        return _generate_media_element(node)

    else:
        # Nó genérico — recurse filhos
        return "\n".join(
            _walk_tree_to_html(child, mapping_by_block, field_tree, layout)
            for child in node.get("children", [])
        )


def _generate_table_html(table_node, mapping_by_block, field_tree):
    """Gera <table> real com Knockout.js foreach."""
    table_id = table_node.get("table_id", "")
    headers = table_node.get("headers", [])
    xsd_array_path = table_node.get("xsd_array_path", "items")

    header_cells = "".join(f"<th>{h}</th>" for h in headers)

    # Determinar colunas mapeadas do XSD
    row_fields = []
    for child in table_node.get("children", []):
        block_id = child.get("id", "").replace("block-", "")
        mapping = mapping_by_block.get(block_id, {})
        path = mapping.get("xsd_field_path", "")
        field_name = path.split(".")[-1] if path else ""
        row_fields.append(field_name)

    body_cells = "".join(
        f'<td data-bind="text: {f}"></td>' if f
        else "<td></td>"
        for f in row_fields
    )

    return f"""<table class="data-table" data-table-id="{table_id}">
  <thead><tr>{header_cells}</tr></thead>
  <tbody>
    <!-- ko foreach: {xsd_array_path} -->
    <tr>{body_cells}</tr>
    <!-- /ko -->
  </tbody>
</table>"""
```

**Resultado:** HTML hierárquico, tabelas reais, condicionais com conteúdo, filtrado por layout.

### 8.2 Sub-step 5.2 — CSS-from-Extraction

**Problema AS-IS:** CSS hardcoded (Arial 10pt, cores fixas, zonas fixas 144px/96px).

**Proposta v3.16:** CSS gerado dos dados extraídos nos Stages 2-3.

```python
def stage_5_2_css_from_extraction(document_trees, enriched_documents,
                                   visual_analysis, drawn_elements):
    """5.2 — Gera CSS a partir dos dados extraídos.

    Fontes: text_blocks[].font_name, font_size → CSS font-family, font-size
    Cores: text_blocks[].color → CSS color
    Backgrounds: drawn_elements[] (retângulos preenchidos) → background-color
    Zonas: visual_analysis.regions[] → header/footer heights dinâmicos
    """
    css_rules = [_BASE_CSS_RESET]  # reset mínimo, não template fixo

    # 1. Zonas de visual_analysis (header/footer heights reais)
    if visual_analysis:
        for region in visual_analysis.get("regions", []):
            region_type = region.get("type")  # "header", "body", "footer"
            bounds = region.get("bounds", {})
            if region_type == "header" and bounds:
                h_px = round(bounds.get("height", 0.12) * 1123)
                css_rules.append(f".header {{ height: {h_px}px; }}")
            elif region_type == "footer" and bounds:
                h_px = round(bounds.get("height", 0.08) * 1123)
                css_rules.append(f".footer {{ height: {h_px}px; }}")

    # 2. Backgrounds de drawn_elements (retângulos preenchidos)
    for elem in (drawn_elements or []):
        if elem.get("type") == "rect" and elem.get("fill_color"):
            color = elem["fill_color"]
            # Associar ao nó mais próximo por bbox overlap
            css_rules.append(f"/* background: {color} for rect at {elem.get('bbox')} */")

    # 3. Font classes das fontes mais usadas
    font_counts = _count_fonts(enriched_documents)
    for font_name, font_size in font_counts.most_common(5):
        safe_name = font_name.lower().replace(" ", "-")
        css_rules.append(
            f".font-{safe_name} {{ font-family: {font_name}, sans-serif; "
            f"font-size: {font_size}pt; }}"
        )

    return "\n".join(css_rules)
```

### 8.3 Sub-step 5.3 — Coverage Multidimensional

**Problema AS-IS:** Só conta fields, tables/images/charts sempre 0.

```python
def stage_5_3_coverage(field_mappings, field_tree, document_trees,
                        enriched_documents, layout_types):
    """5.3 — Coverage multidimensional por layout.

    Pesos: fields 60% + tables 25% + images 15%.
    """
    coverage_by_layout = {}

    for layout in layout_types:
        layout_id = layout["id"]
        tree = document_trees.get(layout_id)

        # Fields
        layout_mappings = [m for m in field_mappings
                           if m.get("layout_type_id") == layout_id]
        flat_paths = field_tree.get("flat_paths", []) if field_tree else []
        mapped_fields = len({m["xsd_field_path"] for m in layout_mappings
                             if m.get("xsd_field_path")})
        total_fields = len(flat_paths) if flat_paths else 0

        # Tables — contar nós type=table na document_tree
        total_tables = _count_nodes_by_type(tree, "table")
        mapped_tables = _count_mapped_tables(tree, layout_mappings)

        # Images — contar nós type=image
        total_images = _count_nodes_by_type(tree, "image")
        mapped_images = _count_images_with_binding(tree)

        # Charts — contar nós type=chart
        total_charts = _count_nodes_by_type(tree, "chart")

        # Percentage weighted
        f_pct = (mapped_fields / total_fields * 100) if total_fields else 0
        t_pct = (mapped_tables / total_tables * 100) if total_tables else 100
        i_pct = (mapped_images / total_images * 100) if total_images else 100
        percentage = round(f_pct * 0.6 + t_pct * 0.25 + i_pct * 0.15)

        coverage_by_layout[layout_id] = {
            "fields": {"mapped": mapped_fields, "total": total_fields},
            "tables": {"mapped": mapped_tables, "total": total_tables},
            "images": {"mapped": mapped_images, "total": total_images},
            "charts": {"mapped": 0, "total": total_charts},
            "percentage": percentage,
        }

    return coverage_by_layout
```

### 8.4 Sub-step 5.4 — Overlay Items (per-layout)

**Problema AS-IS:** Mesma lista replicada para todos os layouts.

```python
def stage_5_4_overlay_items(field_mappings, layout_types, page_dims):
    """5.4 — Overlay items FILTRADO por layout_type_id."""
    overlay_by_layout = {}

    for layout in layout_types:
        layout_id = layout["id"]
        layout_mappings = [m for m in field_mappings
                           if m.get("layout_type_id") == layout_id]

        items = []
        for mapping in layout_mappings:
            bbox = mapping.get("bbox")
            if not bbox or len(bbox) < 4:
                continue
            x0, y0, x1, y1 = [float(v) for v in bbox]
            page_num = int(mapping.get("page_number", 0))
            page_w, page_h = page_dims.get(page_num, (595.0, 842.0))
            scale_x = 794.0 / page_w
            scale_y = 1123.0 / page_h

            items.append({
                "node_id": mapping.get("block_id"),
                "xsd_path": mapping.get("xsd_field_path"),
                "label": mapping.get("label_text", ""),
                "value": mapping.get("pdf_text", ""),
                "status": mapping.get("status", "unmapped"),
                "page_number": page_num,
                "bbox_canvas": {
                    "left": round(x0 * scale_x, 1),
                    "top": round((page_h - y1) * scale_y, 1),
                    "width": round((x1 - x0) * scale_x, 1),
                    "height": round((y1 - y0) * scale_y, 1),
                },
                "bbox_pdf": {
                    "left": round(x0, 1), "top": round(y0, 1),
                    "width": round(x1 - x0, 1), "height": round(y1 - y0, 1),
                },
            })

        overlay_by_layout[layout_id] = items

    return overlay_by_layout
```

### 8.5 Sub-step 5.5 — VariationMatrix Assembly (PA6)

**Resolve PA6-S5.**

```python
def stage_5_5_variation_matrix(block_classifications, clusters, layout_types):
    """5.5 — Monta VariationMatrix de block_classifications.

    block_classifications[block_id] = {
        "variant": "required"|"optional"|"conditional",
        "present_in_pdfs": ["0", "2"],  # só se conditional
        ...
    }

    clusters[].pages[].pdf_id → mapeamento pdf_id ↔ layout_id

    Output: VariationMatrix + Detections + PdfDocument[]
    """
    # 1. Construir pdfs[] dos clusters
    all_pdf_ids = set()
    layout_pdf_map = {}  # layout_id → set(pdf_ids)
    for cluster in clusters:
        layout_id = cluster.get("cluster_id")
        pdf_ids = {p.get("pdf_id") for p in cluster.get("pages", []) if p.get("pdf_id")}
        all_pdf_ids |= pdf_ids
        layout_pdf_map[layout_id] = pdf_ids

    # 1b. Determinar "base" = PDF presente em mais clusters (mais completo)
    pdf_cluster_coverage = {}  # pdf_id → quantos clusters contém páginas dele
    for cluster in clusters:
        contributing = {p.get("pdf_id") for p in cluster.get("pages", []) if p.get("pdf_id")}
        for pid in contributing:
            pdf_cluster_coverage[pid] = pdf_cluster_coverage.get(pid, 0) + 1

    # PDF com maior cobertura = base. Empate: primeiro por ordem de upload (sorted)
    base_pdf_id = max(sorted(all_pdf_ids), key=lambda pid: pdf_cluster_coverage.get(pid, 0))

    pdfs = [
        {"id": pid, "name": f"document-{pid}",
         "role": "base" if pid == base_pdf_id else "variation",
         "sizeKB": 0, "pages": 0, "uploadedAt": ""}
        for pid in sorted(all_pdf_ids)
    ]

    # 2. Construir cells: layoutId → pdfId → present
    layout_ids = [lt["id"] for lt in layout_types]
    variation_ids = sorted(all_pdf_ids)

    cells = {}
    for layout_id in layout_ids:
        cells[layout_id] = {}
        for pdf_id in variation_ids:
            cells[layout_id][pdf_id] = pdf_id in layout_pdf_map.get(layout_id, set())

    matrix = {
        "layoutIds": layout_ids,
        "variationIds": variation_ids,
        "cells": cells,
    }

    # 3. Gerar Detections de block_classifications
    detections = []
    for block_id, classification in block_classifications.items():
        variant = classification.get("variant", "required")
        if variant == "required":
            continue  # Só gerar detections para optional/conditional

        present_in = classification.get("present_in_pdfs", [])
        det_type = "conditional_section" if variant == "conditional" else "optional_field"

        detections.append({
            "id": f"det-{block_id}",
            "pdfId": present_in[0] if present_in else "",
            "type": det_type,
            "description": f"Bloco presente em {len(present_in)}/{len(all_pdf_ids)} PDFs",
            "confidence": len(present_in) / len(all_pdf_ids) if all_pdf_ids else 0,
            "nodeBinding": block_id,
        })

    return {"pdfs": pdfs, "matrix": matrix, "detections": detections}
```

### 8.6 Sub-step 5.6 — PipelineResult Assembly

**Consolida tudo numa única estrutura para o frontend.**

```python
def stage_5_6_pipeline_result(context, template_draft, css_global,
                               coverage_by_layout, overlay_by_layout, multi_doc):
    """5.6 — Monta result_json completo.

    DIFERENÇAS vs AS-IS (pipeline_result.py):
    1. trees_by_layout: de document_trees (Stage 3), não de parsed_documents
    2. template_draft: monolítico (layout ativo) — G21-S5
    3. overlay_items: filtrado por layout_type_id + hierarquia tabelas (G22)
    4. intelligence: block_classifications incluído
    5. validation_result: do Stage 4 incluído
    6. block_classifications_confirmed: PA4 incluído
    7. multi_doc: VariationMatrix + Detections (PA6)
    8. confidence normalizada 0-100 todos os fatores (G18)
    9. layout_types[] com documentTree/confidence/coverage embutidos (G19)
    """
    document_trees = context.get("document_trees", {})
    layout_types = context.get("layout_types", [])

    # trees_by_layout: árvores hierárquicas do Stage 3.4
    trees_by_layout = {}
    for lt in layout_types:
        layout_id = lt.get("id")
        tree = document_trees.get(layout_id)
        if tree:
            trees_by_layout[layout_id] = _convert_tree_to_css_coords(tree, lt)

    # root: backward compat — primeira árvore
    first_layout_id = layout_types[0]["id"] if layout_types else None
    root = trees_by_layout.get(first_layout_id)

    # G18-S5: Normalizar TODOS os fatores de confidence para 0-100
    normalized_confidence = _normalize_confidence(
        context.get("confidence_scores", {}), layout_types)

    # G19-S5: Embutir estado per-layout nos layout_types
    enriched_layout_types = []
    for lt in layout_types:
        layout_id = lt.get("id")
        enriched = dict(lt)
        if layout_id in trees_by_layout:
            enriched["documentTree"] = {"root": trees_by_layout[layout_id]}
        if layout_id in coverage_by_layout:
            enriched["coverage"] = coverage_by_layout[layout_id]
        if layout_id in normalized_confidence:
            enriched["confidence"] = normalized_confidence[layout_id]
        enriched_layout_types.append(enriched)

    # G21-S5: template_draft monolítico (layout ativo / primeiro)
    monolithic_draft = template_draft.get(first_layout_id, {"html": "", "css": ""})

    result_json = {
        "document_structure": {
            "pages": _serialise_parsed_documents(context.get("parsed_documents", [])),
            "layout_types": enriched_layout_types,
            "root": root,
            "trees_by_layout": trees_by_layout,
        },
        "field_mappings": context.get("field_mappings", []),
        "confidence_scores": normalized_confidence,   # G18: tudo 0-100
        "coverage": coverage_by_layout,
        "layout_types": enriched_layout_types,        # G19: com documentTree/confidence/coverage
        "template_draft": {                           # G21: monolítico
            "html": monolithic_draft.get("html", ""),
            "css": css_global,                        # CSS é global (fonts/cores do template)
        },
        "ambiguous_fields": [m for m in context.get("field_mappings", [])
                             if m.get("is_ambiguous")],
        "format_functions": context.get("format_functions", {}),
        "overlay_items": overlay_by_layout,           # G22: com overlay_type
        "document_type": _get_document_type(context),
        "document_type_confidence": context.get("document_type_confidence", 0.0),
        "visual_analysis": context.get("visual_analysis"),
        "intelligence": context.get("intelligence"),
        "validation_result": context.get("validation_result"),
        "block_classifications_confirmed": context.get("block_classifications_confirmed"),
        "multi_doc": multi_doc,                       # PA6
        "page_config": _build_page_config(context),   # G17-S5 — paginação
    }

    context["result_json"] = result_json
    return result_json
```

### 8.7 Sub-step 5.7 — Persistência com Checkpoint

**Princípio:** Nenhuma decisão que comprometa o resultado sem avisar o operador.

```python
async def stage_5_7_persist(context, result_json, job):
    """5.7 — Persiste result_json no Supabase com Checkpoint em caso de falha.

    NÃO é try/except silencioso como no AS-IS.
    """
    supabase = context.get("supabase_client")
    job_id = context.get("job_id")

    if not supabase or not job_id:
        return  # sem Supabase configurado — ok (dev/local)

    try:
        await _persist_to_supabase(supabase, job_id, result_json)
    except Exception as e:
        decision = await handle_service_failure(
            context=context,
            service_name="Supabase",
            stage_name="Template Generation",
            error=e,
            fallback_description="Continuar sem salvar — resultado ficará apenas em memória",
            impact_description="Se a sessão for encerrada, o resultado será perdido",
            job=job,
            timeout=300
        )
        if decision == "retry":
            await stage_5_7_persist(context, result_json, job)
        # else: operador aceitou continuar sem persistência
```

### 8.8 Frontend — loadFromPipelineResult atualizado

```typescript
// session.ts — ADICIONAR multiDocStore à lista de stores
async loadFromPipelineResult(result: PipelineResult) {
  // ... stores existentes ...
  const { useMultiDocStore } = await import('./multiDocStore')
  const multiDocStore = useMultiDocStore()

  // Adicionar ao storeLoaders:
  {
    name: 'multiDocStore',
    fn: () => {
      if (result.multi_doc) {
        multiDocStore.populateFromPipeline(result.multi_doc)
      }
    }
  },

  // trees_by_layout: carregar árvore do layout ativo
  {
    name: 'templateStore (trees_by_layout)',
    fn: () => {
      if (result.document_structure?.trees_by_layout) {
        const activeId = layoutStore.activeLayoutId
        const tree = result.document_structure.trees_by_layout[activeId]
        if (tree) templateStore.loadTree(tree)
      }
    }
  },

  // G17-S5: page_config → usePagination (substitui hardcoded 80/60)
  {
    name: 'pagination',
    fn: () => {
      if (result.page_config) {
        const { setPageConfig } = usePagination()
        setPageConfig({
          headerHeight: result.page_config.header_height_px,
          footerHeight: result.page_config.footer_height_px,
          size: result.page_config.size,
          orientation: result.page_config.orientation,
        })
      }
    }
  }
}
```

### 8.9 Ordem de Execução — Stage 5

```
5.1 Tree-Driven HTML ──┐
                        ├── 5.3 Coverage ──┐
5.2 CSS-from-Extraction ┘                  │
                                           ├── 5.6 PipelineResult ── 5.7 Persist
5.4 Overlay Items ─────────────────────────┤
                                           │
5.5 VariationMatrix ───────────────────────┘
```

**Paralelismo:** 5.1+5.2 podem rodar em paralelo. 5.4 e 5.5 são independentes. 5.3 depende de 5.1.

### 8.10 LLM Usage — Stage 5

| Sub-step | LLM | Modelo | Chamadas/job | Custo/job | Fallback |
|----------|-----|--------|:---:|---:|---|
| 5.1 | Não | algorítmico | 0 | $0 | — |
| 5.2 | Não | algorítmico | 0 | $0 | — |
| 5.3 | Não | algorítmico | 0 | $0 | — |
| 5.4 | Não | algorítmico | 0 | $0 | — |
| 5.5 | Não | algorítmico | 0 | $0 | — |
| 5.6 | Não | algorítmico | 0 | $0 | — |
| 5.7 | Não | Supabase | 0 | $0 | Checkpoint |
| **Total** | | | **0** | **$0** | |

**Stage 5 é 100% algorítmico.** Zero chamadas LLM. Todo o trabalho de IA já foi feito nos Stages 1-4.

### 8.11 Gaps Stage 5 — 17 gaps + 3 melhorias estruturais

| # | Gap | Severidade | Resolve |
|---|-----|-----------|---------|
| G1-S5 | Tabelas ignoradas no HTML (is_table_cell → continue) | **CRÍTICO** | 5.1 Tree-Driven HTML gera `<table>` real |
| G2-S5 | `trees_by_layout` não existe no result_json | **ALTO** | 5.6 PipelineResult inclui trees_by_layout de document_trees |
| G3-S5 | Document tree de parsed_documents flat, não document_trees | **ALTO** | 5.1+5.6 usam document_trees do Stage 3.4 |
| G4-S5 | Coverage só fields, tables/images/charts hardcoded 0 | **MÉDIO** | 5.3 Coverage multidimensional com pesos |
| G5-S5 | PA6: VariationMatrix não produzida | **ALTO** | 5.5 VariationMatrix Assembly |
| G6-S5 | visual_analysis / html_suggestion não usado | **MÉDIO** | 5.2 CSS-from-Extraction usa visual_regions |
| G7-S5 | CSS hardcoded A4, sem fonts/cores do PDF | **MÉDIO** | 5.2 CSS-from-Extraction (fonts, cores, backgrounds) |
| G8-S5 | Overlay items replicado para todos layouts | **ALTO** | 5.4 filtra por layout_type_id |
| G9-S5 | validation_result não passa ao frontend | **MÉDIO** | 5.6 inclui validation_result |
| G10-S5 | block_classifications_confirmed não passa | **MÉDIO** | 5.6 inclui block_classifications_confirmed |
| G11-S5 | intelligence não incluída | **MÉDIO** | 5.6 inclui intelligence |
| G12-S5 | document_type_confidence ausente | **BAIXO** | 5.6 inclui document_type_confidence |
| G13-S5 | Persistência Supabase sem Checkpoint | **MÉDIO** | 5.7 usa handle_service_failure |
| G14-S5 | Conditional sections vazias (ko if sem conteúdo) | **ALTO** | 5.1 walk recursivo coloca filhos dentro do ko if |
| G15-S5 | Field mappings não filtrados por layout | **ALTO** | 5.1+5.4 filtram por layout_type_id |
| G16-S5 | loadFromPipelineResult não chama multiDocStore | **ALTO** | 8.8 adiciona multiDocStore à distribuição |
| G17-S5 | Paginação: Stage 5 não popula metadados que o frontend já consome | **ALTO** | 5.1 enriquece TreeNode header/footer + 5.6 inclui `page_config` |
| G18-S5 | Confidence factors escala inconsistente — overall 0-100, outros 0-1 | **MÉDIO** | 5.6 normaliza TODOS para 0-100 antes de enviar |
| G19-S5 | layout_types[] sem documentTree/confidence/coverage — layout switch quebra | **ALTO** | 5.6 embute per-layout + session.ts pre-popula todos os layouts |
| G20-S5 | PipelineResult type desatualizado — faltam 8 campos novos (v3.16) | **ALTO** | Atualizar pipeline.types.ts com todos os campos novos |
| G21-S5 | template_draft per-layout vs monolítico — generationStore não parseia per-layout | **ALTO** | 5.6 envia monolítico (layout ativo) + árvores em trees_by_layout |
| G22-S5 | Overlay de tabelas: cells individuais vs tabela inteira — sem hierarquia | **MÉDIO** | 5.4 gera ambos: container (tabela) + sub-items (cells, visíveis no hover) |

### 8.12 Melhorias Estruturais Stage 5

| # | Melhoria | Impacto |
|---|----------|---------|
| ME1-S5 | **Tree-Driven HTML** — walk document_trees em vez de field_mappings flat | HTML preserva hierarquia, seções, condicionais, tabelas reais |
| ME2-S5 | **CSS-from-Extraction** — CSS gerado de fonts/cores/backgrounds extraídos | Template preserva aparência visual do PDF original |
| ME3-S5 | **Multi-Doc Pipeline** — result_json.multi_doc conecta multiDocStore | Operador vê tabela de variações, detections, condicionais |

### 8.13 Paginação — G17-S5

**Contexto:** O frontend JÁ resolve paginação em runtime (Stories 9.5 e 9.6):
- `usePagination.ts` — calcula page breaks em tempo real
- `table-pagination.ts` — divide tabelas entre páginas com `repeatHeader`
- `buildHeaderFooterLayout()` — monta quais headers/footers repetem por página
- `SectionInspector.vue` — checkbox "Repetir em cada página" (`repeat_per_page`)

**Problema:** O frontend tem a infraestrutura mas recebe dados hardcoded:
```typescript
// HTMLCanvas.vue — HARDCODED
const headerHeight = 80   // ← deveria vir do visual_analysis
const footerHeight = 60   // ← deveria vir do visual_analysis
const defaultMargins = { top: 40, bottom: 40, left: 40, right: 40 }
```

O Stage 5 não alimenta esses valores.

**Decisão arquitetural:** Paginação é problema de RUNTIME, não de pipeline.
O Stage 5 gera UMA página por layout (correto). O frontend calcula page breaks
quando o conteúdo excede. O Stage 5 só precisa passar os metadados certos.

**Solução — 3 pontos de enriquecimento:**

**1. Tree walk (5.1) — enriquecer nós header/footer:**
```python
def _walk_tree_to_html(node, ...):
    if node_type == "header":
        # Setar properties que o SectionInspector.vue consome
        node["properties"]["section_type"] = "header"
        node["properties"]["repeat_per_page"] = True
        node["properties"]["height"] = _header_height_from_visual(visual_analysis)
        # ...gera HTML da zona header...

    elif node_type == "footer":
        node["properties"]["section_type"] = "footer"
        node["properties"]["repeat_per_page"] = True
        node["properties"]["height"] = _footer_height_from_visual(visual_analysis)
```

**2. Tree walk (5.1) — tabelas com repeat_header:**
```python
def _generate_table_html(table_node, ...):
    # Marcar thead como repetível
    table_node["properties"]["repeat_header"] = True
    # table-pagination.ts já sabe consumir isso
```

**3. PipelineResult (5.6) — incluir `page_config`:**
```python
result_json["page_config"] = {
    "size": _detect_page_size(page_dims),  # "A4" | "letter" | "custom"
    "orientation": "portrait" if w < h else "landscape",
    "header_height_px": header_h,   # do visual_analysis bbox escalado
    "footer_height_px": footer_h,   # do visual_analysis bbox escalado
    "margins": {"top": 10, "bottom": 10, "left": 10, "right": 10}
}

def _header_height_from_visual(visual_analysis):
    """Extrai altura do header da visual_analysis (visual_regions).

    Fallback: 15% da página se visual_analysis indisponível.
    """
    for region in (visual_analysis or {}).values():
        for r in region.get("visual_regions", []):
            if r.get("type") == "header":
                bbox = r.get("bbox", [])
                if len(bbox) == 4:
                    return round((bbox[3] - bbox[1]) * (1123 / 842))  # pts → px
    return round(0.15 * 1123)  # fallback: 15% da página A4
```

**Frontend (session.ts) — consumir page_config:**
```typescript
// Adicionar ao storeLoaders:
{
  name: 'pagination',
  fn: () => {
    if (result.page_config) {
      const { setPageConfig } = usePagination()
      setPageConfig({
        headerHeight: result.page_config.header_height_px,
        footerHeight: result.page_config.footer_height_px,
        size: result.page_config.size,
        orientation: result.page_config.orientation,
      })
    }
  }
}
```

**Risco e fallback:** Se `visual_analysis` estiver null (operador continuou sem Vision),
usa threshold 15% header / 10% footer — melhor que os 80px/60px hardcoded atuais.

**LLM:** Não necessário. Paginação é 100% algorítmica.

### 8.14 Gaps G18-G22 — Integração Pipeline↔Frontend (v3.17)

#### G18-S5: Confidence — Normalizar escala para 0-100

**Problema:** Backend converte `overall` para 0-100 mas deixa os 5 fatores em 0-1. Frontend `ConfidenceFactors` define todos como `number` sem escala documentada. Se exibidos juntos, `layout_stability: 0.85` ao lado de `overall: 87` confunde.

**Solução no sub-step 5.6:**

```python
def _normalize_confidence(raw_scores: dict, layout_types: list) -> dict:
    """Normaliza TODOS os fatores para 0-100 (inteiro).

    Frontend compara >= 95 (approved), >= 80 (review), < 80 (human_review).
    Escala uniforme elimina confusão na exibição.
    """
    normalized = {}
    for lt in layout_types:
        layout_id = lt.get("id", f"layout-{lt.get('cluster_id', 0)}")
        entry = raw_scores.get(layout_id, raw_scores.get("global", {}))
        factors = entry.get("factors", {})
        global_score = entry.get("global_score", 0.0)

        normalized[layout_id] = {
            "layout_stability": round(factors.get("layout_stability", 0) * 100),
            "anchor_detection": round(factors.get("anchor_detection", 0) * 100),
            "grid_quality": round(factors.get("grid_quality", 0) * 100),
            "field_variability": round(factors.get("field_variability", 0) * 100),
            "vision_agreement": round(factors.get("vision_agreement", 0) * 100),
            "overall": round(global_score * 100),
        }

    return normalized
```

**Frontend:** `ConfidenceFactors` interface inalterada — todos os números agora são 0-100.

---

#### G19-S5: layout_types[] — Pre-popular documentTree/confidence/coverage

**Problema:** `session.ts` carrega `trees_by_layout` apenas para o layout ativo. Quando o operador troca de layout (Story 12.9), `layout.ts` tenta restaurar `newLayout.documentTree` que é `undefined`.

**Fluxo quebrado:**
```
Pipeline envia: trees_by_layout = { "layout-0": tree_A, "layout-1": tree_B }
session.ts: templateStore.loadTree(trees_by_layout["layout-0"])  → carrega tree_A
session.ts: layoutStore.loadLayoutTypes(layout_types)            → SEM documentTree!

Operador troca para layout-1:
  layout.ts: salva layout-0.documentTree = tree_A                → OK
  layout.ts: restaura layout-1.documentTree = ???                → UNDEFINED!
```

**Solução no sub-step 5.6 — embutir per-layout:**

```python
# Em stage_5_6_pipeline_result:
enriched_layout_types = []
for lt in layout_types:
    layout_id = lt.get("id")
    enriched = dict(lt)  # copiar dados existentes
    # Embutir estado per-layout
    if layout_id in trees_by_layout:
        enriched["documentTree"] = {"root": trees_by_layout[layout_id]}
    if layout_id in coverage_by_layout:
        enriched["coverage"] = coverage_by_layout[layout_id]
    if layout_id in normalized_confidence:
        enriched["confidence"] = normalized_confidence[layout_id]
    enriched_layout_types.append(enriched)

result_json["layout_types"] = enriched_layout_types
```

**Frontend — session.ts (complementar ao 8.8):**

```typescript
// Após loadLayoutTypes, popular estado per-layout de trees_by_layout
{
  name: 'layoutState',
  fn: () => {
    const trees = result.document_structure?.trees_by_layout
    if (!trees) return
    for (const lt of layoutStore.layoutTypes) {
      if (trees[lt.id]) lt.documentTree = { root: trees[lt.id] }
      if (result.confidence_scores?.[lt.id]) lt.confidence = result.confidence_scores[lt.id]
      if (result.coverage?.[lt.id]) lt.coverage = result.coverage[lt.id]
    }
  }
}
```

**Resultado:** Layout switch funciona desde o primeiro load — cada layout já tem sua árvore, confidence e coverage.

---

#### G20-S5: PipelineResult type — Atualizar com campos v3.16/v3.17

**Problema:** `pipeline.types.ts` falta 8 campos que o Stage 5.6 produz. TypeScript impede acesso sem cast.

**Solução — Atualizar `pipeline.types.ts`:**

```typescript
// Novo tipo para document_structure (substituir DocumentTree direto)
export interface DocumentStructure {
  pages: unknown[]
  layout_types: LayoutType[]
  root: TreeNode
  trees_by_layout?: Record<string, DocumentTree>
}

export interface PageConfig {
  size: string        // "A4" | "letter" | "custom"
  orientation: string // "portrait" | "landscape"
  header_height_px: number
  footer_height_px: number
  margins?: { top: number; bottom: number; left: number; right: number }
}

export interface ValidationResult {
  warnings: string[]
  errors: string[]
  type_format_mismatches?: Array<{ field: string; xsd_type: string; detected_format: string }>
}

export interface PipelineResult {
  document_structure: DocumentStructure               // ← expandido
  field_mappings: FieldMappingEntry[]
  confidence_scores: Record<string, ConfidenceFactors>
  coverage: Record<string, CoverageData>
  layout_types: LayoutType[]
  template_draft: { html: string; css: string }
  ambiguous_fields: AmbiguousField[]
  format_functions: FormatFunction[]
  overlay_items?: Record<string, BackendOverlayItem[]>
  document_type?: string
  // v3.16/v3.17 — campos novos
  document_type_confidence?: number
  validation_result?: ValidationResult
  intelligence?: Record<string, unknown>
  block_classifications_confirmed?: Record<string, unknown>
  multi_doc?: { pdfs: PdfDocument[]; matrix: VariationMatrix; detections: Detection[] }
  page_config?: PageConfig
  visual_analysis?: Record<string, unknown>
}
```

**Importar tipos de multi-doc:**
```typescript
import type { PdfDocument, VariationMatrix, Detection } from './multi-doc.types'
```

---

#### G21-S5: template_draft — Monolítico (layout ativo) + árvores per-layout

**Problema:** Sub-step 5.1 gera HTML per-layout. `generationStore.loadTemplateDraft()` aceita apenas `{html, css}` monolítico. Se enviar dict per-layout, generationStore não parseia.

**Decisão arquitetural:** O HTML é **derivado da árvore** — não precisa ser persistido per-layout. A árvore já está em `trees_by_layout`. Quando o operador troca de layout, o editor pode regenerar o HTML da nova árvore.

**Solução no sub-step 5.6:**

```python
# template_draft no result_json: monolítico (layout ativo / primeiro)
first_layout_id = layout_types[0]["id"] if layout_types else None
monolithic_draft = template_draft.get(first_layout_id, {"html": "", "css": ""})

# CSS é GLOBAL (mesmo CSS para todos os layouts — fonts/cores são do template)
global_css = stage_5_2_css  # já gerado como string

result_json["template_draft"] = {
    "html": monolithic_draft.get("html", ""),
    "css": global_css,
}

# Per-layout HTML fica em trees_by_layout (regenerável pela árvore)
# NÃO duplicar HTML em template_draft
```

**Impacto frontend:** Nenhuma mudança em `generationStore`. Continua recebendo `{html, css}`.

**Quando operador troca layout:** `layout.ts` já recarrega a árvore (G19-S5). O Monaco editor atualiza o HTML do novo layout via tree → HTML sync.

---

#### G22-S5: Overlay de tabelas — Container + cells com hierarquia

**Problema:** Overlay inclui cells individuais de tabela. Operador vê dezenas de retângulos sobrepostos. Sem contexto de "isso é uma tabela".

**Solução no sub-step 5.4:**

```python
def _generate_table_overlay(table_node, mapping_by_block, page_dims, page_num):
    """Gera overlay hierárquico para tabela: container + cells."""
    items = []

    # 1. Container — bbox da tabela inteira
    table_bbox = table_node.get("bbox")
    if table_bbox and len(table_bbox) >= 4:
        table_mapped = any(
            mapping_by_block.get(child.get("id", "").replace("block-", ""))
            for child in table_node.get("children", [])
        )
        items.append({
            "node_id": table_node.get("table_id"),
            "xsd_path": table_node.get("xsd_array_path"),
            "label": f"Tabela: {table_node.get('name', '')}",
            "value": "",
            "status": "mapped" if table_mapped else "unmapped",
            "page_number": page_num,
            "bbox_canvas": _scale_bbox(table_bbox, page_dims, page_num),
            "bbox_pdf": _raw_bbox(table_bbox),
            "overlay_type": "table_container",   # NOVO — frontend pode distinguir
        })

    # 2. Cells — cada coluna mapeada
    for child in table_node.get("children", []):
        block_id = child.get("id", "").replace("block-", "")
        mapping = mapping_by_block.get(block_id, {})
        cell_bbox = child.get("bbox")
        if not cell_bbox or len(cell_bbox) < 4:
            continue

        items.append({
            "node_id": block_id,
            "xsd_path": mapping.get("xsd_field_path", ""),
            "label": mapping.get("label_text", ""),
            "value": mapping.get("pdf_text", ""),
            "status": mapping.get("status", "unmapped"),
            "page_number": page_num,
            "bbox_canvas": _scale_bbox(cell_bbox, page_dims, page_num),
            "bbox_pdf": _raw_bbox(cell_bbox),
            "overlay_type": "table_cell",         # NOVO — hover-only
        })

    return items
```

**Frontend — `BackendOverlayItem` expandido:**

```typescript
export interface BackendOverlayItem {
  node_id: string | null
  xsd_path: string | null
  label: string
  value: string
  status: string
  page_number: number
  bbox_canvas: { left: number; top: number; width: number; height: number }
  bbox_pdf: { left: number; top: number; width: number; height: number }
  overlay_type?: 'field' | 'table_container' | 'table_cell'  // v3.17
}
```

**CoverageOverlay.vue:** Renderizar `table_container` com borda + background semitransparente. `table_cell` renderizar apenas no hover do container. Default: `field` (comportamento atual).

---

## 9. SSE Progress — Adaptação

Com 5 estágios em vez de 28, o SSE precisa reportar sub-progress:

```json
{
  "stage": 1,
  "stage_name": "Layout Clustering",
  "status": "running",
  "progress_pct": 0.15,
  "sub_step": "1.5 Content Abstraction",
  "sub_progress_pct": 0.60,
  "summary": {"pages_processed": 60, "total_pages": 100}
}
```

O frontend pode mostrar:
- **Barra principal:** 5 estágios (20% cada)
- **Sub-barra:** progresso dentro do estágio atual

---

## 10. Performance Estimada

### 100 páginas, 2 templates reais

| Stage | Páginas | Operações | Tempo est. |
|-------|---------|-----------|----------:|
| **1. Layout Clustering** | 100 (leve) | 3 camadas: prevenção + detecção + correção | ~5.5s + $0.003 |
| **2. Deep Extraction** | ~6 (representativas) | get_text("dict") + span flags + page.rect + color + reconstruct + fonts + images + screenshots + find_tables() + get_drawings() + XSD + quality check | ~10s |
| **3. Structural Analysis** | ~6 | multi-example + visual (GPT-4o) + semantic + hierarchy | ~20s (com Vision) / ~5s (sem) |
| **4. Field Mapping** | ~6 | Section scoping + batch LLM (1/layout) + two-pass + heurísticas | ~6s (LLM scoped) / ~2s (fallback) |
| **5. Template Generation** | ~6 | Tree-Driven HTML + CSS-from-Extraction + coverage multidimensional + overlay per-layout + VariationMatrix + PipelineResult + persist | ~3s |
| **TOTAL** | | | **~60s (com Vision+LLM scoped)** |
| | | | **~26s (sem Vision, sem LLM)** |

### Comparação com pipeline atual

| Métrica | AS-IS | Proposta v3 |
|---------|-------|-------------|
| Páginas na deep extraction | 100 | ~6 |
| Chamadas LLM (Field Matching) | ~3000 | ~4 (batch, 1/layout) |
| Chamadas Vision AI | 2-4 | 2-4 (sem mudança) |
| Tempo total (100 páginas) | ~20 min | ~1.5 min |
| Custo API estimado | ~$3-5 | ~$0.08-0.20 |
| Defesas contra erro de clustering | 0 | **15** (3 camadas) |
| LLM validation do clustering | Nenhum | Gemini Flash (~$0.003) |

---

## 11. Estratégia de Implementação

### Abordagem: Refactor incremental, não rewrite

O código existente dos estágios **funciona**. A proposta não é reescrever tudo, mas:
1. **Reorganizar** — mover estágios para dentro dos novos stages como sub-steps
2. **Adicionar** — novos sub-steps que não existem (content abstraction, hierarchy builder, etc.)
3. **Substituir** — apenas onde a abordagem é fundamentalmente diferente (KMeans → Graph clustering)

### Fases

```
FASE 0: Storage Gateway — PRÉ-REQUISITO (antes de qualquer stage novo)
  ├── Motivação: Pipeline atual salva tudo em /tmp (volátil, sem escala,
  │   sem versionamento). Pipeline v3.2 adiciona mais artefatos (thumbnails,
  │   pHash images). Migrar AGORA evita retrabalho posterior.
  ├── Criar StorageGateway abstrato
  │   ├── save_screenshot(job_id, page_key, bytes) → URL
  │   ├── save_asset(job_id, filename, bytes) → URL
  │   ├── save_thumbnail(job_id, page_key, bytes) → URL   ← NOVO Stage 1
  │   ├── get_local_path(job_id, filename) → Path          ← download temp
  │   ├── save_result(job_id, result_json) → None
  │   └── cleanup_local(job_id) → None
  ├── Implementar SupabaseStorageGateway
  │   ├── Upload → Supabase Storage (buckets: jobs/{id}/pdfs|screenshots|assets|thumbnails)
  │   ├── Download → /tmp local (cache para PyMuPDF)
  │   └── Cleanup → rm temp local após pipeline
  ├── Implementar LocalStorageGateway (dev/testes — escolha EXPLÍCITA)
  │   └── Comportamento atual (/tmp) encapsulado. NÃO é fallback de cloud.
  ├── Configurar Supabase
  │   ├── Tabela jobs (existe, tornar result_json obrigatório)
  │   ├── Tabela job_clusters (NOVA — persistir clustering)
  │   ├── Tabela templates (NOVA — persistir templates salvos)
  │   ├── Bucket jobs (Storage — PDFs, screenshots, assets)
  │   └── Bucket templates (Storage — assets de templates)
  ├── Adaptar código existente (7 arquivos):
  │   ├── backend/routers/upload.py        → upload Storage + temp local
  │   ├── backend/routers/analyze.py       → download Storage → temp → cleanup
  │   ├── backend/routers/assets.py        → CRUD via Storage
  │   ├── backend/services/stages/screenshot_generator.py  → save via gateway
  │   ├── backend/services/stages/image_extraction.py      → save via gateway
  │   ├── backend/services/stages/pipeline_result.py       → save DB obrigatório
  │   └── frontend/src/stores/session.ts   → screenshots via signed URL
  └── Resultado: Todos os stages novos usam StorageGateway desde o início

FASE 1: Stage 1 — Layout Clustering (NOVO — 22 sub-steps, 2 fases + 3 camadas)
  ├── Criar stage1_layout_clustering.py
  ├── FASE A — Intra-PDF (isolado por PDF):
  │   ├── CAMADA 1 (prevenção — steps 1.1-1.12):
  │   │   ├── get_text("blocks") + normalização + content abstraction
  │   │   ├── Header/footer removal (POR PDF — threshold correto)
  │   │   ├── DBSCAN grid detection (sem ruído cross-template)
  │   │   ├── Spatial bitmap (grade 10×14)
  │   │   ├── Fingerprint 6-dimensional
  │   │   ├── Tolerant Similarity Matrix (geo 0.8 + den 0.2)
  │   │   ├── Graph clustering (NetworkX threshold 0.85)
  │   │   ├── Consensus check (hierarchical valida)
  │   │   └── Representative selection (highest degree)
  │   ├── CAMADA 2 (detecção — steps 1.13-1.15):
  │   │   ├── Cluster quality score
  │   │   ├── Visual hash cross-check (pHash)
  │   │   └── Representative validation
  │   ├── CAMADA 3 (correção — steps 1.16-1.17):
  │   │   ├── Auto-correction (com sinais algorítmicos + LLM)
  │   │   └── Confidence score (quality + pHash + consensus + LLM)
  │   └── Output: clusters[] com pdf_id preservado
  ├── VALIDAÇÃO:
  │   └── Step 1.16: Document Homogeneity Check (template_mismatch se shared_ratio < 0.20)
  ├── Checkpoint humano (condicional: low confidence | auto-correction | template_mismatch | always_confirm)
  └── Output: clusters[] com confidence + pdf_id preservado + _raw_text_blocks

FASE 2: Reorganizar Stages 2-6 + 17-18 → Stage 2 (Deep Extraction)
  ├── Criar stage2_deep_extraction.py que orquestra sub-steps
  ├── Filtrar: só rodar nas representative_pages
  ├── 2.1: Capturar page.rect (width/height) + span["flags"] (bold/italic/mono)
  ├── 2.2: Threshold proporcional ao font_size, preservar sub_spans
  ├── 2.3: Expandir FONT_MAP (~50 fontes), usar span flags para bold/italic
  ├── 2.4: Filtrar masks, validar bbox, marcar bbox_valid
  ├── 2.5: SÓ representativas, alpha=False (fundo branco)
  ├── 2.6: Substituir KMeans por Jenks Natural Breaks (jenkspy), excluir header/footer zones
  ├── 2.7: Substituir custom 3-evidências por PyMuPDF find_tables() — ruling lines + multi-tabela
  ├── 2.8: Usar TableCell com bbox (modelo já existe), multi-page % height
  ├── 2.9: NOVO Extraction Quality Check — validar text_blocks, encoding, tabelas (renumerado de 2.10)
  ├── XSD Parsing MOVIDO para Stage 4.1 (v3.12)
  ├── NOVO: get_drawings() → drawn_elements[] (linhas, retângulos, backgrounds)
  ├── NOVO: span["color"] obrigatório em TextBlock (default 0 = preto)
  ├── Screenshots/images via StorageGateway (não disco direto)
  ├── Verificar PyMuPDF ≥ 1.23.0 para find_tables()
  └── ✅ RESOLVIDO v3.10: G8 — Stage 1 preserva _raw_text_blocks, Stage 3 consome

FASE 3: Reorganizar Stages 12-16 + 19 + 20-22 → Stage 3 (Structural Analysis)
  ├── Criar stage3_structural_analysis.py (orquestrador 4 sub-steps)
  ├── 3.1: Multi-Example Analysis — consolidar Stages 12-15 numa passada
  │       Estatística + spaCy NER + regex → position_classifications
  │       Dependência: spacy + pt_core_news_lg (~50MB)
  ├── 3.2: Visual Analysis — consolidar Stages 20-22 em 1 chamada GPT-4o
  │       OBRIGATÓRIO. 1 chamada combinada (segmentation + interpretation + self-check)
  │       Fallback: thresholds adaptativos se operador continuar sem Vision
  ├── 3.3: Semantic Classification — Stage 19 + Stage 16 + label-value pairing
  │       Algorítmico: intelligence (3.1) + visual_regions (3.2) + cor + font_size
  │       NOVO: label-value pairing (movido do Stage 4.2)
  ├── 3.4: Hierarchy Builder — NOVO MELHORADO
  │       4 sinais: visual regions + drawn_elements + grid_info + gap proporcional
  │       Label-value pairs como nós field. Seções condicionais como nós variant
  │       Imagens (Stage 2), charts e barcodes (Visual Analysis) incluídos na árvore (v3.14)
  ├── document_type: keyword matching existente em pipeline_result.py (sem LLM)
  ├── Paralelismo: 3.1 e 3.2 podem rodar em paralelo
  └── Stage 4.2 renomeado: Label-Value Pairing → Pair Validation

FASE 4: Reorganizar Stages 23-26 + XSD → Stage 4 (Field Mapping) — v3.15
  ├── Criar stage4_field_mapping.py (orquestrador 7 sub-steps)
  ├── 4.1: XSD Parsing (movido do Stage 2 — lxml, sem mudança funcional)
  ├── 4.2: Pair Validation — consumir field_pair do Stage 3.3
  │       Validar pares existentes + parear blocos soltos restantes
  │       NÃO re-descobrir labels do zero
  ├── 4.3: Format Pre-Detection — regex ANTES do matching (REORDENADO)
  │       Detectar formatos (date, cpf, currency) para enriquecer prompt LLM
  │       Mesmos patterns do Stage 24 existente
  ├── 4.4: Section↔XSD Matching — NOVO
  │       Cruzar seções do document_trees com nós complexos do XSD
  │       Reduz search space de ~80 paths para ~3-5 por campo
  │       Algorítmico: nome da seção + filhos vs nome do nó + filhos
  ├── 4.5: Field Matching — BATCH LLM (1 chamada Gemini Flash por layout)
  │       Prompt enriquecido: seção XSD + formato detectado + label + value
  │       Two-pass: pass 1 alta confiança, pass 2 elimina paths já usados
  │       PA4: XSD confirma likely_dynamic → dynamic (confidence ≥ 0.7)
  │       block_id + layout_type_id obrigatórios
  ├── 4.6: Confidence Scoring — heurísticas determinísticas (REMOVER Claude Sonnet)
  │       Per-layout (não global) — alinha com frontend ConfidenceByLayout
  │       PA1: smart_signals + classification_quality ajustam field_variability
  │       PA5: propagar smart_signals nos field_mappings
  └── 4.7: Consistency Validation — consumir document_trees + block_classifications
          NOVO: validação tipo↔formato (XSD type vs detected_format)
          NOVO: reverse mapping (campos XSD required sem mapping)

FASE 5: Reescrever Stages 27-28 → Stage 5 (Template Generation) — v3.16
  ├── Criar stage5_template_generation.py (orquestrador 7 sub-steps)
  ├── 5.1: Tree-Driven HTML — walk document_trees (Stage 3.4)
  │       <table> real com foreach, condicionais com conteúdo
  │       Filtrado por layout_type_id
  ├── 5.2: CSS-from-Extraction — fonts, cores, backgrounds de Stages 2-3
  │       Zonas header/footer de visual_regions
  ├── 5.3: Coverage multidimensional — fields(60%) + tables(25%) + images(15%)
  │       Contagem real de nós na document_tree
  ├── 5.4: Overlay Items — per-layout (filtrado layout_type_id)
  ├── 5.5: VariationMatrix Assembly — PA6: variant + present_in_pdfs → matrix
  │       Gera Detections automaticamente
  ├── 5.6: PipelineResult Assembly — trees_by_layout, validation_result,
  │       intelligence, block_classifications_confirmed, multi_doc
  ├── 5.7: Persistência com Checkpoint (handle_service_failure)
  ├── Frontend: loadFromPipelineResult → multiDocStore.populateFromPipeline
  └── Frontend: trees_by_layout → templateStore por layout ativo

FASE 6: Frontend
  ├── Adaptar types para novo PipelineResult
  ├── Screenshots/assets via signed URLs (não paths locais)
  ├── trees_by_layout no editor
  └── Coverage multidimensional
```

---

### 10.1 Fase 0: Storage Gateway — Detalhamento Técnico

#### Problema Atual

O pipeline salva todos os artefatos em `/tmp/jobs/{jobId}/` com TTL de 1 hora. Isso causa:

| Problema | Impacto | Cenário |
|----------|---------|---------|
| **Volatilidade** | Dados perdidos | Server restart, deploy, crash |
| **Sem escala horizontal** | Single instance only | 2 instâncias = job not found |
| **Template assets sem cleanup** | Disco acumula infinitamente | `/tmp/templates/{id}/assets/` nunca deletado |
| **Sem versionamento** | Impossível rastrear | Qual pipeline gerou qual resultado? |
| **Pipeline v3.2 piora** | Mais artefatos em disco | Thumbnails pHash, LLM, multi-PDF |

#### Arquitetura Storage Gateway

```
                    ┌─────────────────────────┐
                    │     StorageGateway       │
                    │     (interface ABC)      │
                    └──────────┬──────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
    ┌───────────────┐ ┌──────────────┐ ┌─────────────────┐
    │ Supabase      │ │ Local        │ │ S3 (futuro)     │
    │ Storage       │ │ Storage      │ │                 │
    │ Gateway       │ │ Gateway      │ │                 │
    │               │ │              │ │                 │
    │ Buckets:      │ │ /tmp/jobs/   │ │ s3://bucket/    │
    │ jobs/         │ │ (fallback    │ │                 │
    │ templates/    │ │  dev/testes) │ │                 │
    └───────────────┘ └──────────────┘ └─────────────────┘
```

```python
# backend/services/storage/gateway.py

from abc import ABC, abstractmethod
from pathlib import Path


class StorageGateway(ABC):
    """Abstração de storage — stages não sabem se é disco ou cloud."""

    @abstractmethod
    async def upload_pdf(self, job_id: str, index: int, content: bytes) -> str:
        """Salva PDF e retorna identificador (URL ou path)."""

    @abstractmethod
    async def upload_screenshot(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        """Salva screenshot e retorna URL."""

    @abstractmethod
    async def upload_asset(self, job_id: str, filename: str, content: bytes) -> str:
        """Salva imagem extraída e retorna URL."""

    @abstractmethod
    async def upload_thumbnail(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        """Salva thumbnail para pHash/LLM e retorna URL."""

    @abstractmethod
    async def get_local_path(self, job_id: str, filename: str) -> Path:
        """Baixa arquivo para path local temporário (PyMuPDF precisa de Path).
        Retorna Path do arquivo local. Cache: se já baixou, retorna cache."""

    @abstractmethod
    async def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        """Gera URL assinada para acesso frontend."""

    @abstractmethod
    async def save_result(self, job_id: str, result_json: dict) -> None:
        """Persiste resultado no banco de dados."""

    @abstractmethod
    async def save_clusters(self, job_id: str, clusters: list[dict]) -> None:
        """Persiste clusters no banco de dados."""

    @abstractmethod
    async def cleanup_local(self, job_id: str) -> None:
        """Remove arquivos temporários locais (após pipeline completo)."""

    @abstractmethod
    async def delete_job(self, job_id: str) -> None:
        """Remove todos os artefatos de um job (Storage + DB)."""
```

```python
# backend/services/storage/supabase_gateway.py

from supabase import AsyncClient
from pathlib import Path
import tempfile

class SupabaseStorageGateway(StorageGateway):
    """Implementação com Supabase Storage + DB."""

    def __init__(self, supabase: AsyncClient, tmp_base: Path = Path("/tmp/jobs")):
        self._supabase = supabase
        self._tmp_base = tmp_base

    async def upload_pdf(self, job_id: str, index: int, content: bytes) -> str:
        filename = "input.pdf" if index == 0 else f"input_{index + 1}.pdf"
        path = f"jobs/{job_id}/pdfs/{filename}"
        await self._supabase.storage.from_("jobs").upload(path, content)

        # Também salva local para processamento imediato
        local_dir = self._tmp_base / job_id
        local_dir.mkdir(parents=True, exist_ok=True)
        (local_dir / filename).write_bytes(content)

        return path

    async def upload_screenshot(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = f"jobs/{job_id}/screenshots/{page_key}.png"
        await self._supabase.storage.from_("jobs").upload(path, png_bytes,
            file_options={"content-type": "image/png"})
        return path

    async def upload_thumbnail(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = f"jobs/{job_id}/thumbnails/{page_key}.png"
        await self._supabase.storage.from_("jobs").upload(path, png_bytes,
            file_options={"content-type": "image/png"})
        return path

    async def upload_asset(self, job_id: str, filename: str, content: bytes) -> str:
        path = f"jobs/{job_id}/assets/{filename}"
        await self._supabase.storage.from_("jobs").upload(path, content)
        return path

    async def get_local_path(self, job_id: str, filename: str) -> Path:
        local_path = self._tmp_base / job_id / filename
        if local_path.exists():
            return local_path  # cache hit

        # Download do Storage
        local_path.parent.mkdir(parents=True, exist_ok=True)
        data = await self._supabase.storage.from_("jobs").download(
            f"jobs/{job_id}/pdfs/{filename}"
        )
        local_path.write_bytes(data)
        return local_path

    async def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        result = await self._supabase.storage.from_(bucket).create_signed_url(
            path, expires_in
        )
        return result["signedURL"]

    async def save_result(self, job_id: str, result_json: dict) -> None:
        await self._supabase.table("jobs").update({
            "result_json": result_json,
            "status": "completed"
        }).eq("id", job_id).execute()

    async def save_clusters(self, job_id: str, clusters: list[dict]) -> None:
        rows = [
            {
                "job_id": job_id,
                "cluster_id": c["cluster_id"],
                "pages": c["pages"],
                "representative": c["representative_page"],
                "confidence": c.get("confidence"),
            }
            for c in clusters
        ]
        await self._supabase.table("job_clusters").upsert(rows).execute()

    async def cleanup_local(self, job_id: str) -> None:
        local_dir = self._tmp_base / job_id
        if local_dir.exists():
            import shutil
            shutil.rmtree(local_dir, ignore_errors=True)

    async def delete_job(self, job_id: str) -> None:
        # Storage
        files = await self._supabase.storage.from_("jobs").list(f"jobs/{job_id}")
        for f in files:
            await self._supabase.storage.from_("jobs").remove([f["name"]])
        # DB (cascade deleta job_clusters)
        await self._supabase.table("jobs").delete().eq("id", job_id).execute()
```

```python
# backend/services/storage/local_gateway.py

class LocalStorageGateway(StorageGateway):
    """Fallback para dev/testes — comportamento atual encapsulado."""

    def __init__(self, tmp_base: Path = Path("/tmp/jobs")):
        self._tmp_base = tmp_base

    async def upload_pdf(self, job_id: str, index: int, content: bytes) -> str:
        filename = "input.pdf" if index == 0 else f"input_{index + 1}.pdf"
        local_dir = self._tmp_base / job_id
        local_dir.mkdir(parents=True, exist_ok=True)
        path = local_dir / filename
        path.write_bytes(content)
        return str(path)

    async def upload_screenshot(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = self._tmp_base / job_id / "screenshots" / f"{page_key}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png_bytes)
        return str(path)

    async def upload_thumbnail(self, job_id: str, page_key: str, png_bytes: bytes) -> str:
        path = self._tmp_base / job_id / "thumbnails" / f"{page_key}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(png_bytes)
        return str(path)

    async def get_local_path(self, job_id: str, filename: str) -> Path:
        return self._tmp_base / job_id / filename  # já é local

    async def get_signed_url(self, bucket: str, path: str, expires_in: int = 3600) -> str:
        return f"/api/files/{path}"  # serve via API local

    # ... save_result salva em JSON local, etc.
```

#### Configuração — Escolha explícita, sem fallback silencioso

> **REGRA CARDINAL:** Se configurou cloud, é cloud. Se Supabase falha, o pipeline
> usa `handle_service_failure()` (Seção 12) — NUNCA degrada silenciosamente para disco local.
> Local é uma escolha explícita de configuração, não um fallback automático.

```python
# backend/services/storage/__init__.py

from backend.config import settings

class StorageMode(str, Enum):
    SUPABASE = "supabase"   # Produção — Supabase Storage + DB
    LOCAL = "local"          # Dev/testes — disco local

def create_storage_gateway() -> StorageGateway:
    """Factory — escolhe implementação baseado em config EXPLÍCITA.

    IMPORTANTE: NÃO faz fallback automático.
    - STORAGE_MODE=supabase → SupabaseStorageGateway. Se Supabase indisponível, FALHA + checkpoint.
    - STORAGE_MODE=local → LocalStorageGateway. Disco local, sem cloud.
    - Sem config → ERRO na inicialização (obriga definir).
    """
    mode = settings.STORAGE_MODE  # obrigatório — sem default

    if mode == StorageMode.SUPABASE:
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise ConfigurationError(
                "STORAGE_MODE=supabase requer SUPABASE_URL e SUPABASE_KEY configurados"
            )
        from .supabase_gateway import SupabaseStorageGateway
        return SupabaseStorageGateway(supabase_client)

    elif mode == StorageMode.LOCAL:
        from .local_gateway import LocalStorageGateway
        return LocalStorageGateway()

    else:
        raise ConfigurationError(f"STORAGE_MODE inválido: {mode}. Use 'supabase' ou 'local'.")

# Singleton — importar de qualquer lugar
storage = create_storage_gateway()
```

**Variáveis de ambiente:**

```env
# .env — OBRIGATÓRIO definir:
STORAGE_MODE=supabase       # "supabase" ou "local" — sem default, sem fallback

# Se STORAGE_MODE=supabase:
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...

# Se STORAGE_MODE=local:
# Nenhuma config extra necessária (usa /tmp/jobs)
```

**O que acontece quando Supabase falha (STORAGE_MODE=supabase):**

Cada método do `SupabaseStorageGateway` usa `handle_service_failure()`:

```python
# SupabaseStorageGateway — exemplo de upload com checkpoint
async def upload_screenshot(self, job_id, page_key, png_bytes, context=None, job=None):
    try:
        path = f"jobs/{job_id}/screenshots/{page_key}.png"
        await self._supabase.storage.from_("jobs").upload(path, png_bytes,
            file_options={"content-type": "image/png"})
        return path
    except Exception as e:
        if context and job:
            decision = await handle_service_failure(
                context=context,
                service_name="Supabase Storage",
                stage_name=context.get("_current_stage_name", "Unknown"),
                error=e,
                fallback_description="Screenshot não será persistido na cloud — ficará apenas em memória",
                impact_description="Se o server reiniciar, screenshot será perdido. Pipeline continua mas sem persistência.",
                job=job
            )
            if decision == "retry":
                return await self.upload_screenshot(job_id, page_key, png_bytes, context, job)
            elif decision == "fallback":
                # Operador ACEITOU continuar sem persistência — log explícito
                logger.warning(f"Operador aceitou: screenshot {page_key} NÃO persistido (Supabase offline)")
                return None  # caller trata None como "sem URL"
            # abort já foi handled (raises PipelineAbortError)
        raise  # sem context/job = erro fatal (startup, não pipeline)
```

| Cenário | STORAGE_MODE=supabase | STORAGE_MODE=local |
|---------|----------------------|-------------------|
| Upload OK | Salva no Supabase Storage | Salva em `/tmp/jobs/` |
| Upload falha | **Checkpoint** → operador decide | Erro fatal (disco cheio?) |
| Download OK | Baixa do Storage → temp local | Lê de `/tmp/jobs/` |
| Download falha | **Checkpoint** → retry/abort | Erro fatal (arquivo não existe) |
| Startup sem config | `ConfigurationError` | Funciona sem Supabase vars |

#### Tabelas Supabase — SQL

```sql
-- Tabela jobs (evolução do que já existe)
CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    status TEXT NOT NULL DEFAULT 'pending',   -- pending, running, completed, failed, cancelled
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    pdf_count INT DEFAULT 0,
    page_count INT DEFAULT 0,
    result_json JSONB,                        -- PipelineResult completo
    config JSONB DEFAULT '{}'::jsonb,         -- failure_policy, thresholds, etc.
    error_message TEXT                        -- se status = failed
);

-- Clusters persistidos (rastreabilidade + reprocessamento)
CREATE TABLE IF NOT EXISTS job_clusters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    cluster_id TEXT NOT NULL,                 -- "A", "B", ...
    pages JSONB NOT NULL,                     -- [{pdf_id, page_index}]
    representative JSONB NOT NULL,            -- {pdf_id, page_index}
    page_count INT NOT NULL,
    confidence JSONB,                         -- {confidence, level, factors}
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(job_id, cluster_id)
);

-- Templates salvos pelo operador (permanente)
CREATE TABLE IF NOT EXISTS templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID REFERENCES jobs(id),          -- job que originou (opcional)
    name TEXT NOT NULL,
    html TEXT,
    css TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,       -- document_type, field_count, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_job_clusters_job ON job_clusters(job_id);
CREATE INDEX idx_templates_job ON templates(job_id);
CREATE INDEX idx_jobs_status ON jobs(status);

-- RLS (se necessário)
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE templates ENABLE ROW LEVEL SECURITY;
```

#### Buckets Supabase Storage

```sql
-- Criar buckets via Supabase Dashboard ou API
INSERT INTO storage.buckets (id, name, public) VALUES
    ('jobs', 'jobs', false),        -- privado — acesso via signed URLs
    ('templates', 'templates', false);

-- Políticas de acesso (ajustar conforme auth strategy)
CREATE POLICY "Jobs bucket: authenticated read/write"
    ON storage.objects FOR ALL
    USING (bucket_id = 'jobs')
    WITH CHECK (bucket_id = 'jobs');

CREATE POLICY "Templates bucket: authenticated read/write"
    ON storage.objects FOR ALL
    USING (bucket_id = 'templates')
    WITH CHECK (bucket_id = 'templates');
```

#### Adaptação dos arquivos existentes (7 arquivos)

**1. `backend/routers/upload.py`** — Upload via gateway

```python
# ANTES:
job_dir = Path(f"/tmp/jobs/{job_id}")
job_dir.mkdir(parents=True, exist_ok=True)
(job_dir / "input.pdf").write_bytes(pdf_bytes)

# DEPOIS:
from backend.services.storage import storage
await storage.upload_pdf(job_id, index=0, content=pdf_bytes)
```

**2. `backend/routers/analyze.py`** — Download + cleanup

```python
# ANTES (pipeline start):
job_dir = Path(f"/tmp/jobs/{job_id}")
if not job_dir.exists():
    raise HTTPException(404, "Job not found")

# DEPOIS:
pdf_path = await storage.get_local_path(job_id, "input.pdf")  # download se necessário

# ANTES (pipeline end):
# TTL cleanup em _evict_stale_jobs()

# DEPOIS (pipeline end):
await storage.cleanup_local(job_id)  # remove temp local imediatamente
# Dados permanecem no Supabase Storage — acessíveis via signed URL
```

**3. `backend/services/stages/screenshot_generator.py`**

```python
# ANTES:
out_path = screenshots_dir / f"page_{pdf_id}_{page_num}.png"
pix.save(str(out_path))

# DEPOIS:
png_bytes = pix.tobytes("png")
url = await storage.upload_screenshot(job_id, f"page_{pdf_id}_{page_num}", png_bytes)
page_data["screenshot_url"] = url  # URL em vez de path local
```

**4. `backend/services/stages/image_extraction.py`**

```python
# ANTES:
asset_path = assets_dir / f"img_{pdf_id}_{page_num}_{img_index}.{ext}"
asset_path.write_bytes(image_bytes)

# DEPOIS:
filename = f"img_{pdf_id}_{page_num}_{img_index}.{ext}"
url = await storage.upload_asset(job_id, filename, image_bytes)
```

**5. `backend/services/stages/pipeline_result.py`**

```python
# ANTES (opcional, falha silenciosa):
try:
    supabase_client.table("jobs").update(payload).eq("id", job_id).execute()
except: pass

# DEPOIS (obrigatório, com checkpoint se falhar):
try:
    await storage.save_result(job_id, result_json)
    await storage.save_clusters(job_id, context["clusters"])
except Exception as e:
    decision = await handle_service_failure(context, "Supabase", "Template Generation", e, ...)
    # retry / operador aceita continuar sem persistência / abort
```

**6. `backend/routers/assets.py`** — Template assets via Storage

```python
# ANTES:
assets_dir = Path(f"/tmp/templates/{template_id}/assets")
(assets_dir / filename).write_bytes(content)

# DEPOIS:
path = f"templates/{template_id}/assets/{filename}"
await storage.supabase.storage.from_("templates").upload(path, content)
```

**7. `frontend/src/stores/session.ts`** — Screenshots via signed URLs

```typescript
// ANTES:
screenshotUrl = `/api/files/${jobId}/screenshots/page_${pdfIndex}_${pageNum}.png`

// DEPOIS:
screenshotUrl = await api.get(`/api/jobs/${jobId}/screenshot-url`, {
    params: { page_key: `page_${pdfIndex}_${pageNum}` }
})
// Backend retorna signed URL do Supabase Storage (expira em 1h)
```

#### Lifecycle com Storage Gateway

```
┌─ UPLOAD ────────────────────────────────────────────────────┐
│  1. Frontend envia PDF(s) + XSD                              │
│  2. Backend recebe → storage.upload_pdf()                    │
│     ├── Supabase: upload Storage + salva temp local           │
│     └── Local: salva em /tmp/jobs/{id}/                       │
│  3. Cria registro na tabela jobs (status: pending)           │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─ PIPELINE START ────────────────────────────────────────────┐
│  1. storage.get_local_path() — garante PDFs em temp local   │
│  2. Pipeline roda stages 1-5                                 │
│     ├── Screenshots → storage.upload_screenshot()            │
│     ├── Assets → storage.upload_asset()                      │
│     ├── Thumbnails → storage.upload_thumbnail()    (Stage 1) │
│     └── Resultados intermediários: em memória (context)      │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─ PIPELINE DONE ─────────────────────────────────────────────┐
│  1. storage.save_result(job_id, result_json)                 │
│  2. storage.save_clusters(job_id, clusters)                  │
│  3. storage.cleanup_local(job_id)  ← IMEDIATO, não TTL      │
│     Temp local deletado. Dados permanecem no Supabase.       │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─ FRONTEND ACESSA ───────────────────────────────────────────┐
│  PDFs: IndexedDB (já funciona) + fallback signed URL         │
│  Screenshots: signed URL do Supabase Storage                 │
│  Assets: signed URL do Supabase Storage                      │
│  Result: Supabase DB (tabela jobs.result_json)               │
│  Clusters: Supabase DB (tabela job_clusters)                 │
└──────────────────────────────────────────────────────────────┘
```

#### Custo de mudar agora vs depois

| | Agora (Fase 0) | Depois (com pipeline v3.2 implementado) |
|---|----------------|----------------------------------------|
| Arquivos a adaptar | 7 | 7 + todos os novos stages |
| Padrão | Wrapper simples | Migração + refactor |
| Dados existentes | Zero para migrar | Jobs com artefatos em disco |
| Risco | Baixo — encapsula | Alto — breaking changes |
| Estimativa | ~2-3 stories | ~4-5 stories + migrations |

---

## 12. Política de Falhas — Nunca Agir Silenciosamente

### Princípio

> **Nenhuma decisão que comprometa o resultado pode ser tomada sem avisar o operador.**
> Se um serviço falha (LLM, Vision AI, Supabase), o pipeline NÃO continua silenciosamente
> com um fallback degradado. O operador é notificado e decide o que fazer.

### Padrão: Service Failure Checkpoint

Quando qualquer serviço externo falha, o pipeline emite um **checkpoint de falha** via SSE:

```python
# Padrão reutilizável para qualquer falha de serviço
async def handle_service_failure(
    context: dict,
    service_name: str,        # "LLM Vision", "Gemini Flash", "Supabase", "OpenRouter"
    stage_name: str,          # "Layout Clustering", "Field Matching", etc.
    error: Exception,
    fallback_description: str,  # "Usar somente quality_score + pHash (sem validação LLM)"
    impact_description: str,    # "Clustering pode ter menor precisão"
    job: dict,
    timeout: int = 300
):
    """Notifica operador sobre falha e aguarda decisão."""

    checkpoint = {
        "type": "service_failure",
        "service": service_name,
        "stage": stage_name,
        "error": str(error),
        "options": [
            {
                "action": "retry",
                "label": f"Tentar {service_name} novamente",
                "description": "Re-executa a chamada ao serviço"
            },
            {
                "action": "fallback",
                "label": f"Continuar sem {service_name}",
                "description": fallback_description,
                "warning": impact_description
            },
            {
                "action": "abort",
                "label": "Cancelar pipeline",
                "description": "Para a execução para investigar o problema"
            }
        ],
        "timeout_seconds": timeout,
        "timeout_action": "fallback",  # o que fazer se operador não responder
        "message": f"{service_name} falhou no {stage_name}: {error}"
    }

    await emit_progress({
        "stage": context.get("_current_stage", 0),
        "stage_name": stage_name,
        "status": "service_failure",
        "checkpoint": checkpoint
    })

    # Aguarda decisão do operador
    job["confirmation_event"] = asyncio.Event()
    job["status"] = "awaiting_confirmation"

    confirmation = await wait_for_confirmation(job, timeout=timeout)

    if confirmation["action"] == "retry":
        return "retry"      # chamador re-executa a operação
    elif confirmation["action"] == "abort":
        raise PipelineAbortError(f"Operador cancelou: {service_name} falhou")
    else:  # fallback ou timeout
        return "fallback"   # chamador usa alternativa degradada
```

### Endpoint de Resposta a Falhas

```python
# backend/routers/analyze.py

@router.post("/jobs/{job_id}/handle-failure")
async def handle_failure(job_id: str, body: FailureResponse):
    """Operador responde a uma falha de serviço."""
    job = get_job(job_id)
    if not job or job["status"] != "awaiting_confirmation":
        raise HTTPException(404, "Job not found or not awaiting confirmation")

    job["cluster_confirmation"] = {
        "action": body.action,  # "retry" | "fallback" | "abort"
        "by": "human"
    }
    job["confirmation_event"].set()
    return {"status": "accepted"}


class FailureResponse(BaseModel):
    action: Literal["retry", "fallback", "abort"]
```

### Frontend — Tela de Falha de Serviço

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚠ Falha de Servico — LLM Vision (Gemini Flash)                │
│                                                                  │
│  Erro: "Connection timeout after 30s"                            │
│  Stage: Layout Clustering (1.16 LLM Cluster Validation)         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ O que acontece se continuar sem LLM Vision:                 │ │
│  │                                                              │ │
│  │ O clustering sera validado apenas por quality_score + pHash. │ │
│  │ A precisao pode ser menor — clusters incorretos nao serao   │ │
│  │ detectados pela validacao LLM.                               │ │
│  │                                                              │ │
│  │ Impacto: Medio — o resultado pode precisar de mais           │ │
│  │ correcoes manuais no editor.                                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │ 🔄 Tentar de novo│  │ ▶ Continuar sem │  │ ✖ Cancelar   │  │
│  │                  │  │   LLM Vision    │  │   pipeline    │  │
│  └──────────────────┘  └─────────────────┘  └───────────────┘  │
│                                                                  │
│  ⏱ Auto-continua sem LLM em 4:32                                │
└─────────────────────────────────────────────────────────────────┘
```

Wireframe visual: `wireframe-cluster-checkpoint.html` (mesmo padrão modal)

### Aplicação por Stage — Todos os pontos de falha

#### Stage 1: Layout Clustering

| Sub-step | Serviço | Se falha | Opções para operador |
|----------|---------|----------|---------------------|
| 1.16 LLM Cluster Validation | Gemini Flash | Checkpoint | Retry / Continuar sem LLM (só quality+pHash) / Cancelar |

#### Stage 2: Deep Extraction

| Sub-step | Serviço | Se falha | Opções para operador |
|----------|---------|----------|---------------------|
| 2.1 Full Text Extraction | PyMuPDF | Checkpoint | Retry / Cancelar (sem texto = pipeline inviável) |
| 2.4 Image Extraction | PyMuPDF | Continuar | Imagens ausentes = template sem logos/charts. Warning logged |
| 2.5 Screenshot Rendering | PyMuPDF | Checkpoint | Retry / Continuar sem screenshots (Vision AI não rodará) / Cancelar |
| 2.7 Table Detection | PyMuPDF find_tables() | Continuar | Fallback para algoritmo custom (alignment + pattern). Warning logged |
| 2.9 XSD Parsing | lxml (arquivo local) | Checkpoint | Retry / Continuar sem XSD (field matching não terá paths) / Cancelar |
| 2.10 Quality Check (severity=error) | Local | Checkpoint | Fornecer OCR externo / Continuar mesmo assim / Cancelar |

#### Stage 3: Structural Analysis

| Sub-step | Serviço | Se falha | Opções para operador |
|----------|---------|----------|---------------------|
| 3.2 Visual Analysis | GPT-4o Vision | 1 retry automático → Checkpoint | Retry / Continuar sem Vision (~75% qualidade, thresholds adaptativos) / Cancelar |

#### Stage 4: Field Mapping

| Sub-step | Serviço | Se falha | Opções para operador |
|----------|---------|----------|---------------------|
| 4.5 Field Matching | Gemini Flash / OpenRouter | Checkpoint | Retry / Continuar sem IA (qualidade reduzida ~60%) / Cancelar |
| 4.6 Confidence Scoring | Local (heurísticas) | — | Sem falha possível (v3.15: Claude Sonnet removido — algorítmico puro) |

#### Stage 5: Template Generation

| Sub-step | Serviço | Se falha | Opções para operador |
|----------|---------|----------|---------------------|
| 5.1-5.6 | Local (algorítmico) | — | Sem falha possível (v3.16: 100% algorítmico, zero LLM) |
| 5.7 Persistence | Supabase | Checkpoint | Retry / Continuar sem salvar (resultado só em memória) / Cancelar |

### Uso no código — Exemplo concreto

```python
# Stage 1, sub-step 1.16:
async def llm_validate_clusters(clusters, pdf_docs, vision_client, context, job):
    try:
        result = await _call_gemini_flash(clusters, pdf_docs, vision_client)
        return result
    except Exception as e:
        decision = await handle_service_failure(
            context=context,
            service_name="LLM Vision (Gemini Flash)",
            stage_name="Layout Clustering",
            error=e,
            fallback_description="Clustering validado apenas por quality_score + pHash, sem LLM",
            impact_description="Clusters incorretos podem não ser detectados",
            job=job,
            timeout=300
        )
        if decision == "retry":
            return await llm_validate_clusters(clusters, pdf_docs, vision_client, context, job)
        else:
            return None  # fallback — chamador trata None como "sem validação LLM"


# Stage 4, sub-step 4.3 (v3.15 — batch LLM, 1 chamada por layout):
async def field_matching_batch(layout_pairs, field_tree, openrouter_client, context, job):
    """Batch: envia TODOS os pares label-value de um layout numa única chamada."""
    try:
        return await _llm_batch_match(layout_pairs, field_tree, openrouter_client)
    except Exception as e:
        decision = await handle_service_failure(
            context=context,
            service_name="OpenRouter (Gemini Flash)",
            stage_name="Field Mapping",
            error=e,
            fallback_description="Continuar sem IA — mapeamento por similaridade de texto (qualidade reduzida)",
            impact_description="Mais campos ficarão sem mapeamento ou ambíguos — será necessário corrigir manualmente",
            job=job,
            timeout=300
        )
        if decision == "retry":
            return await field_matching_batch(layout_pairs, field_tree, openrouter_client, context, job)
        else:
            return _fuzzy_match_batch(layout_pairs, field_tree)  # fallback aceito pelo operador
```

### Retry com backoff

Se o operador clica "Tentar de novo", o retry usa exponential backoff:

```python
MAX_RETRIES = 3  # máximo de retries consecutivos

async def retry_with_backoff(operation, context, service_name, stage_name, job, max_retries=MAX_RETRIES):
    """Tenta a operação com backoff. Após MAX_RETRIES, força checkpoint."""
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                await emit_progress({
                    "stage": context.get("_current_stage", 0),
                    "status": "retrying",
                    "message": f"Retry {attempt + 2}/{max_retries} em {wait_time}s...",
                    "service": service_name
                })
                await asyncio.sleep(wait_time)
            else:
                # Último retry falhou — agora sim, checkpoint obrigatório
                decision = await handle_service_failure(
                    context=context,
                    service_name=service_name,
                    stage_name=stage_name,
                    error=e,
                    fallback_description=f"Todas as {max_retries} tentativas falharam",
                    impact_description="Serviço indisponível — resultado será degradado",
                    job=job
                )
                if decision == "retry":
                    # Operador quer tentar mais — reset counter
                    return await retry_with_backoff(operation, context, service_name, stage_name, job)
                elif decision == "abort":
                    raise PipelineAbortError(f"Operador cancelou após {max_retries} retries")
                else:
                    return None  # fallback
```

### O que muda vs. pipeline atual

| Situação | Pipeline atual (AS-IS) | Pipeline v3.1 (proposta) |
|----------|----------------------|--------------------------|
| Vision AI indisponível | Skip silencioso, emite warning no log | **Checkpoint** (v3.13): 1 retry automático → operador escolhe retry / continuar sem Vision (~75% qualidade) / cancelar |
| Supabase indisponível | Skip silencioso, emite SSE warning | **Checkpoint**: operador escolhe retry/fallback/abort |
| OpenRouter indisponível | Fallback silencioso (qualidade reduzida) | **Checkpoint**: operador escolhe retry/fallback/abort |
| LLM retorna erro | Fallback silencioso | **Checkpoint** após 3 retries com backoff |
| XSD não encontrado | `field_tree = None`, continua | **Checkpoint**: operador escolhe retry/continuar sem XSD/abort |
| PDF encriptado | ValueError, pipeline para | Mantém — erro fatal legítimo |

### Configuração — Nível de notificação

O operador pode configurar por job o nível de intervenção:

```python
{
    "config": {
        "failure_policy": "notify",      # "notify" | "auto" | "strict"
        # "notify" (default) = checkpoint com timeout (5 min), auto-fallback se não responder
        # "auto" = fallback automático sem perguntar (logging apenas)
        # "strict" = checkpoint sem timeout, pipeline PARA até operador decidir
        "failure_timeout": 300           # segundos (só para "notify")
    }
}
```

| Política | Checkpoint | Timeout | Uso |
|----------|-----------|---------|-----|
| **notify** (default) | Sim | 5 min → auto-fallback | Produção normal |
| **auto** | Não | N/A | Batch processing, testes |
| **strict** | Sim | Sem timeout — para até decidir | Documentos críticos |

---

## 13. Riscos

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| Graph clustering produz clusters diferentes do KMeans | Média | Alto | Consensus check (2 algoritmos). Se discordam, mantém separado. KMeans como fallback |
| Content Abstraction muito agressiva | Baixa | Médio | 4 categorias simples. Spatial bitmap compensa (captura forma real) |
| LLM Vision falha ou indisponível | Baixa | Médio | v3.13: 1 retry automático → checkpoint operador (continuar sem Vision ~75% qualidade / cancelar). Hierarchy Builder usa fallback thresholds + drawn_elements |
| pHash gera falso positivo | Baixa | Baixo | pHash é cross-check, não decisor. Só gera warning quando discorda do texto |
| Auto-correction faz merge/split errado | Baixa | Alto | Regra: só merge com 2+ fontes concordando. Na dúvida, mantém separado |
| Hierarchy Builder agrupa errado | Média | Médio | v3.13: 5 sinais em cascata (visual regions + drawn_elements + grid_info + doc_type + gap proporcional). Editor permite correção manual |
| Breaking change no PipelineResult | Alta | Alto | Backward compat: `root` mantido, novos campos são aditivos |
| SSE com 5 estágios perde granularidade | Baixa | Baixo | Sub-progress reporta cada sub-step |
| Custo extra do LLM validation | Baixa | Nenhum | ~$0.003 por job — 100x menor que o Field Matching |
| Supabase Storage indisponível | Baixa | Alto | **Checkpoint** (Seção 12) — operador decide retry/continuar sem persistência/abort. **NÃO** faz fallback silencioso para disco |
| Latência upload Storage no pipeline | Média | Baixo | Upload async paralelo ao próximo step. ~50-200ms por arquivo |
| Dados em disco sem migrar para cloud | Alta | Alto | **Fase 0 é pré-requisito** — migrar antes de implementar stages |
| Text Reconstruction funde colunas de tabela | Média | Médio | Respeitar grid zones do Stage 1 como hint, não mergear cross-column |
| Grid Detection polui com header/footer | Média | Médio | Excluir top 15% e bottom 10% da página antes de clusterizar |
| PDF scanned sem OCR passa silenciosamente | Média | Alto | Quality Check (2.10) detecta empty_page e faz checkpoint |
| Encoding quebrado contamina pipeline | Baixa | Alto | Quality Check (2.10) detecta non-printable ratio > 10% |
| `find_tables()` não disponível em PyMuPDF < 1.23 | Baixa | Alto | Validar versão no startup; fallback para algoritmo custom se necessário |
| Stage 5 gera `<table>` errada ou faltante | Média | Médio | Editor: addNode("table") + TableInspector + Monaco HTML direto. Operador corrige manualmente — custo de produtividade, não bloqueio |
| CSS com fontes inexistentes no browser | Média | Baixo | **Já mitigado:** Stage 2 `_normalize_pdf_font_name` + editor `useFontCascade` (3 cascatas: normalização, catálogo IndexedDB, backend AI) + `FontWarning.vue` com upload de fonte |
| Seções condicionais KO.js incorretas | Média | Médio | Editor: VisibilityControl (Always/Conditional/Hidden) + lógica booleana visual. **Gap A:** bindings condicionais não validados no pre-export |
| Coverage percentual falso | Baixa | Baixo | Editor: CoverageOverlay visual (retângulos verde/vermelho/amarelo) + FieldNavItem com status. Operador confia nos olhos, não no número |
| VariationMatrix incompleta | Média | Médio | Editor: DiffViewer lado-a-lado + DetectionCard. **Gap B:** não existe "Marcar como variação" no editor — operador precisa editar KO.js no Monaco |
| Stage 5 zero LLM = zero autocorreção | Baixa | Médio | Editor: AutoFix com IA (3 runs/sessão) + Undo/Redo (20 snapshots) + Pre-export validation (6 checks). **Gap C:** limite de 3 runs pode ser insuficiente |

---

## 14. Gaps do Editor — Mitigação Pipeline↔Frontend (v3.17)

Análise de riscos cruzada: o que o pipeline pode errar vs o que o editor consegue corrigir. Identificados 3 gaps onde o editor NÃO consegue mitigar completamente.

### Gap A: Validação de bindings condicionais `<!-- ko if/foreach -->` (ALTA)

**Problema:** `usePreExportValidation.ts` valida `data-bind="text: campo"` contra o XSD, mas **NÃO valida** comentários Knockout.js:
- `<!-- ko if: secao_xyz -->` — não verifica se `secao_xyz` existe no modelo de dados
- `<!-- ko foreach: items -->` — não verifica se `items` é um array no XSD

Se o Stage 5.1 gerar um binding condicional com nome inválido, o template exporta sem erro mas **quebra em runtime** no Planet Express. É um **silent failure** — exatamente o que a política de falhas (Seção 12) proíbe.

**Validações atuais do pre-export (6 checks):**
1. `##TEMPLATE_DATA##` presente no HTML ✅
2. `ko.applyBindings` presente no JS ✅
3. `data-bind` fields existem no XSD ✅
4. HTML well-formed (DOMParser) ✅
5. CSS syntax válida (braces match) ✅
6. Library refs existem no catálogo ✅

**Validação faltante:**
7. `<!-- ko if: X -->` — X existe no modelo de dados ❌
8. `<!-- ko foreach: X -->` — X é array no XSD ❌

**Solução proposta:** Adicionar 2 checks no `usePreExportValidation.ts`:

```typescript
// ── AC7: ko comment bindings (if/foreach) ────────────────────────
const koCommentRe = /<!--\s*ko\s+(if|foreach|with|ifnot)\s*:\s*([\w.$]+)\s*-->/g
let koMatch: RegExpExecArray | null
while ((koMatch = koCommentRe.exec(html)) !== null) {
  const bindingType = koMatch[1]  // "if", "foreach", "with", "ifnot"
  const fieldRef = koMatch[2]      // "secao_xyz", "items"

  if (koBuiltins.has(fieldRef)) continue
  if (fieldRef.startsWith('$')) continue

  // Verificar se existe no XSD/modelo
  const found = [...knownPaths].some(
    (p) => p === fieldRef || p.endsWith(`.${fieldRef}`) || p.endsWith(`/${fieldRef}`)
  )

  if (!found) {
    errors.push({
      code: 'KO_COMMENT_FIELD_NOT_FOUND',
      message: `Binding "${bindingType}: ${fieldRef}" em comentário ko não encontrado no XSD`,
      blocking: true,
    })
  }
}
```

**Quando implementar:** Junto com o Stage 5 (antes de qualquer template ser exportado).

---

### Gap B: "Marcar como variação" desconectado do multiDocStore (MÉDIA)

**Problema:** O operador pode mudar visibilidade no `VisibilityControl.vue` (Always → Conditional), mas isso **NÃO registra** a seção como Detection no multiDocStore. O fluxo está desconectado:

```
VisibilityControl (templateStore)  ←→  multiDocStore (variações)
         ❌ NÃO CONECTADO
```

**Cenário:** Pipeline classificou um bloco como "required" mas o operador percebe que é condicional (aparece em 2 de 3 PDFs). Passos atuais:
1. Abrir StructureTree → selecionar seção
2. No Inspector → VisibilityControl → marcar "Conditional"
3. Definir condição booleana (field + operator + value)
4. **MAS:** O multiDocStore não sabe que isso é uma variação → DiffViewer não mostra → VariationMatrix não atualiza

**Solução proposta:** No `VisibilityControl`, quando modo muda para "conditional":

```typescript
// Em VisibilityControl.vue — onModeChange
watch(() => props.visibility?.mode, (newMode, oldMode) => {
  if (newMode === 'conditional' && oldMode !== 'conditional') {
    // Registrar como detection no multiDocStore
    const multiDocStore = useMultiDocStore()
    multiDocStore.addDetection({
      type: 'optional',
      description: `Seção "${nodeLabel}" marcada como condicional pelo operador`,
      confidence: 1.0,  // operador confirmou manualmente
    })
  }
})
```

**Quando implementar:** Story do editor — não bloqueia Stage 5.

---

### Gap C: AutoFix limite de 3 runs por sessão (BAIXA)

**Problema:** `autoFixStore.ts` limita a 3 execuções (`SESSION_RUN_LIMIT = 3`). Para templates complexos onde o pipeline gerou muitos problemas (primeiro uso, ~50+ campos), 3 runs pode não cobrir todas as correções necessárias.

**Dados atuais:**
- Cada run envia o estado completo do template (`documentTree`) para `/api/auto-fix`
- Backend retorna lista de sugestões (spacing, alignment, font, binding, position)
- Operador aceita/rejeita/skip cada sugestão individualmente
- Limite é por sessão (reset ao recarregar página)

**Análise de custo:** Uma chamada ao `/api/auto-fix` provavelmente usa LLM. Mas o custo é do **operador** (tempo vs qualidade), não do sistema.

**Solução proposta:** Tornar configurável via variável de ambiente:

```typescript
const SESSION_RUN_LIMIT = parseInt(
  import.meta.env.VITE_AUTOFIX_LIMIT ?? '5', 10
)
```

Aumentar default de 3 para 5, permitir override.

**Quando implementar:** Trivial — pode ser feito a qualquer momento.

---

### Matriz de Mitigação Pipeline↔Editor

| Risco do Pipeline | Editor Mitiga? | Como | Gap? |
|-------------------|---------------|------|------|
| Tabela faltante/errada | **SIM** | addNode + TableInspector + Monaco | — |
| CSS/Fontes incorretas | **SIM** | FontCascade (3 níveis) + FontWarning + upload | — |
| Seção condicional errada | **SIM parcial** | VisibilityControl + lógica booleana | **Gap B**: não sincroniza com multiDocStore |
| Coverage falsa | **SIM** | Overlay visual + FieldNavItem | — |
| VariationMatrix incompleta | **SIM parcial** | DiffViewer + DetectionCard | **Gap B**: sem "Marcar como variação" |
| Binding KO inválido | **NÃO** | Pre-export não valida ko comments | **Gap A**: silent failure em runtime |
| Muitos erros para AutoFix | **SIM parcial** | 3 runs/sessão + Undo/Redo | **Gap C**: limite pode ser insuficiente |
| Posicionamento errado | **SIM** | Canvas drag-drop + snap lines + grid | — |
| Overlay desalinhado | **SIM** | CoverageOverlay com dual bbox (canvas + PDF) | — |
| HTML malformado | **SIM** | Pre-export valida + Monaco com syntax | — |

---

## 15. Dependências Novas

| Biblioteca | Propósito | Instalação |
|------------|-----------|------------|
| `networkx` | Graph clustering (Stage 1) | `pip install networkx` |
| `scipy` | Hierarchical clustering (consensus) | Já instalado (scikit-learn depende) |
| `imagehash` | Perceptual hash (pHash) | `pip install imagehash` |
| `Pillow` | Manipulação de imagens para pHash | Já instalado |
| `scikit-learn` | DBSCAN | Já instalado |
| `numpy` | Array operations | Já instalado |
| `supabase` | Storage + DB (Fase 0) | `pip install supabase` |
| `jenkspy` | Jenks Natural Breaks para grid detection (Stage 2) | `pip install jenkspy` |
| `PyMuPDF` ≥ 1.23.0 | `find_tables()` para table detection (Stage 2) | Verificar versão atual; `pip install --upgrade PyMuPDF` |

**Novas:** `networkx` + `imagehash` + `jenkspy`. PyMuPDF já existe mas requer ≥ 1.23.0 para `find_tables()`.

---

— Aria, arquitetando o futuro 🏗️
