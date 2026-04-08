# Epic 36 — Code Editor & Save/Load Completo

**Prioridade:** P2
**Fase:** 3
**Estimativa:** 5 stories
**Dependências:** Epic 31 (export funcional — save precisa incluir mesmos dados)
**Objetivo:** Sincronização bidirecional completa entre Monaco/Árvore/Canvas, e save/load preserva todo o estado do projeto incluindo código editado e assets.

---

## Contexto

A sincronização structure→code está suprimida quando existe templateDraft.html do backend. Monaco→Árvore (clicar linha → selecionar nó) não implementado. Save não inclui código editado, assets, testData nem xsdFlatPaths. Formato é .json sem assets (spec: .zip).

---

## Stories

### 36.1 — Sincronização structure→code quando templateDraft.html existe
**Gap:** C17
**Escopo:** Frontend (`codeStore.ts`)
**AC:**
- [ ] Remover guard `if (generationStore.templateDraft?.html) return` no watch do documentTree
- [ ] Implementar merge seletivo: mudanças na árvore atualizam HTML do backend (patch por data-node-id)
- [ ] Guard `_isSyncing` previne loop infinito
- [ ] Teste: editar nome de nó na árvore → HTML no Monaco atualiza → Canvas re-renderiza

### 36.2 — Clicar no Monaco seleciona nó na Árvore
**Gap:** I26
**Escopo:** Frontend (`MonacoTabsInner.vue`)
**AC:**
- [ ] Handler `onDidChangeCursorPosition` detecta linha atual
- [ ] Extrai `data-node-id` mais próximo da linha (busca para cima no DOM parseado)
- [ ] Chama `editorStore.selectElement(nodeId)` + `inspectorStore.selectNode(node)`
- [ ] Árvore destaca nó correspondente e Inspector abre
- [ ] Funciona apenas no arquivo `index.html` (não no CSS/JS)

### 36.3 — Save inclui código editado, assets, testData, xsdFlatPaths
**Gap:** I27
**Escopo:** Frontend (`TopToolbar.vue`, `session.ts`)
**AC:**
- [ ] `SavedProjectV2` expandido com campos: `codeFiles`, `testDatasets`, `xsdFlatPaths`, `assetReferences`
- [ ] `codeFiles: { html, css, js }` de `codeStore.fileContents`
- [ ] `testDatasets` de `testDataStore.datasets`
- [ ] `xsdFlatPaths` de `mappingStore.flatPaths`
- [ ] `assetReferences` com nomes/metadados dos assets (sem binários)
- [ ] `session.loadFromSavedProject()` restaura todos os novos campos
- [ ] Teste: salvar → reabrir → Monaco mostra código editado, FieldNavigator tem dropdown XSD, testDataStore tem datasets

### 36.4 — Formato save migra para .zip com assets
**Gap:** I28
**Escopo:** Frontend (`TopToolbar.vue`)
**AC:**
- [ ] Save usa JSZip para criar `{templateName}.projeto.zip`
- [ ] ZIP contém: `project.json` (estado serializado) + `assets/` (imagens base64 ou blobs)
- [ ] Abrir projeto aceita tanto .json (legado v2.0) quanto .zip (v3.0)
- [ ] Ao abrir .zip, assets restaurados no AssetGallery
- [ ] Tamanho do ZIP razoável (< 10MB para projeto típico)

### 36.5 — Dados do upload inicial populam testDataStore
**Gap:** I40
**Escopo:** Frontend (`session.ts`)
**AC:**
- [ ] Em `loadFromPipelineResult()`, se `result.example_data` ou `sessionStore.dataFile` existir, chama `testDataStore.addDataset()` automaticamente
- [ ] Dataset adicionado com nome "Upload inicial" e status "não validado"
- [ ] Operador não precisa re-importar dados na aba Dados de Teste
- [ ] Se nenhum dado no upload, testDataStore permanece vazio (sem erro)
