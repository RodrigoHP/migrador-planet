# RCA — rca-2026-03-31-spacy-xsd-warnings

**Data:** 2026-03-31
**Investigador:** @qa (Quinn)
**Domain:** Clear — Fast-Track (fases 2-6 puladas)
**Severidade:** Low
**Status:** Resolvido

---

## 1. Classificação (Fase 0)

- **Domínio Cynefin:** Clear (causa-efeito óbvio em ambos os erros)
- **Severidade:** Low (pipeline completa com 200 OK — nenhum erro fatal)
- **Scope:** Multi-file
- **Fast-Track aplicado:** Fases 2-6 puladas

### Dedup Check

| RCA Anterior | Error Msg (+40) | File Overlap (+30) | Tag Overlap (+20) | AP Match (+10) | Score |
|---|---|---|---|---|---|
| rca-2026-03-29-analyzing-page | Não | stage3 sim (+30) | Não (+0) | Não | 30% |
| rca-2026-03-31-stage5-contract | Não | stage3 sim (+30) | Não (+0) | Não | 30% |
| rca-2026-03-31-custo-api-zero | Não | stage3 sim (+30) | Não (+0) | Não | 30% |

**Resultado: NEW** — Ambos os problemas são novos.

---

## 2. Archaeology (Fase 1)

**Timeline observada nos logs:**
- `02:20:53` — `spaCy model not available — NER layer disabled` × 7 (simultâneos)
- `02:20:56` — `Stage 4.1: no xsd_path — field_tree will be None` × 1
- `02:21:16` — `GET /api/analyze/{job_id}/result HTTP/1.1 200 OK`

**Conclusão imediata:** O pipeline completou com sucesso. Ambas as mensagens são warnings, não erros fatais.

---

## 3. Root Causes

### Problema A — spaCy warning repetido ×7

**Arquivo:** `backend/services/stages/stage3_structural_analysis.py:37-58`

**Causa:** Bug no padrão de sentinel. A variável `_nlp = None` é usada para dois estados distintos:
- "não tentei carregar ainda" → `None`
- "tentei e falhei" → também `None` (bug!)

O guard `if _nlp is not None: return _nlp` só salta o load quando bem-sucedido. Após falha, `_nlp` permanece `None`, e cada chamada subsequente a `_get_nlp()` repete a tentativa completa (import + load × 2 + warning + return None).

Com 7 blocos de texto sendo classificados paralelamente, `_smart_classify()` chama `_get_nlp()` 7 vezes → 7 warnings.

**Fix aplicado:** Adicionar sentinela `False` para "tentou e falhou":
```python
_nlp = None  # None = not yet attempted; False = attempted and unavailable

def _get_nlp():
    global _nlp
    if _nlp is False:
        return None  # Already attempted and failed — skip retry and warning
    if _nlp is not None:
        return _nlp
    ...
    except Exception:
        logger.warning("spaCy model not available — NER layer disabled")
        _nlp = False  # Sentinel: mark as failed so we don't retry or re-log
        return None
```

### Problema B — Stage 4.1: no xsd_path

**Arquivos:** `backend/routers/analyze.py:265`, `backend/services/stages/stage4_field_mapping.py:165-168`

**Causa:** **Comportamento by design.** XSD é opcional no pipeline.

```python
# analyze.py:265
xsd_path = str(job_dir / "schema.xsd") if (job_dir / "schema.xsd").exists() else ""
```

Quando o job não tem XSD, `xsd_path = ""`. String vazia é falsy → Stage 4 detecta ausência, loga warning informacional, e continua sem field_tree. Stage 5 já declara `field_tree: Optional[Dict[str, Any]]` e lida com `None` corretamente:
- `_is_array_field` (linha 299-303): `if not field_tree: return False`
- `flat_paths` (linha 668): `field_tree.get("flat_paths", []) if field_tree else []`

**Fix:** Nenhum fix de código necessário. O warning é correto e informacional.

---

## 4. Evidence Summary

| # | Claim | Level | Confidence | Sources |
|---|---|---|---|---|
| 1 | Sentinel bug em `_get_nlp()` causa retry + warning por bloco classificado | E1_confirmed | 0.97 | code_analysis (stage3:37-58), log_analysis (7× 02:20:53) |
| 2 | xsd_path ausente é comportamento by design — pipeline completa 200 OK | E1_confirmed | 0.95 | code_analysis (analyze.py:265, stage4:165-168, stage5:299-303), log_analysis (02:21:16) |

---

## 5. Fix Aplicado

**Arquivo modificado:** `backend/services/stages/stage3_structural_analysis.py`

**Mudança:** Adição de sentinela `False` + guard `if _nlp is False: return None` no topo de `_get_nlp()`.

**Resultado esperado:** Warning `spaCy model not available — NER layer disabled` aparece **exatamente uma vez** por processo, na primeira chamada que detecta ausência do modelo.

---

## 6. Testes Criados

Nenhum teste automatizado novo necessário para o fix do sentinel:
- O comportamento de "warning aparece apenas uma vez" é garantido pelo próprio mecanismo de sentinela
- Testes existentes de stage3 mocam `_get_nlp()` → não afetados pela mudança
- Lógica da mudança é trivial (1 nova guarda + 1 atribuição de sentinela)

Para Problema B: Sem mudança de código → sem necessidade de novo teste.

---

## 7. Achados Colaterais (Backlog)

| ID | Tipo | Severidade | Descrição | Localização | Ação Sugerida |
|---|---|---|---|---|---|
| F-1 | improvement | Low | Warning spaCy deveria ser `logger.info` — é comportamento esperado em dev/cloud sem modelo | stage3:57 | Avaliar downgrade de WARNING para INFO para reduzir ruído em ambientes sem spaCy |

---

## 8. Anti-Pattern Registrado

**AP-006:** Lazy Load sem Sentinel de Falha — adicionado a `docs/qa/known-anti-patterns.md`

---

## 9. Tags Utilizadas

- `logic_error` — error_type ✓
- `guard_missing` — root_cause_category ✓
- `backend_stage` — affected_layer ✓
- `guard_added` — fix_type ✓
- `custom:lazy_load_sentinel` — padrão específico sem equivalente na taxonomia

---

## 10. Barrier Analysis (resumido — Clear domain)

| Camada | Status | Criticality | Contrafactual |
|---|---|---|---|
| Code Level | absent (sentinel) | HIGH | Guard `_nlp is False` teria evitado os 7 warnings |
| Test Level | absent | LOW | Difícil testar (depende de spaCy ausente) |

**Escalation Assessment:** Nenhum critério atingido — escalonamento não necessário.
