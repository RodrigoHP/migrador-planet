# Ready for QA Re-Review

**Investigation:** PGRST205 — public.jobs
**Fixed By:** @dev (Dex)
**Timestamp:** 2026-03-31
**Commit:** 11048e4

## Issues Fixed

- [x] FIX-JOBS-001: Criada migration `supabase/migrations/20260321000000_create_jobs.sql`
- [x] FIX-JOBS-002: `save_result` usa `.upsert()` em vez de `.update()`

## Verification Results

- ✅ `test_save_result` — upsert chamado com payload correto
- ✅ `test_save_result_upserts_when_no_prior_row` — upsert sem row prévia, `.update()` não chamado
- ✅ Falha `test_upload_pdf` confirmada como pré-existente (não introduzida por estes fixes)

## Arquivos Modificados

- `supabase/migrations/20260321000000_create_jobs.sql` (novo)
- `backend/services/storage/supabase_gateway.py` (linha 97-100)
- `backend/tests/test_storage_gateway.py` (atualizado + novo teste)

## Ação pendente em produção

`supabase db push` precisa ser executado no ambiente de produção para aplicar a migration.

---

**Next Step:** @devops executa `supabase db push` em prod → pipeline Stage 5 funciona.
