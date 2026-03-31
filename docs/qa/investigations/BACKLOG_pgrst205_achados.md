# Backlog de Achados — Investigação PGRST205

**Origem:** `/investigate` PGRST205 "Could not find table 'public.jobs'"
**Data:** 2026-03-31
**Status dos fixes principais:** RESOLVIDO (commit 11048e4 + supabase db push)

---

## Achados Colaterais (Não Bloqueantes)

### B-1 — 7 falhas pré-existentes em test_storage_gateway.py (async mock)

| Campo | Valor |
|-------|-------|
| Tipo | Tech Debt |
| Prioridade | LOW |
| Localização | `backend/tests/test_storage_gateway.py` |

**Problema:** 7 testes falham com erros de mock assíncrono (`assert_awaited_once` / `coroutine never awaited`):
- `test_upload_pdf`, `test_upload_screenshot`, `test_upload_thumbnail`, `test_upload_asset`
- `test_get_local_path_cache_miss`, `test_get_signed_url`
- `test_save_visual_data`, `test_load_visual_data_exists`, `test_delete_job`

**Causa:** `supabase_gateway.py` chama métodos de storage de forma síncrona (`.upload()`, `.download()`) mas os mocks esperam awaits. O `supabase-py v2` é síncrono — os mocks estão configurados como `AsyncMock` incorretamente.

**Sugestão:** Revisar os mocks para usar `MagicMock` (não `AsyncMock`) para as chamadas síncronas do `supabase-py v2`.

**Ação sugerida:** @dev corrigir mocks em sprint dedicado de tech debt.

---

### B-2 — CI não valida migrations do Supabase

| Campo | Valor |
|-------|-------|
| Tipo | Process Improvement |
| Prioridade | LOW |
| Localização | `.github/workflows/ci.yml` |

**Problema:** O CI roda testes com `STORAGE_MODE=local` e nunca executa `supabase db push` ou valida que as migrations são sintaticamente válidas e aplicáveis. A migration com FK orphan (`job_clusters → jobs`) teria sido detectada se o CI aplicasse as migrations contra um DB de teste.

**Sugestão:** Adicionar step no CI:
```yaml
- name: Validate migrations
  run: npx supabase db push --dry-run
  env:
    SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
```

**Ação sugerida:** @devops adicionar step de validação de migrations no CI.

---

## Status

| ID | Descrição | Status |
|----|-----------|--------|
| FIX-JOBS-001 | Migration public.jobs criada | ✅ DONE |
| FIX-JOBS-002 | save_result → upsert | ✅ DONE |
| F-3 | FK orphan job_clusters→jobs | ✅ DONE (resolvido pela migration) |
| F-4 | STORAGE_MODE=local mascara bugs | ❌ REMOVIDO |
| B-1 | 7 async mock failures | 📋 BACKLOG |
| B-2 | CI não valida migrations | 📋 BACKLOG |
