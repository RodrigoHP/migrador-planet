# Epic 14 — Wireframes de Baixa Fidelidade

> **Autora:** Uma (@ux-design-expert)
> **Fidelidade:** Baixa (Lo-Fi)
> **Data:** 2026-03-22
> **Epic:** 14 — Capacidades Visuais do Editor
> **Stories:** 14.1, 14.5, 14.6, 14.8, 14.12

---

## 1. Layout Geral do Editor (Referência Visual)

```
+------------------------------------------------------------------+
| [Logo] migrador-planet       [Salvar] [Desfazer] [Refazer] [Config] |
+----------+--------------------------------------+----------------+
|          |  [Canvas] [PDF] [Code] [Sync] [Split]|                |
| BARRA    |                                      |  BARRA         |
| LATERAL  |                                      |  LATERAL       |
| ESQ.     |        PAINEL CENTRAL                 |  DIR.          |
| [Struct] |                                      | Inspetor de    |
| [Fields] |    +--------------------------+      | Elemento       |
| [Files]  |    |                          |      |                |
| [Layers] |    |    CANVAS / EDITOR       |      | [Posicao]      |
|   NOVO   |    |                          |      | [Dimensoes]    |
|          |    |    (ou Visão Dividida)   |      | [Box Model]    |
|          |    |                          |      |   NOVO         |
|          |    +--------------------------+      | [Aparencia]    |
|          |                                      |   NOVO         |
|          |                                      | [Tipografia]   |
|          |                                      | [Dados]        |
|          |                                      | [Format]       |
|          |                                      | [Condicional]  |
+----------+--------------------------------------+----------------+
```

**Legenda:** Itens marcados `NOVO` são novos neste epic.

---

## 2. Story 14.5 — Barra de Alinhamento (Toolbar Contextual)

### 2.1 Wireframe: Toolbar aparece ao selecionar 2+ elementos

```
Área do Canvas
+----------------------------------------------------------+
|                                                          |
|   +--------+      +--------+       +--------+           |
|   | Data   |      | Número |       | Espécie|           |
|   | Emissão|      | Doc    |       |        |           |
|   +--------+      +--------+       +--------+           |
|         ↑ selecionados (borda azul tracejada)            |
|                                                          |
|   ┌──────────────────────────────────────┐               |
|   │ [⫷] [⫿] [⫸] │ [⤒] [⊞] [⤓] │ [⫰] [⫱] │  ← Toolbar|
|   └──────────────────────────────────────┘               |
|    ↑Alinhar H      ↑Alinhar V     ↑Distribuir           |
|                                                          |
+----------------------------------------------------------+
```

### 2.2 Detalhe: 8 botões da barra de alinhamento

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  ALINHAMENTO HORIZONTAL    VERTICAL      DISTRIBUIÇÃO    │
│  ┌────┐ ┌────┐ ┌────┐   ┌────┐ ┌────┐ ┌────┐  ┌────┐ ┌────┐│
│  │ ⫷  │ │ ⫿  │ │ ⫸  │   │ ⤒  │ │ ⊞  │ │ ⤓  │  │ ⫰  │ │ ⫱  ││
│  │Esq │ │Cent│ │Dir │   │Topo│ │Meio│ │Base│  │ DH │ │ DV ││
│  └────┘ └────┘ └────┘   └────┘ └────┘ └────┘  └────┘ └────┘│
│                                                          │
│  [DH] [DV] ficam DESABILITADOS quando selectedCount < 3  │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 2.3 Fluxo de Interação

```
[Canvas] → [Ctrl+Clique em 2+ elementos]
    ↓
[multiSelection.size >= 2]
    ↓
[AlignmentToolbar aparece ACIMA do bounding box da seleção]
    ↓
[Usuário clica botão de alinhamento]
    ↓
[Elementos se movem animados] → [Snapshot de desfazer salvo]
    ↓
[Limpar seleção] → [Toolbar desaparece]
```

### 2.4 Anotações (UX)

| Item | Anotação |
|------|----------|
| **Posicionamento** | Toolbar flutua 8px ACIMA do bounding box união dos elementos selecionados. Se não cabe acima (próximo ao topo do canvas), aparece ABAIXO |
| **Feedback visual** | Após alinhar, flash de 300ms com borda destaque nos elementos movidos (cor accent #3B82F6) |
| **Zoom** | Toolbar escala inversamente ao zoom do canvas para manter tamanho legível (mín 24px botões) |
| **Z-index** | Toolbar z-index: 200 (acima de overlays de seleção que usam 99-102) |
| **Teclas** | Sem atalhos de teclado nesta story (teclado é story 14.7) |
| **Acessibilidade** | Cada botão com `aria-label` descritivo (ex: "Alinhar à esquerda"), role="toolbar" no container |

---

## 3. Story 14.8 — Painel de Camadas + Grupos

### 3.1 Wireframe: Painel de Camadas na barra lateral esquerda

```
BARRA LATERAL ESQUERDA
+---------------------------+
| [Estrutura] [Campos] [Arquivos] [Camadas] |  ← nova aba
+---------------------------+
|                           |
| CAMADAS (por z-index)     |
| ========================= |
|                           |
| [▼] [Trazer Frente] [Enviar Trás] [↑] [↓] |
|                           |
| ┌─ z:4 ─────────────────┐|
| │ ⠿  🔤 "237"        [👁]│|  ← alça de arraste, tipo, nome, visibilidade
| └────────────────────────┘|
|                           |
| ┌─ z:3 ─────────────────┐|
| │ ⠿  🖼 Logo Bradesco [👁]│|
| └────────────────────────┘|
|                           |
| ┌─ z:2 ── GRUPO ────────┐|
| │ ⠿  📁 "Campos Cabeçalho" │|  ← grupo recolhível
| │   ├─ 🔤 "Data Emissão"│|
| │   ├─ 🔤 "Núm Doc"     │|
| │   └─ 🔤 "Espécie"     │|
| └────────────────────────┘|
|                           |
| ┌─ z:1 ─────────────────┐|
| │ ⠿  ▬ Linha Separadora │|
| └────────────────────────┘|
|                           |
| [+ Agrupar Selecionados]  |  ← quando multi-seleção ativo
| [Desagrupar]              |  ← quando grupo selecionado
|                           |
+---------------------------+
```

### 3.2 Wireframe: Grupo selecionado no Canvas

```
Área do Canvas
+----------------------------------------------------------+
|                                                          |
|   ┌─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┐              |
|   ╎ +--------+  +--------+  +--------+   ╎              |
|   ╎ | Data   |  | Número |  | Espécie|   ╎              |
|   ╎ | Emissão|  | Doc    |  |        |   ╎              |
|   ╎ +--------+  +--------+  +--------+   ╎              |
|   └─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┘              |
|     ↑ borda tracejada azul = grupo selecionado           |
|     Arrastar o grupo move TODOS os filhos proporcionalmente |
|                                                          |
+----------------------------------------------------------+
```

### 3.3 Fluxo de Interação

```
[Ctrl+Clique em 3 elementos]
    ↓
[Ctrl+G ou botão "Agrupar Selecionados"]
    ↓
[Grupo criado no documentTree]
    ↓
[Painel de Camadas mostra grupo recolhível]
    ↓
[Canvas mostra borda tracejada ao redor do grupo]
    ↓
[Arrastar o grupo] → [Todos os filhos movem proporcionalmente]
    ↓
[Ctrl+Shift+G] → [Desagrupar — filhos restaurados como independentes]
```

### 3.4 Anotações (UX)

| Item | Anotação |
|------|----------|
| **Arrastar p/ reordenar** | Alça de arraste (⠿) permite arrastar itens no painel para mudar z-index. Feedback: espaço reservado azul na posição de destino |
| **Ícones de tipo** | 🔤 = texto, 🖼 = imagem, ▬ = linha/separador, 📁 = grupo, 📊 = tabela |
| **Visibilidade** | Ícone 👁 alterna (clique) — oculta/mostra elemento no canvas sem remover da árvore |
| **Seleção sincronizada** | Clique no painel de camadas = seleciona no canvas (destaque). Clique no canvas = destaque no painel |
| **Grupo recolhível** | Clique no 📁 expande/recolhe filhos no painel (sem afetar canvas) |
| **Menu de contexto** | Clique direito na camada: "Agrupar", "Desagrupar", "Trazer p/ Frente", "Enviar p/ Trás", "Excluir" |
| **Acessibilidade** | `role="listbox"` no container, `role="option"` em cada item, `aria-expanded` em grupos |

---

## 4. Story 14.1 — Editor CSS ao Vivo (Visão Dividida + Estilos Computados)

### 4.1 Wireframe: Modo Visão Dividida

```
PAINEL CENTRAL
+------------------------------------------------------------------+
| [Canvas] [PDF] [Código] [Sincronizar]  [⫼ Dividir]  ← novo botão |
+------------------------------------------------------------------+
|                              │                                    |
|   CANVAS (50%)               │  EDITOR MONACO (50%)               |
|                              │                                    |
|   +-----------------------+  │  ┌──────────────────────────┐      |
|   |                       |  │  │ [index.html] [style.css] │      |
|   |   +------+ +------+  |  │  │ [base.js]  [exemplo.js]  │      |
|   |   | Data | | Num  |  |  │  │                          │      |
|   |   | Emis.| | Doc  |  |  │  │ .field-value {           │      |
|   |   +------+ +------+  |  │  │   font-size: 10px;       │      |
|   |                       |  │  │   color: #333;           │      |
|   |   Banco:   BRADESCO   |  │  │   border: 1px solid #ccc;│      |
|   |   237-2               |  │  │ }                        │      |
|   |                       |  │  │                          │      |
|   +-----------------------+  │  │ #template-header {       │      |
|                              │  │   background: #f5f5f5;   │      |
|   [elemento selecionado      │  │ }                        │      |
|    destaca no canvas]        │  │ ← autocomplete: #ids     │      |
|                              │  │   e .classes do template  │      |
|                              │  └──────────────────────────┘      |
|                     [alça de redimensionamento]                   |
+------------------------------------------------------------------+
```

### 4.2 Wireframe: Painel de Estilos Computados

```
MONACO (modo CSS ativo, elemento selecionado)
+------------------------------------------+--------+
|                                          |Estilos |  ← barra lateral recolhível
| .field-value {                           |Comput. |
|   font-size: 10px;                       |--------|
|   color: #333;                           | font   |
|   border: 1px solid #ccc;               |  size: 10px |
| }                                        |  family: Arial|
|                                          |  weight: 400  |
| #template-header {                       |  color: #333  |
|   background: #f5f5f5;                   | layout |
| }                                        |  x: 120px    |
|                                          |  y: 50px     |
| /* Erros CSS marcados com ~~~~ */        |  w: 180px    |
| .broken {                                |  h: 24px     |
|   colr: red; ← ~~~~~ (erro sublinhado)  | bg     |
| }                                        |  none        |
|                                          | border |
| [⚠ 1 erro]  ← indicador na aba style.css|  1px solid   |
+------------------------------------------+--------+
```

### 4.3 Fluxo de Interação

```
[Clicar botão "Dividir" na barra de abas]
    ↓
[PainelCentral entra em modo Visão Dividida]
    ↓
[Canvas (esq) + Monaco (dir) — 50/50, redimensionável]
    ↓
[Editar CSS no Monaco]
    ↓
[Debounce 500ms] → [injectTemplateCSS()] → [Canvas atualiza ao vivo]
    ↓
[Selecionar elemento no canvas]
    ↓
[Painel de Estilos Computados abre na barra lateral do Monaco]
    ↓
[Mostrar CSS aplicado ao elemento (somente leitura)]
```

### 4.4 Anotações (UX)

| Item | Anotação |
|------|----------|
| **Botão Dividir** | Ícone de "colunas verticais" (⫼). Alternável — clique ativa, clique novamente desativa e volta para aba normal |
| **Alça de arraste** | Barra vertical de 4px entre canvas e editor. Cursor: `col-resize`. Largura mín: 30% cada lado |
| **Erros CSS** | Sublinhado ondulado vermelho (severidade Erro) ou amarelo (Aviso). Indicador com contagem na aba |
| **Autocompletar** | Digitar `#` sugere IDs do template, digitar `.` sugere classes. Gatilho: Monaco CompletionItemProvider |
| **Painel Computado** | Barra lateral recolhível à direita do Monaco. Só aparece quando um elemento está selecionado no canvas |
| **Desempenho** | Injeção CSS é síncrona (textContent=css), repaint automático pelo navegador. Sem rAF necessário |
| **Acessibilidade** | Visão dividida: `aria-label="Canvas"` e `aria-label="Editor de código"`. Alça: `role="separator"` |

---

## 5. Story 14.6 — Seletor de Cores Aprimorado

### 5.1 Wireframe: InspectorColorPicker Aprimorado

```
BARRA LATERAL DIREITA — Inspetor de Elemento
+----------------------------------+
| [Aparência]  ← NOVA seção        |
|                                  |
| Cor de Fundo                     |
| ┌──────────────────────────────┐ |
| │ [████] #336699   [Transp] [Herdar] │ ← amostra + hex + predefinidos
| │                              │ |
| │ Opacidade: [========●===] 80%│ |  ← controle deslizante RGBA
| │            rgba(51,102,153,0.8)│ |
| │                              │ |
| │ Cores do Documento (12)      │ |
| │ [██][██][██][██][██][██]     │ |  ← paleta extraída do PDF
| │ [██][██][██][██][██][██]     │ |
| │                              │ |
| │ Recentes (8)                 │ |
| │ [██][██][██][██][██][██][██][██]│ |  ← localStorage
| │                              │ |
| │ [🎨 Seletor Avançado ▼]     │ |  ← expande roda de cores/entradas
| └──────────────────────────────┘ |
|                                  |
+----------------------------------+
```

### 5.2 Wireframe: Seletor Avançado (expandido)

```
┌──────────────────────────────┐
│ [████] #336699   [Transp] [Herdar]│
│                              │
│ ┌────────────────────────┐   │
│ │                        │   │  ← Área de cor (saturação/brilho)
│ │     ●                  │   │
│ │                        │   │
│ └────────────────────────┘   │
│ Matiz:     [=============●] │   │  ← Controle de matiz (arco-íris)
│ Opacidade: [========●=====] │   │
│                              │
│ R: [051]  G: [102]  B: [153]│   │  ← Entradas RGB manuais
│ Hex: [#336699]               │
│                              │
│ Cores do Documento (12)      │
│ [██][██][██][██][██][██]     │
│ [██][██][██][██][██][██]     │
│                              │
│ Recentes (8)                 │
│ [██][██][██][██][██][██][██][██]│
└──────────────────────────────┘
```

### 5.3 Anotações (UX)

| Item | Anotação |
|------|----------|
| **Amostra** | Quadrado 24x24 mostrando a cor atual. Clique abre seletor avançado |
| **Entrada hex** | Editável, aceita #RGB e #RRGGBB. Valida ao perder foco |
| **Transparente** | Botão que emite valor `transparent`. Visual: quadrado xadrez (checkerboard) |
| **Herdar** | Botão que emite valor `inherit`. Visual: seta para cima (↑) |
| **Controle de opacidade** | Faixa 0-100%. Quando < 100%, valor muda de hex para rgba() |
| **Paleta do doc** | 12 amostras 20x20, extraídas das cores únicas do documentTree. Ordenadas por frequência |
| **Recentes** | 8 amostras 20x20, persistidas em localStorage. FIFO — nova cor entra no início |
| **Retrocompat** | SectionInspector e ChartInspector usam o mesmo componente. enableAlpha=false desabilita controle |
| **Acessibilidade** | Cada amostra: `role="option"`, `aria-label="Cor #RRGGBB"`. Container: `role="listbox"`. Controle: `aria-valuemin/max/now` |

---

## 6. Story 14.12 — Visualização Box Model

### 6.1 Wireframe: Visualização Box Model no Inspetor de Elemento

```
BARRA LATERAL DIREITA — Inspetor de Elemento
+----------------------------------+
| [Posição]                        |
|  X: 120px  Y: 50px              |
|                                  |
| [Dimensões]                      |
|  Largura: 180px  Altura: 24px   |
|                                  |
| [Box Model]  ← NOVA seção        |
| ┌──────────────────────────────┐ |
| │        margin                 │ |
| │    ┌─── 0 ───┐               │ |  ← margin-top (clicavel)
| │    │          │               │ |
| │ 0  │ border   │  0            │ |  ← margin-left / right
| │    │ ┌─ 1 ──┐ │              │ |  ← border-top
| │    │ │      │ │              │ |
| │    │1│paddin│1│              │ |  ← border-left/right
| │    │ │┌─ 4 ┐│ │              │ |  ← padding-top
| │    │ ││    ││ │              │ |
| │    │ │4 ** 4│ │              │ |  ← padding-left/right + content
| │    │ ││180×24│ │              │ |  ← content dimensions
| │    │ │└─ 4 ┘│ │              │ |  ← padding-bottom
| │    │ └─ 1 ──┘ │              │ |  ← border-bottom
| │    └─── 0 ───┘               │ |  ← margin-bottom
| │                               │ |
| └──────────────────────────────┘ |
|  Cores: 🟠margem 🟡borda        |
|         🟢preenchimento 🔵conteúdo |
|                                  |
| [Tipografia]                     |
|  ...                             |
+----------------------------------+
```

### 6.2 Wireframe: Edição inline de valor

```
┌──────────────────────────────┐
│        margin                 │
│    ┌─── [0] ───┐             │   ← click no "0" → input inline
│    │            │             │
│ [0]│  borda     │ [0]        │   ← cada número é clicável
│    │ ┌── 1 ──┐  │            │
│    │ │       │  │            │
│    │1│padding│ 1│            │
│    │ │┌─[8]─┐│  │            │   ← usuário editando padding-top: 8
│    │ ││     ││  │            │      (entrada com borda azul)
│    │ │4 *** 4│  │            │
│    │ ││180×24│  │            │
│    │ │└─ 4 ──┘│  │            │
│    │ └── 1 ──┘  │            │
│    └─── 0 ───┘               │
└──────────────────────────────┘

Interação:
  Clique no valor → <input type="number"> inline
  Enter ou Perder foco → salva via updateNodeProperty
  Escape → cancela
```

### 6.3 Anotações (UX)

| Item | Anotação |
|------|----------|
| **Cores** | margem: hsla(30,100%,50%,0.3) laranja, borda: hsla(50,100%,50%,0.3) amarelo, preenchimento: hsla(120,60%,40%,0.3) verde, conteúdo: hsla(210,80%,55%,0.3) azul |
| **Valores** | Números centralizados em cada lado. Fonte: monospace 11px. Cor: branco com sombra para legibilidade |
| **Edição** | Clique → entrada inline (32px largura, monospace). Aceita números inteiros ≥ 0. Tab avança para próximo valor (sentido horário: cima→direita→baixo→esquerda) |
| **Conteúdo** | Centro mostra `largura × altura` em texto menor. Não editável aqui (usar seção Dimensões) |
| **Referência** | Baseado no Chrome DevTools box model — padrão reconhecido por devs |
| **Acessibilidade** | Cada valor: `role="spinbutton"`, `aria-label="margem superior"`, `aria-valuenow`. Cores acompanhadas de rótulo textual para daltônicos |

---

## 7. Story 14.12 (cont.) — Inspetor de Tabela Editável

### 7.1 Wireframe: Colunas editáveis

```
BARRA LATERAL DIREITA — Inspetor de Tabela
+--------------------------------------+
| [Colunas]                            |
|                                      |
| Campo      | Largura | Alinhamento   |
| ========== | ======= | ============= |
| ⠿ data_emissao    | [120px▼] | [esq   ▼] |  ← entradas editáveis
| ⠿ numero_doc      | [180px▼] | [centro▼] |
| ⠿ especie         | [ 80px▼] | [esq   ▼] |
| ⠿ aceite          | [ 60px▼] | [centro▼] |
|                                      |
|                [+ Coluna]            |  ← adicionar nova coluna
|                                      |
| ⠿ = alça de arraste para reordenar  |
| × = botão remover (ao passar mouse) |
+--------------------------------------+
```

### 7.2 Wireframe: Ao passar mouse na coluna (remover visível)

```
| ⠿ numero_doc    | [180px▼] | [centro▼] | [×] |
                                            ↑ aparece ao passar mouse
```

### 7.3 Anotações (UX)

| Item | Anotação |
|------|----------|
| **Campo** | Somente leitura (texto). Editável apenas via binding/dados — não pelo inspetor |
| **Largura** | Entrada numérica com sufixo "px". Aceita `auto`. Mín: 20px |
| **Alinhamento** | Lista suspensa: esquerda, centro, direita. Padrão: esquerda |
| **Arraste** | Alça ⠿ visível sempre. Arraste: HTML5 Drag API. Espaço reservado: linha azul na posição destino |
| **Remover** | Botão × aparece ao passar mouse na linha. Sem confirmação (desfazer disponível) |
| **Adicionar** | Padrões: field='', width='auto', align='left'. Foco automático no campo "field" |
| **Acessibilidade** | Tabela: `role="grid"`. Arraste: `aria-grabbed`, `aria-dropeffect`. Remover: `aria-label="Remover coluna X"` |

---

## 8. Inventário de Componentes (Atomic Design)

### Novos Átomos
| Componente | Story | Descrição |
|-----------|-------|-----------|
| `OpacitySlider` | 14.6 | Controle deslizante 0-100% com rótulo e valor |
| `ColorSwatch` | 14.6 | Quadrado 20-24px com cor, clicável, aria-label |
| `InlineNumberInput` | 14.12 | Span→entrada alternável para edição inline de números |
| `DragHandle` | 14.8, 14.12 | Ícone ⠿ com manipuladores de evento de arraste |

### Novas Moléculas
| Componente | Story | Descrição |
|-----------|-------|-----------|
| `AlignmentToolbar` | 14.5 | 8 botões de alinhamento/distribuição, contextual |
| `BoxModelVisualization` | 14.12 | Diagrama box model com edição inline |
| `ColorPickerAdvanced` | 14.6 | Área de cor + matiz + opacidade + paleta + recentes |
| `ComputedStylesPanel` | 14.1 | Painel somente leitura de CSS computado do elemento |
| `LayerItem` | 14.8 | Item do painel de camadas: alça + tipo + nome + visibilidade |

### Novos Organismos
| Componente | Story | Descrição |
|-----------|-------|-----------|
| `LayerPanel` | 14.8 | Painel lateral com lista ordenável de camadas + grupos |
| `SplitView` | 14.1 | Container canvas+editor com alça de redimensionamento |

---

## 9. Guia de Espaçamento e Dimensões

```
Unidade base: 4px (consistente com design system existente)

Toolbar (14.5):
  - Botões: 28×28px (área de toque: 32×32 com preenchimento)
  - Espaço entre botões: 4px
  - Separadores entre grupos: 8px
  - Distância do bounding box: 8px

Painel de Camadas (14.8):
  - Altura do item: 32px
  - Recuo por nível: 16px (grupos)
  - Ícone tipo: 16×16px
  - Alça de arraste: 12×16px
  - Preenchimento horizontal: 8px

Seletor de Cores (14.6):
  - Amostra: 24×24px (principal), 20×20px (paleta/recentes)
  - Espaço entre amostras: 4px
  - Altura do controle: 8px (trilha), 16px (indicador)
  - Preenchimento interno: 12px

Box Model (14.12):
  - Largura total: 240px
  - Preenchimento interno entre camadas: 20px
  - Fonte valores: 11px monospace
  - Área de conteúdo: 80×40px mínimo

Visão Dividida (14.1):
  - Largura da alça: 4px (ao passar mouse: 8px)
  - Largura mín do painel: 30% do container
  - Divisão padrão: 50/50
```

---

## 10. Comportamento Responsivo

O editor é exclusivo para desktop (não responsivo). Canvas requer mouse e teclado.

**Ponto de quebra mínimo suportado:** 1280px de largura (barra lateral esquerda 240px + centro 800px + barra lateral direita 240px)

**Zoom do canvas:** Toolbar (14.5) e sobreposições escalam inversamente ao zoom para manter legibilidade.

---

## 11. Decisões de Design e Justificativas

| Decisão | Justificativa |
|---------|---------------|
| Toolbar ACIMA da seleção, não na barra lateral | Proximidade com o contexto de uso (lei de Fitts). Reduz distância do mouse entre seleção e ação |
| Box Model estilo Chrome DevTools | Modelo mental já existente para devs. Zero curva de aprendizado |
| Seletor de cores customizado em vez de biblioteca | InspectorColorPicker já existe — extensão incremental. Evita dependência nova para 1 componente |
| Painel de Camadas como aba (não modal) | Precisa ficar aberto durante manipulação do canvas. Aba permite alternar com Estrutura/Campos |
| Visão Dividida 50/50 padrão | Equilíbrio entre ver o canvas e ter espaço suficiente para editar CSS |
| Arrastar-para-reordenar nativo (HTML5) | Evita dependência de vuedraggable. Projeto já usa padrão similar em StructureTree |

---

*Criado por Uma (@ux-design-expert) — Epic 14 Wireframes de Baixa Fidelidade v1.1*

— Uma, desenhando com empatia 💝
