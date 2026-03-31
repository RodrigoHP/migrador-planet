# QA Fix Request: public.jobs — Migration Ausente + save_result Bug

**Generated:** 2026-03-31
**Investigation Source:** `/investigate` — PGRST205 "Could not find the table 'public.jobs'"
**Reviewer:** Quinn (Test Architect)
**Severity:** HIGH

---

## Contexto

Pipeline para na Stage 5 (Geração do Template) com o erro:

```
Storage falhou no Template Generation:
{'message': "Could not find the table 'public.jobs' in the schema cache",
 'code': 'PGRST205', 'hint': None, 'details': None}
```

**Root cause:** A tabela `public.jobs` **nunca foi criada** via migration. O Epic 13 criou `job_clusters` (que referencia `public.jobs` via FK) e políticas de storage, mas omitiu a migration da tabela principal.

---

## Instructions for @dev

Fix ONLY os dois issues listados abaixo. Não adicionar features ou refatorar código não relacionado.

**Processo:**
1. Ler cada issue com atenção
2. Aplicar o fix exato descrito
3. Verificar com os passos de verificação
4. Marcar como fixado
5. Rodar os testes antes de marcar completo

---

## Summary

| Severity | Count | Status |
|----------|-------|--------|
| HIGH | 2 | Must fix before next deploy |
| MEDIUM | 0 | — |
| LOW | 2 | Opcional |

---

## Issues to Fix

### 1. [HIGH] Migration ausente — tabela `public.jobs` não existe

**Issue ID:** FIX-JOBS-001

**Location:** `supabase/migrations/` (arquivo novo a criar)

**Problem:**
Não existe nenhuma migration que crie `public.jobs`. O arquivo `20260322000001_create_job_clusters.sql` faz referência à tabela na linha 6:
```sql
job_id uuid not null references public.jobs(id) on delete cascade,
```
Mas a tabela referenciada nunca foi criada. Isso causa:
1. `PGRST205` ao chamar `.table("jobs")` via PostgREST
2. A própria migration `job_clusters` também falharia em um DB fresh

**Expected:**
Criar `supabase/migrations/20260321000000_create_jobs.sql` com conteúdo:

```sql
-- Migration: Create jobs table — primary job tracking table
-- Must run BEFORE 20260322000001_create_job_clusters (FK dependency)

create table if not exists public.jobs (
    id          uuid primary key default gen_random_uuid(),
    status      text not null default 'pending',
    result_json jsonb,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- Index for status queries
create index if not exists idx_jobs_status on public.jobs(status);

-- RLS policies
alter table public.jobs enable row level security;

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
```

**Verificação:**
- [ ] Arquivo `supabase/migrations/20260321000000_create_jobs.sql` criado
- [ ] Timestamp `20260321` é anterior a `20260322000001` (ordem de execução correta)
- [ ] `supabase db push` aplicado no ambiente de produção sem erros

**Status:** [ ] Fixed

---

### 2. [HIGH] `save_result()` usa `.update()` sem garantir row existente

**Issue ID:** FIX-JOBS-002

**Location:** `backend/services/storage/supabase_gateway.py:95-101`

**Problem:**
```python
async def save_result(self, job_id: str, result_json: dict) -> None:
    (
        self._supabase.table("jobs")
        .update({"result_json": result_json, "status": "completed"})
        .eq("id", job_id)
        .execute()
    )
```
`.update()` sem row pré-existente silenciosamente atualiza 0 rows. Não há nenhum `.insert()` de `public.jobs` em nenhum lugar do codebase — a row nunca é criada antes de `save_result` ser chamado.

**Expected:**
Trocar `.update()` por `.upsert()` para garantir que a row seja criada se não existir:

```python
async def save_result(self, job_id: str, result_json: dict) -> None:
    (
        self._supabase.table("jobs")
        .upsert({"id": job_id, "result_json": result_json, "status": "completed"})
        .execute()
    )
```

**Verificação:**
- [ ] `save_result` usa `.upsert()` em vez de `.update()`
- [ ] Teste unitário existente em `test_storage_gateway.py` ainda passa
- [ ] Adicionar teste: chamar `save_result` sem row prévia → row criada com status "completed"

**Status:** [ ] Fixed

---

## Issues Adicionais (Low — Opcional)

### L-1. [LOW] `20260322000001` falharia em DB fresh por FK orphan

**Location:** `supabase/migrations/20260322000001_create_job_clusters.sql:6`

Depois de aplicar o Fix 1 acima, esta issue deixa de existir. Documentada apenas para registro.

### L-2. [LOW] `STORAGE_MODE=local` mascara bugs Supabase em dev

**Location:** `backend/.env:2`

Considerar criar um ambiente de staging/CI com `STORAGE_MODE=supabase` para capturar esses bugs antes do deploy em produção. Não requer mudança de código.

---

## Constraints

**CRITICAL: @dev deve seguir estas restrições:**

- [ ] Fix ONLY os dois issues HIGH acima
- [ ] NÃO adicionar features
- [ ] NÃO refatorar código não relacionado
- [ ] Rodar testes antes de marcar completo: `cd backend && python -m pytest`
- [ ] Atualizar story file list se novos arquivos forem criados

---

## Arquivos a Criar/Modificar

| Ação | Arquivo |
|------|---------|
| CRIAR | `supabase/migrations/20260321000000_create_jobs.sql` |
| MODIFICAR | `backend/services/storage/supabase_gateway.py` (linha 97) |
| ADICIONAR TESTE | `backend/tests/test_storage_gateway.py` (upsert sem row prévia) |

---

## After Fixing

1. Marcar cada issue como fixado neste documento
2. Rodar `supabase db push` no ambiente de produção
3. Solicitar re-review: `@qa *review` para validar

---

_Generated by Quinn (Test Architect) — Investigation: PGRST205 public.jobs_
