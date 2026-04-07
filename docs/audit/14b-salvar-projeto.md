# Auditoria: Salvar / Abrir Projeto

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR10** (PRD v3.0): salvar e retomar sessões completas via botão 💾 Salvar na toolbar; serializa estado completo como JSON para download; não inclui PDFs originais nem assets binários; restaurável via Home → Abrir Projeto, que navega direto para o Editor.

**`docs/ideias/ux/template_saving_strategy.md`**: o template salvo é um pacote completo (`template.zip`) contendo:
- `template.json` (estrutura completa: seções, componentes, elementos, bindings, regras, âncoras, estilos, posições)
- `schema.json` (XSD convertido para JSON)
- `examples/` (PDFs de exemplo, não reprocessados)
- `assets/` (imagens extraídas do PDF)
- `fonts/` (opcional, fontes customizadas)
- `layout/skeleton.json` (estrutura detectada de layout)

O arquivo `template.zip` deve ser abrível sem re-executar pipeline. Estado de UI não é salvo (zoom, scroll, elemento selecionado).

**`docs/wireframes/wireframes-mid-fi.md`**: Home tem card "Abrir Projeto" (.json); toolbar tem botão "💾 Salvar Template".

---

## Frontend — Status de Implementação

### Componentes existentes

| Componente | Arquivo | Status |
|---|---|---|
| Composable projeto (v1) | `frontend/src/composables/useProject.ts` | Legado (v1.0, wizard) |
| Store de sessão | `frontend/src/stores/session.ts` | Implementado |
| Toolbar (botão Salvar) | `frontend/src/organisms/TopToolbar.vue` | Implementado |
| Tela Home | `frontend/src/pages/HomePage.vue` | Implementado |
| Tipos do projeto | `frontend/src/types/index.ts` | `SavedProjectV2` definido |

### O que funciona

**Salvar (TopToolbar.vue `onSave`):**
- Serializa `SavedProjectV2` (versão `'2.0'`) com:
  - `templateName` (de `sessionStore.template_name`)
  - `documentTree` (de `templateStore`)
  - `fieldMappings` (de `mappingStore.fields`, convertido para `FieldMappingEntry[]`)
  - `editorState` (de `editorStore`: tab ativo, zoom, elemento selecionado, toggles)
  - `layoutTypes` (de `layoutStore`)
  - `activeLayoutId`
  - `confidence` (de `confidenceStore.confidenceByLayout`)
  - `coverage` (de `coverageStore.coverageByLayout`)
- Download via `downloadJson()` → `downloadBlob()` → `<a download>` — **não usa File System Access API** (`showSaveFilePicker`); arquivo baixado como `{templateName}.projeto.json`
- Implementação rápida, sem modal de confirmação

**Abrir Projeto (HomePage.vue):**
- Card "📂 Abrir Projeto" com botão "Carregar arquivo"
- Input `<input type="file" accept=".json">` oculto
- Detecta versão `'2.0'` → chama `session.loadFromSavedProject(data)`
- Detecta versão legada `'1.0'` → marca `analysisCompleted = true`, navega para `/editor`
- Navega automaticamente para `/editor` após carga

**`session.loadFromSavedProject()` (session.ts):**
- Restaura `templateStore` (documentTree), `mappingStore` (fieldMappings), `layoutStore` (layoutTypes + activeLayoutId), `confidenceStore`, `coverageStore`, `editorStore` (toggles, tab ativo, zoom)
- Marca `analysisCompleted = true` para que guard de rota `/editor` passe

### O que falta / está incompleto

**Comparado com a spec `template_saving_strategy.md`:**

- **Formato JSON, não ZIP**: a spec define `template.zip` com múltiplos arquivos. O que foi implementado é um único arquivo `.projeto.json` sem assets, PDFs de exemplo, fontes ou `schema.json` separado.
- **Assets não incluídos**: imagens extraídas do PDF não são serializadas no save. Ao abrir o projeto, elementos de imagem perdem suas referências visuais.
- **PDFs de exemplo não salvos**: não há `examples/` — ao restaurar, a aba "PDF Referência" não terá os PDFs originais.
- **`schema.json` / XSD flat_paths**: `mappingStore.flatPaths` não está incluído no `SavedProjectV2` — ao restaurar, o BindingEditor dropdown pode ficar sem as opções de campo XSD.
- **`testDataStore` não serializado**: datasets de teste não são incluídos no save (não consta no `SavedProjectV2`). Ao abrir o projeto, a Área de Testes estará vazia.
- **`codeStore.fileContents` não serializado**: os arquivos editados no Monaco (HTML/CSS/JS customizados) não são salvos — ao restaurar, o Monaco exibe o scaffold padrão ou o HTML do `generationStore.templateDraft`, não o conteúdo editado manualmente.
- **Auto-save periódico**: não implementado.
- **`showSaveFilePicker` não usado**: o save usa apenas download via `<a>` (sem File System Access API), apesar de `useProject.ts` (v1) ter implementação com `showSaveFilePicker`. A v2 simplificou.
- **Job ID não persistido**: `sessionStore.jobId` não está em `SavedProjectV2` — impossível retomar análise de pipeline de um projeto salvo.
- **`useProject.ts` é legado**: o composable original `useProject.ts` serializa stores do paradigma v1 (wizard: session, mapping, layout, generation com campos como `monacoEdits`, `chartConfigs`). Não é usado pelo fluxo v3 do editor.

---

## Backend — Status de Implementação

O save/load é puramente frontend — nenhum endpoint de backend envolvido. O backend não persiste projetos.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Assets de imagem não salvos — elementos de imagem perdem referências ao restaurar | 🔴 Crítico | `TopToolbar.vue:onSave` — `SavedProjectV2` sem assets | `template_saving_strategy.md` seção 7 |
| 2 | `codeStore.fileContents` (HTML/CSS/JS editados no Monaco) não incluídos no save | 🔴 Crítico | `SavedProjectV2` sem campo `codeFiles` | FR10, FR24 |
| 3 | `testDataStore` (datasets de teste) não serializado no save | 🟡 Importante | `SavedProjectV2` sem campo `testData` | FR42, FR10 |
| 4 | XSD flat_paths (`mappingStore.flatPaths`) não salvo — BindingEditor perde dropdown de campos | 🟡 Importante | `SavedProjectV2` sem campo `xsdFlatPaths` | Story 28.1 |
| 5 | PDFs de exemplo não incluídos no save — aba PDF Referência fica vazia ao restaurar | 🟡 Importante | `SavedProjectV2` sem `pdfReferences` | `template_saving_strategy.md` seção 6 |
| 6 | Formato é `.json`, não `.zip` com estrutura completa como definido na spec | 🟡 Importante | Design de formato | `template_saving_strategy.md` seção 3 |
| 7 | `jobId` não salvo — impossível retomar análise de pipeline | 🟢 Menor | `SavedProjectV2` sem `jobId` | FR10 |
| 8 | Auto-save periódico ausente | 🟢 Menor | Não implementado | FR10 |
| 9 | `useProject.ts` (v1) é código legado não usado no fluxo v3 | 🟢 Menor | `frontend/src/composables/useProject.ts` | — |

---

## Backlog Gerado

1. **Adicionar `codeFiles` ao `SavedProjectV2`**: incluir `{ html, css, js }` de `codeStore.fileContents` na serialização do save e restaurar em `session.loadFromSavedProject`.
2. **Adicionar `testDatasets` ao `SavedProjectV2`**: serializar `testDataStore.datasets` e restaurar ao abrir o projeto.
3. **Adicionar `xsdFlatPaths` ao `SavedProjectV2`**: incluir `mappingStore.flatPaths` para restaurar o BindingEditor dropdown.
4. **Salvar referências de PDFs**: incluir nomes/metadados dos PDFs enviados (sem conteúdo binário) para exibir no painel PDF Referência após restauração.
5. **Avaliar migração para formato ZIP**: empacotar JSON + assets/imagens em ZIP via JSZip (já disponível no projeto) para suportar assets; ou definir estratégia de referências base64 para imagens pequenas.
6. **Implementar auto-save**: debounce de 5 minutos em `watch(templateStore.documentTree, () => saveToIndexedDB())` com indicador visual de "salvo" na toolbar.
7. **Deprecar `useProject.ts`**: remover ou documentar claramente como código legado do paradigma v1.

---

## Status Geral

🟡 **Parcial** — O fluxo básico de save/load funciona para o estado core do editor: árvore de estrutura, mapeamentos de campos, layout types, confiança, cobertura e estado da UI são salvos e restaurados corretamente. Porém faltam os assets de imagem e os arquivos editados no Monaco, o que torna o save incompleto para projetos com customizações visuais ou código editado manualmente.
