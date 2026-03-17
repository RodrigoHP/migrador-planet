# Arquitetura Técnica v5.0 — Document AI Platform

**Versão:** 5.0
**Data:** 2026-03-15
**Autor:** @architect (Aria)
**Status:** Proposta
**Base:** architecture-v4.md + document_ai_complete_master_architecture.md + document_ai_pipeline_23_stages.md

---

## Change Log

| Versão | Data | Descrição |
|--------|------|-----------|
| 3.0 | 2026-03-10 | Web app puro, stateless, sem banco, Levenshtein matching |
| 3.1 | 2026-03-10 | Gap review, ZIP autocontido, preview cache |
| 4.0 | 2026-03-14 | Document AI Platform: Supabase, Vision AI, Layout Model, pgvector, Konva.js |
| **5.0** | **2026-03-15** | **Pipeline 23 stages com sub-stages: Text Reconstruction, Font Extraction→CSS, Image Extraction, Grid Detection→CSS Grid no parsing. Template Generation separado em HTML+CSS+Knockout. Template Confidence Score agregado. Coverage Mode + Auto Layout Fix + Chart Detection (prioridade baixa) no review. OpenRouter substitui LiteLLM.** |

---

## 1. Visão Geral

Plataforma de **Document Reverse Engineering** que converte PDFs estáticos do PlanetPress em templates HTML/Knockout.js reutilizáveis e dinâmicos. O sistema opera em três macro-fases: **Document Understanding** (extrair estrutura física), **Layout Intelligence** (inferir semântica e lógica) e **Template Generation** (produzir template reutilizável).

A v5.0 expande o pipeline de 13 para **23 stages** organizados em **8 blocos lógicos**, adicionando inteligência de layout (multi-example analysis, variant detection, stability classification), inteligência de tabelas (detection antes de anchors, continuação multi-página) e um **Layout Registry** que permite reutilizar templates para layouts conhecidos.

```
┌──────────────────────────────────────────────────────────────────┐
│  BROWSER  (Chrome/Edge — zero instalação)                        │
│                                                                   │
│  Vue 3 + TypeScript + Vite + Pinia                               │
│  ├── PDF.js           render PDF no Canvas                       │
│  ├── Konva.js         anotação interativa sobre PDF (regions)    │
│  ├── Monaco Editor    editor HTML/CSS/JS                         │
│  ├── Chart.js         preview de gráficos                        │
│  ├── SSE client       progresso em tempo real                    │
│  ├── File System Access API   (nativa, zero dep)                 │
│  └── IndexedDB (idb)          catálogo Bibliotecas               │
└──────────────────────────────────────────────────────────────────┘
                    ↕  REST + SSE
┌──────────────────────────────────────────────────────────────────┐
│  SERVIDOR  FastAPI / Python                                       │
│                                                                   │
│  7 Módulos de Serviço:                                           │
│  ├── DocumentAnalysisModule     parsing, skeleton, screenshots   │
│  ├── LayoutDiscoveryModule      clustering, fingerprint, registry│
│  ├── LayoutIntelligenceModule   multi-example, stability, variant│
│  ├── TableIntelligenceModule    table identity, continuation     │
│  ├── VisionModule               segmentation, interpretation,    │
│  │                              self-check (GPT-4o, LayoutLMv3)  │
│  ├── DataMappingModule          field matching, format detection, │
│  │                              confidence (pgvector, Gemini)     │
│  └── TemplateEngineModule       generation, pagination, optimize │
│                                                                   │
│  AI Pipeline (OpenRouter):                                       │
│  ├── GPT-4o Vision    segmentação + interpretação de layout      │
│  ├── Gemini 2.0 Flash matching semântico label→campo             │
│  ├── Claude Sonnet    fidelity scoring + auto-correção           │
│                                                                   │
│  ML Models (PyTorch + HuggingFace) — FUTURO:                    │
│  ├── LayoutLMv3       layout segmentation fine-tuned             │
│  ├── MiniLM fine-tuned  field matching especializado             │
│  ├── BERT fine-tuned    format detection BR                      │
└──────────────────────────────────────────────────────────────────┘
                    ↕  HTTPS
┌──────────────────────────────────────────────────────────────────┐
│  SUPABASE                                                         │
│  ├── PostgreSQL + pgvector   jobs, layout_registry, embeddings   │
│  ├── Storage                 PDFs, templates, ZIPs               │
│  └── Auth                    FUTURO (quando multi-tenant)        │
└──────────────────────────────────────────────────────────────────┘
                    ↕  HTTPS
┌──────────────────────────────────────────────────────────────────┐
│  AI APIs                                                          │
│  ├── OpenAI API       GPT-4o Vision                              │
│  ├── Google AI        Gemini 2.0 Flash                           │
│  └── Anthropic API    Claude Sonnet                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Decisões Arquiteturais

### 2.1 Mudanças v4.0 → v5.0

| v4.0 | v5.0 | Motivo |
|------|------|--------|
| Pipeline 13 stages, 3 fases | Pipeline 23 stages, 8 blocos lógicos | Granularidade para reverse engineering robusto |
| 1 PDF obrigatório | 1 PDF obrigatório, 3-5 recomendados | Multi-example analysis diferencia labels de valores dinâmicos |
| Sem Layout Registry | Layout Fingerprint + Registry lookup | Reutilizar templates para layouts já processados |
| Sem multi-example analysis | Multi-Example + Stability + Variant Detection | Detecção de blocos condicionais e campos opcionais |
| Table detection dentro da Vision | Table Intelligence como bloco separado, ANTES de anchors | Evita interpretar headers de tabela como campos de formulário |
| Sem Vision Self-Check | Vision Self-Check valida consistência | Reprocessa página se inconsistências detectadas |
| Sem Layout Consistency Validation | Validação cruzada skeleton vs resultado final | Garante que template final respeita estrutura detectada |
| 5 serviços implícitos | 7 módulos explícitos | Modularidade clara sem microservices excessivos |

### 2.2 Decisões mantidas da v4.0

| Decisão | Motivo para manter |
|---------|-------------------|
| Web app puro (sem Electron/Tauri) | NFR1: zero instalação |
| Vue 3 + TypeScript + Pinia frontend | Stack implementada e funcional |
| FastAPI backend | Melhor ecossistema Python para AI/ML |
| Knockout.js nos templates (não Jinja2) | Preview reativo, compatibilidade PlanetPress |
| Supabase (PostgreSQL + pgvector + Storage) | Persistência, embeddings, feedback |
| GPT-4o Vision + Gemini + Claude (OpenRouter) | Multi-modelo, 1 API key, 1 billing |
| Konva.js anotação interativa | Seleção visual de regiões no PDF |
| SSE para progresso | Simples e suficiente |
| XSD obrigatório, dados de exemplo **opcionais** (XML/JSON) | XSD define data-bind; dados reais melhoram detecção de tipos e servem de dataset na Área de Testes (PRD v3.0 FR2a) |
| Learning System (online pgvector + batch fine-tuning futuro) | Melhoria contínua |

### 2.3 Multi-PDF — Recomendado, não obrigatório

| Cenário | PDFs | Comportamento |
|---------|------|---------------|
| Mínimo | 1 PDF | Pipeline funcional. Vision AI interpreta sem comparação. Sem variant detection. |
| Recomendado | 3-5 PDFs | Multi-example analysis ativa. Labels vs valores dinâmicos inferidos. Variant detection funcional. |
| Ideal | 5+ PDFs | Melhor cobertura de blocos condicionais. Stability analysis robusta. |

O frontend exibe aviso na Tela 1: _"Enviar 3-5 exemplos do mesmo tipo de documento melhora significativamente a detecção de campos dinâmicos e blocos condicionais."_

---

## 3. Stack Tecnológica

### 3.1 Frontend (browser)

| Tecnologia | Versão | Função |
|------------|--------|--------|
| Vue 3 | 3.5+ | Framework UI |
| TypeScript | 5.x | Tipagem estática |
| Vite | 7.x | Build tool + dev server |
| Pinia | 3.x | State management |
| Vue Router | 5.x | Navegação entre telas (Home, Upload, Analyzing, Editor) |
| PDF.js | 5.x | Renderização de PDF no Canvas |
| Konva.js | 9.x | Anotação interativa sobre PDF |
| vue-konva | 3.x | Wrapper Vue para Konva.js |
| Monaco Editor | 0.55+ | Editor de código HTML/CSS/JS |
| Chart.js | 4.x | Preview de gráficos |
| idb | 8.x | IndexedDB wrapper |
| @vueuse/core | 14.x | Composables Vue |
| Tailwind CSS | 4.x | Styling |
| File System Access API | nativa | Acesso filesystem local |

### 3.2 Backend (Python)

| Tecnologia | Versão | Função |
|------------|--------|--------|
| Python | 3.12+ | Linguagem |
| FastAPI | 0.115+ | Framework REST + SSE |
| Uvicorn | 0.32+ | ASGI server |
| PyMuPDF (fitz) | 1.24+ | Extração PDF (texto, coordenadas, fontes, imagens, vetores) |
| lxml | 5.x | Parse de XSD e XML |
| openai | 1.30+ | SDK OpenAI (compatível com OpenRouter API) |
| supabase | 2.5+ | SDK Supabase (PostgreSQL + Storage) |
| sentence-transformers | 3.0+ | Embeddings para semantic matching (384 dims) |
| scikit-learn | 1.4+ | Page clustering (KMeans) |
| numpy | 1.26+ | Vetores de features |
| torch | 2.3+ | PyTorch — runtime para modelos fine-tuned (FUTURO) |
| transformers | 4.40+ | HuggingFace — LayoutLMv3, BERT, MiniLM (FUTURO) |
| Pillow | 10.x | Screenshots de páginas para Vision AI |
| python-multipart | 0.0.x | Upload multipart |
| python-dotenv | 1.x | Configuração .env |
| sse-starlette | 2.x | Server-Sent Events |

### 3.3 Infraestrutura

| Componente | Escolha |
|-----------|---------|
| Database | Supabase PostgreSQL + pgvector |
| Storage | Supabase Storage (PDFs, ZIPs, templates) |
| Auth | Sem autenticação (ferramenta interna, 1-3 operadores) |
| Deploy backend | Railway |
| Deploy frontend | Railway (servido pelo FastAPI via StaticFiles) |
| Background tasks | FastAPI BackgroundTasks + asyncio |
| ML Training | RunPod / Lambda Labs (GPU cloud) — FUTURO |
| Model Registry | HuggingFace Hub (repositório privado) — FUTURO |
| Monitoring | Sentry |

---

## 4. Processing Pipeline — 23 Stages (8 Blocos)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    PROCESSING PIPELINE — 23 STAGES                       │
│                                                                          │
│  ┌─── BLOCO 1: DOCUMENT ACQUISITION ─────────────────────────────────┐  │
│  │                                                                    │  │
│  │  [1] Upload PDFs + XSD                                            │  │
│  │      Frontend → POST /api/upload/{pdf,xsd}                       │  │
│  │      Múltiplos PDFs recomendados (1 obrigatório, 3-5 ideal)      │  │
│  │      Arquivos → Supabase Storage                                  │  │
│  │      Job criado → Supabase jobs table                             │  │
│  │                                                                    │  │
│  │  [2] PDF Parsing + Extraction                                     │  │
│  │      PyMuPDF (fitz) em RAM, para CADA PDF:                       │  │
│  │                                                                    │  │
│  │      2a. Text Extraction                                          │  │
│  │          - TextBlocks com bbox, font, font_size                  │  │
│  │          - Vetores gráficos (linhas, retângulos)                 │  │
│  │          - Page screenshots (PNG) para Vision AI                 │  │
│  │                                                                    │  │
│  │      2b. Text Reconstruction                                      │  │
│  │          PDF engines fragmentam texto em múltiplos spans:        │  │
│  │          "Cl" + "iente" → "Cliente"                               │  │
│  │          Merge por: proximidade Y, font similar, espaçamento X   │  │
│  │          CRÍTICO: sem isso, anchors e fields falham               │  │
│  │                                                                    │  │
│  │      2c. Font Extraction → CSS Mapping                            │  │
│  │          Extrai metadata de fontes por span:                      │  │
│  │          { font:"Helvetica-Bold", size:12 }                       │  │
│  │          Normaliza para CSS:                                       │  │
│  │          font-family: Arial, sans-serif;                          │  │
│  │          font-size: 12px; font-weight: bold;                      │  │
│  │          Propósito: preservar fidelidade visual do template       │  │
│  │                                                                    │  │
│  │      2d. Image Extraction                                          │  │
│  │          page.get_images() → logos, selos, ícones                 │  │
│  │          Salva em Supabase Storage: /assets/{jobId}/              │  │
│  │          Gera: { type:"image", src:"logo.png", w, h, bbox }      │  │
│  │                                                                    │  │
│  │      2e. Chart Detection (PRIORIDADE BAIXA)                        │  │
│  │          Detecta regiões de gráficos → Chart.js blocks            │  │
│  │          Tipos: bar, line, pie                                     │  │
│  │          Implementar no final — raro em PlanetPress               │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─── BLOCO 2: LAYOUT DISCOVERY ─────────────────────────────────────┐  │
│  │                                                                    │  │
│  │  [3] Layout Skeleton Builder                                      │  │
│  │      Cria esqueleto estrutural de cada página:                   │  │
│  │      - text blocks + bounding boxes                               │  │
│  │      - áreas candidatas a tabela                                  │  │
│  │      - zonas de layout (regiões geométricas)                     │  │
│  │                                                                    │  │
│  │      3a. Grid Detection                                            │  │
│  │          Clustering de coordenadas X/Y para detectar grid:        │  │
│  │          - Rows (agrupamento por Y similar)                       │  │
│  │          - Columns (agrupamento por X similar)                    │  │
│  │          Resultado: { columns: 2, rows: 3 }                      │  │
│  │          Gera CSS Grid em vez de position:absolute:               │  │
│  │          display:grid; grid-template-columns:150px 1fr;           │  │
│  │          CRÍTICO para fidelidade e responsividade do template     │  │
│  │                                                                    │  │
│  │      Resultado: LayoutSkeleton por página (inclui grid info)     │  │
│  │                                                                    │  │
│  │  [4] Page Layout Clustering                                       │  │
│  │      scikit-learn KMeans sobre feature vectors:                  │  │
│  │      - num_blocks, avg_font_size, table_count                    │  │
│  │      - text_density, header_height_ratio                         │  │
│  │      PDFs de 500 páginas → processa ~5-10 representantes         │  │
│  │                                                                    │  │
│  │  [5] Representative Page Selection                                │  │
│  │      Seleciona o melhor representante de cada cluster.           │  │
│  │      Se múltiplos PDFs: usa páginas de diferentes exemplos.      │  │
│  │                                                                    │  │
│  │  [6] Layout Fingerprint Generation                                │  │
│  │      Gera assinatura estrutural do layout:                       │  │
│  │      {                                                            │  │
│  │        tableCount: 1,                                             │  │
│  │        columnCount: 3,                                            │  │
│  │        headerBlocks: 4,                                           │  │
│  │        bodyZoneRatio: 0.65,                                       │  │
│  │        footerPresent: true                                        │  │
│  │      }                                                            │  │
│  │      Hash do fingerprint → usado para lookup no registry.        │  │
│  │                                                                    │  │
│  │  [7] Layout Registry Lookup                                       │  │
│  │      Consulta layout_registry no Supabase:                       │  │
│  │      - Se fingerprint existe → template_id encontrado            │  │
│  │        → SKIP direto para stage [19] (Data Mapping) com          │  │
│  │          template existente, apenas remapear campos               │  │
│  │      - Se não existe → continuar pipeline normal                 │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─── BLOCO 3: LAYOUT INTELLIGENCE ──────────────────────────────────┐  │
│  │  (requer múltiplos PDFs para máxima eficácia)                     │  │
│  │                                                                    │  │
│  │  [8] Layout Alignment                                             │  │
│  │      Alinha coordenadas entre múltiplos PDFs de exemplo.         │  │
│  │      Normaliza pequenas diferenças de posicionamento.            │  │
│  │      Com 1 PDF: stage executado trivialmente (auto-align).       │  │
│  │                                                                    │  │
│  │  [9] Multi-Example Layout Analysis                                │  │
│  │      Compara múltiplos documentos para detectar:                 │  │
│  │      - Labels (texto que NÃO muda entre exemplos)                │  │
│  │      - Valores dinâmicos (texto que MUDA entre exemplos)         │  │
│  │                                                                    │  │
│  │      Exemplo:                                                     │  │
│  │        PDF A: "Cliente: João"                                     │  │
│  │        PDF B: "Cliente: Maria"                                    │  │
│  │        → "Cliente" = label, valor = campo dinâmico                │  │
│  │                                                                    │  │
│  │      Com 1 PDF: Vision AI assume toda inferência (stage útil     │  │
│  │      mas com menor confiança).                                    │  │
│  │                                                                    │  │
│  │  [10] Layout Stability Analysis                                   │  │
│  │       Classifica blocos do layout:                                │  │
│  │       - STABLE: presente em todos os exemplos, mesma posição     │  │
│  │       - VARIABLE: presente em todos, conteúdo muda               │  │
│  │       - OPTIONAL: presente apenas em alguns exemplos             │  │
│  │                                                                    │  │
│  │       Com 1 PDF: tudo classificado como STABLE ou VARIABLE       │  │
│  │       (sem dados para inferir OPTIONAL).                          │  │
│  │                                                                    │  │
│  │  [11] Variant Detection                                           │  │
│  │       Detecta blocos condicionais comparando exemplos:           │  │
│  │       - Bloco aparece em PDF A mas não em PDF B                  │  │
│  │       → Gera lógica condicional no template:                     │  │
│  │         <!-- ko if: saldoNegativo -->                             │  │
│  │         <div class="aviso">Saldo negativo</div>                  │  │
│  │         <!-- /ko -->                                              │  │
│  │                                                                    │  │
│  │       Com 1 PDF: stage SKIP (sem comparação possível).           │  │
│  │                                                                    │  │
│  │  [12] Structural Layout Normalization                             │  │
│  │       Converte layout raw em zonas lógicas:                      │  │
│  │       HEADER, BODY, TABLE, FOOTER                                │  │
│  │       Remove dependência de coordenadas de página específicas.   │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─── BLOCO 4: TABLE INTELLIGENCE ───────────────────────────────────┐  │
│  │  ⚠️  REGRA: Tables ANTES de Anchor Detection                     │  │
│  │      (evita interpretar headers de tabela como campos)            │  │
│  │                                                                    │  │
│  │  [13] Table Identity Detection                                    │  │
│  │       Detecta tabelas e atribui identificadores:                 │  │
│  │       - transactions_table                                        │  │
│  │       - fees_table                                                │  │
│  │       - coverage_table                                            │  │
│  │       Usa: linhas horizontais/verticais, alinhamento de colunas, │  │
│  │       padrão de repetição de rows.                                │  │
│  │                                                                    │  │
│  │  [14] Table Continuation Detection                                │  │
│  │       Detecta tabelas que continuam em múltiplas páginas:        │  │
│  │       - Headers repetidos                                         │  │
│  │       - Colunas alinhadas entre páginas                          │  │
│  │       - Padrão de rows mantido                                    │  │
│  │       → Marca como single logical table com pagination rules     │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─── BLOCO 5: LAYOUT SEMANTICS ─────────────────────────────────────┐  │
│  │                                                                    │  │
│  │  [15] Layout Zone Detection                                       │  │
│  │       Confirma zonas macro do documento:                         │  │
│  │       HEADER, BODY, FOOTER, SIDEBAR                              │  │
│  │       Refina resultado do stage [12] com informação de tabelas.  │  │
│  │                                                                    │  │
│  │  [16] Anchor Detection                                            │  │
│  │       Detecta âncoras textuais (labels) usados para mapear       │  │
│  │       campos:                                                     │  │
│  │       - "Cliente", "CPF", "Data", "Valor"                        │  │
│  │       Executado DEPOIS de Table Intelligence (stage 13-14)       │  │
│  │       para não confundir headers de tabela com anchors.          │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─── BLOCO 6: VISION INTERPRETATION ────────────────────────────────┐  │
│  │                                                                    │  │
│  │  [17] Vision Analysis                                             │  │
│  │       GPT-4o Vision (API) — page screenshot + TextBlocks:        │  │
│  │       → pares label↔valor com bounding boxes                     │  │
│  │       → hierarquia de seções                                      │  │
│  │       → reading order                                             │  │
│  │       → estrutura de tabelas (headers, rows, cols)               │  │
│  │       → relações visuais (proximity, alignment)                  │  │
│  │       Fallback: LayoutLMv3 fine-tuned (local) — FUTURO           │  │
│  │                                                                    │  │
│  │  [18] Vision Self-Check                                           │  │
│  │       Valida output da Vision para consistência:                 │  │
│  │       - Alinhamento label-value                                   │  │
│  │       - Posicionamento de campos                                  │  │
│  │       - Consistência de estrutura de tabelas                     │  │
│  │       Se inconsistências detectadas:                              │  │
│  │       → Reprocessar Vision com contexto adicional                │  │
│  │       → Ou reduzir confidence score                              │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─── BLOCO 7: DATA MAPPING ─────────────────────────────────────────┐  │
│  │  ⚠️  REGRA: Schema (XSD) aplicado DEPOIS da Vision              │  │
│  │      (evita forçar mapeamentos incorretos)                        │  │
│  │                                                                    │  │
│  │  [19] Field Intelligence Mapping                                  │  │
│  │       Camada 1: pgvector similarity search                       │  │
│  │         Busca embeddings de labels já conhecidos                  │  │
│  │         Se similaridade > 0.85 → mapeamento automático           │  │
│  │       Camada 2: LLM matching (Gemini 2.0 Flash)                  │  │
│  │         Para labels novos sem match no pgvector                   │  │
│  │       Camada 3: MiniLM fine-tuned (FUTURO)                       │  │
│  │         Modelo especializado no domínio PlanetPress              │  │
│  │       → Salvar embeddings novos no pgvector                      │  │
│  │                                                                    │  │
│  │  [20] Format Detection                                            │  │
│  │       Camada 1: Regex determinístico                              │  │
│  │         CPF, CNPJ, CEP, telefone, data BR, moeda BR             │  │
│  │       Camada 2: BERT fine-tuned (FUTURO)                         │  │
│  │       Camada 3: LLM fallback (Gemini Flash)                      │  │
│  │       → Template inclui formatters:                               │  │
│  │         data-bind="text: formatCpf(cpf)"                         │  │
│  │                                                                    │  │
│  │  [21] Confidence Scoring                                          │  │
│  │       Cada elemento recebe confidence score:                     │  │
│  │       - ≥ 0.8 → automático (✅)                                  │  │
│  │       - 0.6–0.8 → review opcional (🟡)                           │  │
│  │       - < 0.6 → review obrigatório (🔴)                         │  │
│  │       Claude Sonnet: análise visual PDF vs template              │  │
│  │       → fidelityScore, fidelityComment, iaSuggestions[]          │  │
│  │                                                                    │  │
│  │       Template Confidence Score (agregado):                       │  │
│  │       - Agrega scores individuais de todos os campos/tabelas     │  │
│  │       - Fatores: layout stability, anchor detection, grid         │  │
│  │         quality, field variability, vision agreement              │  │
│  │       - 95-100% → auto-approved                                   │  │
│  │       - 80-95%  → review recommended                              │  │
│  │       - < 80%   → human review required                           │  │
│  │       → templateConfidenceScore (exibido no frontend)             │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─── BLOCO 8: VALIDATION + TEMPLATE GENERATION ─────────────────────┐  │
│  │                                                                    │  │
│  │  [22] Layout Consistency Validation                               │  │
│  │       Validação cruzada: estrutura interpretada pela Vision      │  │
│  │       vs Layout Skeleton detectado no Bloco 2.                   │  │
│  │       Garante que o template final respeita a geometria real.    │  │
│  │       Se divergência > threshold:                                 │  │
│  │       → reprocessar Vision com skeleton como contexto extra      │  │
│  │                                                                    │  │
│  │  [23] Template Generation (3 sub-steps)                            │  │
│  │                                                                    │  │
│  │       23a. HTML Structure Generation                               │  │
│  │            Layout Model → HTML semântico                          │  │
│  │            Seções → <div class="section section--header">         │  │
│  │            Tables → <table> com estrutura de rows/columns         │  │
│  │            Conditionals → <!-- ko if: --> (de Variant Detection)  │  │
│  │            Images → <img src="/assets/logo.png">                  │  │
│  │                                                                    │  │
│  │       23b. CSS Layout Generation                                   │  │
│  │            Grid Detection (stage 3a) → CSS Grid layout            │  │
│  │            display:grid; grid-template-columns:150px 1fr;         │  │
│  │            Font Extraction (stage 2c) → font-family, size, weight │  │
│  │            Pagination rules para tabelas multi-página             │  │
│  │                                                                    │  │
│  │       23c. Knockout Binding Generation                             │  │
│  │            Bindings → <span data-bind="text: campo">              │  │
│  │            Formatters → ko.computed com filtros BR                │  │
│  │            Tables → data-bind="foreach: items"                    │  │
│  │            JS → ViewModel com ko.observable() por campo           │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ┌─── PÓS-PIPELINE ──────────────────────────────────────────────────┐  │
│  │  (operações após o pipeline core de 23 stages)                    │  │
│  │                                                                    │  │
│  │  [P1] Pagination Rules Injection                                  │  │
│  │       Regras de paginação para tabelas multi-página              │  │
│  │       (detectadas no stage 14)                                    │  │
│  │                                                                    │  │
│  │  [P2] Template Optimization                                       │  │
│  │       Minificação CSS, consolidação de classes repetidas         │  │
│  │                                                                    │  │
│  │  [P3] Human Review (Vue wizard — Steps 2-4)                      │  │
│  │       Tela 2 (Campos): PDF.js + Konva.js → anotação interativa  │  │
│  │       Tela 3 (Layout): margens, fontes, cabeçalho/rodapé        │  │
│  │       Tela 4 (Geração): Monaco Editor, preview, "Melhorar IA"   │  │
│  │       → Correções persistidas no Supabase                        │  │
│  │                                                                    │  │
│  │       Template Coverage Mode:                                      │  │
│  │       Overlay visual no PDF mostrando mapeamento:                 │  │
│  │       🟢 Verde = mapeado | 🔴 Vermelho = não mapeado             │  │
│  │       🟡 Amarelo = detectado mas não confirmado                   │  │
│  │       → Coverage score: "93% dos elementos mapeados"              │  │
│  │                                                                    │  │
│  │       Auto Layout Fix (PRIORIDADE BAIXA):                           │  │
│  │       Normalização automática de spacing:                          │  │
│  │       - Alinhamento de colunas                                     │  │
│  │       - Espaçamento de rows                                        │  │
│  │       - Gaps do grid                                                │  │
│  │       - Inconsistências de font                                    │  │
│  │       Implementar no final — nice-to-have                          │  │
│  │                                                                    │  │
│  │  [P4] Learning Engine                                             │  │
│  │       Online: atualiza pgvector embeddings + format_patterns     │  │
│  │       Batch (FUTURO): fine-tune LayoutLMv3, MiniLM, BERT        │  │
│  │                                                                    │  │
│  │  [P5] Layout Registry Update                                      │  │
│  │       Após template aprovado pelo operador:                      │  │
│  │       → Registra fingerprint + template_id no layout_registry    │  │
│  │       → Próximo documento com mesmo fingerprint → skip pipeline  │  │
│  │                                                                    │  │
│  │  [P6] Template Registry + Export                                  │  │
│  │       → Supabase templates table + Storage                       │  │
│  │       → ZIP autocontido (index.html, css/, js/, fonts/, img/)    │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Supabase — Data Layer

### 5.1 Schema do Banco de Dados

```sql
-- Habilitar pgvector
create extension if not exists vector;

-- ============================================================
-- JOBS — Estado do pipeline
-- ============================================================
create table jobs (
  id uuid primary key default gen_random_uuid(),
  user_id text,
  status text not null default 'pending'
    check (status in ('pending', 'uploading', 'parsing', 'skeleton',
                       'clustering', 'fingerprinting', 'registry_lookup',
                       'aligning', 'analyzing', 'stability', 'variants',
                       'normalizing', 'table_detection', 'table_continuation',
                       'zone_detection', 'anchor_detection',
                       'vision', 'vision_check',
                       'mapping', 'format_detection', 'scoring',
                       'consistency_check', 'generating',
                       'reviewing', 'done', 'error')),
  error_msg text,
  current_stage int default 0,    -- 1-23 (stage atual do pipeline)
  total_stages int default 23,
  pdf_count int default 1,        -- quantidade de PDFs enviados
  pdf_storage_paths text[],       -- array de paths para múltiplos PDFs
  xsd_storage_path text,
  pdf_page_count int,
  xsd_field_count int,
  layout_fingerprint_hash text,   -- hash do fingerprint (para lookup)
  matched_template_id uuid,       -- se layout registry encontrou match
  processing_time_ms int,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================================
-- LAYOUT REGISTRY — Templates reutilizáveis por fingerprint
-- ============================================================
create table layout_registry (
  id uuid primary key default gen_random_uuid(),
  fingerprint_hash text unique not null,
  fingerprint jsonb not null,
  -- fingerprint: {tableCount, columnCount, headerBlocks, bodyZoneRatio, footerPresent, ...}
  template_id uuid references templates,
  usage_count int default 1,
  last_used_at timestamptz default now(),
  created_at timestamptz default now()
);

create index idx_layout_registry_hash on layout_registry(fingerprint_hash);

-- ============================================================
-- LAYOUT SKELETONS — Esqueleto estrutural por página
-- ============================================================
create table layout_skeletons (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs on delete cascade,
  pdf_index int default 0,        -- qual PDF (0-based, para multi-PDF)
  page_index int not null,
  text_blocks jsonb not null,     -- [{text, bbox, font, font_size}]
  table_candidates jsonb,         -- [{bbox, row_count, col_count}]
  layout_zones jsonb,             -- [{type, bbox}]
  feature_vector float[] not null,
  created_at timestamptz default now()
);

create index idx_skeletons_job on layout_skeletons(job_id);

-- ============================================================
-- LAYOUT MODELS — Representação intermediária estruturada
-- ============================================================
create table layout_models (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs on delete cascade,
  page_index int not null,
  cluster_id text,
  sections jsonb not null,
  stability jsonb,        -- {block_id: "STABLE"|"VARIABLE"|"OPTIONAL"}
  variants jsonb,         -- [{condition, block_id, present_in_pdfs: [0,1,3]}]
  metadata jsonb,
  created_at timestamptz default now()
);

create index idx_layout_models_job on layout_models(job_id);

-- ============================================================
-- FIELD MAPPINGS — Mapeamento de campos com embeddings
-- ============================================================
create table field_mappings (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs on delete cascade,
  pdf_text text not null,
  json_path text,
  field_type text default 'text'
    check (field_type in ('text', 'date', 'currency', 'list', 'composite', 'cpf', 'cnpj', 'cep', 'phone')),
  confidence text default 'low'
    check (confidence in ('high', 'medium', 'low')),
  confidence_score float,
  status text default 'not_found'
    check (status in ('ok', 'ambiguous', 'not_found', 'optional')),
  stability text default 'variable'
    check (stability in ('stable', 'variable', 'optional')),
  candidates jsonb,
  is_manual boolean default false,
  page_ref int,
  bounding_box jsonb,
  data_value text,
  xsd_type text,
  format_detected text,
  embedding vector(384),
  created_at timestamptz default now()
);

create index idx_field_mappings_job on field_mappings(job_id);
create index idx_field_mappings_embedding on field_mappings
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ============================================================
-- TABLE DEFINITIONS — Tabelas detectadas no documento
-- ============================================================
create table table_definitions (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs on delete cascade,
  table_name text not null,       -- identificador (ex: "transactions")
  page_indices int[] not null,    -- páginas onde a tabela aparece
  is_multi_page boolean default false,
  headers jsonb not null,         -- ["Data", "Descrição", "Valor"]
  column_count int not null,
  row_count_estimate int,
  bbox_per_page jsonb,            -- {page_index: [x,y,w,h]}
  binding_array text,             -- campo XSD array (ex: "movimentacoes")
  created_at timestamptz default now()
);

create index idx_tables_job on table_definitions(job_id);

-- ============================================================
-- TEMPLATES — Templates gerados
-- ============================================================
create table templates (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs on delete cascade,
  html text,
  css text,
  js text,
  exemplo text,
  fidelity_score float,
  fidelity_comment text,
  ia_suggestions jsonb,
  conditionals jsonb,     -- [{condition, block_html}] de Variant Detection
  zip_storage_path text,
  version int default 1,
  created_at timestamptz default now()
);

create index idx_templates_job on templates(job_id);

-- ============================================================
-- HUMAN FEEDBACK — Correções do operador (Learning System)
-- ============================================================
create table human_feedback (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs on delete cascade,
  field_mapping_id uuid references field_mappings,
  feedback_type text not null
    check (feedback_type in ('correction', 'approval', 'rejection', 'region_created', 'region_adjusted')),
  original_json_path text,
  corrected_json_path text,
  original_value text,
  corrected_value text,
  metadata jsonb,
  created_at timestamptz default now()
);

create index idx_feedback_job on human_feedback(job_id);

-- ============================================================
-- LABEL EMBEDDINGS — Memória semântica (pgvector)
-- ============================================================
create table label_embeddings (
  id uuid primary key default gen_random_uuid(),
  label text not null,
  canonical_field text not null,
  embedding vector(384) not null,
  usage_count int default 1,
  source text default 'system'
    check (source in ('system', 'human_feedback', 'llm')),
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  unique(label, canonical_field)
);

create index idx_label_embeddings_vector on label_embeddings
  using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- ============================================================
-- FORMAT PATTERNS — Padrões de formato aprendidos
-- ============================================================
create table format_patterns (
  id uuid primary key default gen_random_uuid(),
  pattern text not null,
  format_type text not null
    check (format_type in ('cpf', 'cnpj', 'date', 'currency', 'cep', 'phone', 'email', 'percentage', 'custom')),
  example text,
  confidence float default 1.0,
  source text default 'system'
    check (source in ('system', 'human_feedback')),
  usage_count int default 0,
  created_at timestamptz default now()
);

-- ============================================================
-- PAGE CLUSTERS — Agrupamento de páginas por layout
-- ============================================================
create table page_clusters (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs on delete cascade,
  cluster_id text not null,
  representative_page int not null,
  page_indices int[] not null,
  feature_vector float[] not null,
  page_count int not null,
  created_at timestamptz default now()
);

create index idx_clusters_job on page_clusters(job_id);

-- ============================================================
-- FUNCTIONS — pgvector similarity search
-- ============================================================

-- Buscar labels similares por embedding
create or replace function match_labels(
  query_embedding vector(384),
  match_threshold float default 0.7,
  match_count int default 5
) returns table (
  id uuid,
  label text,
  canonical_field text,
  similarity float,
  usage_count int
) language plpgsql as $$
begin
  return query
    select
      le.id,
      le.label,
      le.canonical_field,
      1 - (le.embedding <=> query_embedding) as similarity,
      le.usage_count
    from label_embeddings le
    where 1 - (le.embedding <=> query_embedding) > match_threshold
    order by le.embedding <=> query_embedding
    limit match_count;
end;
$$;

-- Buscar field mappings similares de jobs anteriores
create or replace function match_previous_mappings(
  query_embedding vector(384),
  match_threshold float default 0.8,
  match_count int default 3
) returns table (
  pdf_text text,
  json_path text,
  field_type text,
  similarity float,
  job_id uuid
) language plpgsql as $$
begin
  return query
    select
      fm.pdf_text,
      fm.json_path,
      fm.field_type,
      1 - (fm.embedding <=> query_embedding) as similarity,
      fm.job_id
    from field_mappings fm
    where fm.embedding is not null
      and fm.status = 'ok'
      and fm.is_manual = false
      and 1 - (fm.embedding <=> query_embedding) > match_threshold
    order by fm.embedding <=> query_embedding
    limit match_count;
end;
$$;
```

### 5.2 Storage Buckets

```
supabase-storage/
  uploads/
    {job_id}/
      pdf-0.pdf         ← primeiro PDF
      pdf-1.pdf         ← segundo PDF (se houver)
      pdf-2.pdf         ← terceiro PDF (se houver)
      schema.xsd
  templates/
    {job_id}/
      template-v1.zip
  page-images/
    {job_id}/
      pdf0-page-001.png
      pdf0-page-002.png
      pdf1-page-001.png  ← de outro PDF
```

---

## 6. Service Architecture — 7 Módulos

### 6.1 Visão Geral dos Módulos

```
┌─────────────────────────────────────────────────────────────────────┐
│  DocumentAnalysisModule                                              │
│  Stages: [1] Upload, [2] PDF Parsing                                │
│  Deps: PyMuPDF, Pillow, lxml                                        │
├─────────────────────────────────────────────────────────────────────┤
│  LayoutDiscoveryModule                                               │
│  Stages: [3] Skeleton, [4] Clustering, [5] Representative,         │
│          [6] Fingerprint, [7] Registry Lookup                       │
│  Deps: scikit-learn, numpy, Supabase                                │
├─────────────────────────────────────────────────────────────────────┤
│  LayoutIntelligenceModule                                            │
│  Stages: [8] Alignment, [9] Multi-Example, [10] Stability,         │
│          [11] Variant Detection, [12] Normalization                 │
│  Deps: numpy (comparação de layouts)                                │
├─────────────────────────────────────────────────────────────────────┤
│  TableIntelligenceModule                                             │
│  Stages: [13] Table Identity, [14] Table Continuation               │
│  Deps: PyMuPDF (linhas/retângulos), numpy                           │
├─────────────────────────────────────────────────────────────────────┤
│  VisionModule                                                        │
│  Stages: [15] Zone Detection, [16] Anchor Detection,               │
│          [17] Vision Analysis, [18] Vision Self-Check               │
│  Deps: OpenRouter (GPT-4o Vision), LayoutLMv3 (FUTURO)              │
├─────────────────────────────────────────────────────────────────────┤
│  DataMappingModule                                                   │
│  Stages: [19] Field Mapping, [20] Format Detection,                │
│          [21] Confidence Scoring                                     │
│  Deps: sentence-transformers, pgvector, OpenRouter (Gemini, Claude) │
├─────────────────────────────────────────────────────────────────────┤
│  TemplateEngineModule                                                │
│  Stages: [22] Layout Consistency Validation, [23] Template Gen      │
│  Post: Pagination, Optimization, Export                             │
│  Deps: Knockout.js patterns, ZIP builder                            │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Pipeline Orchestrator

```python
# services/pipeline_orchestrator.py

class PipelineOrchestrator:
    """
    Orquestra os 23 stages do pipeline + operações pós-pipeline.
    Emite progresso via SSE para o frontend.
    """

    def __init__(self, modules: dict):
        self.doc_analysis = modules['doc_analysis']
        self.layout_discovery = modules['layout_discovery']
        self.layout_intelligence = modules['layout_intelligence']
        self.table_intelligence = modules['table_intelligence']
        self.vision = modules['vision']
        self.data_mapping = modules['data_mapping']
        self.template_engine = modules['template_engine']

    async def run(self, job_id: str, sse_callback) -> PipelineResult:

        # === BLOCO 1: DOCUMENT ACQUISITION ===
        await sse_callback(1, 23, "Parsing PDFs...")
        pdf_data_list = await self.doc_analysis.parse_all_pdfs(job_id)  # [2]

        # === BLOCO 2: LAYOUT DISCOVERY ===
        await sse_callback(3, 23, "Building layout skeleton...")
        skeletons = await self.layout_discovery.build_skeletons(pdf_data_list)  # [3]

        await sse_callback(4, 23, "Clustering pages...")
        clusters = await self.layout_discovery.cluster_pages(skeletons)  # [4]

        await sse_callback(5, 23, "Selecting representative pages...")
        representatives = await self.layout_discovery.select_representatives(clusters)  # [5]

        await sse_callback(6, 23, "Generating layout fingerprint...")
        fingerprint = await self.layout_discovery.generate_fingerprint(skeletons)  # [6]

        await sse_callback(7, 23, "Checking layout registry...")
        registry_match = await self.layout_discovery.lookup_registry(fingerprint)  # [7]

        if registry_match:
            # Layout já conhecido → skip para Data Mapping com template existente
            await sse_callback(19, 23, "Layout known — remapping fields...")
            # Pular direto para stage 19 com template existente
            return await self._remap_existing_template(
                job_id, registry_match, pdf_data_list, skeletons, sse_callback
            )

        # === BLOCO 3: LAYOUT INTELLIGENCE ===
        multi_pdf = len(pdf_data_list) > 1

        await sse_callback(8, 23, "Aligning layouts...")
        aligned = await self.layout_intelligence.align(skeletons, pdf_data_list)  # [8]

        await sse_callback(9, 23, "Analyzing multi-example patterns...")
        labels_vs_values = await self.layout_intelligence.multi_example_analysis(
            aligned, skip=not multi_pdf
        )  # [9]

        await sse_callback(10, 23, "Classifying layout stability...")
        stability = await self.layout_intelligence.stability_analysis(
            aligned, skip=not multi_pdf
        )  # [10]

        await sse_callback(11, 23, "Detecting conditional variants...")
        variants = await self.layout_intelligence.detect_variants(
            aligned, skip=not multi_pdf
        )  # [11]

        await sse_callback(12, 23, "Normalizing layout structure...")
        normalized = await self.layout_intelligence.normalize(aligned)  # [12]

        # === BLOCO 4: TABLE INTELLIGENCE ===
        await sse_callback(13, 23, "Detecting tables...")
        tables = await self.table_intelligence.detect_tables(normalized, skeletons)  # [13]

        await sse_callback(14, 23, "Detecting multi-page tables...")
        tables = await self.table_intelligence.detect_continuations(tables, skeletons)  # [14]

        # === BLOCO 5: LAYOUT SEMANTICS ===
        await sse_callback(15, 23, "Detecting layout zones...")
        zones = await self.vision.detect_zones(normalized, tables)  # [15]

        await sse_callback(16, 23, "Detecting text anchors...")
        anchors = await self.vision.detect_anchors(normalized, tables)  # [16]

        # === BLOCO 6: VISION INTERPRETATION ===
        await sse_callback(17, 23, "Vision AI analyzing document...")
        interpretation = await self.vision.analyze(
            representatives, skeletons, zones, anchors, labels_vs_values
        )  # [17]

        await sse_callback(18, 23, "Validating Vision output...")
        interpretation = await self.vision.self_check(
            interpretation, skeletons
        )  # [18]

        # === BLOCO 7: DATA MAPPING ===
        await sse_callback(19, 23, "Mapping fields to schema...")
        mappings = await self.data_mapping.map_fields(
            interpretation, xsd_fields, anchors
        )  # [19]

        await sse_callback(20, 23, "Detecting formats...")
        formats = await self.data_mapping.detect_formats(mappings)  # [20]

        await sse_callback(21, 23, "Computing confidence scores...")
        scored = await self.data_mapping.compute_confidence(
            mappings, formats, stability
        )  # [21]

        # === BLOCO 8: VALIDATION + GENERATION ===
        await sse_callback(22, 23, "Validating layout consistency...")
        validated = await self.template_engine.validate_consistency(
            interpretation, skeletons
        )  # [22]

        await sse_callback(23, 23, "Generating template...")
        template = await self.template_engine.generate(
            validated, scored, tables, variants, stability
        )  # [23]

        return PipelineResult(
            template=template,
            mappings=scored,
            tables=tables,
            fingerprint=fingerprint,
            variants=variants,
            stability=stability,
        )
```

---

## 7. Layout Model

### 7.1 Pydantic Models

```python
# models/layout_model.py
from pydantic import BaseModel
from enum import Enum

class StabilityClass(str, Enum):
    STABLE = "stable"
    VARIABLE = "variable"
    OPTIONAL = "optional"

class FontInfo(BaseModel):
    family: str               # ex: "Helvetica-Bold"
    size: float               # ex: 12.0
    weight: str = "normal"    # "normal", "bold"
    css_family: str | None    # normalizado: "Arial, sans-serif"
    css_size: str | None      # "12px"
    css_weight: str | None    # "bold"

class ImageElement(BaseModel):
    src: str                  # path no Storage: "/assets/{jobId}/logo.png"
    bbox: tuple[float, float, float, float]
    width: int
    height: int
    alt: str | None = None

class GridInfo(BaseModel):
    columns: int
    rows: int
    column_widths: list[str]  # ex: ["150px", "1fr"]
    row_heights: list[str] | None = None
    css_template: str         # "display:grid; grid-template-columns:150px 1fr;"

class LayoutElement(BaseModel):
    type: str         # 'label', 'value', 'image', 'table_cell', 'table_header'
    text: str | None
    bbox: tuple[float, float, float, float]  # x, y, w, h (normalized 0-1)
    binding: str | None       # campo do XSD mapeado
    format: str | None        # 'cpf', 'date', 'currency', etc.
    font: FontInfo | None     # font metadata + CSS mapping
    is_label: bool = False
    confidence: float = 0.0
    stability: StabilityClass = StabilityClass.VARIABLE

class TableDefinition(BaseModel):
    table_id: str             # identificador (ex: "transactions")
    headers: list[str]
    binding_array: str | None
    column_bindings: list[str | None]
    column_formats: list[str | None]
    is_multi_page: bool = False
    page_indices: list[int] = []

class VariantBlock(BaseModel):
    condition: str            # expressão (ex: "saldoNegativo")
    block_elements: list[LayoutElement]
    present_in_pdfs: list[int]  # índices dos PDFs onde aparece

class LayoutSection(BaseModel):
    type: str           # 'header', 'body', 'table', 'footer', 'sidebar'
    bbox: tuple[float, float, float, float]
    elements: list[LayoutElement]
    table: TableDefinition | None = None
    variants: list[VariantBlock] = []

class PageLayout(BaseModel):
    page_index: int
    cluster_id: str
    sections: list[LayoutSection]
    images: list[ImageElement] = []
    grid: GridInfo | None = None
    reading_order: list[int] | None = None
    stability_map: dict[str, StabilityClass] = {}

class LayoutFingerprint(BaseModel):
    table_count: int
    column_counts: list[int]
    header_block_count: int
    body_zone_ratio: float
    footer_present: bool
    hash: str           # hash determinístico para lookup

class TemplateConfidence(BaseModel):
    overall_score: float      # 0.0-1.0 (agregado)
    layout_stability: float   # contribuição da estabilidade
    anchor_detection: float   # contribuição dos anchors
    grid_quality: float       # contribuição do grid detection
    field_variability: float  # contribuição da variabilidade
    vision_agreement: float   # contribuição do Vision Self-Check
    level: str                # "auto_approved" | "review_recommended" | "human_required"

class LayoutModel(BaseModel):
    pages: list[PageLayout]
    fingerprint: LayoutFingerprint
    metadata: dict  # {fonts_used, dominant_colors, page_size, orientation}
    pdf_count: int = 1
    variants: list[VariantBlock] = []
    template_confidence: TemplateConfidence | None = None
```

---

## 8. Konva.js — Anotação Interativa sobre PDF

(Mantido da v4.0 — sem alterações)

### 8.1 Arquitetura de Layers

```
┌─────────────────────────────────────┐
│  Canvas Container (Tela 2)          │
│                                     │
│  Layer 1: PDF.js                    │
│    └── Renderiza a página do PDF    │
│                                     │
│  Layer 2: Konva.js (overlay)        │
│    ├── Bounding boxes existentes    │
│    │   (cores: ✅verde 🟡amarelo    │
│    │    🔴vermelho)                 │
│    ├── Região sendo desenhada       │
│    └── Handles de resize            │
│                                     │
│  Interações:                        │
│  - Click em bbox → seleciona campo  │
│  - Drag no canvas → desenha região  │
│  - Drag em handle → resize região   │
│  - Double-click → associar campo    │
│  - Right-click → menu contextual    │
└─────────────────────────────────────┘
```

### 8.2 Componente Vue

```typescript
// organisms/PdfAnnotator.vue

interface AnnotationRegion {
  id: string
  x: number         // normalized 0-1
  y: number
  width: number
  height: number
  fieldId: string | null
  status: 'ok' | 'ambiguous' | 'not_found'
  stability: 'stable' | 'variable' | 'optional'  // NOVO v5.0
  source: 'ai' | 'manual'
}
```

---

## 9. Learning System

(Mantido da v4.0 — sem alterações estruturais)

### 9.1 Online Learning (implementar agora)

Operador corrige mapeamento → POST /api/feedback → atualiza pgvector + format_patterns.

### 9.2 Layout Registry Learning (NOVO v5.0)

Após template aprovado pelo operador:
1. Salvar fingerprint + template_id no `layout_registry`
2. Próximo documento com mesmo fingerprint → skip pipeline, apenas remapear campos

### 9.3 Batch Fine-Tuning (FUTURO)

Quando volume justificar (~50+ docs): fine-tune MiniLM, LayoutLMv3, BERT.

---

## 10. API REST — Endpoints

```
# ============================================================
# UPLOAD
# ============================================================
POST   /api/upload/pdf          Upload PDF (múltiplos aceitos) → Supabase Storage
POST   /api/upload/xsd          Upload XSD → Supabase Storage

# ============================================================
# PIPELINE
# ============================================================
POST   /api/jobs                Inicia pipeline completo (23 stages)
GET    /api/progress/{jobId}    SSE — progresso em tempo real (stage X/23)
GET    /api/result/{jobId}      Resultado da extração + mapeamento

# ============================================================
# AI (chamadas individuais para re-processamento)
# ============================================================
POST   /api/ai/segment         Segmentar layout de uma página (Vision)
POST   /api/ai/interpret       Interpretar layout (Vision)
POST   /api/ai/match           Matching semântico (Gemini + pgvector)
POST   /api/ai/fidelity        Score de fidelidade (Claude Vision)
POST   /api/ai/correct         Auto-correção HTML/CSS (Claude)

# ============================================================
# GENERATION
# ============================================================
POST   /api/generate            Gera template Knockout a partir do Layout Model
GET    /api/preview/{jobId}     HTML renderizável (cache efêmero)

# ============================================================
# EXPORT
# ============================================================
GET    /api/export/{jobId}/zip  Download ZIP autocontido

# ============================================================
# FEEDBACK (Learning System)
# ============================================================
POST   /api/feedback            Registra correção do operador
GET    /api/feedback/stats      Estatísticas do learning system

# ============================================================
# LAYOUT REGISTRY
# ============================================================
GET    /api/registry            Lista layouts registrados
GET    /api/registry/{hash}     Busca template por fingerprint hash

# ============================================================
# LIBRARIES
# ============================================================
GET    /api/libraries           Lista assets (fonts, CSS, JS)
POST   /api/libraries/upload    Adiciona asset
DELETE /api/libraries/{tipo}/{nome}  Remove asset

# ============================================================
# ADMIN
# ============================================================
GET    /api/health              Health check
GET    /api/stats               Estatísticas de uso
```

---

## 11. Estrutura do Repositório

```
migrador-planet/
├── frontend/                         # Vue 3 app
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/index.ts
│   │   ├── stores/
│   │   │   ├── session.ts
│   │   │   ├── mapping.ts
│   │   │   ├── layout.ts
│   │   │   └── generation.ts
│   │   ├── atoms/
│   │   ├── molecules/
│   │   ├── organisms/
│   │   │   ├── AppHeader.vue
│   │   │   ├── PdfAnnotator.vue      # PDF.js + Konva.js
│   │   │   ├── PDFViewer.vue
│   │   │   ├── FieldMappingTable.vue
│   │   │   ├── FieldDetailPanel.vue
│   │   │   ├── MonacoTabs.vue
│   │   │   ├── ChartjsConfigPanel.vue
│   │   │   ├── LayoutControls.vue
│   │   │   ├── LayoutPreview.vue
│   │   │   ├── ExportChecklist.vue
│   │   │   ├── BibliotecasModal.vue
│   │   │   └── WizardStepper.vue
│   │   ├── templates/
│   │   ├── pages/
│   │   │   ├── HomePage.vue          # Tela 0
│   │   │   ├── UploadPage.vue        # Tela 1 (multi-PDF)
│   │   │   ├── CamposPage.vue        # Tela 2 (PdfAnnotator)
│   │   │   ├── LayoutPage.vue        # Tela 3
│   │   │   ├── GeracaoPage.vue       # Tela 4
│   │   │   └── ExportarPage.vue      # Tela 5
│   │   ├── composables/
│   │   └── types/
│   └── package.json
│
├── backend/                          # FastAPI + AI Pipeline
│   ├── main.py
│   ├── routers/
│   │   ├── upload.py
│   │   ├── jobs.py
│   │   ├── progress.py
│   │   ├── ai.py
│   │   ├── generate.py
│   │   ├── preview.py
│   │   ├── export.py
│   │   ├── feedback.py
│   │   ├── registry.py              # ← NOVO: /api/registry
│   │   └── libraries.py
│   ├── services/
│   │   ├── pipeline_orchestrator.py  # ← NOVO: orquestra 23 stages
│   │   ├── document_analysis.py     # módulo: parsing, skeleton
│   │   ├── layout_discovery.py      # módulo: clustering, fingerprint, registry
│   │   ├── layout_intelligence.py   # módulo: alignment, multi-example, stability, variants
│   │   ├── table_intelligence.py    # módulo: table detection, continuation
│   │   ├── vision_module.py         # módulo: zones, anchors, vision, self-check
│   │   ├── data_mapping.py          # módulo: field mapping, format, confidence
│   │   ├── template_engine.py       # módulo: consistency, generation, optimization
│   │   ├── pdf_extractor.py         # PyMuPDF wrapper
│   │   ├── xsd_parser.py
│   │   ├── ai_vision.py             # GPT-4o Vision calls
│   │   ├── ai_matcher.py            # Gemini + pgvector
│   │   ├── ai_fidelity.py           # Claude Sonnet
│   │   ├── semantic_embeddings.py   # SentenceTransformers
│   │   ├── format_detector.py       # regex + ML
│   │   ├── feedback_tracker.py
│   │   ├── job_manager.py
│   │   └── zip_builder.py
│   ├── models/
│   │   ├── job.py
│   │   ├── layout_model.py          # LayoutModel + Fingerprint + Variants
│   │   ├── layout_skeleton.py       # ← NOVO
│   │   ├── table_definition.py      # ← NOVO
│   │   ├── field_mapping.py
│   │   ├── extraction_result.py
│   │   ├── text_block.py
│   │   └── feedback.py
│   ├── core/
│   │   ├── config.py
│   │   └── supabase_client.py
│   ├── assets/
│   │   └── libraries/
│   └── requirements.txt
│
├── ml/                               # Machine Learning (FUTURO)
│   ├── training/
│   └── evaluation/
│
├── supabase/
│   └── migrations/
│       ├── 001_initial_schema.sql
│       ├── 002_pgvector_setup.sql
│       ├── 003_layout_registry.sql   # ← NOVO
│       ├── 004_table_definitions.sql # ← NOVO
│       └── 005_rls_policies.sql      # FUTURO
│
├── docs/
│   ├── prd.md
│   ├── architecture/
│   │   ├── document_ai_complete_master_architecture.md
│   │   ├── document_ai_pipeline_23_stages.md
│   │   ├── architecture-v4.md        # histórico
│   │   └── architecture-v5.md        # ESTE DOCUMENTO
│   ├── stories/
│   └── wireframes/
│
├── .env
├── .env.example
└── README.md
```

---

## 12. Epics de Implementação

| Epic | Descrição | Blocos Pipeline | Prioridade | Fase |
|------|-----------|----------------|------------|------|
| **Epic 5** | Supabase Integration | Schema v5, Storage, novo schema (registry, skeletons, tables) | CRÍTICA | Fase 1 |
| **Epic 6** | Vision AI Pipeline | GPT-4o segmentation + interpretation + self-check (stages 17-18) | CRÍTICA | Fase 1 |
| **Epic 7** | Layout Model + Template Gen | LayoutModel v5 (stability, variants, fingerprint), template gen com conditionals (stages 22-23) | ALTA | Fase 1 |
| **Epic 8** | Semantic Matching (pgvector) | Field mapping, format detection, confidence (stages 19-21) | ALTA | Fase 1 |
| **Epic 14** | Layout Discovery | Skeleton builder, clustering, fingerprint, registry (stages 3-7) | ALTA | Fase 1 |
| **Epic 15** | Layout Intelligence | Alignment, multi-example, stability, variants, normalization (stages 8-12) | ALTA | Fase 2 |
| **Epic 16** | Table Intelligence | Table identity, continuation detection (stages 13-14) | ALTA | Fase 2 |
| **Epic 17** | Layout Semantics | Zone detection, anchor detection (stages 15-16) | MÉDIA | Fase 2 |
| **Epic 9** | Konva.js — Anotação Interativa | PdfAnnotator, stability indicators | ALTA | Fase 2 |
| **Epic 10** | Pipeline Orchestrator | Orquestrador 23 stages, SSE granular, registry skip | MÉDIA | Fase 2 |
| **Epic 11** | Learning System Online | Feedback API, embeddings, registry update | MÉDIA | Fase 2 |
| **Epic 13** | PyMuPDF Migration | Substituir pdfplumber por PyMuPDF | MÉDIA | Fase 2 |
| **Epic 18** | Chart Detection | Detecção de gráficos → Chart.js blocks (stage 2e) | BAIXA | Fase 3 |
| **Epic 19** | Auto Layout Fix + Coverage Mode | Normalização de spacing, overlay de cobertura (pós-pipeline P3) | BAIXA | Fase 3 |
| **Epic 12** | Fine-Tuning Pipeline (FUTURO) | LayoutLMv3, MiniLM, BERT | BAIXA | Fase 3 |

**Ordem recomendada:** 5 → 6 → 14 → 7 → 8 → 16 → 15 → 17 → 9 → 10 → 13 → 11 → 18 → 19 → 12

---

## 13. Custo Estimado

### 13.1 Por Documento (1 PDF)

| Componente | Custo |
|-----------|-------|
| GPT-4o Vision (segmentação + interpretação + self-check) | ~$0.15 |
| Gemini 2.0 Flash (matching + format fallback) | ~$0.02 |
| Claude Sonnet (fidelity) | ~$0.05 |
| SentenceTransformers (local) | $0.00 |
| Supabase (storage + database) | ~$0.001 |
| **Total por documento (1 PDF)** | **~$0.22** |

### 13.2 Por Documento (3-5 PDFs — recomendado)

| Componente | Custo |
|-----------|-------|
| GPT-4o Vision (×3-5 PDFs, mas clustering reduz pages) | ~$0.25-0.40 |
| Layout Intelligence (local, CPU) | $0.00 |
| Gemini + Claude (mesmo) | ~$0.07 |
| **Total (3-5 PDFs)** | **~$0.32-0.47** |

---

## 14. NFRs

| NFR | Como atende |
|-----|-------------|
| NFR1 — Browser sem instalação | Mantido: web app puro |
| NFR3 — Precisão ≥ 80% | Melhorado: multi-example + table intelligence + vision self-check |
| NFR4 — 50 páginas em < 60s | Melhorado: clustering + registry skip |
| NFR5 — Fidelidade visual | Melhorado: Layout Consistency Validation |
| NFR7 — ZIP autocontido | Mantido |
| **NOVO — Registry reuse** | Layouts conhecidos → processamento em segundos |
| **NOVO — Conditional blocks** | Variant Detection gera <!-- ko if: --> |
| **NOVO — Multi-page tables** | Table Continuation Detection → pagination rules |

---

— Aria, arquitetando o futuro 🏗️
