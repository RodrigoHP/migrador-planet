-- Down migration: Revert RLS policies from owner-based back to authenticated-only
-- (reverses 20260409000004_rewrite_rls_policies.sql)

-- ============================================================
-- JOBS TABLE — revert to permissive authenticated policies
-- ============================================================

drop policy if exists "Owner can read own jobs" on public.jobs;
drop policy if exists "Owner can insert own jobs" on public.jobs;
drop policy if exists "Owner can update own jobs" on public.jobs;
drop policy if exists "Owner can delete own jobs" on public.jobs;

create policy "Authenticated users can read jobs"
    on public.jobs for select
    to authenticated
    using (true);

create policy "Authenticated users can insert jobs"
    on public.jobs for insert
    to authenticated
    with check (true);

create policy "Authenticated users can update jobs"
    on public.jobs for update
    to authenticated
    using (true)
    with check (true);

create policy "Authenticated users can delete jobs"
    on public.jobs for delete
    to authenticated
    using (true);

-- ============================================================
-- TEMPLATES TABLE
-- ============================================================

drop policy if exists "Owner can read own templates" on public.templates;
drop policy if exists "Owner can insert own templates" on public.templates;
drop policy if exists "Owner can update own templates" on public.templates;
drop policy if exists "Owner can delete own templates" on public.templates;

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

-- ============================================================
-- JOB_CLUSTERS TABLE
-- ============================================================

drop policy if exists "Owner can read own job_clusters" on public.job_clusters;
drop policy if exists "Owner can insert own job_clusters" on public.job_clusters;
drop policy if exists "Owner can update own job_clusters" on public.job_clusters;
drop policy if exists "Owner can delete own job_clusters" on public.job_clusters;

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
