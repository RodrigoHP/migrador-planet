-- Migration: Add updated_at trigger and status CHECK constraint on jobs table
-- Story 40.1 — DB-004 (updated_at trigger) + DB-005 (status CHECK)

-- DB-004: Create trigger function for updated_at auto-update
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- DB-004: Attach trigger to jobs table
create trigger trg_jobs_updated_at
    before update on public.jobs
    for each row
    execute function public.update_updated_at_column();

-- DB-005: Normalize any invalid status values before adding constraint
update public.jobs
set status = 'failed'
where status not in ('pending', 'running', 'completed', 'failed', 'cancelled');

-- DB-005: Add CHECK constraint on jobs.status
alter table public.jobs
    add constraint chk_jobs_status
    check (status in ('pending', 'running', 'completed', 'failed', 'cancelled'));
