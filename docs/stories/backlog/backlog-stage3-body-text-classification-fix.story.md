# Backlog — Stage 3: Classificar Texto Corrido de Carta como Estático

## Status: Done — implementado como Story 48.14 (commit 6ad74b2)

## Origem

RCA `rca-2026-04-25-scalar-coverage-residual-53pct` (RC-A) identificado durante AC6 da Story 48.12.
E2E run 2026-04-25: 7 de 32 field_mappings são parágrafos de carta classificados erroneamente como `likely_dynamic` pelo Stage 3.1.

## Problema

O Stage 3.1 (`multi_example_analysis.py`) classifica campos comparando valores entre múltiplos PDFs:
- Valores que variam entre PDFs → `dynamic`
- Valores que se repetem → `static`
- Valores sem evidência suficiente → `likely_dynamic` (fallback)

O fallback `likely_dynamic` captura parágrafos inteiros de cartas corporativas que variam ligeiramente entre clientes (ex: nome do cliente embutido no texto corrido). Esses campos chegam ao Stage 4 como candidatos para binding XSD. O LLM tenta mapear mesmo que o campo seja claramente texto não-estruturado — consumindo caminhos XSD que deveriam ir para campos reais.

**Exemplos de false positives confirmados (run 2026-04-25):**
- `'Pedimos que você verifique seus dados'` → mapeado para `ClienteTelefone`
- `'pessoais e planos contratados'` → mapeado para `Bairro`
- `'JARDIM PAIQUERE, VALINHOS, SP'` → mapeado para `CEP`
- `'Conforme seu pedido, apresentamos'` → mapeado para `ClienteTelefone` (duplicado)
- `'(demais localidades) e 0800 771 5472'` → mapeado para `NomeCliente`
- `'de contato disponíveis no site'` → mapeado para `DataUltAltHistRelacionamento`

**Impacto:** 7 caminhos XSD "roubados" → campos reais (TELEFONE, E-MAIL, CEP, Apólice) ficam sem mapeamento.

## Solução Proposta

Adicionar heurística de classificação pós-multi-example em Stage 3 para identificar texto corrido:

**Heurística 1 — Ausência de delimitador label:valor:**
- Campos sem label explícito E com value contendo ≥3 palavras funcionais (artigos, preposições, verbos) → candidato a body text

**Heurística 2 — Comprimento e pontuação:**
- value_text com > N tokens e sem padrão de campo (sem `:`, sem formato numérico, sem data) → provável texto corrido

**Heurística 3 — Ratio de palavras funcionais:**
- Calcular ratio stopwords/total usando spaCy `pt_core_news_sm` já disponível no stack
- Ratio > 0.5 → classificar como `static_body_text` (nova categoria) — não enviar ao Stage 4

**Alternativa simples (v1):** Allowlist de padrões de "campos estruturados" (CPF, CNPJ, telefone, e-mail, data, CEP, valor monetário, número de certificado) — só passar ao Stage 4 campos que batem pelo menos um padrão OR têm label explícito.

## Acceptance Criteria

- [ ] **AC1:** Heurística implementada em Stage 3 — campos classificados como `static_body_text` não chegam ao Stage 4 como candidatos para binding XSD
- [ ] **AC2:** Re-run E2E com os 4 PDFs: `scalar_coverage ≥ 0.80` atingido com fix RC-A aplicado (nenhum path XSD consumido por parágrafos de carta)
- [ ] **AC3:** Testes unitários para a heurística com exemplos de body text brasileiro (carta, instruções, saudações) e campos estruturados (telefone, e-mail, certificado)
- [ ] **AC4:** `likely_dynamic` count nos resultados Stage 3 não inclui texto corrido com ratio de stopwords > 0.5
- [ ] **AC5:** Nenhuma regressão no tipo `boleto` — campos de boleto continuam classificados como `dynamic`

## Escopo

### IN
- `backend/services/stages/stage3_structural/multi_example_analysis.py` — heurística de body text
- `backend/services/stages/stage3_structural/` — nova categoria `static_body_text` se necessário
- Testes unitários

### OUT
- Stage 4 section_matching.py (o fix RC-C é story separada)
- Stage 4 constants.py — sem alteração de prompt nesta story
- Re-trabalhar Stage 1 ou Stage 2

## Estimativa

3-5h

## Dependências

- Nenhuma — pode ser implementada independentemente de RC-C e RC-D

## Prioridade

**P0** — Bloqueante para o gate de scalar_coverage ≥ 80% do Epic 49.
RC-A é responsável por ~7 das 15 lacunas de cobertura (46% dos campos não mapeados).

## Change Log

| Data | Agente | Ação |
|------|--------|------|
| 2026-04-25 | @dev | Draft criado — origem AC6 Story 48.12, RCA rca-2026-04-25-scalar-coverage-residual-53pct |
