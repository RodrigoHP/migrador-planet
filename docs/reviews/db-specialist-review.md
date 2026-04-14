# Database Specialist Review

**Reviewer:** @data-engineer (Dara)
**Date:** 2026-04-09
**Input:** `docs/prd/technical-debt-DRAFT.md` (Sections 2, 5, 6, 7) + `supabase/docs/DB-AUDIT.md`

---

## Debitos Validados

| ID | Debito | Severidade Original | Severidade Ajustada | Horas | Complexidade | Notas |
|----|--------|---------------------|---------------------|-------|-------------|-------|
| DB-001 | RLS policies com `USING (true)` | CRITICAL | **CRITICAL** | 8h | Complex | Confirmado. Todas as 3 tabelas + storage buckets. Requer DB-002 como pre-requisito. |
| DB-002 | Sem multi-tenancy / `user_id` | CRITICAL | **CRITICAL** | 12h | Complex | Confirmado. Nenhuma tabela tem `user_id`. Bloqueia DB-001 e DB-003. Inclui: migration + backfill + application code + testes. |
| DB-003 | Service role key bypassa RLS | CRITICAL | **HIGH** | 4h | Medium | **Rebaixado.** O backend PRECISA de service role para operacoes de storage (upload, download, signed URLs) -- nao ha como evitar com anon key. O risco real eh a ausencia de audit logging e o uso indiscriminado para operacoes de leitura. A key em si nao eh o debito; o debito eh usa-la para TUDO sem separar operacoes privilegiadas de nao-privilegiadas. |
| DB-004 | `jobs.updated_at` sem trigger | HIGH | **HIGH** | 1h | Simple | Confirmado. Trigger existe para `templates` mas nao para `jobs`. Copy-paste do pattern existente. |
| DB-005 | `jobs.status` sem CHECK constraint | HIGH | **HIGH** | 1h | Simple | Confirmado. Valores validos: `pending`, `running`, `completed`, `failed`, `cancelled`. Migracao trivial. |
| DB-006 | Sem rollback migrations | HIGH | **MEDIUM** | 6h | Medium | **Rebaixado.** Com apenas 4 migration files e schema simples (3 tabelas), o risco operacional eh baixo. Rollback manual eh viavel. Importante para quando schema crescer. |
| DB-007 | Supabase SDK sincrono em async | HIGH | **HIGH** | 6h | Medium | Confirmado. Verificado: `supabase_gateway.py` declara metodos `async` mas todas as chamadas ao SDK sao sincronas (`.upload()`, `.download()`, `.upsert()`, `.execute()`). Nenhum uso de `asyncio.to_thread()`. Sob carga concorrente, bloqueia o event loop. |
| DB-008 | Dual state stores (3 lugares) | HIGH | **HIGH** | 8h | Complex | Confirmado. Verificado que `recover_running_jobs()` existe no `job_store.py` mas NAO eh chamado no lifespan handler (`main.py:35-39`). Alem disso, `save_result()` no `supabase_gateway.py` faz upsert com status `completed` sem verificar o status atual -- race condition possivel. |
| DB-009 | Buckets nao criados nas migrations | MEDIUM | **MEDIUM** | 1h | Simple | Confirmado. SQL de criacao esta em comentario na migration `20260322000003`. |
| DB-010 | Sem indice `created_at` em `jobs` | MEDIUM | **LOW** | 0.5h | Simple | **Rebaixado.** Com volume atual (dezenas/centenas de jobs), sequential scan eh aceitavel. Indice so se justifica com >10K rows. Manter como melhoria futura. |
| DB-011 | Storage cleanup nao atomico | MEDIUM | **MEDIUM** | 4h | Medium | Confirmado. Bug adicional encontrado: `delete_job()` em `supabase_gateway.py:171-174` lista apenas o top-level (`list(f"jobs/{job_id}")`) mas os arquivos estao em subdiretorios (`pdfs/`, `screenshots/`, `thumbnails/`, `assets/`). O `remove()` provavelmente falha silenciosamente para a maioria dos arquivos. |
| DB-012 | Sem safeguard `AUTH_DISABLED` prod | MEDIUM | **MEDIUM** | 0.5h | Simple | Confirmado. `_AUTH_DISABLED` eh lido no modulo-level em `middleware/auth.py:33` sem check de environment. |
| DB-013 | `templates` sem FK para `jobs` | LOW | **LOW** | 1h | Simple | Confirmado. Por design, templates sao entidades independentes. FK opcional eh adequado. |
| DB-014 | Sem UPDATE policy em `storage.objects` | LOW | **LOW** | 0.5h | Simple | Confirmado. Impacto minimo -- backend usa service role. |
| REDIS-001 | Sem prefixo de app nas keys | LOW | **LOW** | 0.5h | Simple | Confirmado. Pattern atual: `job:{uuid}`. Deveria ser `migrador:job:{uuid}`. |
| REDIS-002 | Sem reconnection / circuit breaker | MEDIUM | **MEDIUM** | 4h | Medium | Confirmado. Fallback para InMemoryJobStore so ocorre em `get_job_store()` no startup. Se Redis cai depois, `save_job`/`get_job` lancam excecoes nao tratadas em varias code paths. |
| REDIS-003 | `all_jobs()` usa `scan_iter` | LOW | **LOW** | 1h | Simple | Confirmado. Aceitavel com TTL de 1h limitando o keyspace. |

---

## Debitos Removidos (False Positives)

Nenhum debito removido. Todos os 17 debitos do audit original sao problemas reais e foram corretamente capturados no DRAFT.

---

## Debitos Adicionados

### DB-015: `delete_job()` nao lista subdiretorios no storage

**Severidade:** MEDIUM
**Horas:** 2h
**Complexidade:** Simple

O metodo `delete_job()` em `supabase_gateway.py:171` faz `list(f"jobs/{job_id}")` que retorna apenas o conteudo do diretorio raiz do job. Arquivos em subdiretorios (`pdfs/`, `screenshots/`, `thumbnails/`, `assets/`) nao sao listados e portanto nao sao removidos. Isso agrava DB-011 -- alem do cleanup nao ser atomico, ele tambem eh incompleto.

**Fix:** Listar recursivamente todos os subdiretorios, ou usar um pattern como `list(f"jobs/{job_id}", {"recursive": true})` se suportado pela API, ou listar cada subdir explicitamente.

### DB-016: `recover_running_jobs()` nao eh chamado no lifespan

**Severidade:** HIGH
**Horas:** 0.5h
**Complexidade:** Simple

A funcao `recover_running_jobs()` existe em `job_store.py:195-217` e esta corretamente implementada, mas NUNCA eh chamada. O lifespan handler em `main.py:35-39` chama apenas `_cleanup_orphaned_dirs()`. Jobs com status `running` no Redis permanecem nesse estado indefinidamente apos restart do servidor.

**Fix:** Adicionar `recover_running_jobs()` ao lifespan handler, antes do `yield`.

**Nota:** Este debito foi mencionado indiretamente em SYS-004 ("recover_running_jobs() existe mas NAO eh chamado no lifespan handler") mas nao recebeu um ID proprio. Merece tratamento independente porque o fix eh trivial (0.5h) e tem impacto direto na confiabilidade.

### DB-017: `save_result()` faz upsert sem condicao de status

**Severidade:** LOW
**Horas:** 1h
**Complexidade:** Simple

O metodo `save_result()` em `supabase_gateway.py:121-126` faz upsert com `status: "completed"` sem verificar o status atual do job. Se um job foi cancelado (`cancelled`) ou ja falhou (`failed`), o upsert sobrescreve o status para `completed`. Isso pode mascarar cancelamentos.

**Fix:** Usar `.update().eq("id", job_id).neq("status", "cancelled")` ou verificar o status antes do upsert.

### REDIS-004: Redis client eh sincrono em contexto async

**Severidade:** MEDIUM
**Horas:** 3h
**Complexidade:** Medium

Similar ao DB-007, o `RedisJobStore` usa `redis.from_url()` (cliente sincrono) em vez de `redis.asyncio.from_url()`. Chamadas como `setex`, `get`, `scan_iter` bloqueiam o event loop. Com Redis local/Railway o impacto eh minimo (~1ms), mas com Redis remoto com latencia, pode causar frame drops no SSE streaming.

**Fix:** Migrar para `redis.asyncio` client ou wrappear chamadas em `asyncio.to_thread()`.

---

## Cross-Cutting Review

### CC-001: Split-Brain State Management

**Validacao:** CONFIRMADO com agravamento.

O DRAFT descreve corretamente o problema de 3 state stores (in-memory, Redis, Supabase). Porem, a situacao eh pior do que descrita:

1. **`recover_running_jobs()` nunca eh chamado** (DB-016) -- o mecanismo de recuperacao existe mas esta desconectado. Isso significa que jobs "running" no Redis permanecem em estado fantasma apos restart.
2. **`save_result()` nao respeita cancelamentos** (DB-017) -- o sync final para Supabase pode sobrescrever estados intermediarios.
3. **Nao ha write-ahead log nem transacao distribuida** -- a ordem de escrita eh: in-memory -> Redis (periodico) -> Supabase (final). Qualquer falha no meio perde dados.

**Recomendacao:** A decisao arquitetural deve considerar:
- **Curto prazo:** Chamar `recover_running_jobs()` no lifespan (0.5h) + adicionar guard no `save_result()` (1h) = mitigacao imediata por 1.5h.
- **Medio prazo:** Redis como source of truth primario com sync para Supabase em background (write-behind pattern). In-memory dict reduzido a cache de leitura.

### CC-002: Seguranca de Dados End-to-End

**Validacao:** CONFIRMADO.

A cadeia de seguranca esta corretamente mapeada. Adiciono um detalhe tecnico:

- **DB-003 rebaixado para HIGH** porque o service role key eh NECESSARIO para storage operations (Supabase Storage requer service role para uploads server-side). O debito real nao eh "usar service role" mas "usar service role para TUDO sem separacao de operacoes".
- A solucao deve ser: (a) usar anon key + JWT pass-through para queries de leitura (`jobs`, `templates`), (b) manter service role APENAS para storage uploads/downloads e operacoes administrativas, (c) implementar audit logging para todas as operacoes com service role.

**Ordem de resolucao recomendada:**
1. DB-012 (safeguard AUTH_DISABLED) -- 0.5h, zero risco
2. DB-002 (add user_id) -- pre-requisito para tudo
3. DB-001 (fix RLS) -- depende de DB-002
4. DB-003 (scoped credentials) -- pode ser feito em paralelo com DB-001

---

## Respostas ao Architect

### 1. DB-001 + DB-002: Estrategia de migracao de dados

**Recomendacao: `user_id` nullable com enforcement gradual.**

- **Migration 1:** `ALTER TABLE jobs ADD COLUMN user_id UUID REFERENCES auth.users(id);` (nullable)
- **Migration 2:** Mesmo para `job_clusters` (herda de jobs via FK) e `templates`
- **Backfill:** Rows existentes recebem `user_id = NULL`. Criar RLS policy que trata NULL como "legacy data" visivel por admins apenas: `USING (user_id = auth.uid() OR user_id IS NULL)`
- **Enforcement futuro:** Apos periodo de transicao, `ALTER TABLE jobs ALTER COLUMN user_id SET NOT NULL` com default do JWT
- **Downtime:** Zero. Todas as operacoes sao `ALTER TABLE ADD COLUMN` (nao reescreve tabela no PostgreSQL) e `CREATE POLICY`
- **Risco:** Baixo. O unico risco eh queries existentes que nao passam `user_id` no INSERT -- o backend precisa ser atualizado para extrair `user_id` do JWT e inclui-lo em todas as escritas

### 2. DB-003: Service role key vs scoped credentials

**O backend PRECISA de service role para:**
- `storage.from_("jobs").upload()` -- uploads server-side requerem service role
- `storage.from_("jobs").download()` -- downloads server-side idem
- `storage.from_("jobs").create_signed_url()` -- gerar URLs assinadas
- `storage.from_("jobs").list()` / `.remove()` -- cleanup

**Nao precisa de service role para:**
- `table("jobs").upsert()` / `.select()` / `.delete()` -- queries de tabela podem usar anon key + JWT
- `table("job_clusters").upsert()` -- idem
- `table("templates").upsert()` / `.select()` -- idem

**Recomendacao:** Dois clientes Supabase:
1. `supabase_admin = create_client(url, service_role_key)` -- apenas para storage
2. `supabase_user = create_client(url, anon_key)` -- para queries de tabela, com JWT pass-through via `set_session()`

### 3. DB-007: Supabase async client

**Status do ecossistema:**
- `supabase-py` v2.x eh sincrono. Nao ha timeline oficial para versao async.
- `postgrest-py` (usado internamente) tem branch async experimental, mas nao esta estavel.
- `httpx` contra PostgREST eh viavel mas perde os type helpers do SDK.

**Recomendacao:** `asyncio.to_thread()` como solucao imediata e suficiente. O overhead do thread pool eh negligivel comparado ao tempo de I/O da rede. Exemplo:

```python
async def save_result(self, job_id: str, result_json: dict) -> None:
    await asyncio.to_thread(
        lambda: self._supabase.table("jobs")
        .upsert({"id": job_id, "result_json": result_json, "status": "completed"})
        .execute()
    )
```

Migrar para `httpx` direto contra PostgREST so se justifica se o volume de operacoes concorrentes crescer significativamente (>50 req/s).

### 4. DB-008 + SYS-004: Single source of truth

**Recomendacao: Opcao (b) -- Redis como source of truth com Supabase como persistencia final.**

Justificativa:
- Redis eh o unico store que tem TANTO a velocidade para SSE streaming QUANTO persistencia entre restarts
- In-memory dict deve ser reduzido a cache de leitura (ou eliminado -- `get_job` do Redis com ~1ms latencia local eh suficiente)
- Supabase recebe o resultado final via write-behind pattern (fire-and-forget com retry)
- Se Redis nao esta disponivel, fallback para InMemoryJobStore (atual) eh aceitavel para dev/staging

**Risco de perda de dados minimizado:** Redis com AOF (append-only file) habilitado no Railway tem durabilidade suficiente para jobs que duram minutos. A perda maxima eh o ultimo segundo de eventos SSE, nao o resultado final (que ja eh salvo no Supabase ao completar).

### 5. DB-010: Indices adicionais

- **`jobs.created_at`:** Nao urgente. Util apenas para listagem ordenada ou cleanup de jobs antigos. Adicionar quando volume > 10K rows.
- **`templates.name`:** Nao necessario. Nao ha busca por nome no codigo atual (`select *` ou `select by id`).
- **`templates.created_at`:** Nao necessario pelo mesmo motivo.
- **Volume esperado:** Baixo. Templates sao criados 1 por job processado. Estimativa: < 1000 templates no primeiro ano.

### 6. DB-011: Cleanup atomico

**Soft-delete eh a melhor abordagem.** Edge Functions introduzem complexidade desnecessaria (cold start, outro deploy artifact, debugging dificil).

Proposta:
1. Adicionar `deleted_at TIMESTAMPTZ` a `jobs` (nullable, default NULL)
2. `delete_job()` faz `UPDATE SET deleted_at = now()` em vez de DELETE
3. Background task (cron ou lifespan) limpa jobs com `deleted_at < now() - interval '1 day'`: remove storage files primeiro, depois DELETE da row
4. RLS policies adicionam `AND deleted_at IS NULL` ao filtro

**Vantagem:** Se o cleanup de storage falhar, a row permanece marcada para retry. Sem orfaos.

### 7. REDIS-002: Reconnection strategy

**Railway Redis SLA:** Best-effort, sem SLA formal. Pode reiniciar durante deploys.

**Recomendacao: Retry simples com fallback runtime (nao circuit breaker completo).**

Circuit breaker completo (com half-open state, counters, etc.) eh overengineering para o volume atual. Proposta:
1. Wrappear chamadas Redis em try/except com 1 retry (backoff 100ms)
2. Se ambos falham, logar warning e operar em modo degradado (sem persistencia para aquela operacao)
3. Health check periodico (a cada 30s) tenta reconectar se a conexao caiu
4. NAO fazer fallback completo para InMemoryJobStore em runtime (perderia jobs existentes no Redis)

---

## Recomendacoes

### Ordem de resolucao recomendada (perspectiva DB)

#### Wave 1 -- Quick Wins (4h total, zero risco)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 1 | DB-016 | Chamar `recover_running_jobs()` no lifespan | 0.5h | Fix trivial, impacto imediato na confiabilidade |
| 2 | DB-012 | Safeguard `AUTH_DISABLED` em producao | 0.5h | Fix trivial, previne bypass acidental |
| 3 | DB-004 | Trigger `updated_at` em `jobs` | 1h | Copy-paste do pattern de `templates` |
| 4 | DB-005 | CHECK constraint em `jobs.status` | 1h | Migration simples, previne dados invalidos |
| 5 | DB-009 | Incluir bucket creation nas migrations | 1h | Descomenta e wrappeia SQL existente |

#### Wave 2 -- Seguranca (20h total, requer coordenacao com @dev)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 6 | DB-002 | Adicionar `user_id` a todas as tabelas | 12h | Pre-requisito para DB-001 e DB-003 |
| 7 | DB-001 | Reescrever RLS policies com owner filter | 4h | Depende de DB-002 |
| 8 | DB-003 | Separar service role de queries regulares | 4h | Pode ser feito em paralelo com DB-001 |

#### Wave 3 -- Confiabilidade (15h total)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 9 | DB-008 | Consolidar state stores (Redis como SSOT) | 8h | Requer decisao arquitetural CC-001 |
| 10 | DB-007 | Wrappear SDK em `asyncio.to_thread()` | 6h | Independente, pode ser feito a qualquer momento |
| 11 | DB-017 | Guard em `save_result()` para cancelamentos | 1h | Pode ser feito junto com DB-008 |

#### Wave 4 -- Operacoes e Redis (10h total)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 12 | DB-011 + DB-015 | Soft-delete + fix recursive listing | 6h | Relacionados, devem ser feitos juntos |
| 13 | DB-006 | Criar rollback migrations | 6h | Melhoria operacional, nao urgente |
| 14 | REDIS-002 | Retry simples com health check | 4h | Melhoria de resiliencia |
| 15 | REDIS-004 | Migrar para `redis.asyncio` | 3h | Pode ser feito junto com DB-007 |
| 16 | REDIS-001 | Adicionar prefixo `migrador:` | 0.5h | Trivial |

#### Deprioritizados

| ID | Debito | Motivo |
|----|--------|--------|
| DB-010 | Indice `created_at` | Volume insuficiente para justificar |
| DB-013 | FK `templates` -> `jobs` | Nice-to-have, nao bloqueia nada |
| DB-014 | UPDATE policy em storage | Impacto zero no cenario atual |
| REDIS-003 | `scan_iter` em `all_jobs()` | TTL limita keyspace, aceitavel |

### Esforco total estimado: ~60h

| Wave | Horas | Bloqueado por |
|------|-------|---------------|
| Wave 1 (Quick Wins) | 4h | Nada |
| Wave 2 (Seguranca) | 20h | Wave 1 (DB-005 para validar status antes de migration) |
| Wave 3 (Confiabilidade) | 15h | Decisao arquitetural CC-001 |
| Wave 4 (Operacoes) | 10h | Nada (independente) |
| Deprioritizados | ~4h | N/A |

---

## Controle de Versoes

| Versao | Data | Autor | Mudanca |
|--------|------|-------|---------|
| v1.0 | 2026-04-09 | @data-engineer (Dara) | Review inicial -- Phase 5 Brownfield Discovery |
