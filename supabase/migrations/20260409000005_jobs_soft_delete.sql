-- Migration: Add soft-delete support to jobs table
-- Story 41.4 — DB-011: Sem soft-delete para jobs (hard delete perde historico)
--
-- Adds deleted_at column to jobs table.
-- Application code must filter WHERE deleted_at IS NULL by default.
-- Use delete_job() function (or application-layer soft-delete) instead of DELETE.

alter table public.jobs
    add column if not exists deleted_at timestamptz;

-- Index to speed up "active jobs only" queries (WHERE deleted_at IS NULL)
create index if not exists idx_jobs_deleted_at on public.jobs(deleted_at)
    where deleted_at is null;

-- Helper function: soft-delete a job by setting deleted_at to now()
-- Returns TRUE if the job was found and marked deleted, FALSE if not found.
create or replace function public.soft_delete_job(p_job_id uuid)
returns boolean as $$
declare
    v_rows_updated integer;
begin
    update public.jobs
    set deleted_at = now()
    where id = p_job_id
      and deleted_at is null;

    get diagnostics v_rows_updated = row_count;
    return v_rows_updated > 0;
end;
$$ language plpgsql security definer;

-- Update RLS: deleted jobs should still only be visible to their owners,
-- but restrict write access on soft-deleted rows
-- (existing owner-based policies already handle reads correctly;
--  deleted rows remain accessible to admin queries via security definer functions)

comment on column public.jobs.deleted_at is
    'Soft-delete timestamp. NULL = active job. Non-NULL = deleted at that time.';
comment on function public.soft_delete_job(uuid) is
    'Soft-delete a job by setting deleted_at. Use instead of hard DELETE.';
