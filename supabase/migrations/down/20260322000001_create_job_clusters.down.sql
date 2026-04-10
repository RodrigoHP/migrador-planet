-- Down migration: Drop job_clusters table (reverses 20260322000001_create_job_clusters.sql)
-- WARNING: This drops all cluster data. Run only after confirming data is backed up.

drop index if exists public.idx_job_clusters_job_id;

drop policy if exists "Authenticated users can read job_clusters" on public.job_clusters;
drop policy if exists "Authenticated users can insert job_clusters" on public.job_clusters;
drop policy if exists "Authenticated users can update job_clusters" on public.job_clusters;
drop policy if exists "Authenticated users can delete job_clusters" on public.job_clusters;

drop table if exists public.job_clusters;
