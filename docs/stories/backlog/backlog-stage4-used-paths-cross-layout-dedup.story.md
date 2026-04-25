# Backlog — Stage 4: Corrigir Deduplicação Cross-Layout de used_paths

## Status: Done — implementado como Story 48.13 (commit 0257f11)

## Origem

RCA `rca-2026-04-25-scalar-coverage-residual-53pct` (RC-C) identificado durante AC6 da Story 48.12.
Bug confirmado em `backend/services/stages/stage4_mapping/section_matching.py:365`.

## Problema

Em `section_matching.py`, a variável `used_paths` que previne atribuição duplicada de caminhos XSD é inicializada **dentro** do loop `for layout_id`:

```python
# section_matching.py:~360
for layout_id in layouts:
    used_paths: set = set()   # BUG: reset por layout
    # ... lógica de matching ...
```

O resultado é que o mesmo caminho XSD pode ser atribuído a campos em layout A **e** campo em layout B independentemente. Se um template tem 2 layouts (ex: carta de 4 páginas + relatório de 11 páginas), o mesmo `Propostas.Propostas.ClienteTelefone` aparece em ambos os outputs.

**Evidência confirmada (run 2026-04-25):**
- Layout A: `'Pedimos que você verifique'` → `Propostas.Propostas.ClienteTelefone`
- Layout B: `'Conforme seu pedido'` → `Propostas.Propostas.ClienteTelefone` (duplicado)

Ambos são false positives (RC-A), mas o bug de dedup aparece independentemente — se RC-A for corrigido, campos reais também poderiam sofrer dedup incorreta em templates multi-layout.

## Solução Proposta

Mover `used_paths` para fora do loop de layouts:

```python
# ANTES
for layout_id in layouts:
    used_paths: set = set()  # reset por layout
    ...

# DEPOIS
used_paths: set = set()  # cross-layout
for layout_id in layouts:
    ...
```

**Considerações:**
- Verificar se layouts distintos legitimamente podem ter campos com o mesmo XSD path (ex: dois layouts com um campo `NomeCliente` cada). Se sim, a semântica correta é `used_paths` por `job_id` (não por `layout_id`), não por template.
- Alternativa: `used_paths_per_run: Dict[str, set]` keyed por `job_id` para suportar batch de múltiplos clientes.

## Acceptance Criteria

- [ ] **AC1:** `used_paths` não é resetado entre layouts do mesmo template — mesmo path XSD não aparece em outputs de layouts distintos do mesmo job
- [ ] **AC2:** Testes: template com 2 layouts e mesmos campos candidatos → path atribuído apenas ao layout com maior score de confiança
- [ ] **AC3:** Nenhuma regressão em templates single-layout (comportamento idêntico ao atual)
- [ ] **AC4:** Documentação do comportamento esperado no código (`# cross-layout dedup: same XSD path can appear at most once per job`)

## Escopo

### IN
- `backend/services/stages/stage4_mapping/section_matching.py` — reposicionar `used_paths` init

### OUT
- Stage 3 (body text fix é story separada)
- Stage 4 constants.py
- Mudança na estrutura de dados de output

## Estimativa

1-2h

## Dependências

- Pode ser implementada independentemente de RC-A e RC-D
- Teste completo requer RC-A corrigido para distinguir dedup legítima de dedup causada por false positives

## Prioridade

**P1** — Bug estrutural que afeta qualidade de templates multi-layout. Não é bloqueante direto para scalar_coverage gate (RC-A é o bloqueante principal), mas deve ser corrigido antes do Epic 49 para evitar regressões em produção.

## Change Log

| Data | Agente | Ação |
|------|--------|------|
| 2026-04-25 | @dev | Draft criado — origem AC6 Story 48.12, RCA rca-2026-04-25-scalar-coverage-residual-53pct |
