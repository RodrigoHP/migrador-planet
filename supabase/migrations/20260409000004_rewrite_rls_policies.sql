-- Migration: Rewrite RLS policies with owner-based access (auth.uid() = user_id)
-- Story 40.2 — DB-001: RLS policies com USING (true) — acesso blanket
-- CRITICAL: Replaces permissive USING(true) with actual owner filtering.
--
-- NOTE: Rows with user_id IS NULL (pre-migration data) are accessible to
-- all authenticated users until backfill assigns ownership. This is
-- intentional for gradual enforcement.

-- ============================================================
-- JOBS TABLE — drop old permissive policies, create owner-based
-- ============================================================

drop policy if exists "Authenticated users can read jobs" on public.jobs;
drop policy if exists "Authenticated users can insert jobs" on public.jobs;
drop policy if exists "Authenticated users can update jobs" on public.jobs;
drop policy if exists "Authenticated users can delete jobs" on public.jobs;

-- SELECT: owner sees own rows; NULL user_id visible to all (gradual migration)
create policy "Owner can read own jobs"
    on public.jobs for select
    to authenticated
    using (user_id = auth.uid() or user_id is null);

-- INSERT: user_id must match the authenticated user
create policy "Owner can insert own jobs"
    on public.jobs for insert
    to authenticated
    with check (user_id = auth.uid());

-- UPDATE: only owner can update
create policy "Owner can update own jobs"
    on public.jobs for update
    to authenticated
    using (user_id = auth.uid() or user_id is null)
    with check (user_id = auth.uid());

-- DELETE: only owner can delete
create policy "Owner can delete own jobs"
    on public.jobs for delete
    to authenticated
    using (user_id = auth.uid() or user_id is null);

-- ============================================================
-- TEMPLATES TABLE
-- ============================================================

drop policy if exists "Authenticated users can read templates" on public.templates;
drop policy if exists "Authenticated users can insert templates" on public.templates;
drop policy if exists "Authenticated users can update templates" on public.templates;
drop policy if exists "Authenticated users can delete templates" on public.templates;

create policy "Owner can read own templates"
    on public.templates for select
    to authenticated
    using (user_id = auth.uid() or user_id is null);

create policy "Owner can insert own templates"
    on public.templates for insert
    to authenticated
    with check (user_id = auth.uid());

create policy "Owner can update own templates"
    on public.templates for update
    to authenticated
    using (user_id = auth.uid() or user_id is null)
    with check (user_id = auth.uid());

create policy "Owner can delete own templates"
    on public.templates for delete
    to authenticated
    using (user_id = auth.uid() or user_id is null);

-- ============================================================
-- JOB_CLUSTERS TABLE
-- ============================================================

drop policy if exists "Authenticated users can read job_clusters" on public.job_clusters;
drop policy if exists "Authenticated users can insert job_clusters" on public.job_clusters;
drop policy if exists "Authenticated users can update job_clusters" on public.job_clusters;
drop policy if exists "Authenticated users can delete job_clusters" on public.job_clusters;

create policy "Owner can read own job_clusters"
    on public.job_clusters for select
    to authenticated
    using (user_id = auth.uid() or user_id is null);

create policy "Owner can insert own job_clusters"
    on public.job_clusters for insert
    to authenticated
    with check (user_id = auth.uid());

create policy "Owner can update own job_clusters"
    on public.job_clusters for update
    to authenticated
    using (user_id = auth.uid() or user_id is null)
    with check (user_id = auth.uid());

create policy "Owner can delete own job_clusters"
    on public.job_clusters for delete
    to authenticated
    using (user_id = auth.uid() or user_id is null);
