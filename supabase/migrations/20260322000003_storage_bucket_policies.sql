-- Migration: Storage bucket policies for jobs and templates
-- Story 13.1 -- StorageGateway abstraction
--
-- NOTE: Bucket creation is typically done via Supabase Dashboard or CLI.
-- These policies assume the buckets already exist.  If running in a fresh
-- environment, create the buckets first:
--
--   insert into storage.buckets (id, name, public)
--   values ('jobs', 'jobs', false), ('templates', 'templates', false)
--   on conflict (id) do nothing;

-- Jobs bucket policies
create policy "Authenticated users can upload to jobs bucket"
    on storage.objects for insert
    to authenticated
    with check (bucket_id = 'jobs');

create policy "Authenticated users can read from jobs bucket"
    on storage.objects for select
    to authenticated
    using (bucket_id = 'jobs');

create policy "Authenticated users can delete from jobs bucket"
    on storage.objects for delete
    to authenticated
    using (bucket_id = 'jobs');

-- Templates bucket policies
create policy "Authenticated users can upload to templates bucket"
    on storage.objects for insert
    to authenticated
    with check (bucket_id = 'templates');

create policy "Authenticated users can read from templates bucket"
    on storage.objects for select
    to authenticated
    using (bucket_id = 'templates');

create policy "Authenticated users can delete from templates bucket"
    on storage.objects for delete
    to authenticated
    using (bucket_id = 'templates');
