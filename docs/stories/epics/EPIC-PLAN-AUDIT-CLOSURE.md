# Plano de Epics — Fechamento da Auditoria

**Data:** 2026-04-07
**Autor:** @architect (Aria) — modo YOLO
**Base:** docs/audit/TRIAGEM-DECISOES.md (59 gaps validados)

---

## Princípios de Agrupamento

1. **Dependência técnica** — epics que desbloqueiam outros vêm primeiro
2. **Coerência funcional** — gaps do mesmo subsistema ficam juntos
3. **Impacto no output** — export/ZIP funcional é o objetivo final
4. **Incrementalidade** — cada epic entrega valor testável

---

## Avaliação I37 (Renomeação de Layout Types)

**Decisão @architect:** ✅ Incluir como item menor dentro do epic de Layout/Canvas.
**Razão:** Baixa complexidade (1 campo editável + persistência no store), alto valor de usabilidade quando há múltiplos layouts. Não justifica epic próprio — encaixa como story dentro do epic de Canvas/Layout.

---

## Epic 31 — Export ZIP Funcional (NFR7 Compliance)

**Prioridade:** 🔴 P0 — Sem isso, o produto não entrega output utilizável
**Dependências:** Nenhuma (pode iniciar imediatamente)

| Story | Gap(s) | Descrição |
|-------|--------|-----------|
| 31.1 | C1 | Incluir `css/style.css` no ZIP de export |
| 31.2 | C1 | Incluir pasta `assets/` no ZIP (com imagens extraídas) |
| 31.3 | C2 | Tornar ZIP autocontido — embalar KO, Chart.js, JsBarcode no ZIP (ou CDN com fallback) |
| 31.4 | C5 | Enviar `codeStore.fileContents` para `/api/generate` — edições Monaco prevalecem |
| 31.5 | C19 | Injetar JsBarcode CDN/lib no `index.html` gerado |
| 31.6 | C21 | Gerar `@font-face` para fontes do catálogo Bibliotecas e incluí-las no ZIP |
| 31.7 | C18 | Implementar funções de paginação runtime (`quebrarTabelaEntrePaginas`, `criarNovaPagina`) no `base.js` gerado |
| 31.8 | — | Teste E2E NFR7: gerar ZIP, descompactar, abrir `index.html` localmente, verificar renderização |

**Estimativa:** 8 stories, ~3 dias

---

## Epic 32 — Fidelidade Visual do Canvas (Stage 5 CSS↔HTML)

**Prioridade:** 🔴 P0 — Fidelidade visual é o core do produto
**Dependências:** Nenhuma (paralelo ao 31)

| Story | Gap(s) | Descrição |
|-------|--------|-----------|
| 32.1 | C3 | Aplicar classes `.c-{hex}`, `.border-N`, `.bg-N` nos elementos HTML do 5.1 |
| 32.2 | C4 | Incluir `is_bold`/`is_italic` nas classes de fonte CSS (5.2) |
| ~~32.3~~ | ~~I7~~ | ~~REMOVIDA — já implementada na Story 29.4~~ |
| ~~32.4~~ | ~~C6~~ | ~~REMOVIDA — já implementada no stage2 existente~~ |
| 32.5 | C20 | Implementar SVG inline (FR32) — detecção no stage3 + embedding no stage5 |
| 32.6 | I31 | Adicionar MSI ao `_FORMAT_MAP` do backend |

**Estimativa:** 4 stories, ~1.5 dias (2 removidas: 32.3, 32.4)

---

## Epic 33 — Inspector Loop Completo

**Prioridade:** 🔴 P1 — Inspector é a interface principal de edição
**Dependências:** Epic 32 (data-node-id nos elementos)

| Story | Gap(s) | Descrição |
|-------|--------|-----------|
| 33.1 | C7 | Corrigir roteamento Header/Footer/Flow → SectionInspector (LEVEL_MAP) |
| 33.2 | C8 | Tornar Posição X/Y e tamanho W/H editáveis no ElementInspector |
| 33.3 | I6 | `updateNodeProperties()` (bulk) disparar patch + mutationVersion |
| 33.4 | I8 | Implementar `patchNodeStyle()` — font_size, font_weight, color |
| 33.5 | C23 | Garantir re-render Canvas após mudança de visibility |
| 33.6 | I16 | Tipo de campo selecionável (dropdown em vez de badge read-only) |
| 33.7 | I29 | Keep-together editável no TableInspector |
| 33.8 | I30 | Seleção de header row (qual linha = thead) no TableInspector |
| ~~33.9~~ | ~~I33~~ | ~~REMOVIDA — já implementada em ElementInspector.vue:43-49~~ |
| 33.10 | I34 | LayerPanel: toggle visibilidade + lock/unlock por camada |

**Estimativa:** 9 stories, ~3 dias (1 removida: 33.9)

---

## Epic 34 — Field Mapping & Coverage Accuracy

**Prioridade:** 🔴 P1 — Precisão de mapeamento é core
**Dependências:** Nenhuma

| Story | Gap(s) | Descrição |
|-------|--------|-----------|
| 34.1 | C10 | Propagar score de confiança real do stage4 ao frontend (remover hardcode 'medium') |
| 34.2 | C11 | Corrigir `charts.mapped` hardcoded 0 + incluir gráficos na fórmula ponderada |
| 34.3 | I20 | Cobertura atualiza em tempo real ao mapear/desmapear campo |
| ~~34.4~~ | ~~I17~~ | ~~REMOVIDA — já implementada na Story 28.4 (commit 863792c)~~ |
| 34.5 | I18 | Modo de agrupamento por tipo no FieldNavigator (Campos/Tabelas/Gráficos) |
| 34.6 | I19 | Busca/filtro no FieldNavigator |
| 34.7 | I15 | Auto-bind semântico (match nome nó → campo XSD por similaridade) |
| 34.8 | I35 | Integrar ConsolePanel ↔ coverageStore (warnings de cobertura) |

**Estimativa:** 7 stories, ~2.5 dias (1 removida: 34.4)

---

## Epic 35 — Sync View & Diff Mode Completo

**Prioridade:** 🟡 P2 — Features de comparação/validação
**Dependências:** Epic 32 (fidelidade visual), Epic 34 (coverage accuracy)

| Story | Gap(s) | Descrição |
|-------|--------|-----------|
| 35.1 | C15, C16 | Implementar âncoras de layout no SyncView + seleção sincronizada Canvas↔PDF |
| 35.2 | I25 | SyncView usa página representativa do Layout Type ativo |
| 35.3 | C13 | Implementar tipo `moved` (🟨) no Diff — comparar posições entre docs |
| 35.4 | C14 | Painel de inferências no DiffViewer com Confirmar/Rejeitar |
| 35.5 | I24 | Highlights do Diff usam coordenadas PDF (não Canvas) |
| 35.6 | C12 | Corrigir Matriz Variação para Campos × PDFs (não Layout Types × PDFs) |
| ~~35.7~~ | ~~I21~~ | ~~REMOVIDA — já implementada em EditorLayout.vue:41~~ |
| 35.8 | I22 | Agrupamento de campos adjacentes com mesmo padrão em seção opcional |
| 35.9 | I23 | Detecção de `dynamic_table` (tabelas com linhas variáveis) |

**Estimativa:** 8 stories, ~3.5 dias (1 removida: 35.7)

---

## Epic 36 — Code Editor & Save/Load Completo

**Prioridade:** 🟡 P2 — Persistência e edição avançada
**Dependências:** Epic 31 (export funcional — save precisa incluir mesmos dados)

| Story | Gap(s) | Descrição |
|-------|--------|-----------|
| 36.1 | C17 | Remover guard que suprime structure→code quando templateDraft.html existe |
| 36.2 | I26 | Clicar no Monaco seleciona nó na Árvore (mapeamento linha→nodeId) |
| 36.3 | I27 | Save inclui assets, code editado, testData, xsdFlatPaths |
| 36.4 | I28 | Migrar formato save de .json para .zip (JSZip) com assets |
| 36.5 | I40 | Dados do upload inicial (FR2a) populam testDataStore automaticamente |

**Estimativa:** 5 stories, ~2 dias

---

## Epic 37 — Canvas UX Polish (Snap, Zoom, Undo, Interaction)

**Prioridade:** 🟡 P2 — Polimento de UX do editor
**Dependências:** Epic 33 (inspector loop — para que patches funcionem)

| Story | Gap(s) | Descrição |
|-------|--------|-----------|
| 37.1 | I9 | Implementar Redo (Ctrl+Y) — redoStack no templateStore |
| 37.2 | I10 | Snap habilitado por padrão (`true`) |
| 37.3 | I11 | Integrar `columnPositions` do backend ao Canvas + calcSnapLines |
| 37.4 | I12 | Snap lines visuais durante resize |
| 37.5 | I13 | Expor ferramentas de alinhamento na UI (botões quando multi-seleção) |
| 37.6 | I38 | Harmonizar ZOOM_MAX + implementar zoom por mousewheel |
| 37.7 | I39 | Toggle "Mostrar Guias" na toolbar |
| 37.8 | I37 | Renomeação de Layout Types pelo operador (campo editável no LayoutSelector) |

**Estimativa:** 8 stories, ~2 dias

---

## Epic 38 — Features Avançadas (Tematização, Bibliotecas, Vision AI)

**Prioridade:** 🟡 P3 — Features de longo prazo
**Dependências:** Epics 31-34 (core funcional)

| Story | Gap(s) | Descrição |
|-------|--------|-----------|
| 38.1 | C9 | Avaliar Vision AI + pgvector para matching semântico (custo/benefício) |
| 38.2 | I32 | Tematização condicional — UI + geração de funções no base.js (FR30) |
| 38.3 | C22 | Biblioteca de snippets/componentes estruturais (save/insert) |
| ~~38.4~~ | ~~I36~~ | ~~REMOVIDA — funcionalidade coberta por MultiDocAnalyzer + DiffViewer + Inspector~~ |
| 38.5 | I1 | FR2b: Geração sintética de dados a partir do XSD |
| 38.6 | I2 | Persistir `template_name` no job e propagar ao pipeline |
| 38.7 | I14 | Avaliar remoção do nível `page` intermediário na árvore |

**Estimativa:** 7 stories, ~4 dias

---

## Ordem de Execução Recomendada

```
Fase 1 (P0 — paralelo):
  Epic 31 — Export ZIP ─────────┐
  Epic 32 — Fidelidade Visual ──┤
                                ▼
Fase 2 (P1 — paralelo):
  Epic 33 — Inspector Loop ─────┐
  Epic 34 — Field Mapping ──────┤
                                ▼
Fase 3 (P2 — paralelo):
  Epic 35 — Sync/Diff ──────────┐
  Epic 36 — Code/Save ──────────┤
  Epic 37 — Canvas UX ──────────┤
                                ▼
Fase 4 (P3):
  Epic 38 — Features Avançadas
```

**Total:** 8 epics, **54 stories** (~20 dias estimados) — 7 stories removidas por validação QA (ver EPIC-VALIDATION-REPORT.md)

---

## Resumo

| Epic | Nome | Stories | Prioridade | Fase |
|------|------|---------|-----------|------|
| 31 | Export ZIP Funcional | 8 | P0 | 1 |
| 32 | Fidelidade Visual Canvas | **4** (-2) | P0 | 1 |
| 33 | Inspector Loop Completo | **9** (-1) | P1 | 2 |
| 34 | Field Mapping & Coverage | **7** (-1) | P1 | 2 |
| 35 | Sync View & Diff Mode | **8** (-1) | P2 | 3 |
| 36 | Code Editor & Save/Load | 5 | P2 | 3 |
| 37 | Canvas UX Polish | 8 | P2 | 3 |
| 38 | Features Avançadas | **6** (-1) | P3 | 4 |
| **Total** | | **53** (-8) | | |

> **Validação QA (2026-04-07):** 5 stories removidas (já implementadas: 32.3, 32.4, 33.9, 34.4, 35.7), 6 stories reframed (escopo reduzido: 31.1, 31.4, 31.7, 32.1, 37.5, 37.7), 14 ACs ajustados. Ver `EPIC-VALIDATION-REPORT.md` para detalhes.
