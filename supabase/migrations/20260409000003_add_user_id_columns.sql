-- Migration: Add user_id column to all data tables for multi-tenancy
-- Story 40.2 — DB-002: Sem multi-tenancy / user_id em nenhuma tabela
-- CRITICAL: This is the foundation for owner-based RLS policies.
--
-- Strategy: Add as NULLABLE first. Existing rows will have user_id = NULL.
-- A future migration will enforce NOT NULL after backfill.
--
-- Backfill strategy for existing data:
--   UPDATE public.jobs SET user_id = '<admin-user-uuid>' WHERE user_id IS NULL;
--   UPDATE public.templates SET user_id = '<admin-user-uuid>' WHERE user_id IS NULL;
--   UPDATE public.job_clusters SET user_id = '<admin-user-uuid>' WHERE user_id IS NULL;
--   Then: ALTER TABLE ... ALTER COLUMN user_id SET NOT NULL;

-- jobs table
alter table public.jobs
    add column if not exists user_id uuid references auth.users(id);

create index if not exists idx_jobs_user_id on public.jobs(user_id);

-- templates table
alter table public.templates
    add column if not exists user_id uuid references auth.users(id);

create index if not exists idx_templates_user_id on public.templates(user_id);

-- job_clusters table
alter table public.job_clusters
    add column if not exists user_id uuid references auth.users(id);

create index if not exists idx_job_clusters_user_id on public.job_clusters(user_id);
