# Auditoria: Field Mapping — Field Navigator + Auto-binding + Format String

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR4** (`docs/prd-v3.md` linha 77): Matching automático com IA entre valores do PDF e campos do XSD, com correspondência semântica (Vision AI + pgvector embeddings), normalização de formatos (moeda BR, datas, CEP, telefone) e reconhecimento de texto contextual.

**FR5** (`docs/prd-v3.md` linha 79): Quando matching retornar múltiplos candidatos para um mesmo trecho do PDF, apresentar a lista de opções ao operador para escolha manual.

**FR6** (`docs/prd-v3.md` linha 81): Para campos formatados (ex: `"R$ 1.234,56"` → `1234.56`), tentar desnormalizar automaticamente; se incerto, apresentar opções de tipo de formatação e gerar função correspondente no `base.js`.

**FR8** (`docs/prd-v3.md` linha 174): Operador pode mapear manualmente campos via aba Campos no painel esquerdo — lista todos os campos do XSD por tipo com status (🟩 mapeado, 🟥 não mapeado, 🟨 não confirmado); arrastar campo para a Árvore de Estrutura cria binding.

**FR21** (`docs/prd-v3.md` linha 220): Format strings customizados combinando múltiplos campos JSON (ex: `"{Logradouro}, {Numero} - {Bairro}"`), gerando função computada no `base.js` com autocomplete de campos na UI.

**Field Navigator** (`docs/ideias/ux/template_editor_main_screen_spec.md` seção 3): Lista de campos (FIELDS, TABLES, CHARTS, ASSETS), click → highlight no PDF, drag → assign para template, hover → preview no PDF.

**Wireframe Aba Campos** (`docs/wireframes/wireframes-mid-fi.md` linhas 485-514): campos agrupados com status visual (🟩/🟥/🟨), seções para Campos/Tabelas/Gráficos/Seções/Recursos, click localiza na árvore + canvas + inspector, drag para árvore cria binding.

**Story 30.1** (`docs/stories/backlog/` ou stories): validar auto-mapping com Boleto Bancário — confirmação de que o matching funciona end-to-end com documento real.

---

## Frontend — Status de Implementação

### FieldNavigator.vue
**Arquivo:** `frontend/src/organisms/FieldNavigator.vue`

Implementado:
- Summary header com contagem dual (mapeados/total) e barra de progresso
- Agrupamento por status: XSD obrigatórios sem match (grupo vermelho 🔴), campos unmapped/unconfirmed/mapped separados
- Grupo `xsdOnlyFields` — campos XSD que não têm correspondência no PDF (Story 28.2)
- Colapso/expansão de grupos (grupo `mapped` começa colapsado)
- Seleção de campo → `onSelectField` navega para o nó na árvore + destaca no Canvas + abre Inspector
- Modal de ambiguidade (`AmbiguousFieldModal`) para resolução de candidatos múltiplos (Story 28.3)
- Hint contextual ao clicar "Vincular →" orientando drag/click no canvas

**Drag de campo para a árvore:**
- `FieldNavItem.vue` implementa `draggable="true"` com `dataTransfer.setData('drag-type', 'field')` e `dataTransfer.setData('field-path', ...)`
- `StructureTree.vue` recebe o drop via `handleDropField()` → `mappingStore.mapField()`
- Drag para o Canvas diretamente: não implementado — Story 28.4 (`docs/stories/28.4.drag-campo-canvas.story.md`) prevê isso mas não confirmado como Done

**Falta da spec:**
- Hover sobre campo não exibe preview de localização no PDF
- Filtros e busca no Field Navigator — não há campo de busca/filtro visible no template
- Agrupamento por tipo (Tabelas, Gráficos, Seções, Recursos) conforme wireframe — implementação agrupa por status (mapped/unmapped/unconfirmed), não por tipo de campo

### FieldMappingTable.vue
**Arquivo:** `frontend/src/organisms/FieldMappingTable.vue`

Componente simples e funcional:
- Exibe campos com colunas: Campo XSD, Texto PDF, Tipo, Confiança (ConfidenceBadge), Status (FieldStatusBadge + ManualEditIndicator)
- Seleção de linha emite `select` event
- Sem filtros/busca

### FieldDetailPanel.vue
**Arquivo:** `frontend/src/organisms/FieldDetailPanel.vue`

Implementado (formato legacy, pre-FieldNavigator redesign):
- Exibe detalhes do campo selecionado: ID, Texto PDF, Tipo, Status
- Edição manual de `jsonPath` via input + botão Salvar
- Lista de candidatos alternativos com botão para selecionar

**Observação:** Este componente parece ser parte da UI legada anterior ao redesign do FieldNavigator (Stories 28.x). Pode estar duplicado ou sobreposto com funcionalidades do novo FieldNavigator.

### mapping.ts (Pinia store)
**Arquivo:** `frontend/src/stores/mapping.ts`

Implementado:
- `fieldNavItems` — lista de itens para o FieldNavigator com status (mapped/unmapped/unconfirmed), path XSD, nome PDF, isAmbiguous
- `xsdOnlyFields` — campos XSD sem match no PDF (UnmappedXsdField)
- `flatPaths` — caminhos XSD planos para autocomplete no BindingEditor
- `mapField(nodeId, fieldPath)` — aplica binding no nó via templateStore + atualiza status
- `removeBinding(nodeId)` — remove binding
- `updateNodeBinding(nodeId, xsdPath)` — alternativa com sync de fieldNavItem
- `resolveAmbiguous(fieldPath, chosenPath)` — resolve ambiguidade escolhendo um candidato
- `loadPipelineFields(entries, ambiguousFields)` — popula store a partir do resultado do pipeline, incluindo candidatos ambíguos
- `setUnmappedXsdFields(fields)` — popula `xsdOnlyFields`

**Confiança por campo:** O pipeline retorna `confidence` por field mas o store mapeia como `'medium'` hardcoded (linha 140 de mapping.ts: `confidence: 'medium' as FieldMapping['confidence']`). A confiança real do backend não está sendo propagada para exibição.

---

## Backend — Status de Implementação

### stage4_field_mapping.py
**Arquivo:** `backend/services/stages/stage4_field_mapping.py`

Implementado:
- Sub-step 4.1: XSD Parsing (via `xsd_parser.py`)
- Sub-step 4.3: Format Pre-Detection com regex antes do matching (currency_brl, date_numeric, date_extenso, cpf, cnpj, phone, cep, percentage)
- Sub-step 4.4: Section-XSD Matching — fuzzy match de seções para nós XSD complexos
- Sub-step 4.5: Batch Field Matching via Gemini Flash (`google/gemini-2.0-flash-001`) via OpenRouter — 1 chamada LLM por layout, two-pass
- Sub-step 4.6: Confidence Scoring — 5 fatores heurísticos (`layout_stability`, `anchor_detection`, `grid_quality`, `field_variability`, `vision_agreement`)
- Sub-step 4.7: Consistency Validation — orphans, unmapped required, type-format compatibility
- Prompt batch retorna até 3 candidatos por pair com score (FR5 implementado)
- Geração de funções JS de formatação para `base.js` (FR6: currency, date, cpf, cnpj, phone, cep, percentage)

**Vision AI + pgvector embeddings (FR4):**
- O modelo usado é Gemini Flash via OpenRouter — sem pgvector ou embeddings vetoriais no código de stage4
- Vision AI (GPT-4o Vision) é usado no stage3 para análise visual das páginas, não no stage4 para matching
- O matching em stage4 é por LLM text-only (Gemini Flash), não por similarity search vetorial (pgvector)
- `vision_agreement` é um dos 5 fatores de confiança mas refere-se a acordo com a análise visual do stage3, não a chamada Vision AI nova no stage4

**OpenRouter/Gemini configuração:**
- `GEMINI_FLASH_MODEL = "google/gemini-2.0-flash-001"` (linha 40)
- `openrouter_client` obtido do contexto via `context.get("openrouter_client")` (linha 1127)
- Fallback gracioso quando `openrouter_client` é None — retorna resultados sem LLM matching

### matcher.py
**Arquivo:** `backend/services/matcher.py`

Implementado:
- `normalize_name(name)` — remove acentos, lowercase, colapsa separadores
- `levenshtein_similarity(a, b)` — sem dependências externas
- `normalize_br_format(value, field_type)` — normalização de formatos BR (moeda, data, CEP, telefone)

**Observação:** `matcher.py` parece ser um helper simples. O matching principal via LLM está em `stage4_field_mapping.py`. Não há pgvector, embeddings, ou similarity search vetorial neste arquivo.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Vision AI + pgvector embeddings (FR4) não implementados — matching usa LLM text-only (Gemini Flash), sem embeddings vetoriais ou busca por similaridade semântica com pgvector | 🔴 Crítico | Backend (stage4_field_mapping.py) | FR4 "Vision AI + pgvector embeddings", prd-v3.md linha 77 |
| 2 | Confiança por campo não propagada ao frontend — store mapping.ts hardcoda `confidence: 'medium'` para todos os campos, ignorando score real do stage4 | 🔴 Crítico | Frontend (mapping.ts linha 140) + Backend (contrato de dados) | FR5, FieldMappingTable.vue (coluna Confiança) |
| 3 | Drag de campo para o Canvas (mapeamento manual visual) não implementado — Story 28.4 planejada mas não confirmada como Done | 🟡 Importante | Frontend (FieldNavigator.vue, HTMLCanvas.vue) | FR8: "arrastar campo da lista para a Árvore de Estrutura cria binding", Story 28.4 |
| 4 | Agrupamento do FieldNavigator por status (mapped/unmapped) não corresponde ao wireframe que agrupa por tipo (Campos/Tabelas/Gráficos/Seções/Recursos) | 🟡 Importante | Frontend (FieldNavigator.vue) | wireframes-mid-fi.md linhas 489-510 |
| 5 | Busca e filtros no Field Navigator não implementados | 🟡 Importante | Frontend (FieldNavigator.vue) | wireframes-mid-fi.md (campo de busca implícito), template_editor_main_screen_spec.md seção 3 |
| 6 | Story 30.1 (auto-mapping validado com Boleto) — status não confirmado como Done no backlog. Com nomes semânticos da Story 29.4 implementados, validation pendente | 🟡 Importante | End-to-end (backend + frontend) | Story 30.1, epic-29 Story 29.4 AC5 (> 10/66 campos) |
| 7 | Hover sobre campo no Field Navigator não mostra preview de localização no PDF | 🟢 Menor | Frontend (FieldNavItem.vue, FieldNavigator.vue) | template_editor_main_screen_spec.md seção 3: "Hover → preview location in PDF" |
| 8 | FieldDetailPanel.vue parece componente legado redundante com funcionalidades do novo FieldNavigator | 🟢 Menor | Frontend (FieldDetailPanel.vue) | Dívida técnica |

---

## Backlog Gerado

1. **Implementar Vision AI embeddings + pgvector para matching semântico (FR4)** — atual matching via Gemini Flash LLM text-only. Avaliar custo/benefício de adicionar embeddings vetoriais. Alternativa: usar similarity search textual mais robusta (sentence embeddings via OpenRouter).

2. **Propagar score de confiança real do stage4 ao frontend** — alterar `loadPipelineFields()` em `mapping.ts` para usar o score real retornado pelo pipeline (`entry.confidence` ou similar) em vez de hardcodar `'medium'`. Atualizar o tipo `FieldMapping.confidence` para suportar valores numéricos ou categorias derivadas do score real.

3. **Implementar drag de campo do FieldNavigator para o Canvas (Story 28.4)** — quando operador arrasta campo e solta em elemento no Canvas, criar binding automaticamente. Requer handler `drop` no Canvas identificando elemento clicado por posição.

4. **Adicionar modo de agrupamento por tipo no FieldNavigator** — toggle ou aba para alternar entre agrupamento por status (atual) e agrupamento por tipo (Campos/Tabelas/Gráficos/Seções/Recursos) conforme wireframe.

5. **Adicionar busca/filtro no FieldNavigator** — campo de texto para filtrar campos por nome. Implementar como `computed` sobre `fieldNavItems` filtrado por query string.

6. **Validar auto-mapping com Boleto Bancário (Story 30.1)** — executar pipeline completo com Boleto Bancário após Story 29.4 (nomes semânticos) para confirmar que coverage > 10/66 conforme AC5 da Story 29.4. Documentar resultado.

7. **Remover ou deprecar FieldDetailPanel.vue** — auditar se ainda é usado em alguma tela. Se redundante com o novo FieldNavigator redesign (Stories 28.x), marcar para remoção.

8. **Implementar hover preview no FieldNavigator** — ao hover em campo, destacar bounding box correspondente na aba PDF Referência. Requer comunicação entre FieldNavigator e PDFReferencePanel via store ou evento.

---

## Status Geral

🟡 Parcial — O Field Navigator e o mapping store estão bem implementados (agrupamento, status visual, candidatos ambíguos, drag para árvore, format string no ElementInspector). O matching automático via Gemini Flash via OpenRouter funciona (stage4 com LLM batch). Os gaps críticos são: Vision AI + pgvector não implementados (FR4 parcialmente atendido apenas com LLM text), confiança real não propagada ao frontend, e drag de campo para Canvas ausente. O end-to-end com Boleto Bancário (Story 30.1) ainda pendente de validação.
