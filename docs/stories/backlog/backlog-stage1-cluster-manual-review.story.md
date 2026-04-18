# Backlog — Stage 1: Revisão Humana de Clusters (Human-in-the-Loop)

**Tipo:** Feature Futura  
**Prioridade:** P2 — útil quando ensemble voting errar em casos edge  
**Esforço estimado:** 3–4 dias (backend + frontend + infra)  
**Dependências:** Stage 1 ensemble voting implementado (48.10/48.11 ✅)

---

## Problema

O ensemble voting (4 sinais) é robusto para os 6 tipos testados, mas pode falhar em casos edge:
- Templates visualmente muito similares com conteúdos diferentes (ex.: duas versões do mesmo boleto de fornecedores distintos)
- PDFs com baixa qualidade de renderização (fontes não embarcadas, imagens dominando o layout)
- Templates novos ainda sem calibração suficiente

Quando `confidence.level == "low"` (ensemble score < threshold), o pipeline hoje continua silenciosamente. A feature futura pausa e exibe uma tela de revisão para o operador confirmar, corrigir ou abortar.

## UX Desenhada

**Wireframe:** `docs/frontend/wireframes/wireframe-cluster-checkpoint.html`

A tela é um **modal overlay** que aparece sobre a tela de progresso do pipeline, que fica visível mas pausada/desfocada ao fundo.

### Componentes do modal

**Header:**
- Ícone de alerta + título "Verificação de Clustering"
- Subtítulo: "O sistema identificou N tipos de página. Confira antes de continuar."
- Timer regressivo: "Auto-continua em 4:32" — se o operador não interagir, pipeline prossegue com o resultado automático

**Banner de análise AI (opcional):**
- Sugestão do modelo (ex.: Gemini Flash): "Tipo A e Tipo C parecem ser o mesmo tipo..."
- Confiança da sugestão: ex. 65%
- Sugestão de ação: "Merge Tipo A + Tipo C"

**Grid de clusters (3 colunas):**
Cada card exibe:
- Thumbnail representativo do cluster (fake PDF visual no wireframe, real no prod)
- Badge de confiança: `high` (verde), `medium` (amarelo), `low` (vermelho)
- Nome do tipo: "Tipo A — Boleto", "Tipo B — Extrato"
- Metadados: `N páginas`, confiança %
- (Opcional) Banner "Auto-correção aplicada: split" quando o sistema já corrigiu automaticamente

Cards com `low-confidence` têm borda amarela. Cards selecionados têm borda azul (para operações de merge).

**Strip de páginas de amostra (clusters com baixa confiança):**
- Thumbnails miniaturas das páginas do cluster problemático
- Scroll horizontal com "+N" ao final
- Clique abre painel lateral (detail panel)

**Painel lateral de detalhe (ao clicar numa página):**
- Preview ampliado da página
- Metadados: cluster atual, confiança, similaridade com representante, pHash distance, blocos detectados, grid
- Ações: "Mover para outro tipo" | "Isolar (novo tipo)"

**Barra de ações de correção:**
- **Merge A + C** — une dois clusters selecionados em um único template
- **Split Tipo B** — divide um cluster com baixa confiança em dois
- **Renomear** — altera o label do tipo (ex.: "Tipo B" → "Extrato Mensal")
- **Mover Página** — arrastar uma página para outro cluster

**Footer:**
- Botão "Pular (continuar sem confirmar)" — pipeline usa resultado automático
- Timer auto-continua
- Botão "Confirmar e Continuar" (verde) — pipeline usa o resultado (possivelmente corrigido) e avança

---

## Arquitetura Backend

### Infra de checkpoint (Story 1.1 do design spec)

**Migration necessária:** tabela `pipeline_checkpoints`
```sql
CREATE TABLE pipeline_checkpoints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id UUID REFERENCES pipeline_jobs(id),
  stage TEXT NOT NULL,           -- 'stage1_clustering'
  checkpoint_type TEXT NOT NULL, -- 'low_confidence_review'
  status TEXT DEFAULT 'pending', -- pending | resolved | timeout | aborted
  payload JSONB,                 -- clusters, signals_summary
  decision JSONB,                -- action tomada pelo operador
  created_at TIMESTAMPTZ DEFAULT now(),
  resolved_at TIMESTAMPTZ,
  timeout_at TIMESTAMPTZ
);
```

**Novo serviço:** `backend/services/pipeline_checkpoints.py`
- CRUD de checkpoints
- `asyncio.Event` por checkpoint (pipeline aguarda)
- Cleanup semanal de checkpoints `resolved`/`timeout`

**Novo endpoint:** `POST /jobs/{id}/checkpoint/{cid}/decision`
```json
{
  "action": "confirm" | "abort" | "modify",
  "modifications": {
    "merges": [["cluster_0", "cluster_2"]],
    "splits": [],
    "renames": {"cluster_1": "Extrato Mensal"},
    "page_moves": []
  }
}
```

**Endpoint thumbnail:** `GET /jobs/{id}/pages/{pdf_id}/{page_index}/thumbnail?size=256`
- Gera imagem JPEG da página via PyMuPDF
- Cache em Supabase Storage: `thumbnails/{job_id}/{pdf_id}_{page_index}_{size}.jpg`

**Wire no Stage 1:** em `stage1_layout_clustering.py`, após `_cluster_graph`:
```python
low_conf_clusters = [c for c in clusters if c.confidence.level == "low"]
if low_conf_clusters and config.human_review_enabled:
    checkpoint = await create_checkpoint(job_id, clusters)
    await emit_sse(job_id, "stage1_review_required", checkpoint)
    decision = await wait_for_decision(checkpoint.id, timeout=300)
    clusters = apply_decision(clusters, decision)
```

### Modelo de confiança

Já produzido pelo ensemble voting (`_ensemble_similarity`):
- `score >= 0.90` → `level = "high"` (3–4 sinais concordam)
- `0.75 <= score < 0.90` → `level = "medium"` (2 sinais)
- `score < 0.75` → `level = "low"` → dispara checkpoint

---

## Arquitetura Frontend

**Novo componente:** `frontend/src/organisms/analyzing/ClusterReviewModal.vue`

```
ClusterReviewModal.vue
├── ClusterCard.vue          — card de cluster com thumbnail + badge + seleção
├── PageStripCarousel.vue    — strip de miniaturas com scroll horizontal
├── PageDetailPanel.vue      — painel lateral com detalhe da página
├── ClusterActionBar.vue     — botões merge/split/rename/move
└── CountdownTimer.vue       — timer regressivo auto-continua
```

**Store:** `frontend/src/stores/clusterReview.ts`
- `pendingCheckpoint: Checkpoint | null`
- `selectedClusters: string[]` — para operações de merge
- `modifications: ClusterModification[]`
- `submitDecision(action, modifications): Promise<void>`

**SSE listener** (já existe infra de SSE no projeto):
```typescript
// Em analyzingStore.ts ou pipeline SSE handler
case 'stage1_review_required':
  clusterReviewStore.open(event.data)
  break
```

---

## Configuração

Feature deve ser **opt-in** via config do job ou env:
```python
class ClusteringConfig:
    human_review_enabled: bool = True   # False em testes automatizados
    human_review_timeout_s: int = 300   # 5 min antes de auto-continuar
    human_review_threshold: float = 0.75  # score abaixo disso = low confidence
```

---

## O que já existe (reaproveitar)

| Componente | Status | Localização |
|-----------|--------|-------------|
| `CheckpointCard.vue` | ✅ Existe | `frontend/src/organisms/analyzing/CheckpointCard.vue` |
| SSE pipeline events | ✅ Existe | infra de SSE do pipeline |
| `pipeline_checkpoints` table | ❌ Não existe | precisa de migration |
| Endpoint thumbnail | ❌ Não existe | novo endpoint |
| `ClusterReviewModal.vue` | ❌ Não existe | novo componente |
| `clusterReview.ts` store | ❌ Não existe | novo store |

O `CheckpointCard.vue` existente é genérico (service_failure, etc.). A nova tela é específica para revisão de clustering — componente separado que pode reutilizar estilos do CheckpointCard.

---

## Artefatos de Design

- **Wireframe interativo:** `docs/frontend/wireframes/wireframe-cluster-checkpoint.html`
  - Modal completo com grid de clusters, strip de páginas, barra de ações, footer
  - Detail panel lateral ao clicar em página
  - Background desfocado mostrando pipeline pausado
  - Timer regressivo
  - Badges de confiança: high (verde) / medium (amarelo) / low (vermelho)
  - Ações: Merge, Split, Renomear, Mover Página

- **Design spec técnico:** `docs/reports/epic-48/stage1-clustering-analysis.md`
  - Stories 1.1 (checkpoint infra), 1.2 (remove LLM factor), 1.3 (frontend), 1.4 (observability)
  - §6 "Pegadinhas" — lista de armadilhas de implementação já identificadas

---

## Quando implementar

Implementar quando um destes gatilhos ocorrer:
1. O ensemble voting produzir erros visíveis em produção com templates reais (fora dos 6 tipos calibrados)
2. O usuário reportar que o Stage 1 agrupou incorretamente tipos que deviam ser distintos
3. Escala de templates aumentar significativamente (>200 tipos distintos)

**Não implementar antes de:** Stage 1 ensemble voting rodar em produção com pelo menos 2–3 meses de dados reais.

---

## Referências

| Artefato | Localização |
|---------|-------------|
| Wireframe | `docs/frontend/wireframes/wireframe-cluster-checkpoint.html` |
| Design spec completo | `docs/reports/epic-48/stage1-clustering-analysis.md` §9–§11 |
| Ensemble voting (implementado) | `backend/services/stages/stage1_clustering/signals.py` |
| CheckpointCard existente | `frontend/src/organisms/analyzing/CheckpointCard.vue` |
| Stories design (não formalizadas) | stage1-clustering-analysis.md Stories 1.1, 1.2, 1.3, 1.4 |
