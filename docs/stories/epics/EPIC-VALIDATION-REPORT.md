# Relatório de Validação — Stories vs Código Real

**Data:** 2026-04-07
**Método:** 6 agentes QA em paralelo validaram cada story contra o código fonte
**Resultado:** De 61 stories, 7 já estão implementadas e devem ser removidas

---

## Resumo Executivo

| Epic | Stories | Confirmadas | Parcial | Já Done | AC Ajuste |
|------|---------|-------------|---------|---------|-----------|
| 31 — Export ZIP | 8 | 4 | 2 | 1 (31.7 funções existem) | 4 |
| 32 — Fidelidade Visual | 6 | 3 | 1 | 2 (32.3, 32.4) | 2 |
| 33 — Inspector Loop | 10 | 8 | 0 | 1 (33.9) | 1 |
| 34 — Field Mapping | 8 | 6 | 0 | 1 (34.4) | 1 |
| 35 — Sync/Diff | 9 | 7 | 1 | 1 (35.7) | 1 |
| 36 — Code/Save | 5 | 5 | 0 | 0 | 0 |
| 37 — Canvas UX | 8 | 4 | 2 | 0 | 3 |
| 38 — Avançadas | 7 | 3 | 3 | 0 | 2 |
| **TOTAL** | **61** | **40** | **9** | **5+2 reframe** | **14** |

---

## Stories a REMOVER (já implementadas)

| Story | Evidência |
|-------|-----------|
| **32.3** — data-node-id em todos os tipos | Feito na Story 29.4. Rect, image, chart, barcode, line todos têm data-node-id |
| **32.4** — Extração automática de imagens do PDF | Stage 2 já extrai via `page.get_images()`, salva via `storage.upload_asset()`, stage5 gera `<img>` |
| **33.9** — FontWarning integrado ao ElementInspector | `ElementInspector.vue:43-49` já tem FontWarning, useFontCascade, upload funcional |
| **34.4** — Drag campo FieldNavigator para Canvas | `FieldNavItem.vue` tem draggable, `HTMLCanvas.vue` tem onFieldDrop com confirmação |
| **35.7** — Ocultar MultiDocAnalyzer com 1 PDF | `EditorLayout.vue:41` já tem `v-if="multiDocStore.hasMultiplePdfs"` |

---

## Stories a REFRAME (escopo menor que o planejado)

| Story | Situação | Novo escopo |
|-------|----------|-------------|
| **31.1** — CSS no ZIP | CSS **existe** no ZIP mas conteúdo é genérico (template_generator). Stage5 gera CSS rico mas não é o usado no export | Garantir que export use CSS do stage5 (não do template_generator genérico) |
| **31.4** — Edições Monaco no ZIP | Backend **já tem** suporte `monacoEdits` (`generate.py:73-76`). Frontend não envia | Apenas frontend: enviar `codeStore.fileContents` como `monacoEdits` no payload |
| **31.7** — Paginação runtime | Funções `criarNovaPagina` e `quebrarTabelaEntrePaginas` **já existem** no base.js. Falta invocação automática | Apenas: adicionar auto-invocação via `window.onload` ou callback |
| **32.1** — CSS cor/borda/background | Cores aplicadas via **inline styles** (funciona visualmente). Classes CSS são dead code | Reframe: remover dead CSS classes OU refatorar para usá-las. Fidelidade visual ~OK via inline |
| **37.5** — Ferramentas alinhamento na UI | **Já implementado** em `HTMLCanvas.vue` como floating toolbar com 6 align + 2 distribute | Reframe: verificar se cobertura é suficiente ou se precisa botões no Inspector também |
| **37.7** — Toggle Guias na toolbar | `showGuides` state e `CanvasGuides.vue` existem. Falta apenas botão na TopToolbar | Escopo reduzido: apenas adicionar 1 botão toggle |

---

## AC Adjustments Necessários

### Epic 31
| Story | Ajuste |
|-------|--------|
| 31.1 | Clarificar qual gerador CSS é usado no export (stage5 rico vs template_generator genérico) |
| 31.4 | Escopo é apenas frontend — backend já tem suporte `monacoEdits` |
| 31.5 | Distinguir: barcodes estáticos funcionam (SVG stage5). JsBarcode só necessário para dinâmicos |
| 31.6 | Re-avaliar prioridade: stage5 documenta que PDFs Planet Express usam apenas fontes de sistema. Validar com templates reais |

### Epic 32
| Story | Ajuste |
|-------|--------|
| 32.1 | Reframe: inline styles já funcionam. Gap é dead CSS code, não ausência visual |
| 32.2 | Adicionar: stage3 precisa propagar `is_italic` para tree nodes (hoje só `is_bold` é propagado) |

### Epic 33
| Story | Ajuste |
|-------|--------|
| 33.5 | VisibilityControl emite `VisibilityConfig` objeto, não boolean. Condição `typeof value === 'boolean'` nunca match. AC deve especificar `value.mode === 'hidden'` |

### Epic 34
| Story | Ajuste |
|-------|--------|
| 34.1 | Adicionar AC: "Extend `FieldMappingEntry` type em `pipeline.types.ts` com campo `confidence`" |

### Epic 35
| Story | Ajuste |
|-------|--------|
| 35.6 | Clarificar: `VariationMatrix` type precisa de `fieldIds` (ou repurpose `layoutIds`). Backend `block_classifications` deve ser source das rows |

### Epic 37
| Story | Ajuste |
|-------|--------|
| 37.3 | `calcSnapLines` não tem parâmetro `columnPositions`. Data flow stage2→frontend precisa ser mapeado |
| 37.6 | ZOOM_MAX já está correto (125 canvas, 200 PDF). Gap real é mousewheel + atalhos teclado |
| 37.7 | Reduzir escopo: apenas adicionar botão na TopToolbar (state e componente já existem) |

### Epic 38
| Story | Ajuste |
|-------|--------|
| 38.2 | UI do rule builder (ConditionalStyleSection.vue) já existe. Gap é só `baseJsGenerators` + runtime |
| 38.6 | `template_name` já aceito no upload. Gap: não persiste no job_state nem propaga ao pipeline |

---

## Números Finais Ajustados

| Métrica | Original | Ajustado |
|---------|----------|----------|
| Total de stories | 61 | **54** (7 removidas: 5 done + 2 reframe para existente) |
| Gaps confirmados | — | **40 integrais + 9 parciais** |
| ACs com ajuste | — | **14 stories** |
| Epics | 8 | **8** (mesmos) |

---

## Observações Arquiteturais dos Agentes

1. **Dois paths de export existem:** Frontend (useExport.ts + JSZip) e Backend (export.py + zipfile). Epic 31 deve definir qual é canônico.
2. **Stage5 CSS é rico mas não usado no export:** O template_generator.py gera CSS genérico. O CSS com fontes/cores/bordas reais vem do stage5 mas pode não estar fluindo para o export.
3. **`@font-face` pode ser desnecessário:** Stage5 documenta explicitamente que PDFs Planet Express usam apenas fontes de sistema. Story 31.6 deve ser validada com templates reais antes de priorizar.
4. **Inline styles vs CSS classes:** Cores/bordas/backgrounds já funcionam via inline styles no HTML. As classes CSS geradas pelo 5.2 são dead code. O impacto visual real de C3 é menor que o auditado.
