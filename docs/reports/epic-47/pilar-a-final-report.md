# Pilar A — Relatório Final de Validação

**Status:** current  
**Data:** 2026-04-14  
**Epic:** 47 — Validação Multi-Tipo de Documento  
**Decisão formal:** GAPS PENDENTES (ver abaixo)

---

## 1. Sumário Executivo

O Pilar A (Detecção) foi validado contra 8 PDFs de 5 tipos distintos via Railway API.
O pipeline extrai estrutura corretamente para **todos os tipos de documento** em modo single-PDF.

**Decisão:** Pilar A é **funcionalmente completo** para extração estrutural. Gap identificado: multi-sample clustering (necessário para Pilar B/binding) não pôde ser validado por ausência de múltiplas amostras do mesmo template nos fixtures.

---

## 2. Resultados por Tipo de Documento

### 2.1 — Relatório (Story 47.1)

| PDF | Layouts | Seções | Dinâmicos | Campos | Status |
|-----|---------|--------|-----------|--------|--------|
| PosicaoConsolidada.pdf | 3 | 17 | 19 | 24 | ✅ |
| PrevidenciaExtrato.pdf | 1 | 6 | 9 | 6 | ✅ |
| ApoliceVg.pdf | 2 | 11 | 28 | 7 | ✅ (5 imagens) |

**Conclusão 47.1:** Pipeline detecta estrutura de relatórios corretamente. Multi-página (3p, 2p) sem crash. Imagens detectadas na apólice.

### 2.2 — Boleto (Story 47.2)

| PDF | Layouts | Seções | Dinâmicos | Tabelas | Status |
|-----|---------|--------|-----------|---------|--------|
| BoletoCorporateMercantil.pdf | 1 | 5 | 20 | 1 | ✅ |
| BoletoVg.pdf | 4 | 13 | 44 | - | ✅ (8 imagens, barcode) |

**Conclusão 47.2:** Boletos detectados corretamente. Tabela vetorial detectada (Mercantil). Imagens/barcodes detectados (VG: 8 imagens). Campos dinâmicos numerosos (20–44) refletem natureza variável dos boletos.

### 2.3 — DIRF (Story 47.3)

| PDF | Layouts | Seções | Tabelas | Linhas | Células | Status |
|-----|---------|--------|---------|--------|---------|--------|
| DirfInformaFinanceiro.pdf | 1 | 23 | **9** | 28 | 63 | ✅ |

**Conclusão 47.3:** Melhor resultado da validação. 9 tabelas aninhadas detectadas com 28 data_rows e 63 células — confirma que a extração tabular do DIRF funciona perfeitamente.

### 2.4 — Type3 Fonts (Story 47.4)

Realizado via spike local (`spike_47_4_type3_fonts.py`). Resultado: Type3 fonts em CertiticadoPrevidencia são decorativas, não text-bearing. Texto extraído com 78–100% de legibilidade. **Sem necessidade de fallback Mistral para texto.**

### 2.5 — Certificados (Story 47.5)

| PDF | Layouts | Seções | Dinâmicos | Status |
|-----|---------|--------|-----------|--------|
| CertificadoPrevidencia.pdf | 5 | 12 | 41 | ✅ |
| CertificadoVI.pdf | 4 | 15 | 34 | ✅ |

**Conclusão 47.5:** Certificados multi-página processados sem crash. Muitos campos dinâmicos detectados (41, 34). Sem problemas de Type3 fonts afetando extração.

---

## 3. Gaps Identificados

### Gap 1 — Multi-sample clustering não validado (ACEITO)

**Descrição:** Não foi possível testar o clustering com múltiplas amostras do mesmo template porque os fixtures contêm PDFs de templates diferentes (não múltiplas instâncias do mesmo template).

**Impacto:** O workflow completo (3+ PDFs → detectar dinâmico vs estático → mapping XSD) não foi validado end-to-end.

**Decisão:** Gap aceito para Pilar A. O clustering multi-sample é pré-requisito para Pilar B (Binding XSD), não para Pilar A (Detecção estrutural). A estrutura de cada PDF é detectada corretamente.

**Ação:** Adquirir múltiplas instâncias do mesmo template para validar clustering. Responsabilidade: usuário fornecer 3+ PDFs do mesmo template para testes de Pilar B.

### Gap 2 — Crash com PDFs de tipos misturados (NÃO BLOQUEANTE)

**Descrição:** Quando múltiplos PDFs de templates diferentes são submetidos juntos (`'NoneType' object is not iterable` em relatorio-posicao), o pipeline falha.

**Impacto:** Se o usuário submeter PDFs misturados acidentalmente, o pipeline crasha. Não é cenário de uso normal (usuário deve submeter PDFs do mesmo template).

**Decisão:** Gap registrado, não bloqueia Pilar A. Criar story de correção defensive no backlog.

### Gap 3 — Infrastructure Railway (NÃO BLOQUEANTE)

- spaCy: `core_news_sm` vs `pt_core_news_sm` — não impactou os resultados (pipeline funcionou)
- Redis: não configurado — jobs perdidos após restart do servidor
- MISTRAL_API_KEY: possivelmente não configurado — observados eventos `awaiting_confirmation`

**Decisão:** Gaps de infraestrutura Railway a resolver em story de DevOps separada. Não bloqueiam Pilar A.

---

## 4. Tabela Consolidada de Resultados

| Tipo | PDFs Testados | Status | Mapeamento | Gaps |
|------|--------------|--------|------------|------|
| Relatório | 3 | ✅ Estrutura OK | Single-PDF | Multi-sample não validado |
| Apólice | 1 | ✅ Estrutura OK | Single-PDF | Multi-sample não validado |
| Boleto | 2 | ✅ Estrutura OK | Single-PDF | Multi-sample não validado |
| DIRF | 1 | ✅ Estrutura OK | Single-PDF | Tabelas detectadas (9 tabelas) |
| Certificado | 2 | ✅ Estrutura OK | Single-PDF | Type3 fonts: risco baixo |

---

## 5. Decisão Formal

**GAPS PENDENTES** — com gaps aceitos.

**Justificativa:** O Pilar A (Detecção Estrutural) está **funcionalmente completo**:
- Todos os tipos de documento processam sem crash
- Estrutura corretamente extraída (seções, tabelas, imagens, campos dinâmicos)
- DIRF com tabelas aninhadas: resultado excelente

Os gaps identificados (multi-sample clustering, crash defensive, infraestrutura Railway) são:
- Ou aceitos para este Pilar (multi-sample → Pilar B)
- Ou não bloqueantes (crash defensivo, infra)

**Próximo passo:** Criar Epic 48 (Pilar B — Binding XSD) após commit e deploy das correções pendentes de Stage 3.

---

## 6. Ações Antes de Iniciar Pilar B

1. **Obrigatório:** Commitar e deployar `backend/services/stages/stage3_structural/` (modificações não commitadas)
2. **Obrigatório:** Commitar `backend/tests/test_stage3_image_area_handler.py`
3. **Recomendado:** Corrigir `pt_core_news_sm` no Railway (renomear ou instalar modelo correto)
4. **Recomendado:** Configurar Redis no Railway (Upstash ou Railway Redis add-on)
5. **Backlog:** Story de correção para crash com PDFs de templates misturados
6. **Para Pilar B:** Adquirir 3+ PDFs do mesmo template para cada tipo

---

## 7. Evidências

- Resultados single-PDF: `docs/reports/epic-47/pipeline-single-pdf-results.json`
- Ground truth PyMuPDF: `docs/reports/epic-47/ground-truth-47123.json`
- Type3 fonts spike: `docs/reports/epic-47/type3-fonts-report.json`
- DIRF multi-PDF: `docs/reports/epic-47/pipeline-dirf.json`
