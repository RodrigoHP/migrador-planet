# RCA — `'list' object has no attribute 'get'` — Stage 5 Geração do Template

**Data:** 2026-03-31
**ID:** rca-2026-03-31-stage5-document-trees-contract
**Reportado por:** Usuário (screenshot da UI)
**Investigado por:** Quinn (@qa)

---

## 1. Classificação (Fase 0)

| Dimensão | Valor |
|----------|-------|
| Cynefin | **Complicated** |
| Severidade | **High** — funcionalidade principal quebrada |
| Scope | **Cross-module** — Stage 3, 4 e 5 |
| Estratégia | 0 → 1 → 3 → 7 → 8 → 9 |

---

## 2. Sintoma Observado

Pipeline falha no Estágio 5 (Geração do Template) com:

```
'list' object has no attribute 'get'
```

Stages 1–4 concluem com sucesso. Stage 5 tenta 1 vez e falha.

---

## 3. Archaeology (Fase 1)

### Top Suspects

| Rank | Arquivo | Relevância | Motivo |
|------|---------|-----------|--------|
| 1 | `stage5_template_generation.py` | Alta | Crash confirmado neste stage |
| 2 | `stage3_structural_analysis.py` | Alta | Produtor de `document_trees` |
| 3 | `stage4_field_mapping.py` | Média | Consumidor intermediário com conversão idêntica |

### Timeline

- `d3b0cbf` (2026-03-22) — Epic 13: pipeline redesign 28→5 stages. Stage 3 passa a gravar `document_trees` como `List[Dict]`. Stages 4 e 5 recebem conversão ad-hoc local.
- `2623d8b` — fix anterior tentou resolver Stage 5 com `isinstance` guards em pontos de travessia, mas não atacou o contrato de dados.

---

## 4. Grafo Causal (Fase 3)

```
CRASH: 'list' object has no attribute 'get'
  em _step_5_6_pipeline_result() linha 1163
        │
        ▼ [E1_confirmed]
document_trees lido de context["document_trees"] → é lista
        │
        ├── Stage 3 grava List[Dict] em context["document_trees"]   [E1]
        │
        ├── Stage 4 converte localmente mas NÃO escreve de volta     [E1]
        │
        └── Stage 5 run_stage5() converte localmente mas não persiste
            → _step_5_6_pipeline_result() lê context direto → CRASH  [E1]
```

**Root cause primary:** Stage 3 publica `document_trees` no context compartilhado como `List[Dict]`, mas 100% dos consumidores (Stage 4, Stage 5 e suas sub-funções) precisam de `Dict[str, Dict]`. Nenhum estágio é dono da normalização.

**Contributing factors:**
- Conversão List→Dict duplicada em Stage 4 e Stage 5 (code smell documentado com comentário em Stage 4: "Stage 3 outputs document_trees as a list")
- Sub-funções leem de `context` diretamente sem garantia de formato normalizado
- Fix anterior (`2623d8b`) adicionou guards em pontos de consumo sem atacar o contrato na fonte

---

## 5. Challenge (Fase 4)

**Hipótese refutada:** "O bug é um isinstance guard faltando em `_step_5_6_pipeline_result`."
- Contra-evidência: Stage 4 tem o mesmo padrão e não crasha porque suas sub-funções recebem o dict via parâmetro, não via context.
- Counterfactual: adicionar guard em `_step_5_6_pipeline_result` seria band-aid — qualquer nova sub-função que lesse context diretamente reproduziria o bug.
- Verdict: **REFUTED** — guard é proteção adicional, não o fix principal.

**Hipótese confirmada:** "O contrato de dados entre Stage 3 e consumidores é inconsistente."
- Evidência E1: comentário explícito em Stage 4 admite a inconsistência; código de conversão duplicado em dois stages.
- Verdict: **CONFIRMED** (confidence: 0.97)

---

## 6. Barrier Analysis (Fase 5)

| Camada | Status | Detalhe |
|--------|--------|---------|
| Code Level | **Falhou** | Conversão feita localmente, sem writeback ao context compartilhado |
| Test Level | **Ausente** | Nenhum teste cobre fluxo ponta-a-ponta com `document_trees` como lista vinda de Stage 3 |
| Static Analysis | **Ausente** | Tipo `Dict[str, Any]` no context não captura o formato real |
| CI/CD | **Ausente** | Sem teste de integração entre stages |
| Processo | **Falhou** | Fix anterior (`2623d8b`) não investigou causa raiz |

**Swiss Cheese:** Code sem contrato formal + sem teste de integração = bug atinge produção.

---

## 7. Evidence Summary (Fase 6)

| Level | Achado | Source |
|-------|--------|--------|
| E1 | Stage 3 retorna `List[Dict]` de `_run_3_4()` | `code_analysis`: stage3 linha 1062 |
| E1 | Stage 3 grava lista direto no context | `code_analysis`: stage3 linha 1555 |
| E1 | Stage 4 tem conversão local sem writeback | `code_analysis`: stage4 linhas 1115-1122 |
| E1 | `_step_5_6_pipeline_result` lê context sem conversão e crasha | `code_analysis`: stage5 linha 1153+1163 |
| E1 | Nenhum consumidor fora de stages 3-5 usa `document_trees` | `git_analysis`: grep no codebase |

---

## 8. Fix Aplicado (Fase 7)

**Estratégia:** Normalização única na fonte (Stage 3), remoção de código duplicado nos consumidores.

### `stage3_structural_analysis.py`
```python
# ANTES
document_trees = _run_3_4(...)
context["document_trees"] = document_trees  # List[Dict]

# DEPOIS
_raw_trees = _run_3_4(...)
document_trees: Dict[str, Dict[str, Any]] = {
    entry.get("cluster_id", ""): entry.get("tree", {})
    for entry in _raw_trees
}
context["document_trees"] = document_trees  # Dict[str, Dict] — normalizado
```

### `stage4_field_mapping.py`
```python
# REMOVIDO: bloco isinstance + loop de conversão (8 linhas)
# SUBSTITUÍDO POR:
document_trees: Dict[str, Dict[str, Any]] = context.get("document_trees", {})
```

### `stage5_template_generation.py`
```python
# REMOVIDO: bloco isinstance + loop de conversão (8 linhas)
# SUBSTITUÍDO POR:
document_trees: Dict[str, Dict[str, Any]] = context.get("document_trees", {})
```

---

## 9. Testes Criados

Nenhum teste automatizado foi criado nesta sessão.

**Justificativa:** O bug é de contrato de dados entre stages — o teste adequado é de integração (Stage 3 → Stage 4 → Stage 5), não unitário. Recomendação: criar `test_pipeline_stage3_to_stage5_document_trees.py` validando que `context["document_trees"]` é `Dict` após Stage 3 e permanece `Dict` ao longo do pipeline.

**Backlog:** F-1 abaixo.

---

## 10. Achados Colaterais

| ID | Tipo | Severidade | Descrição | Localização | Ação Sugerida |
|----|------|-----------|-----------|-------------|---------------|
| F-1 | Debt | HIGH | Ausência de teste de integração Stage 3→5 para formato de `document_trees` | `backend/tests/` | Criar `test_pipeline_stage_contracts.py` |
| F-2 | Debt | MEDIUM | Fix anterior (`2623d8b`) deixou `isinstance` guards em pontos de consumo que agora são dead code | `stage5_template_generation.py` linhas diversas | Audit e remoção em story dedicada |

---

## 11. Anti-Pattern Registrado

**AP-003** — veja `docs/qa/known-anti-patterns.md`

---

## 12. Recomendações

**Immediate:**
- ✅ Fix aplicado — Stage 3 normaliza para dict na fonte

**Short-term:**
- Criar teste de integração cobrindo contrato de dados entre stages (F-1)
- Audit dos guards `isinstance` remanescentes em stage5 para remoção (F-2)

**Long-term:**
- Definir contratos formais de output para cada stage (TypedDict ou dataclass)
- Adicionar validação de schema do context no orchestrator após cada stage
