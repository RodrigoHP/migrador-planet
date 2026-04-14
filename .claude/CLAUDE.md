# Migrador Planet — Projeto

## O que é

Sistema que **migra documentos gerados pelo motor Planet Express para HTML templates reutilizáveis**. Usuário sobe PDFs de exemplo → pipeline analisa → gera template HTML com campos dinâmicos + mapping XSD.

## O que NÃO é

- **NÃO é extrator de dados** de documentos. O valor das células, dos campos variáveis, etc. NÃO é o entregável final.
- O entregável é o **template visualmente fiel** que depois é preenchido por qualquer fonte de dados.

## O template precisa preservar

- Estrutura visual completa (layout, posições, bboxes)
- **Fontes** (family, size, weight)
- **Cores** (texto, background, borders)
- Imagens (estáticas como logos; dinâmicas como barcodes)
- Tabelas (estrutura + valores fixos + campos dinâmicos)
- Valores **fixos** (texto que não muda entre instâncias — preservar o texto exato)
- Valores **dinâmicos** (identificados por comparação multi-sample, mapeados para XSD)

## Workflow do usuário

1. **Criação de template:** sobe 3+ PDFs de exemplo do mesmo tipo → pipeline clusteriza cross-document → detecta dinâmico vs fixo → gera template + mapping XSD
2. **Edição/reuso:** re-importa template para ajustar bindings, trocar fonte de dados, testar configurações
3. **Criação do zero:** ou cria template manualmente no editor e reprocessa

## Escala

- **~200 templates distintos** em produção (one-time creation, depois só edição)
- Cada template criado com 3+ sample PDFs
- Cada PDF com até ~20 páginas, tipicamente ~18 clusters distintos (2 extras são overflow de tabelas dinâmicas)
- **NÃO é cenário de milhares de docs/dia** — é low-volume, high-fidelity template authoring

## Domínio — PDFs Planet Express

- Sempre **gerados por motor** (vetoriais, não escaneados, sem form fields)
- Tabelas podem ser vetoriais OU raster (JPEG queimado com tabela embutida)
- **Idioma:** Portuguese (BR) — acentos, cedilhas, R$, dd/mm/aaaa
- Tipos comuns: boletos bancários, convênios, relatórios corporativos

## Framework de trabalho do usuário — 3 Pilares sequenciais

Usuário divide o problema em pilares que devem ser fechados em ordem:
- **Pilar A — Detecção:** capturar TUDO do PDF (texto, estrutura, tabelas, imagens, cores, fontes)
- **Pilar B — Binding:** mapear para XSD / fonte de dados
- **Pilar C — Editor:** exibir no editor visual

**Nunca avance para B ou C com A incompleto.**

## Stack

- **Backend:** Python 3.12 + FastAPI + PyMuPDF (fitz) + pdfplumber + spaCy pt_core_news_sm + scikit-learn
- **LLM:** Mistral OCR (tabelas raster + bbox imagens, Stage 3) + Gemini (field mapping) — GPT-4o Vision eliminado no Epic 46.2
- **Frontend:** Vue 3 + TypeScript + Pinia + Vite
- **Storage:** Supabase (Postgres + Storage)
- **Deploy:** Railway (backend) + Vercel (frontend)

## Convenções Backend

**Modelos de dados:** Pydantic v2 obrigatório — `dict` raw é anti-pattern para dados de domínio (migrado no Epic 42). Modelos em `backend/models/`. API v2: `model_validate()` / `model_dump()`.

**Testes:** Todo teste precisa de marker — testes sem marker não são coletados pelo tier correto.
- `@pytest.mark.unit` — sem I/O real (sem PDF, fitz, LLM, Supabase)
- `@pytest.mark.integration` — toca pipeline real, PDFs sintéticos, LLM mockado
- `@pytest.mark.benchmark` — performance, não roda em CI
- `make test` (unit, ~5s) · `make test-integration` (paralelo xdist) · `make test-all`
- Fixtures session-scoped em `backend/tests/conftest.py`: `session_simple_pdf_path`, `session_boleto_pdf_path`, `session_simple1p_pdf_path`

## Estado Atual

> **Atualizar a cada epic fechado. Workflow/SDC state fica em `.aios/` — não duplicar aqui.**

- **Pilar A:** GAPS PENDENTES aceitos — validação multi-tipo concluída (Epic 47). Estrutura detectada para todos os 5 tipos (relatório, boleto, DIRF, apólice, certificado). Gap: multi-sample clustering não validado (sem fixtures multi-instância).
- **Epic ativo:** Epic 48 — Pilar B: Binding XSD (6 stories criadas, 20h estimadas)
- **Pré-requisito Epic 48:** usuário fornecer 3+ PDFs do mesmo template por tipo antes de iniciar 48.4
- **Iniciar com:** 48.1 (Railway infra) + 48.2 (crash fix) + 48.3 (ground truth) em paralelo
- **Decisão locked:** GPT-4o Vision eliminado — Mistral incondicional no Stage 3.2
- **Decisão locked:** Pipeline = 5 stages reais (não 28 do design)

Para contexto completo: `docs/CURRENT-STATE.md`

## Referências profundas

> **Agentes — leia nesta ordem antes de qualquer trabalho:**
> 1. Seção `## Estado Atual` acima — snapshot do projeto (já está aqui)
> 2. `docs/INDEX.md` — onde encontrar qualquer informação

- **Mapa de navegação:** `docs/INDEX.md`
- **Contexto detalhado:** `docs/CURRENT-STATE.md` (decisões, histórico de epics, código pendente)
- Pipeline real (o que roda): `docs/architecture/pipeline-real.md`
- Convenções e workflow AIOS: `.claude/rules/`

## Manutenção de Documentação

**Modelo:** um doc por tópico, atualizado in-place. Git guarda o histórico. Sem sufixos `-v2`, `-v3` em nomes de arquivo.

Cada doc canônico tem `**Status:**` no cabeçalho:
- `current` — reflete o código hoje
- `reference` — design/visão, pode divergir do código
- (sem status ou em `_archive/`) — histórico, não usar para decisões

**Regras de atualização:**
- Story modifica `backend/services/stages/stage*/` → `@architect` atualiza `pipeline-real.md` antes do QA gate
- Story modifica Stage 3 especificamente → `@architect` atualiza `pipeline-stage3-epic43.md`
- Mudança de stack ou novo serviço → `@architect` atualiza `system-architecture.md`
- Doc novo criado → quem criou adiciona entrada em `docs/INDEX.md` na mesma PR
- Epic fechado → `@architect` valida se todos os `current` ainda refletem o código
