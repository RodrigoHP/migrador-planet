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
- **LLM:** OpenRouter → GPT-4o Vision (visual) + Gemini (field mapping)
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

## Referências profundas

- Arquitetura sistema: `docs/architecture/system-architecture.md`
- Arquitetura pipeline: `docs/architecture/pipeline-architecture-v2.md`
- Convenções e workflow AIOS: `.claude/rules/` (story lifecycle, agent handoff, RCA, tool examples)
