# Arquitetura Técnica — Migrador Planetexpress → HTML/Knockout.js

**Versão:** 3.0
**Data:** 2026-03-10
**Autor:** @architect (Aria)
**Status:** Aprovada

---

## Change Log

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0 | 2026-03-09 | Versão inicial — web app hospedada, servidor com sessões em disco |
| 2.0 | 2026-03-10 | Revisão completa — Tauri como shell desktop, servidor 100% stateless sem disco, geração em RAM com stream ZIP, sem Supabase, sem PostgreSQL |
| 2.1 | 2026-03-10 | Bibliotecas: catálogo local gerenciado pelo Tauri no workspace do usuário |
| 3.0 | 2026-03-10 | Tauri removido — web app puro no browser (Chrome/Edge); File System Access API substitui IPC Rust; IndexedDB substitui Tauri store; alinhado com NFR1 e NFR2 sem conflitos |
| 3.1 | 2026-03-10 | Gap review: (1) "stateless" redefinido como "sem disco/banco" — in-memory efêmero por job é correto; (2) ZIP agora autocontido com Bibliotecas bundladas pelo servidor — resolve NFR7; (3) preview da Tela 5 via /preview/{jobId} com cache efêmero; (4) deploy unificado — FastAPI serve o frontend via StaticFiles |

---

## 1. Visão Geral

Aplicação **web hospedada**, acessada no browser sem instalação. FastAPI serve tanto a API quanto o frontend Vue 3 compilado (StaticFiles). O servidor Python processa PDF e orquestra IA em memória RAM — **sem disco, sem banco de dados**. O estado efêmero por job (filas de progresso, cache de preview) existe apenas em memória enquanto a operação está ativa.

**Definição precisa de "sem persistência":**
- **Sem disco:** nenhum arquivo escrito no servidor
- **Sem banco:** nenhum PostgreSQL, Redis, Supabase ou similar
- **Com estado efêmero em memória:** filas de progresso por jobId e cache de preview (TTL 10min) — correto e esperado para instância única

```
┌──────────────────────────────────────────────────────────────┐
│  BROWSER  (Chrome/Edge — zero instalação, URL direta)        │
│                                                               │
│  Vue 3 + TypeScript + Vite + Pinia                           │
│  ├── PDF.js          render PDF + seleção interativa (FR8)   │
│  ├── Monaco Editor   editor de código (FR24)                 │
│  ├── Chart.js        preview de gráficos (FR26)              │
│  ├── SSE client      progresso em tempo real                 │
│  ├── File System Access API  (nativa, zero dependência)      │
│  │   ├── showOpenFilePicker()   → PDF, XSD, dados, projeto   │
│  │   └── showSaveFilePicker()   → salvar projeto .json       │
│  └── IndexedDB (idb)            → catálogo Bibliotecas       │
└──────────────────────────────────────────────────────────────┘
                    ↕  REST + SSE  (JSON e bytes)
┌──────────────────────────────────────────────────────────────┐
│  SERVIDOR  FastAPI / Python — sem disco, sem banco           │
│                                                               │
│  POST /extract      PyMuPDF em RAM → JSON estruturado        │
│  POST /ai/match     LiteLLM → Gemini 2.0 Flash               │
│  POST /ai/fidelity  LiteLLM → Claude Sonnet                  │
│  POST /ai/correct   LiteLLM → Claude Sonnet                  │
│  POST /ai/font      LiteLLM → Gemini Vision                  │
│  POST /generate     gera ZIP em RAM → stream + cache preview │
│  GET  /progress/{jobId}   SSE (asyncio.Queue em memória)     │
│  GET  /preview/{jobId}    HTML renderizável (cache 10min)    │
│  GET  /                   serve frontend Vue (StaticFiles)   │
│                                                               │
│  Estado efêmero em memória:                                  │
│  job_queues: Dict[jobId, asyncio.Queue]  ← progresso ativo  │
│  preview_cache: Dict[jobId, Output]      ← TTL 10min        │
└──────────────────────────────────────────────────────────────┘
                    ↕  HTTPS
       Gemini API / Claude API (Anthropic)
```

---

## 2. Decisões Arquiteturais

### 2.1 Por que web app puro (não Tauri, não Electron, não PWA)

| Opção avaliada | Avaliação |
|----------------|-----------|
| Electron | 150MB de Chromium embutido; Node.js redundante com Python no servidor; requer instalador |
| Tauri | ~10MB mas ainda requer instalação; Rust sem ganho real pois File System Access API cobre tudo; viola NFR1 e NFR2 |
| PWA (installable) | Adiciona camada de instalação opcional sem benefício; a ferramenta funciona sem instalar |
| **Web app puro** | Zero instalação; URL direta; update automático via deploy; File System Access API cobre todos os casos de uso de arquivo local |

**O Tauri foi avaliado e descartado porque:**
1. NFR1 exige "acessível via browser sem instalação" — Tauri requer instalação
2. NFR2 exige "sem instalações complexas" — Tauri é uma instalação
3. Todo o Rust era wrapper sobre APIs que o Chrome/Edge já implementam nativamente (File System Access API)
4. Auto-update via Tauri é mais complexo que auto-update via deploy do servidor (que é zero-config)
5. Vibe coding com apenas Vue + Python é mais fluido que Vue + Python + Rust

### 2.2 File System Access API — o que resolve

A File System Access API está disponível no Chrome e Edge (que são exatamente os browsers alvo definidos no PRD). Cobre todos os casos de uso de arquivo local sem nenhuma instalação:

| Necessidade | API usada | Comportamento |
|-------------|-----------|---------------|
| Upload PDF / XSD / dados | `showOpenFilePicker()` | Dialog de arquivo padrão |
| Salvar projeto `.json` | `showSaveFilePicker()` | Dialog "Salvar como" |
| Abrir projeto salvo | `showOpenFilePicker()` | Lê JSON, restaura estado |
| Selecionar pasta Bibliotecas | `showDirectoryPicker()` | Dialog de pasta |
| Persistir handle entre sessões | `IndexedDB` (idb) | Handle salvo, permissão re-solicitada |
| Re-acessar Bibliotecas na sessão seguinte | `handle.requestPermission()` | Banner pequeno, 1 clique |
| Download do ZIP gerado | `StreamingResponse` → download nativo | Browser gerencia automaticamente |

### 2.3 Por que servidor stateless sem disco

O servidor **nunca escreve em disco**. Todo processamento ocorre em RAM:

- PDF recebido como bytes → PyMuPDF lê da RAM → retorna JSON → bytes descartados
- Geração de HTML/CSS/JS → strings Python em memória → ZIP em BytesIO → stream → RAM liberada
- Sem pastas de sessão, sem storage externo, sem banco de dados

**Exceção explícita — catálogo de Bibliotecas (FR27a):** o catálogo de fontes/CSS/JS é persistente por natureza. Ele **não passa pelo servidor** — vive exclusivamente no filesystem local do usuário, acessado via File System Access API. Ver seção 12.

### 2.4 Por que sem Supabase/PostgreSQL

Para 1-3 usuários migrando 21-100 templates:

| O que Supabase resolveria | Necessário? |
|--------------------------|-------------|
| Backend stateless | Não — processamento em RAM resolve |
| Persistência de jobs | Não — SSE streaming é suficiente |
| Versionamento de projetos | Não — FR10 resolve com `.json` local (File System Access API) |
| Storage de uploads e outputs | Não — RAM + stream |

Supabase seria correto para 10+ usuários com histórico de projetos no servidor. Para este contexto, adiciona complexidade e custo sem benefício.

### 2.5 Por que geração no servidor (não no cliente)

A geração de `index.html`, `style.css`, `base.js` e `exemplo.js` fica no Python porque:

1. Lógica de domínio complexa (Knockout bindings, formatadores BR, paginação)
2. Centralizada e testável em Python
3. Imagens já estão em RAM desde a extração — incluí-las no ZIP é natural
4. Cliente permanece exclusivamente como camada de UI

O servidor gera tudo em RAM e faz **streaming do ZIP diretamente** — sem salvar em disco.

### 2.6 Por que Python no backend

| Alternativa | Por que Python vence |
|-------------|---------------------|
| Node.js | `pdf-parse` limitado vs `PyMuPDF` (coordenadas precisas, fontes, tabelas, imagens) |
| Node.js | Ecossistema IA/ML é Python — LiteLLM, Anthropic SDK nativos |
| Node.js | `lxml` para XSD é mais robusto que alternativas JS |

### 2.7 Por que Vue 3 no frontend

| Alternativa | Por que Vue 3 vence |
|-------------|---------------------|
| Blazor WASM | Exige JS interop para PDF.js e Monaco — os componentes mais críticos |
| React | Vue 3 tem curva menor, Composition API similar ao C# |
| Angular | Overhead desnecessário para ferramenta interna |

### 2.8 Estratégia multi-modelo de IA (LiteLLM)

| Operação | Modelo | Justificativa |
|----------|--------|---------------|
| FR4 — Matching semântico | `gemini/gemini-2.0-flash` | Alto volume, texto puro, custo mínimo |
| FR2b — Dados sintéticos XSD | `gemini/gemini-2.0-flash` | Geração estruturada simples |
| FR27 — Font detection (visão) | `gemini/gemini-1.5-flash` | Visão básica, custo mínimo |
| FR33 — Score de fidelidade | `claude-sonnet-4-6` | Análise visual detalhada |
| FR34 — Auto-correção HTML/CSS | `claude-sonnet-4-6` | Melhor raciocínio sobre código |

**Custo estimado por documento: $0.05–$0.20 | 100 templates: $5–$20 total**

---

## 3. Stack Tecnológica

### 3.1 Frontend (browser)

| Tecnologia | Versão | Função |
|------------|--------|--------|
| Vue 3 | 3.5+ | Framework UI |
| TypeScript | 5.x | Tipagem estática |
| Vite | 6.x | Build tool + dev server |
| Pinia | 2.x | State management |
| Vue Router | 4.x | Navegação entre telas do wizard |
| PDF.js | 4.x | Renderização de PDF + seleção de texto (FR8) |
| Monaco Editor | 0.52+ | Editor de código embutido (FR24) |
| Chart.js | 4.x | Preview e configuração de gráficos (FR26) |
| idb | 8.x | Wrapper ergonômico para IndexedDB (catálogo Bibliotecas) |
| File System Access API | nativa | Acesso ao filesystem local (sem lib extra) |

### 3.2 Backend Remoto

| Tecnologia | Versão | Função |
|------------|--------|--------|
| Python | 3.12+ | Linguagem |
| FastAPI | 0.115+ | Framework REST + SSE |
| Uvicorn | 0.32+ | ASGI server |
| PyMuPDF (fitz) | 1.24+ | Extração de PDF (texto, coordenadas, fontes, imagens, tabelas) |
| lxml | 5.x | Parse de XSD e XML |
| LiteLLM | 1.x | Interface unificada Gemini + Claude |
| Pillow | 10.x | Processamento de imagens extraídas |
| python-multipart | 0.0.x | Upload de bytes multipart |

### 3.3 Infraestrutura

| Componente | Escolha |
|------------|---------|
| Deploy backend | Railway |
| Deploy frontend | Railway (estático) ou Vercel |
| Auth | HTTP Basic (se URL pública) / IP whitelist (se VPN) |
| Banco de dados | Nenhum |
| Storage | Nenhum |
| Background tasks | FastAPI BackgroundTasks + asyncio |

---

## 4. Estrutura do Repositório

```
migrador-planet/
├── frontend/                    # Vue 3 app (sem Rust, sem Tauri)
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── router/index.ts      # Rotas: /, /upload, /campos, /layout, /geracao, /exportar
│   │   ├── stores/
│   │   │   ├── session.ts       # jobId, estado global
│   │   │   ├── mapping.ts       # campos mapeados, status ✅🟡🔴
│   │   │   └── layout.ts        # configurações de página e layout
│   │   ├── views/
│   │   │   ├── HomeView.vue     # Tela 0 — Novo Template / Abrir Projeto
│   │   │   ├── UploadView.vue   # Tela 1 — upload PDF + XSD + dados
│   │   │   ├── CamposView.vue   # Tela 2 — de-para + PDF.js + painel
│   │   │   ├── LayoutView.vue   # Tela 3 — configurações de layout
│   │   │   ├── GeracaoView.vue  # Tela 4 — preview + Monaco + fidelidade
│   │   │   └── ExportarView.vue # Tela 5 — download ZIP
│   │   ├── components/
│   │   │   ├── PdfViewer.vue        # PDF.js wrapper + seleção de texto
│   │   │   ├── FieldPanel.vue       # Painel de-para com status
│   │   │   ├── MonacoEditor.vue     # Monaco wrapper
│   │   │   ├── ProgressBar.vue      # Progresso global
│   │   │   ├── WizardNav.vue        # Progress bar 5 etapas
│   │   │   └── BibliotecasModal.vue # Gestão de fontes/CSS/JS
│   │   └── composables/
│   │       ├── useSSE.ts        # EventSource para progresso
│   │       ├── useSession.ts    # jobId e estado de sessão
│   │       ├── useFileSystem.ts # File System Access API (substitui useTauri.ts)
│   │       └── useBibliotecas.ts# Catálogo IndexedDB + FileSystemDirectoryHandle
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
│
├── backend/                     # Servidor Python
│   ├── main.py                  # FastAPI app
│   ├── routers/
│   │   ├── extract.py           # POST /extract
│   │   ├── ai.py                # POST /ai/match, /ai/fidelity, /ai/correct, /ai/font
│   │   └── generate.py          # POST /generate → stream ZIP
│   ├── services/
│   │   ├── pdf_extractor.py     # PyMuPDF em RAM
│   │   ├── xsd_parser.py        # lxml — XSD → árvore de campos
│   │   ├── ai_matcher.py        # LiteLLM → Gemini (matching FR4)
│   │   ├── ai_vision.py         # LiteLLM → Claude (fidelidade FR33)
│   │   ├── html_generator.py    # Gera index.html + bindings Knockout
│   │   ├── css_generator.py     # Gera style.css com layout do PDF
│   │   ├── js_generator.py      # Gera base.js + exemplo.js
│   │   └── zip_builder.py       # Empacota tudo em BytesIO
│   ├── models/
│   │   ├── extraction.py        # TextBlock, Font, Image, PageStructure
│   │   ├── mapping.py           # FieldMatch, ConfidenceLevel, MappingResult
│   │   └── generation.py        # GenerationRequest, GenerationResult
│   ├── core/
│   │   └── config.py            # Settings (API keys, limites)
│   └── requirements.txt
│
└── docs/
    ├── prd.md
    ├── architecture/
    │   ├── architecture.md      # este documento
    │   └── architecturev2.md   # proposta comparativa (referência histórica)
    └── wireframes/
        └── wireframes-mid-fi.md
```

---

## 5. File System Access API — Implementação

### 5.1 useFileSystem.ts

```typescript
// composables/useFileSystem.ts
// File System Access API — substitui completamente o Tauri IPC

export const useFileSystem = () => {

  // Abre um arquivo e retorna os bytes (para upload ao servidor)
  const abrirArquivo = async (tipos: FilePickerAcceptType[]) => {
    const [handle] = await window.showOpenFilePicker({ types: tipos })
    const file = await handle.getFile()
    return { bytes: await file.arrayBuffer(), nome: file.name, handle }
  }

  // Salva conteúdo em arquivo — abre dialog "Salvar como"
  const salvarArquivo = async (conteudo: string, nome: string) => {
    const handle = await window.showSaveFilePicker({
      suggestedName: nome,
      types: [{ description: 'Projeto', accept: { 'application/json': ['.json'] } }]
    })
    const writable = await handle.createWritable()
    await writable.write(conteudo)
    await writable.close()
  }

  // Recebe blob do servidor e dispara download nativo
  const baixarZip = (blob: Blob, nome: string) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = nome
    a.click()
    URL.revokeObjectURL(url)
  }

  return { abrirArquivo, salvarArquivo, baixarZip }
}
```

### 5.2 useBibliotecas.ts

```typescript
// composables/useBibliotecas.ts
// Catálogo de Bibliotecas: FileSystemDirectoryHandle + IndexedDB (idb)

import { openDB } from 'idb'

const DB_NAME = 'migrador-planet'
const STORE = 'bibliotecas'

export const useBibliotecas = () => {
  const db = openDB(DB_NAME, 1, {
    upgrade(db) { db.createObjectStore(STORE) }
  })

  // Solicita acesso à pasta Bibliotecas — salva handle no IndexedDB
  const selecionarPasta = async () => {
    const handle = await window.showDirectoryPicker()
    const store = await db
    await (await store).put(handle, 'bibliotecasHandle')
    return handle
  }

  // Recupera handle salvo e re-solicita permissão (banner pequeno)
  const recuperarPasta = async (): Promise<FileSystemDirectoryHandle | null> => {
    const store = await db
    const handle = await (await store).get('bibliotecasHandle')
    if (!handle) return null
    const perm = await handle.requestPermission({ mode: 'read' })
    return perm === 'granted' ? handle : null
  }

  // Lista arquivos de um tipo dentro da pasta Bibliotecas
  const listar = async (handle: FileSystemDirectoryHandle, tipo: 'fonts' | 'css' | 'js') => {
    const subDir = await handle.getDirectoryHandle(tipo, { create: true })
    const arquivos: string[] = []
    for await (const [nome] of subDir.entries()) arquivos.push(nome)
    return arquivos
  }

  // Adiciona arquivo à pasta Bibliotecas (copia via FileSystem API)
  const adicionar = async (handle: FileSystemDirectoryHandle, tipo: string, file: File) => {
    const subDir = await handle.getDirectoryHandle(tipo, { create: true })
    const dest = await subDir.getFileHandle(file.name, { create: true })
    const writable = await dest.createWritable()
    await writable.write(await file.arrayBuffer())
    await writable.close()
  }

  // Remove arquivo da pasta Bibliotecas
  const remover = async (handle: FileSystemDirectoryHandle, tipo: string, nome: string) => {
    const subDir = await handle.getDirectoryHandle(tipo)
    await subDir.removeEntry(nome)
  }

  return { selecionarPasta, recuperarPasta, listar, adicionar, remover }
}
```

---

## 6. Fluxo de Dados Completo

### 6.1 Orquestração pelo cliente (multi-step)

O cliente (Pinia store) é o coordenador do fluxo. O servidor não tem conhecimento das etapas anteriores — cada chamada recebe tudo que precisa no corpo da requisição:

```
CLIENTE (Pinia)                    SERVIDOR
────────────────────────           ─────────────────────────────
showOpenFilePicker() → PDF bytes
POST /extract ─────────────────→   PyMuPDF em RAM
  { pdf, xsd?, data? }   ←──────   retorna JSON completo
store.extraction = result          (bytes descartados)

POST /ai/match ────────────────→   LiteLLM → Gemini Flash
  { textBlocks, fieldTree }        abre asyncio.Queue[jobId]
SSE /progress/{jobId} ─────────→   emite progresso incremental
               ←───────────────    retorna mapping + scores
store.mapping = result             (Queue descartada)

[operador revisa, edita]

POST /generate ────────────────→   gera em RAM:
  { mapping, layout, libs }          index.html, style.css
  (cliente envia tudo)               base.js, exemplo.js, imgs
               SSE /progress ──→   emite % de geração
               ←─ ZIP stream ───   StreamingResponse
               ←─ preview cache─   guarda Output 10min
```

**Nota sobre jobId:** é gerado pelo servidor na primeira chamada de uma operação longa (/ai/match ou /generate) e retornado ao cliente. O cliente usa esse jobId apenas para abrir o SSE correspondente. Não há estado persistido entre chamadas distintas.

### 6.2 Geração e download (Tela 4 → Tela 5)

```
Operador confirma mapeamento e layout
        ↓
POST /generate  { mapping, layout, libs[], images[] }
  (cliente envia tudo — servidor não precisa de contexto anterior)
        ↓
Servidor em RAM:
  html_generator  → index.html (Knockout bindings, refs relativas)
  css_generator   → style.css (coordenadas do PDF)
  js_generator    → base.js + exemplo.js
  zip_builder:
    buffer = io.BytesIO()
    ZipFile(buffer):
      writestr('index.html', html)           ← refs: ./js/, ./css/
      writestr('css/style.css', css)
      writestr('js/base.js', js)
      writestr('js/exemplo.js', exemplo)
      for lib in libs_padrao:               ← bundla Bibliotecas
        writestr(f'{lib.path}', lib.bytes)  ← ex: js/knockout.js
      for img in images:
        writestr(f'img/{img.nome}', img.bytes)
    buffer.seek(0)
        ↓
preview_cache[jobId] = output  ← cache efêmero 10min
        ↓
StreamingResponse(buffer, media_type='application/zip')
        ↓
Browser → baixarZip() dispara download nativo

ZIP resultante é autocontido (NFR7):
  template.zip/
    index.html            ← <script src="./js/knockout.js">
    css/style.css
    css/sentico.css        ← bundlado do servidor
    js/base.js
    js/exemplo.js
    js/knockout-3.4.2.js  ← bundlado do servidor
    js/knockout.mapping.js
    fonts/MinhaFonte.woff  ← bundlado do servidor
    img/
  → abrir index.html localmente funciona sem dependências externas
```

### 6.3 Preview na Tela 5

```
Operador clica [Abrir Preview]
        ↓
Cliente abre nova aba: GET /preview/{jobId}
        ↓
Servidor recupera Output do preview_cache
Retorna HTMLResponse com HTML completo
  (CSS e JS injetados inline para funcionar em qualquer contexto)
        ↓
Nova aba renderiza o documento com exemplo.js
  → visualização fiel sem depender de arquivo local
        ↓
Cache expirado após 10min → /preview retorna 404
  (usuário pode regerar ou usar o ZIP baixado)
```

---

## 7. API REST — Endpoints

```
POST   /extract                  Extrai PDF + parse XSD/dados em RAM → retorna JSON completo
GET    /progress/{jobId}         SSE — progresso da operação ativa (asyncio.Queue efêmera)
POST   /ai/match                 Matching semântico (Gemini Flash) → retorna mapping completo
POST   /ai/fidelity              Score visual (Claude Vision)
POST   /ai/correct               Auto-correção HTML/CSS (Claude)
POST   /ai/font                  Font detection (Gemini Vision)
POST   /generate                 Gera ZIP em RAM → stream + armazena preview em cache 10min
GET    /preview/{jobId}          Retorna HTML renderizável do último /generate (cache efêmero)
GET    /*                        Serve frontend Vue compilado (StaticFiles)
```

**Contrato de independência:** cada endpoint recebe no corpo tudo que precisa para executar. Nenhum endpoint depende de estado deixado por chamadas anteriores no servidor. O cliente (Pinia) é o único coordenador do fluxo multi-etapa.

**Estado efêmero em memória (não é persistência):**
- `job_queues[jobId]` — asyncio.Queue ativa enquanto uma operação processa; descartada ao concluir
- `preview_cache[jobId]` — output HTML do último /generate; TTL 10min; descartado automaticamente

---

## 8. Comunicação em Tempo Real (SSE)

```python
# Backend — stream de progresso sem estado em disco
async def stream_progress(job_id: str):
    yield f"data: {json.dumps({'step': 'Extraindo PDF', 'pct': 10})}\n\n"
    yield f"data: {json.dumps({'step': 'Matching com IA', 'pct': 45})}\n\n"
    yield f"data: {json.dumps({'step': 'Gerando HTML', 'pct': 80})}\n\n"
    yield f"data: {json.dumps({'step': 'Concluído', 'pct': 100})}\n\n"
```

```typescript
// Frontend — composable SSE
export const useSSE = (jobId: string, onProgress: (step: string, pct: number) => void) => {
  const source = new EventSource(`${API_BASE}/progress/${jobId}`)
  source.onmessage = (e) => {
    const { step, pct } = JSON.parse(e.data)
    onProgress(step, pct)
    if (pct === 100) source.close()
  }
}
```

---

## 9. Deploy

FastAPI serve tanto a API quanto o frontend Vue compilado. Uma URL, um deploy, sem CORS.

```python
# main.py
from fastapi.staticfiles import StaticFiles

app = FastAPI()
# routers da API primeiro
app.include_router(extract_router)
app.include_router(ai_router)
app.include_router(generate_router)
# frontend por último — captura tudo que não é API
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
```

```toml
# railway.toml
[build]
builder = "nixpacks"
buildCommand = "cd frontend && npm ci && npm run build && cd .."

[deploy]
startCommand = "uvicorn backend.main:app --host 0.0.0.0 --port $PORT"
```

```env
# Variáveis de ambiente no Railway
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
```

**Update da ferramenta = `git push`.** Railway rebuilda backend + frontend e reinicia. O browser carrega a nova versão na próxima abertura. Zero ação do usuário.

---

## 10. NFRs — Como a Arquitetura Atende

| NFR | Como atende |
|-----|-------------|
| NFR1 — Hospedável em servidor, acessível via browser sem instalação | FastAPI + Railway; frontend servido pelo próprio backend — zero instalação no cliente |
| NFR2 — Interface web sem instalações complexas | Browser Chrome/Edge direto na URL — absolutamente zero instalação |
| NFR3 — Precisão ≥ 80% matching | Gemini 2.0 Flash com contexto semântico + fallback básico |
| NFR4 — 50 páginas em < 60s | PyMuPDF em RAM é rápido; SSE garante feedback contínuo |
| NFR5 — Fidelidade visual | Claude Sonnet para score + FR25 WYSIWYG para ajustes |
| NFR6 — Caminhos aninhados JSON | Tratado em matching e geração de data-bind |
| NFR7 — ZIP autocontido | ZIP inclui todos os assets (Bibliotecas bundladas pelo servidor); HTML usa paths relativos internos; abre localmente sem dependências externas |

---

## 11. Comparação com Propostas Anteriores

| Tema | V1 (web hospedada) | V2 (Electron + Supabase) | V2.1 (Tauri + stateless) | **V3 — Final (web app puro)** |
|------|-------------------|--------------------------|--------------------------|-------------------------------|
| Shell | Browser | Electron 150MB | Tauri 10MB | **Browser (zero instalação)** |
| File access | File System Access API | Electron Main | Rust IPC | **File System Access API nativa** |
| Instalação | Não | Sim (150MB) | Sim (10MB) | **Não** |
| Persistência servidor | Sessões em disco | Supabase + Storage | Zero | **Zero** |
| Persistência cliente | Não | Electron store | Tauri store | **IndexedDB (nativo do browser)** |
| Auto-update | Deploy | Electron Updater | tauri-plugin-updater | **Deploy (automático)** |
| CI de empacotamento | Não | Sim | Sim | **Não** |
| Linguagens no repo | Vue + Python | Vue + Python + Node | Vue + Python + Rust | **Vue + Python** |
| NFR1 + NFR2 | Parcial | Não | Não | **Total** |
| Complexidade | Baixa | Alta | Média | **Mínima** |

---

## 12. Bibliotecas — Catálogo e Bundling (FR27 / FR27a)

### 12.1 Onde vivem os arquivos de Bibliotecas

Os assets padrão (knockout.js, sentico.css, fontes, etc.) ficam **no servidor**, dentro de `/backend/assets/libraries/`:

```
backend/
  assets/
    libraries/
      css/
        sentico.css
        sentico-v2.css
      js/
        knockout-3.4.2.js
        knockout.mapping.js
        chart.min.js
        chartjs-plugin-datalabels.min.js
      fonts/
        MinhaFonte.woff
        MinhaFonte.woff2
```

Esses arquivos são bundlados **dentro de cada ZIP gerado** pelo `zip_builder`. O ZIP é autocontido (NFR7) — não depende de nenhuma pasta externa no disco do usuário.

### 12.2 Catálogo no browser (IndexedDB)

O catálogo exibido na Tela 0 é uma lista de metadados dos assets disponíveis — carregada do servidor na inicialização e cacheada no IndexedDB:

```json
[
  { "tipo": "css",   "nome": "sentico.css",         "ativo": true },
  { "tipo": "js",    "nome": "knockout-3.4.2.js",   "ativo": true },
  { "tipo": "fonts", "nome": "MinhaFonte.woff",      "ativo": true }
]
```

O operador pode marcar quais assets são incluídos no próximo template. A seleção é enviada no corpo do POST /generate.

### 12.3 Fluxo de gestão (Tela 0 — BibliotecasModal)

```
Operador abre Tela 0 → clica [📚 Bibliotecas]
        ↓
GET /libraries → servidor retorna lista de assets disponíveis
Vue exibe nas 3 abas (Fontes / CSS / JS) com checkboxes
        ↓
[+ Adicionar Arquivo]
  showOpenFilePicker() → usuário seleciona arquivo local
  POST /libraries/upload { file, tipo }
  Servidor salva em /backend/assets/libraries/{tipo}/
  IndexedDB atualizado localmente
        ↓
[🗑️ Remover] → DELETE /libraries/{tipo}/{nome}
```

### 12.4 Como o ZIP inclui as Bibliotecas

```python
# zip_builder.py
def build_zip(html, css, js, exemplo, images, libs_selecionadas):
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w') as zf:
        zf.writestr('index.html', html)       # refs: ./js/, ./css/, ./fonts/
        zf.writestr('css/style.css', css)
        zf.writestr('js/base.js', js)
        zf.writestr('js/exemplo.js', exemplo)
        for lib in libs_selecionadas:
            path = ASSETS_DIR / lib.tipo / lib.nome
            zf.writestr(f'{lib.tipo}/{lib.nome}', path.read_bytes())
        for img in images:
            zf.writestr(f'img/{img.nome}', img.bytes)
    buffer.seek(0)
    return buffer
```

```python
# html_generator.py — paths relativos dentro do ZIP
HEAD_SCRIPTS = """
<link rel="stylesheet" href="./css/sentico.css">
<script src="./js/knockout-3.4.2.js"></script>
<script src="./js/knockout.mapping.js"></script>
"""
```

**Resultado:** unzip o template em qualquer pasta → abrir `index.html` → renderiza corretamente. Sem dependências externas.

---

## 13. Decisões Futuras (fora do MVP)

| Decisão | Quando revisar |
|---------|----------------|
| Supabase para histórico | Se projetos precisarem ser salvos no servidor |
| Redis para cache de IA | Se o mesmo PDF for processado repetidamente |
| Celery para fila | Se usuários simultâneos passarem de 10 |
| Auth OAuth | Se ferramenta for aberta para mais equipes |

---

— Aria, arquitetando o futuro 🏗️
