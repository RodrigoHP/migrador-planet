-- Down migration: Drop templates table (reverses 20260322000002_create_templates.sql)
-- WARNING: This drops all template data. Run only after confirming data is backed up.

drop trigger if exists trg_templates_updated_at on public.templates;
drop function if exists public.update_templates_updated_at();

drop policy if exists "Authenticated users can read templates" on public.templates;
drop policy if exists "Authenticated users can insert templates" on public.templates;
drop policy if exists "Authenticated users can update templates" on public.templates;
drop policy if exists "Authenticated users can delete templates" on public.templates;

drop table if exists public.templates;
