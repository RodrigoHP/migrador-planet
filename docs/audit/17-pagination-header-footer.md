# Auditoria: Paginação + Header/Footer multi-página

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR12** (`docs/prd-v3.md`, linhas 190–194): Duas camadas de paginação — Camada 1 (Layout Engine no editor, tempo de edição) calcula quebras com `remainingSpace = bodyHeight - headerHeight - footerHeight`; tabelas quebram por linha com `<thead>` replicado. Camada 2 (template gerado, runtime) inclui funções `quebrarTabelaEntrePaginas()` / `criarNovaPagina()` no `base.js`. O operador configura parâmetros (altura máxima, cabeçalho repetido, mínimo de linhas) no Inspetor de Componente nível 3 — Tabela.

**FR13** (`docs/prd-v3.md`): Detecção automática de elementos repetidos entre páginas como candidatos a header/footer. Header e Footer são seções estruturais na Árvore com propriedade "Repetir em cada página" no Inspetor de Seção.

**FR22** (`docs/prd-v3.md`): Configuração de tamanho de página (A4, Carta, Custom), orientação, margens; alturas de Header e Footer reservam espaço fixo; Área de Conteúdo calculada automaticamente.

**`canvas_pagination_spec.md`**: Canvas renderiza múltiplas páginas empilhadas verticalmente; cada página tem `<div class="page">` com header/flow/footer; paginação dinâmica baseada na altura do conteúdo.

**`03_pagination_engine.md`**: Estratégia Render → Measure → Paginate; geração de `<div class="page">` por página.

**`04_table_pagination.md`** e **`05_keep_together_blocks.md`**: Tabela longa quebra em múltiplas páginas com header repetido; blocos com `keepTogether: true` não quebram.

**FR Reposicionamento** (`docs/prd-v3.md` / `usePagination.ts`): elemento fixo se reposiciona abaixo de elemento dinâmico de referência via `reposicionarElementoFixo`.

---

## Frontend — Status de Implementação

**Componentes existentes:**

- `/home/user/migrador-planet/frontend/src/composables/usePagination.ts` (Story 9.5): implementa `calcBodyHeight()`, `calcRemainingSpace()`, `calculatePageBreaks()`, `buildHeaderFooterLayout()`, `repositionFixedElement()`. Exporta composable `usePagination()` com state reativo.
- `/home/user/migrador-planet/frontend/src/composables/header-footer.spec.ts` (Story 9.6): testes unitários cobrindo `buildHeaderFooterLayout` (seção repeat=true em todas as páginas, repeat=false só na página 1, mix de repeating/não-repeating), `calculateRemainingSpace` (subtrai header+footer, nunca negativo), integração com `calculatePageBreaks` (header/footer reduzem bodyHeight e causam mais quebras).
- `/home/user/migrador-planet/frontend/src/composables/table-pagination.ts` (Story 9.5): `splitTableRows()` divide linhas em chunks respeitando `maxHeightPx` e `minRowsPerPage`; `buildTablePages()` gera `TablePage[]` com `isContinuation` e `showHeader`; `calcMinRowsPerPage()` valida mínimo de 1.
- `/home/user/migrador-planet/frontend/src/organisms/inspectors/PageInspector.vue`: configura tamanho (A4/Letter/Custom), orientação, margens (top/bottom/left/right em mm), altura de Header (px) e Footer (px), exibe Área de Conteúdo calculada, altura do corpo e espaço restante via Layout Engine.

**O que funciona:**
- Algoritmo de quebra de página no Layout Engine (FR12 Camada 1): `calculatePageBreaks()` itera elementos top-to-bottom, insere quebra quando `currentY + el.height > bodyHeight`.
- Header/Footer com `repeat=true` em todas as páginas; `repeat=false` apenas na página 1 — via `buildHeaderFooterLayout()`.
- Reposicionamento dinâmico: `repositionFixedElement()` implementado e exposto pelo composable.
- Configuração de margens, alturas de header/footer e tamanho de página via PageInspector.
- Table pagination: `splitTableRows()` + `buildTablePages()` com `repeatHeader` e `minRowsPerPage` configuráveis.
- Testes unitários cobrindo todos os cenários acima (`header-footer.spec.ts`).

**O que falta:**
- Header/Footer diferenciado "primeira página vs demais": a lógica de `buildHeaderFooterLayout` implementa `repeat=false` para aparecer só na página 1, mas **não há suporte a uma seção específica "apenas páginas 2+"** (ex: footer diferente nas páginas intermediárias vs última). O modelo atual é binário: repete em tudo ou só na 1.
- Canvas multi-página renderizado visualmente (empilhamento de páginas com gap/sombra entre elas): a lógica de quebra está no composable, mas a renderização visual das múltiplas páginas no Canvas component não foi verificada nesta auditoria.
- Keep-together no Canvas: `05_keep_together_blocks.md` especifica que bloco com `keepTogether: true` não deve quebrar. A flag `keep_together` aparece como display-only no `TableInspector` (`InspectorField` — somente leitura) — não há lógica no `calculatePageBreaks()` para honrar essa flag.
- `base.js` runtime (FR12 Camada 2): funções `quebrarTabelaEntrePaginas()` / `criarNovaPagina()` não foram encontradas no backend de geração do template (stage5). A paginação é calculada no editor, mas não há evidência de que o `base.js` gerado contenha essas funções.

---

## Backend — Status de Implementação

**Stage 3** (`stage3_structural_analysis.py`):
- Detecção de zonas header/footer via heurística de posição Y: `header_end = zone_map.get("header", {}).get("bbox")[3]` ou fallback `page_height * 0.10`; `footer_start` ou fallback `page_height * 0.90` (linhas 861–862).
- Os bboxes de header e footer são propagados como zonas estruturais com `"type": "header"` / `"footer"` nas seções.

**Stage 5** (`stage5_template_generation.py`):
- Header e footer height extraídos das regiões detectadas (linhas 746–770): `header_height_px` e `footer_height_px` são usados para gerar CSS `.header { height: Npx; }` e `.footer { height: Npx; }`.
- Os valores `header_height_px` e `footer_height_px` são incluídos no output do PipelineResult (linhas 1308–1309).
- **Não encontrado**: lógica de `quebrarTabelaEntrePaginas()` ou `criarNovaPagina()` sendo emitida no `base.js` gerado. O stage5 gera HTML com a estrutura de uma página, mas não há evidência de geração de múltiplas `<div class="page">` nem de funções JS de paginação runtime.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | `base.js` runtime não contém funções `quebrarTabelaEntrePaginas()` / `criarNovaPagina()` — FR12 Camada 2 não implementada | 🔴 Crítico | Backend (stage5) | FR12, `docs/prd-v3.md` linha 192 |
| 2 | Keep-together: flag `keep_together` exibida apenas como read-only no TableInspector; `calculatePageBreaks()` não a honra | 🟡 Importante | Frontend | `05_keep_together_blocks.md`, FR12 |
| 3 | ~~Header/Footer diferenciado por posição~~ — **ADIADO (P3 futuro)**: modelo binário (repeat/não-repeat) é suficiente para agora. Story 33.1 já expõe toggle de repetição no SectionInspector. Caso avançado (header diferente por posição: first/middle/last) pode ser retomado no futuro se necessário — complexidade estimada: baixa (enum no buildHeaderFooterLayout) a média (seções separadas na árvore) | ⏸ Adiado | — | Decisão de produto — suficiente com repeat/não-repeat por agora |
| 4 | Canvas multi-página empilhado visualmente (múltiplas `<div class="page">` com gap, sombra, número de página) — implementação no componente Canvas não verificada | 🟡 Importante | Frontend | `canvas_pagination_spec.md` seção 10, FR7 |
| 5 | ~~Stage5 página única~~ — **DESCARTADO**: comportamento correto. Dados são dinâmicos (KO bindings), não é possível pré-gerar páginas sem dados reais. Stage5 gera estrutura de 1 página (header/flow/footer) e `base.js` pagina em runtime após injeção de dados. Decisão arquitetural confirmada | ✅ Correto | — | Decisão arquitetural — paginação é 100% runtime no template |

---

## Backlog Gerado

1. **FR12 Camada 2 — base.js runtime**: Implementar geração de `quebrarTabelaEntrePaginas()` e `criarNovaPagina()` no stage5; o template exportado deve conter a lógica de paginação idêntica à do Layout Engine.
2. **Keep-together no Layout Engine**: Extender `calculatePageBreaks()` para aceitar flag `keepTogether` por elemento; mover bloco inteiro para próxima página quando não cabe no espaço restante.
3. **Keep-together no TableInspector**: Tornar o campo "Manter Junto" editável (trocar `InspectorField` por `InspectorCheckbox`) e persistir a propriedade.
4. ~~**Stage5 multi-página**~~ — **RESOLVIDO**: paginação é 100% runtime no template. Stage5 gera 1 página (header/flow/footer), KO injeta dados, `base.js` mede conteúdo e cria páginas extras dinamicamente. Comportamento atual é correto.
5. ~~**Header/Footer por tipo de página**~~ — **ADIADO (P3 futuro)**: repeat/não-repeat suficiente por agora (coberto na Story 33.1). Se necessário no futuro: estender `buildHeaderFooterLayout()` com enum `first|middle|last|all` (baixa complexidade) ou seções separadas na árvore (média complexidade).

---

## Status Geral

🟡 Parcial — O Layout Engine frontend (cálculo de quebras, header/footer repetição, table pagination, reposicionamento) está bem implementado com testes unitários. O gap crítico é a ausência das funções de paginação runtime no `base.js` gerado pelo stage5, o que compromete a fidelidade do template exportado.
