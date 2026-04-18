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
| 48 — Pilar B: Binding XSD | **Done (GAPS PENDENTES aceitos)** | Todas as stories concluídas. Core funciona (Stage 3/4/5 PASS). Scalar coverage 63.2% precisa re-validação com Stage 1 fixado antes de declarar COMPLETO. |
| 47 — Pilar A Multi-Tipo Validation | Done | Validação single-PDF: todos os 5 tipos OK. Gaps aceitos (multi-sample, infra). |
| 46 — Vision Optimization | Done | GPT-4o eliminado, custo Stage 3.2: $0.01 → $0.001/cluster |
| 45 — Test Infrastructure | Done | 288 unit tests, `make test` ~5s, xdist paralelo |
| 44 — Pipeline Foundation Audit | Done | Clustering reavaliado e validado |
| 43 — Pipeline Accuracy | Done | Stage 3: 17% → ≥80% mapeamento boleto |

---

## Para o Próximo Epic

- **Epic 48 concluído (2026-04-18)** — Pilar B: GAPS PENDENTES (aceitos). Re-validação E2E recomendada após deploy.
- **Próximo epic:** Epic 49 — Pilar C: Editor Visual (renderizar `<repeat>` como loop interativo no Vue 3)
- **Pré-requisito Pilar C:** deploy da branch `feature/epic-48-pilar-b` + re-validação E2E confirmar scalar coverage ≥ 80%

### Epic 48 — Status detalhado (2026-04-18)

**Wave 0 — Stage 1 Fix: CONCLUÍDA ✅**

Gap 1 Stage 1 identificado no spike 48.7 (fórmula `0.8*geo + 0.2*den` pesava conteúdo, não estrutura) foi corrigido via ensemble voting de 4 sinais estruturais:

| Sinal | Threshold | Função | Tipo |
|-------|-----------|--------|------|
| pHash masked thumbnail | distância ≤ 16 | `masked_phash(page)` | bidirecional |
| Font Jaccard | jaccard ≥ 0.47 | `font_signature(page)` | bidirecional |
| Struct edit distance | edit_dist ≤ 0.65 | `struct_sequence(blocks)` | bidirecional |
| Markdown fingerprint | match = SAME | `markdown_fingerprint(page)` | one-sided |

ENSEMBLE_SCORES: `{4: 0.97, 3: 0.90, 2: 0.75, 1: 0.35, 0: 0.05}`

Validação local (7/7 casos, 6 tipos de template): PosicaoConsolidada×4, BoletoVg×3, BoletoIndividual×4, BoletoCorporate×4, ApoliceVgB×2, DirfInforma×3 → todos cluster único em p0. Boleto DIFF → 3 clusters distintos.

**Gaps remanescentes (aceitos antes de continuar):**

| Gap | Impacto | Status |
|-----|---------|--------|
| **Gap 2 — Scalar coverage 63.2%** | Template gerado incompleto | P1 — atacar após Stage 1→3 fix completo |

**Próximo passo:** iniciar Wave 1 (48.1 + 48.2 + 48.3) — Railway infra, crash fix, ground truth.
