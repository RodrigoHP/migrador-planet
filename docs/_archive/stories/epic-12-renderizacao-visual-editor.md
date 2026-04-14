# Epic 12 — Renderização Visual do Editor: Posicionamento, Campos, Cobertura e Funcionalidades

**Status:** Draft
**Branch:** feature/epic-12-renderizacao-visual-editor
**Data:** 2026-03-20
**Origem:** Análise profunda do estado atual do editor após Epic 11

---

## Problema Central

Após 11 epics, o editor ainda não entrega a proposta de valor principal: **mostrar o documento PDF renderizado com os campos identificados e posicionados corretamente no canvas**. A tela atual mostra:

- Canvas com elementos sem estilo e sem posicionamento (todos empilhados)
- "Cobertura 0%" mesmo quando o pipeline mapeia campos
- "Campos nada identificado" no painel de campos
- Erro ao clicar na aba PDF
- Snap e Coverage desabilitados (botões sem efeito)

Este epic documenta **todos** os problemas encontrados na análise de 2026-03-20 e cria as stories para resolvê-los sistematicamente.

---

## Análise Root Cause — Screenshot

O screenshot mostra (branch `feature/epic-11-estabilizacao-editor`):

```
┌─────────────────────────────────────────────────────────────────┐
│ Sem template │ Confiança 23% │ Cobertura 0%    [Cobertura][Diff][Snap]
├────────────────┬────────────────────────────────────────────────┤
│ Estrutura      │  [Canvas] [PDF] [</> Código] [Sincronizar]     │
│ Campos         │                                                 │
│                │         (página em branco com texto            │
│ (árvore com    │          espalhado sem layout,                 │
│  nomes de      │          sem estilos, coordenadas              │
│  campos)       │          incorretas)                           │
│                │                                                 │
└────────────────┴────────────────────────────────────────────────┘
```

**PDF Original (Corporate.Boleto.Convenio.pdf):** Boleto bancário com:
- Cabeçalho: "Relação de Boletos / de Convênio / 237"
- Tabela de cobranças com colunas: nome, código, nosso_numero, valor, frequência
- Seção "Recibo do Sacado": Beneficiário, Agência, Data Emissão, Vencimento
- Rodapé: Local de Pagamento, código de barras

**Gap entre PDF e Canvas:** O canvas renderiza os elementos extraídos pelo pipeline, mas:
1. Sem posição absoluta (os divs flutuam em flow normal)
2. Sem tamanho/fonte corretos
3. Sem separação visual de seções
4. Sem linhas/bordas do boleto

---

## Problemas Identificados (Prioridade Decrescente)

### CRÍTICOS — Bloqueiam funcionalidade core

#### P1: Canvas sem posicionamento absoluto (bbox ignorado)
**Arquivo:** `backend/services/stages/template_draft.py`
**Sintoma:** Elementos do canvas empilhados no topo, sem layout
**Root Cause:**
- `_bbox_to_style()` existe mas só é chamado condicionalmente
- Template draft gera `<div class="field-group">` sem `position: absolute`
- Coordenadas bbox (em pontos PDF) não são convertidas para px CSS
- `SCALE_X = 794/595` correto para A4, mas não aplicado
**Impacto:** O editor não mostra NENHUM valor visual do pipeline

#### P2: Cobertura 0% — divisão por zero
**Arquivo:** `backend/services/stages/template_draft.py` + `pipeline_result.py`
**Sintoma:** Badge "Cobertura 0%" mesmo com campos mapeados
**Root Cause:**
```python
def _calculate_coverage(field_mappings, field_tree):
    flat_paths = field_tree.get("flat_paths", []) if field_tree else []
    total = len(flat_paths)  # = 0 quando field_tree is None
    mapped = len(mapped_paths & set(flat_paths)) if flat_paths else len(mapped_paths)
    # Se total=0: percentage = mapped/0 → 0%  ← BUG
```
- Quando não há XSD carregado (`field_tree is None`): total=0, coverage=0%
- Coverage deveria ser calculada também com base em campos encontrados vs total de blocos no PDF
**Impacto:** Métrica principal do editor sempre incorreta

#### P3: Campos vazios — fieldNavItems nunca populado
**Arquivo:** `frontend/src/stores/mapping.ts`
**Sintoma:** Painel "Campos" vazio, mostra "nada identificado"
**Root Cause:**
```typescript
// session.ts chama:
mappingStore.loadPipelineFields(result.field_mappings)
// Mas loadPipelineFields() carrega apenas mappingStore.fields[]
// NÃO popula mappingStore.fieldNavItems[]
// FieldNavigator.vue lê fieldNavItems → vazio → "0 campos"
```
**Impacto:** Usuário não vê NENHUM campo identificado pelo pipeline

#### P4: PDF tab falha/erro
**Arquivo:** `frontend/src/organisms/PDFReference.vue`
**Sintoma:** Clicar na aba PDF não mostra o PDF, ou mostra erro
**Root Cause (múltiplo):**
1. `sessionStore.uploadedPdfs[i].bytes` pode ser `undefined` se:
   - Usuário fez refresh (bytes não persistem no localStorage/IndexedDB)
   - Job foi criado em sessão anterior
2. Fallback `GET /api/jobs/{jobId}/pdf?index=N` pode retornar 404 se:
   - Job expirou via TTL (Epic 11.9 implementou TTL)
   - Job não está em `_pipeline_jobs` dict (restart do servidor)
3. Sem mensagem de erro visual — falha silenciosa
**Impacto:** Aba PDF inutilizável após refresh ou expiração de job

#### P5: Inspector mostra "—" para propriedades
**Arquivo:** `frontend/src/stores/inspectorStore.ts` + `backend/services/stages/pipeline_result.py`
**Sintoma:** Ao selecionar elemento, x/y/width/height/font aparecem como "—"
**Root Cause:**
- Story 11.5 fixou `initFromTree()` (inspector inicializa), MAS
- `TreeNode.properties` não tem `x`, `y`, `width`, `height` quando:
  - `document_structure.root` é construído sem bbox nos nodes
  - `pipeline_result.py::_build_tree()` não mapeia bbox → properties
- `ElementInspector.vue` lê `node.properties.x` → undefined → "—"
**Impacto:** Inspector não serve para nada — principal ferramenta de edição

---

### ALTOS — Degradam UX significativamente

#### P6: Snap desabilitado (toggle sem efeito)
**Arquivo:** `frontend/src/composables/useCanvasInteraction.ts`
**Sintoma:** Botão Snap ativado, mas elementos não alinham ao arrastar
**Root Cause:**
```typescript
function calcSnapLines(selectedNodeId: string): SnapLine[] {
  if (!editorStore.snapEnabled) return []
  // TODO: Implementar lógica real de snap
  return []  // ← STUB! Sempre retorna vazio
}

function snapToGrid(value: number): number {
  return Math.round(value / GRID_SIZE) * GRID_SIZE  // Implementado mas não chamado no drag
}
```
- `snapToGrid()` existe mas `onDrag()` não chama para aplicar snap
- `calcSnapLines()` é stub

#### P7: Coverage overlay vazio
**Arquivo:** `frontend/src/stores/coverageStore.ts` + `backend/services/stages/pipeline_result.py`
**Sintoma:** Botão "Cobertura" ativado, mas sem highlights visuais no canvas/PDF
**Root Cause:**
```typescript
// coverageStore tem:
overlayDataByLayout: Map<string, Record<'canvas'|'pdf', OverlayItemData[]>>
// Mas NUNCA é populado! Não há código em pipeline_result.py que gera OverlayItem[]
// CoverageOverlay.vue lê overlayDataByLayout → vazio → sem render
```
- Backend não envia coordenadas bbox por campo no resultado
- Frontend não tem como renderizar overlay sem bbox por campo

#### P8: Multi-layout switching perde estado
**Arquivo:** `frontend/src/stores/layout.ts`
**Sintoma:** Trocar de layout (dropdown) não preserva seleção/estado anterior
**Root Cause:**
- `setActiveLayout(id)` muda `activeLayoutId` mas não salva estado do layout anterior
- Sem snapshot de `templateStore`, `mappingStore`, `inspectorStore` por layout

#### P9: CanvasGuides sem colunas detectadas
**Arquivo:** `frontend/src/organisms/CanvasGuides.vue`
**Sintoma:** Guides só mostram margens e header/footer, sem guias de coluna
**Root Cause:**
- `columnPositions` sempre recebe `[]` (sem detecção automática)
- Backend não envia informação de colunas no `document_structure`

---

### MÉDIOS — Erros silenciosos / confiança baixa

#### P10: PDF bytes perdidos no refresh
**Arquivo:** `frontend/src/stores/session.ts`
**Sintoma:** Voltar ao editor após F5 = sessionStorage vazio, PDF perdido
**Root Cause:** `uploadedPdfs[].bytes` é `Uint8Array` em memória, não serializado para localStorage

#### P11: Race condition _eventQueue no AnalyzingPage
**Arquivo:** `frontend/src/pages/AnalyzingPage.vue`
**Sintoma:** Stages pulados se usuário faz retry
**Root Cause:** `_eventQueue` não é resetado entre tentativas; events do run anterior persistem

#### P12: Coverage calculation ignora tabelas/imagens
**Arquivo:** `backend/services/stages/pipeline_result.py`
**Sintoma:** Coverage sempre mostra apenas "fields" — tables/images/charts = 0
**Root Cause:**
```python
coverage_entry = {
    "fields": {"mapped": mapped, "total": total},
    "tables": {"mapped": 0, "total": 0},   # ← Hardcoded zero
    "images": {"mapped": 0, "total": 0},   # ← Hardcoded zero
    "charts": {"mapped": 0, "total": 0},   # ← Hardcoded zero
}
```

#### P13: Template matching não dispara
**Arquivo:** Frontend + Backend
**Sintoma:** Badge "Sem template" sempre presente
**Root Cause:** Não há lógica de seleção/sugestão de template no pipeline result

#### P14: Gaps de teste — código não coberto por testes
**Arquivos:** Vários
**Root Cause:**
- Sem testes para `_bbox_to_layout()` em template_draft.py
- Sem testes para coverage com field_tree=None
- Sem testes para overlay data generation
- Sem testes para multi-layout switching

---

## Fluxo de Dados Completo (Atual vs Desejado)

### Atual (quebrado)
```
PDF → Pipeline (28 stages) → result_json
  ↓
result_json.template_draft.html = "<div class='field-group'>texto</div>"
  (sem position:absolute, sem dimensões, sem font)
  ↓
HTMLCanvas.vue → iframe com HTML sem layout
  = tela em branco com texto espalhado
```

### Desejado
```
PDF → Pipeline (28 stages) → result_json
  ↓
result_json.template_draft.html = "<div style='position:absolute;left:Xpx;top:Ypx;width:Wpx;height:Hpx;font-family:F;font-size:Spt'>texto</div>"
  ↓
HTMLCanvas.vue → iframe com HTML posicionado = BOLETO VISUAL
  + Coverage overlay verde/vermelho nos campos
  + Campos listados no painel lateral com binding XSD
  + Inspector mostrando x,y,w,h,font de cada elemento
```

---

## Arquitetura de Solução

### Backend (pipeline_result.py + template_draft.py)

```
template_draft.py::_generate_html()
  HOJE: <div class="field-group"><span data-bind="text: path">valor</span></div>

  DEVE SER:
  <div class="page" data-page="1"
       style="position:relative;width:794px;height:1123px;overflow:hidden">
    <span
      data-node-id="block-uuid"
      data-bind="text: customer.name"
      data-xsd-path="customer.name"
      data-status="mapped"
      style="position:absolute;
             left:{bbox.x0 * SCALE_X}px;
             top:{bbox.y0 * SCALE_Y}px;
             width:{(bbox.x1-bbox.x0) * SCALE_X}px;
             height:{(bbox.y1-bbox.y0) * SCALE_Y}px;
             font-family:{font_name};
             font-size:{font_size}pt;
             white-space:nowrap;overflow:hidden">
      {text}
    </span>
    ...
  </div>
```

### Frontend (mapping.ts, coverageStore.ts, useCanvasInteraction.ts)

```
mapping.ts::loadPipelineFields()
  DEVE: Transformar FieldMappingEntry[] → FieldNavItem[]
  FieldNavItem = {id, name, path, status, bbox, pageNum, xsdPath, confidence}

coverageStore.ts::loadCoverageWithOverlay()
  DEVE: Receber overlayItems por layout
  OverlayItem = {nodeId, bbox, status, target:'canvas'|'pdf'}

useCanvasInteraction.ts::onDrag()
  DEVE: Aplicar snapToGrid() ao soltar elemento
  + Calcular snap lines contra vizinhos (mesma linha Y, mesma coluna X)
```

---

## Stories do Epic 12

| ID | Título | Prioridade | Tipo | Agente |
|----|--------|-----------|------|--------|
| **12.11** | **field_matching: table_cell filtrado — CAUSA RAIZ de 0% boletos** | **Crítica P0** | bug | @dev |
| 12.1 | Canvas: posicionamento absoluto via bbox | Crítica | feat | @dev |
| 12.2 | Coverage: Stage 29 silent fail + intersecção vazia | Crítica | bug | @dev |
| 12.3 | Campos: popular fieldNavItems no mapping store | Crítica | bug | @dev |
| 12.4 | PDF Tab: persistência e fallback robusto | Crítica | bug | @dev |
| 12.5 | Inspector: propriedades bbox no pipeline result | Alta | bug | @dev |
| 12.6 | Coverage Overlay: gerar overlayData no pipeline | Alta | feat | @dev |
| 12.7 | Snap: implementar lógica real no canvas interaction | Alta | feat | @dev |
| 12.8 | Template: seleção automática + badge dinâmico | Média | feat | @dev |
| 12.9 | Multi-layout: preservar estado por layout | Média | feat | @dev |
| 12.10 | Testes: cobrir gaps críticos de cobertura | Média | test | @qa |

---

## Critério de Sucesso do Epic 12

Ao final deste epic, ao carregar o arquivo `Corporate.Boleto.Convenio.pdf`:

1. **Canvas** mostra o documento com layout visual similar ao PDF original
2. **Cobertura** mostra % real de campos identificados (não 0%)
3. **Campos** lista todos os campos extraídos com status mapped/unmapped
4. **PDF tab** mostra o PDF sem erro, antes e depois do refresh
5. **Inspector** mostra x, y, width, height, font para cada elemento selecionado
6. **Coverage overlay** mostra highlights verde/vermelho ao ativar Cobertura
7. **Snap** alinha elementos ao grid ao arrastar

---

## Referências

- Screenshot: `D:\Downloads\Captura de tela 2026-03-20 112618.png`
- PDF Original: `D:\Downloads\Corporate.Boleto.Convenio.pdf`
- Branch Atual: `feature/epic-11-estabilizacao-editor`
- Análise completa: Orion / 2026-03-20

---

*Epic criado por @aios-master (Orion) via análise direta do codebase — 2026-03-20*
