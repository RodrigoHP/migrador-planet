-- Down migration: Remove updated_at trigger and status CHECK constraint
-- (reverses 20260409000001_jobs_trigger_and_check.sql)

-- DB-004: Remove trigger and function
drop trigger if exists trg_jobs_updated_at on public.jobs;
drop function if exists public.update_updated_at_column();

-- DB-005: Remove CHECK constraint
alter table public.jobs
    drop constraint if exists chk_jobs_status;
