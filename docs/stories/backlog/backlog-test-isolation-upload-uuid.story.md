---
epic: TBD
story: TBD
title: "Fix: isolamento de testes test_upload_validation e test_uuid_validation"
status: Done
executor: "@dev"
quality_gate: "@qa"
quality_gate_tools: [unit_test]
depends_on: []
source_debt: "DT-42-5"
priority: medium
---

# Story TBD: Corrigir isolamento de testes upload_validation e uuid_validation

## Status
Draft

## Story
**As a** desenvolvedor executando a suite completa de testes,
**I want** que `test_upload_validation.py` e `test_uuid_validation.py` passem em qualquer
ordem de execução,
**so that** o CI não tenha falhas não-determinísticas dependentes de estado compartilhado.

## Contexto

7 testes em `test_upload_validation.py` e `test_uuid_validation.py` passam quando
executados isoladamente mas falham quando a suite completa roda (844 passed, 12 failed).
Isso indica dependência de estado global (provavelmente FastAPI TestClient, app state,
ou mock patches que não são limpos entre módulos de teste).

## Acceptance Criteria

- [ ] AC1: `python -m pytest tests/` (suite completa) → os 7 testes passam independente da ordem
- [ ] AC2: Causa raiz identificada (qual estado compartilhado causa a falha)
- [ ] AC3: Fix aplica `@pytest.fixture(autouse=True)` ou equivalente para limpar estado

## Estimativa
2h

## Dependências
Nenhuma

## Change Log

| Date | Agent | Action |
|------|-------|--------|
| 2026-04-10 | @dev | Story criada — falhas de isolamento identificadas no Epic 42 |
