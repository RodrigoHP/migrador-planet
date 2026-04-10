-- Down migration: Remove atomic job cleanup support
-- (reverses 20260409000006_atomic_job_cleanup.sql)

drop function if exists public.atomic_delete_job(uuid, text, text);

drop policy if exists "Service role can manage pending cleanup" on public.jobs_pending_cleanup;

drop index if exists public.idx_pending_cleanup_created_at;

drop table if exists public.jobs_pending_cleanup;
