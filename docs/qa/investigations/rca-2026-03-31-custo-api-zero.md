# RCA — rca-2026-03-31-custo-api-zero

**Data:** 2026-03-31  
**Investigado por:** @qa (Quinn)  
**Sintoma:** Campo "CUSTO API" exibe `$0.00` na tela de conclusão da análise  
**Severidade:** Medium  
**Status:** Investigação concluída — fix pendente

---

## 1. Classificação

| Dimensão | Valor |
|---|---|
| Cynefin | Complicated |
| Severidade | Medium |
| Scope | Cross-module |
| Estratégia | Fases 0→1→2→3→5→6→7→8→9 |

---

## 2. Dedup Check

| RCA Anterior | Error Msg (+40) | File Overlap (+30) | Tag Overlap (+20) | AP Match (+10) | Score |
|---|---|---|---|---|---|
| rca-2026-03-31-stage5-document-trees-contract | não | não | não | não | 0% |
| rca-2026-03-29-analyzing-page | não | não | não | não | 0% |

**Resultado:** NEW — Problema inédito na knowledge base.

---

## 3. Sintoma Observado

Na tela `AnalyzingPage` → `CompletedSummary`, após análise completa com sucesso (5 stages, 2 layouts, 2 páginas, 20s total), o campo **CUSTO API** exibe `$0.00`.

O usuário reportou "parece ser um problema maior" — intuição correta. O `$0.00` é sintoma de **degradação silenciosa de qualidade** (Vision AI não rodou).

---

## 4. Archaeology — Cadeia Causal

```
OPENROUTER_API_KEY ausente ou inválida
  ↓
backend/services/stages/stage3_structural_analysis.py:452
  get_client() → raises ValueError("OPENROUTER_API_KEY environment variable is not set")
  ↓
stage3:456  except (ValueError, ImportError): vision_available = False
            ← CAPTURADO SILENCIOSAMENTE — nenhum warning adicionado
  ↓
stage3:474  for cluster → if not vision_available:
                visual_analysis[page_key] = _fallback_visual_analysis(page_data)
                api_calls NUNCA incrementado
  ↓
stage3:554  context["_vision_api_calls"] = 0 + 0 = 0
  ↓
pipeline_orchestrator_v2.py:394
  api_cost = round(0 * 0.025, 4) = 0.0
  ↓
SSE event "pipeline_completed" summary: { api_cost: 0.0, ... }
  ↓
AnalyzingPage.vue:521  summaryData.value.apiCost = 0
AnalyzingPage.vue:392  apiCostEstimate: 0 ?? undefined = 0
  ↓
CompletedSummary.vue:20
  0 != null → `$${(0).toFixed(2)}` = "$0.00"
  ← INDISTINGUÍVEL de "Vision API chamada e custou zero"
```

**Evidência temporal:** Stage 3 executou em 6s. Cada chamada Vision API tem REQUEST_TIMEOUT=30s. Para 2 layouts, o mínimo seria ~60s se Vision AI estivesse ativa. **6s confirma fallback mode.**

---

## 5. Grafo Causal

**Root Cause Primary (E1 — Confirmed):**
- `OPENROUTER_API_KEY` não configurada → `get_client()` lança `ValueError` → capturado silenciosamente → `vision_available = False`

**Root Cause Contributing (E2 — Correlated):**
- `chat_with_vision` retorna apenas texto (`completion.choices[0].message.content`), descartando `completion.usage` → custo tracking é estimado ($0.025 fixo), não real. Mesmo quando Vision AI rodar, não há como saber o custo real.

**Design Gap (E2 — Correlated):**
- `CompletedSummary.vue:20` — `apiCostEstimate != null ? ... : '$0.00'` — zero (API chamada e gratuita) e null (API nunca chamada) exibem identicamente como `$0.00`

---

## 6. Barrier Analysis

| Camada | Status | Criticality | Contrafactual |
|---|---|---|---|
| Code Level | `absent` | **HIGH** | `context["warnings"].append(...)` quando `vision_available=False` → surfaceado no SSE |
| Test Level | `absent` | **HIGH** | Teste do path "OPENROUTER_API_KEY ausente" teria detectado em CI |
| Static Analysis | `absent` | LOW | Não detectável via lint |
| CI/CD | `absent` | LOW | Requer integration test para detectar |
| Monitoring | `partial` | MEDIUM | `logger.warning("Vision API call failed")` existe mas não propagado ao usuário |
| Process Level | `failed` | MEDIUM | QA gate não verificou observabilidade de serviço degradado |

**Swiss Cheese:** Code guard absent + Test absent + No SSE warning = usuário não sabe que Vision AI não rodou.

**Fix This First:** Code Level — warning propagado ao usuário quando fallback é ativado.

---

## 7. O Problema Maior

O `$0.00` é sintoma de **degradação silenciosa de qualidade de análise**:

1. **Vision AI não rodou** → análise estrutural a ~75% de qualidade em vez de ~95%
   - `_fallback_visual_analysis()` usa thresholds adaptativos estáticos (header=top 10%, footer=bottom 10%)
   - Vision AI fornece análise real da imagem com detecção de regiões, layout, consistência
2. **Usuário não sabe** → nenhum badge, warning, indicator na UI quando fallback é usado
3. **Sem rastreabilidade** → mesmo quando Vision AI rodar, custo é estimado (fixo), não real
4. **Ambiguidade na UI** → `$0.00` pode significar "gratuito" ou "não chamada" — indistinguíveis

---

## 8. Fixes Recomendados

### Fix 1 — Primário: Warning quando Vision AI não disponível (Immediate — HIGH)
**Arquivo:** `backend/services/stages/stage3_structural_analysis.py:456`

```python
# ANTES:
except (ValueError, ImportError):
    vision_available = False

# DEPOIS:
except (ValueError, ImportError) as e:
    vision_available = False
    warnings = context.setdefault("_pipeline_warnings", [])
    warnings.append(f"Vision AI desabilitado: {e}. Análise estrutural rodando em modo fallback (~75% qualidade).")
```

### Fix 2 — SSE Summary inclui vision_ai_used (Immediate — HIGH)
**Arquivo:** `backend/services/pipeline_orchestrator_v2.py:391`

```python
summary={
    "layouts_detected": len(real_clusters),
    "page_count": total_pages,
    "api_cost": round(context.get("_vision_api_calls", 0) * ESTIMATED_COST_PER_VISION_CALL, 4),
    "vision_ai_used": context.get("_vision_api_calls", 0) > 0,  # NEW
}
```

### Fix 3 — Frontend distingue $0.00 de "Vision AI desabilitado" (Immediate — MEDIUM)
**Arquivo:** `frontend/src/components/analyzing/CompletedSummary.vue:20`  
**Arquivo:** `frontend/src/pages/AnalyzingPage.vue` (receber `vision_ai_used`)

Quando `visionAiUsed = false AND apiCostEstimate = 0`: exibir "N/A" ou badge de aviso em vez de `$0.00`.

### Fix 4 — Custo real via completion.usage (Short-term — LOW)
**Arquivo:** `backend/services/openrouter_client.py:165`

Modificar `chat_with_vision` para retornar `(text, cost)` onde `cost` é calculado de `completion.usage.prompt_tokens` e `completion.usage.completion_tokens` com os rates reais.

---

## 9. Testes Recomendados

| Teste | O que valida |
|---|---|
| `test_stage3_vision_fallback_warning` | Quando `OPENROUTER_API_KEY` ausente → `_pipeline_warnings` contém entry sobre Vision AI |
| `test_orchestrator_summary_vision_ai_used_false` | Quando `_vision_api_calls=0` → summary inclui `vision_ai_used: false` |
| `test_orchestrator_summary_vision_ai_used_true` | Quando `_vision_api_calls>0` → summary inclui `vision_ai_used: true` e `api_cost > 0` |
| `test_completed_summary_zero_cost_no_vision` | Frontend: quando `visionAiUsed=false` → exibe "N/A" não "$0.00" |

---

## 10. Anti-Pattern Registrado

**AP-005: Silent Service Degradation** — novo anti-pattern identificado.  
Ver `docs/qa/known-anti-patterns.md`.

---

## 11. Barrier Criticality Ranking

"Fix This First": **Code Level** — `context["_pipeline_warnings"]` entry quando `vision_available=False`

Isolada, esta barreira teria surfaceado o problema ao usuário via SSE warnings já existentes.

---

## 12. Achados Colaterais

| ID | Tipo | Severidade | Descrição | Localização | Ação |
|---|---|---|---|---|---|
| F-1 | Design Gap | LOW | `chat_with_vision` descarta `completion.usage` — custo nunca é real | `openrouter_client.py:165` | Story de melhoria |
| F-2 | UX Gap | MEDIUM | `$0.00` e null exibem identicamente em CompletedSummary | `CompletedSummary.vue:20` | Fix junto ao Fix 3 |
| F-3 | Config Gap | LOW | `.env.example` documenta `OPENROUTER_API_KEY` mas sem mensagem de startup indicando se Vision AI está ativa | `backend/main.py` | Story de observabilidade |

---

## 13. Escalation Assessment

| Critério | Atingido? |
|---|---|
| Scope amplo (3+ módulos) | SIM — stage3, orchestrator, frontend (3 módulos) |
| Design pattern incorreto | NÃO |
| Interface change | SIM — `chat_with_vision` signature e SSE summary contract |
| Barrier systemic (4+) | NÃO |

**Recomendação:** Escalar Fix 2 e Fix 4 para @architect validar contrato SSE antes de implementar (impacta interface backend→frontend).

---

## 14. Recomendações Finais

1. **Imediato:** Fixes 1, 2 e 3 — observabilidade de degradação de qualidade
2. **Curto prazo:** Fix 4 — custo real em vez de estimado
3. **Longo prazo:** Startup check — logar no boot se Vision AI está habilitada/configurada (F-3)
