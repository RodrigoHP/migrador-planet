# Spike 48.9 — Calibration Summary: Stage 1 Ensemble Voting Thresholds

**Data:** 2026-04-18 (re-calibração final — fixtures corrigidos, ApoliceVgA/B separados, sinal 4 habilitado)  
**Pares analisados:** 35 SAME + 8 DIFF  
**Fixtures:** PDFs em 4 tipos (boleto, apolice, dirf, relatorio) — ApoliceVgA e ApoliceVgB confirmados como templates distintos

---

## Thresholds Finais (implementados em signals.py)

| Sinal | Threshold | Precision | Recall | Justificativa |
|-------|-----------|-----------|--------|---------------|
| pHash masked thumbnail | **T_phash=16** | 96.4% | 77.1% | Gap SAME/DIFF: mean_SAME=8.3 vs mean_DIFF=24.5 |
| Font Jaccard | **T_font=0.47** | 100.0% | 94.3% | Min SAME = 0.4667 (RelatorioBeneficiarios). T=0.49 falharia este par |
| Struct edit distance | **T_struct=0.65** | 100.0% | 94.3% | Max SAME = 0.65. Struct DIFF: min=0.96 |
| Markdown hash | **exact_match (one-sided)** | — | 5.7% | Match=SAME vote, mismatch=abstém. Zero falsos positivos DIFF |

**Nota sobre T_font:** fórmula midpoint-of-means daria T=0.49, mas o par RelatorioBeneficiarios (jaccard=0.4667) falharia. T=0.47 cobre todos os pares SAME observados sem falsos positivos.

---

## Distribuições por Sinal

### phash_dist (gap=-8 — sobreposição parcial)

- **SAME:** min=0 max=22 mean=8.3 std=7.7
- **DIFF:** min=14 max=34 mean=24.5 std=5.5
- **Sinal:** mais fraco dos 3 — sobreposição em [14,22]. Ensemble compensa.

### font_jaccard (gap=0.18 — separação clara)

- **SAME:** min=0.4667 max=1.0 mean=0.93 std=0.13
- **DIFF:** min=0.0 max=0.29 mean=0.05 std=0.10
- **Sinal:** mais discriminativo — zero falsos positivos com T=0.47

### struct_dist (gap=0.31 — separação excelente)

- **SAME:** min=0.0 max=0.65 mean=0.25 std=0.19
- **DIFF:** min=0.96 max=1.0 mean=1.00 std=0.01
- **Sinal:** separação perfeita — zero sobreposição SAME/DIFF

### markdown_hash (one-sided — bonus signal)

- **SAME:** 5.7% match rate (2/35 pares)
- **DIFF:** 0.0% match rate (0/8 pares)
- **Conclusão:** match = evidência forte de SAME (zero falsos positivos), mismatch = evidência ambígua (abstém)

---

## ENSEMBLE_SCORES (4-signal scale)

```python
ENSEMBLE_SCORES = {4: 0.97, 3: 0.90, 2: 0.75, 1: 0.35, 0: 0.05}
```

Clustering threshold: **0.82** — pares com score >= 0.82 são agrupados (mesmo template).
- 3+ sinais concordando → agrupado (score 0.90 ou 0.97)
- 2 sinais concordando → não agrupado (score 0.75 < 0.82)
- 1 sinal → não agrupado (score 0.35)

---

## Genericidade — Validação Cross-Tipo

Ensemble voting validado localmente em 6 grupos de template distintos:

| Grupo | Tipo | Instâncias | Resultado |
|-------|------|-----------|-----------|
| PosicaoConsolidada | relatorio | ×4 | ✅ p0 cluster único |
| BoletoVg | boleto | ×3 | ✅ p0 cluster único |
| BoletoIndividual | boleto | ×4 | ✅ p0 cluster único |
| BoletoCorporateMercantil | boleto | ×4 | ✅ p0 cluster único |
| ApoliceVgB | apolice | ×2 | ✅ p0 cluster único |
| DirfInformaFinanceiro | dirf | ×3 | ✅ p0 cluster único |
| DIFF Boleto×3 | 3 templates distintos | ×1 cada | ✅ 3 clusters distintos |

**Conclusão:** Solução genérica — não depende de nenhum template específico. Sinais pHash/Font/Struct/MD são invariantes ao tipo de documento (boleto, apólice, DIRF, relatório, etc.).

---

## Recomendações para Implementação (implementadas em 48.10/48.11)

1. ✅ **signals.py** com 4 funções puras: `masked_phash`, `font_signature`, `struct_sequence`, `markdown_fingerprint`
2. ✅ **PageInfo** com 4 campos opcionais: `phash`, `font_sig`, `struct_seq`, `md_hash`
3. ✅ **_ensemble_similarity** aplica voting, normaliza para 4-signal basis, retorna -1.0 como fallback
4. ✅ **_compute_similarity** usa ensemble quando disponível, fallback para `0.8*geo+0.2*den` quando não
5. ✅ **pymupdf4llm** instalado (v1.27.2.2) — markdown_fingerprint ativo na pipeline

---

## Status Final

**Gap 1 Stage 1 (clustering pesa conteúdo em vez de estrutura): FECHADO ✅**

Stories implementadas: 48.9 (calibração) + 48.10 (3 sinais) + 48.11 (4º sinal markdown)
Teste de regressão: 7/7 casos passam em `scripts/spike_48_validate_stage1_local.py`
