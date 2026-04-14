# Epic 22 — Tech Debt: Storage Gateway & CI Hardening

## Status
Ready

## Objetivo
Resolver débito técnico identificado durante investigação PGRST205 (2026-03-31):
correção dos mocks assíncronos em `test_storage_gateway.py` e adição de
validação de migrations no pipeline CI.

## Origem
Backlog de achados colaterais da investigação `/investigate` PGRST205.
Referência: `docs/qa/investigations/BACKLOG_pgrst205_achados.md`

## Stories

| Story | Título | Executor | Status |
|-------|--------|----------|--------|
| 22.1 | Corrigir async mock failures em test_storage_gateway.py | @dev | Draft |
| 22.2 | Adicionar validação de migrations no CI | @devops | Draft |
| 22.3 | Tech Debt: Garantir children: [] em nós folha do Stage 3 | @dev | Draft |

## Definition of Done
- Todos os testes de `test_storage_gateway.py` passando
- CI valida migrations antes de merge
- Todos os nós folha do Stage 3 possuem `children: []` + teste de contrato
- Zero regressões

## Prioridade
LOW — tech debt, não bloqueia funcionalidades
