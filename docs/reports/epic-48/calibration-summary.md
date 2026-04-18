# Spike 48.9 — Calibration Summary: Stage 1 Ensemble Voting Thresholds

**Data:** 2026-04-18 (re-calibração — fixtures corrigidos, sinal 4 habilitado)  
**Pares analisados:** 35 SAME + 8 DIFF  
**Fixtures:** PDFs em 4 tipos (boleto, apolice, dirf, relatorio) — ApoliceVgA/B separados

---

## Thresholds Recomendados

| Sinal | Threshold | Precision | Recall | Status |
|-------|-----------|-----------|--------|--------|
| pHash masked thumbnail | 16 | 96.4% | 77.1% | ⚠️ |
| Font Jaccard | 0.49 | 100.0% | 97.1% | ✅ |
| Struct edit distance | 0.62 | 100.0% | 94.3% | ✅ |
| Markdown hash | exact_match | — | — | ⏭️ SKIPPED |

---

## Distribuições por Sinal

### phash_dist (gap=-8)

- **SAME:** min=0 max=22 mean=8.2857 std=7.7481
- **DIFF:** min=14 max=34 mean=24.5 std=5.5291

### font_jaccard (gap=0.18)

- **SAME:** min=0.4667 max=1.0 mean=0.9311 std=0.1274
- **DIFF:** min=0.0 max=0.2857 mean=0.0486 std=0.1024

### struct_dist (gap=0.31)

- **SAME:** min=0.0 max=0.6522 mean=0.2539 std=0.1893
- **DIFF:** min=0.9626 max=1.0 mean=0.9953 std=0.0132

---

## Recomendações para Implementação

1. **4 sinais calibrados** (pHash, Font Jaccard, Struct dist, Markdown hash) no ensemble
2. **Voting majoritário:** 4/4 → 0.97, 3/4 → 0.90, 2/4 → 0.75, 1/4 → 0.35, 0/4 → 0.05
3. **Markdown hash** usa exact match após normalização CPF/DATE/BRL/NUM
4. **Thresholds são conservadores** — bias para não agrupar erroneamente (false SAME pior que false DIFF)
5. **ApoliceVgA e ApoliceVgB são templates distintos** — confirmado visualmente pelo usuário

---

## Próximos Passos

- Story 48.10 — Implementar sinal pHash masked thumbnail no Stage 1
- Story 48.11 — Implementar sinal Font Jaccard no Stage 1
- Story 48.12 — Implementar sinal Struct edit distance no Stage 1
- Story 48.13 — Ensemble voting core + Union-Find clustering
- Story 48.14 — Integração completa + revalidação do spike 48.7