# Spike 48.9 — Calibration Summary: Stage 1 Ensemble Voting Thresholds

**Data:** 2026-04-18  
**Pares analisados:** 37 SAME + 7 DIFF  
**Fixtures:** 36 PDFs em 4 tipos (boleto, apolice, dirf, relatorio)

---

## Thresholds Recomendados

| Sinal | Threshold | Precision | Recall | Status |
|-------|-----------|-----------|--------|--------|
| pHash masked thumbnail | 16 | 96.4% | 73.0% | ⚠️ |
| Font Jaccard | 0.47 | 100.0% | 91.9% | ✅ |
| Struct edit distance | 0.65 | 100.0% | 91.9% | ✅ |
| Markdown hash | skipped | — | — | ⏭️ SKIPPED |

---

## Distribuições por Sinal

### phash_dist (gap=-10)

- **SAME:** min=0 max=24 mean=9.2973 std=7.8912
- **DIFF:** min=14 max=34 mean=24.5714 std=5.9682

### font_jaccard (gap=-0.29)

- **SAME:** min=0.0 max=1.0 mean=0.8808 std=0.2468
- **DIFF:** min=0.0 max=0.2857 mean=0.0556 std=0.1085

### struct_dist (gap=-0.02)

- **SAME:** min=0.0 max=1.0 mean=0.2943 std=0.2512
- **DIFF:** min=0.9813 max=1.0 mean=0.9973 std=0.0071

---

## Recomendações para Implementação

1. **Usar os 3 sinais calibrados** (pHash, Font Jaccard, Struct dist) como base do ensemble
2. **Voting majoritário:** 3/3 → high confidence, 2/3 → medium, 1/3 → low/review
3. **Instalar pymupdf4llm** para habilitar sinal 4 (markdown hash) — eleva precision
4. **Thresholds são conservadores** — bias para não agrupar erroneamente (false SAME pior que false DIFF)
5. **Rever após integração** com mais tipos (apolice Certificados distintos podem ter gap menor)

---

## Próximos Passos

- Story 48.10 — Implementar sinal pHash masked thumbnail no Stage 1
- Story 48.11 — Implementar sinal Font Jaccard no Stage 1
- Story 48.12 — Implementar sinal Struct edit distance no Stage 1
- Story 48.13 — Ensemble voting core + Union-Find clustering
- Story 48.14 — Integração completa + revalidação do spike 48.7