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

### AP-006: Lazy Load sem Sentinel de Falha — retry e re-log por chamada
- **Status:** active
- **Recurrence:** 1
- **Encontrado em:** RCA 2026-03-31 (rca-2026-03-31-spacy-xsd-warnings)
- **Descricao:** Componente opcional carregado lazily usa `None` como sentinela tanto para "não tentou" quanto para "tentou e falhou". Ao usar `if x is not None` como guard, cada chamada após falha repete a tentativa de load e reloga o warning — uma vez por invocação, em vez de uma vez por processo.
- **Buscar:** `global _\w+\n\s+if _\w+ is not None:\s*\n\s*return _\w+` seguido de load que pode falhar mas não seta sentinela de falha
- **Guard esperado:** Usar `False` (ou objeto sentinela dedicado) para distinguir "não tentou" (`None`) de "tentou e falhou" (`False`). Guard passa para `if _nlp is False: return None` antes do check de sucesso.
- **Severidade:** LOW
- **Escopo:** `backend/services/stages/*.py`, qualquer módulo com componente opcional lazy-loaded
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


### AP-008: CSS reset sem dimensões de fallback — container colapsa com overflow:hidden
- **Status:** active
- **Recurrence:** 1
- **Encontrado em:** RCA 2026-03-31 (rca-2026-03-31-canvas-blank-v2)
- **Descricao:** Um container CSS com `overflow: hidden` não tem `width`/`height` no CSS reset. Todos os filhos são `position: absolute`, portanto não expandem o pai. O container colapsa para `0×0px` e `overflow: hidden` corta silenciosamente todo o conteúdo. Sintoma: área de render em branco sem erros visíveis.
- **Buscar:** `overflow:\s*hidden` em blocos CSS onde o container pode ter apenas filhos absolutos
- **Guard esperado:** Qualquer container com `overflow: hidden` que possa ter apenas filhos `position: absolute` DEVE ter `width` e `height` (ou `min-height`) explícitos no CSS reset. Usar fallback de dimensões conhecidas (ex: A4 = 794×1123px) para garantir que o container nunca colapsa.
- **Severidade:** HIGH
- **Escopo:** `backend/services/stages/stage5_template_generation.py` (`_BASE_CSS_RESET`), qualquer template CSS que use `overflow:hidden` em containers de layout
- **SOP:** null

### AP-009: Race condition watch/lifecycle com IntersectionObserver sem nextTick fence
- **Status:** active
- **Recurrence:** 1
- **Encontrado em:** RCA 2026-03-31 (rca-2026-03-31-canvas-blank-selector-mismatch)
- **Descricao:** Um `watch` Vue que reage a mudança de dado executa `.clear()` em mapa de refs e em seguida chama `nextTick()` sem `await`. O IntersectionObserver pode disparar entries antes do DOM estar reconstituído, lendo elementos desconectados ou reciclados. `visiblePages` fica em estado indefinido — páginas nunca marcadas como visíveis → `v-if` false → iframes não montados → canvas branco.
- **Buscar:** `watch\(` com `.clear\(\)` seguido de `nextTick\(` sem `await` em componentes que também instanciem `IntersectionObserver`
- **Guard esperado:** Callback do `watch` deve ser `async` e usar `await nextTick()` antes de qualquer lógica que dependa do DOM atualizado. Desconectar o observer (`teardownObserver`) antes do clear e reconectar dentro do `await nextTick()` garante que o observer não observe elementos em estado transitório.
- **Severidade:** HIGH
- **Escopo:** `frontend/src/organisms/HTMLCanvas.vue`, qualquer componente Vue com `IntersectionObserver` + `watch` que manipule refs de DOM
- **SOP:** null

### AP-010: Atributo HTML de seleção dessincronizado entre gerador e consumidor
- **Status:** active
- **Recurrence:** 1
- **Encontrado em:** RCA 2026-03-31 (rca-2026-03-31-canvas-blank-selector-mismatch)
- **Descricao:** Backend gera markup com atributo A (ex: `data-layout-type`) mas frontend faz `querySelector` com atributo B (ex: `[data-page]`). Ausência de schema compartilhado ou contrato de atributos HTML entre camadas causa fallback silencioso: `querySelectorAll` retorna NodeList vazia, o componente usa o HTML inteiro como fallback sem sinalizar erro. Mock de DOMParser nos testes hardcoda o atributo antigo, mascarando completamente o mismatch em CI.
- **Buscar:** `querySelector\('\[data-` em `frontend/src/**/*.{vue,ts}` — cruzar cada atributo lido com os atributos emitidos em `backend/services/stages/stage5_template_generation.py`; qualquer `dataset\.\w+` em callbacks de `IntersectionObserver` — verificar se o elemento observado carrega o atributo lido
- **Guard esperado:** Definir constante compartilhada ou comentário explícito listando todos os `data-*` usados como seletores funcionais, quem os emite e quem os consome. Testes de contrato devem verificar que o HTML gerado pelo backend contém os atributos esperados pelo frontend. Ao mudar um atributo no backend, grep por todos os consumidores no frontend antes do commit.
- **Severidade:** CRITICAL
- **Escopo:** `frontend/src/organisms/HTMLCanvas.vue`, `frontend/src/organisms/SyncView.vue`, `backend/services/stages/stage5_template_generation.py`, qualquer componente Vue que use `querySelectorAll('[data-*]')` com HTML gerado pelo backend
- **SOP:** null

### AP-007: Nó de árvore sem chave `children` — crash em travessia recursiva
- **Status:** active
- **Recurrence:** 1
- **Encontrado em:** RCA 2026-03-31 (rca-2026-03-31-editor-redirect-to-home)
- **Descricao:** Nós folha de árvore de documento (cell, image, chart, barcode) criados sem a chave `children`. Função de conversão ou travessia assume `children` sempre presente. Em runtime, `for (const child of node.children)` lança TypeError quando `children === undefined`, abortando silenciosamente o carregamento do store e impedindo navegação.
- **Buscar:** `{"type": "cell"` ou `{"type": "image"` ou `{"type": "chart"` ou `{"type": "barcode"` sem chave `children` em construtores de árvore
- **Guard esperado:** Todo nó de árvore DEVE ter `children: []` explícito. Função de conversão deve garantir `result.setdefault("children", [])` ou equivalente. Travessias devem usar `node.children ?? []`.
- **Severidade:** HIGH
- **Escopo:** `backend/services/stages/stage3_structural_analysis.py`, `backend/services/stages/stage5_template_generation.py`, `frontend/src/stores/templateStore.ts`, `frontend/src/stores/session.ts`
- **SOP:** null
