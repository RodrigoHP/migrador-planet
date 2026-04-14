# Epic 11: Estabilização do Fluxo Upload/Editor

**Status:** Ready for Development
**Data:** 2026-03-20
**Criado por:** @pm (Morgan) — baseado em audit técnico @analyst (Atlas)
**Epic Owner:** @dev (Dex)
**Audit Source:** Atlas Technical Audit Report — 2026-03-20

---

## Epic Goal

Estabilizar o fluxo completo Upload → Analyzing → Editor resolvendo os problemas estruturais identificados no audit técnico: consolidação do pipeline canônico, compatibilidade de formatos de dados entre backend e frontend, e implementação completa dos componentes do editor que estão como stubs ou com stores não populados.

---

## Contexto do Sistema

**Problema raiz:** Dois sistemas de pipeline paralelos e incompatíveis coexistem em produção:
- `backend/routers/jobs.py` (legacy, 3 etapas, usado por `useSSE.ts`)
- `backend/routers/analyze.py` (novo, 28 etapas, usado por `AnalyzingPage.vue`)

**Stack afetada:**
- **Backend:** FastAPI — `routers/analyze.py`, `routers/jobs.py`, `routers/upload.py`
- **Frontend:** Vue 3 + Pinia — `AnalyzingPage.vue`, `TemplateEditor.vue`, `InspectorPanel.vue`, `HTMLCanvas.vue`, stores `session.ts`, `inspectorStore.ts`

**Referências de audit:**
- Atlas Audit Report: 12 problemas, P1-P3 críticos, P4-P6 altos, P7-P9 médios, P10-P12 baixos
- Stories afetadas anteriormente: 10.2, 10.9, 10.14, 10.20

---

## Stories

### Wave 1 — Fundação (Críticos, deve ser feito em ordem)

| Story | Título | Prioridade | Executor | Quality Gate |
|-------|--------|-----------|----------|--------------|
| 11.1 | Consolidar pipeline canônico — deprecar jobs.py legacy | P1-Crítico | @dev | @architect |
| 11.2 | Adaptar template_draft para formato pages[] no HTMLCanvas | P1-Crítico | @dev | @architect |
| 11.3 | Implementar TemplateEditor.vue completo (3-pane layout) | P1-Crítico | @dev | @qa |

### Wave 2 — Consistência de Estado (Altos, após Wave 1)

| Story | Título | Prioridade | Executor | Quality Gate |
|-------|--------|-----------|----------|--------------|
| 11.4 | Unificar jobId/job_id no session store | P2-Alto | @dev | @dev |
| 11.5 | Corrigir InspectorPanel — popular inspectorStore no loadFromPipelineResult | P2-Alto | @dev | @qa |
| 11.6 | Corrigir useSSE.ts endpoint e remover dead code | P2-Alto | @dev | @architect |

### Wave 3 — Segurança e Robustez (Médios/Baixos, paralelos)

| Story | Título | Prioridade | Executor | Quality Gate |
|-------|--------|-----------|----------|--------------|
| 11.7 | Adicionar UUID validation em analyze.py | P3-Médio | @dev | @dev |
| 11.8 | Suporte multi-PDF no pipeline e persistência de pdfBytes | P3-Médio | @dev | @architect |
| 11.9 | TTL com limpeza de arquivos do disco | P3-Baixo | @dev | @dev |

---

## Dependências

```
11.1 → 11.2 → 11.3 (sequencial — fundação)
11.1 → 11.6 (analyze.py canônico antes de corrigir SSE)
11.3 → 11.5 (editor implementado antes de popular inspector)
11.4 independente (pode ser paralela na Wave 2)
11.7, 11.8, 11.9 independentes entre si (Wave 3)
```

---

## Riscos e Mitigação

| Risco | Mitigação |
|-------|-----------|
| jobs.py tem dependências não mapeadas | Audit de uso via grep antes de deprecar (11.1) |
| TemplateEditor stub com rotas existentes | Manter guards de rota, implementar progressivamente (11.3) |
| Mudança no session store quebra outros fluxos | Testes de regressão completos após 11.4 |
| pdfBytes perdidos no refresh | SessionStorage como fallback temporário (11.8) |

---

## Definition of Done (Epic)

- [ ] Fluxo completo upload → analyzing → editor funcional sem erros console
- [ ] Pipeline único e canônico (analyze.py) — jobs.py removido ou claramente deprecado
- [ ] HTMLCanvas renderiza template_draft corretamente
- [ ] Inspector exibe propriedades reais dos elementos selecionados
- [ ] TemplateEditor.vue com 3 painéis funcionais
- [ ] Sem nomenclatura dupla jobId/job_id no session store
- [ ] useSSE.ts atualizado ou removido
- [ ] Todos os testes passando (backend + frontend)
- [ ] Sem regressões nas histórias anteriores (10.x)

---

## Handoff para @sm

"Criar stories detalhadas para Epic 11 — Estabilização do Fluxo Upload/Editor.

Contexto crítico:
- Stack: FastAPI (backend) + Vue 3 + Pinia (frontend)
- Problema raiz: dois pipelines paralelos incompatíveis — jobs.py (legacy) vs analyze.py (novo, 28 etapas)
- SSE endpoint mismatch: useSSE.ts aponta /api/progress/ (legacy), AnalyzingPage usa /api/analyze/{id}/progress (novo)
- TemplateEditor.vue tem apenas 24 linhas (stub)
- inspectorStore nunca populado no loadFromPipelineResult
- template_draft = {html, css} mas HTMLCanvas espera pages[] array

Padrões existentes a seguir:
- Stories de bug do Epic 10 como referência de formato
- Testes: pytest para backend, Vitest para frontend
- Cada story deve ter AC verificáveis e tasks granulares

Sequência obrigatória: Wave 1 (11.1→11.2→11.3) antes de Wave 2, Wave 2 antes de Wave 3."

— Morgan, planejando o futuro 📊
