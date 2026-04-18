# docs/INDEX.md — Mapa de Navegação Canônico

> **Para agentes — ordem de leitura obrigatória:**
> 1. `docs/CURRENT-STATE.md` → onde estamos agora (epic ativo, decisões recentes)
> 2. Este arquivo → onde encontrar qualquer informação
> Não escaneie a pasta `docs/` manualmente.

---

## O que é este projeto

Sistema que migra documentos gerados pelo motor Planet Express para HTML templates reutilizáveis.
- **Não** é extrator de dados — o entregável é o **template visualmente fiel**
- PDFs Planet Express: sempre gerados por motor (vetoriais, não escaneados)
- Domínio: Portuguese (BR), boletos, convênios, relatórios corporativos

---

## Conceitos Fundamentais do Produto ← ler antes de qualquer epic de Pilar B ou C

| O que você quer saber | Onde ler | Status |
|----------------------|----------|--------|
| **Modelo template + contrato de dados (XSD opcional, label/value, coleções)** | `architecture/template-data-contract-model.md` | `current` |
| **Taxonomia de campos e modelo de binding (3 eixos, gaps para Pilar C)** | `architecture/field-taxonomy-and-binding-model.md` | `current` |

---

## Arquitetura do Sistema

| O que você quer saber | Onde ler | Status |
|----------------------|----------|--------|
| Visão geral do sistema (stack, componentes, deploy) | `architecture/system-architecture.md` | `current` |
| **Pipeline que REALMENTE RODA** ← começar aqui | `architecture/pipeline-real.md` | `current` |
| Contratos entre stages (5 stages reais, com tipos Pydantic) | `architecture/pipeline-contracts.md` | `current` |
| Stage 3 em detalhe (pós-Epic 43/46) | `architecture/pipeline-stage3-epic43.md` | `current` |
| Decisões arquiteturais (ADRs) | `adrs/` | — |

---

## Frontend / Editor Visual

| O que você quer saber | Onde ler |
|----------------------|----------|
| Spec canônica do frontend | `frontend/frontend-spec.md` |
| Audit de features (27 seções numeradas) | `frontend/feature-audit/` |
| Wireframes (HTML) | `frontend/wireframes/` |
| Specs de UX do editor | `frontend/ux-specs/` |
| Gap analysis spec vs implementação atual | `frontend/gap-analysis-frontend-v3.md` |

---

## Produto / PRD

| O que você quer saber | Onde ler |
|----------------------|----------|
| Product Requirements (PRD canônico) | `prd/prd.md` |
| Tech debt assessment | `prd/technical-debt-assessment.md` |

---

## Stories / Epics (AIOS)

| O que você quer saber | Onde ler |
|----------------------|----------|
| Epics ativos (40–46) | `stories/epics/` |
| Backlog de stories | `stories/backlog/` |

---

## QA / Investigações RCA

> Os caminhos abaixo são **gerados automaticamente por skills** — não mover nem renomear.

| O que você quer saber | Onde ler |
|----------------------|----------|
| Knowledge base RCA (padrões, SOPs, anti-patterns) | `qa/rca-knowledge/` |
| Investigações RCA executadas | `qa/investigations/` |
| Gap reports por epic | `qa/gap-reports/` |
| Fix requests pendentes | `qa/fix-requests/` |
| Guia de investigação RCA | `qa/rca-knowledge/rca-investigation-guide.md` |

---

## Reports / Reviews

> Gerados automaticamente por agents — não editar manualmente.

| O que você quer saber | Onde ler |
|----------------------|----------|
| Technical Debt Report | `reports/TECHNICAL-DEBT-REPORT.md` |
| Reports de bakeoff/spikes por epic | `reports/` |
| Reviews de brownfield (DB, QA, UX) | `reviews/` |

---

## Referências Externas

| O que você quer saber | Onde ler |
|----------------------|----------|
| Mistral API (OCR, bbox) | `api-references/mistral-openapi.yaml` |

---

## Investigações Técnicas (Spikes)

- `spikes/` — investigações pontuais de tecnologia
- `reports/epic-48/stage1-clustering-analysis.md` — análise completa Stage 1: problemas, diagnóstico, soluções em 3 camadas (2026-04-17)

---

## Assets Planet Express

- `exemplos/` — templates HTML de exemplo do motor Planet Express
- **Não editar** — são artefatos de referência do domínio

---

## O que NÃO está aqui

- `_archive/` — documentos históricos que levaram ao estado atual. Não leia para tomar decisões. Consulte apenas para entender contexto histórico.

---

## Para @architect

Leia: `architecture/system-architecture.md` → `architecture/pipeline-architecture-v2.md` → `adrs/`

## Para @dev

Leia: `architecture/pipeline-real.md` → `architecture/pipeline-contracts-v2.md` → story em `stories/epics/{epic}/` → `architecture/pipeline-stage3-epic43.md` (se tocando Stage 3)

## Para @qa

Leia: `qa/rca-knowledge/investigations.yaml` → `qa/rca-knowledge/anti-patterns.yaml` → story em review

## Para @ux-design-expert

Leia: `frontend/frontend-spec.md` → `frontend/ux-specs/` → `frontend/gap-analysis-frontend-v3.md`

## Para @pm / @po

Leia: `stories/epics/` → `stories/backlog/` → `prd/tech-debt-assessment.md`
