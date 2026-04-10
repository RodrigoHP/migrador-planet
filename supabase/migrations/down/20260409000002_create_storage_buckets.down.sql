-- Down migration: Remove storage buckets created by migration
-- (reverses 20260409000002_create_storage_buckets.sql)
-- WARNING: This removes bucket metadata but does NOT delete stored objects.
-- Delete objects via Supabase Dashboard or CLI before running this.

delete from storage.buckets where id in ('jobs', 'templates');
