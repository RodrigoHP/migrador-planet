-- Down migration: Remove soft-delete support from jobs table
-- (reverses 20260409000005_jobs_soft_delete.sql)

drop function if exists public.soft_delete_job(uuid);

drop index if exists public.idx_jobs_deleted_at;

alter table public.jobs
    drop column if exists deleted_at;
