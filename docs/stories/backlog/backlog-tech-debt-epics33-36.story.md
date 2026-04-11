---
origin: qa-review-post-epic-35
created: 2026-04-08
status: Done
type: tech-debt
priority: medium
identified_by: "@qa (Quinn)"
---

# Tech Debt — Epics 33-36: Cobertura de Testes e Type Safety

## Contexto

Auditoria QA pos-merge dos Epics 33-36 identificou 3 debitos tecnicos nao-bloqueantes
mas recomendados antes de novas features sobre esses componentes.

---

## Story TD-1: Testes para MonacoTabsInner.vue

**Severidade:** ALTA — componente de 14K sem nenhum teste

**Descricao:**
`frontend/src/organisms/MonacoTabsInner.vue` foi adicionado no Epic 36 (code editor)
e nao possui arquivo de testes. Componente lida com tabs de editor, switch entre arquivos,
e sincronizacao com o tree de template.

**Acceptance Criteria:**
- [ ] Criar `frontend/src/organisms/__tests__/MonacoTabsInner.spec.ts`
- [ ] Cobrir: renderizacao de tabs, switch entre tabs, sincronizacao com templateStore
- [ ] Cobrir: estados de loading, empty state, tab close
- [ ] Minimo 12 testes

**Estimativa:** P (pequena, ~1h)

---

## Story TD-2: Expandir testes do DiffViewer.vue

**Severidade:** MEDIA — 4 testes para componente de 21K

**Descricao:**
`frontend/src/organisms/DiffViewer.vue` possui apenas 4 testes em `DiffViewer.spec.ts`.
O componente foi expandido significativamente nos Epics 35 (inference panel, moved type,
PDF coordinate highlights) e a cobertura nao acompanhou.

**Acceptance Criteria:**
- [ ] Expandir `frontend/src/organisms/__tests__/DiffViewer.spec.ts`
- [ ] Cobrir: renderizacao dos paineis A/B
- [ ] Cobrir: diff summary counts (added, removed, moved, changed)
- [ ] Cobrir: inference panel — confirm/reject detection buttons
- [ ] Cobrir: pending count badge
- [ ] Cobrir: empty state sem documentos
- [ ] Minimo 15 testes adicionais (total >= 19)

**Estimativa:** P (pequena, ~1.5h)

---

## Story TD-3: Type Safety — DiffViewer e session.ts

**Severidade:** MEDIA — `ref<any>` e double casts

**Descricao:**
Tres padroes de type safety insuficiente identificados:

1. **DiffViewer.vue:236** — `ref<any>(null)` para `pdfDocA`/`pdfDocB` deve usar `PDFDocumentProxy` do pdfjs-dist
2. **session.ts:20-32** — Pattern `as unknown as Record<string,unknown>` repetido em `applyTableCellFlags()` e `reconcileFieldBindings()` — criar interfaces proprias
3. **coverageStore.ts:40** — Cast `layoutStore as unknown as {...}` desnecessario

**Acceptance Criteria:**
- [ ] Importar e usar `PDFDocumentProxy` no DiffViewer.vue em vez de `any`
- [ ] Criar interfaces tipadas para node properties em session.ts (eliminar double casts)
- [ ] Corrigir cast desnecessario no coverageStore.ts
- [ ] `npm run typecheck` passa sem erros
- [ ] Zero `as any` em codigo de producao

**Estimativa:** P (pequena, ~1h)

---

## Ordem de Prioridade

1. **TD-1** (MonacoTabsInner sem testes) — risco alto, componente descoberto
2. **TD-2** (DiffViewer cobertura) — risco medio, expansao recente sem testes
3. **TD-3** (Type Safety) — risco medio, melhoria de manutencao

## Notas

- Nenhum debito bloqueante — todos sao melhoria preventiva
- Backend bem coberto (124 testes stage5, 63 stage3)
- Zero TODO/FIXME/HACK nos arquivos dos Epics 33-36
- Zero `console.log` esquecido (1 `console.warn` justificado em codeStore.ts error handler)
