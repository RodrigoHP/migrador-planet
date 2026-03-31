# Known Anti-Patterns Registry

> Cada RCA adiciona o padrao problematico encontrado a esta lista.
> Use `*audit-patterns` para buscar esses padroes no codebase.

## Como Usar

1. Depois de cada investigacao RCA, registre o padrao aqui
2. Periodicamente (ou antes de releases), rode `*audit-patterns`
3. Cada achado vira story ANTES de causar crash

## Schema (v6.0)

Campos obrigatorios para cada anti-pattern:
- **ID:** AP-XXX (sequencial)
- **Status:** `active` (default) | `superseded`
- **Recurrence:** Numero de incidentes (incrementado a cada RCA)
- **Encontrado em:** Referencia a RCA(s)
- **Descricao:** O que o padrao faz de errado
- **Buscar (search_pattern):** Regex para deteccao automatica (**obrigatorio quando possivel**)
- **Guard esperado:** O que deveria existir para prevenir
- **Severidade:** CRITICAL / HIGH / MEDIUM / LOW
- **Escopo:** Quais arquivos/diretorios buscar
- **SOP:** Referencia ao SOP associado (ou `null`)

Campos opcionais (supersession):
- **superseded_by:** `AP-XXX` — indica que este anti-pattern eh sintoma de um mais profundo

### Exemplo de Anti-Pattern Bem Formado

```markdown
### AP-XXX: Descricao curta do padrao
- **Status:** active
- **Recurrence:** 2
- **Encontrado em:** RCA 2026-XX-XX
- **Descricao:** O que acontece de errado
- **Buscar:** `regex_pattern` em arquivos do escopo
- **Guard esperado:** O que deveria existir
- **Severidade:** HIGH
- **Escopo:** `path/to/files/*.ext`
- **SOP:** `sop-slug.yaml`
```

---

## Padroes Registrados

### AP-001: .get() em objeto sem isinstance guard
- **Status:** active
- **Recurrence:** 4
- **Encontrado em:** RCA 15.18, 15.19, 15.20, RCA 2026-03-29 (PR #42)
- **Descricao:** Chamada `.get()` em objeto que pode ser lista em vez de dict. Causa `'list' object has no attribute 'get'`
- **Buscar:** `\.get\(` em arquivos Python que processam dados externos (stages, parsers, transformers)
- **Guard esperado:** `isinstance(x, dict)` antes de qualquer `.get()`
- **Severidade:** CRITICAL
- **Escopo:** `backend/services/stages/*.py`, qualquer modulo que processe arvores/JSON externo
- **SOP:** `sop-missing-isinstance-guard.yaml`

### AP-002: Import de arquivo renomeado em spec sem atualização
- **Status:** active
- **Recurrence:** 1
- **Encontrado em:** RCA 2026-03-29 (PR #42)
- **Descricao:** Arquivo de teste importa módulo pelo nome antigo após renomeação. Causa falha de transform no Vitest sem falha de compilação TypeScript.
- **Buscar:** `from ['"]\.\/[a-zA-Z]+(?:V[0-9]+)?['"]` em specs — verificar se modulo referenciado existe no filesystem
- **Guard esperado:** Ao renomear um módulo, grep por todos os imports do nome antigo e atualizar
- **Severidade:** HIGH
- **Escopo:** `frontend/src/**/*.spec.ts`, qualquer spec que importe de modulos refatorados
- **SOP:** null

### AP-004: Contrato de retorno de orquestrador não tipado — resultado incompleto para o frontend
- **Status:** active
- **Recurrence:** 1
- **Encontrado em:** RCA 2026-03-31 (rca-20260331-editor-empty-after-analysis)
- **Descricao:** Orquestrador de pipeline constrói dict de retorno ad-hoc a partir de chaves `stage_N_result`, ignorando o objeto `result_json` que um stage interno já montou com o contrato correto. O frontend recebe estrutura diferente da esperada e todos os stores ficam vazios (editor vazio).
- **Buscar:** `context\.get\("stage_\d_result"` em blocos de montagem de resultado final de orquestradores
- **Guard esperado:** Tipo de retorno explícito em `run_pipeline_*` + merge de `result_json` (contrato autoritativo) em vez de montagem manual por stage
- **Severidade:** HIGH
- **Escopo:** `backend/services/pipeline_orchestrator_v2.py`, qualquer orquestrador que monte resultado final de pipeline
- **SOP:** null

### AP-003: Contrato de dados inconsistente entre stages — normalização duplicada sem dono
- **Status:** active
- **Recurrence:** 1
- **Encontrado em:** RCA 2026-03-31 (stage5-document-trees-contract)
- **Descricao:** Um stage publica dados no context compartilhado em formato A (ex: `List[Dict]`), mas todos os consumidores precisam do formato B (ex: `Dict[str, Dict]`). Cada consumidor reimplementa a mesma conversão localmente sem escrever de volta no context. Sub-funções que leem o context diretamente crasham porque nunca recebem o formato normalizado.
- **Buscar:** `if isinstance\(.+, list\):` duplicado em multiplos stages para a mesma chave de context compartilhado
- **Guard esperado:** O stage **produtor** normaliza para o formato esperado pelos consumidores antes de gravar no context. Uma única normalização na fonte elimina toda a duplicação.
- **Severidade:** CRITICAL
- **Escopo:** `backend/services/stages/*.py`, qualquer pipeline com context compartilhado entre stages
- **SOP:** null

### AP-005: Silent Service Degradation — fallback sem notificação ao usuário
- **Status:** active
- **Recurrence:** 1
- **Encontrado em:** RCA 2026-03-31 (rca-2026-03-31-custo-api-zero)
- **Descricao:** Quando um serviço externo (Vision AI, LLM, API) falha ou não está configurado, o sistema silenciosamente ativa um fallback de menor qualidade sem notificar o usuário. O resultado aparece como "sucesso" mas com qualidade degradada (~75% vs ~95%). Sintoma visível: métricas que deveriam ter valor positivo exibem zero ou N/A sem explicação.
- **Buscar:** `except.*ImportError.*ValueError.*:\s*\n\s*(vision|service|client)_available\s*=\s*False` em stages e serviços
- **Guard esperado:** Ao ativar fallback, adicionar entrada em `context["_pipeline_warnings"]` com mensagem clara. Orquestrador propaga `warnings` no SSE summary. Frontend exibe indicator de qualidade degradada.
- **Severidade:** HIGH
- **Escopo:** `backend/services/stages/*.py`, `backend/services/*.py`, qualquer serviço que implemente fallback silencioso
- **SOP:** null
