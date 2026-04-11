---
id: backlog-jsbarcode-canvas
title: "Carregar JsBarcode no Canvas iframe para renderização WYSIWYG de barcodes"
type: feature
status: Done
priority: medium
epic: TBD
complexity: M
business_value: >
  Canvas renderiza barcodes como SVG estático gerado por python-barcode (backend),
  que não suporta todos os formatos (ex: MSI). O template exportado usa JsBarcode
  (JS runtime) que suporta todos os formatos. Resultado: preview no editor difere
  do output final. Carregar JsBarcode no iframe do Canvas resolve a discrepância
  e entrega WYSIWYG real para barcodes.
scope_out:
  - Chart.js no iframe (avaliar separadamente)
  - Remoção total de python-barcode (ainda útil para barcodes com valor estático conhecido)
risks:
  - Tamanho do srcdoc aumenta ~47KB por página com JsBarcode inline
  - Conflito potencial com CANVAS_INTERACTION_SCRIPT (risco baixo — JsBarcode não usa event listeners globais)
origin: "Auditoria Epic 32 — gap I31 (MSI) + avaliação @architect 2026-04-08"
architect_review:
  status: APPROVED
  date: 2026-04-08
  reviewer: "@architect (Aria)"
  notes: >
    Complexidade baixa, valor alto. Canvas já permite scripts (sandbox allow-scripts).
    JsBarcode é pequeno (~47KB). Consistente com princípio WYSIWYG. Lazy rendering
    limita overhead a 5 iframes visíveis. Abre precedente para libs JS no iframe
    mas cada caso deve ser avaliado separadamente.
dependencies:
  - "Story 31.3 (auto-seed SYSTEM_LIBS — JsBarcode em public/libs/)"
---

# Story — Carregar JsBarcode no Canvas iframe

## Story
**Como** operador editando um template com barcodes no editor visual,
**Quero** ver o barcode renderizado no Canvas com o formato correto (incluindo MSI, CODABAR),
**Para** ter preview WYSIWYG fiel ao output final sem discrepâncias de formato.

## Status
Draft

## Context

### Problema
- Canvas iframe renderiza HTML via `srcdoc` — sem libs JS externas
- Barcodes no Canvas são SVG estáticos gerados por `python-barcode` no stage5
- `python-barcode` não suporta MSI — gera CODE128 como fallback (enganoso)
- Template exportado usa JsBarcode (JS) que suporta todos os formatos
- Resultado: operador vê barcode errado no editor, correto no export

### Solução Aprovada (@architect)
- Injetar JsBarcode no `buildPageSrcdoc()` do HTMLCanvas.vue
- Adicionar script de inicialização que renderiza barcodes no iframe
- Abordagem: ler conteúdo de `/libs/JsBarcode.all.min.js` e embutir como `<script>` inline no srcdoc (srcdoc não tem acesso a fetch externo)

## Acceptance Criteria

- [ ] AC1: Canvas iframe carrega JsBarcode e renderiza barcodes dinamicamente
- [ ] AC2: Formato MSI renderiza corretamente no Canvas (não como CODE128)
- [ ] AC3: Todos os formatos do BarcodeInspector (CODE128, CODE39, EAN13, EAN8, UPC, ITF, MSI, CODABAR) renderizam corretamente no Canvas
- [ ] AC4: Performance aceitável — tempo de renderização do Canvas não aumenta mais que 200ms
- [ ] AC5: CANVAS_INTERACTION_SCRIPT (click, resize, drag) continua funcionando normalmente
- [ ] AC6: Barcodes com valor estático (preview) e dinâmico (binding KO) ambos renderizam

## Scope

**IN:**
- Injetar JsBarcode no `buildPageSrcdoc()` (HTMLCanvas.vue) quando há nós `data-type="barcode"`
- Script de inicialização no iframe que processa barcodes após DOM ready
- Testes unitários para renderização de cada formato
- Teste de regressão para interação no Canvas (clicks, drag, resize)

**OUT:**
- Chart.js no iframe (story separada se necessário)
- Remoção de python-barcode do backend (mantém para barcodes com valor estático)
- Mudanças no BarcodeInspector

## Dev Notes

**Arquivos chave:**
- `frontend/src/organisms/HTMLCanvas.vue` — `buildPageSrcdoc()` (linha ~465)
- `frontend/src/organisms/HTMLCanvas.vue` — `CANVAS_INTERACTION_SCRIPT` (linha ~331)
- `frontend/public/libs/JsBarcode.all.min.js` — lib disponível após Story 31.3
- `backend/services/stages/stage5_template_generation.py` — handler barcode (gera SVG estático)

**Abordagem técnica:**
1. No `buildPageSrcdoc()`, detectar se HTML contém `data-type="barcode"`
2. Se sim, ler JsBarcode de `/libs/JsBarcode.all.min.js` via fetch (uma vez, cachear)
3. Embutir como `<script>` inline no srcdoc antes de `</head>`
4. Adicionar script de inicialização após `</body>`:
   ```js
   document.querySelectorAll('[data-type="barcode"]').forEach(el => {
     const format = el.dataset.format || 'CODE128'
     const value = el.dataset.value || '0000000000'
     el.innerHTML = '' // limpar SVG estático
     try { JsBarcode(el, value, { format, displayValue: true }) } catch(e) {}
   })
   ```
5. Stage5 pode simplificar: gerar `<div data-type="barcode" data-format="MSI" data-value="123">` sem SVG inline

## Change Log
| Data | Agente | Mudança |
|------|--------|---------|
| 2026-04-08 | @architect | Avaliação aprovada — complexidade baixa, valor alto |
| 2026-04-08 | @sm | Story draft criada no backlog |
