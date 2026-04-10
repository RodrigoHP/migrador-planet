-- Down migration: Remove user_id columns from all data tables
-- (reverses 20260409000003_add_user_id_columns.sql)
-- WARNING: All user ownership data will be permanently lost.

-- job_clusters table
drop index if exists public.idx_job_clusters_user_id;
alter table public.job_clusters drop column if exists user_id;

-- templates table
drop index if exists public.idx_templates_user_id;
alter table public.templates drop column if exists user_id;

-- jobs table
drop index if exists public.idx_jobs_user_id;
alter table public.jobs drop column if exists user_id;
