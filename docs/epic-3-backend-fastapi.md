---
epic: 3
title: "Backend FastAPI — Motor de Migração"
status: Draft
owner: "@pm (Morgan)"
executor: "@dev"
quality_gate: "@architect"
---

# Epic 3: Backend FastAPI — Motor de Migração

## Status

Draft

## Objetivo

Construir o backend FastAPI que implementa o motor de migração de documentos planetexpress → HTML/Knockout.js, expondo os endpoints consumidos pelo frontend web (Epic 1).

## Contexto

O frontend (Epic 1) está pronto e conectado via proxy Vite ao `http://localhost:8000`. Todos os tipos de dados, eventos SSE e fluxo de navegação estão definidos. O backend precisa implementar a lógica de processamento e expor os endpoints esperados.

## Endpoints Esperados pelo Frontend

| Método | Path | Descrição |
|--------|------|-----------|
| `POST` | `/api/upload/pdf` | Upload do PDF preenchido |
| `POST` | `/api/upload/xsd` | Upload do XSD (schema) |
| `POST` | `/api/upload/data` | Upload do arquivo de dados (JSON/XML) |
| `POST` | `/api/jobs` | Iniciar job de extração/matching |
| `GET` | `/api/progress/{jobId}` | Stream SSE de progresso |
| `GET` | `/api/result/{jobId}` | Resultado: ExtractionResult + HTML/CSS/JS |
| `POST` | `/api/preview` | Gerar preview do template gerado |
| `GET` | `/api/health` | Health check |

## Contratos de Dados (alinhados com frontend/src/types/index.ts)

```typescript
// Resultado esperado pelo frontend
interface ExtractionResult {
  fields: FieldMapping[]
  fidelityScore: number
  fidelityComment: string
  iaSuggestions: IASuggestion[]
  html: string
  css: string
  js: string
  exemplo: string
}

// Eventos SSE emitidos durante processamento
// event: step | pct | done | error | warning
// data: { step?: string, pct?: number, message?: string }
```

## Stories do Epic

### Story 3.1 — Scaffold FastAPI
**Objetivo:** Estrutura base do backend Python com FastAPI, CORS, upload de arquivos e health check.

**Escopo:**
- Inicializar projeto Python (`backend/`) com FastAPI + uvicorn
- Configurar CORS para `http://localhost:5173`
- Endpoints de upload: `POST /api/upload/pdf`, `/xsd`, `/data` — salvam arquivos em `/tmp/jobs/{jobId}/`
- `GET /api/health` retorna `{"status": "ok"}`
- `requirements.txt` com dependências mínimas
- Script de start: `uvicorn main:app --reload --port 8000`

**Arquivos a criar:**
- `backend/main.py`
- `backend/routers/upload.py`
- `backend/requirements.txt`
- `backend/.env.example`

---

### Story 3.2 — Extração de PDF
**Objetivo:** Extrair texto, posicionamento e estrutura do PDF usando `pdfplumber` ou `pypdf`.

**Escopo:**
- Serviço `PDFExtractor` que recebe path do PDF e retorna estrutura de campos detectados
- Extração de: texto, posição (x,y,w,h), fonte, tamanho, tabelas, imagens
- Suporte a PDFs multi-página
- Retornar lista de `TextBlock` com coordenadas normalizadas
- Integrar com rota `POST /api/jobs` (fase 1 do pipeline)
- Emitir eventos SSE: `step: "Extraindo PDF"`, `pct: 20`

**Arquivos a criar:**
- `backend/services/pdf_extractor.py`
- `backend/models/text_block.py`

---

### Story 3.3 — Matching IA com Campos JSON/XSD
**Objetivo:** Implementar matching semântico entre blocos extraídos do PDF e campos do contrato (JSON/XSD).

**Escopo:**
- Parser de XSD: extrair campos, tipos, `minOccurs`
- Parser de JSON/XML de dados: extrair campos e valores
- Algoritmo de matching:
  - Correspondência por nome normalizado (sem acento, lowercase)
  - Correspondência semântica (distância de string / embeddings simples)
  - Score de confiança por campo: 🟢 ≥0.8, 🟡 0.5–0.8, 🔴 <0.5
- Normalização de formatos: moeda BR, datas, CEP, telefone
- Validação cruzada XSD vs dados: detectar campos ausentes em cada lado
- Retornar `ExtractionResult.fields: FieldMapping[]`
- Emitir SSE: `step: "Matching de campos"`, `pct: 60`

**Arquivos a criar:**
- `backend/services/xsd_parser.py`
- `backend/services/data_parser.py`
- `backend/services/matcher.py`
- `backend/models/field_mapping.py`

---

### Story 3.4 — Jobs Assíncronos e SSE Progress
**Objetivo:** Implementar fila de jobs assíncrona com streaming de progresso via Server-Sent Events.

**Escopo:**
- `POST /api/jobs` — cria job, retorna `{ jobId: string }`
- Job executa pipeline: extração PDF → matching → geração HTML
- `GET /api/progress/{jobId}` — endpoint SSE com `EventSourceResponse`
- Eventos emitidos: `step`, `pct`, `done`, `error`, `warning`
- Jobs gerenciados em memória (dict global ou asyncio Queue)
- Timeout de job: 5 minutos
- `GET /api/result/{jobId}` — retorna `ExtractionResult` completo após `done`

**Arquivos a criar:**
- `backend/routers/jobs.py`
- `backend/services/job_manager.py`
- `backend/routers/progress.py`

---

### Story 3.5 — Geração de Template HTML/Knockout.js
**Objetivo:** Gerar o template HTML + CSS + JS/Knockout.js a partir do mapeamento de campos.

**Escopo:**
- Serviço `TemplateGenerator` que recebe `FieldMapping[]` e estrutura do PDF
- Gerar `html`: template com bindings Knockout.js (`data-bind="text: campo"`)
- Gerar `css`: estilos preservando layout visual do PDF (fontes, tamanhos, posicionamento)
- Gerar `js`: `base.js` com normalizadores de formato por campo
- Gerar `exemplo.js`: dados de exemplo para preview
- Calcular `fidelityScore` (0–100) comparando layout original vs gerado
- `POST /api/preview` — gerar preview HTML completo para iframe
- Emitir SSE: `step: "Gerando template"`, `pct: 85`

**Arquivos a criar:**
- `backend/services/template_generator.py`
- `backend/services/fidelity_scorer.py`
- `backend/routers/preview.py`
- `backend/templates/base_template.html`

---

## Estrutura de Diretórios Target

```
backend/
├── main.py                    # App FastAPI + CORS + routers
├── requirements.txt
├── .env.example
├── routers/
│   ├── upload.py              # POST /api/upload/*
│   ├── jobs.py                # POST /api/jobs, GET /api/result/{id}
│   ├── progress.py            # GET /api/progress/{id} (SSE)
│   └── preview.py             # POST /api/preview
├── services/
│   ├── pdf_extractor.py       # Extração de PDF
│   ├── xsd_parser.py          # Parser de XSD
│   ├── data_parser.py         # Parser JSON/XML
│   ├── matcher.py             # Matching semântico
│   ├── template_generator.py  # Geração HTML/Knockout
│   ├── fidelity_scorer.py     # Score de fidelidade
│   └── job_manager.py         # Fila de jobs assíncronos
└── models/
    ├── text_block.py
    ├── field_mapping.py
    └── job.py
```

## Dependências Python

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.9    # Upload de arquivos
pdfplumber>=0.10.0         # Extração de PDF
lxml>=5.0.0                # Parser XSD/XML
sse-starlette>=2.0.0       # Server-Sent Events
python-dotenv>=1.0.0
```

## Quality Gates

- `@architect`: revisão da estrutura de routers/services, padrão async/await, segurança de upload
- `tsc --noEmit` frontend: verificar que contratos não foram quebrados
- Teste manual: pipeline completo PDF → HTML com arquivo real do planetexpress

## 🤖 CodeRabbit Integration

> **CodeRabbit Integration**: Disabled
>
> CodeRabbit CLI is not enabled em `core-config.yaml`.
> Quality validation via manual review + architect gate.

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-03-12 | 1.0 | Epic criado — backend FastAPI do zero | @pm (Morgan) |
