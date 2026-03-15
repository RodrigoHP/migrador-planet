# Arquitetura Técnica v4.0 — Document AI Platform

**Versão:** 4.0
**Data:** 2026-03-14
**Autor:** @architect (Aria)
**Status:** Proposta
**Base:** DOCUMENT_AI_PLATFORM_MASTER_ARCHITECTURE.md + architecture.md v3.1

---

## Change Log

| Versão | Data | Descrição |
|--------|------|-----------|
| 3.0 | 2026-03-10 | Web app puro, stateless, sem banco, Levenshtein matching |
| 3.1 | 2026-03-10 | Gap review, ZIP autocontido, preview cache |
| **4.0** | **2026-03-14** | **Evolução para Document AI Platform: Supabase, Vision AI, Layout Model, Semantic Matching (pgvector), Page Clustering, Learning System (PyTorch + HuggingFace), Konva.js** |

---

## 1. Visão Geral

Plataforma de **Document AI** que converte PDFs estáticos do PlanetPress em templates HTML/Knockout.js reutilizáveis e dinâmicos. Combina processamento determinístico, modelos de visão (GPT-4o, LayoutLMv3), matching semântico com embeddings (pgvector), e um learning system que melhora com cada documento processado.

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
│  Document Processing:                                            │
│  ├── PyMuPDF         extração PDF (texto, coords, fontes, imgs)  │
│  ├── Page Clusterer  scikit-learn KMeans (agrupa páginas)        │
│  ├── Format Detector regex + modelo fine-tuned (BR formats)      │
│  │                                                               │
│  AI Pipeline (LiteLLM):                                          │
│  ├── GPT-4o Vision    segmentação + interpretação de layout      │
│  ├── Gemini 2.0 Flash matching semântico label→campo             │
│  ├── Claude Sonnet    fidelity scoring + auto-correção           │
│  │                                                               │
│  ML Models (PyTorch + HuggingFace):                              │
│  ├── LayoutLMv3       layout segmentation fine-tuned             │
│  ├── MiniLM fine-tuned  field matching especializado             │
│  ├── BERT fine-tuned    format detection BR                      │
│  │                                                               │
│  Template Generation:                                            │
│  ├── Layout Model     representação intermediária estruturada    │
│  └── Knockout.js gen  HTML + CSS + JS com data-bind              │
└──────────────────────────────────────────────────────────────────┘
                    ↕  HTTPS
┌──────────────────────────────────────────────────────────────────┐
│  SUPABASE                                                         │
│  ├── PostgreSQL + pgvector   jobs, mappings, embeddings, feedback │
│  ├── Storage                 PDFs, templates, ZIPs               │
│  ├── Auth                    FUTURO (quando multi-tenant)        │
│  └── Realtime                notificações (futuro)               │
└──────────────────────────────────────────────────────────────────┘
                    ↕  HTTPS
┌──────────────────────────────────────────────────────────────────┐
│  AI APIs                                                          │
│  ├── OpenAI API       GPT-4o Vision                              │
│  ├── Google AI        Gemini 2.0 Flash                           │
│  └── Anthropic API    Claude Sonnet                              │
└──────────────────────────────────────────────────────────────────┘
                    ↕  GPU Cloud (batch training)
┌──────────────────────────────────────────────────────────────────┐
│  ML TRAINING INFRA                                                │
│  ├── RunPod / Lambda Labs    GPU para fine-tuning                │
│  ├── HuggingFace Hub         model registry (privado)            │
│  └── Datasets (HF)           export Supabase → training data     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Decisões Arquiteturais

### 2.1 Mudanças em relação à v3.0

| Decisão v3.0 | Decisão v4.0 | Motivo |
|-------------|-------------|--------|
| Sem banco de dados | Supabase (PostgreSQL + pgvector) | Persistência de jobs, feedback, embeddings, templates |
| Levenshtein matching | LLM + Embeddings + pgvector | Matching semântico real para labels variantes |
| Sem Vision AI | GPT-4o Vision + LayoutLMv3 | Interpretação visual de layout e relações label↔valor |
| String concat templates | Layout Model → Knockout | Templates semânticos em vez de pixel-perfect |
| Sem learning | PyTorch + HuggingFace + feedback loop | Sistema que melhora com cada documento |
| Sem Konva.js | Konva.js para anotação interativa | Seleção visual de regiões no PDF |
| pdfplumber | PyMuPDF (fitz) | Acesso completo a fontes, vetores, imagens |

### 2.2 Decisões mantidas da v3.0

| Decisão | Motivo para manter |
|---------|-------------------|
| Web app puro (sem Electron/Tauri) | NFR1: zero instalação, acesso via URL |
| Vue 3 + TypeScript frontend | Stack já implementada e funcional |
| FastAPI backend | Melhor ecossistema Python para AI/ML |
| Knockout.js nos templates (não Jinja2) | Já implementado; preview reativo no browser; operador edita e vê resultado em tempo real |
| SSE para progresso | Funciona sem WebSocket, simples e suficiente |
| File System Access API | Acesso a arquivos locais sem deps |
| ZIP autocontido (NFR7) | Template funciona offline após download |

### 2.3 Knockout.js como Template Engine (não Jinja2)

O Master Architecture especifica Jinja2. Esta arquitetura substitui por Knockout.js porque:

1. **Já implementado** — template_generator.py gera Knockout bindings
2. **Preview reativo** — operador vê mudanças em tempo real no browser sem roundtrip ao servidor
3. **Client-side rendering** — template funciona abrindo index.html localmente
4. **Compatibilidade** — Knockout é o padrão dos templates PlanetPress existentes na organização

O template gerado usa `data-bind="text: campo"` em vez de `{{ campo }}`. O ViewModel Knockout com `ko.observable()` por campo substitui funcionalmente o `jinja2.render(template, data)`.

### 2.4 Por que Supabase (não PostgreSQL raw)

| Necessidade | Supabase Feature | Alternativa descartada |
|-------------|-----------------|----------------------|
| PostgreSQL | Incluído | Gerenciar instância própria |
| pgvector (embeddings) | Extensão habilitável | Instalar manualmente |
| Storage (PDFs, ZIPs) | S3-compatible, SDKs prontos | Gerenciar bucket S3 |
| Dashboard | Admin UI para debug | Não ter |
| Free tier | 500MB database, 1GB storage | Pagar desde o dia 1 |
| Auth (FUTURO) | OAuth + API keys + RLS | Quando multi-tenant for necessário |

### 2.5 Por que GPT-4o Vision como segmentador (não LayoutParser)

| Critério | LayoutParser + OpenCV | GPT-4o Vision |
|----------|----------------------|---------------|
| Deps | ~500MB (modelos PaddleDetection) | 0 (API call) |
| Deploy | Complexo (binários nativos) | Simples (HTTP) |
| Precisão em docs empresariais | Alta | Alta |
| Custo | $0 (local) | ~$0.05/página |
| Manutenção | Atualizar modelos manualmente | Modelo atualizado pela OpenAI |

Para o volume atual (21-100 templates), o custo de API é negligível (~$5-10 total) e a simplicidade de deploy compensa. Quando o volume justificar, o LayoutLMv3 fine-tuned (Bloco ML) assume essa função localmente.

### 2.6 Estratégia multi-modelo de IA (LiteLLM)

| Operação | Modelo | Justificativa | Custo/doc |
|----------|--------|---------------|-----------|
| Layout segmentation | GPT-4o Vision | Melhor compreensão visual | ~$0.05 |
| Layout interpretation | GPT-4o Vision | Pares label↔valor, hierarquia | ~$0.05 |
| Matching semântico | Gemini 2.0 Flash | Alto volume, texto puro, barato | ~$0.02 |
| Font detection | Gemini 1.5 Flash Vision | Visão básica, custo mínimo | ~$0.01 |
| Fidelity scoring | Claude Sonnet | Análise visual detalhada | ~$0.05 |
| Auto-correção HTML/CSS | Claude Sonnet | Melhor raciocínio sobre código | ~$0.03 |
| **Total por documento** | | | **~$0.15-0.25** |
| **100 templates** | | | **~$15-25** |

---

## 3. Stack Tecnológica

### 3.1 Frontend (browser)

| Tecnologia | Versão | Função |
|------------|--------|--------|
| Vue 3 | 3.5+ | Framework UI |
| TypeScript | 5.x | Tipagem estática |
| Vite | 7.x | Build tool + dev server |
| Pinia | 3.x | State management |
| Vue Router | 5.x | Navegação wizard |
| PDF.js | 5.x | Renderização de PDF no Canvas |
| **Konva.js** | **9.x** | **Anotação interativa sobre PDF (seleção de regiões, resize, associação a campos)** |
| **vue-konva** | **3.x** | **Wrapper Vue para Konva.js** |
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
| **PyMuPDF (fitz)** | **1.24+** | **Extração PDF (texto, coordenadas, fontes, imagens, tabelas, vetores)** |
| lxml | 5.x | Parse de XSD e XML |
| **LiteLLM** | **1.40+** | **Interface unificada GPT-4o + Gemini + Claude** |
| **anthropic** | **0.30+** | **SDK Anthropic (Claude)** |
| **openai** | **1.30+** | **SDK OpenAI (GPT-4o)** |
| **supabase** | **2.5+** | **SDK Supabase (PostgreSQL + Storage)** |
| **sentence-transformers** | **3.0+** | **Embeddings para semantic matching (384 dims)** |
| **scikit-learn** | **1.4+** | **Page clustering (KMeans)** |
| **numpy** | **1.26+** | **Vetores de features para clustering** |
| **torch** | **2.3+** | **PyTorch — runtime para modelos fine-tuned** |
| **transformers** | **4.40+** | **HuggingFace Transformers — LayoutLMv3, BERT, MiniLM** |
| **datasets** | **2.19+** | **HuggingFace Datasets — preparação de dados de treino** |
| **accelerate** | **0.30+** | **Accelerate — training distribuído e mixed precision** |
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
| ML Training | RunPod / Lambda Labs (GPU cloud) |
| Model Registry | HuggingFace Hub (repositório privado) |
| Monitoring | Sentry |

---

## 4. Processing Pipeline — 13 Etapas

```
┌─────────────────────────────────────────────────────────────┐
│                    PROCESSING PIPELINE                       │
│                                                              │
│  ┌─── FASE 1: EXTRAÇÃO ──────────────────────────────────┐  │
│  │                                                        │  │
│  │  [1] Upload PDF + XSD + dados                          │  │
│  │      Frontend → POST /api/upload/{pdf,xsd,data}        │  │
│  │      Arquivos → Supabase Storage                       │  │
│  │      Job criado → Supabase jobs table                  │  │
│  │                                                        │  │
│  │  [2] Parse PDF structure                               │  │
│  │      PyMuPDF (fitz) em RAM:                            │  │
│  │      - TextBlocks com bbox, font, font_size            │  │
│  │      - Tabelas com estrutura de linhas/colunas         │  │
│  │      - Imagens extraídas como bytes                    │  │
│  │      - Vetores gráficos (linhas, retângulos)           │  │
│  │      - Page screenshots (PNG) para Vision AI           │  │
│  │                                                        │  │
│  │  [3] Cluster pages by layout                           │  │
│  │      scikit-learn KMeans sobre feature vectors:        │  │
│  │      - num_blocks, avg_font_size, table_count          │  │
│  │      - text_density, header_height_ratio               │  │
│  │      Resultado: 1 representante por cluster            │  │
│  │      PDFs de 500 páginas → processa ~5-10 páginas      │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── FASE 2: INTELIGÊNCIA ──────────────────────────────┐  │
│  │                                                        │  │
│  │  [4] Detect layout regions                             │  │
│  │      GPT-4o Vision (API) — page screenshot input:      │  │
│  │      → header, body, table, footer, sidebar            │  │
│  │      Fallback: LayoutLMv3 fine-tuned (local)           │  │
│  │                                                        │  │
│  │  [5] Interpret layout with vision models               │  │
│  │      GPT-4o Vision (API) — screenshot + TextBlocks:    │  │
│  │      → pares label↔valor                               │  │
│  │      → hierarquia de seções                            │  │
│  │      → reading order                                   │  │
│  │      → estrutura de tabelas (headers, rows, cols)      │  │
│  │                                                        │  │
│  │  [6] Build Layout Model                                │  │
│  │      Modelo intermediário estruturado:                 │  │
│  │      LayoutModel {                                     │  │
│  │        pages: [{                                       │  │
│  │          page_index, cluster_id,                       │  │
│  │          sections: [{                                  │  │
│  │            type, bbox,                                 │  │
│  │            elements: [{                                │  │
│  │              type, text, bbox, binding,                │  │
│  │              format, font, font_size                   │  │
│  │            }]                                          │  │
│  │          }]                                            │  │
│  │        }],                                             │  │
│  │        metadata: { fonts, colors, page_size }          │  │
│  │      }                                                 │  │
│  │      → Persistir no Supabase (layout_models)           │  │
│  │                                                        │  │
│  │  [7] Infer data formats                                │  │
│  │      Camada 1: Regex determinístico                    │  │
│  │        CPF, CNPJ, CEP, telefone, data BR, moeda BR    │  │
│  │      Camada 2: BERT fine-tuned (classificador)         │  │
│  │        Para formatos ambíguos ou novos                 │  │
│  │      Camada 3: LLM fallback (Gemini Flash)             │  │
│  │        Para formatos não reconhecidos                  │  │
│  │                                                        │  │
│  │  [8] Map labels to schema fields                       │  │
│  │      Camada 1: pgvector similarity search              │  │
│  │        Busca embeddings de labels já conhecidos        │  │
│  │        Se similaridade > 0.85 → mapeamento automático  │  │
│  │      Camada 2: LLM matching (Gemini 2.0 Flash)         │  │
│  │        Para labels novos sem match no pgvector         │  │
│  │      Camada 3: MiniLM fine-tuned                       │  │
│  │        Modelo especializado no domínio PlanetPress     │  │
│  │      → Salvar embeddings novos no pgvector             │  │
│  │                                                        │  │
│  │  [9] Compute confidence score                          │  │
│  │      Rule-based: distribuição de confiança dos campos  │  │
│  │      Claude Sonnet: análise visual PDF vs template     │  │
│  │      → fidelityScore (0-100), fidelityComment          │  │
│  │      → iaSuggestions[] para o operador                 │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── FASE 3: HUMANO + GERAÇÃO ─────────────────────────┐  │
│  │                                                        │  │
│  │  [10] Human review (Vue wizard — Steps 2-4)            │  │
│  │       Tela 2 (Campos):                                 │  │
│  │         PDF.js + Konva.js → seleção interativa         │  │
│  │         Operador desenha regiões, associa a campos     │  │
│  │         Corrige mapeamentos, altera confiança          │  │
│  │       Tela 3 (Layout):                                 │  │
│  │         Configura margens, fontes, cor primária        │  │
│  │       Tela 4 (Geração):                                │  │
│  │         Monaco Editor para edição de HTML/CSS/JS       │  │
│  │         Preview inline via iframe                      │  │
│  │         "Melhorar com IA" → re-gera com sugestões      │  │
│  │       → Correções persistidas no Supabase              │  │
│  │         (human_feedback + label_embeddings update)     │  │
│  │                                                        │  │
│  │  [11] Generate Knockout template                       │  │
│  │       Layout Model → HTML semântico com data-bind      │  │
│  │       Seções → <div class="section section--header">   │  │
│  │       Bindings → <span data-bind="text: campo">       │  │
│  │       Formatters → ko.computed com filtros BR          │  │
│  │       Tables → data-bind="foreach: items"              │  │
│  │       CSS → layout posicional + responsivo             │  │
│  │       JS → ViewModel com ko.observable() por campo     │  │
│  │                                                        │  │
│  │  [12] Store template                                   │  │
│  │       → Supabase templates table (html, css, js)       │  │
│  │       → ZIP gerado em RAM (BytesIO)                    │  │
│  │       → ZIP → Supabase Storage                         │  │
│  │                                                        │  │
│  │  [13] Export ZIP autocontido                            │  │
│  │       template.zip/                                    │  │
│  │         index.html          ← Knockout bindings        │  │
│  │         css/style.css       ← layout do PDF            │  │
│  │         css/sentico.css     ← biblioteca bundlada      │  │
│  │         js/base.js          ← ViewModel + formatters   │  │
│  │         js/exemplo.js       ← dados de amostra         │  │
│  │         js/knockout-3.4.2.js← bundlado                 │  │
│  │         fonts/              ← fontes do PDF            │  │
│  │         img/                ← imagens extraídas        │  │
│  │       → Download via browser (StreamingResponse)       │  │
│  │       → Abre localmente sem dependências externas      │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
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
  user_id text,  -- identificador simples; FUTURO: references auth.users quando Auth for implementado
  status text not null default 'pending'
    check (status in ('pending', 'uploading', 'parsing', 'clustering',
                       'segmenting', 'interpreting', 'matching',
                       'scoring', 'reviewing', 'generating',
                       'done', 'error')),
  error_msg text,
  pdf_storage_path text,
  xsd_storage_path text,
  data_storage_path text,
  pdf_page_count int,
  xsd_field_count int,
  processing_time_ms int,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- ============================================================
-- LAYOUT MODELS — Representação intermediária estruturada
-- ============================================================
create table layout_models (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references jobs on delete cascade,
  page_index int not null,
  cluster_id text,
  sections jsonb not null,
  -- sections: [{type, bbox, elements: [{type, text, bbox, binding, format, font, font_size}]}]
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

-- Incrementar uso de um label
create or replace function increment_label_usage(target_label text)
returns void language plpgsql as $$
begin
  update label_embeddings
  set usage_count = usage_count + 1,
      updated_at = now()
  where label = target_label;
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
      documento.pdf
      schema.xsd
      dados.json (ou .xml)
  templates/
    {job_id}/
      template-v1.zip
      template-v2.zip
  page-images/
    {job_id}/
      page-001.png
      page-002.png
```

### 5.3 Row Level Security (RLS) — FUTURO

> **Status:** Não implementar agora. Ferramenta interna com 1-3 operadores, sem autenticação.
> **Quando implementar:** Quando abrir para múltiplas equipes/clientes (multi-tenant).

```sql
-- FUTURO: habilitar quando Supabase Auth for configurado
-- alter table jobs enable row level security;
-- create policy "Users can view own jobs"
--   on jobs for select using (auth.uid() = user_id);
-- create policy "Users can insert own jobs"
--   on jobs for insert with check (auth.uid() = user_id);

-- Por enquanto: tabelas sem RLS, acesso via service_role_key no backend
-- label_embeddings e format_patterns são globais por design (compartilhados)
```

---

## 6. Vision AI Pipeline

### 6.1 Arquitetura do AI Pipeline

```python
# services/ai_pipeline.py

class AIPipeline:
    """
    Orquestra as 3 camadas de inteligência:
    1. Determinístico (regex, heurísticas)
    2. LLM APIs (GPT-4o Vision, Gemini Flash, Claude Sonnet)
    3. Modelos fine-tuned (LayoutLMv3, MiniLM, BERT)
    """

    async def process_document(self, job_id: str) -> ExtractionResult:
        # [2] Parse PDF
        pdf_data = await self.pdf_extractor.extract(job_id)

        # [3] Cluster pages
        clusters = self.page_clusterer.cluster(pdf_data.pages)

        # Processar apenas representantes de cada cluster
        for cluster_id, representative_page in clusters.items():
            # [4] Segment layout
            sections = await self.segment_page(representative_page)

            # [5] Interpret layout
            interpretation = await self.interpret_layout(
                representative_page, sections
            )

            # [6] Build layout model
            layout_model = self.build_layout_model(
                representative_page, sections, interpretation
            )

            # Persistir no Supabase
            await self.save_layout_model(job_id, layout_model)

        # [7] Infer formats
        formats = await self.detect_formats(pdf_data.text_blocks)

        # [8] Match fields
        mappings = await self.match_fields(
            pdf_data.text_blocks, xsd_fields, data_sample
        )

        # [9] Compute confidence
        score = await self.compute_fidelity(mappings, pdf_data)

        return ExtractionResult(
            fields=mappings,
            fidelity_score=score,
            layout_model=layout_model,
        )
```

### 6.2 Vision — Segmentação de Layout

```python
# services/ai_vision.py
import litellm
import base64

SEGMENTATION_PROMPT = """
Analise esta página de documento empresarial brasileiro.

Identifique todas as regiões estruturais. Retorne JSON:
{
  "sections": [
    {
      "type": "header|body|table|footer|sidebar|logo",
      "bbox": [x, y, width, height],  // coordenadas normalizadas 0-1
      "confidence": 0.95,
      "description": "Cabeçalho com logo e dados do cliente"
    }
  ]
}

Priorize: headers (topo), footers (base), tabelas (linhas/colunas visíveis),
corpo (texto entre header e footer).
"""

async def segment_page(page_image_bytes: bytes) -> list[Section]:
    img_b64 = base64.b64encode(page_image_bytes).decode()

    response = await litellm.acompletion(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": SEGMENTATION_PROMPT},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{img_b64}"
                }}
            ]
        }],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    data = json.loads(response.choices[0].message.content)
    return [Section(**s) for s in data["sections"]]
```

### 6.3 Vision — Interpretação de Layout

```python
# services/ai_vision.py (continuação)

INTERPRETATION_PROMPT = """
Analise esta página de documento e os blocos de texto extraídos por OCR.

Blocos de texto com coordenadas (x, y, width, height normalizados 0-1):
{text_blocks}

Seções detectadas:
{sections}

Retorne JSON:
{{
  "label_value_pairs": [
    {{
      "label": "Cliente",
      "value": "João Silva",
      "label_bbox": [x, y, w, h],
      "value_bbox": [x, y, w, h],
      "relationship": "right_of|below|inside_table",
      "confidence": 0.92
    }}
  ],
  "table_structure": [
    {{
      "section_index": 2,
      "headers": ["Data", "Descrição", "Valor"],
      "row_count": 15,
      "column_count": 3
    }}
  ],
  "reading_order": [0, 1, 3, 2, 4],
  "hierarchy": {{
    "title": "Extrato Bancário",
    "groups": [
      {{"name": "Dados do Cliente", "fields": ["Cliente", "CPF", "Agência"]}},
      {{"name": "Movimentações", "type": "table"}}
    ]
  }}
}}

Priorize relações visuais (proximidade, alinhamento) sobre ordem do texto.
Identifique labels mesmo quando implícitos (ex: valor ao lado de "R$" é currency).
"""

async def interpret_layout(
    page_image_bytes: bytes,
    text_blocks: list[dict],
    sections: list[dict]
) -> LayoutInterpretation:
    img_b64 = base64.b64encode(page_image_bytes).decode()

    response = await litellm.acompletion(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": INTERPRETATION_PROMPT.format(
                    text_blocks=json.dumps(text_blocks, ensure_ascii=False),
                    sections=json.dumps(sections, ensure_ascii=False)
                )},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/png;base64,{img_b64}"
                }}
            ]
        }],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    data = json.loads(response.choices[0].message.content)
    return LayoutInterpretation(**data)
```

### 6.4 Matching Semântico (LLM + pgvector)

```python
# services/ai_matcher.py

from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

async def match_fields(
    text_blocks: list,
    xsd_fields: list,
    data_sample: dict | None,
    supabase_client
) -> list[FieldMapping]:

    mappings = []

    for block in text_blocks:
        # Camada 1: pgvector — buscar labels já conhecidos
        embedding = embedding_model.encode(block.text).tolist()
        known = await supabase_client.rpc('match_labels', {
            'query_embedding': embedding,
            'match_threshold': 0.85,
            'match_count': 1
        }).execute()

        if known.data and len(known.data) > 0:
            # Match encontrado no histórico — alta confiança
            match = known.data[0]
            mappings.append(FieldMapping(
                pdf_text=block.text,
                json_path=match['canonical_field'],
                confidence='high',
                confidence_score=match['similarity'],
                status='ok',
                embedding=embedding,
                source='pgvector'
            ))
            continue

        # Camada 2: LLM matching — para labels novos
        # (batch para eficiência)
        # Acumulado e processado em batch abaixo

    # Batch LLM matching para blocks sem match no pgvector
    unmatched = [b for b in text_blocks if not has_match(b, mappings)]
    if unmatched:
        llm_mappings = await match_with_llm(unmatched, xsd_fields, data_sample)
        mappings.extend(llm_mappings)

    # Salvar novos embeddings para learning
    for mapping in mappings:
        if mapping.embedding and mapping.status == 'ok':
            await supabase_client.table('label_embeddings').upsert({
                'label': mapping.pdf_text,
                'canonical_field': mapping.json_path,
                'embedding': mapping.embedding,
                'source': 'llm'
            }).execute()

    return mappings


MATCHING_PROMPT = """
Mapeie os blocos de texto extraídos de um PDF para os campos do schema XSD.

Blocos de texto (labels encontrados no PDF):
{blocks}

Campos do schema XSD:
{fields}

Dados de exemplo (se disponível):
{sample}

Retorne JSON:
{{
  "mappings": [
    {{
      "pdf_text": "Cliente",
      "json_path": "cliente.nome",
      "field_type": "text",
      "confidence": "high",
      "reasoning": "Label 'Cliente' mapeia diretamente para campo 'cliente.nome' do XSD"
    }}
  ],
  "unmapped_labels": ["Logo", "Página"],
  "unmapped_fields": ["cliente.email"]
}}

Regras:
- Labels como "CPF", "Documento", "Doc" todos mapeiam para o campo de documento
- Considere variações brasileiras (Data/Dt, Valor/Vlr, Quantidade/Qtd)
- confidence: "high" (>85%), "medium" (60-85%), "low" (<60%)
"""

async def match_with_llm(
    blocks: list,
    xsd_fields: list,
    data_sample: dict | None
) -> list[FieldMapping]:
    response = await litellm.acompletion(
        model="gemini/gemini-2.0-flash",
        messages=[{
            "role": "user",
            "content": MATCHING_PROMPT.format(
                blocks=json.dumps([b.text for b in blocks], ensure_ascii=False),
                fields=json.dumps(xsd_fields, ensure_ascii=False),
                sample=json.dumps(data_sample, ensure_ascii=False) if data_sample else "N/A"
            )
        }],
        response_format={"type": "json_object"},
        temperature=0.1
    )

    data = json.loads(response.choices[0].message.content)
    return [FieldMapping(**m) for m in data["mappings"]]
```

---

## 7. Layout Model

### 7.1 Pydantic Models

```python
# models/layout_model.py
from pydantic import BaseModel

class LayoutElement(BaseModel):
    type: str         # 'label', 'value', 'image', 'table_cell', 'table_header'
    text: str | None
    bbox: tuple[float, float, float, float]  # x, y, w, h (normalized 0-1)
    binding: str | None       # campo do XSD mapeado (ex: "cliente.nome")
    format: str | None        # 'cpf', 'date', 'currency', etc.
    font: str | None
    font_size: float | None
    is_label: bool = False    # True se é um rótulo estático (não dinâmico)
    confidence: float = 0.0

class TableDefinition(BaseModel):
    headers: list[str]
    binding_array: str | None  # campo do XSD que é array (ex: "movimentacoes")
    column_bindings: list[str | None]  # binding de cada coluna
    column_formats: list[str | None]   # formato de cada coluna

class LayoutSection(BaseModel):
    type: str           # 'header', 'body', 'table', 'footer', 'sidebar'
    bbox: tuple[float, float, float, float]
    elements: list[LayoutElement]
    table: TableDefinition | None = None  # se type == 'table'

class PageLayout(BaseModel):
    page_index: int
    cluster_id: str
    sections: list[LayoutSection]
    reading_order: list[int] | None = None

class LayoutModel(BaseModel):
    pages: list[PageLayout]
    metadata: dict  # {fonts_used, dominant_colors, page_size, orientation}
```

### 7.2 Layout Model → Knockout Template

```python
# services/template_generator.py

def generate_knockout_template(layout_model: LayoutModel) -> tuple[str, str, str, str]:
    """
    Converte Layout Model em template HTML/CSS/JS com Knockout bindings.

    Retorna: (html, css, js, exemplo)
    """
    html_parts = ['<!doctype html>', '<html>', '<head>',
                  '<meta charset="utf-8"/>',
                  '<link rel="stylesheet" href="./css/style.css">',
                  '<link rel="stylesheet" href="./css/sentico.css">',
                  '</head>', '<body>']

    css_rules = []
    viewmodel_fields = {}
    exemplo_data = {}

    for page in layout_model.pages:
        html_parts.append(f'<div class="page page--{page.page_index}">')

        for section in page.sections:
            section_class = f'section section--{section.type}'
            html_parts.append(f'<div class="{section_class}">')

            if section.type == 'table' and section.table:
                # Gerar tabela com foreach binding
                html_parts.append(generate_table_html(section))
                viewmodel_fields[section.table.binding_array] = '[]'
            else:
                for el in section.elements:
                    if el.binding:
                        # Elemento dinâmico com data-bind
                        formatter = get_knockout_formatter(el.format)
                        if formatter:
                            html_parts.append(
                                f'<span class="field" data-bind="text: {formatter}({el.binding})">'
                                f'{el.text or ""}</span>'
                            )
                        else:
                            html_parts.append(
                                f'<span class="field" data-bind="text: {el.binding}">'
                                f'{el.text or ""}</span>'
                            )
                        viewmodel_fields[el.binding] = f"'{el.text or ''}'"
                        exemplo_data[el.binding] = el.text or ''
                    elif el.is_label:
                        # Label estático
                        html_parts.append(f'<span class="label">{el.text}</span>')

                    # CSS para posicionamento
                    css_rules.append(generate_position_css(el))

            html_parts.append('</div>')

        html_parts.append('</div>')

    html_parts.extend([
        '<script src="./js/knockout-3.4.2.js"></script>',
        '<script src="./js/base.js"></script>',
        '<script src="./js/exemplo.js"></script>',
        '</body>', '</html>'
    ])

    html = '\n'.join(html_parts)
    css = generate_css(css_rules, layout_model.metadata)
    js = generate_viewmodel_js(viewmodel_fields)
    exemplo = generate_exemplo_js(exemplo_data)

    return html, css, js, exemplo


def generate_table_html(section: LayoutSection) -> str:
    table = section.table
    lines = ['<table>']

    # Headers
    lines.append('<thead><tr>')
    for header in table.headers:
        lines.append(f'<th>{header}</th>')
    lines.append('</tr></thead>')

    # Body com foreach
    lines.append(f'<tbody data-bind="foreach: {table.binding_array}">')
    lines.append('<tr>')
    for i, binding in enumerate(table.column_bindings):
        fmt = table.column_formats[i] if table.column_formats else None
        if binding and fmt:
            formatter = get_knockout_formatter(fmt)
            lines.append(f'<td data-bind="text: {formatter}({binding})"></td>')
        elif binding:
            lines.append(f'<td data-bind="text: {binding}"></td>')
        else:
            lines.append('<td></td>')
    lines.append('</tr>')
    lines.append('</tbody></table>')

    return '\n'.join(lines)


def get_knockout_formatter(format_type: str | None) -> str | None:
    """Retorna nome do formatter Knockout para formatos BR."""
    formatters = {
        'currency': 'formatCurrency',
        'date': 'formatDate',
        'cpf': 'formatCpf',
        'cnpj': 'formatCnpj',
        'cep': 'formatCep',
        'phone': 'formatPhone',
        'percentage': 'formatPercentage',
    }
    return formatters.get(format_type)
```

---

## 8. Konva.js — Anotação Interativa sobre PDF

### 8.1 Arquitetura de Layers

```
┌─────────────────────────────────────┐
│  Canvas Container (Tela 2)          │
│                                     │
│  Layer 1: PDF.js                    │
│    └── Renderiza a página do PDF    │
│         (canvas nativo)             │
│                                     │
│  Layer 2: Konva.js (overlay)        │
│    ├── Bounding boxes existentes    │
│    │   (retângulos coloridos por    │
│    │    status: ✅verde 🟡amarelo   │
│    │    🔴vermelho)                 │
│    ├── Região sendo desenhada       │
│    │   (retângulo com drag)         │
│    └── Handles de resize            │
│                                     │
│  Interações:                        │
│  - Click em bbox → seleciona campo  │
│  - Drag no canvas → desenha região  │
│  - Drag em handle → resize região   │
│  - Double-click → abre associação   │
│    de campo (dropdown XSD fields)   │
│  - Right-click → menu contextual    │
│    (remover, editar, reassociar)    │
└─────────────────────────────────────┘
```

### 8.2 Componente Vue

```typescript
// organisms/PdfAnnotator.vue — conceito

interface AnnotationRegion {
  id: string
  x: number         // normalized 0-1
  y: number         // normalized 0-1
  width: number     // normalized 0-1
  height: number    // normalized 0-1
  fieldId: string | null  // campo associado
  status: 'ok' | 'ambiguous' | 'not_found'
  source: 'ai' | 'manual'  // criado pela IA ou pelo operador
}

// Props:
//   pdfBytes: ArrayBuffer
//   page: number
//   regions: AnnotationRegion[]
//   selectedFieldId: string | null
//
// Emits:
//   region-created(region)      — operador desenhou nova região
//   region-updated(region)      — operador moveu/redimensionou
//   region-selected(regionId)   — click em região existente
//   region-deleted(regionId)    — operador removeu região
//   field-associated(regionId, fieldId)  — associou campo a região
```

### 8.3 Dependências Frontend

```json
{
  "konva": "^9.3.0",
  "vue-konva": "^3.0.0"
}
```

---

## 9. Learning System

### 9.1 Arquitetura do Feedback Loop

```
                    LEARNING SYSTEM
┌─────────────────────────────────────────────┐
│                                             │
│  ONLINE (imediato, a cada correção)         │
│  ── IMPLEMENTAR NOS EPICS INICIAIS ──       │
│                                             │
│  Operador corrige mapeamento                │
│       ↓                                     │
│  POST /api/feedback                         │
│       ↓                                     │
│  1. Salvar em human_feedback (Supabase)     │
│  2. Gerar embedding do label corrigido      │
│  3. Upsert em label_embeddings (pgvector)   │
│  4. Atualizar format_patterns se aplicável  │
│       ↓                                     │
│  Próximo documento com label similar        │
│  → pgvector encontra automaticamente        │
│  → Confiança alta desde o primeiro match    │
│                                             │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│                                             │
│  BATCH (fine-tuning de modelos)             │
│  ── FUTURO: implementar por último ──       │
│  ── quando houver volume suficiente ──      │
│                                             │
│  Scheduler (cron ou manual):                │
│       ↓                                     │
│  1. Export human_feedback → HF Dataset      │
│  2. Fine-tune LayoutLMv3 com layouts        │
│     corrigidos do PlanetPress               │
│  3. Fine-tune MiniLM com pares             │
│     label↔canonical_field corrigidos        │
│  4. Fine-tune BERT com format patterns      │
│     confirmados/corrigidos                  │
│  5. Push modelos → HuggingFace Hub          │
│  6. Backend carrega modelos atualizados     │
│       ↓                                     │
│  Modelos especializados no domínio          │
│  → Menos chamadas a APIs externas           │
│  → Maior precisão em docs PlanetPress       │
│  → Menor custo por documento                │
│                                             │
│  PRE-REQUISITOS para iniciar batch:         │
│  - ~50+ documentos processados (matcher)    │
│  - ~200+ documentos (layout segmenter)      │
│  - Infraestrutura GPU (RunPod/Lambda)       │
│  - HuggingFace Hub configurado              │
│                                             │
└─────────────────────────────────────────────┘
```

### 9.2 API de Feedback

```python
# routers/feedback.py

@router.post("/api/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    supabase: SupabaseClient = Depends(get_supabase)
):
    """
    Recebe correção do operador e atualiza o learning system.
    """
    # 1. Persistir feedback
    await supabase.table('human_feedback').insert({
        'job_id': feedback.job_id,
        'field_mapping_id': feedback.field_mapping_id,
        'feedback_type': feedback.type,
        'original_json_path': feedback.original_path,
        'corrected_json_path': feedback.corrected_path,
    }).execute()

    # 2. Atualizar embeddings
    if feedback.type == 'correction' and feedback.corrected_path:
        embedding = embedding_model.encode(feedback.label).tolist()

        await supabase.table('label_embeddings').upsert({
            'label': feedback.label,
            'canonical_field': feedback.corrected_path,
            'embedding': embedding,
            'source': 'human_feedback'
        }).execute()

    # 3. Atualizar format patterns
    if feedback.format_correction:
        await supabase.table('format_patterns').upsert({
            'pattern': feedback.format_correction.pattern,
            'format_type': feedback.format_correction.type,
            'example': feedback.format_correction.example,
            'source': 'human_feedback'
        }).execute()

    return {"status": "ok"}
```

### 9.3 Fine-Tuning Pipeline (FUTURO)

> **Status:** Documentado para implementação futura. Será o último epic a ser implementado.
> **Pré-requisito:** Volume mínimo de ~50 documentos processados com feedback humano.
> **Infra necessária:** GPU cloud (RunPod/Lambda Labs) + HuggingFace Hub privado.

```python
# ml/training/fine_tune_matcher.py
# FUTURO — implementar quando houver volume de dados suficiente

from datasets import Dataset
from transformers import (
    AutoTokenizer, AutoModel,
    TrainingArguments, Trainer
)
import torch

async def prepare_training_data(supabase_client) -> Dataset:
    """
    Exporta feedbacks do Supabase para HuggingFace Dataset.
    """
    feedbacks = await supabase_client.table('human_feedback') \
        .select('*, field_mappings(pdf_text, json_path)') \
        .eq('feedback_type', 'correction') \
        .execute()

    pairs = []
    for fb in feedbacks.data:
        pairs.append({
            'text': fb['field_mappings']['pdf_text'],
            'label': fb['corrected_json_path'],
        })

    return Dataset.from_list(pairs)


def fine_tune_matcher(dataset: Dataset, output_dir: str):
    """
    Fine-tune MiniLM para matching semântico no domínio PlanetPress.
    """
    model_name = 'sentence-transformers/all-MiniLM-L6-v2'
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=5,
        per_device_train_batch_size=16,
        learning_rate=2e-5,
        warmup_steps=100,
        fp16=torch.cuda.is_available(),
        save_strategy='epoch',
        evaluation_strategy='epoch',
        push_to_hub=True,
        hub_model_id='org/planetpress-field-matcher',
        hub_private_repo=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        tokenizer=tokenizer,
    )

    trainer.train()
    trainer.push_to_hub()
```

### 9.4 Modelos Fine-Tuned (FUTURO)

> **Status:** Planejado. Implementar após acumular volume suficiente de feedback humano.

| Modelo | Base | Dados de Treino | Função | Inferência | Quando implementar |
|--------|------|----------------|--------|------------|-------------------|
| **planetpress-layout-segmenter** | LayoutLMv3 | layout_models + human_feedback (regions) | Detectar header/body/table/footer sem API call | GPU ou CPU (quantizado) | Após ~200 docs |
| **planetpress-field-matcher** | all-MiniLM-L6-v2 | label_embeddings + human_feedback (corrections) | Matching semântico label→campo especializado | CPU (80MB) | Após ~50 docs |
| **planetpress-format-detector** | bert-base-multilingual | format_patterns + human_feedback (formats) | Classificar formatos BR (CPF, data, moeda) | CPU (440MB) | Após ~500 docs |

**Estratégia de transição:**
1. **Agora:** 100% APIs (GPT-4o, Gemini, Claude) + learning online (pgvector) — funciona desde o dia 1
2. **Futuro (~50 docs):** Fine-tune MiniLM matcher — reduz chamadas a Gemini
3. **Futuro (~200 docs):** Fine-tune LayoutLMv3 — reduz chamadas a GPT-4o Vision
4. **Futuro (~500 docs):** Fine-tune BERT format — elimina regex frágil

**Nota:** O learning online (modo 1 — pgvector embeddings) já fornece melhoria contínua sem fine-tuning. O batch fine-tuning é uma otimização de custo e precisão para quando o volume justificar.

---

## 10. API REST — Endpoints Completos

```
# ============================================================
# UPLOAD
# ============================================================
POST   /api/upload/pdf          Upload PDF → Supabase Storage, retorna jobId
POST   /api/upload/xsd          Upload XSD → Supabase Storage
POST   /api/upload/data         Upload JSON/XML → Supabase Storage

# ============================================================
# PIPELINE
# ============================================================
POST   /api/jobs                Inicia pipeline completo (13 etapas)
GET    /api/progress/{jobId}    SSE — progresso em tempo real
GET    /api/result/{jobId}      Resultado da extração + mapeamento

# ============================================================
# AI (chamadas individuais para re-processamento)
# ============================================================
POST   /api/ai/segment         Segmentar layout de uma página (Vision)
POST   /api/ai/interpret       Interpretar layout (Vision)
POST   /api/ai/match           Matching semântico (Gemini + pgvector)
POST   /api/ai/fidelity        Score de fidelidade (Claude Vision)
POST   /api/ai/correct         Auto-correção HTML/CSS (Claude)
POST   /api/ai/font            Font detection (Gemini Vision)

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
# LIBRARIES
# ============================================================
GET    /api/libraries           Lista assets disponíveis (fonts, CSS, JS)
POST   /api/libraries/upload    Adiciona asset
DELETE /api/libraries/{tipo}/{nome}  Remove asset

# ============================================================
# ADMIN
# ============================================================
GET    /api/health              Health check
GET    /api/stats               Estatísticas de uso (jobs, templates, feedback)
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
│   │   │   ├── session.ts            # jobId, estado global
│   │   │   ├── mapping.ts            # campos mapeados
│   │   │   ├── layout.ts             # configurações de layout
│   │   │   └── generation.ts         # HTML/CSS/JS gerados
│   │   ├── atoms/                    # Componentes atômicos
│   │   ├── molecules/                # Composições simples
│   │   │   ├── FileDropzone.vue
│   │   │   ├── IASuggestionList.vue
│   │   │   └── RightPanelToggle.vue
│   │   ├── organisms/                # Componentes complexos
│   │   │   ├── AppHeader.vue
│   │   │   ├── PdfAnnotator.vue      # ← NOVO: PDF.js + Konva.js
│   │   │   ├── PDFViewer.vue         # PDF.js puro (mantido para compat)
│   │   │   ├── FieldMappingTable.vue
│   │   │   ├── FieldDetailPanel.vue
│   │   │   ├── MonacoTabs.vue
│   │   │   ├── ChartjsConfigPanel.vue
│   │   │   ├── LayoutControls.vue
│   │   │   ├── LayoutPreview.vue
│   │   │   ├── ExportChecklist.vue
│   │   │   ├── BibliotecasModal.vue
│   │   │   └── WizardStepper.vue
│   │   ├── templates/                # Layouts de página
│   │   │   ├── WizardLayout.vue
│   │   │   ├── SplitPaneLayout.vue
│   │   │   └── FullWidthLayout.vue
│   │   ├── pages/                    # Telas do wizard
│   │   │   ├── HomePage.vue          # Tela 0
│   │   │   ├── UploadPage.vue        # Tela 1
│   │   │   ├── CamposPage.vue        # Tela 2 (com PdfAnnotator)
│   │   │   ├── LayoutPage.vue        # Tela 3
│   │   │   ├── GeracaoPage.vue       # Tela 4
│   │   │   └── ExportarPage.vue      # Tela 5
│   │   ├── composables/
│   │   │   ├── useSSE.ts
│   │   │   ├── useProject.ts
│   │   │   ├── useFileSystem.ts
│   │   │   └── useBibliotecas.ts
│   │   └── types/
│   │       └── index.ts
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                          # FastAPI + AI Pipeline
│   ├── main.py
│   ├── routers/
│   │   ├── upload.py
│   │   ├── jobs.py
│   │   ├── progress.py
│   │   ├── ai.py                     # ← NOVO: /api/ai/* endpoints
│   │   ├── generate.py
│   │   ├── preview.py
│   │   ├── export.py
│   │   ├── feedback.py               # ← NOVO: /api/feedback
│   │   └── libraries.py              # ← NOVO: /api/libraries
│   ├── services/
│   │   ├── pdf_extractor.py          # PyMuPDF (migrar de pdfplumber)
│   │   ├── xsd_parser.py
│   │   ├── data_parser.py
│   │   ├── page_clusterer.py         # ← NOVO: scikit-learn KMeans
│   │   ├── ai_pipeline.py            # ← NOVO: orquestrador AI
│   │   ├── ai_vision.py              # ← NOVO: GPT-4o Vision
│   │   ├── ai_matcher.py             # ← NOVO: Gemini + pgvector
│   │   ├── ai_fidelity.py            # ← NOVO: Claude Sonnet
│   │   ├── semantic_embeddings.py    # ← NOVO: SentenceTransformers
│   │   ├── format_detector.py        # ← NOVO: regex + BERT
│   │   ├── layout_builder.py         # ← NOVO: constrói LayoutModel
│   │   ├── template_generator.py     # REFATORADO: Layout Model → Knockout
│   │   ├── fidelity_scorer.py
│   │   ├── feedback_tracker.py       # ← NOVO: learning system
│   │   ├── job_manager.py
│   │   └── zip_builder.py
│   ├── models/
│   │   ├── job.py
│   │   ├── layout_model.py           # ← NOVO: LayoutModel Pydantic
│   │   ├── field_mapping.py
│   │   ├── extraction_result.py
│   │   ├── text_block.py
│   │   └── feedback.py               # ← NOVO: FeedbackRequest
│   ├── core/
│   │   ├── config.py                 # Settings (API keys, Supabase)
│   │   └── supabase_client.py        # ← NOVO: cliente Supabase
│   ├── assets/
│   │   └── libraries/                # Assets bundláveis no ZIP
│   │       ├── css/
│   │       ├── js/
│   │       └── fonts/
│   └── requirements.txt
│
├── ml/                               # ← NOVO: Machine Learning
│   ├── training/
│   │   ├── fine_tune_matcher.py      # Fine-tune MiniLM
│   │   ├── fine_tune_layout.py       # Fine-tune LayoutLMv3
│   │   ├── fine_tune_format.py       # Fine-tune BERT
│   │   └── export_training_data.py   # Supabase → HF Dataset
│   ├── evaluation/
│   │   ├── eval_matcher.py           # Avaliar precisão do matcher
│   │   ├── eval_layout.py            # Avaliar segmentação
│   │   └── benchmark.py             # Benchmark completo do pipeline
│   └── README.md
│
├── supabase/                         # ← NOVO: Supabase config
│   └── migrations/
│       ├── 001_initial_schema.sql    # Schema completo
│       ├── 002_pgvector_setup.sql    # Extensão + índices
│       └── 003_rls_policies.sql      # FUTURO: Row Level Security (quando Auth)
│
├── docs/
│   ├── prd.md
│   ├── front-end-spec.md
│   ├── architecture/
│   │   ├── DOCUMENT_AI_PLATFORM_MASTER_ARCHITECTURE.md  # Referência original
│   │   ├── architecture.md           # v3.0 (histórico)
│   │   └── architecture-v4.md        # ESTE DOCUMENTO
│   ├── stories/
│   └── wireframes/
│
├── .env                              # API keys (gitignored)
├── .env.example
├── start-backend.bat
├── start-frontend.bat
└── README.md
```

---

## 12. Dependências Completas

### 12.1 Backend — requirements.txt

```
# ============================================================
# Core Framework
# ============================================================
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
python-multipart>=0.0.9
python-dotenv>=1.0.0
sse-starlette>=2.0.0

# ============================================================
# PDF Processing
# ============================================================
PyMuPDF>=1.24.0
Pillow>=10.0.0
lxml>=5.0.0

# ============================================================
# AI — LLM APIs
# ============================================================
litellm>=1.40.0
anthropic>=0.30.0
openai>=1.30.0

# ============================================================
# AI — Embeddings & Semantic Matching
# ============================================================
sentence-transformers>=3.0.0

# ============================================================
# AI — Page Clustering
# ============================================================
scikit-learn>=1.4.0
numpy>=1.26.0

# ============================================================
# ML — PyTorch + HuggingFace (Fine-Tuning & Inference)
# ============================================================
torch>=2.3.0
transformers>=4.40.0
datasets>=2.19.0
accelerate>=0.30.0

# ============================================================
# Database — Supabase
# ============================================================
supabase>=2.5.0
```

### 12.2 Frontend — package.json (adições)

```json
{
  "dependencies": {
    "konva": "^9.3.0",
    "vue-konva": "^3.0.0"
  }
}
```

### 12.3 Variáveis de Ambiente

```env
# AI APIs
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
OPENROUTER_API_KEY=sk-or-...
DEEPSEEK_API_KEY=sk-...

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# HuggingFace (para model registry)
HF_TOKEN=hf_...
HF_ORG=organizacao

# Monitoring
SENTRY_DSN=https://...

# Server
HOST=0.0.0.0
PORT=8000
```

---

## 13. Epics de Implementação

| Epic | Descrição | Blocos | Prioridade | Esforço | Fase |
|------|-----------|--------|------------|---------|------|
| **Epic 5** | Supabase Integration | Schema, Storage, migrar de in-memory (sem Auth) | CRÍTICA | Médio | Fase 1 |
| **Epic 6** | Vision AI Pipeline | GPT-4o Vision segmentação + interpretação, LiteLLM setup | CRÍTICA | Alto | Fase 1 |
| **Epic 7** | Layout Model + Template Refactor | LayoutModel Pydantic, refatorar template_generator para Knockout semântico | ALTA | Médio | Fase 1 |
| **Epic 8** | Semantic Matching (pgvector) | SentenceTransformers, pgvector functions, ai_matcher refatorado | ALTA | Médio | Fase 1 |
| **Epic 9** | Konva.js — Anotação Interativa | PdfAnnotator.vue, integrar na CamposPage, região→campo workflow | ALTA | Médio | Fase 2 |
| **Epic 10** | Page Clustering | scikit-learn KMeans, feature vectors, cluster-aware pipeline | MÉDIA | Baixo | Fase 2 |
| **Epic 11** | Learning System Online | Feedback API, label_embeddings update, format_patterns update | MÉDIA | Médio | Fase 2 |
| **Epic 13** | PyMuPDF Migration | Substituir pdfplumber por PyMuPDF, extrair vetores gráficos e imagens | MÉDIA | Baixo | Fase 2 |
| **Epic 12** | Fine-Tuning Pipeline (FUTURO) | Export dados, treino LayoutLMv3 + MiniLM + BERT, model registry, GPU cloud | BAIXA | Alto | Fase 3 (futuro) |

**Ordem recomendada:** 5 → 6 → 7 → 8 → 9 → 13 → 10 → 11 → ... → 12

**Fases:**

**Fase 1 — Fundação + Inteligência (Epics 5-8):**
- Epic 5: Supabase é fundação para todo o resto (persistência, embeddings, feedback)
- Epic 6: Vision AI é o diferencial que transforma matching textual em compreensão real
- Epic 7: Layout Model conecta Vision AI ao template generator
- Epic 8: pgvector + embeddings melhoram matching e habilitam learning online

**Fase 2 — UX + Otimização (Epics 9-11, 13):**
- Epic 9: Konva.js transforma o review humano de tabela para interação visual
- Epic 13: PyMuPDF melhora fidelidade de extração
- Epic 10: Page clustering otimiza performance com PDFs grandes
- Epic 11: Learning online fecha o loop de feedback (pgvector, sem fine-tuning)

**Fase 3 — Fine-Tuning (Epic 12) — FUTURO:**
- Implementar somente quando houver volume suficiente (~50+ docs com feedback)
- Requer infraestrutura GPU (RunPod/Lambda Labs)
- Objetivo: reduzir dependência de APIs externas e custo por documento
- Até lá, o learning online (pgvector) + APIs já fornecem melhoria contínua

---

## 14. Decisões Futuras (fora do escopo atual)

| Decisão | Quando revisar |
|---------|----------------|
| Docker/Kubernetes | Se deploy em infraestrutura própria (não Railway) |
| Workers distribuídos (Celery/RabbitMQ) | Se > 10 usuários simultâneos |
| Puppeteer/Playwright no servidor | Se precisar gerar PDF a partir do template (rendering engine) |
| Redis cache | Se mesmo PDF for reprocessado frequentemente |
| Supabase Auth + RLS | Se abrir para múltiplas equipes/clientes (multi-tenant) |
| OAuth SSO | Se integrar com sistema de identidade corporativo |
| WebSocket (substituir SSE) | Se precisar de comunicação bidirecional em tempo real |
| CDN para assets | Se templates gerados forem servidos para muitos consumidores |

---

## 15. Custo Estimado

### 15.1 Por Documento

| Componente | Custo |
|-----------|-------|
| GPT-4o Vision (segmentação + interpretação) | ~$0.10 |
| Gemini 2.0 Flash (matching) | ~$0.02 |
| Claude Sonnet (fidelity) | ~$0.05 |
| SentenceTransformers (local) | $0.00 |
| Supabase (storage + database) | ~$0.001 |
| **Total por documento** | **~$0.17** |

### 15.2 Mensal

| Componente | Free Tier | Pro |
|-----------|-----------|-----|
| Supabase | 500MB DB, 1GB Storage | $25/mês |
| Railway | $5/mês (hobby) | $20/mês |
| OpenAI API | Pay per use | ~$15-25/100 docs |
| Google AI | Free tier generoso | ~$2-5/100 docs |
| Anthropic | Pay per use | ~$5-10/100 docs |
| GPU (fine-tuning) | — | ~$10/sessão (RunPod) |
| **Total** | **~$5-10/mês** | **~$60-90/mês** |

---

## 16. NFRs — Como a Arquitetura v4.0 Atende

| NFR | Como atende |
|-----|-------------|
| NFR1 — Acessível via browser sem instalação | Mantido: web app puro, URL direta |
| NFR2 — Sem instalações complexas | Mantido: Chrome/Edge direto |
| NFR3 — Precisão ≥ 80% matching | Melhorado: Vision AI + embeddings + learning system |
| NFR4 — 50 páginas em < 60s | Melhorado: page clustering processa ~5 páginas em vez de 50 |
| NFR5 — Fidelidade visual | Melhorado: Layout Model semântico + Claude Vision scoring |
| NFR6 — Caminhos aninhados JSON | Mantido: tratado no matching e bindings Knockout |
| NFR7 — ZIP autocontido | Mantido: template funciona offline |
| **NOVO — Learning** | Sistema melhora com cada documento processado |
| **FUTURO — Multi-tenant** | Supabase Auth + RLS quando necessário |
| **NOVO — Persistência** | Jobs, templates, feedbacks persistidos no Supabase |

---

— Aria, arquitetando o futuro 🏗️
