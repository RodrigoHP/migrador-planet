# Migrador Planet

Ferramenta de migração que converte documentos PDF gerados pelo motor PlanetExpress em templates HTML interativos com bindings Knockout.js. Inclui análise por IA (Vision AI), detecção de campos, descoberta de layout e geração de templates com preview e testes.

## Stack Tecnológica

| Camada | Tecnologias |
|--------|------------|
| **Frontend** | Vue 3, TypeScript 5.9, Vite 7.3, Pinia, Vue Router, Tailwind CSS 4, Monaco Editor, PDF.js |
| **Backend** | Python, FastAPI, Uvicorn, pdfplumber, PyMuPDF, scikit-learn, OpenAI/OpenRouter |
| **Testes** | Vitest + Vue Test Utils (frontend), pytest + pytest-asyncio (backend) |

## Estrutura do Projeto

```
migrador-planet/
├── frontend/                    # Vue 3 + TypeScript + Vite
│   └── src/
│       ├── pages/               # 4 páginas (Home, Upload, Analyzing, TemplateEditor)
│       ├── organisms/           # Componentes complexos (50+ arquivos)
│       ├── molecules/           # Componentes reutilizáveis (70+ arquivos)
│       ├── atoms/               # Componentes primitivos (15 arquivos)
│       ├── stores/              # Pinia stores (12+: template, editor, coverage, confidence, session...)
│       ├── services/            # Clientes API
│       ├── types/               # Interfaces TypeScript (~15 arquivos)
│       ├── composables/         # Composition functions
│       ├── utils/               # Helpers
│       └── router/              # Vue Router (4 rotas)
├── backend/                     # FastAPI Python
│   ├── main.py                  # Entry point (CORS, middleware, routers)
│   ├── routers/                 # 11 endpoints API
│   ├── services/                # Lógica de negócio
│   │   └── stages/              # Pipeline de 23 estágios ML
│   ├── models/                  # Pydantic schemas
│   └── tests/                   # 13 módulos de teste
├── docs/                        # PRD, specs, épicos, stories (96 stories)
│   ├── prd-v3.md                # Product Requirements Document
│   ├── front-end-spec.md        # Especificação UI detalhada
│   ├── stories/                 # Stories organizadas por épico
│   └── Exemplos/                # 40+ PDFs de exemplo reais
└── .claude/rules/               # Regras para agentes IA
```

## Comandos de Desenvolvimento

### Frontend
```bash
cd frontend
npm install              # Instalar dependências
npm run dev              # Dev server em :5173 (proxy para backend :8000)
npm run build            # Build de produção (tsc + vite)
npm run lint             # Type check (vue-tsc)
npm run typecheck        # Validação TypeScript
npm test                 # Testes unitários (Vitest)
```

### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py           # FastAPI em :8000
pytest                   # Testes
```

### Variáveis de Ambiente
Copiar `.env.example` para `.env`. A variável `OPENROUTER_API_KEY` é necessária para Vision AI.

## Arquitetura

### Frontend — Atomic Design + Pinia

- **Páginas:** HomePage → UploadPage → AnalyzingPage → TemplateEditor
- **TemplateEditor** possui 5 regiões: TopToolbar, LeftPanel (árvore + fields), CenterPanel (4 tabs: Canvas/PDF/Code/Sync), InspectorPanel (direita), TestDataPanel (inferior)
- **Stores principais:**
  - `templateStore` — FieldMapping, estrutura do documento, layouts
  - `editorStore` — Seleções ativas, estado do canvas
  - `coverageStore` — % de mapeamento por layout
  - `confidenceStore` — Métricas de confiança (5 fatores)
  - `session` — Job ID, progresso da análise, route guards

### Backend — Pipeline de 23 Estágios

O pipeline de análise processa PDFs em 23 estágios sequenciais registrados em `backend/services/stages/register_all.py`:
- Extração de texto, fontes e imagens
- Detecção de tabelas e grids CSS
- Análise semântica e matching de campos XSD ↔ PDF
- Descoberta de layout e clustering de páginas
- Scoring de confiança (5 fatores)
- Geração de draft do template
- Validação por Vision AI

**Progresso via SSE** (Server-Sent Events) no endpoint `POST /api/analyze`.

### API Endpoints Principais

```
POST   /api/upload          # Upload PDF, XSD, dados
POST   /api/analyze         # Iniciar pipeline → SSE stream
GET    /api/progress/{id}   # Status do job
POST   /api/preview         # Preview HTML+CSS+JS
POST   /api/generate        # Gerar arquivos de saída
GET    /api/export           # Download ZIP
POST   /api/auto-fix        # Sugestões Vision AI
```

### Output Gerado

O template gerado consiste em:
- `index.html` — HTML com bindings Knockout.js (`data-bind`)
- `style.css` — CSS para A4 (grid ou absolute positioning)
- `base.js` — Observables KO
- `exemplo.js` — Dados sintéticos de teste

## Convenções de Código

### Frontend
- **Atomic Design:** atoms → molecules → organisms → pages
- **TypeScript estrito** — interfaces em `src/types/`
- **Composables** para lógica reutilizável
- **Testes:** arquivos `.spec.ts` co-localizados ou em `__tests__/`
- **Tailwind CSS** para estilização

### Backend
- **FastAPI routers** em `backend/routers/` — um arquivo por domínio
- **Services** em `backend/services/` — lógica de negócio separada dos routers
- **Stages** em `backend/services/stages/` — cada estágio é um arquivo independente
- **Pydantic models** em `backend/models/`
- **Type hints** em todo o código Python

### Geral
- Idioma do código: inglês para identificadores, português para documentação e mensagens de UI
- Commits seguem conventional commits: `feat(scope):`, `fix(scope):`, etc.
- Stories organizadas por épico em `docs/stories/`

## Conceitos do Domínio

- **FieldMapping:** Mapeamento entre campo XSD e região detectada no PDF
- **Coverage (Cobertura):** % de campos mapeados vs detectados (≥95% completo, 80-95% revisar, <80% revisão necessária)
- **Confidence (Confiança):** 5 fatores — estabilidade, detecção de âncoras, qualidade do grid, variabilidade de campos, concordância da Vision AI
- **Layout Type:** Tipo de layout detectado por clustering de páginas similares
- **Format String:** String de formatação para valores (ex: `999.999.999,99` para valores monetários BR)
- **Structure Tree:** Hierarquia Document > Header > Flow > Footer
