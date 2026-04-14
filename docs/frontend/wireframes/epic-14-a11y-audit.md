# Epic 14 — WCAG AA Accessibility Audit

> **Author:** Uma (@ux-design-expert)
> **Standard:** WCAG 2.2 Level AA
> **Date:** 2026-03-22
> **Input:** epic-14-lofi-wireframes.md
> **Status:** Pre-implementation audit (design phase)

---

## Audit Summary

| Componente | Story | Resultado | Issues | Severity |
|-----------|-------|-----------|--------|----------|
| AlignmentToolbar | 14.5 | ⚠ 3 issues | Keyboard, Focus, Labels | Medium |
| LayerPanel | 14.8 | ⚠ 4 issues | Drag a11y, Focus, Live region, Reorder | High |
| SplitView | 14.1 | ✅ 1 issue | Separator role | Low |
| ComputedStylesPanel | 14.1 | ✅ 0 issues | — | — |
| ColorPicker Enhanced | 14.6 | ⚠ 3 issues | Slider labels, Color-only, Live region | Medium |
| BoxModelVisualization | 14.12 | ⚠ 2 issues | Color-only, Spinbutton pattern | Medium |
| TableInspector (editable) | 14.12 | ⚠ 3 issues | Drag a11y, Grid role, Live region | Medium |

**Total: 16 issues encontrados (0 Critical, 2 High, 12 Medium, 2 Low)**

---

## 1. AlignmentToolbar (Story 14.5)

### PERCEIVABLE

| Check | Status | Notes |
|-------|--------|-------|
| Text contrast >= 4.5:1 | N/A | Toolbar usa icones SVG, nao texto |
| UI controls contrast >= 3:1 | ✅ | Icones devem ter contraste >= 3:1 contra fundo da toolbar |
| No color-only indicators | ⚠ **ISSUE** | Distribute buttons disabled: usar opacity 0.4 + `cursor: not-allowed` nao e suficiente. **Adicionar tooltip "Selecione 3+ elementos"** |
| Icon buttons have aria-label | ✅ | Planejado no wireframe: cada botao com aria-label descritivo |

### OPERABLE

| Check | Status | Notes |
|-------|--------|-------|
| Keyboard accessible | ⚠ **ISSUE** | Toolbar aparece/desaparece com mouse. **Precisa: quando toolbar visivel, Tab navega entre botoes. Enter/Space aciona o botao** |
| Tab order logical | ⚠ **ISSUE** | **Definir tabindex no container. Ordem: left→center→right, top→middle→bottom, distH→distV** |
| Focus indicators visible | ✅ | Usar `outline: 2px solid #3B82F6` no focus de cada botao |
| No keyboard traps | ✅ | Toolbar e flat (sem modal), Tab sai naturalmente |

### UNDERSTANDABLE

| Check | Status | Notes |
|-------|--------|-------|
| Disabled state aria-disabled | ✅ | Distribute buttons: `aria-disabled="true"` quando < 3 selecionados |

### ROBUST

| Check | Status | Notes |
|-------|--------|-------|
| ARIA roles | ✅ | `role="toolbar"` no container, `role="button"` em cada acao |
| aria-label | ✅ | Exemplo: `aria-label="Alinhar a esquerda"`, `aria-label="Distribuir horizontalmente"` |

### Recomendacoes para Story 14.5

```
AC ADICIONAL SUGERIDO:
- AC_A11Y: AlignmentToolbar acessivel via teclado — Tab navega
  entre botoes, Enter/Space aciona, botoes disabled tem
  aria-disabled="true" e tooltip explicativo.

IMPLEMENTACAO:
- Container: role="toolbar", aria-label="Ferramentas de alinhamento"
- Botoes: role="button", tabindex="0", aria-label descritivo
- Disabled: aria-disabled="true", title="Selecione 3+ elementos"
- Focus: outline: 2px solid var(--color-accent)
```

---

## 2. LayerPanel (Story 14.8)

### PERCEIVABLE

| Check | Status | Notes |
|-------|--------|-------|
| No color-only indicators | ✅ | Icones de tipo (🔤🖼▬📁) alem de cor |
| Images have alt text | ✅ | Icones de tipo: aria-label por tipo |

### OPERABLE

| Check | Status | Notes |
|-------|--------|-------|
| Keyboard accessible | ⚠ **ISSUE HIGH** | **Drag-to-reorder nao e acessivel via teclado por padrao. OBRIGATORIO: alternativa com Alt+Arrow Up/Down para reordenar sem mouse** |
| Tab order logical | ⚠ **ISSUE** | Lista de layers precisa de navegacao por setas (Arrow Up/Down), nao Tab entre cada item. **Usar roving tabindex pattern** |
| Focus indicators visible | ✅ | Item focado: background highlight + outline |
| No keyboard traps | ✅ | Tab sai do panel normalmente |

### UNDERSTANDABLE

| Check | Status | Notes |
|-------|--------|-------|
| States indicated | ⚠ **ISSUE** | **Quando layer e reordenado via drag, anunciar nova posicao via aria-live. Exemplo: "Logo Bradesco movido para posicao 2 de 4"** |

### ROBUST

| Check | Status | Notes |
|-------|--------|-------|
| ARIA roles | ⚠ **ISSUE** | **Usar `role="listbox"` no container, `role="option"` em cada item. Grupos: `role="group"` com `aria-label` do nome do grupo. Colapsavel: `aria-expanded`** |
| aria-live | ⚠ | **Adicionar `aria-live="polite"` em regiao de status para anunciar reordenacoes** |

### Recomendacoes para Story 14.8

```
ACs ADICIONAIS SUGERIDOS:
- AC_A11Y_KEYBOARD: Layers navegaveis via Arrow Up/Down.
  Alt+Arrow Up/Down reordena o layer selecionado (alternativa ao drag).
- AC_A11Y_ANNOUNCE: Reordenacao de layers anunciada via
  aria-live="polite" com texto descritivo.

IMPLEMENTACAO:
- Container: role="listbox", aria-label="Camadas do template"
- Item: role="option", aria-selected, tabindex via roving pattern
- Grupo: role="group", aria-label="Nome do grupo", aria-expanded
- Reorder keyboard: Alt+ArrowUp/Down move item
- Status: <div aria-live="polite" class="sr-only">
  "Logo Bradesco movido para camada 2 de 4"
- Visibilidade toggle: aria-pressed no botao 👁
```

---

## 3. SplitView (Story 14.1)

### PERCEIVABLE

| Check | Status | Notes |
|-------|--------|-------|
| All checks | ✅ | Split view e estrutural, nao tem conteudo proprio |

### OPERABLE

| Check | Status | Notes |
|-------|--------|-------|
| Keyboard accessible | ✅ | Canvas e Monaco ja sao acessiveis individualmente |
| Drag handle keyboard | ⚠ **ISSUE LOW** | **Handle resizavel deve aceitar Arrow Left/Right para resize via teclado. Implementar `role="separator"` com `aria-valuenow` (porcentagem)** |

### ROBUST

| Check | Status | Notes |
|-------|--------|-------|
| ARIA roles | ✅ | Canvas: `aria-label="Canvas do template"`. Monaco: `aria-label="Editor de codigo"` |
| Separator | ✅ | `role="separator"`, `aria-orientation="vertical"`, `aria-valuenow="50"` |

### Recomendacoes para Story 14.1

```
IMPLEMENTACAO:
- Handle: role="separator", aria-orientation="vertical",
  aria-valuenow="50", aria-valuemin="30", aria-valuemax="70"
- Keyboard: ArrowLeft/Right ajusta split em 5% por keypress
- Labels: aria-label="Canvas" e aria-label="Editor CSS"
- Split button: aria-pressed="true/false" para toggle state
```

---

## 4. ComputedStylesPanel (Story 14.1)

### Todas as verificacoes: ✅

| Check | Status | Notes |
|-------|--------|-------|
| Read-only panel | ✅ | Nenhuma interacao — apenas exibicao |
| Semantic HTML | ✅ | Usar `<dl>` (definition list) para pares propriedade/valor |
| Collapsible | ✅ | `aria-expanded` no toggle, `aria-controls` apontando para conteudo |

---

## 5. ColorPicker Enhanced (Story 14.6)

### PERCEIVABLE

| Check | Status | Notes |
|-------|--------|-------|
| Color contrast | ✅ | Labels e inputs seguem padrao existente do InspectorColorPicker |
| No color-only indicators | ⚠ **ISSUE** | **Swatches de paleta e recentes mostram APENAS cor. Adicionar tooltip com valor hex e aria-label="Cor #336699" em cada swatch** |

### OPERABLE

| Check | Status | Notes |
|-------|--------|-------|
| Keyboard accessible | ✅ | Swatches navegaveis via Arrow keys (grid navigation) |
| Slider keyboard | ⚠ **ISSUE** | **Opacity slider deve aceitar Arrow Left/Right (incremento 1%) e Page Up/Down (incremento 10%). Usar `<input type="range">` nativo que ja suporta isso** |

### UNDERSTANDABLE

| Check | Status | Notes |
|-------|--------|-------|
| Labels | ⚠ **ISSUE** | **Opacity slider precisa de `aria-label="Opacidade"` e `aria-valuetext="80 porcento"` (nao so o numero)** |
| Required fields | ✅ | Nenhum campo obrigatorio |

### ROBUST

| Check | Status | Notes |
|-------|--------|-------|
| ARIA roles | ✅ | Swatches: role="option" dentro de role="listbox" |
| aria-live | ⚠ | **Quando cor muda, anunciar novo valor via aria-live="polite" na regiao de preview** |

### Recomendacoes para Story 14.6

```
IMPLEMENTACAO:
- Swatches: role="option", aria-label="Cor #RRGGBB",
  aria-selected para swatch ativo
- Container paleta: role="listbox", aria-label="Cores do documento"
- Container recentes: role="listbox", aria-label="Cores recentes"
- Opacity slider: <input type="range">, aria-label="Opacidade",
  aria-valuetext="${value} porcento"
- Transparent btn: aria-label="Definir transparente"
- Inherit btn: aria-label="Herdar cor do elemento pai"
- Preview: aria-live="polite" anuncia "Cor alterada para #336699"
```

---

## 6. BoxModelVisualization (Story 14.12)

### PERCEIVABLE

| Check | Status | Notes |
|-------|--------|-------|
| Color contrast | ✅ | Valores brancos sobre fundo colorido — garantir contraste com text-shadow |
| No color-only indicators | ⚠ **ISSUE** | **As 4 camadas (margin/border/padding/content) sao diferenciadas APENAS por cor. Adicionar labels textuais ("margin", "border", etc.) dentro de cada camada** |

### OPERABLE

| Check | Status | Notes |
|-------|--------|-------|
| Keyboard accessible | ⚠ **ISSUE** | **Valores editaveis inline devem ser acessiveis via Tab. Usar pattern: Tab navega entre valores editaveis no sentido horario (top→right→bottom→left por camada, depois proxima camada)** |
| Focus indicators | ✅ | Input inline: borda azul 2px |

### UNDERSTANDABLE

| Check | Status | Notes |
|-------|--------|-------|
| Labels | ✅ | Cada input: aria-label descritivo (ex: "margin top") |

### ROBUST

| Check | Status | Notes |
|-------|--------|-------|
| ARIA roles | ✅ | Cada valor editavel: `role="spinbutton"`, `aria-valuenow`, `aria-valuemin="0"` |

### Recomendacoes para Story 14.12 (BoxModel)

```
IMPLEMENTACAO:
- Cada valor: role="spinbutton", aria-label="margin top",
  aria-valuenow="0", aria-valuemin="0"
- Labels textuais: "margin", "border", "padding", "content"
  visiveis dentro de cada camada (font 9px, uppercase)
- Tab order: margin-top → margin-right → margin-bottom → margin-left
  → border-top → ... → padding-top → ... (16 valores total)
- Arrow Up/Down incrementa/decrementa valor em 1
- Shift+Arrow incrementa/decrementa em 10
```

---

## 7. TableInspector Editavel (Story 14.12)

### OPERABLE

| Check | Status | Notes |
|-------|--------|-------|
| Keyboard accessible | ⚠ **ISSUE** | **Drag-to-reorder de colunas precisa alternativa teclado: Alt+Arrow Up/Down move coluna selecionada** |
| Tab order | ✅ | Tab navega: width input → align dropdown → proximo row |
| Focus indicators | ✅ | Inputs e dropdowns ja tem focus ring nativo |

### UNDERSTANDABLE

| Check | Status | Notes |
|-------|--------|-------|
| Labels | ⚠ **ISSUE** | **Inputs de width/align precisam de aria-label contextual: "Largura da coluna data_emissao", nao generico "Largura"** |
| Live region | ⚠ **ISSUE** | **Anunciar quando coluna e adicionada/removida/reordenada via aria-live** |

### ROBUST

| Check | Status | Notes |
|-------|--------|-------|
| ARIA roles | ✅ | `role="grid"` no container, `role="row"` em cada linha, `role="gridcell"` em cada celula |

### Recomendacoes para Story 14.12 (Table)

```
IMPLEMENTACAO:
- Container: role="grid", aria-label="Colunas da tabela"
- Row: role="row", com aria-rowindex
- Cell: role="gridcell"
- Width input: aria-label="Largura da coluna {campo}"
- Align dropdown: aria-label="Alinhamento da coluna {campo}"
- Remove btn: aria-label="Remover coluna {campo}"
- Add btn: aria-label="Adicionar nova coluna"
- Reorder keyboard: Alt+ArrowUp/Down move coluna
- Live region: aria-live="polite" anuncia mudancas
```

---

## 8. Resumo de Issues por Categoria WCAG

### PERCEIVABLE (3 issues)
1. **14.5** — Distribute disabled: adicionar tooltip explicativo
2. **14.6** — Swatches color-only: adicionar aria-label com hex
3. **14.12** — BoxModel color-only: adicionar labels textuais nas camadas

### OPERABLE (8 issues)
4. **14.5** — Toolbar keyboard navigation (Tab + Enter/Space)
5. **14.5** — Tab order definido para botoes
6. **14.8** — Drag-to-reorder keyboard alternative (Alt+Arrow)
7. **14.8** — Roving tabindex pattern para lista de layers
8. **14.1** — Split handle keyboard resize (Arrow Left/Right)
9. **14.6** — Opacity slider keyboard (nativo com `<input type="range">`)
10. **14.12** — BoxModel Tab navigation entre 16 valores
11. **14.12** — Table drag-to-reorder keyboard alternative

### UNDERSTANDABLE (3 issues)
12. **14.8** — Reorder anuncio via aria-live
13. **14.6** — Opacity slider aria-valuetext
14. **14.12** — Table column labels contextuais

### ROBUST (2 issues)
15. **14.8** — ARIA roles corretos para listbox/group/expanded
16. **14.12** — Table live region para add/remove/reorder

---

## 9. Recomendacoes Globais

### Pattern: Drag-to-Reorder Acessivel
Applies to: 14.8 (LayerPanel) e 14.12 (TableInspector)

```typescript
// Keyboard alternative for drag-to-reorder
function handleKeydown(e: KeyboardEvent, index: number) {
  if (e.altKey && e.key === 'ArrowUp' && index > 0) {
    reorder(index, index - 1)
    announce(`${itemName} movido para posicao ${index}`)
  }
  if (e.altKey && e.key === 'ArrowDown' && index < items.length - 1) {
    reorder(index, index + 1)
    announce(`${itemName} movido para posicao ${index + 2}`)
  }
}

// Live region announcer
function announce(message: string) {
  const el = document.getElementById('a11y-announcer')
  if (el) el.textContent = message
}
```

### Pattern: Color Swatch Acessivel
Applies to: 14.6 (ColorPicker)

```html
<div role="listbox" aria-label="Cores do documento">
  <button
    v-for="color in documentColors"
    role="option"
    :aria-label="`Cor ${color}`"
    :aria-selected="modelValue === color"
    :style="{ backgroundColor: color }"
    @click="selectColor(color)"
  />
</div>
```

### Global A11y Announcer
Adicionar ao App.vue (se nao existir):

```html
<div id="a11y-announcer" aria-live="polite" class="sr-only" />
```

```css
.sr-only {
  position: absolute;
  width: 1px; height: 1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
}
```

---

## 10. Testing Checklist

### Per-Component A11y Tests (jest-axe)

```typescript
import { axe, toHaveNoViolations } from 'jest-axe'
expect.extend(toHaveNoViolations)

it('should have no a11y violations', async () => {
  const { container } = render(AlignmentToolbar, { props: { ... } })
  const results = await axe(container)
  expect(results).toHaveNoViolations()
})
```

### Manual Testing Protocol
- [ ] Tab through all new components — verify logical order
- [ ] Activate every button via Enter and Space
- [ ] Verify all focus indicators are visible (2px+ outline)
- [ ] Test drag alternatives with Alt+Arrow keys
- [ ] Verify screen reader announces state changes
- [ ] Check contrast with browser devtools (>= 3:1 for UI, >= 4.5:1 for text)

---

**Result:** ⚠ **16 Issues Found — 0 Critical, 2 High, 12 Medium, 2 Low**

As 2 issues HIGH sao ambas no LayerPanel (14.8) — drag-to-reorder sem alternativa de teclado e ARIA roles incompletos. Recomendo adicionar ACs de acessibilidade nas stories 14.5, 14.6, 14.8 e 14.12 antes da implementacao.

---

*Audited by Uma (@ux-design-expert) — WCAG 2.2 Level AA*

— Uma, desenhando com empatia 💝
