-- Migration: Create job_clusters table for pipeline v3 layout clustering
-- Story 13.1 -- StorageGateway abstraction

create table if not exists public.job_clusters (
    id          uuid primary key default gen_random_uuid(),
    job_id      uuid not null references public.jobs(id) on delete cascade,
    cluster_id  integer not null,
    pages       jsonb not null default '[]'::jsonb,
    representative jsonb,
    confidence  jsonb,
    created_at  timestamptz not null default now(),

    -- One cluster_id per job
    constraint uq_job_clusters_job_cluster unique (job_id, cluster_id)
);

-- Index for fast lookup by job
create index if not exists idx_job_clusters_job_id on public.job_clusters(job_id);

-- RLS policies
alter table public.job_clusters enable row level security;

create policy "Authenticated users can read job_clusters"
    on public.job_clusters for select
    to authenticated
    using (true);

create policy "Authenticated users can insert job_clusters"
    on public.job_clusters for insert
    to authenticated
    with check (true);

create policy "Authenticated users can update job_clusters"
    on public.job_clusters for update
    to authenticated
    using (true)
    with check (true);

create policy "Authenticated users can delete job_clusters"
    on public.job_clusters for delete
    to authenticated
    using (true);
