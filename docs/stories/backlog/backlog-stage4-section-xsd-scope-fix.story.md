# Backlog — Stage 4: Corrigir Section-XSD Scope Mismatch (RC-B)

## Status: Draft

## Origem

RCA `rca-2026-04-25-scalar-coverage-residual-53pct` (RC-B), evidence E2_correlated.
Identificado durante análise do E2E run 2026-04-25 (scalar_coverage=53.1%).

## Problema

Em `section_matching.py:_step_4_4_section_xsd_matching`, quando o label de uma seção de layout não casa diretamente com o nó XSD correto, o LLM recebe um **candidate set restrito ao nó errado** e escolhe o "menos errado" — gerando mapeamentos espúrios mas semanticamente plausíveis.

**Exemplo confirmado (E2E run 2026-04-25):**
- Seção `"Dados dos seguros:"` → deveria mapear para `Propostas.Propostas`
- Stage 4 casou a seção com nó `DadosPosicaoAteEmissao` (errado)
- LLM recebeu só os campos filhos de `DadosPosicaoAteEmissao` como candidatos
- Campo `"Contribuição 591,70"` → mapeado para `DadosPosicaoAteEmissao.NumeroCertificado` (wrong)

**Root cause estrutural:** O matching de seção usa comparação string/heurística fraca entre o label da seção no PDF e o nome do nó XSD. Divergência de vocabulário (PT vs. XSD inglês/abreviado) causa cascata de mapeamentos errados em toda a subárvore.

## Solução Proposta

**Fase 1 — Fallback flat_paths (rápido, baixo risco):**
Quando score de confiança do section-XSD matching cai abaixo de um threshold (ex: 0.4), em vez de forçar o LLM a usar o nó errado, usar `flat_paths` (todos os caminhos XSD disponíveis) como candidate set.

```python
if section_xsd_score < SECTION_MATCH_CONFIDENCE_THRESHOLD:
    candidate_paths = flat_xsd_paths  # fallback: busca global
else:
    candidate_paths = subtree_paths   # comportamento atual
```

**Fase 2 — Embedding similarity (melhor qualidade):**
Substituir a comparação string por embedding cosine similarity entre o label da seção e os nomes dos nós XSD. Usa `sentence-transformers` ou o próprio Gemini embedding API.

## Acceptance Criteria

- [ ] **AC1:** Seção com score < threshold usa `flat_paths` como candidate set
- [ ] **AC2:** Threshold documentado como constante em `constants.py`
- [ ] **AC3:** `"Contribuição 591,70"` para de mapear para `NumeroCertificado` — passa a mapear para path correto ou fica unmapped
- [ ] **AC4:** Nenhuma regressão em seções com score alto (comportamento atual preservado)
- [ ] **AC5:** Teste unitário: seção com score baixo recebe flat_paths; seção com score alto recebe subtree_paths

## Escopo

### IN
- `backend/services/stages/stage4_mapping/section_matching.py` — `_step_4_4_section_xsd_matching`
- `backend/services/stages/stage4_mapping/constants.py` — nova constante `SECTION_MATCH_CONFIDENCE_THRESHOLD`

### OUT
- Embedding similarity (Fase 2) — escopo desta story é só o fallback flat_paths
- Stage 3, Stage 2, Stage 5

## Estimativa

3–4h

## Dependências

- Story 48.16 Done (gate ≥80% confirmado) — RC-B é melhoria incremental, não bloqueante
- Não bloqueia Epic 49

## Prioridade

**P2** — Melhoria de qualidade pós-gate. Não é bloqueante para scalar_coverage ≥80% (RC-A/C/D já garantem isso). Aumenta cobertura em casos de vocabulário divergente PT vs. XSD inglês.

## Change Log

| Data | Agente | Ação |
|------|--------|------|
| 2026-04-25 | @sm | Draft criado — RC-B de rca-2026-04-25-scalar-coverage-residual-53pct |
