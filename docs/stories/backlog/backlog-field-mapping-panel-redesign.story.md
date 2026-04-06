# Backlog: Field Mapping Panel — Redesign Completo

**Origem:** RCA investigation 2026-04-01 — @qa Quinn
**Trigger:** Investigação profunda da aba Campos + achados colaterais de UX quebrada
**Prioridade sugerida:** Alta — fluxo central de uso do editor

---

## Problema Documentado (evidências do código)

### 1. Arquitetura de 2 tabs separadas não funciona

O usuário precisa navegar entre **aba Campos** e **aba Estrutura** para fazer uma operação única:

```
Aba Campos     → lista os campos do PDF / XSD
Aba Estrutura  → é onde drag/context-menu permite re-mapear
Inspector      → mostra binding mas read-only
```

Não existe nenhum caminho de "ver campo errado → corrigir inline". O usuário precisa:
1. Ver o campo errado na aba Campos
2. Trocar para aba Estrutura
3. Fazer drag ou right-click → "Remover binding"
4. Voltar para Campos
5. Arrastar o campo correto para o nó

**Evidência:** `StructureTree.vue:337` — `removeBinding` só via context menu na Estrutura.
`ElementInspector.vue:142` — binding é `InspectorField` read-only, sem edição.

---

### 2. Campos mostrados com nomes sem sentido

Os nomes na lista (ex: `4.978,54`, `000`, `30/03/2026`) são o **texto bruto do PDF**:

```python
# stage4_field_mapping.py:687
"name": label_text or pdf_text   ← raw PDF text quando não tem label
```

O usuário não consegue identificar qual campo é qual apenas pela lista.

---

### 3. Campos XSD sem match são invisíveis

`validation_result.unmapped_xsd_fields` existe no backend mas é descartado no frontend.
Campos que o XSD exige mas não apareceram no PDF não aparecem em lugar nenhum.

```
session.ts:178 → loadPipelineFields(result.field_mappings)
                                    ↑ só PDF fields — unmapped_xsd_fields ignorado
```

---

### 4. Campos ambíguos (🟨) sem UI de resolução

`FieldNavItem.vue:81` dispara `emit('open-ambiguous')` mas `FieldNavigator.vue` não tem handler para esse evento. O modal de resolução nunca abre.

---

### 5. Drag & drop sem feedback de falha

Arrastar um campo para fora de um alvo válido no Canvas não dá nenhum feedback visual. O usuário não sabe se o drop funcionou.

---

## Redesign Proposto (escopo a validar com @pm/@sm)

### Opção A — Panel Unificado "Mapeamento de Campos"

Substituir as 2 abas separadas por um único painel integrado:

```
┌─────────────────────────────────────┐
│ 📊 Mapeamento de Campos   25/55 ██░ │
├─────────────────────────────────────┤
│ [Buscar campo...]  [Todos ▼]        │
├─────────────────────────────────────┤
│ 🟩 Vencimento        → data.vencim │ ← clica abre dropdown XSD inline
│ 🟥 Valor Cobrado     → (sem vínculo)│ ← arrasta ou clica para vincular
│ 🟨 Beneficiário      → ? 3 opções  │ ← badge "resolver" abre modal
│ 🔴 data.nome_cliente → (XSD only)  │ ← XSD field sem PDF match
└─────────────────────────────────────┘
```

Cada linha tem:
- **Nome semântico** (label do XSD quando disponível, não raw PDF text)
- **Binding atual** com pill clicável para trocar
- **Ação rápida** inline (trocar, remover, resolver ambiguidade)

### Opção B — Inspector com edição de binding

Manter as abas, mas no Inspector adicionar:
- Dropdown editável no campo "Binding" (busca nos `flat_paths` do XSD)
- Botão "Remover binding" direto no Inspector
- Badge de status (🟩🟥🟨) no Inspector

---

## Stories sugeridas

| # | Título | Escopo |
|---|--------|--------|
| X.1 | Painel unificado campo+estrutura | Novo componente FieldMappingPanel |
| X.2 | Inline binding editor no Inspector | Dropdown editável + remove |
| X.3 | Modal de resolução de ambiguidade | Handler para open-ambiguous event |
| X.4 | XSD fields sem match visíveis | Incluir unmapped_xsd_fields no panel |
| X.5 | Nomes semânticos nos campos | Label XSD como nome preferencial |

---

## Arquivos impactados

```
frontend/src/organisms/FieldNavigator.vue         (substituir ou extender)
frontend/src/organisms/StructureTree.vue           (remover duplicação de binding mgmt)
frontend/src/organisms/inspectors/ElementInspector.vue  (binding editável)
frontend/src/stores/mapping.ts                     (novos actions)
frontend/src/stores/session.ts                     (surfaçar unmapped_xsd_fields)
frontend/src/types/field-navigator.types.ts        (novos tipos)
```

---

## Contexto RCA

- `rca-2026-04-01-campos-xsd-invisivel` — XSD fields invisíveis
- `rca-2026-04-01-fieldnav-click-silent-failure` — click quebrado (CORRIGIDO)
- Fix aplicado em `session.ts:reconcileFieldBindings()` e `FieldNavigator.vue:onSelectField()`
