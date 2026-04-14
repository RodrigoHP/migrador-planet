# Recommended Approach - Story 1.1 Follow-through

## Scope
Based on `*analyze-project-structure` for Story 1.1 with:
- External API integration: `No`
- Database changes: `No`

## Recommended Service Type
- Keep implementation as **frontend-only modular monolith** inside `frontend/`
- Do not introduce backend service boundaries yet
- Preserve AIOS workflow by advancing story-by-story (`1.2` onward)

## Recommended Implementation Steps
1. Normalize Story 1.1 artifacts before QA:
   - Align task wording for `useFileSystem` vs `useProject` responsibilities
   - Keep `useFileSystem` focused on file picking and `useProject` on save/load
2. Remove avoidable build warnings:
   - Place global font import in a warning-free location
   - Keep manual chunks configured but accept empty chunks until real imports occur
3. Prepare quality foundation for Story 1.2:
   - Add real test runner baseline (`vitest` + Vue Test Utils) in upcoming story or tech debt
   - Keep `lint/typecheck/build` as mandatory pre-merge gates
4. Preserve architectural continuity:
   - Keep route-guard progression contract
   - Extend existing stores/composables instead of duplicating state logic

## Design Rules for Next Stories
- `useFileSystem`: file access concerns only
- `useProject`: project persistence and restore orchestration
- Page components should consume stores/composables; avoid direct low-level browser APIs in pages
- Keep `@` alias and strict TypeScript settings as non-negotiable baseline

## Expected Outcome
- Story 1.1 remains a stable platform layer
- Stories 1.2-1.6 can add feature behavior without refactoring foundational architecture
- Reduced risk of regressions in routing/state/persistence contracts

