-- Migration: Add atomic job cleanup support
-- Story 41.4 — DB-015: Storage listing recursiva nao atomica (cleanup parcial)
--
-- Creates a jobs_pending_cleanup table to track storage paths that need to be
-- deleted when a job is soft-deleted. This enables atomic cleanup:
--   1. Soft-delete job (sets deleted_at)
--   2. Insert storage paths into jobs_pending_cleanup (same transaction)
--   3. Background worker processes cleanup asynchronously
--
-- This prevents partial cleanup: if storage deletion fails mid-way,
-- the pending_cleanup record survives and can be retried.

create table if not exists public.jobs_pending_cleanup (
    id          uuid primary key default gen_random_uuid(),
    job_id      uuid not null references public.jobs(id) on delete cascade,
    storage_bucket text not null,
    storage_prefix  text not null,
    created_at  timestamptz not null default now(),
    attempted_at timestamptz,
    attempt_count integer not null default 0,

    constraint uq_pending_cleanup_job unique (job_id)
);

-- Index for processing order (oldest first)
create index if not exists idx_pending_cleanup_created_at
    on public.jobs_pending_cleanup(created_at);

-- RLS: only service role (via security definer functions) should manage this table
alter table public.jobs_pending_cleanup enable row level security;

create policy "Service role can manage pending cleanup"
    on public.jobs_pending_cleanup
    to service_role
    using (true)
    with check (true);

-- Atomic soft-delete + schedule cleanup in a single transaction
-- Usage: SELECT atomic_delete_job('<job_id>', 'jobs', 'jobs/<job_id>');
create or replace function public.atomic_delete_job(
    p_job_id uuid,
    p_storage_bucket text,
    p_storage_prefix text
)
returns boolean as $$
declare
    v_rows_updated integer;
begin
    -- Step 1: Soft-delete the job
    update public.jobs
    set deleted_at = now()
    where id = p_job_id
      and deleted_at is null;

    get diagnostics v_rows_updated = row_count;

    if v_rows_updated = 0 then
        -- Job not found or already deleted
        return false;
    end if;

    -- Step 2: Register storage for cleanup (same transaction = atomic)
    insert into public.jobs_pending_cleanup (job_id, storage_bucket, storage_prefix)
    values (p_job_id, p_storage_bucket, p_storage_prefix)
    on conflict (job_id) do update
        set storage_bucket = excluded.storage_bucket,
            storage_prefix = excluded.storage_prefix,
            attempt_count = 0,
            attempted_at = null;

    return true;
end;
$$ language plpgsql security definer;

comment on table public.jobs_pending_cleanup is
    'Tracks storage paths to clean up after job soft-delete. Enables atomic delete + cleanup scheduling.';
comment on function public.atomic_delete_job(uuid, text, text) is
    'Atomically soft-delete a job and schedule its storage files for cleanup in one transaction.';
