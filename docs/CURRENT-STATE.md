# Estado Atual do Projeto — Contexto de Domínio

**Status:** `current` — estado do domínio (Pilares, decisões locked, epics recentes)
**Dono:** `@pm` — atualiza ao fechar cada epic
**Fonte:** decisões de projeto + epics concluídos + código commitado
**Atualizar quando:** epic fechado ou decisão arquitetural locked/revertida
**Última validação:** 2026-04-14 (Epic 47 concluído)

> **Escopo:** decisões arquiteturais, estado do domínio, Pilares A/B/C.
> **NÃO inclui:** estado do SDC/workflow (fica em `.aios/`), handoffs entre agentes (`.aios/handoffs/`).
> **Responsável:** `@pm` atualiza ao fechar cada epic.

---

## Pilares — Estado

| Pilar | Descrição | Status |
|-------|-----------|--------|
| **A — Detecção** | Capturar TUDO do PDF (texto, tabelas raster, imagens, cores, fontes) | **GAPS PENDENTES aceitos** — validação multi-tipo concluída (Epic 47). Ver detalhes abaixo |
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

### Pilar A — Resultado da Validação (Epic 47, 2026-04-14)

Validação single-PDF via Railway API. Todos os tipos processam sem crash.

| Tipo | PDF | Layouts | Estrutura detectada | Status |
|------|-----|---------|---------------------|--------|
| Relatório | PosicaoConsolidada.pdf | 3 | 17 seções, 19 dinâmicos, 24 campos | ✅ |
| Extrato | PrevidenciaExtrato.pdf | 1 | 6 seções, 9 dinâmicos, 6 campos | ✅ |
| Apólice | ApoliceVg.pdf | 2 | 11 seções, 5 imagens, 28 dinâmicos | ✅ |
| Boleto | BoletoCorporateMercantil.pdf | 1 | 5 seções, 1 tabela, 20 dinâmicos | ✅ |
| Boleto | BoletoVg.pdf | 4 | 13 seções, 8 imagens, 44 dinâmicos | ✅ |
| DIRF | DirfInformaFinanceiro.pdf | 1 | **9 tabelas**, 28 linhas, 63 células | ✅ |
| Certificado | CertificadoPrevidencia.pdf | 5 | 12 seções, 41 dinâmicos | ✅ |
| Certificado | CertificadoVI.pdf | 4 | 15 seções, 34 dinâmicos | ✅ |

**Gaps aceitos:**
1. Multi-sample clustering: não validado por falta de múltiplas amostras do mesmo template. Validação possível quando Pilar B começar (precisa de 3+ PDFs do mesmo template).
2. Infra Railway: spaCy degradado, Redis não configurado — corrigir antes de Pilar B.
3. Crash defensivo: submeter PDFs de templates diferentes juntos causa crash — criar story backlog.

**Ações antes de Pilar B:**
- Commitar `backend/services/stages/stage3_structural/` + `test_stage3_image_area_handler.py`
- Corrigir spaCy no Railway (`pt_core_news_sm`)
- Adquirir 3+ PDFs do mesmo template para cada tipo

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
| 48 — Pilar B: Binding XSD | **Em progresso** | Spike 48.7 executado (2026-04-17). 2 gaps bloqueantes identificados. Ver `docs/reports/epic-48/spike-48-7-findings.md`. |
| 47 — Pilar A Multi-Tipo Validation | Done | Validação single-PDF: todos os 5 tipos OK. Gaps aceitos (multi-sample, infra). |
| 46 — Vision Optimization | Done | GPT-4o eliminado, custo Stage 3.2: $0.01 → $0.001/cluster |
| 45 — Test Infrastructure | Done | 288 unit tests, `make test` ~5s, xdist paralelo |
| 44 — Pipeline Foundation Audit | Done | Clustering reavaliado e validado |
| 43 — Pipeline Accuracy | Done | Stage 3: 17% → ≥80% mapeamento boleto |

---

## Para o Próximo Epic

- **Epic 48 em progresso** — Pilar B: Binding XSD
- **Spike 48.7 concluído (2026-04-17):** 3 PDFs PosicaoConsolidada via Railway API
- **Fix entregue:** Stage 5 `data-list=""` corrigido (commit `82a1d56`, deployado)

### Gaps bloqueantes identificados (ver `docs/reports/epic-48/spike-48-7-findings.md`)

| Gap | Impacto | Prioridade |
|-----|---------|-----------|
| **Gap 1 — Stage 1 clustering:** 3 layouts / 3 PDFs em vez de 1. Algoritmo pesa conteúdo em vez de estrutura. | Degrada Stage 3 (menos dinâmicos) e Stage 4 (menos cobertura) | P0 |
| **Gap 2 — Scalar coverage 63.2%** (threshold: 80%). Campos do PDF não casam com nós do XSD. | Template gerado incompleto | P1 — só atacar após Gap 1 |

**Próximo passo:** investigar Stage 1 — ler algoritmo de similaridade, instrumentar scores para os 3 PDFs, ajustar para usar similaridade estrutural (bboxes/labels) e não de conteúdo.
