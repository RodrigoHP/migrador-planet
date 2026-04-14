# Auditoria: Editor de Código (Monaco) — Sincronização Bidirecional

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR24** (PRD v3.0) e seções 12–13 de `docs/ideias/ux/editor_architecture_spec.md`:

- Monaco Editor multi-arquivo com abas: `index.html`, `style.css`, `base.js`, `exemplo.js`
- Explorador de Arquivos no painel esquerdo (aba **Arquivos**, aparece automaticamente ao entrar em Code)
- Syntax highlighting HTML/CSS/JS, auto-indentação, numeração de linhas, busca
- Avisos visuais em seções estruturais (`⚠ SEÇÃO ESTRUTURAL`)
- Detecção de erros inline (bindings inválidos, CSS com erro, HTML inválido)
- **Sincronização bidirecional** (Story 29.3 / GAP 2 — `gap-analysis-frontend-v3.md`):
  - Código → Estrutura: editar HTML no Monaco atualiza `templateStore` (parser HTML → TreeNode)
  - Estrutura → Código: editar na árvore/inspector regenera o código no Monaco
- Seleção bidirecional: clicar numa linha seleciona o nó na Árvore; selecionar na Árvore rola o código
- Validação ao salvar: rejeita edição com HTML/bindings inválidos
- MVP: criar/excluir/renomear arquivos bloqueados intencionalmente

**Story 29.3** (epic-29-editor-loop-closure.md): implementar `syncHtmlToTree()` com parser DOMParser que sincronize text, data-field, posição/tamanho e detecte adição/remoção de nós.

**GAP 2** (gap-analysis-frontend-v3.md): faltava qualquer `parseHTML()` / `htmlToTree()` — `codeStore` salvava no `setFileContent()` mas não disparava atualização no `templateStore`.

**Backlog 30.3** (backlog-epic29-scope-out.md): parser completo HTML→árvore com reconstrução de nós adicionados/removidos.

---

## Frontend — Status de Implementação

### Componentes existentes

| Componente | Arquivo | Status |
|---|---|---|
| Monaco Editor (host) | `frontend/src/organisms/MonacoTabsInner.vue` | Implementado |
| File Explorer | `frontend/src/organisms/FileExplorer.vue` | Implementado |
| Code Store | `frontend/src/stores/codeStore.ts` | Implementado |
| Wrapper pai | `frontend/src/organisms/MonacoTabs.vue` | Existente |

### O que funciona

- Monaco carregado via `import('monaco-editor')` com `automaticLayout: true`
- Abas das 4 arquivos: `index.html`, `style.css`, `base.js`, `exemplo.js` — troca correta de arquivo com `setModelLanguage` + `setValue`
- `exemplo.js` marcado como read-only (badge `RO` visível, `file.readOnly` impede escrita)
- FileExplorer exibe estrutura `Template / css/ / js/ / assets/` com navegação funcional; footer exibe "Criar/excluir/renomear: bloqueado (MVP)" (decisão intencional per GAP 10)
- Debounce 500ms antes de aplicar edição ao store (`applyMonacoEdit`)
- CSS validation inline com `applyCssMarkers` — badge de erro vermelho na aba CSS
- CSS autocomplete provider registrado (`registerCssCompletionProvider`)
- Decorações `⚠ SEÇÃO ESTRUTURAL` em linhas com padrão `/SEÇÃO ESTRUTURAL/i`
- Watch `codeStore.fileContents[activeFile]` → Monaco update (sincronização Visual→Code via store externo)
- Watch `editorStore.selectedElementId` → `revealLineInCenter` (seleção na Árvore rola o código)
- Guard anti-loop `suppressWatch` (booleano) no componente e `_isSyncing` no store
- Banner "Alteração externa detectada" quando templateDraft muda durante edição (toast)
- `syncHtmlToTree()` implementado em `codeStore.ts` (Story 29.3 + Story 30.3):
  - Fase 1: parsing DOMParser, build `htmlMap` por `data-node-id`
  - Fase 2: safety guard — scaffold sem `data-node-id` não dispara add/remove
  - Fase 3: sync text, `data-field`, posição (left/top), tamanho (width/height) de nós existentes
  - Fase 4: detecta nós removidos do HTML → `templateStore.removeNode`
  - Fase 5: detecta nós adicionados no HTML → `templateStore.addNodeFromSync`
- Guard `_isSyncing` cobre o loop code→tree→code

### O que falta / está incompleto

- **Sincronização structure → código parcial**: `watch(templateStore.documentTree)` em `codeStore.ts` regenera HTML apenas quando `generationStore.templateDraft?.html` está vazio. Com template do backend carregado, `if (generationStore.templateDraft?.html) return` suprime a regeneração → editar a árvore não atualiza o código mostrado no Monaco enquanto existir HTML do backend.
- **`_parseHtmlIntoStore`** é no-op explícito: `"No-op para MVP: templateStore remains source of truth; full parse is future work"` — a função chama apenas validação de string não-vazia.
- **Detecção de erros inline de bindings** (FR24): `usePreExportValidation` valida bindings, mas o Monaco não exibe marcadores inline de bindings inválidos em tempo real durante a edição.
- **Validação ao salvar HTML inválido**: não há rejeição de edição; edição inválida é aceita no store e validação ocorre apenas no pré-export.
- Seleção bidirecional completa: árvore → Monaco funciona (scroll); Monaco → árvore (clicar linha seleciona nó) **não implementado**.

---

## Backend — Status de Implementação

O Monaco Editor opera puramente no frontend. O backend não tem endpoint específico para sincronização de código. A integração com o backend ocorre via:

- `generationStore.loadTemplateDraft()` — recebe HTML/CSS/JS do pipeline → popula `codeStore.fileContents`
- `/api/generate` (chamado pelo export) — regenera artifacts a partir do `templateStore`

Não há endpoint de "parse HTML → structure" no backend — a decisão arquitetural (Story 29.1) escolheu Opção B (geração frontend com DOMParser) para o parser Code→Structure.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Editar estrutura/árvore não regenera código no Monaco quando `templateDraft.html` existe | 🔴 Crítico | Frontend `codeStore.ts` watch guard linha ~399 | GAP 2 parcial, Story 29.3 |
| 2 | `_parseHtmlIntoStore` é no-op — mudanças de comentários/estrutura não chegam ao templateStore | 🟡 Importante | `codeStore.ts:_parseHtmlIntoStore` | Story 29.3 |
| 3 | Sem marcadores inline de bindings inválidos em tempo real no Monaco | 🟡 Importante | `MonacoTabsInner.vue` | FR24 |
| 4 | Clicar numa linha do Monaco não seleciona o nó na Árvore de Estrutura | 🟡 Importante | `MonacoTabsInner.vue` — sem mapeamento linha→nodeId | FR24 seleção bidirecional |
| 5 | Edição com HTML inválido não é rejeitada — validação só no export | 🟢 Menor | `codeStore.ts:applyMonacoEdit` | FR24, seção 14 editor_architecture_spec |
| 6 | FileExplorer CRUD (criar/excluir/renomear) bloqueado | 🟢 Menor | `FileExplorer.vue` footer | Decisão MVP intencional — GAP 10 |

---

## Backlog Gerado

1. **Remover guard `if (generationStore.templateDraft?.html) return`** em `codeStore.ts` watch do `templateStore.documentTree`, substituindo-o por lógica de merge seletivo que preserva partes não-estruturais do HTML do backend mas reflete mudanças da árvore.
2. **Implementar marcadores Monaco inline para bindings inválidos**: reutilizar lógica de `extractDataBindValues` / `extractBindingFields` de `usePreExportValidation.ts` para gerar `monacoApi.editor.setModelMarkers` em tempo real no arquivo HTML.
3. **Implementar seleção Monaco → Árvore**: adicionar handler `onDidChangeCursorPosition` em `MonacoTabsInner.vue` que extrai o `data-node-id` mais próximo da linha atual e chama `editorStore.setSelectedElement`.
4. **Completar `_parseHtmlIntoStore`**: implementar extração de nomes de seções dos comentários estruturais para atualizar nomes de nós no `templateStore`.
5. **Validação ao editar**: adicionar verificação básica de HTML bem-formado (DOMParser) antes de aplicar edição ao store, exibindo decoração de erro sem bloquear.
6. **Desbloquear FileExplorer CRUD** (post-MVP): implementar criação, renomeação e exclusão de arquivos de template no FileExplorer.

---

## Status Geral

🟡 **Parcial** — O Monaco Editor está integrado e funcional com abas, syntax highlighting, CSS validation, avisos estruturais e guard anti-loop. A sincronização code→structure (Story 29.3) foi implementada via `syncHtmlToTree()` com DOMParser cobrindo text, data-field, posição/tamanho, adição e remoção de nós. No entanto, a sincronização structure→code está suprimida enquanto há HTML do backend, e faltam marcadores inline de bindings em tempo real e seleção Monaco→Árvore.
