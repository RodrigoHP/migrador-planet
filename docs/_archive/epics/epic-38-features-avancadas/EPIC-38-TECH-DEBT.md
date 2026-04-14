# Epic 38 — Tech Debt Backlog

> Identificados durante QA Gate do Epic 38 (Features Avancadas)
> Data: 2026-04-08
> Branch: `feature/epic-38-features-avancadas`

---

## Debitos Tecnicos

### TD-38.1: ZIP import previewHtml sem sanitizacao

| Campo | Valor |
|-------|-------|
| **Severidade** | LOW |
| **Origem** | Story 38.3 QA Gate (CONCERNS) |
| **Arquivo** | `frontend/src/organisms/BibliotecasModal.vue` (import ZIP) |
| **Estimativa** | ~30 min (1 ponto) |

**Problema:** Ao importar ZIP de componentes, o campo `previewHtml` do JSON eh renderizado via `v-html` sem regenerar via `generatePreviewHtml()`. Um ZIP crafted poderia injetar HTML/JS (self-XSS).

**Fix proposto:** No handler de import ZIP, regenerar `previewHtml` chamando `generatePreviewHtml(component.data)` em vez de usar o valor do arquivo importado.

**Justificativa de severidade LOW:** Self-XSS requer acao explicita do usuario (importar um ZIP malicioso manualmente).

---

### TD-38.2: template_name sem sanitizacao de conteudo

| Campo | Valor |
|-------|-------|
| **Severidade** | LOW |
| **Origem** | Story 38.6 QA Gate |
| **Arquivo** | `backend/routers/upload.py`, frontend exibicao |
| **Estimativa** | ~30 min (1 ponto) |

**Problema:** `template_name` eh input do usuario persistido e exibido na toolbar/save/ZIP filename sem sanitizacao de conteudo (caracteres especiais, HTML entities).

**Fix proposto:** Sanitizar `template_name` no upload: strip HTML, limitar charset a alfanumerico + espacos + hifens, max 100 chars.

**Justificativa de severidade LOW:** Usado apenas em display e filename tem fallback seguro.

---

## Oportunidades de Melhoria (Backlog Futuro)

> Estas NAO sao debitos tecnicos — sao oportunidades de evolucao identificadas no Spike 38.1 (Vision AI + pgvector Evaluation).
> Referencia completa: `docs/spikes/38.1-vision-ai-pgvector-evaluation.md` secao 7.

| # | Oportunidade | Descricao |
|---|-------------|-----------|
| OM-38.1 | Cache de matchings | Cache por XSD + layout hash para evitar re-processamento |
| OM-38.2 | Prompt engineering few-shot | Adicionar few-shot examples no prompt do Gemini Flash para melhorar qualidade do matching |
| OM-38.3 | Feedback loop de matchings | Aproveitar matchings manuais do usuario como dados de treinamento/refinamento |
| OM-38.4 | Table-aware matching | Matching especializado para headers multi-nivel em tabelas complexas |

---

## Resumo

| Tipo | Qtd | Pontos |
|------|-----|--------|
| Debitos tecnicos (LOW) | 2 | 2 |
| Oportunidades de melhoria | 4 | A estimar |
| **Total debitos** | **2** | **2 pontos** |
