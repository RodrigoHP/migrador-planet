# Audit Anti-Patterns — Busca proativa no codebase

```yaml
task: auditPatterns()
responsavel: Quinn (Guardian)
responsavel_type: Agente
atomic_layer: Molecule

inputs:
  - campo: scope
    tipo: string
    origem: User Input
    obrigatorio: false
    descricao: "Escopo da auditoria (ex: backend/, frontend/). Default: projeto inteiro"

outputs:
  - campo: audit_report
    tipo: file
    destino: "docs/qa/audit-reports/audit-{date}.md"
    persistido: true
  - campo: findings_count
    tipo: number
  - campo: stories_suggested
    tipo: array
```

---

## Objetivo

Buscar proativamente no codebase todos os anti-patterns conhecidos registrados em `docs/qa/known-anti-patterns.md`. Encontrar problemas ANTES que causem crash.

---

## Execucao

### Passo 1 — Effectiveness Review (v6.0 — PRIORIDADE MAXIMA)

> Movido de Passo 6 para Passo 1 (v6.0 enforcement). Effectiveness review
> eh a primeira coisa que roda para garantir que knowledge base esteja atualizada.

1. Ler `docs/qa/rca-knowledge/investigations.yaml`
2. Filtrar investigacoes com `effectiveness: pending` ha mais de **7 dias**
3. Para cada investigacao pending:
   - Grep pelos mesmos `symptoms` e `tags` em commits dos ultimos 7 dias
   - Verificar se `anti_patterns` associados foram detectados neste audit
   - SE recorreu (mesmo sintoma/tag em commits OU anti-pattern encontrado): `effectiveness: ineffective`
   - SE variante do bug: `effectiveness: partial`
   - SE nenhuma recorrencia: `effectiveness: resolved`
4. Atualizar `effectiveness` e `effectiveness_reviewed_at` na investigations.yaml
5. SE SOP foi usado (fast-track) — Atualizar outcome tracking no SOP (v7.0):
   - Abrir `docs/qa/rca-knowledge/sops/{sop_id}.yaml`
   - SE effectiveness = `resolved`: incrementar `times_effective` (+1)
   - SE effectiveness = `partial` ou `ineffective`: incrementar `times_ineffective` (+1)
   - Recalcular: `effectiveness_rate = times_effective / times_applied` (arredondar 2 casas)
   - SE effectiveness_rate = 0% E times_applied >= 3: marcar `needs_review: true`
   - **SALVAR o arquivo SOP imediatamente**
6. Verificar SOPs com `needs_review: true` em `docs/qa/rca-knowledge/sops/*.yaml`:
   - Para cada SOP com `needs_review: true`: incluir no relatorio como alerta
   - Formato: "SOP {sop_id} precisa revisao — effectiveness_rate = {rate}% apos {times_applied} aplicacoes"
7. SE alguma investigacao marcada como `ineffective`:
   ```
   ALERTA: Fix ineficaz detectado!
   Investigacao: {id}
   Sintomas recorrentes: {lista}
   Recomendacao: executar nova investigacao com *investigate
   ```

### Passo 2 — Ler o registry

Ler `docs/qa/known-anti-patterns.md` e extrair todos os padroes registrados com seus grep patterns e escopos.

### Passo 3 — Buscar cada padrao

Para cada anti-pattern com status `active`:
1. Executar grep/busca no escopo definido usando `search_pattern`
2. Para cada match encontrado, verificar se o guard esperado esta presente
3. SE guard AUSENTE → registrar como finding
4. SE guard PRESENTE → ignorar (ja protegido)

### Passo 3b — Auto-increment Recurrence (v7.0)

Para cada anti-pattern onde findings foram encontrados (guard ausente):
1. Abrir `docs/qa/known-anti-patterns.md`
2. Encontrar o AP-ID
3. Incrementar `Recurrence` (+1) para CADA nova instancia encontrada (nao contada anteriormente)
4. Adicionar data do audit ao campo "Encontrado em" (append)
5. **SALVAR o arquivo imediatamente**
6. Registrar no relatorio: "AP-{ID} recurrence atualizado: {N_anterior} → {N_novo} ({N_novas_instancias} novas instancias)"

> **NOTA:** So incrementar para instancias NOVAS (nao previamente conhecidas). Se a mesma instancia ja foi reportada em audit anterior, nao incrementar novamente.

### Passo 4 — Classificar findings

Para cada finding:
- Localizacao (arquivo:linha)
- Anti-pattern ID (AP-XXX)
- Severidade (herdada do anti-pattern)
- Contexto (trecho do codigo)
- Acao sugerida

### Passo 5 — Gerar relatorio

Gerar `docs/qa/audit-reports/audit-{date}.md`:

```markdown
# Audit Report — {date}

## Resumo
- Anti-patterns verificados: {N}
- Findings encontrados: {N}
- CRITICAL: {N} | HIGH: {N} | MEDIUM: {N}

## Findings

### Finding 1: AP-001 em {arquivo}:{linha}
- **Padrao:** {descricao do anti-pattern}
- **Codigo:** {trecho}
- **Guard ausente:** {o que deveria ter}
- **Acao:** {sugestao}

...
```

### Passo 6 — Sugerir stories

SE findings encontrados:
- Agrupar por anti-pattern ou por modulo
- Sugerir stories para correcao
- Priorizar por severidade

SE zero findings:
- Registrar auditoria limpa no relatorio

### Passo 7 — Supersession Check

Verificar consistencia de anti-patterns superseded:
1. Para cada anti-pattern com `superseded_by`:
   - Verificar que o anti-pattern referenciado existe
   - Verificar que SOP associada esta marcada como deprecated
   - Verificar que nao ha ciclos (AP-A → AP-B → AP-A)
2. Reportar inconsistencias no relatorio

---

## Invocacao

```bash
# Auditoria completa
*audit-patterns

# Auditoria em escopo especifico
*audit-patterns backend/services/

# Via @aios-master
*task audit-patterns
```

---

## Quando Usar

- Antes de releases
- Periodicamente (ex: a cada sprint)
- Depois de adicionar novos anti-patterns ao registry
- Quando entrar em area do codebase pouco conhecida
- Apos cada investigacao RCA (para review de effectiveness de anteriores)
