# RCA Report: rca-2026-03-31-canvas-blank-selector-mismatch

**Data:** 2026-03-31
**ID:** rca-2026-03-31-canvas-blank-selector-mismatch
**Reportado por:** Investigação pós-fix (canvas branco persistiu após 70d8519)
**Preset:** adaptive:complicated
**Pipeline:** Phase 0→1→2/3(parallel)→4→5→6→6.5→8a

---

## 1. Classificação

| Campo | Valor |
|-------|-------|
| Domínio | Complicated |
| Severidade | High |
| Scope | Cross-module (backend stage5 + frontend HTMLCanvas + SyncView) |
| Confidence Score | 94 |
| Dedup Status | related |
| Related RCAs | rca-2026-03-31-canvas-blank-v2, rca-2026-03-31-canvas-blank-tree-no-labels |
| Anti-patterns | AP-009 (HTML Attribute Contract Mismatch), AP-010 (Missing Integration Test) |

---

## 2. Problema Reportado

Canvas continua em branco após o fix `70d8519` ("fix(editor): canvas em branco + árvore de
estrutura sem labels"). O fix anterior resolveu a árvore de estrutura e alguns casos de
canvas, mas a causa raiz principal — mismatch de atributo HTML entre backend e frontend —
permaneceu intacta.

**Sintomas observados:**
- Editor abre com canvas completamente branco
- Árvore de estrutura pode estar correta (fix anterior foi efetivo para ela)
- Nenhum erro no console que aponte para o mismatch diretamente
- Comportamento aparece para documentos com campos que têm bbox (`position:absolute`)

---

## 3. Causa Raiz (E1_confirmed, confidence=94)

### Root Cause Primária: HTML Attribute Contract Mismatch

**Pattern:** `html_attribute_contract_mismatch`

O backend e o frontend adotaram atributos HTML diferentes para identificar elementos de
página, sem contrato validado por testes de integração.

**Backend** (`stage5_template_generation.py:144`):
```python
# Emite nas divs de página:
f'<div data-layout-type="{layout_type}" class="page" ...'
```

**Frontend** (`HTMLCanvas.vue:228`):
```typescript
// Busca pelo atributo ERRADO:
const pages = container.querySelectorAll('[data-page]')
// → retorna NodeList vazia (0 elementos)
// → pages.length === 0
// → fallback: usa o HTML inteiro como uma única "página"
// → conteúdo position:absolute sem bbox de referência → canvas branco
```

**Mesmo mismatch** em `SyncView.vue:249`:
```typescript
const pages = el.querySelectorAll('[data-page]')
// → mesmo resultado: 0 elementos → canvas branco em sync view
```

### Mecanismo Causal

```
Canvas branco
  └─ pages.length === 0 em HTMLCanvas.vue
       └─ querySelectorAll('[data-page]') → NodeList vazia
            └─ HTML gerado pelo backend usa data-layout-type (não data-page)
                 └─ Fix 70d8519 alterou atributo no backend sem atualizar frontend
                      └─ Sem teste de integração validando o contrato de atributo
```

### Por que passa em testes unitários

O mock global de `DOMParser` nos testes de `HTMLCanvas.vue` injeta HTML com atributo
`data-page` (string hardcoded pré-fix do backend). O mock controla o DOM, então
`querySelectorAll('[data-page]')` sempre retorna elementos em teste — mascarando
completamente o mismatch em produção.

**Barrier Analysis — Test Level:** Presente mas bypassed (mock mascara contrato real).

---

## 4. Grafo Causal

```
Canvas branco (UI)
  └─ [E1] HTMLCanvas.vue não encontra páginas
       └─ querySelectorAll('[data-page]') → 0 elementos
            ├─ [E1] Backend emite data-layout-type (não data-page) → stage5:144
            │    └─ Fix 70d8519 mudou atributo sem notificação ao frontend
            └─ [E1] Sem teste de integração validando atributo esperado → AP-010
                 └─ Mock de DOMParser com data-page mascara mismatch → AP-009b

SyncView branco (achado colateral, HIGH)
  └─ [E1] SyncView.vue linha 249: mesmo querySelectorAll('[data-page]')
       └─ mesma causa raiz

Race condition (achado colateral, MEDIUM, P=15%)
  └─ [E2] visiblePages pode estar vazio quando IntersectionObserver dispara
       └─ Timing entre montagem do componente e setup do observer
```

---

## 5. Causas Secundárias

### E2 — Race condition visiblePages + IntersectionObserver (P=15%)

Em alguns cenários de carregamento rápido, o `IntersectionObserver` pode disparar seu
primeiro callback antes de `visiblePages` ser inicializado com a página 0. Isso resulta
em um renderização com estado inconsistente.

**Evidência:** Correlated (não confirmado diretamente, identificado por análise de fluxo).

### E3 — Empty HTML fallback path (P=10%)

Se o HTML gerado vier vazio ou malformado, não há guard explícito — o componente falha
silenciosamente sem feedback ao usuário.

---

## 6. Fix Requirements

### MUST (bloqueantes para AC do canvas)

**Fix 1 — HTMLCanvas.vue linha 228:**
```typescript
// ANTES (quebrado):
const pages = container.querySelectorAll('[data-page]')

// DEPOIS (correto):
const pages = container.querySelectorAll('[data-layout-type]')
```

**Fix 2 — SyncView.vue linha 249:**
```typescript
// ANTES (quebrado):
const pages = el.querySelectorAll('[data-page]')

// DEPOIS (correto):
const pages = el.querySelectorAll('[data-layout-type]')
```

### SHOULD (melhoria de resiliência)

**Fix 3 — Race condition IntersectionObserver:**
Garantir que `visiblePages` contém pelo menos a página 0 antes do primeiro callback do
`IntersectionObserver`. Opções:
- Inicializar `visiblePages` com `[0]` antes de `observe()`
- Adicionar guard no callback: `if (visiblePages.size === 0) return`

**Fix 4 — Guard no fallback path:**
```typescript
const pages = container.querySelectorAll('[data-layout-type]')
if (pages.length === 0) {
  console.warn('[HTMLCanvas] Nenhum elemento [data-layout-type] encontrado.')
  // emitir estado de erro controlado
  return
}
```

---

## 7. Testes Necessários

### Testes existentes a corrigir

| Arquivo | Problema | Correção |
|---------|---------|---------|
| `tests/HTMLCanvas.spec.*` | Mock HTML usa `data-page` | Substituir por `data-layout-type` |
| `tests/SyncView.spec.*` | Mock HTML usa `data-page` | Substituir por `data-layout-type` |

### Novos testes a adicionar

| Caso | Arquivo | Tipo |
|------|---------|------|
| `querySelectorAll` retorna 0 → comportamento controlado | HTMLCanvas.spec | Unit |
| `querySelectorAll` retorna 0 → comportamento controlado | SyncView.spec | Unit |
| Backend HTML contém `data-layout-type` → canvas renderiza | e2e ou integration | Integration |

### Contrato de atributo (test a adicionar — previne regressão futura)

```typescript
// Verificação que o contrato backend→frontend está alinhado
it('should use data-layout-type attribute matching backend output', () => {
  const backendHtml = '<div data-layout-type="document" class="page">...</div>'
  // ... montar componente com backendHtml
  // ... verificar que pages.length > 0
})
```

---

## 8. Barrier Analysis

### Swiss Cheese Model

```
Produção (canvas branco) ←─ Bug passou por 3 camadas de defesa com buracos alinhados
         │
         │   [Buraco 1]              [Buraco 2]              [Buraco 3]
         ▼       ▼                      ▼                      ▼
  ┌──────────────┐         ┌──────────────────────┐   ┌──────────────────────┐
  │ Code Review  │         │   Unit Tests         │   │ Integration Tests    │
  │ (ausente)    │         │   (bypassed)         │   │ (absent)             │
  │              │         │                      │   │                      │
  │ Nenhuma      │         │ Mock de DOMParser    │   │ Nenhum teste         │
  │ validação de │         │ com data-page        │   │ valida atributo HTML │
  │ contrato de  │         │ mascara o mismatch   │   │ emitido pelo backend │
  │ atributo     │         │                      │   │                      │
  └──────────────┘         └──────────────────────┘   └──────────────────────┘
```

### Barrier Ranking — Fix This First

| Prioridade | Camada | Fix | Impacto |
|-----------|--------|-----|---------|
| 1 | Code Level | Substituir selector em HTMLCanvas.vue + SyncView.vue | CRÍTICO — elimina causa raiz imediatamente |
| 2 | Test Level | Corrigir mocks de DOMParser para usar `data-layout-type` | HIGH — revela regressões futuras |
| 3 | Integration Test | Adicionar teste contrato atributo backend→frontend | MEDIUM — previne recorrência |
| 4 | Code Level | Guard fallback + race condition IO | MEDIUM — resiliência |

### Contrafactual por camada

- **Se Code Review tivesse validado contrato de atributo HTML ao aplicar fix 70d8519:** Bug seria detectado antes do merge. Fix: documentar contrato em comentário ou tipo TypeScript.
- **Se Unit Test usasse HTML real do backend (não mock hardcoded):** `querySelectorAll('[data-page]')` retornaria 0 e o teste falharia. Fix: usar fixtures geradas pelo backend ou validadas contra output real.
- **Se Integration Test existisse:** Toda pipeline backend→frontend teria o atributo testado e2e. Fix: adicionar teste de contrato na suite de integração.

---

## 9. Achados Colaterais

### Colateral 1 — SyncView.vue mesmo mismatch (HIGH)

**Arquivo:** `frontend/src/components/editor/SyncView.vue:249`
**Impacto:** Canvas branco em modo de visualização sincronizada (diff view)
**Status:** Coberto como MUST na story gerada (Fix 2)
**Story-worthy:** Sim — incluído na story principal

### Colateral 2 — Race condition IntersectionObserver (MEDIUM)

**Arquivo:** `frontend/src/components/editor/HTMLCanvas.vue`
**Impacto:** Em 15% dos casos, primeiro render pode ser incompleto
**Status:** Coberto como SHOULD na story gerada (Fix 3)
**Story-worthy:** Sim — incluído como AC4 na story principal

---

## 10. Pipeline Metrics

| Métrica | Valor |
|---------|-------|
| Preset | adaptive:complicated |
| Fases executadas | 0, 1, 2+3 (parallel), 4, 5, 6, 6.5, 8a |
| Confidence score final | 94 |
| SOP fast-track | false (padrão para cross-module) |
| Dedup score | related (+30 file overlap + +20 tag overlap) |
| Story gerada | docs/stories/backlog/backlog-canvas-selector-mismatch.story.md |
| Phases 2+3 | Parallel (ambas dependem apenas da Fase 1) |

---

## 11. Schema Validation Checklist (v6.0 obrigatório)

- [x] id segue padrão `rca-{date}-{slug}`
- [x] date formato YYYY-MM-DD
- [x] symptoms: lista não vazia
- [x] domain: valor válido (complicated)
- [x] severity: valor válido (high)
- [x] scope: valor válido (cross-module)
- [x] root_causes: pelo menos 1 E1_confirmed
- [x] contributing_factors: lista não vazia
- [x] fix_approach: string descritiva
- [x] files_affected: lista não vazia
- [x] tags: todos do vocabulário tag-taxonomy.yaml ou prefixo custom:
- [x] effectiveness: valor inicial "pending"
- [x] effectiveness_reviewed_at: null
- [x] sop_generated: null (sem SOP existente)
- [x] sop_fast_track_used: false
- [x] confidence_score: 94 (calculado)
- [x] dedup_status: "related"
- [x] related_rcas: lista preenchida
- [x] report: path correto
- [x] anti_patterns: lista com AP-009, AP-010
- [x] barrier_analysis: presente com contrafactual e ranking
- [x] collateral_findings: materializados (story draft gerado)
