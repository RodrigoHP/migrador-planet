# RCA — AnalyzingPage: Logo, Stage 5 Crash, Métricas Incompletas

**Data:** 2026-03-29
**PR:** RodrigoHP/migrador-planet#42
**Branch:** fix/rca-analyzing-page-logo-stage5-metrics
**Investigador:** @aios-master (Orion)

---

## Problema Original

3 bugs reportados na tela de progresso (AnalyzingPage) via screenshot:

1. Logo/breadcrumb diferente do wireframe
2. Pipeline parou com falha no Stage 5 — erro: `'list' object has no attribute 'get'`
3. Estágios concluídos não exibem todas as métricas do wireframe

---

## Bug 1 — Logo e Breadcrumb

### Root Cause (5 Whys)
1. Por que o topbar mostra "Migrador PlanetexpressMigrador"?
2. Porque `AppHeader.vue` renderiza logo "Migrador" + sub "Planetexpress", e o slot stepper do `AnalyzingPage.vue` começa o breadcrumb com "Migrador" novamente
3. Porque o breadcrumb foi implementado com 3 itens: "Migrador > Job# > Analisando" sem considerar que o logo já exibe "Migrador"
4. Porque o wireframe usa "Migrador Planet" como logo e o breadcrumb começa em "Job #"
5. Porque não houve validação visual contra o wireframe v2 durante implementação

### Fix Aplicado
- `AppHeader.vue:5` — `Planetexpress` → `Planet`
- `AnalyzingPage.vue:6-8` — Remove crumb "Migrador" (primeiro item)

---

## Bug 2 — Stage 5 Crash

### Root Cause (5 Whys)
1. Por que stage 5 crasha com `'list' object has no attribute 'get'`?
2. Porque `layout_types[0].get("id")` é chamado sem verificar o tipo
3. Porque `layout_types[0]` pode ser uma lista em vez de dict dependendo da entrada
4. Porque não há guard `isinstance` neste ponto específico
5. Porque o padrão de guard (já aplicado para `document_trees` no mesmo arquivo, linhas 1353-1360) não foi replicado para `first_layout_id`

### Anti-Pattern: AP-001
Mesmo padrão de RCA 15.18/15.19/15.20. Ponto adicional encontrado.

### Fix Aplicado
```python
# Antes (stage5:1168)
first_layout_id = layout_types[0].get("id") if layout_types else None

# Depois
first_layout = layout_types[0] if layout_types else None
first_layout_id = first_layout.get("id") if isinstance(first_layout, dict) else None
```

---

## Bug 3 — Métricas Incompletas nos Estágios Concluídos

### Root Cause (5 Whys)
1. Por que os estágios concluídos não mostram todas as métricas do wireframe?
2. Porque o SSE summary de cada stage emite apenas subset das métricas disponíveis
3. Porque stage 1 emitia apenas `layouts_detected` e `pages_processed`
4. Porque stage 2 emitia apenas `pages_processed`, `blocks_extracted` e `warnings`
5. Porque os dados (confidence, corrections, images, tables, fonts) eram computados durante o processamento mas nunca incluídos no payload de completion

### Fix Aplicado

**Stage 1** (`stage1_layout_clustering.py:1382-1399`):
```python
summary={
    "layouts_detected": len(real_clusters),
    "pages_processed": len(all_pages),
    "confidence": avg_confidence_pct,       # NOVO: média das confidências dos clusters
    "corrections": len(corrections) if isinstance(corrections, (list, tuple)) else 0,  # NOVO
}
```

**Stage 2** (`stage2_deep_extraction.py:1254-1272`):
```python
summary={
    "pages_processed": processed,
    "blocks_extracted": total_blocks,
    "warnings": len(all_warnings),
    "images_extracted": total_images,   # NOVO
    "tables_detected": total_tables,    # NOVO
    "fonts_identified": total_fonts,    # NOVO
}
```

**Frontend** (`analyzingPageConstantsV2.ts`):
```typescript
confidence: 'Confiança (%)',        // NOVO label
corrections: 'Correções automáticas', // NOVO label
```

---

## Achados Colaterais

| ID | Tipo | Severidade | Local | Ação |
|----|------|------------|-------|------|
| AC-01 | Gap de teste | HIGH | `frontend/src/pages/AnalyzingPage.spec.ts` | Spec importa `./analyzingPageConstants` (arquivo renomeado para V2) — causa falha de transform no Vitest. Criar story para corrigir. |

---

## Recomendações

1. **AP-002 mitigação:** Ao renomear módulos, sempre fazer grep pelos imports do nome antigo e atualizar os specs
2. **AP-001 auditoria:** Rodar `*audit-patterns` para verificar outros pontos `[0].get()` sem guard no backend
3. **Stage 3-4 métricas:** Verificar se stages 3 e 4 também têm lacunas no SSE summary (fora do escopo deste RCA, mas recomendado)

---

## Resultado

- ✅ 3 root causes corrigidos na origem
- ✅ 1403 testes passando (1 falha pré-existente AP-002, não introduzida)
- ✅ PR #42 criado
- ✅ AP-001 atualizado, AP-002 registrado
