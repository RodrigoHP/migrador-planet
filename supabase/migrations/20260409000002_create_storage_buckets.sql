-- Migration: Create storage buckets via SQL (not just policies)
-- Story 40.1 — DB-009: Buckets must exist before policies can apply
-- Previously, bucket creation was commented out in 20260322000003 and relied
-- on manual Dashboard/CLI setup. This migration ensures buckets are always
-- created as part of the migration pipeline.

insert into storage.buckets (id, name, public)
values
    ('jobs', 'jobs', false),
    ('templates', 'templates', false)
on conflict (id) do nothing;
