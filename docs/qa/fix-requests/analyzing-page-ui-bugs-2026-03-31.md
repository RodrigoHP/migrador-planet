# QA Bug Report: AnalyzingPage — Bugs Visuais (UI)

**Gerado:** 2026-03-31
**Reviewer:** Quinn (Test Architect / QA Agent)
**Escopo:** AnalyzingPage — Tela de Progresso do Pipeline
**Contexto:** Bugs identificados via inspeção visual manual (screenshots) comparando a implementação com o wireframe de referência `docs/wireframes/wireframe-progress-screen-v2.html`.
**Status:** Todos corrigidos pelo agente @qa nesta sessão.

---

## Resumo

| # | Severidade | Componente | Descrição | Status |
|---|-----------|-----------|-----------|--------|
| 1a | MINOR | `AnalyzingPage.vue` | `subStepPill` sem indicador de total ("de X.X") | ✅ Corrigido |
| 1b | MINOR | `AnalyzingPage.vue` + `InitializingState.vue` | Ícone ⏱ ausente nos labels de tempo estimado | ✅ Corrigido |
| 2 | MAJOR | `AnalyzingPage.vue` | UUID completo exibido no breadcrumb | ✅ Corrigido |
| 3 | MAJOR | `AnalyzingStepper.vue` | Tempo da stage sumia quando `elapsedSeconds = 0` (falsy check) | ✅ Corrigido |

---

## Bug 1a — `subStepPill` sem total de sub-etapas

**Arquivo:** `frontend/src/pages/AnalyzingPage.vue`

**Comportamento observado:**
O pill de sub-etapa exibia apenas `Sub-etapa 3.1`, sem indicar quantas sub-etapas existem na stage atual.

**Comportamento esperado (wireframe):**
`Sub-etapa 3.3 de 3.4` — exibe sub-etapa atual e a última da stage.

**Root cause:**
O `computed subStepPill` extraía apenas o número atual via regex, sem derivar o total a partir de `SUB_STEP_LABELS`.

**Fix aplicado:**
```typescript
// AnalyzingPage.vue — computed subStepPill
const subStepPill = computed(() => {
  if (!v2SubStepRaw.value) return undefined
  const match = v2SubStepRaw.value.match(/^(\d+\.\d+)/)
  if (match) {
    const current = match[1]
    const stageNum = parseInt(current.split('.')[0])
    const lastKey = Object.keys(SUB_STEP_LABELS)
      .filter((k) => k.startsWith(`${stageNum}.`))
      .sort((a, b) => parseFloat(a) - parseFloat(b))
      .at(-1)
    return lastKey ? `Sub-etapa ${current} de ${lastKey}` : `Sub-etapa ${current}`
  }
  return undefined
})
```

**Verificação:**
- Stage 3 ativa, sub-step `3.1` → pill deve exibir `Sub-etapa 3.1 de 3.4`
- Stage 4 ativa, sub-step `4.3` → pill deve exibir `Sub-etapa 4.3 de 4.7`

---

## Bug 1b — Ícone ⏱ ausente nos labels de tempo estimado

**Arquivos afetados:**
- `frontend/src/pages/AnalyzingPage.vue` (`estimatedTimeLabel`)
- `frontend/src/components/analyzing/InitializingState.vue`

**Comportamento observado:**
Labels de tempo mostravam texto sem ícone: `Calculando...`, `~25s restantes`.

**Comportamento esperado (wireframe):**
`⏱ Calculando tempo estimado...`, `⏱ ~25s restantes`.

**Root cause:**
O ícone estava presente no wireframe mas nunca foi implementado.
`InitializingState.vue` tem label hardcoded sem ícone.

**Fix aplicado:**
```typescript
// AnalyzingPage.vue — estimatedTimeLabel
if (stageElapsedTimes.value.size < 1) return '⏱ Calculando...'
if (remaining <= 0) return '⏱ Finalizando...'
if (estSecs < 60) return `⏱ ~${estSecs}s restantes`
return `⏱ ~${mins}m ${secs}s restantes`
```

```html
<!-- InitializingState.vue -->
<span class="progress-footer__time">⏱ Calculando tempo estimado...</span>
```

**Componentes verificados:**
| Componente | Resultado |
|-----------|-----------|
| `InitializingState.vue` | Corrigido ✅ |
| `AnalyzingPage.vue` (estimatedTimeLabel) | Corrigido ✅ |
| `CheckpointCard.vue` | Já tinha `&#x23F1;` ✅ |
| `ErrorCard.vue` | Sem label de tempo — não aplica ✅ |
| `CompletedStageAccordion.vue` | Tempo de duração (não estimativa) — sem ⏱ per wireframe ✅ |

---

## Bug 2 — UUID completo exibido no breadcrumb

**Arquivo:** `frontend/src/pages/AnalyzingPage.vue`

**Comportamento observado:**
Breadcrumb exibia o UUID completo do job:
`Migrador Planet  ›  Job #948e706c-833a-430d-a444-3ece0ccfc189  ›  Analisando`

**Comportamento esperado (wireframe):**
Breadcrumb de navegação por etapas, sem job ID:
`Upload  ›  Analisando  ›  Editor`

**Root cause:**
O slot `#stepper` exibia `session.jobId` como item do breadcrumb. O wireframe define o breadcrumb como navegação entre etapas do fluxo (Upload → Analisando → Editor), não como identificador do job.

**Fix aplicado:**
```html
<nav class="topbar-breadcrumb" aria-label="Breadcrumb">
  <span class="topbar-breadcrumb__item">Upload</span>
  <span class="topbar-breadcrumb__sep" aria-hidden="true">&#x203A;</span>
  <span class="topbar-breadcrumb__item topbar-breadcrumb__item--active" aria-current="page">Analisando</span>
  <span class="topbar-breadcrumb__sep" aria-hidden="true">&#x203A;</span>
  <span class="topbar-breadcrumb__item topbar-breadcrumb__item--future">Editor</span>
</nav>
```

CSS adicionado para item futuro (dimmed):
```css
.topbar-breadcrumb__item--future { color: #cbd5e1; }
```

**Verificação:**
- Breadcrumb deve mostrar `Upload › Analisando › Editor`
- "Editor" deve aparecer em cinza claro (#cbd5e1)
- UUID não deve aparecer em lugar algum no header

---

## Bug 3 — Tempo da stage some quando `elapsedSeconds = 0`

**Arquivo:** `frontend/src/components/analyzing/AnalyzingStepper.vue`

**Comportamento observado:**
Stages que completavam em menos de 500ms tinham o tempo calculado como `0` segundos (via `Math.round`). O `v-if="stageTimes[stage.stage]"` avaliava `0` como falsy em JavaScript, ocultando o label de tempo.

**Comportamento esperado:**
Todas as stages concluídas devem exibir o tempo, incluindo `0s`.

**Root cause:**
```html
<!-- ANTES — falsy check oculta 0 -->
<span v-if="stageTimes[stage.stage]" class="stepper__time">
```
`stageTimes[stage.stage] === 0` → `v-if` avalia como `false` → label some.

**Fix aplicado:**
```html
<!-- DEPOIS — verifica existência da chave, não o valor -->
<span v-if="stage.stage in stageTimes" class="stepper__time">
  {{ formatTime(stageTimes[stage.stage]) }}
</span>
```

**Outros componentes verificados:** `CompletedStageAccordion.vue` e `CompletedSummary.vue` não usam `v-if` no tempo — não afetados.

**Verificação:**
- Stage que completa em < 500ms deve mostrar `0s` no stepper
- Stages com tempo > 0 continuam exibindo normalmente

---

## Arquivos Modificados

| Arquivo | Bugs |
|---------|------|
| `frontend/src/pages/AnalyzingPage.vue` | 1a, 1b, 2 |
| `frontend/src/components/analyzing/InitializingState.vue` | 1b |
| `frontend/src/components/analyzing/AnalyzingStepper.vue` | 3 |
