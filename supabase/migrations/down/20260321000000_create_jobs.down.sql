-- Down migration: Drop jobs table (reverses 20260321000000_create_jobs.sql)
-- WARNING: This drops all job data. Run only after confirming data is backed up.

drop index if exists public.idx_jobs_status;

drop policy if exists "Authenticated users can read jobs" on public.jobs;
drop policy if exists "Authenticated users can insert jobs" on public.jobs;
drop policy if exists "Authenticated users can update jobs" on public.jobs;
drop policy if exists "Authenticated users can delete jobs" on public.jobs;

drop table if exists public.jobs;
