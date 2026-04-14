# Auditoria: Inspetor Hierárquico (4 níveis)

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR39** (`docs/prd-v3.md` linhas 117-128): O painel inspetor (direita) deve adaptar-se ao nível do nó selecionado na Árvore de Estrutura:

| Nível | Nó selecionado | Propriedades |
|-------|---------------|-------------|
| 1 — Página | Document (raiz) | Tamanho (A4/Letter/Custom), orientação, margens, alturas header/footer, grid, colunas detectadas |
| 2 — Seção | Header, Flow, Footer, seções opcionais | Altura, fundo, padding, repetição por página, travar seção, visibilidade (sempre/condicional/escondido) |
| 3 — Componente | Tabela, Gráfico, Container, Imagem | Data source, colunas/datasets, paginação, dimensões, âncora, manter junto, camada, visibilidade |
| 4 — Elemento | Campo de texto, rótulo, ícone | Posição X/Y, tamanho, tipografia (fonte, tamanho, peso, cor, entrelinha), espaçamento, tipo de campo, binding, âncora, visibilidade, camada, travar |

**Propriedade Visibilidade** (todos os níveis): 3 opções — Sempre visível, Condicional (construtor `SE [campo] [operador] [valor]` com E/OU, gera `<!-- ko if: expressão -->`), Escondido.

**Tipos de campo suportados (nível 4):** Texto, Número, Moeda (BRL), Data, CPF, CNPJ, Percentual, Telefone, Personalizado.

**Specs UX adicionais:**
- `docs/ideias/ux/section_inspector_level2_spec.md`: Section Inspector controla regiões Header, Flow, Footer — altura, comportamento de repetição, visibilidade
- `docs/ideias/ux/component_inspector_level3_spec.md`: Component Inspector para Table, Chart, Container, Image — data bindings, paginação, layout flow
- `docs/ideias/ux/element_inspector_level4_spec.md`: Element Inspector — controle preciso de elemento individual, posição, tipografia
- `docs/ideias/ux/page_and_element_configuration.md`: Page Setup com tamanho, margens, header/footer height

---

## Frontend — Status de Implementação

### InspectorPanel.vue — Roteamento de Nível
**Arquivo:** `frontend/src/organisms/InspectorPanel.vue`

Implementado e funcional:
- Roteamento automático via `inspectorMap` (linha 29-35): `page → PageInspector`, `section → SectionInspector`, `component → ComponentInspector`, `element → ElementInspector`, `structural → StructuralNodeInfo`
- Título dinâmico: `"Inspetor de {levelLabel}: {node.name}"` (linha 49-53)
- Seleciona o inspector correto conforme `inspector.level` do `inspectorStore`

**Gap:** Header, Footer e Flow roteiam para `StructuralNodeInfo` (nível `structural`) em vez de `SectionInspector` (nível `section`). Isso contradiz a spec (FR39) que define Header/Footer/Flow como nível 2 — Seção. `StructuralNodeInfo.vue` provavelmente exibe menos propriedades do que o SectionInspector completo.

### inspectorStore.ts — Mapeamento de Tipo → Nível
**Arquivo:** `frontend/src/stores/inspectorStore.ts`

- `LEVEL_MAP` (linhas 6-20): `document → page`, `header/footer/flow → structural`, `section → section`, `table/chart/image/container/barcode → component`, `text/field → element`
- `selectNode()` (linha 50): detecta nível automaticamente ao selecionar nó
- `initFromTree()` (linha 73): inicializa inspector com o nó raiz (document) sem marcar como seleção do usuário

### PageInspector.vue (Nível 1)
**Arquivo:** `frontend/src/organisms/inspectors/PageInspector.vue`

Implementado:
- Dimensões: tamanho (A4/Letter/Custom), orientação (retrato/paisagem), largura/altura customizada
- Margens: top, bottom, left, right (com limites calculados)
- Estrutura: altura do Header, altura do Footer, área de conteúdo calculada automaticamente
- Layout Engine: altura do corpo (px), espaço restante (px)
- Grid: ativar/desativar, tamanho do grid
- Colunas: detectadas, posições, travar

**Falta:** Não implementa o toggle de "header/footer toggle" explicitamente no nível Página — esse controle está no SectionInspector.

### SectionInspector.vue (Nível 2)
**Arquivo:** `frontend/src/organisms/inspectors/SectionInspector.vue`

Implementado:
- Geral: tipo da seção (badge), altura
- Aparência: cor de fundo (color picker), imagem de fundo (upload)
- Bordas: border editor completo
- Espaçamento: padding top/bottom/left/right
- Comportamento: "Repetir em cada página" (apenas para Header/Footer), "Bloquear Seção"
- Visibilidade: VisibilityControl com modos sempre/condicional/escondido
- Botão "Remover do template"
- Alterações atualizam `templateStore.updateNodeProperty()`

**Falta da spec:**
- Layout type/tipo de layout para seções opcionais — não há campo de "tipo de layout" configurável além do tipo estrutural
- Seções condicionais detectadas pelo Analisador Multi-Documento não vêm pré-preenchidas como `Condicional` (dependente de Story 9.1)

**Problema:** Header, Footer e Flow não chegam ao SectionInspector — são roteados para `StructuralNodeInfo` pelo `LEVEL_MAP` (ver gap no InspectorPanel).

### TableInspector.vue / ComponentInspector.vue (Nível 3)
**Arquivo:** `frontend/src/organisms/inspectors/TableInspector.vue`
**Arquivo:** `frontend/src/organisms/inspectors/ComponentInspector.vue`

Implementado (ComponentInspector delega para sub-inspectors):
- TableInspector: nome, fonte de dados (binding), colunas (campo, largura, alinhamento, drag-para-reordenar, remover), header row (TableCellEditor), linhas (altura, padding, border-collapse), paginação (quebrar entre páginas, repetir cabeçalho, min linhas por página), posição (âncora, manter junto), visibilidade (VisibilityControl)
- ImageInspector: dimensões (W/H/escala), alinhamento, URL/path, visibilidade, ações (substituir/baixar/remover)
- ChartInspector: existe como componente separado
- ContainerInspector: existe
- BarcodeInspector: existe

**Falta da spec FR39 para tabela:**
- Binding de `foreach` explícito não está como campo separado — está embutido em "Fonte de Dados" mas sem rótulo `foreach`
- Datasets múltiplos (spec FR26 menciona "múltiplos datasets" para gráficos) — não verificado completamente

### ElementInspector.vue (Nível 4)
**Arquivo:** `frontend/src/organisms/inspectors/ElementInspector.vue`

Implementado:
- Posição X/Y (read-only via `InspectorField`)
- Dimensões largura/altura (read-only)
- Box Model visual (margin/border/padding editáveis)
- Tipografia: família, tamanho, peso, cor, line-height, espaçamento, alinhamento (left/center/right/justify), estilo (italic, underline, strikethrough), transformação (uppercase/lowercase/capitalize)
- Aparência: cor de fundo (color picker com presets e cores do documento)
- Padding (top/right/bottom/left editáveis)
- Bordas: border editor completo
- Dados: tipo de campo (badge), binding editor (BindingEditor com autocomplete de campos XSD)
- Format String: FormatStringEditor com preview de entrada→saída
- Estilo Condicional: ConditionalStyleSection
- Posição Avançada: âncora (read-only)
- Visibilidade: VisibilityControl (sempre/condicional/escondido)
- Camada e bloqueio (read-only)

**Gap da spec:**
- Posição X/Y é read-only — especificado como editável (FR39: "Posição X/Y, tamanho")
- Tamanho W/H também read-only — especificado como editável
- Entrelinha (line-height) exibida mas read-only

### StructuralNodeInfo.vue
**Arquivo:** `frontend/src/organisms/inspectors/StructuralNodeInfo.vue`

Não inspecionado diretamente, mas é o inspector para Header/Footer/Flow. Provavelmente exibe apenas informações básicas do nó sem as propriedades completas do SectionInspector.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Header/Footer/Flow roteiam para `StructuralNodeInfo` em vez de `SectionInspector` — operador não consegue configurar repetição, padding, altura, visibilidade nesses nós estruturais | 🔴 Crítico | Frontend (inspectorStore.ts linha 9-11) | FR39 Nível 2, section_inspector_level2_spec.md |
| 2 | Posição X/Y e tamanho W/H no ElementInspector são read-only — spec define como editável | 🔴 Crítico | Frontend (ElementInspector.vue) | FR39 Nível 4: "Posição X/Y, tamanho" |
| 3 | Edições no Inspector NÃO disparam re-render do Canvas (GAP 1 do gap-analysis-v3) — `templateStore.updateNodeProperty()` é chamado mas Canvas não observa `templateStore` | 🔴 Crítico | Frontend (HTMLCanvas.vue, generation.ts) | gap-analysis-frontend-v3.md GAP 1, Story 29.2 |
| 4 | Tipo de campo (Texto, Número, Moeda BRL, Data, CPF, CNPJ, Percentual, Telefone, Personalizado) exibido como badge read-only — spec define como selecionável para determinar formatação | 🟡 Importante | Frontend (ElementInspector.vue) | FR39 Nível 4: "tipo de campo", prd-v3.md linha 128 |
| 5 | Binding `foreach` de tabela não tem campo dedicado explícito no TableInspector | 🟡 Importante | Frontend (TableInspector.vue) | FR39 Nível 3: "Data source" para tabela |
| 6 | Campos opcionais detectados pelo Analisador Multi-Documento não vêm pré-preenchidos como Condicional no VisibilityControl | 🟡 Importante | Frontend (integração pipeline → inspector) | FR39 linha 126: "já vêm pré-preenchidos como Condicional" |
| 7 | Construtor visual `SE [campo] [operador] [valor]` com suporte E/OU — necessário verificar se VisibilityControl.vue implementa condições compostas | 🟡 Importante | Frontend (VisibilityControl.vue) | FR39 Propriedade Visibilidade, FR9 |
| 8 | Entrelinha (line-height) e letter-spacing exibidos mas não editáveis | 🟢 Menor | Frontend (ElementInspector.vue) | FR39 Nível 4: "tipografia (entrelinha)" |

---

## Backlog Gerado

1. **Corrigir roteamento de Header/Footer/Flow para SectionInspector** — alterar `LEVEL_MAP` em `inspectorStore.ts` para mapear `header/footer/flow → 'section'` em vez de `'structural'`. Validar que `SectionInspector.vue` funciona corretamente para os tipos estruturais.

2. **Tornar Posição X/Y e tamanho W/H editáveis no ElementInspector** — substituir `InspectorField` read-only por `InspectorInput` com handlers que chamam `templateStore.updateNodeProperty()`. Dependente do Story 29.2 (re-render Canvas).

3. **Implementar re-render do Canvas após edições no Inspector** — Story 29.2 do Epic 29. Sem isso, todas as edições via Inspector são invisíveis para o operador. Adicionar watcher em `HTMLCanvas.vue` para `templateStore` mutations.

4. **Tornar Tipo de Campo selecionável no ElementInspector** — substituir badge read-only por dropdown/select com os tipos definidos em FR39 (Texto, Número, Moeda BRL, Data, CPF, CNPJ, Percentual, Telefone, Personalizado). Atualizar `templateStore` ao mudar.

5. **Adicionar campo `foreach` binding explícito no TableInspector** — campo dedicado para `data-bind="foreach: {path}"` separado do campo de nome/fonte de dados.

6. **Integrar detecção do Analisador Multi-Documento com VisibilityControl** — quando pipeline detecta campo opcional, pre-popular modo de visibilidade como `Condicional` com o campo correspondente.

7. **Auditar VisibilityControl.vue** — verificar se o construtor de condições suporta E/OU compostos conforme especificado em FR9/FR39.

---

## Status Geral

🟡 Parcial — A arquitetura do Inspetor Hierárquico está correta (InspectorPanel roteia para componentes especializados, inspectorStore detecta nível automaticamente). PageInspector, SectionInspector, TableInspector e ElementInspector têm boa cobertura de propriedades. Os gaps críticos são: Header/Footer/Flow incorretamente roteados para StructuralNodeInfo, posição/tamanho read-only no ElementInspector, e o loop fundamental quebrado (edições não atualizam o Canvas — GAP 1 do Epic 29 ainda não resolvido).
