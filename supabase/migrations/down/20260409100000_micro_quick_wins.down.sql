-- Down migration: Remove micro quick wins (reverses 20260409100000_micro_quick_wins.sql)
-- Story 41.1 reversals

-- DB-014: Remove storage bucket UPDATE policies
drop policy if exists "Authenticated users can update in jobs bucket" on storage.objects;
drop policy if exists "Authenticated users can update in templates bucket" on storage.objects;

-- DB-013: Remove source_job_id FK and index from templates
drop index if exists public.idx_templates_source_job_id;
alter table public.templates drop column if exists source_job_id;

-- DB-010: Remove created_at index on jobs
drop index if exists public.idx_jobs_created_at;
