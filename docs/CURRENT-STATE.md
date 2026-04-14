# Estado Atual do Projeto — Contexto de Domínio

**Status:** `current` — estado do domínio (Pilares, decisões locked, epics recentes)
**Dono:** `@pm` — atualiza ao fechar cada epic
**Fonte:** decisões de projeto + epics concluídos + código commitado
**Atualizar quando:** epic fechado ou decisão arquitetural locked/revertida
**Última validação:** 2026-04-13 (Epic 46 concluído)

> **Escopo:** decisões arquiteturais, estado do domínio, Pilares A/B/C.
> **NÃO inclui:** estado do SDC/workflow (fica em `.aios/`), handoffs entre agentes (`.aios/handoffs/`).
> **Responsável:** `@pm` atualiza ao fechar cada epic.

---

## Pilares — Estado

| Pilar | Descrição | Status |
|-------|-----------|--------|
| **A — Detecção** | Capturar TUDO do PDF (texto, tabelas raster, imagens, cores, fontes) | **Código completo, validação pendente** — ver detalhes abaixo |
| **B — Binding** | Mapear campos detectados para XSD | Bloqueado — aguarda Pilar A completo |
| **C — Editor** | Exibir template no editor visual | Bloqueado — aguarda Pilar A completo |

**Regra:** nunca avançar para B ou C com A incompleto.

### Pilar A — O que foi feito (Epics 43–46)

| Problema | Solução | Epic | Resultado |
|----------|---------|------|-----------|
| Stage 3.3 classificava VALUE blocks como labels (heurística ≤30 chars) | Heurística corrigida — VALUE blocks preservados como `dynamic` | 43.1 | 87% unmapped → mapeável |
| Tabelas raster (JPEG embutido) sem extração | Mistral OCR com `pages=[page_index]` como fallback | 43.2 | 0/1 → 1/1 tabelas extraídas |
| `image_area` descartada silenciosamente em section_utils.py:469 | Handler PIL heurístico: `aspect > 3.0 AND pct_bw > 85%` → barcode, senão → preserve_as_image_crop | 43.8 | logos e barcodes roteados corretamente |
| GPT-4o Vision custoso ($0.01/cluster) no Stage 3.2 | PyMuPDF para bbox + Mistral incondicional | 46.2 | $0.010 → $0.001/cluster |

### Pilar A — O que falta para declarar completo

1. **Commit obrigatório antes de qualquer validação:**
   - `backend/services/stages/stage3_structural/` — modificado, não commitado
   - `backend/tests/test_stage3_image_area_handler.py` — não rastreado
   - Sem commit, o código em produção não reflete as correções

2. **Re-medição do baseline** contra job Supabase real após deploy:
   - Critério Epic 43: Layout A ≥80% (de 17%), ≥30/38 campos obrigatórios (de 5/38)
   - Nunca foi executado após as correções — o 80% é projeção, não medição confirmada

3. **Validação multi-tipo de documento** — apenas boleto foi testado empiricamente:
   - Boleto bancário — baseline medido (Epic 43)
   - Certificado, Relatório, DIRF, Apólice — não testados
   - Pilar A só é completo quando múltiplos tipos passam
   - **Samples disponíveis em:** `backend/tests/fixtures/samples/` (14 PDFs reais organizados por tipo)

---

## Decisões Arquiteturais Locked

> Estas decisões não devem ser revertidas sem deliberação explícita.

| Decisão | Desde | Detalhes |
|---------|-------|---------|
| GPT-4o Vision **eliminado** do Stage 3.2 | Epic 46.2 | Mistral OCR incondicional por página representativa. PyMuPDF para bbox de imagens raster ($0). Ativado por `MISTRAL_API_KEY`, não `VISION_AI_ENABLED` |
| Pipeline = **5 stages** reais | Epic 43+ | Não 28 — ver `architecture/pipeline-real.md`. Design de 28 stages arquivado |
| **Pydantic v2** obrigatório em modelos de domínio | Epic 42 | `dict` raw é anti-pattern. `model_validate()` / `model_dump()`. Ver `backend/models/pipeline_context.py` |
| Mistral OCR para **tabelas raster** | Epic 43.2 | `pages=[page_index]` — não processa PDF inteiro |
| **Representative-First** no pipeline | Epic 43+ | Stages de análise operam só sobre páginas representativas, nunca todas |

---

## Estado do Código (2026-04-13)

**Modificados não commitados:**
- `backend/services/stages/stage3_structural/` — ajustes pós-Epic 43/46
- `docs/architecture/pipeline-architecture-v2.md` — changelog atualizado

**Não rastreados relevantes:**
- `backend/tests/test_stage3_image_area_handler.py` — testes novos
- `backend/scripts/audit_boleto_pillar_a.py` — script auditoria Pilar A

**Próximo passo de código:** revisar e commitar modificações do `stage3_structural/` antes de iniciar novo epic.

---

## Contexto de Epics Recentes

| Epic | Resultado | Impacto no domínio |
|------|-----------|-------------------|
| 46 — Vision Optimization | Done | GPT-4o eliminado, custo Stage 3.2: $0.01 → $0.001/cluster |
| 45 — Test Infrastructure | Done | 288 unit tests, `make test` ~5s, xdist paralelo |
| 44 — Pipeline Foundation Audit | Done | Clustering reavaliado e validado |
| 43 — Pipeline Accuracy | Done | Stage 3: 17% → ≥80% mapeamento boleto |

---

## Para o Próximo Epic

- Pilar A ainda precisa de validação completa com documento real (boleto + convênio + relatório)
- `@pm *create-epic` para iniciar Epic 47
- Atualizar este arquivo e a seção `## Estado Atual` do `CLAUDE.md` ao criar/fechar epic
