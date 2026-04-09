# Epic 39 — Canvas UX Polish

**Status:** Done
**Branch:** `feature/epic-39-canvas-ux-polish`
**PR:** #62
**Estimativa total:** 12 pontos

---

## Objetivo

Melhorar a experiência do editor canvas com funcionalidades UX faltantes: redo, snap padrão, snap visual no resize, zoom por mousewheel/atalhos, toggle de guias, e renomeação de layouts.

## Stories

| # | Story | Pontos | Status | Gap |
|---|-------|--------|--------|-----|
| 39.1 | Implementar Redo (Ctrl+Y) | 2 | Done | I9 |
| 39.2 | Snap habilitado por padrão | 1 | Done | I10 |
| 39.3 | Column snap (backend data) | 3 | Deferida | I11 |
| 39.4 | Snap lines durante resize | 2 | Done | I12 |
| 39.5 | Verificar alinhamento existente | 1 | Done | I13 |
| 39.6 | Mousewheel zoom + atalhos | 2 | Done | I38 |
| 39.7 | Toggle guias toolbar | 1 | Done | I39 |
| 39.8 | Renomeação layout types | 1 | Done | I17 |

## Waves

- **Wave 1** (simples): 39.2, 39.7
- **Wave 2** (media): 39.1, 39.4, 39.6
- **Wave 3** (complexa): 39.5, 39.8, ~~39.3~~ (deferida)

## Decisoes

- Story 39.3 deferida: requer `column_positions` do pipeline backend que ainda nao existe
- Story 39.5 foi verificacao — nenhum codigo necessario, alinhamento ja coberto por AlignmentToolbar.vue
- ZOOM_MAX: 125% Canvas, 200% PDF — mantido conforme design original

## Resultados

- 7/8 stories implementadas
- 1750 testes passando (121 test files)
- 0 regressoes

## Change Log

| Data | Agente | Mudanca |
|------|--------|---------|
| 2026-04-09 | @aios-master | Epic criado e executado em YOLO mode |
| 2026-04-09 | @dev | Tech debt fixes (ACs, zoom constants, rename persist) |
