# Auditoria: Upload + Fluxo de Navegação (Home → Upload → Analyzing → Editor)

**Data:** 2026-04-07  
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**Fontes:** `docs/prd-v3.md` (FR1, FR2, FR2a, FR2b, Modelo de Navegação) e `docs/wireframes/wireframes-mid-fi.md` (Telas 0 e 1)

### Modelo de Navegação (PRD v3.0)

```
HOME → UPLOAD → ANALYZING → EDITOR
HOME ← Abrir Projeto (.json) → EDITOR (direto, sem Analyzing)
```

### Tela Home (wireframe)
- Dois cards: **Novo Template** (→ Upload) e **Abrir Projeto** (→ carrega .json → EDITOR)
- Botão **Bibliotecas** no header abre modal global

### Tela Upload (FR1, FR2, FR2a, FR2b, wireframe Tela 1)
- **FR1:** Dropzone múltiplos PDFs — mínimo 1 obrigatório, recomendado 3-5
- **FR2:** XSD obrigatório — define nomes canônicos para data-bind Knockout
- **FR2a:** Arquivo de dados XML ou JSON opcional (1 arquivo)
- **FR2b:** Geração sintética de dados de exemplo a partir do XSD (`exemplo.js`)
- **Campo Nome do Template** — identificador do projeto
- **Hints contextuais** conforme estado dos arquivos:
  - Sem arquivos: "Envie ao menos 1 PDF + XSD para continuar"
  - 1 PDF + XSD: "Adicionar mais PDFs melhora a detecção de variações"
  - PDF sem XSD: botão desabilitado
  - PDF + XSD sem dados: "Adicionar dados reais melhora detecção de tipos"
- **Iniciar Análise** → navega para tela Analyzing (não diretamente para o Editor)
- **Voltar** → retorna à Home

---

## Frontend — Status de Implementação

### HomePage.vue (`frontend/src/pages/HomePage.vue`)

| Item planejado | Status | Detalhe |
|---|---|---|
| Card Novo Template → `/upload` | ✅ Implementado | `startNew()` faz `$reset()` e `router.push('/upload')` |
| Card Abrir Projeto → carrega `.json` → `/editor` | ✅ Implementado | `onFileSelected()` suporta formato v2.0 e legacy v1.0 |
| Restauração completa de estado (SavedProjectV2) | ✅ Implementado | `session.loadFromSavedProject(data)` + 4 stores resetados |
| Botão Bibliotecas no header | ✅ Implementado | `<BibliotecasModal>` com prop `:open="isBibliotecasOpen"` |

### UploadPage.vue (`frontend/src/pages/UploadPage.vue`)

| Item planejado | Status | Detalhe |
|---|---|---|
| Dropzone PDFs múltiplos (drag-and-drop) | ✅ Implementado | `@dragenter/dragover/dragleave/drop` + `multiple` no `<input>` |
| Dropzone XSD obrigatório (drag-and-drop) | ✅ Implementado | Separado, com botão limpar |
| Dropzone XML/JSON opcional (FR2a) | ✅ Implementado | Aceita `.xml,.json`, opcional |
| Campo Nome do Template | ✅ Implementado | `v-model="templateName"` |
| Lista de PDFs com remoção individual | ✅ Implementado | `removePdf(index)` com botão 🗑️ |
| Contagem de PDFs com label "recomendado: 3-5" | ✅ Implementado | `📊 {{ pdfFiles.length }} PDFs (recomendado: 3-5)` |
| Botão desabilitado sem PDF+XSD | ✅ Implementado | `isAnalyzeDisabled = !hasPdf \|\| !hasXsd \|\| isUploading` |
| Hints contextuais (4 cenários do wireframe) | ✅ Implementado | `currentHint` computed com 4 casos (AC4-7) |
| Progresso de upload com percentual (XHR onprogress) | ✅ Implementado | `uploadProgress` via `XMLHttpRequest` |
| Deduplicação por nome ao adicionar PDFs | ✅ Implementado | `existingNames` Set |
| Validação de tamanho (PDFs: 50 MB, outros: 10 MB) | ✅ Implementado | `validatePdfSize()` e `validateOtherSize()` |
| Navegação para `/analyzing` após upload | ✅ Implementado | `router.push('/analyzing')` em `handleSuccess()` |
| **FR2b: Geração sintética de exemplo (XSD → exemplo.js)** | ❌ Não implementado | Nenhuma lógica de geração sintética no frontend nem no backend de upload |
| Hint específico "PDF sem XSD → botão desabilitado" com mensagem | 🟡 Parcial | Botão desabilitado ✅, mas o hint exibido não é "botão desabilitado" — é genérico |

### Router (`frontend/src/router/index.ts`)

| Item planejado | Status | Detalhe |
|---|---|---|
| Rotas: `/`, `/upload`, `/analyzing`, `/editor` | ✅ Implementado | Todas as 4 rotas presentes |
| Guard: `/analyzing` sem `jobId` → redirect para Upload | ✅ Implementado | `if (to.name === 'analyzing' && !session.jobId)` |
| Guard: `/editor` sem `analysisCompleted` → redirect para Home | ✅ Implementado | `session.analysisCompleted !== true` |
| Guard de autenticação (`auth.isAuthenticated`) | ✅ Implementado | Todas as rotas não-públicas |

---

## Backend — Status de Implementação

### `/api/upload` (`backend/routers/upload.py`)

| Item planejado | Status | Detalhe |
|---|---|---|
| Endpoint unificado `POST /upload` (PDFs + XSD + data opcional) | ✅ Implementado | `upload_unified()` com `pdfs[]`, `xsd`, `data` e `template_name` |
| Aceita múltiplos PDFs (`pdfs[]`) | ✅ Implementado | `list[UploadFile]` com alias `pdfs[]` |
| XSD obrigatório | ✅ Implementado | `xsd: UploadFile = File(...)` |
| Data XML/JSON opcional | ✅ Implementado | `data: UploadFile \| None = File(None)` |
| Detecção de extensão por conteúdo (fallback) | ✅ Implementado | `data_content.lstrip().startswith(b"<")` |
| Validação de tamanho máximo (50 MB) | ✅ Implementado | `_MAX_FILE_SIZE_BYTES` via env `MAX_FILE_SIZE_MB` |
| Validação de contagem máxima de páginas (500) | ✅ Implementado | `_MAX_PAGE_COUNT` via env `MAX_PAGE_COUNT` |
| Retorna `job_id` | ✅ Implementado | `{"job_id": str(job_id)}` |
| **FR2b: Geração sintética de dados a partir do XSD** | ❌ Não implementado | Nenhum endpoint ou service para gerar `exemplo.js` sintético |
| **`template_name` salvo/utilizado no pipeline** | ❌ Não implementado | `template_name` é aceito no `Form` mas não é persistido no storage nem propagado para o pipeline |

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | FR2b ausente: Geração sintética de dados de exemplo a partir do XSD (`exemplo.js`) não implementada em nenhuma camada | 🔴 Crítico | Backend + Frontend | FR2b, PRD v3.0 |
| 2 | `template_name` não é persistido: aceito no upload mas descartado; não chega ao pipeline nem ao resultado | 🟡 Importante | Backend | `upload.py` linha 37; spec PRD "Nome do Template" |
| 3 | Hint de "botão desabilitado" (cenário PDF sem XSD) não é textual: há um hint genérico de ausência de arquivos, mas o estado específico PDF+sem-XSD não exibe mensagem dedicada conforme wireframe | 🟢 Menor | Frontend | Wireframe Tela 1 "Hints contextuais" |
| 4 | Ausência de hint para o estado "XSD sem PDF": há hint para ausência de ambos, mas não para XSD isolado | 🟢 Menor | Frontend | Wireframe Tela 1 "Hints contextuais" |

---

## Backlog Gerado

1. **[Backend] Implementar geração sintética de dados (FR2b):** Criar service `xsd_synthetic_generator.py` que parseia o XSD e gera um arquivo `exemplo.js` com valores coerentes por tipo (`xs:string`, `xs:date`, `xs:decimal`, CPF, CNPJ). Expor como parte do resultado do pipeline no `job_state["result"]`.

2. **[Backend] Persistir `template_name` no job:** Ao receber `template_name` no `POST /upload`, salvá-lo junto ao job (ex: `storage.upload_asset(job_id, "template_name.txt", template_name.encode())`), e propagá-lo para o resultado final do pipeline para exibição no editor.

3. **[Frontend] Hint específico para PDF-sem-XSD:** Adicionar caso ao `currentHint` computed: quando `hasPdf && !hasXsd`, exibir "💡 Adicione o XSD para habilitar Iniciar Análise".

4. **[Frontend] Hint para XSD-sem-PDF:** Adicionar caso: quando `!hasPdf && hasXsd`, exibir "💡 Adicione ao menos 1 PDF para continuar".

---

## Status Geral

🟡 Parcial — O núcleo do fluxo Upload→Analyzing→Editor está totalmente implementado, incluindo drag-and-drop, hints contextuais, validações, upload com progresso e navegação com guards. O gap crítico é a ausência completa da FR2b (geração sintética de dados do XSD), e o `template_name` é silenciosamente descartado após o upload.
