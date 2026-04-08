# Epic 32 — Fidelidade Visual do Canvas (Stage 5 CSS↔HTML)

**Prioridade:** P0
**Fase:** 1
**Estimativa:** 4 stories (originalmente 6 — 32.3 e 32.4 removidas por já estarem implementadas)
**Dependências:** Nenhuma (paralelo ao Epic 31)
**Objetivo:** Canvas renderiza com fidelidade visual ≥85% — cores, bordas, backgrounds, fontes bold/italic, imagens extraídas e SVG inline aplicados corretamente.

---

## Contexto

O Stage 5 gera classes CSS (cor, borda, background) no sub-step 5.2, mas essas classes nunca são aplicadas nos elementos HTML gerados no sub-step 5.1. No entanto, **cores/bordas/backgrounds já funcionam via inline styles** em `_tree_to_html()` — o impacto visual real é menor que o auditado inicialmente (~50-60%). As classes CSS do 5.2 são efetivamente dead code. Bold/italic são extraídos mas `is_italic` não é propagado pelo stage3. SVG inline não é implementado.

> **Nota QA (2026-04-07):** Stories 32.3 (data-node-id) e 32.4 (extração de imagens) foram **removidas** — já implementadas na Story 29.4 e no stage2 existente, respectivamente.

---

## Stories

### 32.1 — Limpar dead CSS classes ou refatorar para usá-las
**Gap:** C3
**Escopo:** Backend (`stage5_template_generation.py`)
**QA Note:** Cores/bordas/backgrounds **já funcionam via inline styles** em `_tree_to_html()`. As classes CSS geradas pelo 5.2 (`.c-{hex}`, `.border-N`, `.bg-N`) são dead code — nunca aplicadas nos elementos. Reframe: decidir entre remover dead code ou migrar de inline para classes.
**AC:**
- [ ] **Decisão:** Remover classes CSS dead code do 5.2 OU refatorar `_tree_to_html()` para usar classes em vez de inline styles
- [ ] Se remover: limpar `_step_5_2_css_from_extraction()` das classes não usadas
- [ ] Se refatorar: `_tree_to_html()` aplica `.c-{hex}`, `.border-N`, `.bg-N` nos elementos e remove inline styles correspondentes
- [ ] Fidelidade visual mantida ≥80% (já funciona via inline — não regredir)

### 32.2 — Incluir `is_bold`/`is_italic` nas classes de fonte CSS
**Gap:** C4
**Escopo:** Backend (`stage3_structural_analysis.py` + `stage5_template_generation.py`)
**QA Note:** Stage3 precisa propagar `is_italic` para tree nodes — hoje só `is_bold` é propagado.
**AC:**
- [ ] **Stage3:** `_build_tree_nodes()` propaga `is_italic` dos text blocks para os tree nodes (análogo a `is_bold`)
- [ ] `_step_5_2_css_from_extraction()` gera classes por combinação font+size+bold+italic
- [ ] Ex: `.f-helvetica-12-bold { font-family: 'Helvetica'; font-size: 12pt; font-weight: bold; }`
- [ ] `_tree_to_html()` atribui classe correta por variante tipográfica
- [ ] Canvas exibe texto em bold/italic conforme PDF original

### ~~32.3~~ — REMOVIDA (já implementada na Story 29.4)
> `data-node-id` já presente em todos os tipos: rect, image, chart, barcode, line.

### ~~32.4~~ — REMOVIDA (já implementada no stage2 existente)
> Stage 2 já extrai via `page.get_images()`, salva via `storage.upload_asset()`, stage5 gera `<img>`.

### 32.5 — SVG inline (FR32)
**Gap:** C20
**Escopo:** Backend (stage3 + stage5)
**AC:**
- [ ] Stage 3 detecta imagens vetoriais no PDF via PyMuPDF drawings/paths
- [ ] Stage 5 embede SVG inline no `index.html` (não como `<img>`)
- [ ] SVG mantém `viewBox` e é escalável
- [ ] Canvas renderiza SVG inline corretamente

### 32.6 — MSI barcode no backend
**Gap:** I31
**Escopo:** Backend (`stage5_template_generation.py`)
**AC:**
- [ ] `_FORMAT_MAP` inclui `"MSI": "msi"` (ou equivalente em python-barcode)
- [ ] BarcodeInspector frontend e backend consistentes nos formatos suportados
