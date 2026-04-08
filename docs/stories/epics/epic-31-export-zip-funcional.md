# Epic 31 — Export ZIP Funcional (NFR7 Compliance)

**Prioridade:** P0
**Fase:** 1
**Estimativa:** 8 stories
**Dependências:** Nenhuma
**Objetivo:** O ZIP exportado deve ser autocontido — abrir `index.html` localmente renderiza o template corretamente com dados de exemplo.

---

## Contexto

A auditoria revelou que o ZIP de export tem gaps críticos: falta `css/style.css`, falta `assets/`, depende de `../Bibliotecas/js/` externas (NFR7 violado), edições do Monaco são descartadas, JsBarcode CDN ausente, `@font-face` ausente, e funções de paginação runtime ausentes no `base.js`.

---

## Stories

### 31.1 — Garantir que export use CSS rico do stage5 (não template_generator genérico)
**Gap:** C1
**Escopo:** Backend (`export.py` ou `useExport.ts`)
**QA Note:** CSS **existe** no ZIP mas conteúdo é genérico (template_generator). Stage5 gera CSS rico (fontes/cores/bordas) mas não é o usado no export. Escopo reduzido: wiring, não criação.
**AC:**
- [ ] ZIP contém `template/css/style.css` com o CSS **do stage5** (não do template_generator genérico)
- [ ] CSS inclui classes de fonte, cor, borda, background geradas por `_step_5_2_css_from_extraction()`
- [ ] `index.html` referencia `css/style.css` (não inline)
- [ ] Verificar qual dos dois paths de export (frontend useExport.ts + JSZip vs backend export.py + zipfile) é o canônico e garantir consistência

### 31.2 — Incluir pasta `assets/` no ZIP com imagens
**Gap:** C1
**Escopo:** Backend + Frontend
**AC:**
- [ ] ZIP contém `template/assets/` com todas as imagens do template
- [ ] Imagens extraídas do PDF (se implementadas no Epic 32) são incluídas
- [ ] Imagens carregadas via AssetGallery são incluídas
- [ ] `index.html` referencia imagens com path relativo `assets/`

### 31.3 — Tornar ZIP autocontido (embalar bibliotecas JS)
**Gap:** C2
**Escopo:** Backend + Frontend
**AC:**
- [ ] `knockout-3.4.2.js` e `knockout.mapping.js` incluídos em `template/js/libs/` no ZIP
- [ ] `Chart.min.js` e `chartjs-plugin-datalabels.min.js` incluídos quando template tem gráficos
- [ ] `index.html` referencia `js/libs/knockout-3.4.2.js` (não `../Bibliotecas/`)
- [ ] Licenças verificadas (MIT para KO, MIT para Chart.js)
- [ ] Template renderiza localmente sem servidor ou pasta Bibliotecas

### 31.4 — Edições Monaco chegam ao ZIP de export (frontend-only)
**Gap:** C5
**Escopo:** Frontend (`useExport.ts`)
**QA Note:** Backend **já tem** suporte `monacoEdits` em `generate.py:73-76`. Gap é apenas frontend: enviar `codeStore.fileContents` como `monacoEdits` no payload.
**AC:**
- [ ] `useExport.ts` envia `codeStore.fileContents` como `monacoEdits: { html, css, js }` no payload ao backend
- [ ] Backend já processa `monacoEdits` quando presentes (generate.py:73-76) — apenas verificar integração
- [ ] Teste: editar HTML no Monaco → exportar → ZIP contém HTML editado

### 31.5 — JsBarcode no template exportado (apenas barcodes dinâmicos)
**Gap:** C19
**Escopo:** Backend (stage5 / template_generator)
**QA Note:** Barcodes estáticos já funcionam via SVG gerado pelo stage5. JsBarcode só é necessário para barcodes com binding dinâmico (valor vem do KO observable).
**AC:**
- [ ] Quando template tem nós barcode com **binding dinâmico** (KO observable), `JsBarcode.all.min.js` incluído no ZIP em `js/libs/`
- [ ] Barcodes **estáticos** (SVG inline do stage5) não necessitam JsBarcode — sem mudança
- [ ] `index.html` inclui `<script src="js/libs/JsBarcode.all.min.js">` apenas quando há barcodes dinâmicos
- [ ] Barcodes dinâmicos renderizam corretamente com dados de exemplo

### 31.6 — `@font-face` embedding no export (validar necessidade)
**Gap:** C21
**Escopo:** Backend (stage5) + Frontend (useExport)
**QA Note:** Stage5 documenta que PDFs Planet Express usam **apenas fontes de sistema**. Esta story deve ser validada com templates reais antes de priorizar — pode ser desnecessária.
**AC:**
- [ ] **Validar** com 3+ templates reais se alguma fonte não-sistema é usada
- [ ] Se fontes custom detectadas: CSS inclui `@font-face { font-family: 'X'; src: url('assets/fonts/X.woff2'); }`
- [ ] Se fontes custom detectadas: arquivos de fonte incluídos em `template/assets/fonts/` no ZIP
- [ ] Se **apenas fontes de sistema**: documentar que @font-face é desnecessário e marcar story como WAIVED

### 31.7 — Auto-invocação das funções de paginação runtime no `base.js`
**Gap:** C18
**Escopo:** Backend (stage5 / template_generator)
**QA Note:** Funções `criarNovaPagina()` e `quebrarTabelaEntrePaginas()` **já existem** no base.js. Falta apenas auto-invocação.
**AC:**
- [ ] `base.js` já contém `quebrarTabelaEntrePaginas()` e `criarNovaPagina()` — verificar que estão presentes
- [ ] Adicionar auto-invocação via `window.onload` ou `ko.applyBindings` callback
- [ ] Template multi-página renderiza corretamente com dados de tabela longa
- [ ] Paginação executa automaticamente sem intervenção manual

### 31.8 — Teste E2E NFR7
**Gap:** —
**Escopo:** QA
**AC:**
- [ ] Gerar ZIP com template de boleto bancário (tabelas, gráficos, barcodes, fontes)
- [ ] Descompactar em pasta local
- [ ] Abrir `index.html` em Chrome sem servidor
- [ ] Template renderiza com: estilos corretos, fontes, gráficos, barcodes, paginação
- [ ] Nenhum erro no console do browser
