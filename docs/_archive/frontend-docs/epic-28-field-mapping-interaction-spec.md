# Epic 28 — Field Mapping Panel Redesign: Interaction Spec

**Autor:** @ux-design-expert (Uma)
**Data:** 2026-04-01
**Epic:** docs/epics/epic-28-field-mapping-redesign.md
**Stack:** Vue 3 + Pinia + TypeScript — dark editor panel

---

## Contexto Visual

O editor é um painel dark. O Inspector fica no lado direito. A aba "Campos" fica no painel esquerdo (`LeftPanel.vue`). Os tokens de cor existentes:

```
--color-neutral-100   #f3f4f6   (texto principal)
--color-neutral-300   #d1d5db   (texto secundário)
--color-neutral-400   #9ca3af   (labels uppercase)
--color-neutral-600   #4b5563   (border sutil)
--color-neutral-700   #374151   (hover background)
--color-neutral-800   #1f2937   (surface level 2)
--color-neutral-900   #111827   (surface level 1)
--color-primary-200   #bfdbfe   (texto selected)
--color-primary-400   #60a5fa   (focus ring)
--color-primary-900   #1e3a5f   (selected background)
--color-green-500     #22c55e   (mapped / OK)
--color-yellow-400    #facc15   (ambiguous)
--color-red-500       #ef4444   (unmapped / error)
```

---

## Modelo de Interação Completo — Diagrama de Sistema

Antes de detalhar cada story, é essencial entender como os três painéis se relacionam:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EDITOR LAYOUT                              │
│                                                                    │
│  ┌──────────────┐   ┌──────────────────────────┐   ┌───────────┐  │
│  │  LEFT PANEL  │   │        CANVAS            │   │ INSPECTOR │  │
│  │              │   │                          │   │           │  │
│  │  ▼ Estrutura │   │  ┌──────────────────┐    │   │  ▼ Dados  │  │
│  │  └ root      │   │  │  [nó selecionado]│◄───┼───┤  Binding  │  │
│  │    └ section ─────►  │  (highlight)    │    │   │  [editor] │  │
│  │      └ [nó] ◄─────── └──────────────────┘    │   │           │  │
│  │              │   │                          │   │           │  │
│  │  ─────────── │   │                          │   │           │  │
│  │  ▼ Campos    │   │                          │   │           │  │
│  │  └ 🟩 Venc.──┼───────────────────────────────┼─► seleciona  │  │
│  │    🟥 Comp.  │   │                          │   │    nó      │  │
│  │    🟨 Benef. │   │                          │   │           │  │
│  └──────────────┘   └──────────────────────────┘   └───────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Fluxo de seleção (Campos → Estrutura → Inspector → Canvas)

**O que acontece quando clica num campo na aba Campos:**

```
1. FieldNavigator.onSelectField(field)
   ↓
2. inspectorStore.selectNode(node)   ← Inspector atualiza
   editorStore.selectElement(node.id) ← Canvas destaca o elemento
   ↓
3. StructureTree assiste inspectorStore.selectedNode via watch
   → selectedNodeId.value = node.id  ← Estrutura destaca o nó
   ⚠️  GAP: se o nó está dentro de pai COLAPSADO, o highlight não aparece
        (não há auto-expand ao selecionar via FieldNavigator)
```

**Diagnóstico:**
- A sincronização via `watch(inspectorSelectedId)` funciona — mas só destaca. Não expande a árvore.
- Resultado: o usuário clica num campo na aba Campos, o canvas destaca corretamente, mas a aba Estrutura parece não reagir se o nó pai estiver colapsado.

---

### Drag de Campo: onde funciona e onde não funciona

| Destino do drag | Resultado atual | Esperado |
|----------------|----------------|---------|
| Nó na aba **Estrutura** | ✅ Funciona — `handleDropField` chama `mappingStore.mapField` | — |
| Nó no **Canvas** | ❌ Sem handler — HTMLCanvas.vue não aceita drops de campo | Ver Story 28.4 |
| Área vazia do Canvas | ❌ Nenhum feedback visual | Ver Story 28.4 |

**Fluxo do drag que funciona (Campos → Estrutura):**
```
FieldNavItem.dragstart
  → dataTransfer.setData('drag-type', 'field')
  → dataTransfer.setData('field-path', field.path)
       ↓
StructureTreeNode.handleDrop
  → dragType === 'field' → emit('drop-field', { nodeId, fieldPath })
       ↓
StructureTree.handleDropField
  → SE binding existente: abre confirmDialog
  → SE sem binding: mappingStore.mapField(nodeId, fieldPath)
```

**Fluxo do drag que NÃO existe (Campos → Canvas):**
```
FieldNavItem.dragstart → dataTransfer setado
  ↓
HTMLCanvas.vue: sem @dragover, sem @drop → drop silencioso, nada acontece
```

---

### Story 28.4 — Drag de Campo para o Canvas (gap identificado)

Este gap foi descoberto durante a elaboração do interaction spec e **deve ser adicionado ao Epic 28** como story adicional.

**Problema:** O canvas (HTMLCanvas.vue) é a superfície visual principal do editor. É intuitivo que o operador arraste um campo diretamente sobre um elemento visual no canvas para vinculá-lo — mas esse handler não existe.

**Comportamento esperado:**

```
Usuário arrasta 🟥 "Competência" da aba Campos
  → Passa over do canvas
  → Elemento sob o cursor recebe highlight de "drop target" (outline azul pulsante)
  → Solta sobre o elemento
  → mappingStore.mapField(elementId, fieldPath)
  → Binding vinculado — campo muda para 🟩
```

**Arquivos afetados:**
- `frontend/src/organisms/HTMLCanvas.vue` — adicionar `@dragover` + `@drop` handlers
- `frontend/src/organisms/CanvasSelectionOverlay.vue` — adicionar estilo de "drop target" ativo

**AC principais:**
- AC1: Arrastar campo sobre elemento no canvas mostra highlight de "drop aqui" no elemento
- AC2: Soltar vincula o binding (comportamento idêntico ao drop na StructureTree)
- AC3: SE binding existente: mesmo dialog de confirmação da StructureTree
- AC4: Arrastar sobre área vazia do canvas (sem elemento sob cursor) mostra cursor `no-drop` — sem ação

---

### Story 28.5 — Auto-expand na Estrutura ao selecionar via Campos

**Problema:** `StructureTree.selectedNodeId` atualiza via watch quando `inspectorStore.selectedNode` muda, mas os pais colapsados não expandem automaticamente. O operador não consegue ver onde o nó está na árvore.

**Comportamento esperado:**

```
Usuário clica em "🟩 Vencimento" na aba Campos
  → nó correspondente selecionado no inspector e canvas ✅ (já funciona)
  → aba Estrutura expande todos os ancestrais do nó
  → scroll da árvore posiciona o nó visível
  → nó fica destacado (selectedNodeId) na árvore
```

**Arquivo afetado:**
- `frontend/src/organisms/StructureTree.vue` — no `watch(inspectorSelectedId)`, além de setar `selectedNodeId`, calcular ancestrais e adicioná-los a `expandedNodes`

**AC principais:**
- AC1: Selecionar campo na aba Campos expande automaticamente os ancestrais na aba Estrutura
- AC2: O nó selecionado aparece visível na árvore sem scroll manual
- AC3: A expansão automática não colapsa nós que já estavam expandidos

---

### Relação bidirecional completa (pós Epic 28)

```
                        ┌──────────────────┐
                        │   inspectorStore │
                        │  .selectedNode   │
                        └─────────┬────────┘
                                  │  watch bidirecional
              ┌───────────────────┼────────────────────┐
              ▼                   ▼                    ▼
   ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
   │  FieldNavigator  │  │  StructureTree   │  │   HTMLCanvas     │
   │  click campo     │  │  click nó        │  │  click elemento  │
   │  → seleciona nó  │  │  → seleciona nó  │  │  → seleciona nó  │
   │  → highlight     │  │  → highlight     │  │  → highlight     │
   └──────────────────┘  └──────────────────┘  └──────────────────┘
              │                   ▲                    │
              │    28.5: auto-    │                    │
              └───────expand──────┘                    │
              │                                        │
              │    drag campo → canvas (28.4)          │
              └────────────────────────────────────────┘
```

---

### Sequência de Implementação Revisada

```
28.1 (Inspector binding editor)   ← independente, alto valor imediato
  ↓
28.2 (XSD visíveis + nomes)       ← depende de session.ts estável
  ↓
28.3 (Modal ambiguidade)          ← depende de FieldNavigator estável
  ↓
28.5 (Auto-expand StructureTree)  ← depende de 28.2 (FieldNavigator estável)
  ↓
28.4 (Drag para canvas)           ← independente tecnicamente, mas entrega coerência UX completa
```

---

## Story 28.1 — Binding Editor no Inspector

### Objetivo

Substituir o `InspectorField` read-only de "Binding" por um controle editável com busca/autocomplete nos XSD paths disponíveis.

---

### Wireframe: Estado sem binding

```
┌─────────────────────────────────────┐
│ ▼ Dados                             │  ← InspectorSection "Dados" (colapsável)
├─────────────────────────────────────┤
│  TIPO DE CAMPO                      │
│  [texto]                            │
│                                     │
│  BINDING                            │
│  ┌───────────────────────────────┐  │
│  │ 🟥  Sem vínculo XSD         ▾ │  │  ← BindingEditor, estado: sem binding
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Wireframe: Estado com binding definido

```
┌─────────────────────────────────────┐
│ ▼ Dados                             │
├─────────────────────────────────────┤
│  TIPO DE CAMPO                      │
│  [texto]                            │
│                                     │
│  BINDING                            │
│  ┌──────────────────────────── ✕ ┐  │  ← botão ✕ aparece apenas quando binding definido
│  │ 🟩  data.vencimento          ▾ │  │  ← badge status inline + XSD path
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Wireframe: Dropdown aberto + busca

```
┌─────────────────────────────────────┐
│ ▼ Dados                             │
├─────────────────────────────────────┤
│  TIPO DE CAMPO                      │
│  [texto]                            │
│                                     │
│  BINDING                            │
│  ┌──────────────────────────── ✕ ┐  │
│  │ 🟩  data.vencim...           ▾ │  │  ← trigger (fechado trunca o path)
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │  ← dropdown portado ao body (z-index alto)
│  │ [🔍 Buscar XSD path...     ] │  │  ← input de busca auto-focado ao abrir
│  ├──────────────────────────────┤  │
│  │ 🟩  data.vencimento         │  │  ← opção atual (highlight)
│  │    data.valor               │  │
│  │    data.beneficiario        │  │
│  │    cliente.nome             │  │
│  │    cliente.documento        │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Wireframe: Busca filtrando

```
│  ┌──────────────────────────────┐  │
│  │ [🔍 venc                   ] │  │  ← usuário digitou "venc"
│  ├──────────────────────────────┤  │
│  │ 🟩  data.vencimento         │  │  ← único match highlight
│  │     (sem outros resultados) │  │
│  └──────────────────────────────┘  │
```

### Wireframe: XSD não disponível

```
│  BINDING                            │
│  ┌───────────────────────────────┐  │
│  │ ⚪  XSD não disponível        │  │  ← disabled, cursor not-allowed
│  └───────────────────────────────┘  │
│  ⓘ Carregue um XSD para ativar     │  ← tooltip ou caption pequeno
```

---

### Interaction Flow 28.1

```
Usuário clica no trigger ▾
  → Dropdown abre
  → Input de busca recebe foco automático
  → Lista mostra TODOS os flat_paths do XSD
  → À medida que digita: filtra por substring (case-insensitive)
  → Clica em uma opção:
      → Emite update:binding(path)
      → FieldNavigator atualiza status do navItem para 🟩
      → Dropdown fecha
  → Clica em ✕:
      → Emite update:binding(null)
      → Status muda para 🟥
      → Botão ✕ desaparece
  → Pressiona Escape:
      → Dropdown fecha sem mudança
  → flat_paths é null/vazio:
      → Trigger fica disabled
      → Caption "XSD não disponível" visível
```

---

### Estados do BindingEditor

| Estado | Badge | Trigger | Botão ✕ |
|--------|-------|---------|---------|
| Sem binding, XSD disponível | 🟥 | "Sem vínculo XSD" (placeholder) | não aparece |
| Com binding, mapeado | 🟩 | path truncado (max 22 chars + `…`) | aparece |
| Com binding, não confirmado | 🟨 | path truncado | aparece |
| XSD não disponível | ⚪ | "XSD não disponível" | não aparece; disabled |

---

### Componente: `BindingEditor.vue` (nova molécula)

**Localização:** `frontend/src/molecules/BindingEditor.vue`

**Props:**
```typescript
interface Props {
  modelValue: string | null    // XSD path atual (binding)
  flatPaths: string[] | null   // lista de XSD paths disponíveis
  status: 'mapped' | 'unmapped' | 'unconfirmed'
}
```

**Emits:**
```typescript
interface Emits {
  'update:modelValue': [path: string | null]
}
```

**Acessibilidade:**
- `role="combobox"` no trigger
- `aria-expanded` controlado
- `aria-autocomplete="list"` no input de busca
- Navegação por setas no dropdown (↑↓ + Enter + Escape)
- `aria-label="Binding XSD"` no trigger

---

### Mudança no ElementInspector.vue

Substituir a linha 142:
```html
<!-- ANTES -->
<InspectorField label="Binding" :value="(props.node?.binding ?? strValue('binding'))" />

<!-- DEPOIS -->
<BindingEditor
  :model-value="props.node?.binding ?? null"
  :flat-paths="mappingStore.flatPaths"
  :status="bindingStatus"
  @update:model-value="onBindingChange"
/>
```

Onde `bindingStatus` computa com base em `mappingStore.fieldNavItems` se o path atual está mapeado/não confirmado.

---

## Story 28.2 — Campos XSD Visíveis + Nomes Semânticos

### Objetivo

Dois problemas de visibilidade corrigidos:
1. **2a** — Campos XSD sem match aparecem na lista com badge especial
2. **2b** — Nomes semânticos substituem raw PDF text

---

### Wireframe: FieldNavigator antes (estado atual com problemas)

```
┌─────────────────────────────────────┐
│ 📊 Campos    25 de 55 mapeados  ██░ │  ← não mostra XSD-only
├─────────────────────────────────────┤
│ [Buscar campo...]  [Todos ▼]        │
├─────────────────────────────────────┤
│ 📋 4.978,54               🟩        │  ← raw PDF text — sem sentido
│ 📋 000                    🟥        │
│ 📋 30/03/2026             🟩        │
│ 📋 BANCO DO BRASIL S.A.   🟨        │
└─────────────────────────────────────┘
```

### Wireframe: FieldNavigator depois (28.2 implementado)

```
┌─────────────────────────────────────┐
│ 📊 Campos  25/55 PDF + 8 XSD 🔴  ██│  ← contagem dupla; badge alerta XSD
├─────────────────────────────────────┤
│ [Buscar campo...]  [Todos ▼]        │
├─────────────────────────────────────┤
│ 📋 Valor Cobrado          🟩        │  ← nome semântico ("data.valor_cobrado" → "Valor Cobrado")
│    4.978,54                         │  ← raw PDF text como subtítulo em cinza
│                                     │
│ 📋 Competência            🟥        │  ← "data.competencia" → "Competência"
│    000                              │
│                                     │
│ 📋 Vencimento             🟩        │  ← "data.vencimento" → "Vencimento"
│    30/03/2026                       │
│                                     │
│ 📋 Beneficiário           🟨        │  ← ambíguo
│    BANCO DO BRASIL S.A.             │
│                                     │
│ ─────── XSD sem match ─────────    │  ← separador visual
│ 🔴 cliente.nome                    │  ← XSD-only: sem PDF match, badge especial
│ 🔴 cliente.documento               │
│ 🔴 endereco.cep                    │
└─────────────────────────────────────┘
```

---

### Item com nome semântico: anatomia do FieldNavItem

```
┌─────────────────────────────────────┐
│ 📋  [Nome Semântico]          🟩    │  ← linha principal (font-size: 0.8125rem)
│     [raw PDF text]                  │  ← subtítulo (font-size: 0.6875rem, color-neutral-400)
└─────────────────────────────────────┘
```

**Regra de derivação do nome semântico:**
- Se `xsd_field_path` existe: pegar último segmento + capitalizar
  - `data.vencimento` → `Vencimento`
  - `cliente.nome` → `Nome`
  - `endereco.cep` → `Cep` (futuro: dicionário de labels humanizadas)
- Se não tem `xsd_field_path`: usar `field.name` (label do PDF ou raw text)

---

### Item XSD-only: anatomia

```
┌─────────────────────────────────────┐
│ 🔴  cliente.nome                    │  ← sem subtítulo (não tem PDF text)
│     XSD obrigatório                 │  ← caption pequeno em vermelho
└─────────────────────────────────────┘
```

- Badge: `🔴` (não o emoji de status — é um ícone diferente, cor `--color-red-400`)
- Cursor: `default` (não arrastável — não tem PDF block para vincular)
- Click: abre tooltip "Este campo XSD não tem correspondência no PDF. Pode ser preenchido via formato condicional."
- Não aparece no `StructureTree` (não é um nó do template)

---

### Header: contagem atualizada

```
Antes:  "25 de 55 campos mapeados"
Depois: "25/55 PDF · 8 XSD 🔴"
```

- `25/55` = campos PDF mapeados / total PDF
- `8 XSD 🔴` = XSD-only sem match (clicável abre filtro "XSD sem match")
- Progress bar reflete apenas PDF fields (XSD-only não afeta a barra)

---

### Filtro dropdown atualizado

```
[Todos ▼]
├── Todos
├── Mapeados 🟩
├── Não mapeados 🟥
├── Ambíguos 🟨
└── XSD sem match 🔴  ← novo
```

---

### Mudanças de tipo em `FieldNavItem`

**Adicionar ao tipo existente:**
```typescript
interface FieldNavItem {
  // ... campos existentes
  semanticName?: string    // nome derivado do XSD path (28.2b)
  rawPdfText?: string      // raw PDF text preservado como subtítulo (28.2b)
  isXsdOnly?: boolean      // true = campo do XSD sem PDF match (28.2a)
}
```

---

## Story 28.3 — Modal de Resolução de Ambiguidade

### Objetivo

Implementar o handler do evento `open-ambiguous` no `FieldNavigator` para abrir modal com os candidatos XSD e permitir resolução.

---

### Trigger: quando abre

Campo com `isAmbiguous: true` é clicado → `FieldNavItem` emite `open-ambiguous` → `FieldNavigator` recebe e abre `AmbiguousFieldModal`.

---

### Wireframe: Modal fechado (antes da resolução)

```
campo 🟨 Beneficiário  BANCO DO BRASIL S.A.
```

Clique → modal abre:

---

### Wireframe: AmbiguousFieldModal

```
┌─────────────────────────────────────────────┐
│  ⚡ Resolver Ambiguidade                   ✕ │
│─────────────────────────────────────────────│
│  Campo PDF: "BANCO DO BRASIL S.A."           │
│  Selecione o campo XSD correto:              │
│                                             │
│  ┌─────────────────────────────────────────┐ │
│  │ ○  beneficiario.nome          ██ 87%   │ │  ← score bar: verde se >70%, amarelo se 50-70%
│  │ ○  beneficiario.razao_social  ██ 72%   │ │
│  │ ○  cedente.nome               ██ 51%   │ │  ← amarelo
│  │ ○  banco.nome                 ██ 34%   │ │  ← cinza (baixo score)
│  └─────────────────────────────────────────┘ │
│                                             │
│  ○  Nenhum dos anteriores — deixar sem     │
│     mapeamento                             │
│                                             │
│  ─────────────────────────────────────────  │
│         [Cancelar]  [Confirmar →]          │
└─────────────────────────────────────────────┘
```

---

### Wireframe: Opção selecionada

```
│  ┌─────────────────────────────────────────┐ │
│  │ ●  beneficiario.nome          ██ 87%   │ │  ← selecionado (radio preenchido, highlight row)
│  │ ○  beneficiario.razao_social  ██ 72%   │ │
│  │ ○  cedente.nome               ██ 51%   │ │
│  │ ○  banco.nome                 ██ 34%   │ │
│  └─────────────────────────────────────────┘ │
│                                             │
│  ○  Nenhum dos anteriores — deixar sem     │
│     mapeamento                             │
│                                             │
│         [Cancelar]  [Confirmar →]          │  ← "Confirmar" habilitado apenas se seleção feita
```

---

### Wireframe: Score bar visual

Cada candidato exibe uma barra proporcional ao score:

```
beneficiario.nome     [████████░░] 87%   ← cor: --color-green-500
beneficiario.razao    [███████░░░] 72%   ← cor: --color-green-500
cedente.nome          [█████░░░░░] 51%   ← cor: --color-yellow-400
banco.nome            [███░░░░░░░] 34%   ← cor: --color-neutral-500
```

Regras de cor da barra:
- ≥70%: `--color-green-500`
- 50–69%: `--color-yellow-400`
- <50%: `--color-neutral-500`

---

### Interaction Flow 28.3

```
1. Usuário clica campo 🟨 Beneficiário
   → FieldNavItem emite 'open-ambiguous' com field

2. FieldNavigator recebe @open-ambiguous
   → Seta ambiguousField = field
   → showAmbiguousModal = true
   → Modal monta com candidates = field.candidates

3. Usuário vê candidatos ordenados por score (desc)
   → Clica em opção (radio seleciona)
   → "Confirmar" habilita

4a. Confirmar com candidato:
   → mappingStore.resolveAmbiguous(field.path, candidato.path)
   → field.isAmbiguous = false, field.status = 'mapped'
   → node.binding = candidato.path
   → FieldNavItem muda de 🟨 para 🟩
   → Modal fecha
   → Header atualiza contagem

4b. Confirmar com "Nenhum dos anteriores":
   → mappingStore.resolveAmbiguous(field.path, null)
   → field.isAmbiguous = false, field.status = 'unmapped'
   → node.binding = null
   → FieldNavItem muda de 🟨 para 🟥
   → Modal fecha

4c. Cancelar / Escape / ✕:
   → Modal fecha sem mudança
   → Campo permanece 🟨
```

---

### Componente: `AmbiguousFieldModal.vue` (nova molécula)

**Localização:** `frontend/src/molecules/AmbiguousFieldModal.vue`

**Props:**
```typescript
interface Candidate {
  path: string         // XSD path candidato
  score: number        // 0.0 – 1.0
  label?: string       // nome humanizado (opcional)
}

interface Props {
  field: FieldNavItem        // campo ambíguo sendo resolvido
  candidates: Candidate[]    // lista de candidatos (vem de field.candidates)
  modelValue: boolean        // v-model para visibilidade
}
```

**Emits:**
```typescript
interface Emits {
  'update:modelValue': [visible: boolean]
  resolve: [fieldPath: string, xsdPath: string | null]
}
```

**Comportamento:**
- Overlay semi-transparente sobre o editor (não bloqueia o canvas visualmente)
- Focus trap no modal enquanto aberto
- `aria-modal="true"`, `role="dialog"`, `aria-labelledby`
- Fechar com Escape
- Confirmação desabilitada (button disabled) até seleção

---

### Mudança em FieldNavigator.vue

Adicionar handler e estado:

```typescript
// Estado
const ambiguousField = ref<FieldNavItem | null>(null)
const showAmbiguousModal = ref(false)

// Handler
function onOpenAmbiguous(field: FieldNavItem) {
  ambiguousField.value = field
  showAmbiguousModal.value = true
}

// Resolução
function onResolveAmbiguous(fieldPath: string, xsdPath: string | null) {
  mappingStore.resolveAmbiguous(fieldPath, xsdPath)
  showAmbiguousModal.value = false
  ambiguousField.value = null
}
```

No template, adicionar `@open-ambiguous="onOpenAmbiguous"` no `FieldNavItem` e montar o `AmbiguousFieldModal`.

---

## Resumo: Novos Componentes

| Componente | Tipo | Story |
|-----------|------|-------|
| `BindingEditor.vue` | Molécula | 28.1 |
| `AmbiguousFieldModal.vue` | Molécula | 28.3 |

## Resumo: Arquivos Modificados

| Arquivo | Mudança | Story |
|---------|---------|-------|
| `ElementInspector.vue` | Substituir InspectorField por BindingEditor | 28.1 |
| `stores/mapping.ts` | Expor `flatPaths`, action `resolveAmbiguous` | 28.1 + 28.3 |
| `stores/session.ts` | Passar `unmapped_xsd_fields` para mappingStore | 28.2 |
| `FieldNavigator.vue` | Handler `@open-ambiguous`, montar modal, names semânticos | 28.2 + 28.3 |
| `FieldNavItem.vue` | Renderizar `semanticName` + `rawPdfText` como subtítulo | 28.2 |
| `types/field-navigator.types.ts` | Adicionar `semanticName`, `rawPdfText`, `isXsdOnly` | 28.2 |
| `types/pipeline.types.ts` | Adicionar `unmapped_xsd_fields` no contrato | 28.2 |

## Sequência de Implementação

```
28.1 — Independente → pode ir para produção antes das outras
  ↓
28.2 — Depende de session.ts estável (reconcileFieldBindings já implementado)
  ↓
28.3 — Depende de FieldNavigator estável (handler open-ambiguous)
```

---

## Design Decisions

| Decisão | Justificativa |
|---------|---------------|
| BindingEditor como molécula separada | Reusável em outros inspectors; testável isoladamente |
| Dropdown portado ao body | Evita overflow hidden do painel do inspector |
| Score bar com cor por threshold | Guia o usuário para a opção mais provável sem texto extra |
| Subtítulo raw PDF text sempre visível | Operador precisa confirmar qual bloco PDF corresponde |
| XSD-only não arrastável | Não tem block_id/PDF origin para fazer drag-drop |
| "Nenhum dos anteriores" obrigatório | Usuário deve poder rejeitar todos os candidatos explicitamente |
| Progress bar apenas PDF (não XSD) | XSD-only são "alertas", não interferem no progresso do template |

---

*— Uma, desenhando com empatia 💝*
*Spec pronta para @sm criar stories 28.1 → 28.2 → 28.3*
