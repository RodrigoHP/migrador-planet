-- Migration: Create templates table for pipeline v3 template storage
-- Story 13.1 -- StorageGateway abstraction

create table if not exists public.templates (
    id          uuid primary key default gen_random_uuid(),
    name        text not null default '',
    result_json jsonb not null default '{}'::jsonb,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- Updated_at trigger
create or replace function public.update_templates_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_templates_updated_at
    before update on public.templates
    for each row
    execute function public.update_templates_updated_at();

-- RLS policies
alter table public.templates enable row level security;

create policy "Authenticated users can read templates"
    on public.templates for select
    to authenticated
    using (true);

create policy "Authenticated users can insert templates"
    on public.templates for insert
    to authenticated
    with check (true);

create policy "Authenticated users can update templates"
    on public.templates for update
    to authenticated
    using (true)
    with check (true);

create policy "Authenticated users can delete templates"
    on public.templates for delete
    to authenticated
    using (true);
