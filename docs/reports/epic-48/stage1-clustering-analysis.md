# Stage 1 — Análise Técnica: Clustering de Layout

**Data:** 2026-04-17 (v3 — ensemble voting + análise de pegadinhas)
**Autor:** @architect (Aria)
**Status:** `current` — base para planejamento de desenvolvimento
**Relacionado a:** Epic 48 (Pilar B — Binding XSD)

> **v3 — Multi-Signal Ensemble:** abandona pHash-only por ensemble voting de 4 sinais independentes. Cada sinal tem falhas conhecidas mas compensam-se mutuamente. Documento organizado para virar US de desenvolvimento — cada problema tem solução(ões), cada solução tem dono, arquivo, estimativa e critério de aceite.

---

## 0. TL;DR

**Problema:** Stage 1 produz 1 cluster por PDF em vez de 1 cluster para N PDFs do mesmo template. Tela de revisão humana desconectada. Fator LLM inoperante. Diversas premissas do documento anterior eram falsas (não verificadas).

**Descobertas da auditoria:**

| Descoberta | Evidência | Impacto |
|---|---|---|
| `imagehash.phash` já está em uso | `cluster_validation.py:99-120` | Subutilizado como validador; promover a sinal primário |
| `_await_operator_confirmation` **NÃO existe** | `grep` retorna zero no backend inteiro | Story 1.1 precisa implementar do zero |
| Stage 3.1 DE FATO itera `cluster["pages"]` | `multi_example_analysis.py:212-244` | Confirma contrato — Gap 1 é crítico |
| Contract: `total_pdfs = 1` → `strength = "none"` | `multi_example_analysis.py:303` | Clustering errado → classificação silenciosa falha |
| `pymupdf4llm` disponível (PyPI) | Pesquisa web | Permite fingerprint semântico estrutural |

**Solução proposta — Multi-Signal Ensemble Voting:**

Para cada par (P, P'), calcular 4 sinais independentes e aplicar majority voting:

| Sinal | O que mede | Lib | Falha quando | Compensado por |
|---|---|---|---|---|
| **`phash_visual`** | Aparência visual do thumbnail | `imagehash` (✅ já na stack) | Densidade textual varia muito (tabelas dinâmicas) | struct, markdown |
| **`font_jaccard`** | Assinatura tipográfica | `fitz.get_text("dict")` (✅ já na stack) | Emissor muda fonte (raro no domínio) | phash, markdown |
| **`struct_edit`** | Posições dos blocos (bbox-only, sem texto) | custom (~30 LOC) | Leve drift de coordenadas | markdown, font |
| **`markdown_hash`** | Estrutura semântica do conteúdo | `pymupdf4llm` (novo, ~1MB) | Texto com muito ruído OCR-like | phash, struct |

**Regra:**
- 4/4 match → mesmo template, `confidence = "high"`
- 3/4 match → mesmo template, `confidence = "medium"`
- 2/4 match → **revisão humana obrigatória**, `confidence = "low"`
- ≤ 1/4 → templates distintos

**Por que ensemble é objetivamente melhor que sinal único:**
- Robustez comprovada em document classification (Microsoft, Google usam)
- Nenhum sinal precisa ser perfeito
- Debug explícito: "separou porque struct e markdown discordaram"
- Extensível: adicionar sinal novo é adicionar coluna à votação
- Calibração por tipo: cada sinal tem seu threshold, ajustável

---

## 1. Contexto

Durante o Epic 48, ao validar clustering multi-sample (3+ PDFs do mesmo template), foi identificado que o Stage 1 produz **1 cluster por PDF** em vez de **1 cluster para todos os PDFs do mesmo template**. Esse é o Gap 1 do Stage 1.

Além disso: tela de revisão humana não integrada, fator LLM inoperante, e casos de tabelas dinâmicas / PDFs com páginas repetidas não documentados formalmente.

**Este documento registra:**
- Regra de detecção formal (ensemble voting)
- Casos de uso concretos
- Contrato Stage 1 → downstream (validado)
- Pesquisa de libs/métodos prontos
- Problemas + soluções para cada um
- **Pegadinhas conhecidas** + mitigações
- Stories planejadas com escopo explícito
- Plano B se Story 0.1 reprovar

---

## 2. Regra de Detecção — Ensemble Voting

### 2.1 Definição formal

Duas páginas P e P' pertencem ao **mesmo template** se e somente se a votação majoritária dos 4 sinais resulta em `match ≥ 3`:

```
signals = {
    phash_visual:   hamming(phash128(P), phash128(P')) ≤ T_phash,
    font_jaccard:   jaccard(font_sig(P), font_sig(P')) ≥ T_font,
    struct_edit:    norm_edit_distance(layout(P), layout(P')) ≤ T_struct,
    markdown_hash:  hash(abstract_md(P)) == hash(abstract_md(P')),
}

matches = sum(signals.values())
decision = {
    4: "same_template_high_confidence",
    3: "same_template_medium_confidence",
    2: "uncertain → human_review",
    1: "distinct_templates",
    0: "distinct_templates",
}[matches]
```

### 2.2 Detalhamento dos sinais

#### Sinal 1 — `phash_visual` (perceptual hash)

```python
def phash_visual_match(page_a, page_b, T_phash=8) -> bool:
    """Renderiza thumbnail 128×128 grayscale, DCT, compara 64-bit hash."""
    import imagehash
    hash_a = imagehash.phash(render_thumbnail(page_a, 128))
    hash_b = imagehash.phash(render_thumbnail(page_b, 128))
    return (hash_a - hash_b) <= T_phash
```
**Captura:** aparência visual geral, layout macro, presença de logos/tabelas.
**Falha em:** páginas com densidade textual muito variável (tabela 3 linhas vs 15 linhas).
**Custo:** ~50ms render + hash por página.

#### Sinal 2 — `font_jaccard` (tipografia)

```python
def font_jaccard_match(page_a, page_b, T_font=0.70) -> bool:
    """Jaccard sobre {(y_bucket, font_name, size_bucket)}."""
    return jaccard(font_sig(page_a), font_sig(page_b)) >= T_font

def font_sig(page) -> frozenset:
    spans = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0: continue
        for line in block["lines"]:
            for span in line["spans"]:
                if not span["text"].strip(): continue
                y_bucket = round(span["origin"][1] / page.rect.height, 1)  # 0.1 bucket
                size_bucket = round(span["size"] * 2) / 2                  # 0.5pt bucket
                spans.append((y_bucket, span["font"], size_bucket))
    return frozenset(spans)
```
**Captura:** identidade tipográfica do emissor.
**Falha em:** emissores diferentes para mesmo template lógico (raro no domínio Planet Express).
**Custo:** zero extra — usa `get_text("dict")` que substitui `get_text("blocks")` atual.

**Nota sobre buckets:**
- `y_bucket = 0.1` (10% da altura) → tolera drift vertical significativo. Era 0.01 na v1 (granular demais).
- `size_bucket = 0.5pt` → tolera arredondamento do motor.

#### Sinal 3 — `struct_edit` (layout puro, sem texto)

```python
def struct_edit_match(page_a, page_b, T_struct=0.20) -> bool:
    """Compara sequência de (x_bucket, y_bucket, w_bucket, h_bucket) sem texto."""
    layout_a = layout_seq(page_a)
    layout_b = layout_seq(page_b)
    norm_dist = levenshtein(layout_a, layout_b) / max(len(layout_a), len(layout_b))
    return norm_dist <= T_struct

def layout_seq(page) -> list:
    """Sequência ordenada de bboxes bucketizadas — invariante a texto."""
    blocks = sorted(
        [(b[0], b[1], b[2]-b[0], b[3]-b[1]) for b in page.get_text("blocks") if int(b[6]) == 0],
        key=lambda b: (round(b[1], -1), round(b[0], -1))  # sort by y, then x
    )
    return [(round(x/w, 1), round(y/h, 1), round(w/W, 1), round(h/H, 1)) for ...]
```
**Captura:** posição e tamanho dos blocos — **invariante a texto**.
**Falha em:** templates com layout similar mas fontes diferentes (compensa com font).
**Custo:** zero extra — usa blocks já extraídos.

#### Sinal 4 — `markdown_hash` (estrutura semântica)

```python
def markdown_hash_match(page_a, page_b) -> bool:
    """Hash do markdown abstraído (valores variáveis → tokens)."""
    return markdown_fingerprint(page_a) == markdown_fingerprint(page_b)

def markdown_fingerprint(page) -> str:
    import pymupdf4llm, hashlib, re
    md = pymupdf4llm.to_markdown(page.doc, pages=[page.number])
    # Abstração de valores variáveis
    md = re.sub(r'\d{3}\.\d{3}\.\d{3}-\d{2}', '[CPF]', md)
    md = re.sub(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', '[CNPJ]', md)
    md = re.sub(r'\d{2}/\d{2}/\d{4}', '[DATE]', md)
    md = re.sub(r'R\$\s*[\d.,]+', '[BRL]', md)
    md = re.sub(r'\d[\d.,]*', '[NUM]', md)
    md = re.sub(r'\s+', ' ', md).strip()
    return hashlib.sha256(md.encode()).hexdigest()[:16]
```
**Captura:** estrutura semântica (headings, tabelas, listas) + labels fixos. **Invariante a dados da instância.**
**Falha em:** páginas com muito ruído / texto embaralhado / tabelas raster sem OCR.
**Custo:** ~100-200ms por página via pymupdf4llm.

### 2.3 Casos de uso — como o ensemble se comporta

#### Caso A — 3 PDFs PosicaoConsolidada (mesmo template)

| Sinal | Match | Motivo |
|---|---|---|
| phash | ✅ | Thumbnails ~iguais (dados borram) |
| font | ✅ | Mesmo motor → Jaccard ≈ 1.0 |
| struct | ✅ | Bboxes nos mesmos lugares |
| markdown | ✅ | Valores abstraídos → strings idênticas |

**Resultado:** 4/4 → cluster único, high confidence ✅

#### Caso B — Single PDF Rodrigo/Suelen (páginas repetidas)

| Sinal | Match | Motivo |
|---|---|---|
| phash | ✅ | Thumbnail visualmente idêntico |
| font | ✅ | Mesma página do mesmo motor |
| struct | ✅ | Bboxes batem perfeitamente |
| markdown | ✅ | Estrutura markdown idêntica, valores abstraídos |

**Resultado:** 4/4 → cluster único ✅

#### Caso C — Tabela dinâmica (3 vs 15 linhas)

| Sinal | Match | Motivo |
|---|---|---|
| phash | ❌/⚠️ | Densidade do corpo diverge → distance 10-15 |
| font | ✅ | Fontes iguais → Jaccard = 1.0 |
| struct | ❌ | Mais bboxes em uma instância → edit distance alta |
| markdown | ✅ | Linhas abstraídas para tokens → estrutura vira `\| [NUM] \| [TEXT] \|` repetido → **depende de implementação** |

**Resultado esperado:** 2-3/4 match. Aqui está o ponto crítico:
- Se **markdown detectar padrão repetitivo** de linha → match → 3/4 → cluster correto
- Se não → 2/4 → revisão humana (aceitável como fallback)

**Melhoria para Caso C (opcional):** abstração markdown detecta `\| [NUM] \| [TEXT] \|\n` repetido N vezes e normaliza para `[TABLE_ROW × N]` → match ✅.

#### Caso D — Capa + detalhe no mesmo PDF (templates distintos)

| Sinal | Match | Motivo |
|---|---|---|
| phash | ❌ | Layouts visualmente distintos |
| font | ❌/⚠️ | Capa pode usar fontes diferentes |
| struct | ❌ | Bboxes completamente distintos |
| markdown | ❌ | Estrutura semântica diferente (título vs tabela) |

**Resultado:** 0-1/4 → clusters distintos ✅

---

## 3. Contrato de Dados Stage 1 → Downstream (VALIDADO)

```
Stage 1 output: context["clusters"] = list[dict[str, Any]]
  ├── cluster_id: "A", "B", "_blank", "_scanned"
  ├── pages: list[{pdf_id: str, page_index: int}]
  ├── representative_page: {pdf_id, page_index}
  ├── page_count: N
  ├── confidence: {level: "high"|"medium"|"low", confidence: 0-1, factors: {...}}
  └── signals: {phash: bool, font: bool, struct: bool, markdown: bool}  ← NOVO
```

**Validação empírica (leitura de `multi_example_analysis.py:212-244`):**

```python
# Stage 3.1 itera TODAS as páginas do cluster
for page_info in cluster["pages"]:
    for block in raw_text_blocks[f"{pdf_id}:{page_index}"]:
        position_map[(x_center, y_center)]["texts"].append(block["text"])
        position_map[(x_center, y_center)]["pdf_ids"].add(pdf_id)

total_pdfs = len({p["pdf_id"] for p in cluster["pages"]})
# strength = "none" if total_pdfs <= 1 else ("strong" if has_variation else "weak")
```

**Impacto de Gap 1 (cluster errado):**
- `total_pdfs = 1` → `strength = "none"` → tudo classificado como "label" (fixo)
- Template gerado sem campos dinâmicos → **Pilar B fica cego** — confirma prioridade.

| Stage | Consome | Para quê |
|---|---|---|
| Stage 2 | `representative_page` | Extração profunda (fontes, cores, imagens) |
| **Stage 3.1** | **`pages[]` completo** | **Multi-Example Analysis — depende de N ≥ 2 PDFs distintos** |
| Stage 3.2 | `representative_page` | Mistral OCR (tabelas raster, bbox imagens) |
| Stage 3.3 | Output 3.1 + 3.2 | Classifica static/dynamic |
| Stage 4 | Campos dinâmicos | Mapeamento XSD |
| Stage 5 | Estrutura + bindings | Gera HTML com `{{campo}}` |

---

## 4. Pesquisa de Libs e Métodos Prontos

### 4.1 Libs confirmadas na stack

| Lib | Uso atual | Uso proposto |
|---|---|---|
| `imagehash` | Validação secundária em `_phash_crosscheck` | Sinal 1 do ensemble |
| `fitz` (PyMuPDF) | `get_text("blocks")` — posição + texto | **`get_text("dict")`** — adiciona font, size, color (zero custo extra) |
| `Pillow` | Render de thumbnails | Continua |
| `spacy` | NER em Stage 3 | Opcional — NER para abstração markdown (futuro) |

### 4.2 Lib nova recomendada

**`pymupdf4llm`** ([PyPI](https://pypi.org/project/pymupdf4llm/)) — extensão oficial do PyMuPDF que converte PDF em markdown estruturado ([docs](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/)).
- **Tamanho:** ~1MB, depende apenas do fitz já presente
- **Saída:** markdown com headings, tabelas, listas reconhecidas
- **Uso:** Sinal 4 — hash do markdown abstraído = fingerprint semântico
- **Por que é outside-the-box:** captura estrutura de DOCUMENTO (títulos, tabelas) que pHash não vê e font não discrimina. É o único sinal que entende "isso é uma tabela de 3 colunas com totalizador"

### 4.3 Libs avaliadas e descartadas (com motivo)

| Lib | Por que não agora | Condição para reconsiderar |
|---|---|---|
| `docling` (IBM) | Pipeline pesado, GPU recomendada, overkill para PDFs vetoriais | Se ensemble falhar em 5+ tipos |
| `sentence-transformers` | +300MB, ROI questionável para templates determinísticos | Se Camadas 1+2 deixarem ≥ 5% falsos |
| `LayoutParser` / `DocLayout-YOLO` / `surya` | Deep learning para PDFs escaneados (Mistral já cobre) | Nunca (fora do domínio) |
| `datasketch` MinHashLSH | Overkill para 20-100 páginas | Se batches passarem a 500+ páginas |
| `pymupdf-layout` | Duplica funcionalidade de `pymupdf4llm` | Nunca |
| `BK-Tree` | Overkill — union-find resolve | Se batches passarem a 500+ páginas |

### 4.4 Comparação de abordagens

| Abordagem | Acurácia esperada | Complexidade | Deps novas | Debugável |
|---|---|---|---|---|
| Atual (textual + phash 2ário) | 60-70% (gap 1 reprova) | Alta | zero | Média |
| pHash-only (v2) | 80-85% | Baixa | zero | Baixa |
| **Ensemble 4-sinal (v3)** | **90-95%** | Média | +1MB (pymupdf4llm) | **Alta** (vota explícita) |
| Ensemble + Sentence Transformers | 92-96% | Alta | +300MB | Alta |
| Docling pipeline | 92-96% | Muito alta | +GB, GPU | Média |

---

## 5. Problemas Identificados + Soluções Propostas

### 5.1 Gap 1 — Clustering Cross-Document Falha

**Sintoma:** 3 PDFs do mesmo template → 3 clusters.

**Causa raiz:** Similaridade atual é puramente textual-posicional. Body varia por conteúdo → similaridade cai entre instâncias do mesmo template.

**Fix parcial aplicado (commit `4003f67`):** `stable_ys` como filtro. Resolve parcialmente mas depende de N ≥ 3 páginas e ignora tipografia.

**Solução proposta:** Multi-Signal Ensemble (§2). Cada sinal captura dimensão diferente; majority voting compensa falhas individuais.

**Story destino:** 2.1 + 2.2 + 2.3 + 2.4 (Camada 2, uma por sinal).

---

### 5.2 Gap 2 — Tela de Revisão Humana Desconectada

**Sintoma:** `checkpoint_confidence_threshold = 0.70` nunca é consumida.

**Evidência:** `grep -r "checkpoint_confidence_threshold" backend/` retorna apenas a definição.

**Correção crítica da v1:** `_await_operator_confirmation` **NÃO existe** no backend. Precisa ser implementado do zero.

**Soluções consideradas (escolha documentada):**

| Opção | Complexidade | Trade-off | Escolha |
|---|---|---|---|
| A. Asyncio Event in-memory + job status | Baixa | Perde estado em restart do worker | ⚠️ Frágil |
| B. Supabase table `pipeline_checkpoints` | Média | Persistente, mas migration + cleanup | ✅ **Escolhida** |
| C. Redis pub/sub | Alta | Performance alta, mas Redis não está na stack | ❌ Fora de stack |
| D. Polling do frontend a cada 2s | Baixa | Load alto, latência de resposta | ❌ |

**Escolhida:** B (Supabase) porque já está na stack, sobrevive a restart, simples de debugar. Scope inclui migration + endpoint + TTL cleanup job.

**Story destino:** 1.1 (backend) + 1.3 (frontend).

---

### 5.3 Gap 3 — Fator LLM Inoperante

**Estado atual:**
```python
confidence = 0.3*quality + 0.3*phash + 0.2*consensus + 0.2*llm  # llm=0.5 hardcoded
```

**Causa:** Gemini foi removido da stack (decisão locked — Mistral incondicional no Stage 3.2). Fator LLM penaliza arbitrariamente.

**Solução proposta (novo modelo de confiança):**

Com ensemble voting, confidence deriva diretamente do voto:
```python
confidence = matches / 4.0    # 4/4 = 1.0, 3/4 = 0.75, 2/4 = 0.5
level = {4: "high", 3: "medium", 2: "low", 1: "low", 0: "n/a"}[matches]
```

Simplificação radical: **zero pesos arbitrários**. Confidence é proporção objetiva do ensemble.

**Story destino:** 1.2 (remove LLM + redefine confidence model).

---

### 5.4 Gap 4 — Sinal de Similaridade Incompleto

**Sintoma:** `get_text("blocks")` descarta font, size, weight, color.

**Solução:** usar `get_text("dict")` que retorna tudo sem custo extra. Popula Sinal 2 (font_jaccard).

**Story destino:** 2.2.

---

## 6. Pegadinhas Conhecidas + Mitigações

> Cada pegadinha tem solução explícita, transformando-se em scope de história.

### 🔴 Pegadinha #1 — `quality_score` indefinido no novo modelo

**Problema:** na proposta anterior (v2), `quality_score` tinha peso 0.40 mas dependia de função que seria removida.

**Solução v3:** abandonar `quality_score` como fator independente. **Confidence = matches/4.0** (objetivo, derivável, determinístico).

**Status:** resolvido no design.

---

### 🔴 Pegadinha #2 — Infra de persistência de pausa de pipeline não existe

**Problema:** Story 1.1 original assumia tabela e endpoint que não existem.

**Solução explícita:**
1. **Migration** — criar `pipeline_checkpoints` table:
   ```sql
   CREATE TABLE pipeline_checkpoints (
       id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
       job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
       stage_number INT NOT NULL,
       checkpoint_type TEXT NOT NULL, -- 'stage1_review'
       payload JSONB NOT NULL,
       status TEXT NOT NULL CHECK (status IN ('awaiting_review', 'resolved', 'timeout', 'aborted')),
       created_at TIMESTAMPTZ DEFAULT now(),
       resolved_at TIMESTAMPTZ,
       timeout_at TIMESTAMPTZ NOT NULL,
       decision JSONB
   );
   CREATE INDEX ON pipeline_checkpoints(status, timeout_at);
   ```

2. **Endpoint** — `POST /jobs/{job_id}/checkpoint/{checkpoint_id}/decision`:
   ```python
   @router.post("/jobs/{job_id}/checkpoint/{checkpoint_id}/decision")
   async def submit_checkpoint_decision(
       job_id: UUID, checkpoint_id: UUID,
       decision: ReviewDecision,
   ) -> dict:
       # UPDATE pipeline_checkpoints SET decision=?, status='resolved', resolved_at=now()
       # Signal asyncio.Event para worker resumir
   ```

3. **Await pattern no orchestrator:**
   ```python
   async def _await_operator_confirmation(
       job_id: UUID, checkpoint_type: str, payload: dict, timeout_s: int = 600,
   ) -> dict:
       checkpoint_id = await _create_checkpoint(job_id, checkpoint_type, payload, timeout_s)
       event = _checkpoint_events.setdefault(checkpoint_id, asyncio.Event())
       try:
           await asyncio.wait_for(event.wait(), timeout=timeout_s)
           return await _load_checkpoint_decision(checkpoint_id)
       except asyncio.TimeoutError:
           await _mark_checkpoint_timeout(checkpoint_id)
           return {"action": "timeout", "default": "continue"}
   ```

4. **Cleanup job** — cron semanal para remover checkpoints antigos resolved/timeout.

**Scope real:** 1-2 dias. Incluído em Story 1.1.

---

### 🔴 Pegadinha #3 — Endpoint de thumbnails não existe

**Problema:** Frontend precisa exibir páginas problemáticas para o operador decidir.

**Solução explícita:**
1. **Endpoint novo** — `GET /jobs/{job_id}/pages/{pdf_id}/{page_index}/thumbnail?size=256`:
   ```python
   @router.get("/jobs/{job_id}/pages/{pdf_id}/{page_index}/thumbnail")
   async def get_page_thumbnail(
       job_id: UUID, pdf_id: str, page_index: int, size: int = 256,
   ) -> StreamingResponse:
       # 1. Verifica cache Supabase Storage: thumbnails/{job_id}/{pdf_id}_{page_index}_{size}.jpg
       # 2. Se não existe, renderiza via fitz + salva
       # 3. Streams JPEG
   ```

2. **Cache** — Supabase Storage bucket `thumbnails` (ou reaproveitar bucket existente).

3. **Pre-warm opcional** — durante Stage 1, renderizar thumbnails 256×256 em paralelo com pHash (já renderizando 128×128, só mais um tamanho).

**Scope:** 4h. Incluído em Story 1.3 (frontend) como dependência backend.

---

### 🔴 Pegadinha #4 — Calibration spike pode revelar que não há threshold global

**Problema:** se `T_phash` varia de 4 (boleto) a 12 (relatório), não existe threshold global.

**Soluções fora da caixa:**

**Opção A — Threshold adaptativo por batch:**
```python
# Em cada batch: T = média_intra + 2*std_intra
distances = [phash(i) - phash(j) for i, j in pairs_same_pdf]
T_phash_adaptive = np.mean(distances) + 2 * np.std(distances)
```
Vantagem: não precisa saber tipo. Desvantagem: único PDF com páginas muito diferentes → T inflacionado.

**Opção B — Silhouette-optimized threshold:**
```python
# Testa múltiplos T, escolhe o que maximiza silhouette score
from sklearn.metrics import silhouette_score
best_T = max(range(2, 16), key=lambda T: silhouette_for_threshold(T))
```
Vantagem: 100% data-driven. Desvantagem: custo.

**Opção C — Thresholds lenient, confia no ensemble:**
- `T_phash = 12` (generoso)
- `T_font = 0.60` (generoso)
- `T_struct = 0.30` (generoso)
- Se 3 de 4 sinais matam com thresholds lenient → alta confiança

Vantagem: cada sinal individual pode errar; ensemble corrige. Desvantagem: requer 4 sinais bons.

**Escolha documentada:** **Opção C combinada com A** — thresholds lenient fixos como default, adaptativo como ajuste opcional se spike mostrar muita variância.

**Story destino:** 0.1 (spike de calibração decide qual opção prevalece).

---

### 🟡 Pegadinha #5 — pHash falha em casos com variação de densidade

**Problema:** tabela de 3 linhas vs 15 linhas → pHash distance alta mesmo sendo mesmo template.

**Soluções outside-the-box (3 opções, escolhida #3):**

**Opção 1 — Multi-hash ensemble:**
Calcular `phash + dhash + ahash + whash` e fazer majority voting **dentro do sinal visual**. Se 3 de 4 batem → match.
- Ganho marginal — todos os 4 sofrem do mesmo problema de densidade.

**Opção 2 — Region-based pHash:**
Dividir thumbnail em grid 3×3, pHash de cada região. Match se ≥ 6 de 9 regiões batem.
- Pro: cabeçalho bate sempre, corpo pode diferir → capturado.
- Con: mais código, ainda sensível a densidade.

**Opção 3 — Content-masked pHash (ESCOLHIDA):**
Renderizar página mascarando áreas de texto com retângulos cinza uniforme antes do pHash. Isso elimina completamente o efeito de variação textual.
```python
def masked_thumbnail(page, size=128):
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
    img = Image.frombytes("RGB", ...)
    # Desenha retângulo cinza sobre cada bbox de texto
    draw = ImageDraw.Draw(img)
    for block in page.get_text("blocks"):
        if int(block[6]) == 0:  # text block
            draw.rectangle([block[0]*scale, ..., block[3]*scale], fill=(200, 200, 200))
    return img.convert("L")
```
- Pro: captura ESTRUTURA pura, ignora conteúdo. Pronto com Pillow (já na stack).
- Con: mais uma etapa de render. Custo marginal.

**Story destino:** 2.1 (phash_visual implementa masked variant).

---

### 🟡 Pegadinha #6 — Rendering upfront é overhead

**Problema:** Story 2.1 renderiza 128×128 grayscale de TODA página antes de clusterizar. Para 100 páginas, é 5-15s.

**Soluções:**

**Opção A — Lazy render:**
Computar sinais baratos primeiro (font_jaccard + struct_edit), só renderizar (phash, markdown) quando os dois primeiros dão match ambíguo.
- Pro: economia em casos claros.
- Con: lógica de curto-circuito mais complexa.

**Opção B — Paralelização:**
`concurrent.futures.ProcessPoolExecutor` (fitz não é 100% thread-safe mas funciona bem em processos separados).
- Pro: 4x speedup em máquinas multicore.
- Con: overhead de IPC em batches pequenos.

**Opção C — Cache persistent:**
Hash de (pdf_id + page_index + file_mtime) → Supabase Storage. Runs subsequentes do mesmo PDF pulam render.
- Pro: 100% de economia em re-runs (template editing, debug).
- Con: +infra.

**Escolha:** **A + C** — lazy render primário, cache persistent como otimização secundária. Opção B só se benchmark mostrar gargalo real.

**Story destino:** 2.5 (otimização — só se benchmark em 0.2 mostrar ≥ 10s de render).

---

### 🟡 Pegadinha #7 — Font Jaccard granular demais

**Problema:** bucket `y_bucket = 0.01` em proposta v1 era muito granular.

**Solução v3:** `y_bucket = 0.1` (10% da altura da página). Tolera drift de até 50px em A4. Captura estrutura sem explodir com ruído.

**Validação:** spike de Story 0.1 mede Jaccard intra vs inter com bucket 0.1.

---

### 🟡 Pegadinha #8 — Perda de observabilidade

**Problema:** pHash é opaco. "Distance = 12" não diz o quê mudou.

**Soluções outside-the-box:**

**Opção A — Visual XOR diff:**
```python
def visual_diff(page_a, page_b) -> Image:
    """Imagem destacando onde A e B diferem."""
    img_a, img_b = thumbnail(page_a), thumbnail(page_b)
    return ImageChops.difference(img_a, img_b)
```
Salvar em caso de baixa confiança → operador vê exatamente onde diferem.

**Opção B — Sinal explícito logado:**
Cada cluster salva `signals_per_pair` em structured logs:
```json
{"cluster_id": "A", "pair": [0, 1], "signals": {"phash": 1, "font": 1, "struct": 0, "markdown": 1}}
```
Debug imediato: "pair separou porque struct foi o único 0".

**Escolhida:** **Opção B** (log estruturado) + A como bonus no frontend de revisão humana.

**Story destino:** 1.4 (observabilidade em todas as camadas).

---

### 🟡 Pegadinha #9 — Remoção de consensus check elimina rede de segurança

**Problema:** algoritmo atual confronta graph vs hierarchical. Remover significa confiar 100% no novo.

**Solução: deploy paralelo (shadow mode):**

**Fase 1 (Camada 2):** **AMBOS os algoritmos rodam em paralelo**. Novo ensemble produz clusters; antigo continua, mas apenas loga métricas.

```python
new_clusters = _cluster_via_ensemble(pages, ...)
if os.getenv("STAGE1_SHADOW_OLD_ALGO", "0") == "1":
    old_clusters = _cluster_via_old(pages, ...)
    await _log_divergence(new_clusters, old_clusters)
```

**Fase 2 (após N runs):** se divergência < 5%, remover o antigo (Camada 3).

**Story destino:** 2.6 (shadow logging) + 3.1 (remoção final, só depois de validação).

---

### 🟡 Pegadinha #10 — Clusters singleton não explicitamente tratados

**Problema:** uma página que não dá 3/4 match com nenhuma outra vira cluster singleton. Política?

**Solução:** singleton cluster com `len(pages) == 1` E `confidence < high`:
- Se está em batch com outras páginas processáveis → **revisão humana obrigatória**
- Se é a única página processável do batch → aceito automaticamente (não há comparação possível)

**Story destino:** 1.1 (lógica de decisão de review required).

---

### 🟢 Pegadinha #11 — Testes existentes vão quebrar

**Problema:** `tests/test_stage1_layout_clustering.py` testa `_geometry_similarity`, `_cluster_graph`, `_consensus_check` — funções a remover.

**Solução:** parte da Story 2.3 (limpeza) inclui reescrita dos testes para novo algoritmo. Usar fixtures de Story 0.1 como input de regressão.

**Story destino:** 2.3.

---

### 🟢 Pegadinha #12 — Fixtures do usuário com nomes corrompidos

**Problema:** `git status` mostra paths tipo `backend/tests/fixtures/samples/boleto​ && cp D:Downloads...` (parece bug de cp no Windows).

**Solução:** Story 0.1 começa validando inventário de fixtures e renomeando corretamente se necessário. Se fixtures inválidas, gerar fixtures sintéticas para baseline.

**Story destino:** 0.1 (pré-tarefa — validar fixtures).

---

### 🟢 Pegadinha #13 — PyMuPDF `get_pixmap` em threads

**Problema:** documentação do fitz warns sobre thread safety.

**Solução:** começar **serial**. Se benchmark de Story 0.2 mostrar gargalo, migrar para `ProcessPoolExecutor` (processos, não threads). Story 2.5 opcional.

---

### 🟢 Pegadinha #14 — Stub `_vision_client` residual

**Problema:** Gemini removido mas `context.get("_vision_client")` ainda é checado.

**Solução:** Story 1.2 limpa referências residuais.

---

## 7. Arquitetura Proposta — Multi-Signal Ensemble

### 7.1 Nova estrutura de módulos

```
backend/services/stages/stage1_clustering/
├── page_preprocessing.py      # Classificação + extração + normalização (mantém)
├── signals/                   # NOVO
│   ├── __init__.py
│   ├── phash_signal.py       # Sinal 1: imagehash + masked thumbnail
│   ├── font_signal.py        # Sinal 2: font_jaccard
│   ├── struct_signal.py      # Sinal 3: bbox sequence edit distance
│   └── markdown_signal.py    # Sinal 4: pymupdf4llm hash
├── ensemble_voting.py         # NOVO — majority voting + decision
├── union_find.py              # NOVO — agrupamento via Union-Find
├── review_checkpoint.py       # NOVO — detecta clusters para review humana
├── cluster_validation.py      # Mantém validação + confidence (simplificada)
└── clustering_algorithms.py   # REMOVIDO após Camada 3
```

### 7.2 Pipeline de clustering proposto

```
1. Page Preprocessing (existente + get_text("dict"))
   ↓
2. Para cada página, computar 4 signatures (paralelizável)
   ├── thumbnail_hash (imagehash — masked)
   ├── font_signature (frozenset)
   ├── layout_sequence (list[bbox])
   └── markdown_fingerprint (hash 16 chars)
   ↓
3. Para cada par (i, j), computar 4 sinais binários
   ↓
4. Majority voting: matches ≥ 3 → same cluster via Union-Find
   ↓
5. Por cluster: calcular confidence = matches_média / 4.0
   ↓
6. Se qualquer cluster tem level="low" → SSE + pausa + human review
   ↓
7. Output: clusters[] com signals + confidence + factors
```

### 7.3 Modelo de Confidence (simplificado)

```python
def compute_cluster_confidence(cluster_pages: list, signal_results: dict) -> dict:
    """
    confidence = média de matches/4 para todos os pares intra-cluster.
    """
    if len(cluster_pages) == 1:
        return {"level": "high", "confidence": 1.0, "factors": {"singleton": True}}

    total_matches = 0
    total_pairs = 0
    for i in range(len(cluster_pages)):
        for j in range(i+1, len(cluster_pages)):
            total_matches += signal_results[(i, j)]["matches"]
            total_pairs += 1

    avg_match_rate = total_matches / (total_pairs * 4)
    level = {
        (0.95, 1.01): "high",
        (0.75, 0.95): "medium",
        (0.00, 0.75): "low",
    }
    return {"level": ..., "confidence": avg_match_rate, "factors": {...}}
```

---

## 8. Pré-Requisitos (Camada 0)

### Story 0.1 — Validação de Fixtures + Calibration Spike (1 dia)

**Arquivo:** `backend/scripts/spike_ensemble_calibration.py` (novo)

**Entregáveis:**
1. **Inventário de fixtures:** verificar que todos os 5 tipos (relatorio, boleto, dirf, apolice, certificado) têm 3+ PDFs válidos. Renomear se nomes corrompidos. Gerar sintéticas se necessário.
2. **Matriz de sinais por tipo:** para cada par intra-template e inter-template, computar os 4 sinais. Tabela:
   ```
   | type | pair_class | phash_dist | font_jac | struct_dist | md_eq |
   | boleto | intra | 3 | 1.0 | 0.05 | True |
   | boleto | inter | 20 | 0.3 | 0.6 | False |
   | relatorio | intra | 10 | 0.95 | 0.15 | True |
   ...
   ```
3. **Thresholds recomendados:** por tipo OU global (depende dos dados).
4. **Taxa de falso positivo / falso negativo** do ensemble em cada tipo.

**Critério PASS:**
- Ensemble voting distingue intra vs inter template com recall ≥ 95% E precision ≥ 95% em TODOS os 5 tipos.
- Se falhar em algum tipo → ativa Plano B (§12).

**Estimativa:** 1 dia.

---

### Story 0.2 — Observabilidade Baseline (4h)

**Arquivo:** `backend/services/stages/stage1_layout_clustering.py` + Supabase migration.

**Métricas (log estruturado JSON + tabela `pipeline_metrics`):**
- `stage1.cluster_count`
- `stage1.pages_per_cluster_avg`
- `stage1.confidence_distribution` (histograma)
- `stage1.signals_distribution` (quantos pares com 4/3/2/1/0 matches)
- `stage1.review_required_count`
- `stage1.processing_time_ms` + breakdown por sinal
- `stage1.render_time_ms` (específico)
- `stage1.divergence_with_old_algo` (para shadow mode em Camada 2)

**Critério PASS:** métricas emitidas em N runs atuais, baseline registrado.

---

## 9. Camadas de Implementação

```
┌─────────────────── Camada 0 — Pré-requisitos (1.5 dias) ───────────────────┐
│ 0.1 Fixture inventory + Calibration spike                                   │
│ 0.2 Observabilidade baseline                                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌─────────── Camada 1 — Revisão Humana + Confidence simplificada (3 dias) ───┐
│ 1.1 _await_operator_confirmation + checkpoints table + endpoint             │
│ 1.2 Remover LLM factor + redefinir confidence model (matches/4)             │
│ 1.3 Frontend tela de revisão + endpoint de thumbnails                       │
│ 1.4 Observabilidade dos 4 sinais (preparação)                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌────────── Camada 2 — Multi-Signal Ensemble em shadow mode (5-7 dias) ──────┐
│ 2.1 phash_signal (masked thumbnail)                                         │
│ 2.2 font_signal (get_text("dict") + jaccard)                               │
│ 2.3 struct_signal (bbox edit distance)                                      │
│ 2.4 markdown_signal (pymupdf4llm abstraction)                              │
│ 2.5 ensemble_voting + union_find + shadow mode                              │
│ 2.6 Lazy render + cache persistent (otimização — só se gargalo)           │
└─────────────────────────────────────────────────────────────────────────────┘
                                     ↓
┌────────────── Camada 3 — Limpeza (após N runs shadow validados, 1 dia) ────┐
│ 3.1 Remover algoritmo antigo (NetworkX graph, scipy consensus)             │
│ 3.2 Reescrever testes unitários                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Total estimado:** 10-13 dias (sem Camada 3 dependente de validação em prod).

---

## 10. Stories Detalhadas

### Story 0.1 — Fixture Inventory + Calibration Spike (1 dia)

**Escopo:**
- Validar inventário de fixtures em `backend/tests/fixtures/samples/{5 tipos}`
- Renomear paths corrompidos do Windows se detectados
- Se faltar fixture, gerar sintéticas a partir de templates existentes
- Implementar protótipo dos 4 sinais em `backend/scripts/spike_ensemble_calibration.py`
- Rodar em todas as fixtures, salvar CSV `docs/reports/epic-48/spike-ensemble-calibration.csv`
- Gerar relatório `docs/reports/epic-48/spike-ensemble-findings.md` com thresholds e decisão GO/NO-GO

**Critério de aceite:**
- [ ] CSV com todos os pares (intra+inter) dos 5 tipos
- [ ] Thresholds recomendados documentados
- [ ] Decisão GO (prosseguir) ou NO-GO (ativar Plano B) fundamentada

---

### Story 0.2 — Observabilidade Baseline (4h)

**Escopo:**
- Migration Supabase: `pipeline_metrics (id, job_id, stage, metric_name, metric_value, created_at)`
- Instrumentar `stage1_layout_clustering.py` com métricas §8
- Rodar N runs atuais, validar métricas emitindo

**Critério de aceite:**
- [ ] Migration aplicada
- [ ] N runs geram métricas
- [ ] Dashboard simples (queries) para visualizar

---

### Story 1.1 — Checkpoint Infrastructure + Operator Confirmation (1.5 dias)

**Escopo:**
- Migration: `pipeline_checkpoints` table (§6 pegadinha #2)
- `backend/services/pipeline_checkpoints.py` (novo) — CRUD + asyncio.Event management
- `backend/services/pipeline_orchestrator_v2.py` — `_await_operator_confirmation` implementado
- `backend/api/v1/checkpoints.py` (novo) — endpoint `POST /jobs/{id}/checkpoint/{cid}/decision`
- Wire em `stage1_layout_clustering.py` — emite checkpoint se clusters com `level=="low"`
- Cleanup job (cron semanal) para remover resolved/timeout

**Critério de aceite:**
- [ ] Pipeline pausa até decisão chegar ou timeout
- [ ] Worker restart não perde estado (checkpoint persistido)
- [ ] Endpoint testado com 3 actions: confirm, abort, modify

---

### Story 1.2 — Remove LLM Factor + Simplify Confidence Model (4h)

**Escopo:**
- `cluster_validation.py`: remover `_llm_validate` e todas as referências a `llm_factor`/`_vision_client`
- Redefinir `_compute_confidence` para fórmula simplificada (matches/4)
- Limpar imports obsoletos

**Critério de aceite:**
- [ ] `grep -r "llm_factor\|_vision_client\|_llm_validate" backend/` retorna zero
- [ ] Cluster perfeito → `confidence.level == "high"`
- [ ] Testes unitários de confidence atualizados

---

### Story 1.3 — Frontend Review Screen + Thumbnail Endpoint (1 dia)

**Escopo:**
- **Backend:** endpoint `GET /jobs/{id}/pages/{pdf_id}/{page_index}/thumbnail?size=256` (§6 pegadinha #3)
- **Frontend:** `frontend/src/components/ReviewModal.vue` (novo)
  - Escuta SSE `stage1_review_required`
  - Para cada cluster: exibe thumbnails + signals_summary
  - Botões: Confirmar, Modificar (split/merge), Abortar
  - POST `/jobs/{id}/checkpoint/{cid}/decision`
- Cache Supabase Storage `thumbnails/{job_id}/{pdf_id}_{page_index}_{size}.jpg`

**Critério de aceite:**
- [ ] Modal aparece em batch com baixa confiança
- [ ] Operador consegue aprovar/abortar/modificar
- [ ] Pipeline resume corretamente

---

### Story 1.4 — Observability for 4 Signals (Preparation) (4h)

**Escopo:**
- Adicionar colunas em `pipeline_metrics` para cada sinal
- Estrutura JSON para signals_summary em logs

**Critério de aceite:**
- [ ] Schema permite armazenar breakdown por sinal
- [ ] Logs estruturados com pair_signals (ver §6 pegadinha #8)

---

### Story 2.1 — `phash_signal` with Masked Thumbnail (1 dia)

**Arquivo:** `backend/services/stages/stage1_clustering/signals/phash_signal.py` (novo)

**Escopo:**
- Função `masked_thumbnail(page, size=128)` — render com retângulos cinza sobre blocos de texto
- Função `phash_match(page_a, page_b, T_phash)` — computa hamming distance
- Cache por (pdf_id, page_index) dentro do batch
- Testes unitários com 4 casos (§2.3)

**Critério de aceite:**
- [ ] Caso A: intra ≤ T_phash
- [ ] Caso C: tabela dinâmica - masked thumbnail mitiga distância
- [ ] Caso D: inter > T_phash

---

### Story 2.2 — `font_signal` with `get_text("dict")` (1 dia)

**Arquivo:** `backend/services/stages/stage1_clustering/signals/font_signal.py` (novo)

**Escopo:**
- Modificar `_extract_blocks` para usar `get_text("dict")` (preservando `x_center`, `y_center` para Stage 3.1)
- Popular `PageInfo.font_signature = frozenset((y_bucket_0.1, font, size_0.5))`
- Função `font_jaccard_match(page_a, page_b, T_font=0.70)`

**Critério de aceite:**
- [ ] `x_center`, `y_center` continuam populados (Stage 3.1 funciona)
- [ ] Intra-template: Jaccard ≥ 0.90
- [ ] Inter-template: Jaccard < 0.50

---

### Story 2.3 — `struct_signal` (Bbox Edit Distance) (1 dia)

**Arquivo:** `backend/services/stages/stage1_clustering/signals/struct_signal.py` (novo)

**Escopo:**
- Função `layout_sequence(page) -> list[tuple]` — bboxes bucketizadas em grid 10×10
- Função `struct_edit_match(page_a, page_b, T_struct=0.20)` — Levenshtein normalizado
- Lib: `python-Levenshtein` (se não disponível, implementar DP em ~40 LOC)

**Critério de aceite:**
- [ ] Caso A: norm_dist ≤ 0.10
- [ ] Caso D: norm_dist ≥ 0.50

---

### Story 2.4 — `markdown_signal` with pymupdf4llm (1 dia)

**Arquivo:** `backend/services/stages/stage1_clustering/signals/markdown_signal.py` (novo)

**Escopo:**
- Instalar `pymupdf4llm` (`pip install pymupdf4llm`, verificar `pyproject.toml` atualizado)
- Função `markdown_fingerprint(page) -> str` — 16-char hash do markdown abstraído
- Abstração (ver §2.2.4): CPF, CNPJ, DATE, BRL, NUM, repetição de tabela
- Função `markdown_hash_match(page_a, page_b)` — igualdade exata

**Critério de aceite:**
- [ ] Casos A, B: mesmo fingerprint
- [ ] Caso C (tabela dinâmica): mesmo fingerprint se abstração de linha funcionar
- [ ] Caso D: fingerprints distintos

---

### Story 2.5 — Ensemble Voting + Union-Find + Shadow Mode (2 dias)

**Arquivo:** `backend/services/stages/stage1_clustering/ensemble_voting.py` (novo)

**Escopo:**
- Função `compute_signals_matrix(pages) -> dict[(i,j), signals]`
- Função `cluster_via_ensemble(pages, T_*) -> clusters` — usa Union-Find
- Shadow mode: rodar ensemble + algoritmo antigo em paralelo, log divergências
- Feature flag `STAGE1_ENSEMBLE_PRIMARY` (default false → antigo primário, ensemble shadow)

**Critério de aceite:**
- [ ] Shadow mode loga divergências sem afetar resultado
- [ ] Flag flip → ensemble vira primário, antigo vira shadow
- [ ] Caso A: 1 cluster com 3 PDFs
- [ ] Caso D: 2 clusters

---

### Story 2.6 — Performance Optimizations (opcional, só se necessário) (1 dia)

**Escopo (condicional em benchmark):**
- Lazy render (sinais baratos primeiro, phash/markdown só se ambíguo)
- Cache persistent Supabase Storage
- ProcessPoolExecutor se > 10s de render

**Critério de aceite:**
- [ ] Benchmark Stage 1 < 30s em batch de 100 páginas

---

### Story 3.1 — Remove Old Algorithm (1 dia, após validação)

**Pré-requisito:** 10+ runs em shadow mode com divergência < 5%.

**Escopo:**
- Remover `clustering_algorithms.py` (geometry_similarity, compute_similarity, cluster_graph, consensus_check)
- Remover dependências `networkx`, `scipy` (se não usadas em outras stages)
- Reescrever `tests/test_stage1_layout_clustering.py` para novo algoritmo
- Flip flag `STAGE1_ENSEMBLE_PRIMARY` para default true
- Remover feature flag após N runs em produção

**Critério de aceite:**
- [ ] Testes passam
- [ ] Grep `_geometry_similarity\|_cluster_graph\|_consensus_check` retorna zero
- [ ] CI verde

---

## 11. Mapa de Dependências

```
Story 0.1 ──────────────┐
                        ├─── GATE ─→ Camada 1
Story 0.2 ──────────────┘           (1.1 ‖ 1.2 ‖ 1.3 ‖ 1.4)
                                              │
                                              ↓
                                    Camada 2 (2.1 ‖ 2.2 ‖ 2.3 ‖ 2.4)
                                              │
                                              ↓
                                          Story 2.5
                                              │
                                 ┌────────────┴─────────────┐
                                 ↓                          ↓
                            Story 2.6                   Shadow validation
                            (opcional)                  (10+ runs)
                                                            │
                                                            ↓
                                                       Story 3.1
```

`‖` = paralelizável | `→` = sequencial

---

## 12. Plano B — Se Story 0.1 Reprovar

**Cenário:** spike mostra que ensemble voting não distingue intra vs inter template com recall/precision ≥ 95% em algum tipo.

**Opção B.1 — Adicionar 5º sinal:** Sentence Transformers embedding do markdown.
**Opção B.2 — Thresholds adaptativos por tipo:** detectar tipo antes (Stage 0 novo) e usar thresholds específicos.
**Opção B.3 — Reabilitar LLM visão** (apenas Stage 1 em casos `confidence == low`): Mistral Vision ou Gemini Flash. Decisão locked Stage 3 não impede uso em Stage 1.
**Opção B.4 — Fallback agressivo para revisão humana:** aceita que Stage 1 é assistido, não automatizado. Todo batch passa por operador em primeira execução.

**Escolha depende do modo de falha:**
- Falha em 1 tipo só → B.2 (thresholds por tipo)
- Falha em 3+ tipos → B.1 (sinal extra) ou B.3 (LLM assist)
- Falha catastrófica → B.4 (operador no loop sempre)

---

## 13. Arquivos a Modificar por Story

| Story | Arquivos backend | Arquivos frontend | Migrations |
|---|---|---|---|
| 0.1 | `scripts/spike_ensemble_calibration.py` (novo) | — | — |
| 0.2 | `stage1_layout_clustering.py` | — | `pipeline_metrics` |
| 1.1 | `pipeline_orchestrator_v2.py`, `services/pipeline_checkpoints.py` (novo), `api/v1/checkpoints.py` (novo), `stage1_layout_clustering.py` | — | `pipeline_checkpoints` |
| 1.2 | `cluster_validation.py` | — | — |
| 1.3 | `api/v1/thumbnails.py` (novo) | `components/ReviewModal.vue` (novo) | — |
| 1.4 | `stage1_layout_clustering.py` | — | `pipeline_metrics` (alter) |
| 2.1 | `signals/phash_signal.py` (novo) | — | — |
| 2.2 | `signals/font_signal.py` (novo), `page_preprocessing.py` | — | — |
| 2.3 | `signals/struct_signal.py` (novo) | — | — |
| 2.4 | `signals/markdown_signal.py` (novo), `pyproject.toml` | — | — |
| 2.5 | `ensemble_voting.py` (novo), `union_find.py` (novo), `stage1_layout_clustering.py` | — | — |
| 2.6 | `signals/*.py` (optimization) | — | `phash_cache` (opcional) |
| 3.1 | `clustering_algorithms.py` (delete), `tests/test_stage1_layout_clustering.py` (rewrite) | — | — |

---

## 14. Riscos Executivos

| Risco | Prob | Impacto | Mitigação |
|---|---|---|---|
| Story 0.1 reprovar ensemble | Baixa-média | Alto | Plano B (§12) |
| Infra checkpoint gera deadlock | Média | Alto | TTL + cleanup + feature flag para disable review |
| `pymupdf4llm` inconsistente entre tipos | Baixa | Médio | Sinal é 1 de 4 — ensemble compensa |
| Thumbnail endpoint sobrecarregado | Baixa | Médio | Cache Storage + rate limit |
| Shadow mode gera inconsistência UX | Baixa | Baixo | Feature flag isolado |
| Testes existentes difíceis de migrar | Média | Médio | Story 3.1 planeja rewrite |
| Performance regride > 2x | Média | Médio | Story 2.6 + lazy render |

---

## 15. O que NÃO fazer

- **Não** implementar todos os 4 sinais em um único arquivo — cada um é testável isoladamente.
- **Não** remover algoritmo antigo antes de 10+ runs em shadow mode.
- **Não** aumentar threshold individual como band-aid — se ensemble falha, ir para Plano B.
- **Não** reintroduzir LLM factor genérico (0.5 hardcoded) — se precisar LLM, é um sinal explícito do ensemble.
- **Não** confiar cegamente em `pymupdf4llm` — é o sinal mais recente, mais suscetível a edge cases.
- **Não** pular Story 0.1 — é o gate de viabilidade.
- **Não** otimizar performance antes de Story 0.2 mostrar gargalo real (premature optimization).
- **Não** implementar docling/LayoutParser/surya — fora do escopo, resolvem problema diferente.

---

## 16. Referências

### Código atual
- `backend/services/stages/stage1_clustering/page_preprocessing.py`
- `backend/services/stages/stage1_clustering/clustering_algorithms.py`
- `backend/services/stages/stage1_clustering/cluster_validation.py` — pHash já presente (§4.1)
- `backend/services/pipeline_orchestrator_v2.py`
- `backend/services/stages/stage3_structural/multi_example_analysis.py` — contrato validado

### Spikes e fixtures
- `docs/reports/epic-48/spike-48-7-findings.md`
- `docs/reports/epic-48/ground-truth-posicaoconsolidada.json`
- `backend/tests/fixtures/samples/{relatorio,boleto,dirf,apolice,certificado}/`

### Libs e pesquisa

- [ImageHash · PyPI](https://pypi.org/project/ImageHash/) — perceptual hashing (já na stack)
- [pymupdf4llm · PyPI](https://pypi.org/project/pymupdf4llm/) — markdown extraction (novo)
- [PyMuPDF4LLM docs](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) — API reference
- [BK-Tree Hamming search](https://www.sciencedirect.com/science/article/abs/pii/S0031320319303838) — fallback se escala crescer
- [datasketch MinHashLSH](https://ekzhu.com/datasketch/lsh.html) — fallback se escala crescer
- [PyMuPDF Layout](https://pymupdf.io/blog/pymupdf-layout-tutorial) — avaliado, descartado
- [Docling (IBM)](https://docling-project.github.io/docling/) — avaliado, overkill para domínio

### Papers de referência (ensemble methods)
- "A Clustering Based Approach to Perceptual Image Hashing" — IEEE
- "Hamming distributions of popular perceptual hashing techniques" — ScienceDirect
