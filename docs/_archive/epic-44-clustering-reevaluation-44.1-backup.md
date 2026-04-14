# Epic 44 — Clustering Reevaluation: Ablation Study Report

**Data:** 2026-04-13  |  **Story:** 44.1  |  **Agente:** @dev (Dex) YOLO  |  **Budget usado:** $0.00

## 1. Sumário Executivo

Ablation study do Stage 1 Layout Clustering em 3 dimensões:
- **Feature extraction:** F0 (baseline blocks) vs F1 (LayoutLMv3) vs F2 (CLIP) vs F3 (DINOv2)
- **Similarity+Clustering:** S0 (baseline geometry+graph) vs S1-S5 (cosine + HDBSCAN/DBSCAN/Spectral/Agglomerative)
- **Visual cross-check:** V0 (pHash) vs V1 (CLIP cosine) vs V2 (DINOv2 cosine) vs V3 (SSIM)

## 2. Ground Truth

| Métrica | Valor |
|---|---|
| PDFs distintos | 7 |
| Templates distintos | 3 (boleto 2via Sicoob, relação convênios, boleto condomínio) |
| Páginas rotuladas | 9 |
| Ideal (AC1) | 30-50 páginas |
| Clusters esperados | 4 (A, B_page0, B_page1, C) |

**Limitação:** Dataset abaixo do ideal. Spike valida metodologia; expansão em iteração 2.

## 3. Métricas — Feature Extraction Ablation (AC4)

Mantendo S0 (geometry/graph), variando apenas feature extraction:

| Feature | Implementação | ARI | Homogeneity | Completeness | V-measure | N clusters (pred/true) | Status |
|---|---|---|---|---|---|---|---|
| F0 | BlockInfo manual (baseline) | 1.000 ±0.000 | 1.000 ±0.000 | 1.000 ±0.000 | 1.000 ±0.000 | 4/4 | OK |
| F1 | LayoutLMv3 (microsoft/layoutlmv3-base) | 0.571 ±0.000 | 0.727 ±0.000 | 1.000 ±0.000 | 0.842 ±0.000 | 3/4 | OK |
| F2 | CLIP (openai/clip-vit-base-patch32) | 0.571 ±0.000 | 0.727 ±0.000 | 1.000 ±0.000 | 0.842 ±0.000 | 3/4 | OK |
| F3 | DINOv2 (facebook/dinov2-base) | 0.571 ±0.000 | 0.727 ±0.000 | 1.000 ±0.000 | 0.842 ±0.000 | 3/4 | OK |

## 4. Métricas — Similarity + Clustering Ablation (AC5)

Usando melhor feature disponível, variando similarity+clustering:

| Combo | Feature | Similarity | Clustering | ARI | Homogeneity | Completeness | V-measure | N_pred/N_true | Tempo (s) |
|---|---|---|---|---|---|---|---|---|---|
| S0 | F0 | geometry | graph | 1.000 ±0.000 | 1.000 ±0.000 | 1.000 ±0.000 | 1.000 ±0.000 | 4/4 | 0.142 |
| S1 | F3 | cosine | graph | 0.571 ±0.000 | 0.727 ±0.000 | 1.000 ±0.000 | 0.842 ±0.000 | 3/4 | 0.001 |
| S2 | F3 | cosine | hdbscan | — | — | — | — | —/4 | SKIP: hdbscan not installed |
| S3 | F3 | cosine | dbscan | 0.571 ±0.000 | 0.727 ±0.000 | 1.000 ±0.000 | 0.842 ±0.000 | 3/4 | 0.058 |
| S4 | F3 | cosine | spectral | 1.000 ±0.000 | 1.000 ±0.000 | 1.000 ±0.000 | 1.000 ±0.000 | 4/4 | 0.765 |
| S5 | F3 | cosine | agglomerative | 1.000 ±0.000 | 1.000 ±0.000 | 1.000 ±0.000 | 1.000 ±0.000 | 4/4 | 0.001 |

## 5. Métricas — Visual Cross-check Ablation (AC6)

Warnings emitidos pelo cross-check (spurious = páginas do mesmo cluster com visual diferente):

| Check | Método | Warnings gerados | Observação |
|---|---|---|---|
| V0 | pHash (imagehash, distance ≤10) | 0 | OK |
| V1 | CLIP cosine (F2 embeddings) | 0 | OK |
| V2 | DINOv2 cosine (F3 embeddings) | 0 | OK |
| V3 | SSIM (scikit-image) | 0 | OK |

## 6. Casos de Borda (AC7)

### Caso 1: metric_delta

- **baseline:** F0/geometry/graph ARI=1.000
- **alternative:** F2/cosine/graph ARI=0.571
- **ari_delta:** -0.4286
- **interpretation:** baseline better

### Caso 2: metric_delta

- **baseline:** F0/geometry/graph ARI=1.000
- **alternative:** F3/cosine/graph ARI=0.571
- **ari_delta:** -0.4286
- **interpretation:** baseline better

### Caso 3: metric_delta

- **baseline:** F0/geometry/graph ARI=1.000
- **alternative:** F3/cosine/dbscan ARI=0.571
- **ari_delta:** -0.4286
- **interpretation:** baseline better

### Caso 4: density_variation

- **description:** Convênio pages: page 0 has high density (full table), page 1 has low density (footer only). Different labels: B_page0 vs B_page1.
- **pages_involved:** convenio-sample1:pg0, convenio-sample1:pg1, convenio-sample2:pg0, convenio-sample2:pg1
- **expected_behavior:** Correct clustering should separate these into 2 clusters
- **baseline_ari:** 1.0

### Caso 5: multi_sample_same_template

- **description:** Three 2ViaBoleto samples should all cluster together (cluster A). Tests consistency.
- **pages_involved:** boleto-2via-sample1:pg0, boleto-2via-sample2:pg0, boleto-2via-sample3:pg0
- **expected_behavior:** All 3 pages in same cluster
- **baseline_ari:** 1.0

### Caso 6: similar_document_different_template

- **description:** Both 2ViaBoleto and boleto-condominio are boletos but from different templates. Must be in separate clusters.
- **pages_involved:**
  - template_A: ['boleto-2via-sample1', 'boleto-2via-sample2']
  - template_C: ['boleto-condominio-sample1', 'boleto-condominio-sample2']
- **expected_behavior:** Cluster A and Cluster C must be disjoint
- **risk:** Baseline may over-merge due to generic 'boleto' geometry similarity
- **baseline_ari:** 1.0

## 7. Análise de Robustez (AC10)

**Nota sobre N=3 runs:** Todas as combinações testadas são **determinísticas** dado seed fixo.
LLM validation (passo 1.13) foi pulado conforme instrução do spike (economia de budget).
Resultado: std_dev=0.000 em todas as métricas entre os 3 runs.
O N=3 confirma **reprodutibilidade** em vez de medir variância.

## 8. Dependências e Infra (AC11)

| Componente | Modelo | Tamanho | GPU | CPU viável |
|---|---|---|---|---|
| F0 Baseline | BlockInfo manual | ~0MB | N/A | Sim |
| F1 LayoutLMv3 | microsoft/layoutlmv3-base | ~500MB | Recomendada | ok |
| F2 CLIP | openai/clip-vit-base-patch32 | ~600MB | Recomendada | ok |
| F3 DINOv2 | facebook/dinov2-base | ~350MB | Recomendada | ok |
| F4 Nougat/Donut | — | — | — | Skipped (complexidade) |
| V3 SSIM | scikit-image | ~50MB | N/A | Sim |
| V4 LPIPS | lpips + torch | ~500MB | Recomendada | Skipped (budget setup) |

### Instalação
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu  # CPU only
pip install transformers imagehash scikit-image
```

## 9. Orçamento (AC12)

**Budget total gasto:** $0.00 / $5.00

Embeddings são locais (gratuitos). LLM validation pulado.
Zero chamadas de API externas realizadas.

## 10. Recomendações por Componente

### Feature Extraction

- **Baseline (F0) ARI:** 1.000
- **Melhor alternativa:** F0 (ARI=1.000)
- **Delta:** +0.000

**Critério de troca:** delta ARI ≥ +0.10 e sem degradação em homogeneity.

**RECOMENDAÇÃO:** Manter F0 (baseline geometry blocks) — alternativas não superam threshold de +0.10 ARI.

### Similarity + Clustering

- **S0 (baseline graph/geometry):** ARI=1.000
- **S2 (HDBSCAN):** Não requer threshold fixo — mais robusto a distribuições desconhecidas.
- **S5 (Agglomerative):** Hierárquico, interpretável, bom para domínio vetorial.

**RECOMENDAÇÃO:** Avaliar HDBSCAN (S2) se dataset expandir — elimina threshold manual de 0.85.

### Visual Cross-check

- **V0 (pHash):** Simples, rápido, adequado para PDFs vetoriais gerados por motor.
- **V3 (SSIM):** Mais sensível a diferenças estruturais.
- **V1/V2 (CLIP/DINOv2):** Mais robusto semanticamente.

**RECOMENDAÇÃO:** Manter V0 para PDFs Planet Express (vetoriais, baixo noise). Considerar V3+V0 combinados se PDFs raster.

## 11. Projeção de Impacto

Com dataset de apenas 9 páginas, qualquer conclusão tem margem de erro alta.
Se ARI do baseline já é alto (≥0.9), o pipeline atual é adequado para o domínio.
Recomenda-se expandir o dataset para 30-50 páginas com PDFs Planet Express reais antes de decisão final.

---

*Relatório gerado automaticamente por `spike_clustering_reevaluation.py` — @dev (Dex) YOLO — 2026-04-13*