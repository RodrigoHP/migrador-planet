# Auditoria: Bibliotecas — Snippets e Componentes Reutilizáveis

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**Modal Global de Bibliotecas** — Acessível da Home e do Editor. Categorias de componentes reutilizáveis (headers, tabelas, campos, gráficos). Salvar elemento atual como componente. Inserir componente da biblioteca na árvore. IndexedDB para persistência local. Busca/filtro. Import/Export de biblioteca.

**FR27a** — Gestão do catálogo de Bibliotecas com três abas (Fontes, CSS, JS), lista de arquivos com nome/tamanho/remover, botão adicionar com filtro por extensão. Acessível apenas pela Home.

Fontes: `docs/wireframes/wireframes-mid-fi.md` "Modal Global — Bibliotecas"; `docs/prd-v3.md` FR27a.

---

## Frontend — Status de Implementação

### BibliotecasModal.vue (`frontend/src/organisms/BibliotecasModal.vue`)

**Implementado:**
- Modal com overlay, botão fechar, acessibilidade (`role="dialog"`, `aria-modal`)
- 3 abas: Fontes, CSS, JS (alinhado com FR27a)
- Contador de arquivos por aba
- `BibliotecaFileList` — listagem de arquivos (nome, tamanho, botão remover)
- Upload via `<input type="file">` com `currentAccept` filtrado por aba (`.ttf,.otf,.woff,.woff2` para Fontes; `.css` para CSS; `.js` para JS)
- Botão "+ Adicionar {categoria}" no footer
- Confirmação antes de remover arquivo referenciado no template ativo (`isFileReferenced`)
- Loading state e exibição de erros de upload

### useBibliotecas.ts (`frontend/src/composables/useBibliotecas.ts`)

**Implementado:**
- Persistência via IndexedDB (`idb`) — `STORE_NAME = 'biblioteca-files'`
- `loadFiles()`, `addFile()`, `removeFile()`, `getByCategory()`
- `isFileReferenced(name, templateContent)` — verifica se arquivo é citado no template
- `ALLOWED_EXTENSIONS` por categoria

**O que falta:**
- **Bibliotecas de snippets/componentes estruturais** — A spec dos wireframes menciona categorias como "headers, tabelas, campos, gráficos" como *componentes reutilizáveis da estrutura do template*, não apenas arquivos de fonte/CSS/JS. A implementação atual é exclusivamente um **gerenciador de arquivos estáticos** (assets de Bibliotecas), não um catálogo de snippets HTML/estrutura.
- **Salvar elemento atual como componente** — Não existe ação de "Salvar como snippet" no editor nem no modal.
- **Inserir componente na árvore** — O modal não tem mecanismo de drag/insert para adicionar snippets estruturais ao template.
- **Busca/filtro na biblioteca** — Não há campo de busca nem filtro por nome dentro das abas.
- **Import/Export de biblioteca** — Não há botões de exportar ou importar o catálogo completo.
- **Acesso pela Home** — O wireframe mostra botão "📚 Bibliotecas" na Home. Precisa verificar se está implementado no `HomeView.vue`.

---

## Backend — Status de Implementação

As Bibliotecas são gerenciadas inteiramente no frontend via IndexedDB. Não há endpoint de backend para Bibliotecas (corretamente, conforme spec FR27a). A integração com backend se dá indiretamente via `useFontCascade` (que consulta o catálogo para resolver fontes).

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Biblioteca de snippets/componentes estruturais ausente — apenas gerenciador de arquivos estáticos | 🔴 Crítico | Frontend | wireframes-mid-fi.md "Modal Global — Bibliotecas" |
| 2 | Sem ação "Salvar elemento como componente reutilizável" no editor | 🟡 Importante | Frontend | wireframes-mid-fi.md |
| 3 | Sem mecanismo de inserção de componente da biblioteca na árvore do template | 🟡 Importante | Frontend | wireframes-mid-fi.md |
| 4 | Busca/filtro dentro das abas da biblioteca ausente | 🟢 Menor | Frontend | wireframes-mid-fi.md |
| 5 | Import/Export de biblioteca não implementado | 🟢 Menor | Frontend | wireframes-mid-fi.md |
| 6 | Botão Bibliotecas na Home — presença não confirmada nesta auditoria | 🟢 Menor | Frontend | wireframes-mid-fi.md Tela 0 |

---

## Backlog Gerado

1. **Biblioteca de snippets estruturais** — Extender `useBibliotecas` com uma quarta categoria `snippets` que armazena `TreeNode[]` serializado (componentes de template: header padrão, tabela de transações, rodapé com paginação). Exibir no modal com preview HTML.
2. **"Salvar como componente"** — Adicionar item de menu contextual ou botão no Inspetor "💾 Salvar como snippet" que serializa o nó selecionado (e seus filhos) e persiste em IndexedDB categoria `snippets`.
3. **Inserir snippet na árvore** — No modal de Bibliotecas, botão "Inserir" em cada snippet que chama `templateStore.addNode()` abaixo do nó selecionado.
4. **Campo de busca/filtro na biblioteca** — Input de texto no topo do content area que filtra `getByCategory()` por nome de arquivo.
5. **Import/Export do catálogo** — Botões no footer do modal para exportar todos os arquivos IndexedDB como ZIP e importar de ZIP.
6. **Verificar botão Bibliotecas na Home** — Confirmar presença em `HomeView.vue` e garantir que o mesmo modal `BibliotecasModal.vue` seja reutilizado.

---

## Status Geral

🟡 Parcial — A gestão de arquivos estáticos (fontes, CSS, JS) via IndexedDB está implementada e funcional, atendendo FR27a. Porém, o propósito principal descrito nos wireframes — um catálogo de componentes estruturais reutilizáveis (snippets de template) com save/insert — não foi implementado. O modal atual é um asset manager, não uma biblioteca de componentes.
