# Aba Estrutura — Audit UX + Bugs Encontrados

**Autor:** @ux-design-expert (Uma)
**Data:** 2026-04-01

---

## Bugs reais — por que "clico e não muda o inspector"

### Bug 1 — Clicar em um nó faz duas coisas ao mesmo tempo

```javascript
// StructureTreeNode.vue — handleClick()
function handleClick() {
  emit('select', props.node)        // ← seleciona o nó (correto)
  if (hasChildren.value) {
    emit('toggle', props.node.id)   // ← TAMBÉM expande/colapsa (problema!)
  }
}
```

**O que o usuário experimenta:**
```
Usuário clica em "📦 Cabeçalho" (que tem filhos)
  → O subtree colapsa (efeito visual dominante)
  → Clica de novo → subtree expande
  → O inspector muda? SIM, mas o usuário está olhando para o collapse/expand
  → Percepção: "não fez nada no inspector"
```

**O correto:** clique = seleção. O ícone ▶/▼ = toggle (e ele JÁ tem `@click.stop` separado).
A linha `emit('toggle')` dentro de `handleClick` precisa ser removida.

---

### Bug 2 — Clicar em header, footer, flow → inspector errado

**O mapeamento atual em `inspectorStore.ts`:**
```javascript
const LEVEL_MAP = {
  document: 'page',   // → PageInspector
  header:   'page',   // → PageInspector  ← PROBLEMA
  footer:   'page',   // → PageInspector  ← PROBLEMA
  flow:     'page',   // → PageInspector  ← PROBLEMA
  section:  'section', // → SectionInspector ✓
  text:     'element', // → ElementInspector ✓
  field:    'element', // → ElementInspector ✓
  // ...
}
```

**PageInspector** foi construído para o nó raiz `document`. Ele lê `props.node.properties` esperando encontrar:
- `size`, `orientation`, `margin_top`, `margin_bottom`, `header_height`, `footer_height`, `grid_enabled`...

Mas o nó `header` não tem nenhuma dessas propriedades — elas estão no nó `document`.

**O que o usuário vê ao clicar em "Cabeçalho":**
```
Inspector de Página: header          ← título muda (usuário pode não notar)
  ▼ Dimensões
    Tamanho: —                       ← vazio (header não tem 'size')
    Orientação: ○ Retrato ○ Paisagem ← sem valor selecionado
  ▼ Margens
    Topo: —  Base: —  ...           ← todos vazios
  ▼ Grid
    Ativar Grid: □                   ← desmarcado (sem valor)
```

**Percepção do usuário:** "O inspector não mudou nada de útil. Clicar não faz nada."

---

### Bug 3 — Binding sem cor, sem status visual

O nó de texto com binding exibe:
```
🔤 text-47   → {{data.vencimento}}
```

Mas:
- `→ {{data.vencimento}}` está em cinza (`.structure-tree-node__binding`) sem cor de status
- Não há indicação se está 🟩 corretamente mapeado ou 🟨 ambíguo
- Nós SEM binding (que deveriam ter) não têm nenhuma indicação visual de problema

---

## UX Problems — além dos bugs

### Problema 4 — Nomes técnicos sem significado

```
📦 flow                  ← o que é "flow"?
📦 header                ← mais claro, mas ainda técnico
📦 section               ← genérico
🔤 text-47               ← "text-47" não diz nada ao operador
🔤 text-33               ← idem
```

O operador não sabe o que é `text-47`. O conteúdo do PDF (valor atual: `30/03/2026`) estaria disponível, mas não é exibido como label.

---

### Problema 5 — Ações só via context menu (não descobrível)

Para **remover um binding**, o único caminho é:
- Right-click no nó → "Remover binding"

Não existe hover action, nem botão inline. Um usuário que não tentou right-click não descobre essa funcionalidade.

Para **adicionar/trocar um binding**, não existe nenhum caminho na aba Estrutura hoje.

---

### Problema 6 — Sem filtro de cobertura

A aba Campos tem status (🟩🟥🟨) e progressbar. A aba Estrutura não tem nenhuma visão de cobertura — o operador não sabe, olhando para a árvore, se a cobertura de campos está completa ou não.

---

## Redesign Proposto — StructureTreeNode

### Antes (estado atual)

```
┌─────────────────────────────────────────────────────┐
│ ▼ 📦 section-header                                 │  ← click = seleciona E colapsa
│   · 🔤 text-47   → {{data.vencimento}}              │  ← binding em cinza
│   · 🔤 text-12   → {{data.valor_cobrado}}           │
│   · 🔤 text-33                                      │  ← sem binding, sem indicação
│ ▶ 📦 section-body                                   │
│   (colapsado)                                        │
└─────────────────────────────────────────────────────┘
```

### Depois (proposta Epic 28.6)

```
┌─────────────────────────────────────────────────────┐
│ ▼  📦 Cabeçalho                              3/4 ██ │  ← toggle separado; cobertura
│    · 🔤 Vencimento              🟩 data.venc...  [⚙]│  ← hover mostra ação
│    · 🔤 Valor Cobrado           🟩 data.valor... [⚙]│
│    · 🔤 Beneficiário            🟨 3 cand.      [⚙]│  ← amarelo = ambíguo
│    · 🔤 (sem texto — text-33)   🟥 sem binding  [⚙]│  ← vermelho = sem binding
│ ▶  📦 Corpo                                  1/6 █░ │
└─────────────────────────────────────────────────────┘
```

---

## Detalhamento do redesign — linha por linha

### Nó container (section, header, body, footer...)

```
ANTES:  [▼] 📦 section-header
DEPOIS: [▼] 📦 Cabeçalho                              3/4 ██░

         │       │                                     │    │
         │       └─ nome humanizado (não técnico)      │    └─ barra mini de cobertura
         └─ toggle separado (já funciona, só visual)   └─ "X/total filhos com binding"
```

- Toggle `▼`/`▶` só faz expand/collapse (já está correto no código)
- Clique no **nome/área do nó** → só seleciona, não colapsa
- Barra de cobertura opcional (aparece só em seções com filhos binding-able)

---

### Nó de dados (text, field)

```
ANTES:  · 🔤 text-47   → {{data.vencimento}}
DEPOIS: · 🔤 Vencimento              🟩 data.vencimento      [⚙]

         │   │                       │   │                    │
         │   └─ nome do conteúdo ou  │   └─ path truncado     └─ hover: abre binding
         │      XSD label            └─ badge colorido           editor inline ou
         └─ ícone de tipo                                         no inspector
```

**Regra do nome:**
- Tem binding + XSD label → usa label semântico (`data.vencimento` → `Vencimento`)
- Tem binding, sem label → usa path truncado (`data.venc...`)
- Sem binding → usa conteúdo PDF truncado (`"30/03/20..."`) ou `"(vazio)"`

**Cores do badge:**
- 🟩 = binding definido e mapeado (status `mapped`)
- 🟨 = binding ambíguo (status `unconfirmed`)
- 🟥 = nó de dados sem binding (type `text`/`field` sem `node.binding`)
- *(sem badge)* = nó estrutural (section, container) — não tem binding por design

---

### Hover actions

```
· 🔤 Vencimento    🟩 data.vencimento    [⚙]   ← aparece só no hover
                                          │
                              abre binding editor
                              no inspector (28.1)
                              OU inline dropdown
```

Apenas um botão [⚙] discreto no hover — não polui a árvore em estado normal.

---

### Inspector routing corrigido

| Tipo de nó | Inspector atual | Inspector correto |
|-----------|----------------|-------------------|
| `document` | PageInspector | PageInspector ✓ |
| `header` | PageInspector ❌ | **StructuralNodeInfo** (novo, simples) |
| `footer` | PageInspector ❌ | **StructuralNodeInfo** |
| `flow` | PageInspector ❌ | **StructuralNodeInfo** |
| `section` | SectionInspector ✓ | SectionInspector ✓ |
| `container` | ComponentInspector ✓ | ComponentInspector ✓ |
| `text`, `field` | ElementInspector ✓ | ElementInspector ✓ (+ BindingEditor 28.1) |
| `table`, `chart`, etc. | ComponentInspector ✓ | ComponentInspector ✓ |

**StructuralNodeInfo** (novo, minimalista):
```
Inspector de Estrutura: Cabeçalho
  ─────────────────────────────────
  TIPO              Cabeçalho (header)
  FILHOS            4 elementos
  COM BINDING       3 de 4
  ─────────────────────────────────
  ⓘ Propriedades de layout do cabeçalho
    são configuradas no nó Documento.
    Clique em "Documento" para editar.
```

---

## Stories geradas por este audit

### Story 28.6 — StructureTree: separar click de toggle + routing correto
**Tipo:** Bug fix + UX
**Arquivos:**
- `frontend/src/molecules/StructureTreeNode.vue` — remover toggle de handleClick
- `frontend/src/stores/inspectorStore.ts` — corrigir LEVEL_MAP para header/footer/flow
- `frontend/src/organisms/inspectors/StructuralNodeInfo.vue` — novo inspector minimalista

**AC:**
- AC1: Clicar no nome de um nó com filhos seleciona sem expandir/colapsar
- AC2: O ícone ▶/▼ continua funcionando para toggle (já funciona, não mexer)
- AC3: Clicar em header/footer/flow mostra StructuralNodeInfo, não PageInspector
- AC4: O inspector muda visivelmente ao clicar qualquer nó da árvore

### Story 28.7 — StructureTree: status de binding visual nos nós
**Tipo:** Enhancement UX
**Arquivos:**
- `frontend/src/molecules/StructureTreeNode.vue` — adicionar badge 🟩🟥🟨
- `frontend/src/organisms/StructureTree.vue` — passar fieldNavItems como prop para colorir

**AC:**
- AC1: Nós `text`/`field` com binding mostram badge colorido (🟩🟥🟨)
- AC2: Nós `text`/`field` sem binding mostram 🟥 discretamente
- AC3: Nós container (section, header) mostram mini barra de cobertura (X/Y filhos)
- AC4: Badge hover mostra tooltip com o XSD path completo

---

## Sequência revisada do Epic 28 (completa)

```
28.1  Inspector binding editável      ← pivô — bridge entre as duas abas
  ↓
28.6  StructureTree click bug fix     ← desbloqueador: faz a aba Estrutura funcionar
  ↓
28.2  Campos: nomes semânticos + XSD  ← melhora aba Campos
  ↓
28.7  StructureTree: badges de status ← integra visualmente com 28.1 + 28.2
  ↓
28.3  Modal de ambiguidade            ← fecha fluxo Campos
  ↓
28.4  Drag campo → canvas             ← alternativa visual (pode ser paralelo a 28.3)
```

28.6 pode (e deve) ir antes de 28.2/28.7 porque é bug fix.
28.1 + 28.6 juntos formam o MVP mínimo para a aba Estrutura funcionar de verdade.

---

## Resumo visual: antes × depois

```
HOJE — O que o operador experimenta:
─────────────────────────────────────────────────────────────────
Aba Campos:   nomes sem sentido (30/03/2026), clique → inspector ✓
              (depois do fix session.ts desta semana)
              drag → lugar nenhum
              ambíguo → nada acontece

Aba Estrutura: clicar em nó = expande/colapsa (parece não selecionar)
               clicar em header/footer → inspector mostra coisa errada
               nós com binding → texto cinza sem cor
               ações → só via right-click (ninguém descobre)

Inspector:    binding read-only, não pode editar nada

DEPOIS — O que o operador vai experimentar (Epic 28 completo):
─────────────────────────────────────────────────────────────────
Aba Campos:   nomes semânticos ("Vencimento"), clique → inspector ✓
              campo ambíguo → modal de escolha
              XSD sem match → aparece com 🔴
              drag → canvas vincula

Aba Estrutura: clicar em nó = seleciona (inspector atualiza claramente)
               header/footer → inspector mostra info útil
               nós com binding → badge colorido 🟩🟥🟨
               hover → botão ⚙ para editar binding

Inspector:    BINDING EDITÁVEL — dropdown de XSD paths, remove, status badge
              (funciona independente de qual aba está ativa)
```

---

*— Uma, desenhando com empatia 💝*
*StructureTree audit v1 — 2 bugs críticos + 4 UX problems + 2 novas stories (28.6, 28.7)*
