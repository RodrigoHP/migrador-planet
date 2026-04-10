-- Down migration: Drop storage bucket policies (reverses 20260322000003_storage_bucket_policies.sql)

-- Jobs bucket policies
drop policy if exists "Authenticated users can upload to jobs bucket" on storage.objects;
drop policy if exists "Authenticated users can read from jobs bucket" on storage.objects;
drop policy if exists "Authenticated users can delete from jobs bucket" on storage.objects;

-- Templates bucket policies
drop policy if exists "Authenticated users can upload to templates bucket" on storage.objects;
drop policy if exists "Authenticated users can read from templates bucket" on storage.objects;
drop policy if exists "Authenticated users can delete from templates bucket" on storage.objects;
