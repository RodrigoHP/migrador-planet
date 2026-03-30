# Known Anti-Patterns Registry

> Cada RCA adiciona o padrao problematico encontrado a esta lista.
> Use `*audit-patterns` para buscar esses padroes no codebase.

## Como Usar

1. Depois de cada investigacao RCA, registre o padrao aqui
2. Periodicamente (ou antes de releases), rode `*audit-patterns`
3. Cada achado vira story ANTES de causar crash

---

## Padroes Registrados

### AP-001: .get() em objeto sem isinstance guard
- **Encontrado em:** RCA 15.18, 15.19, 15.20, RCA 2026-03-29 (PR #42)
- **Descricao:** Chamada `.get()` em objeto que pode ser lista em vez de dict. Causa `'list' object has no attribute 'get'`
- **Buscar:** `\.get\(` em arquivos Python que processam dados externos (stages, parsers, transformers)
- **Guard esperado:** `isinstance(x, dict)` antes de qualquer `.get()`
- **Severidade:** CRITICAL
- **Escopo:** `backend/services/stages/*.py`, qualquer modulo que processe arvores/JSON externo

### AP-002: Import de arquivo renomeado em spec sem atualização
- **Encontrado em:** RCA 2026-03-29 (PR #42)
- **Descricao:** Arquivo de teste importa módulo pelo nome antigo após renomeação (ex: `analyzingPageConstants` → `analyzingPageConstantsV2`). Causa falha de transform no Vitest sem falha de compilação TypeScript.
- **Buscar:** `from ['"]\.\/analyzingPageConstants['"]` em arquivos `.spec.ts`
- **Guard esperado:** Ao renomear um módulo, grep por todos os imports do nome antigo e atualizar
- **Severidade:** HIGH
- **Escopo:** `frontend/src/pages/*.spec.ts`, qualquer spec que importe de páginas refatoradas
