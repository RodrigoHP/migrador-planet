# Epic 47 — Pilar A: Validação Multi-Tipo de Documento

## Status: Done

## Objetivo

Validar que o pipeline processa corretamente todos os tipos de documento do domínio Planet Express — não apenas o boleto que foi o alvo do Epic 43. Ao final deste epic, o Pilar A deve ser declarado **completo** ou ter um backlog de gaps explícito para o próximo epic.

## Contexto

O Epic 43 corrigiu o pipeline para boleto (`Corporate.Boleto.Convenio.pdf`): 17% → ≥80% de mapeamento. Mas a validação foi feita em apenas **1 tipo de documento**. O Pilar A exige que o pipeline capture TUDO de qualquer PDF Planet Express.

Inspeção realizada em 2026-04-14 contra `backend/tests/fixtures/samples/` (14 PDFs reais) revelou:

| Tipo | Arquivos | Rasters | Tabelas vetoriais | Risco |
|------|---------|---------|-------------------|-------|
| boleto | 4 | 1–3 | 0–1 | 🟢 similar ao validado |
| apolice | 1 | 1 | 1 | 🟢 similar |
| relatorio | 4 | 0–1 | 0–3 | 🟢 mais simples |
| dirf | 1 | 2 | 9 | 🟡 muitas tabelas vetoriais |
| certificado | 5 | 2–6 | 1–7 | 🔴 Type3 fonts, fontes customizadas |

**Riscos identificados:**
- `CertiticadoPrevidencia.pdf` — `Type3 (14 0 R)` font: PyMuPDF não extrai texto de fontes bitmap
- `CertificadoHinode.pdf` — `SenticoSansDT` font customizada: pode não ter mapeamento de caracteres
- `DirfInformaFinanceiro.pdf` — 9 tabelas vetoriais: nunca testamos volumes assim no Stage 3

**Pré-requisito:** `backend/tests/fixtures/samples/` organizado com 14 PDFs reais (gitignored por segurança).

## Stories

| Story | Título | Status | Prioridade | Esforço | Dep |
|-------|--------|--------|-----------|---------|-----|
| 47.1 | SPIKE: Validar relatórios e apólice contra pipeline | Done | P0 | 4h | — |
| 47.2 | SPIKE: Validar boletos novos contra pipeline | Done | P0 | 4h | — |
| 47.3 | SPIKE: Validar DIRF contra pipeline — stress de tabelas vetoriais | Done | P1 | 4h | — |
| 47.4 | SPIKE: Investigar Type3 fonts e fontes customizadas nos certificados | Done | P0 | 6h | — |
| 47.5 | SPIKE: Validar certificados contra pipeline | Done | P1 | 6h | 47.4 |
| 47.6 | Consolidação: declarar Pilar A completo ou abrir backlog de gaps | Done | P0 | 2h | 47.1–47.5 |

**Total estimado:** ~26h

## Método de Validação

Para cada tipo de documento:
1. Subir PDF via API/UI com pipeline rodando
2. Capturar output JSON do job Supabase
3. Rodar `backend/scripts/audit_boleto_pillar_a.py` (adaptado para o PDF)
4. Comparar PyMuPDF ground truth vs pipeline output
5. Documentar gaps encontrados

## Critério de Conclusão do Epic

- Pipeline processa sem crash todos os 13 PDFs válidos (exceto `BoletoIndividual_05220.pdf` criptografado — usar `_unlocked`)
- Relatórios e boletos: mapeamento ≥80% (validado no Epic 43 para boleto)
- Certificados: diagnóstico claro do impacto de Type3/fontes customizadas
- Story 47.6 produz um dos dois resultados:
  - **Pilar A COMPLETO** — todos os tipos passam, avançar para Epic 48 (Pilar B)
  - **Gaps documentados** — lista explícita de issues com stories no backlog

## Arquivos Relevantes

- `backend/tests/fixtures/samples/` — PDFs organizados por tipo (local only, gitignored)
- `backend/scripts/audit_boleto_pillar_a.py` — script de auditoria (adaptável por PDF)
- `backend/scripts/inspect_rca_convenio.py` — inspeção de convênio
- `docs/CURRENT-STATE.md` — atualizar ao fechar epic (Pilar A status)

## Change Log

| Date | Agent | Action |
|------|-------|--------|
| 2026-04-14 | @pm | Epic criado — inspeção de 14 PDFs reais revelou riscos em certificados (Type3 fonts) e DIRF (9 tabelas vetoriais). Stories ordenadas por risco crescente |
| 2026-04-14 | @dev | Epic concluído — validação single-PDF bem-sucedida para todos os tipos. Pipeline funciona para relatórios, extrato, apólice, boleto, DIRF e certificados. Gap: multi-sample clustering não validado (sem múltiplas instâncias do mesmo template nos fixtures). Decisão 47.6: GAPS PENDENTES aceitos. Ver `docs/reports/epic-47/pilar-a-final-report.md` |
