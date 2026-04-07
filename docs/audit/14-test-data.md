# Auditoria: Área de Testes — Data Playground + Test Report

**Data:** 2026-04-07
**Status Geral:** 🟢 Implementado

---

## O que foi planejado

**FR42** (PRD v3.0) e seção 8 de `docs/ideias/ux/template_editor_main_screen_spec.md`:

**Aba "Dados de Teste":**
- Lista de datasets (um ativo por vez); aceita upload de XML ou JSON; validação automática contra XSD
- Indicadores de status: ✓ validado, ⚠ aviso (campos opcionais ausentes), ✕ inválido
- Gerador de dados sintéticos a partir do XSD: `synthetic_small` (1 linha), `synthetic_medium` (10 linhas), `synthetic_large` (100+ linhas)
- Resumo do dataset selecionado: campos, loops, tamanho, status
- "Editar Dataset..." abre modal com Monaco Editor
- "Aplicar no Canvas" renderiza o template com o dataset ativo em tempo real (postMessage ao iframe)
- "Testar Todos" executa todos os datasets em sequência; resultado na aba Relatório
- Limite MVP: máximo 5 datasets por template
- Datasets incluídos opcionalmente no Export (pasta `test_data/`)

**FR2a** (PRD v3.0): upload opcional de XML/JSON com dados reais — popula automaticamente a Área de Testes.

**FR2b** (PRD v3.0): geração sintética a partir do XSD como `exemplo.js`.

**Aba "Relatório":**
- Tabela resumo: dataset × páginas × cobertura × status
- Matriz de cobertura por elemento: quais elementos aparecem em cada dataset

---

## Frontend — Status de Implementação

### Componentes existentes

| Componente | Arquivo | Status |
|---|---|---|
| Painel Dados de Teste | `frontend/src/organisms/TestDataPanel.vue` | Implementado (22KB) |
| Painel Relatório | `frontend/src/organisms/TestReportPanel.vue` | Implementado (12.3KB) |
| Store Dados de Teste | `frontend/src/stores/testDataStore.ts` | Implementado |
| Store Relatório | `frontend/src/stores/testReportStore.ts` | Implementado |
| Gerador Sintético | `frontend/src/utils/syntheticGenerator.ts` | Implementado |

### O que funciona

**TestDataPanel.vue:**
- Lista de datasets gerenciada por `DatasetList` molecule; seleção, exclusão e upload
- Botão "⚡ Gerar Sintético" com dropdown para Small / Médio / Grande — chama `generateSyntheticData()` de `syntheticGenerator.ts`
- Upload de arquivos XML (`parseXmlToJson` via DOMParser) e JSON com FileReader
- Auto-validação após upload e após geração sintética via `store.validateDataset()` usando campos do `mappingStore.fieldNavItems` como definições XSD
- Status badges: ✓ Validado / ⚠ Aviso / ✕ Inválido / não validado
- Stats grid: Campos, Loops, Tamanho, Status
- Exibição de erros e warnings de validação
- "Aplicar no Canvas" — `store.applyDatasetToCanvas(iframes)` envia `postMessage({ type: 'apply-test-data', data: fields })` para iframes do Canvas
- "Editar Dataset..." — modal com textarea (fallback: Monaco component definido como `null` para compatibilidade de testes)
- "Salvar e Revalidar" no modal salva o JSON editado e re-valida
- Limite de 5 datasets por template (`MAX_DATASETS = 5`)

**testDataStore.ts:**
- `validateDatasetAgainstXsd()` — validação completa com: campos obrigatórios ausentes (errors), campos opcionais ausentes (warnings), verificação de tipo (integer, decimal, boolean, date, string)
- `parseXmlToJson()` — parser XML via DOMParser com agrupamento de elementos repetidos como arrays
- `applyDatasetToCanvas()` — postMessage para iframes

**TestReportPanel.vue:**
- Botão "▶ Testar Todos" e "■ Cancelar"
- Iteração sobre todos os datasets; timeout de 30s por dataset
- Tabela resumo (Dataset, Páginas, Cobertura, Status)
- Matriz de cobertura por elemento × dataset
- `simulateTestRun()` — calcula cobertura via correspondência de chaves do dataset com IDs de elementos do template; estimativa de páginas baseada no maior array (maxArrayLen / 30)

### O que falta / está incompleto

- **Monaco Editor no modal** de "Editar Dataset": `MonacoEditorInner = null` — usa `<textarea>` como fallback. A spec (FR42) menciona "abre modal com Monaco Editor" mas o Monaco não está sendo carregado assincronamente no componente (apenas fallback textarea).
- **Preview do template renderizado** com os dados no painel inferior: o "Aplicar no Canvas" envia postMessage ao iframe do Canvas, mas não há visualização embedded de preview dentro do painel inferior. O usuário precisa olhar o painel central (Canvas) para ver o resultado.
- **Paginação do preview** (múltiplas páginas): o relatório estima pageCount via array size / 30, mas não há renderização real de paginação — é simulação.
- **`simulateTestRun` é uma simulação**: a cobertura e pageCount são calculadas heuristicamente (match de chaves), não via renderização real do canvas com os dados. O resultado pode ser impreciso.
- **Troca rápida entre múltiplos conjuntos**: funciona via lista de datasets, mas sem atalho de teclado ou "ciclo de datasets".
- **Dados do FR2a** (upload inicial na tela de Upload): o `dataFile` da sessão não popula automaticamente a Área de Testes ao entrar no editor. O usuário precisa fazer um segundo upload no painel.

---

## Backend — Status de Implementação

O backend tem endpoint `/api/preview` referenciado nas fontes de planejamento, mas o `TestDataPanel.vue` não chama esse endpoint — usa postMessage direto ao iframe do Canvas. A renderização do preview é feita localmente pelo canvas HTML. O `/api/preview` não aparece no código frontend auditado.

`backend/routers/preview.py` existe como fonte de código mas não é usado pelo fluxo atual da Área de Testes.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Monaco Editor no modal de edição de dataset não carregado — usa `<textarea>` como fallback | 🟡 Importante | `TestDataPanel.vue` linha 200 (`MonacoEditorInner = null`) | FR42 "Editar Dataset... abre modal com Monaco Editor" |
| 2 | `simulateTestRun` é heurístico — cobertura e pageCount não refletem renderização real | 🟡 Importante | `TestReportPanel.vue:simulateTestRun` | FR42 aba Relatório |
| 3 | Dados do upload inicial (FR2a) não populam automaticamente a Área de Testes ao entrar no editor | 🟡 Importante | `session.ts:loadFromPipelineResult` — não inclui testDataStore | FR2a |
| 4 | Preview embedded do template com dados não existe no painel inferior | 🟢 Menor | `TestDataPanel.vue` — "Aplicar no Canvas" delega para painel central | FR42 |
| 5 | Troca rápida de datasets sem atalhos de teclado | 🟢 Menor | `TestDataPanel.vue` | FR42 UX |

---

## Backlog Gerado

1. **Carregar Monaco assincronamente** no modal "Editar Dataset" usando `import('monaco-editor')` no onMounted, similar ao padrão de `MonacoTabsInner.vue`, com fallback `<textarea>` enquanto carrega.
2. **Implementar renderização real do `simulateTestRun`**: após aplicar o dataset ao canvas via postMessage, aguardar sinal de renderização (evento customizado do iframe ou polling) e contar as páginas/elementos cobertos efetivamente.
3. **Popular testDataStore com dataFile do upload inicial**: em `session.ts:loadFromPipelineResult`, se `result.example_data` existir, chamar `testDataStore.addDataset` automaticamente com o arquivo de dados reais.
4. **Usar `/api/preview`** para preview server-side com dados reais (FR42) quando o canvas local não for suficiente para templates complexos com paginação.
5. **Documentar no painel** que "Aplicar no Canvas" atualiza o painel central — adicionar tooltip ou seta indicativa para o Canvas.

---

## Status Geral

🟢 **Implementado** — Os dois painéis (Dados de Teste e Relatório) estão completos com geração sintética (3 tamanhos), upload XML/JSON, validação contra XSD, stats grid, modal de edição, "Aplicar no Canvas" e matriz de cobertura. Os gaps são menores: o Monaco no modal usa fallback textarea, o simulateTestRun é heurístico e os dados do upload inicial não chegam automaticamente ao painel.
