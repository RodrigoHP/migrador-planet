-- Migration: Create jobs table — primary job tracking table
-- Story: Investigation PGRST205 / FIX-JOBS-001
-- Must run BEFORE 20260322000001_create_job_clusters (FK dependency)

create table if not exists public.jobs (
    id          uuid primary key default gen_random_uuid(),
    status      text not null default 'pending',
    result_json jsonb,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- Index for status queries
create index if not exists idx_jobs_status on public.jobs(status);

-- RLS policies
alter table public.jobs enable row level security;

create policy "Authenticated users can read jobs"
    on public.jobs for select
    to authenticated
    using (true);

create policy "Authenticated users can insert jobs"
    on public.jobs for insert
    to authenticated
    with check (true);

create policy "Authenticated users can update jobs"
    on public.jobs for update
    to authenticated
    using (true)
    with check (true);

create policy "Authenticated users can delete jobs"
    on public.jobs for delete
    to authenticated
    using (true);
