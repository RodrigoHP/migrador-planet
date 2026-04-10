-- Migration: Micro Quick Wins (Story 41.1)
-- DB-010: Index on jobs.created_at for temporal queries
-- DB-013: Optional FK templates.source_job_id -> jobs.id (traceability)
-- DB-014: UPDATE policy for storage buckets (was missing)

-- ============================================================
-- DB-010: Index on jobs.created_at
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON public.jobs(created_at);

-- ============================================================
-- DB-013: Add source_job_id FK to templates table
-- Optional column (nullable) — existing templates keep NULL.
-- ============================================================

ALTER TABLE public.templates
    ADD COLUMN IF NOT EXISTS source_job_id uuid REFERENCES public.jobs(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_templates_source_job_id ON public.templates(source_job_id);

-- ============================================================
-- DB-014: UPDATE policy for storage buckets
-- Original policies (20260322000003) only had INSERT/SELECT/DELETE.
-- ============================================================

CREATE POLICY "Authenticated users can update in jobs bucket"
    ON storage.objects FOR UPDATE
    TO authenticated
    USING (bucket_id = 'jobs')
    WITH CHECK (bucket_id = 'jobs');

CREATE POLICY "Authenticated users can update in templates bucket"
    ON storage.objects FOR UPDATE
    TO authenticated
    USING (bucket_id = 'templates')
    WITH CHECK (bucket_id = 'templates');
