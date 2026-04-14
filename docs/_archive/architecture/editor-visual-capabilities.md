# Editor Visual Capabilities — Spec para 100% Fidelidade

**Versao:** 1.3
**Data:** 2026-03-22
**Autor:** @architect (Aria)
**Contexto:** Auditoria profunda baseada em reprodução de boleto bancário Bradesco + relatório Mongeral Aegon
**Referência:** `pipeline-redesign-v3.md` v3.18 (Seção 14: Gaps do Editor)

---

## 1. Objetivo

Documentar todas as capacidades visuais que o editor precisa ter para que o operador consiga atingir **100% de fidelidade** na reprodução de qualquer documento PDF como template HTML — incluindo documentos complexos como boletos bancários, notas fiscais, relatórios com tabelas aninhadas e formulários multi-seção.

**Premissa revisada (v1.1):** O pipeline atual (Stage 5) entrega ~40-50% de fidelidade porque **ignora 90% dos dados visuais** que os Stages 2-3 já extraem. Com o Stage 5 redesenhado (v3.16+), sobe para ~85-90%. O editor é a camada de refinamento que fecha os 10-15% restantes — mas precisa das features documentadas aqui para fazê-lo via UI, sem edição de código.

---

## 1.1 Diagnóstico Raiz — O Pipeline Descarta Dados Visuais

**Descoberta crítica:** O problema de fidelidade NÃO é primariamente do editor — é do **Stage 5 atual** que ignora dados visuais já extraídos.

### Dados Extraídos vs. Utilizados pelo Stage 5 Atual

```
STAGE 2 EXTRAI                          STAGE 5 USA?
─────────────────────────────────────────────────────
text_blocks[].font_name (ex: Helvetica)    ✗ Hardcoded "Arial"
text_blocks[].font_size (ex: 10.5pt)       ✗ Hardcoded "10pt"
text_blocks[].is_bold (span flags)         ✗ Ignorado
text_blocks[].is_italic (span flags)       ✗ Ignorado
text_blocks[].color (RGB int)              ✗ Hardcoded #000000
drawn_elements[].type (line/rect)          ✗ Ignorado completamente
drawn_elements[].fill_color (RGB)          ✗ Ignorado completamente
drawn_elements[].stroke_color (RGB)        ✗ Ignorado completamente
drawn_elements[].width (stroke width)      ✗ Ignorado completamente
pages[].width / height                     ✗ Hardcoded 794x1123 (A4)

STAGE 3 EXTRAI                          STAGE 5 USA?
─────────────────────────────────────────────────────
visual_regions[].header bbox               ✗ Hardcoded 144px
visual_regions[].footer bbox               ✗ Hardcoded 96px
document_trees (hierarquia semântica)      ✗ Usa field_mappings flat
grid_info.column_positions                 ✗ Ignorado completamente
```

### O que isso significa para o boleto Bradesco

| Elemento do Boleto | Dado já extraído no Stage 2/3 | Stage 5 faz | Resultado |
|--------------------|-------------------------------|-------------|-----------|
| Bordas do grid (linhas horizontais/verticais) | `drawn_elements[type=line]` com coordenadas exatas | Ignora | **Zero bordas no HTML** |
| Fundo cinza do header | `drawn_elements[type=rect, fill_color=#e0e0e0]` | Ignora | **Fundo branco** |
| Fonte Helvetica 9pt bold | `font_name=Helvetica, font_size=9, is_bold=true` | Arial 10pt | **Fonte errada, tamanho errado, peso errado** |
| Texto azul do link "Pagador" | `color` (RGB int do span) | #000000 | **Cor preta, perde destaque** |
| Tabela com 5 colunas | `document_trees[type=table]` | `is_table_cell → skip` | **Tabela inteira descartada** |
| Header real = 180px | `visual_regions[type=header].bbox` | 144px fixo | **Header cortado** |

### Impacto na estratégia

```
ANTES (premissa antiga):
  Pipeline → 80-90% → Editor fecha 10-20%
  Problema: editor precisa de MUITAS features novas

DEPOIS (diagnóstico real):
  Pipeline atual → 40-50% (ignora dados)
  Pipeline redesenhado (v3.16) → 85-90% (usa dados extraídos)
  Editor → fecha 10-15% restantes
  Problema: Stage 5 precisa ser implementado CORRETAMENTE
```

**Conclusão:** A maior alavanca para fidelidade é implementar o Stage 5 redesenhado (sub-steps 5.1 e 5.2 do v3.16), não adicionar features no editor. O editor complementa, não compensa.

---

## 1.2 Estratégia para 90% Automático + 10% via UI

### Camada 1 — Pipeline Stage 5 Redesenhado (0% → 85-90%)

O Stage 5 v3.16 já documenta como usar os dados extraídos. Implementar corretamente = 85-90% automático.

| Sub-step | O que faz | % Fidelidade |
|----------|-----------|--------------|
| **5.1 Tree-Driven HTML** | HTML hierárquico de `document_trees` (sections, `<table>` real, label-value pairs, condicionais) | +30% (estrutura) |
| **5.2 CSS-from-Extraction** | CSS dinâmico de fonts, cores, drawn_elements, visual_regions | +35% (visual) |
| **5.3 Coverage** | Multidimensional (fields 60% + tables 25% + images 15%) | feedback |
| **5.4 Overlay** | Items per-layout com hierarquia de tabelas (G22) | feedback |

**Detalhamento do 5.2 — CSS que deve ser gerado automaticamente:**

```python
def generate_css_from_extraction(enriched_docs, visual_analysis, drawn_elements):
    css_rules = []

    # ── 1. Fonts (de text_blocks) ──────────────────────────────
    # Cada combinação font_name+size+weight+style → classe CSS
    for block in all_text_blocks:
        cls = f".f-{hash(block.font_name, block.font_size)}"
        css_rules.append(f"""{cls} {{
            font-family: '{block.font_name}', sans-serif;
            font-size: {block.font_size}pt;
            {"font-weight: bold;" if block.is_bold else ""}
            {"font-style: italic;" if block.is_italic else ""}
        }}""")

    # ── 2. Cores de texto (de text_blocks[].color) ────────────
    for color_int in unique_colors:
        hex_val = f"#{color_int:06x}"
        css_rules.append(f".c-{hex_val[1:]} {{ color: {hex_val}; }}")

    # ── 3. Bordas (de drawn_elements[type=line]) ──────────────
    # Linhas horizontais/verticais → CSS border no elemento mais próximo
    for line in drawn_elements_lines:
        target = find_nearest_element(line.bbox, all_elements)
        side = detect_border_side(line, target)  # top/right/bottom/left
        width_px = max(1, round(line.width))
        color = f"#{line.stroke_color:06x}" if line.stroke_color else "#000"
        css_rules.append(
            f".el-{target.id} {{ border-{side}: {width_px}px solid {color}; }}"
        )

    # ── 4. Backgrounds (de drawn_elements[type=rect, fill_color]) ──
    for rect in drawn_elements_filled_rects:
        target = find_overlapping_section(rect.bbox, all_sections)
        fill = f"#{rect.fill_color:06x}"
        css_rules.append(f".sec-{target.id} {{ background-color: {fill}; }}")

    # ── 5. Zonas header/footer (de visual_regions) ─────────────
    for page_key, analysis in visual_analysis.items():
        for region in analysis.regions:
            height_px = round(region.bbox[3] - region.bbox[1])
            css_rules.append(f".{region.type} {{ height: {height_px}px; }}")

    # ── 6. Alinhamento de texto (análise posicional) ───────────
    for block in all_text_blocks:
        container = find_container(block, all_sections)
        if not container: continue
        align = detect_text_alignment(block, container)
        if align != "left":  # left é default
            css_rules.append(f".el-{block.id} {{ text-align: {align}; }}")

    # ── 7. Dimensões de página (de pages[].width/height) ──────
    page = enriched_docs[0].pages[0]
    css_rules.insert(0, f""".page {{
        width: {round(page.width)}px;
        height: {round(page.height)}px;
    }}""")

    return "\n".join(css_rules)


def detect_text_alignment(block, container):
    """Detecta alinhamento baseado na posição do texto vs container."""
    block_left = block.bbox[0]
    block_right = block.bbox[2]
    container_left = container.bbox[0]
    container_right = container.bbox[2]
    container_center = (container_left + container_right) / 2
    block_center = (block_left + block_right) / 2

    # Tolerância de 5px
    if abs(block_right - container_right) < 5:
        return "right"
    if abs(block_center - container_center) < 5:
        return "center"
    return "left"
```

### Camada 2 — AutoFix IA Pós-Pipeline (85% → 93-95%)

Após o Stage 5 gerar HTML+CSS, o AutoFix compara com o PDF original e sugere correções para o que ficou impreciso.

| Fix Type | Como detecta | O que corrige | % Ganho |
|----------|-------------|---------------|---------|
| `border-refine` | Compara drawn_elements com CSS borders gerados | Borda faltante ou com espessura errada | +2% |
| `background-refine` | Compara rects preenchidos com backgrounds gerados | Background não detectado ou cor ligeiramente off | +1% |
| `text-align` | Verifica alinhamento real vs gerado | Texto que deveria ser right/center mas ficou left | +1% |
| `spacing-refine` | Mede gaps entre elementos vs PDF original | Padding/margin 2-3px off | +1% |
| `font-fallback` | Detecta font substituída pelo browser | Sugere font mais próxima ou upload | +1% |
| `z-order` | Detecta overlaps visuais | Elemento atrás quando deveria estar na frente | +0.5% |

**Abordagem de comparação visual (futuro — Camada 2.5):**

```
1. Renderizar HTML gerado via Puppeteer → screenshot_html.png
2. Renderizar página do PDF → screenshot_pdf.png
3. Pixel diff (SSIM ou perceptual hash por região)
4. Regiões com divergência > 5% → gerar fix suggestions
5. Operador vê: "Região (x,y)-(w,h) diverge 12% — sugerir ajuste"
```

Isso eliminaria a necessidade de o AutoFix "adivinhar" o que está errado — ele VÊ a diferença.

### Camada 3 — Editor UI Manual (93-95% → 100%)

Os **5-7% restantes** são ajustes que requerem julgamento humano ou são edge cases que nenhuma automação resolve:

| Tipo de ajuste | Feature necessária | Por que não automatiza |
|---------------|-------------------|----------------------|
| Borda decorativa com estilo especial | F1 (Border Editor) | Borda dupla, pontilhada — decisão subjetiva |
| Espaçamento fino entre campos | F14 (Keyboard arrows) | 1-2px de preferência visual |
| Hierarquia de z-index complexa | F8 (Layer Panel) | Logo sobre barra sobre fundo — 3+ camadas |
| Tabela com células irregulares | F2 (Cell Borders) | Merge/split depende do contexto |
| CSS para propriedades sem UI | F5 (CSS Live Editor) | Escape hatch universal |
| Alinhamento perfeito multi-campo | F4 (Alignment Tools) | Selecionar 6 campos e distribuir uniformemente |

---

### 1.3 Mapa Completo de Propriedades CSS

Todas as propriedades CSS que um template HTML pode precisar, categorizadas por quem resolve.

| Propriedade CSS | Pipeline Auto (5.2) | AutoFix (Camada 2) | Editor UI | Hoje tem UI? |
|----------------|--------------------|--------------------|-----------|-------------|
| `font-family` | gera de text_blocks | refina se fallback | ElementInspector | SIM |
| `font-size` | gera de text_blocks | — | ElementInspector | SIM |
| `font-weight` | gera de is_bold | — | ElementInspector | SIM |
| `font-style` | gera de is_italic | — | **F9** | NAO |
| `color` | gera de text_color | — | InspectorColorPicker | SIM |
| `line-height` | gera proporcional | refina spacing | ElementInspector | SIM |
| `letter-spacing` | — | detecta se necessário | ElementInspector | SIM |
| `text-align` | gera de posição | refina | **F3** | NAO |
| `text-decoration` | — | — | **F9** | NAO |
| `text-transform` | — | detecta UPPERCASE | **F9** | NAO |
| `white-space` | gera (nowrap/normal) | — | **F5** (CSS) | NAO |
| `word-break` | — | — | **F5** (CSS) | NAO |
| `vertical-align` | — | — | **F3** | NAO |
| `position` | gera (absolute) | refina | ElementInspector | SIM |
| `top/left` | gera de bbox | refina | ElementInspector | SIM |
| `width/height` | gera de bbox | refina | ElementInspector | SIM |
| `padding` (elemento) | — | refina | **F11** | NAO |
| `padding` (seção) | gera para sections | refina | SectionInspector | SIM |
| `border` (all) | **gera de drawn_elements** | refina | **F1** | NAO |
| `border-radius` | — | — | **F1** | NAO |
| `border-collapse` | gera para tables | — | **F2** | NAO |
| `background-color` | **gera de filled rects** | refina | **F6** / SectionInsp | PARCIAL |
| `background-image` | — | — | SectionInspector | SIM (seções) |
| `background-gradient` | — | — | **F5** (CSS) | NAO |
| `opacity` | — | — | **M1** (ColorPicker) | NAO |
| `box-shadow` | — | — | **F5** (CSS) | NAO |
| `z-index` | gera de overlap | refina | **F8** | NAO |
| `overflow` | gera (hidden/visible) | — | **F5** (CSS) | NAO |
| `display` | gera (block/flex) | — | **F5** (CSS) | NAO |
| `transform` | — | — | **F5** (CSS) | NAO |
| `@font-face` | **gera de fonts embarcadas no PDF** | — | — | N/A (gerado) |
| `text-overflow` | gera (ellipsis para cells) | — | **F5** (CSS) | NAO |
| `page-break-before/after` | gera para sections | — | SectionInspector | PARCIAL |
| `@media print` | gera base | — | **F5** (CSS) | NAO |

### 1.4 Propriedades que NENHUMA camada resolve hoje

Estas são propriedades CSS que o boleto pode precisar e que **nenhuma das 3 camadas** (Pipeline, AutoFix, Editor UI) consegue resolver:

| Propriedade | Exemplo no boleto | Resolução proposta |
|------------|-------------------|-------------------|
| `border-style: double` | "Ficha de Compensação" | F1 (Border Editor) com opção double |
| `background: linear-gradient(...)` | Header com degradê sutil | F5 (CSS Live Editor) |
| `box-shadow` | Sombra no card do boleto (raro) | F5 (CSS Live Editor) |
| `text-indent` | Parágrafo de instruções | F5 (CSS Live Editor) |
| `list-style` | Marcadores em instruções | F5 (CSS Live Editor) |
| `word-spacing` | Espaçamento na linha digitável | F5 (CSS Live Editor) |

**Conclusão:** F5 (CSS Live Editor) é o **escape hatch universal** — qualquer propriedade sem UI dedicada pode ser ajustada por lá. É a feature mais importante para os 10% manuais.

---

## 2. Estado Atual — Capacidades Existentes

### 2.1 Posicionamento & Canvas

| Capacidade | Status | Componente |
|-----------|--------|------------|
| Posição absoluta (x, y) | OK | `ElementInspector.vue` |
| Dimensões (width, height) | OK | `ElementInspector.vue` |
| Drag & drop no canvas | OK | `useCanvasInteraction.ts` |
| Resize com 8 handles | OK | `useCanvasInteraction.ts` |
| Snap to grid (8/16/24px) | OK | `editorStore.ts` |
| Multi-select (Ctrl/Shift+Click) | OK | `useCanvasInteraction.ts` |
| Hierarchy popup (elementos sobrepostos) | OK | `useCanvasInteraction.ts` |
| Canvas guides (margens, zonas) | OK | `CanvasGuides.vue` |
| Zoom controls | OK | `useZoom` composable |

### 2.2 Tipografia

| Capacidade | Status | Componente |
|-----------|--------|------------|
| Font family | OK | `ElementInspector.vue` |
| Font size | OK | `ElementInspector.vue` |
| Font weight | OK | `ElementInspector.vue` |
| Font color | OK | `InspectorColorPicker.vue` |
| Line height | OK | `ElementInspector.vue` |
| Letter spacing | OK | `ElementInspector.vue` |
| Font cascade (3 níveis) | OK | `useFontCascade.ts` |
| Font upload (fontes faltantes) | OK | `FontWarning.vue` |

### 2.3 Seções

| Capacidade | Status | Componente |
|-----------|--------|------------|
| Background color | OK | `SectionInspector.vue` |
| Background image upload | OK | `SectionInspector.vue` |
| Padding (top/bottom/left/right) | OK | `SectionInspector.vue` |
| Height | OK | `SectionInspector.vue` |
| Repeat per page | OK | `SectionInspector.vue` |
| Visibility (conditional) | OK | `VisibilityControl.vue` |

### 2.4 Imagens

| Capacidade | Status | Componente |
|-----------|--------|------------|
| Image upload/replace | OK | `ImageInspector.vue` |
| Asset gallery | OK | `ImageInspector.vue` |
| SVG inline + sanitização | OK | `ImageInspector.vue` |
| Dimensões + scale | OK | `ImageInspector.vue` |
| Alinhamento (left/center/right) | OK | `ImageInspector.vue` |
| Download | OK | `ImageInspector.vue` |

### 2.5 Tabelas

| Capacidade | Status | Componente |
|-----------|--------|------------|
| Visualização de colunas | OK (read-only) | `TableInspector.vue` |
| Row height / padding | OK | `TableInspector.vue` |
| Page break | OK | `TableInspector.vue` |
| Repeat header | OK | `TableInspector.vue` |
| Keep together | OK | `TableInspector.vue` |

### 2.6 AutoFix (IA)

| Capacidade | Status | Componente |
|-----------|--------|------------|
| Fix: spacing | OK | `autoFixStore.ts` |
| Fix: alignment | OK | `autoFixStore.ts` |
| Fix: font | OK | `autoFixStore.ts` |
| Fix: binding | OK | `autoFixStore.ts` |
| Fix: position | OK | `autoFixStore.ts` |
| Workflow accept/reject/skip | OK | `AutoFixPanel.vue` |
| Undo integration | OK | `templateStore.pushUndoSnapshot()` |

### 2.7 Outros

| Capacidade | Status | Componente |
|-----------|--------|------------|
| Conditional styling (rules) | OK | `ConditionalStyleSection.vue` |
| Coverage mode toggle | OK | `editorStore.ts` |
| Diff mode toggle | OK | `editorStore.ts` |
| Document type detection badge | OK | Story 12.8 |
| Multi-layout switch | OK | Story 12.9 |
| Undo/Redo (20 snapshots) | OK | `templateStore.ts` |

---

## 3. Features Ausentes — Classificadas por Impacto

### Severidade: CRITICO

Sem estas features, o operador **não consegue** reproduzir documentos com grids, bordas e tabelas complexas (como boletos). Fica bloqueado e precisa editar HTML/CSS manualmente.

---

#### F1 — Editor de Bordas (Border Editor)

**Problema:** O editor não tem NENHUM controle de bordas. Boletos são ~90% bordas — retângulos, separadores, grids com bordas de espessuras diferentes. O operador não consegue adicionar, remover ou ajustar bordas em nenhum elemento.

**O que falta:**
- `border-width` (top/right/bottom/left independente)
- `border-color` (por lado)
- `border-style` (solid, dashed, dotted, double, none)
- `border-radius` (cantos arredondados)
- Shorthand visual (all sides / per side toggle)

**Onde implementar:** Nova seção "Borders" no `ElementInspector.vue` e `SectionInspector.vue`

**Exemplo no boleto:** Cada célula do grid "Recibo do Sacado" tem bordas grossas em cima/baixo e finas nos lados. A seção "Ficha de Compensação" tem borda dupla.

**Prioridade:** CRITICA — bloqueia reprodução de qualquer documento com grids/tabelas visuais

---

#### F2 — Borda per-célula em Tabelas (Table Cell Borders)

**Problema:** `TableInspector.vue` mostra colunas como read-only. Não há controle de bordas por célula — essencial para tabelas onde cada célula pode ter estilo diferente.

**O que falta:**
- Seleção de célula individual na tabela
- Border por célula (top/right/bottom/left)
- `border-collapse` toggle
- Background color por célula
- Padding por célula

**Onde implementar:** Expandir `TableInspector.vue` com `TableCellEditor` sub-component

**Exemplo no boleto:** Tabela do corpo com "Beneficiário" (borda grossa embaixo), "Agência/Cód" (borda fina), "Valor" (borda grossa + fundo cinza claro no header)

**Prioridade:** CRITICA — bloqueia reprodução de tabelas estilizadas (boletos, notas fiscais)

---

#### F3 — Alinhamento de Texto (Text Alignment)

**Problema:** `ElementInspector.vue` não tem controle de `text-align`. Valores numéricos precisam de right-align, labels de left-align, títulos de center. O operador não consegue mudar o alinhamento.

**O que falta:**
- `text-align`: left | center | right | justify
- `vertical-align`: top | middle | bottom (para células de tabela)
- UI: grupo de 4 botões com ícones (alinhamento horizontal)

**Onde implementar:** Seção "Typography" do `ElementInspector.vue`, após font controls

**Exemplo no boleto:** Coluna "Valor Documento" = right-align (4.978,54), "Beneficiário" = left-align, "237" = center

**Prioridade:** CRITICA — afeta legibilidade e fidelidade de todos os documentos com dados tabulares

---

#### F4 — Ferramentas de Alinhamento Visual (Alignment Tools)

**Problema:** Multi-select existe mas não há botões para alinhar elementos selecionados entre si. O operador precisa ajustar x/y manualmente para cada campo.

**O que falta:**
- Align left / center / right (horizontal)
- Align top / middle / bottom (vertical)
- Distribute horizontally / vertically (espaçamento uniforme)
- UI: toolbar de alinhamento (aparece quando 2+ elementos selecionados)

**Onde implementar:** Nova toolbar contextual + funções em `useCanvasInteraction.ts`

**Exemplo no boleto:** As 3 colunas "Data Emissão | Número do Documento | Espécie" precisam estar perfeitamente alinhadas horizontalmente e com espaçamento uniforme

**Prioridade:** CRITICA — sem isso, alinhar campos em grids é extremamente tedioso (minutos em vez de segundos)

---

#### F5 — Editor CSS Live (Live CSS Editor)

**Problema:** O Code Tab existe mas é **read-only**. Para ajustes finos de 1-2px, bordas específicas, ou qualquer propriedade CSS não exposta nos inspectors, o operador não tem escape hatch.

**O que falta:**
- Editor CSS editável (Monaco ou CodeMirror)
- Live preview: mudanças no CSS refletem imediatamente no canvas
- Syntax highlighting + autocomplete CSS
- Validação em tempo real (erros de syntax)
- Separação: CSS global (template) vs CSS inline (elemento)

**Onde implementar:** Expandir Code Tab no `CenterPanel` + `codeStore.ts`

**Exemplo no boleto:** Ajuste fino de `border-spacing: 0; border-collapse: collapse;` na tabela do grid, ou `background: linear-gradient(...)` que não tem UI dedicada

**Prioridade:** CRITICA — é o "escape hatch" universal. Qualquer propriedade CSS que não tem UI dedicada pode ser ajustada aqui

---

### Severidade: ALTA

Sem estas features, o operador chega a ~90% mas **nunca a 100%** sem edição de código. A produtividade também é significativamente impactada.

---

#### F6 — Background Color por Elemento

**Problema:** `SectionInspector.vue` tem background color, mas `ElementInspector.vue` não. Campos individuais que precisam de fundo colorido (headers de tabela, destaques) não podem ser estilizados.

**O que falta:**
- `background-color` no ElementInspector
- `background-color` por célula de tabela (ver F2)
- Opcionalidade de `transparent` / `inherit`

**Onde implementar:** Seção "Appearance" no `ElementInspector.vue`

**Exemplo no boleto:** Header "RECIBO DO SACADO" pode ter fundo cinza claro. Linha de "Instruções" tem fundo diferenciado.

**Prioridade:** ALTA

---

#### F7 — Multi-Select + Group/Ungroup

**Problema:** Multi-select já funciona para drag, mas não há conceito de "grupo". Elementos agrupados deveriam se mover/redimensionar juntos e ter operações em batch.

**O que falta:**
- Group: combinar elementos selecionados em um grupo lógico
- Ungroup: desfazer grupo
- Grupo herda operações de move/resize (todos os filhos se movem proporcionalmente)
- Operações batch: aplicar mesma propriedade (cor, fonte, alinhamento) a todos no grupo

**Onde implementar:** `templateStore.ts` (modelo de dados de grupo) + `useCanvasInteraction.ts` (interação)

**Exemplo no boleto:** As 6 células "Data Documento / Número / Espécie / Aceite / Data Processamento / Valor" formam um grupo lógico — ajustar uma célula deveria permitir ajustar todas proporcionalmente

**Prioridade:** ALTA — multiplica produtividade por 3-5x em documentos com muitos campos

---

#### F8 — Z-Index Visual (Layer Panel)

**Problema:** `ElementInspector.vue` tem um campo "layer" (string) mas não há painel visual de camadas. Não há botões "bring to front" / "send to back". Quando elementos se sobrepõem (texto sobre background, logo sobre barra), o operador não consegue controlar a ordem.

**O que falta:**
- Layer panel: lista ordenável de todos os elementos por z-index
- Drag-to-reorder no layer panel
- Botões: Bring to Front / Send to Back / Move Up / Move Down
- Visual feedback de camada selecionada no canvas

**Onde implementar:** Novo componente `LayerPanel.vue` no left sidebar + z-index tracking no `templateStore.ts`

**Exemplo no boleto:** Logo Bradesco precisa ficar sobre a barra separadora. Número "237" precisa ficar sobre o fundo da célula.

**Prioridade:** ALTA

---

#### F9 — Text Decoration & Transform

**Problema:** `ElementInspector.vue` não tem controles de decoração de texto. Títulos em bold/underline, labels em uppercase — o operador não consegue ajustar sem CSS direto.

**O que falta:**
- `text-decoration`: underline | overline | line-through | none
- `text-transform`: uppercase | lowercase | capitalize | none
- `font-style`: normal | italic
- UI: botões toggle na seção Typography (B, I, U, Aa)

**Onde implementar:** Seção "Typography" do `ElementInspector.vue`

**Exemplo no boleto:** "RECIBO DO SACADO" em uppercase bold, "Instruções" em bold, "Código do Órgão" em normal

**Prioridade:** ALTA

---

#### F10 — Snap Lines Visuais (Smart Guides)

**Problema:** A infraestrutura de snap lines existe em `useCanvasInteraction.ts` (tipo `SnapLine[]`, threshold 8px, cálculo de edges), mas as linhas **não são renderizadas no DOM**. O operador faz snap magnético "cego" — sente o snap mas não vê.

**O que falta:**
- Componente `SnapLineOverlay.vue` que renderiza linhas durante drag/resize
- Linhas horizontais/verticais coloridas (magenta, como Figma/Photoshop)
- Labels de distância entre elementos (px display)
- Desaparecem quando drag termina

**Onde implementar:** `SnapLineOverlay.vue` sobre o canvas + emitir snap lines do `useCanvasInteraction.ts`

**Prioridade:** ALTA — diferença entre "ajuste profissional" e "trial and error"

---

### Severidade: MEDIA

Melhoram significativamente a produtividade do operador mas não bloqueiam a fidelidade (operador pode contornar com mais esforço).

---

#### F11 — Padding por Elemento

**Problema:** Só existe padding em sections. Elementos individuais (campos de texto, labels) não têm controle de padding interno. Quando o texto fica "colado" na borda do elemento, o operador precisa ajustar posição/tamanho manualmente em vez de simplesmente adicionar padding.

**Nota:** `margin` não se aplica porque todos os elementos usam `position: absolute`. O espaçamento entre elementos é controlado por `top`/`left`. O que falta é **padding interno** ao elemento.

**Onde implementar:** Seção "Spacing" no `ElementInspector.vue` (padding top/right/bottom/left)

**Prioridade:** MEDIA

---

#### F12 — AutoFix: Novos Fix Types (Refinamento Visual)

**Problema:** AutoFix tem 5 tipos (spacing, alignment, font, binding, position). Com o Stage 5 redesenhado, bordas/backgrounds/alinhamento serão gerados automaticamente — mas podem ficar imprecisos. O AutoFix precisa de tipos de **refinamento** para corrigir o que o pipeline gerou parcialmente.

**O que falta:**
- Fix type `border-refine`: comparar drawn_elements do PDF com CSS borders gerados pelo 5.2 → corrigir borda faltante, espessura errada, cor off
- Fix type `background-refine`: comparar rects preenchidos com backgrounds gerados → corrigir cor ligeiramente diferente ou background não detectado
- Fix type `text-align`: verificar alinhamento real (posição x do texto) vs alinhamento CSS gerado → corrigir right/center que ficou left
- Fix type `z-order`: detectar sobreposições visuais não resolvidas pelo pipeline → sugerir z-index

**Nota:** Estes tipos **refinam** o que o Stage 5.2 já gerou, não criam do zero. Se o Stage 5.2 não gerar bordas (implementação incompleta), estes tipos assumem papel de criação.

**Impacto:** Automatiza 60-70% dos ajustes residuais pós-pipeline

**Onde implementar:** Backend `/api/auto-fix` + `autoFixStore.ts` fix types

**Prioridade:** MEDIA — depende de F1/F3/F6 existirem primeiro para que o operador possa aceitar/editar as sugestões

---

#### F13 — AutoFix: Batch Accept

**Problema:** Operador deve aceitar/rejeitar cada sugestão individualmente. Para templates com 50+ campos e múltiplas sugestões, o fluxo é lento.

**O que falta:**
- Botão "Accept All" (aceitar todas as sugestões pendentes)
- Botão "Accept All of Type" (aceitar todas as sugestões de um tipo, ex: todas de spacing)
- Confidence display por sugestão (score numérico)
- Preview antes de batch accept

**Onde implementar:** `AutoFixPanel.vue` + `autoFixStore.ts`

**Prioridade:** MEDIA

---

#### F14 — Keyboard Shortcuts para Posicionamento

**Problema:** Ajustar posição/tamanho requer usar o Inspector ou drag. Para ajustes finos de 1px, o operador precisa digitar valores. Arrow keys deveriam mover o elemento selecionado.

**O que falta:**
- Arrow keys: mover 1px
- Shift+Arrow: mover 10px (ou grid size)
- Alt+Arrow: resize 1px
- Ctrl+D: duplicar elemento selecionado
- Delete: remover elemento selecionado

**Onde implementar:** Key event handlers no canvas wrapper

**Prioridade:** MEDIA

---

#### F15 — Copy/Paste de Elementos

**Problema:** Não há como duplicar um elemento. Para criar campos similares (mesma fonte, mesma borda, mesma cor), o operador precisa criar do zero e configurar cada propriedade.

**O que falta:**
- Ctrl+C / Ctrl+V: copiar/colar elemento com todas as propriedades
- Ctrl+D: duplicate in place (com offset de 10px)
- Paste herda todas as propriedades CSS do original
- Suporte a copiar múltiplos elementos (com multi-select)

**Onde implementar:** `useCanvasInteraction.ts` + `templateStore.ts` (clone node)

**Prioridade:** MEDIA

---

## 4. Melhorias em Features Existentes

Capacidades que já existem mas precisam de melhorias para suportar fidelidade total.

| # | Feature Atual | Problema | Melhoria Proposta | Impacto |
|---|--------------|----------|-------------------|---------|
| M1 | **ColorPicker** (HTML5 input) | Sem alpha/opacity, sem presets | Adicionar opacity slider (rgba), paleta de cores do documento (extraídas do PDF), presets recentes | ALTO |
| M2 | **AutoFix limit** (3 runs) | Insuficiente para templates complexos (~50+ campos) | Tornar configurável via env var `VITE_AUTOFIX_LIMIT`, default 5 | BAIXO |
| M3 | **Table Inspector** (read-only columns) | Colunas não editáveis, sem adicionar/remover | Permitir edição de width, align por coluna. Adicionar/remover colunas. Reordenar via drag | ALTO |
| M4 | **Element Inspector** | Falta seção "Box Model" | Adicionar visualização Box Model (margin/border/padding) como Chrome DevTools | MEDIO |
| ~~M5~~ | ~~Code Tab~~ | — | Coberto por F5 (CSS Live Editor) | — |
| ~~M6~~ | ~~Snap Lines~~ | — | Coberto por F10 (Snap Lines Visuais) | — |
| M7 | **ConditionalStyle** (4 propriedades) | Só suporta color, background, visibility, image | Adicionar border-color, font-weight, text-decoration, opacity | MEDIO |
| M8 | **AutoFix confidence** | Score existe no backend mas não exibido | Mostrar score de confiança por sugestão no `AutoFixPanel.vue` | BAIXO |

---

## 5. Gaps do Editor Consolidados (da Seção 14 do pipeline-redesign-v3.md)

Estes 3 gaps foram identificados na análise de riscos cruzada Pipeline↔Editor. Consolidados aqui como parte da spec completa.

### Gap A — Validação de bindings condicionais `<!-- ko if/foreach -->` (ALTA)

**Problema:** `usePreExportValidation.ts` valida `data-bind="text: campo"` contra o XSD, mas **não valida** comentários Knockout.js:
- `<!-- ko if: secao_xyz -->` — não verifica se `secao_xyz` existe no modelo de dados
- `<!-- ko foreach: items -->` — não verifica se `items` é um array no XSD

Se o Stage 5.1 gerar um binding condicional com nome inválido, o template exporta sem erro mas **quebra em runtime** no Planet Express. Silent failure.

**Validações atuais do pre-export (6 checks):**
1. `##TEMPLATE_DATA##` presente no HTML
2. `ko.applyBindings` presente no JS
3. `data-bind` fields existem no XSD
4. HTML well-formed (DOMParser)
5. CSS syntax válida (braces match)
6. Library refs existem no catálogo

**Validações faltantes:**
7. `<!-- ko if: X -->` — X existe no modelo de dados
8. `<!-- ko foreach: X -->` — X é array no XSD

**Solução:**

```typescript
// usePreExportValidation.ts — novo check AC7
const koCommentRe = /<!--\s*ko\s+(if|foreach|with|ifnot)\s*:\s*([\w.$]+)\s*-->/g
let koMatch: RegExpExecArray | null
while ((koMatch = koCommentRe.exec(html)) !== null) {
  const bindingType = koMatch[1]
  const fieldRef = koMatch[2]
  if (koBuiltins.has(fieldRef)) continue
  if (fieldRef.startsWith('$')) continue
  const found = [...knownPaths].some(
    (p) => p === fieldRef || p.endsWith(`.${fieldRef}`) || p.endsWith(`/${fieldRef}`)
  )
  if (!found) {
    errors.push({
      code: 'KO_COMMENT_FIELD_NOT_FOUND',
      message: `Binding "${bindingType}: ${fieldRef}" em comentário ko não encontrado no XSD`,
      blocking: true,
    })
  }
}
```

**Quando:** Junto com Stage 5 — antes de qualquer template ser exportado.

---

### Gap B — VisibilityControl desconectado do multiDocStore (MEDIA)

**Problema:** Operador muda visibilidade (Always → Conditional) no `VisibilityControl.vue`, mas multiDocStore não é notificado. DiffViewer e VariationMatrix não atualizam.

**Fluxo quebrado:**
```
VisibilityControl (templateStore)  ←→  multiDocStore (variações)
                  NÃO CONECTADO
```

**Solução:**

```typescript
// VisibilityControl.vue — onModeChange
watch(() => props.visibility?.mode, (newMode, oldMode) => {
  if (newMode === 'conditional' && oldMode !== 'conditional') {
    const multiDocStore = useMultiDocStore()
    multiDocStore.addDetection({
      type: 'optional',
      description: `Seção "${nodeLabel}" marcada como condicional pelo operador`,
      confidence: 1.0,
    })
  }
})
```

**Quando:** Story do editor — não bloqueia Stage 5.

---

### Gap C — AutoFix limite de 3 runs por sessão (BAIXA)

**Problema:** `SESSION_RUN_LIMIT = 3` em `autoFixStore.ts`. Para templates complexos, 3 runs não cobrem todas as correções.

**Solução:**

```typescript
const SESSION_RUN_LIMIT = parseInt(
  import.meta.env.VITE_AUTOFIX_LIMIT ?? '5', 10
)
```

**Quando:** Trivial — pode ser feito a qualquer momento.

---

## 6. AutoFix IA — Evolução Proposta

**Referência:** Esta seção detalha a implementação da **Camada 2** descrita na Seção 1.2. Os fix types aqui documentados são de **refinamento** — o Stage 5.2 gera a primeira versão do CSS, e o AutoFix compara com o PDF original para sugerir correções.

### 6.1 Fix Types Atuais vs Propostos

```
ATUAL (5 tipos):
  spacing | alignment | font | binding | position

PROPOSTO (9 tipos — 4 novos de refinamento):
  spacing | alignment | font | binding | position
  border-refine | background-refine | text-align | z-order
```

### 6.2 Como os Novos Fix Types Funcionam

| Fix Type | O que compara | O que corrige | Dependência UI |
|----------|-------------|---------------|----------------|
| `border-refine` | `drawn_elements` do PDF vs CSS `border` gerado pelo 5.2 | Borda faltante, espessura errada, cor off, estilo wrong (solid vs dashed) | F1 (Border Editor) |
| `background-refine` | Rects preenchidos do PDF vs `background-color` gerado | Background não detectado, cor ligeiramente diferente | F6 (Background) |
| `text-align` | Posição x do texto no PDF vs `text-align` gerado | Texto right/center que ficou left (tolerância 5px) | F3 (Text Alignment) |
| `z-order` | Overlap de elementos posicionados vs z-index gerado | Elemento atrás quando deveria estar na frente | F8 (Layer Panel) |

### 6.3 Comparação Visual (Camada 2.5)

**Conceito:** Após gerar o template HTML, renderizar como imagem e comparar pixel-a-pixel com o PDF original. Destacar regiões com divergência > threshold.

```
1. Renderizar HTML gerado via Puppeteer → screenshot_html.png
2. Renderizar página do PDF → screenshot_pdf.png
3. Pixel diff (SSIM ou perceptual hash por região)
4. Regiões com divergência > 5% → gerar fix suggestions
5. Operador vê: "Região (x,y)-(w,h) diverge 12% — sugerir ajuste"
```

**Potencial:** Esta é a abordagem mais poderosa — elimina a necessidade de o AutoFix "adivinhar" o que está errado. Ele VÊ a diferença.

**Depende de:** Rendering engine server-side (Puppeteer/Playwright) + image diffing library (pixelmatch ou SSIM).
**Prioridade:** Wave 4 — após features do editor estarem implementadas.

---

## 7. Matriz de Priorização

### 7.1 Por Impacto na Fidelidade

| Ordem | Feature | Severidade | O que Desbloqueia | Estimativa |
|-------|---------|-----------|-------------------|------------|
| 1 | **F1** Border Editor | CRITICO | Reprodução de qualquer documento com grids/bordas | M |
| 2 | **F3** Text Alignment | CRITICO | Formatação correta de valores e labels | S |
| 3 | **F5** CSS Live Editor | CRITICO | Escape hatch universal para qualquer ajuste | M |
| 4 | **F6** Background Color (elemento) | ALTO | Headers coloridos, destaques, zebra-striping | S |
| 5 | **F2** Table Cell Borders | CRITICO | Tabelas complexas com bordas diferenciadas | L |
| 6 | **F4** Alignment Tools | CRITICO | Organização rápida de campos em grids | M |
| 7 | **F9** Text Decoration/Transform | ALTO | Bold, italic, underline, uppercase | S |
| 8 | **F10** Snap Lines Visuais | ALTO | Feedback visual de alinhamento durante drag | S |
| 9 | **F8** Z-Index / Layer Panel | ALTO | Controle de sobreposição de elementos | M |
| 10 | **F7** Group/Ungroup | ALTO | Produtividade 3-5x em batch operations | M |
| 11 | **Gap A** KO Comment Validation | ALTO | Prevenir silent failures em runtime | S |
| 12 | **F12** AutoFix novos tipos | MEDIO | Automação de 60-70% dos ajustes manuais | L |
| 13 | **F14** Keyboard Shortcuts | MEDIO | Ajuste fino de 1px, produtividade | S |
| 14 | **F15** Copy/Paste elementos | MEDIO | Duplicação rápida de campos similares | S |
| 15 | **F13** AutoFix Batch Accept | MEDIO | Velocidade de aceitação de sugestões | S |
| 16 | **F11** Padding por elemento | MEDIO | Espaçamento interno em campos/labels | S |
| 17 | **Gap B** Visibility↔multiDoc | MEDIO | Sync entre operador e variações | S |
| 18 | **Gap C** AutoFix limit 3→5 | BAIXO | Mais runs de auto-correção | XS |

**Legenda estimativa:** XS (<2h), S (2-8h), M (1-3 dias), L (3-5 dias)

### 7.2 Ondas de Implementação — Estratégia Revisada (3 Camadas)

A prioridade mudou: o **Stage 5 correto** é a maior alavanca, não as features do editor.

**Pre-Wave — Stage 5 Redesenhado (PRIORIDADE MAXIMA)**
- Implementar sub-steps 5.1 (Tree-Driven HTML) e 5.2 (CSS-from-Extraction)
- Usar TODOS os dados que os Stages 2-3 já extraem
- Resultado: 85-90% de fidelidade automática SEM nenhuma feature nova no editor
- Estimativa: incluído no epic de implementação do pipeline

**Wave 1 — Escape Hatch + Essenciais (F5 + F1 + F3)**
- F5 (CSS Live Editor) — desbloqueia 100% via código, escape universal
- F1 (Border Editor) — bordas são o ajuste visual mais comum
- F3 (Text Alignment) — alinhamento de valores e labels
- Resultado: operador chega a 100% com esforço razoável
- Estimativa: ~6-8 dias
- **Nota:** F2 e F4 também são CRITICO mas ficam na Wave 2 porque F5 (CSS Live Editor) serve como escape hatch temporário para table cell borders e alinhamento multi-campo. Wave 1 prioriza o desbloqueio imediato.

**Wave 2 — Tabelas & Produtividade (F2 + F4 + F6 + F9)**
- F2 (Table Cell Borders) — tabelas complexas (CRITICO, desbloqueado temporariamente por F5)
- F4 (Alignment Tools) — alinhar campos rapidamente (CRITICO, desbloqueado temporariamente por F5)
- F6 (Background por elemento) — headers coloridos
- F9 (Text Decoration) — bold, italic, underline
- Resultado: operador chega a 100% em metade do tempo (sem depender de CSS direto)
- Estimativa: ~8-10 dias

**Wave 3 — Refinamento (F10 + F8 + F7 + F14 + F15 + Gaps A/B/C)**
- Snap lines visuais, layer panel, groups, keyboard shortcuts, copy/paste
- Resultado: experiência profissional de edição
- Estimativa: ~8-10 dias

**Wave 4 — Automação IA (F12 + F13 + M1-M8 + Comparação Visual)**
- Novos fix types, batch accept, comparação pixel-a-pixel
- Resultado: 93-95% automático, operador só ajusta 5-7%
- Estimativa: ~8-12 dias

### 7.3 Projeção de Fidelidade por Camada

```
                    ┌──────────────────────────────────────────┐
100% ──────────────►│                Wave 3+4 (UI + AutoFix)   │ ← operador ajusta 5%
 95% ──────────────►│           Wave 1+2 (Editor essenciais)   │ ← operador ajusta 10%
 90% ──────────────►│      AutoFix IA (Camada 2)               │ ← automático
 85% ──────────────►│  Stage 5 Redesenhado (Camada 1)          │ ← automático
                    │                                          │
 45% ──────────────►│  Stage 5 ATUAL (hardcoded)               │ ← onde estamos hoje
                    └──────────────────────────────────────────┘
```

---

## 8. Documento de Referência — Boleto Bancário Analisado

O documento usado como base para esta auditoria é um boleto bancário Bradesco + relatório Mongeral Aegon (2 páginas).

### Elementos visuais identificados e features necessárias:

| Elemento do Boleto | Feature Necessária |
|--------------------|--------------------|
| Grid "Recibo do Sacado" com bordas mistas | F1 (bordas), F2 (per-cell) |
| Valores à direita (4.978,54) | F3 (text-align: right) |
| 3 colunas "Data/Número/Espécie" alinhadas | F4 (alignment tools) |
| Header com fundo cinza | F6 (background element) |
| "RECIBO DO SACADO" bold uppercase | F9 (text-decoration/transform) |
| Logo Bradesco sobre barra | F8 (z-index) |
| Número "237" grande centralizado | F3 (text-align: center) |
| Bordas duplas na "Ficha de Compensação" | F1 (border-style: double) |
| Instruções: bloco denso com borda | F1 (border) + F6 (background) |
| Barcode posicionado precisamente | F14 (keyboard fine-tuning) |
| Tabela Mongeral (5 colunas simples) | F2 (column borders), F3 (align) |
| Espaçamento uniforme entre campos | F4 (distribute) |

---

## 9. Mapeamento Pipeline → Telas Impactadas

O pipeline redesenhado (v3.18) introduz pontos de interação que precisam de UI nova ou validação de UI existente.

### 9.1 Telas Novas (precisam de @ux)

| Ponto do Pipeline | Tela necessária | Descrição |
|-------------------|----------------|-----------|
| Homogeneity Check (Stage 1.16) | Modal "PDF incompatível" | Operador vê quais PDFs foram detectados como template diferente e decide: remover ou manter. Checkpoint SSE com timeout |
| Overlay hierárquico de tabelas (G22) | CoverageOverlay atualizado | Container da tabela com borda sólida + cells individuais com hover-only. Precisa de interação diferente do overlay de campos |
| AutoFix novos fix types (F12) | AutoFixPanel expandido | Sugestões de border/background/text-align com preview visual antes de aceitar. Diferente dos fix types atuais (texto) |

### 9.2 Telas Existentes que Precisam Validar com Dados Novos

| Tela | O que muda | Precisa UX? |
|------|-----------|-------------|
| ConfidencePanel | Scores agora são 0-100 (eram 0-1 nos fatores). Thresholds inalterados | NAO — só muda escala |
| CoverageOverlay | Coverage multidimensional (fields 60% + tables 25% + images 15%). Hoje tables/images = 0 | TALVEZ — barra de progresso precisa mostrar breakdown |
| Layout Selector | Cada layout agora tem estado embarcado (documentTree, confidence, coverage) | NAO — Story 12.9 já funciona |
| DiffViewer / VariationMatrix | multi_doc agora vem do pipeline (antes era mock) | NAO — Epic 11 já suporta |
| generationStore | template_draft monolítico (layout ativo) | NAO — já aceita {html, css} |

### 9.3 Matriz: Quais Stories Precisam de @ux?

| Story | UI novo? | @ux? | Motivo |
|-------|---------|------|--------|
| **F1** Border Editor | SIM | SIM | Componente novo: 4 lados, estilos, cores, radius |
| **F2** Table Cell Editor | SIM | SIM | Seleção de célula + painel de bordas per-cell |
| **F3** Text Alignment | NAO | NAO | 4 botões padrão (L/C/R/J) |
| **F4** Alignment Tools | SIM | SIM | Toolbar contextual nova com ícones |
| **F5** CSS Live Editor | TALVEZ | TALVEZ | Split view canvas↔code precisa pensar |
| **F6** Background element | NAO | NAO | Reutiliza InspectorColorPicker |
| **F7** Group/Ungroup | SIM | SIM | Visual de grupo no canvas + interação |
| **F8** Layer Panel | SIM | SIM | Painel sidebar novo com drag-to-reorder |
| **F9** Text Decoration | NAO | NAO | Botões B/I/U padrão |
| **F10** Snap Lines | NAO | NAO | Linhas magenta padrão Figma |
| **F11-F15** | NAO | NAO | Controles simples, padrão |
| **Gap A/B/C** | NAO | NAO | Lógica pura, sem UI |
| Homogeneity Check | SIM | SIM | Modal novo de checkpoint |
| Overlay tabelas | SIM | SIM | Interação hover hierárquica |
| AutoFix expandido | SIM | SIM | Preview visual de sugestões |

**Resumo:** 8 de ~21 stories precisam de @ux. As outras seguem padrões ou reutilizam componentes.

---

## 10. Roteiro de Execução — Quem Chamar e Quando

Guia simplificado para orquestrar o Epic 13.

```
PASSO 1 — @pm *create-epic
           Input: este documento (editor-visual-capabilities.md)
           Output: Epic 13 com escopo, waves, AC

PASSO 2 — @sm *draft (para cada story da Wave)
           Input: Epic 13
           Output: Stories 13.1, 13.2, 13.3...

PASSO 3 — @po *validate (para cada story)
           Input: Story draft
           Output: GO ou NO-GO

PASSO 4 — POR STORY (após GO):

           A story precisa de UI novo? (ver tabela 9.3)
              SIM → @ux primeiro → depois @dev
              NAO → @dev direto

           A story é complexa? (estimativa M ou L)
              SIM → @architect *create-plan → depois @dev
              NAO → @dev direto

           Resumindo:
           ┌─────────────────────────────────────────┐
           │ @po GO                                  │
           │   ├── UI novo? → @ux → @architect? → @dev │
           │   └── Simples? → @dev direto            │
           │                                         │
           │ @dev termina → @qa *qa-gate              │
           │   ├── PASS → done                       │
           │   └── FAIL → @dev corrige → @qa again    │
           └─────────────────────────────────────────┘
```

### Exemplo concreto — Wave 1

```
Story F5 (CSS Live Editor) — estimativa M, UI TALVEZ
  @sm *draft → @po *validate → GO
  → @ux (opcional — pensar split view)
  → @architect *create-plan (complexa)
  → @dev *develop
  → @qa *qa-gate

Story F1 (Border Editor) — estimativa M, UI SIM
  @sm *draft → @po *validate → GO
  → @ux (design do componente)
  → @architect *create-plan (complexa)
  → @dev *develop
  → @qa *qa-gate

Story F3 (Text Alignment) — estimativa S, UI NAO
  @sm *draft → @po *validate → GO
  → @dev *develop (direto)
  → @qa *qa-gate
```

---

## 11. Relação com Pipeline v3.18

Este documento complementa — não substitui — a Seção 14 do `pipeline-redesign-v3.md`.

| Documento | Escopo |
|-----------|--------|
| `pipeline-redesign-v3.md` Seção 14 | Matriz de mitigação Pipeline↔Editor (o que o pipeline erra vs o que o editor corrige) |
| `pipeline-redesign-v3.md` Seção 8.1-8.3 | Sub-steps 5.1 (Tree-Driven HTML) e 5.2 (CSS-from-Extraction) — a Camada 1 de automação |
| **Este documento** | Spec completa: diagnóstico raiz (1.1), estratégia 3 camadas (1.2), mapa CSS (1.3), features editor (3), melhorias (4), gaps (5), AutoFix evolução (6), priorização (7) |

Os 3 Editor Gaps (A/B/C) estão duplicados aqui propositalmente — este documento é a **referência canônica** para implementação, enquanto a Seção 14 mantém o contexto de mitigação.

---

## 12. Change Log

| Versao | Data | Descrição |
|--------|------|-----------|
| 1.0 | 2026-03-21 | Versão inicial: 15 features ausentes (F1-F15), 8 melhorias (M1-M8), 3 gaps (A/B/C), priorização |
| 1.1 | 2026-03-21 | Diagnóstico raiz: Stage 5 ignora 90% dos dados visuais. Seções 1.1-1.4 adicionadas. Estratégia revisada para 3 camadas (Pipeline 85% → AutoFix 93% → Editor 100%). Mapa CSS completo (30 propriedades). Projeção de fidelidade por camada. Waves reordenadas com Stage 5 como pré-requisito |
| 1.2 | 2026-03-22 | Revisão: 9 correções. (1) Erro factual "texto vermelho" corrigido. (2) F12 reframed como refinamento, não criação. (3) F11 de margin→padding (position:absolute torna margin irrelevante). (4) M5/M6 duplicatas marcadas. (5) Seção 6 unificada com Camada 2. (6) @font-face, text-overflow, page-break, @media print adicionados ao mapa CSS. (7) Nota explicando F2/F4 CRITICO na Wave 2. (8) Fix types renomeados para border-refine/background-refine. (9) Comparação visual promovida para Wave 4 |
| 1.3 | 2026-03-22 | Mapeamento Pipeline→Telas (Seção 9): 3 telas novas, 5 validações. Matriz @ux por story (8 de 21 precisam). Roteiro de execução (Seção 10): guia passo-a-passo de quem chamar e quando, com exemplo concreto da Wave 1 |

---

— Aria, arquitetando o futuro 🏗️
