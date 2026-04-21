# Epic 49 — Pilar C: Editor Visual + Template Engine

**Status:** Planning  
**Data:** 2026-04-21  
**Pré-requisito atendido:** Spike `spike/ast-validation` GO 3/3 (commit 807aa9c)  
**ADR base:** `docs/adrs/ADR-002-ast-as-source-of-truth.md`  
**Branch de partida:** merge `spike/ast-validation` → `main` + re-validação E2E Epic 48

---

## Objetivo

Implementar o template engine do Pilar C usando `TemplateAstV0` como source-of-truth:
1. **Renderer** — `TemplateAstV0` → HTML/MJML renderizável com campos `{{bind_path | formatter}}`
2. **Editor Vue 3** — canvas interativo que exibe o template renderizado + permite editar bindings
3. **Round-trip** — salvar template editado de volta como `TemplateAstV0` no Supabase

---

## Pré-requisitos técnicos

| Item | Estado | Where |
|------|--------|-------|
| `TemplateAstV0` schema | ✅ Pronto | `backend/models/ast/nodes.py` |
| `ast_emitter.emit()` | ✅ Pronto | `backend/services/stages/stage3_structural/ast_emitter.py` |
| Stage 4 consume_ast | ✅ Pronto (5 LOC patch) | `backend/services/stages/stage4_field_mapping.py` |
| Formatter inference | ✅ Pronto (93.9%) | `backend/services/stages/stage3_structural/formatter_inference.py` |
| XSD binding (Stage 4) | ✅ Epic 48 | stage4_field_mapping |
| E2E scalar coverage ≥80% | ⚠️ Pendente re-validação | branch feature/epic-48-pilar-b |

---

## Escopo — 7 Stories propostas

### Story 49.1 — API: endpoint `GET /templates/{id}/ast` (P0)
Expõe `TemplateAstV0` serializado via API para consumo do frontend editor.
- Serializa `TemplateAstV0.model_dump()` com `mode="json"`
- Rota: `GET /api/templates/{template_id}/ast`
- Autenticação: JWT (padrão existente)
- **Output contract:** `{"schema_version": "template-ast-v0", "root": {...}, "layout_type_id": "..."}`

### Story 49.2 — Backend: `AstRenderer` → HTML (P0)
Converte `TemplateAstV0` em HTML estático com placeholders `{{bind_path}}`.
- `FieldNode` → `<span data-bind="bind_path" data-formatter="kind">{{bind_path}}</span>`
- `SectionNode` → `<div class="section" data-name="name">...</div>`
- `RepeatingNode` → `<div data-repeat="iterator">` com item_template renderizado
- `ImageNode(dynamic)` → `<img data-bind="bind_path" src="placeholder.svg">`
- `TextNode` → `<span class="static">content</span>` (preservar font/color via inline style)
- `TableNode` → `<table>` com células renderizadas
- `RawHtmlNode` → passthrough direto

### Story 49.3 — Frontend: `AstCanvas.vue` — canvas read-only (P0)
Componente Vue 3 que exibe HTML renderizado do AST em iframe sandboxed.
- Recebe `TemplateAstV0` via prop ou store Pinia
- Renderiza via `AstRenderer` (chamada API ou composable local)
- Fidelidade visual: preservar bbox, font-size, font-family do PDF original
- Seleção de FieldNode: click → destaca + emite evento `field:selected`

### Story 49.4 — Frontend: `FieldBindingPanel.vue` — editar bindings (P1)
Painel lateral que permite editar `bind_path` e `formatter` de um `FieldNode` selecionado.
- Input `bind_path`: autocomplete com caminhos XSD do `field_tree` (Stage 4 output)
- Select `formatter.kind`: date | currency | number | percent | raw
- Input `formatter.pattern`: edição livre (validação regex)
- Botão "Salvar" → PATCH `/api/templates/{id}/ast/field/{field_id}`

### Story 49.5 — Backend: PATCH endpoint + persistência AST (P1)
Persiste alterações de `FieldNode` no Supabase.
- `PATCH /api/templates/{id}/ast/field/{field_id}`
- Body: `{bind_path: str, formatter: FormatterSpec}`
- Valida `bind_path` contra `field_tree` (optional — warn se não encontrado)
- Atualiza `template.ast_json` (nova coluna JSONB em `templates`)
- Migração Supabase: `ALTER TABLE templates ADD COLUMN ast_json JSONB`

### Story 49.6 — Frontend: `RepeatingEditor.vue` — editar loops (P1)
Permite configurar `RepeatingNode.iterator` no editor visual.
- Mostra estrutura do loop com item_template expandido
- Input `iterator`: texto livre + validação `[]` suffix
- Preview de quantos items_count_hint serão renderizados

### Story 49.7 — Export: `TemplateAstV0` → MJML/HTML final (P2)
Renderer de saída final para download/deploy do template.
- `FieldNode` → `{{bind_path | formatter_fn(pattern)}}` em Mustache/Handlebars
- `RepeatingNode` → `{{#each iterator}}...{{/each}}`
- Output: arquivo `.html` ou `.mjml` pronto para consumo pelo motor Planet Express
- Rota: `GET /api/templates/{id}/export?format=html|mjml`

---

## Ordem de execução recomendada (waves)

```
Wave 1 (P0 bloqueador): 49.1 → 49.2 → 49.3  (API + Renderer + Canvas)
Wave 2 (P1 binding):    49.4 + 49.5 em paralelo → 49.6
Wave 3 (P2 export):     49.7
```

---

## Decisões de design fixadas

1. **Invariante MJML #1630:** `bind_path` e `formatter` nunca concatenados em string antes da renderização. Renderer transforma na última etapa.
2. **Sandboxed iframe:** Canvas usa `<iframe sandbox>` para isolar CSS do template do CSS da aplicação (lição do Epic 32).
3. **AST imutável no canvas:** edições de binding não mudam a árvore de nós — apenas os campos `bind_path`/`formatter` do `FieldNode` referenciado.
4. **`raw_html` passthrough:** `RawHtmlNode` renderizado como está — não editável no editor v1.

---

## Débitos técnicos conhecidos (backlog pós-Epic 49)

| Débito | Prioridade | Descrição |
|--------|-----------|-----------|
| `xsd_type` hint em FieldNode | P2 | IDs numéricos curtos mal classificados (6/99 no spike) |
| `MultiPageNode` | P2 | Documentos multi-página requerem estrutura nova |
| `TableNode` + OCR | P2 | Integrar com `table_builder.py` Stage 3.2 Mistral |

---

## Métricas de sucesso (Go/No-Go Epic 49)

- [ ] `GET /templates/{id}/ast` retorna `TemplateAstV0` válido em <200ms
- [ ] Canvas renderiza BoletoIndividual com fidelidade visual (diff screenshot <5%)
- [ ] Editar `bind_path` num FieldNode persiste e re-renderiza corretamente
- [ ] Export MJML/HTML parseable pelo motor Planet Express (round-trip test)
