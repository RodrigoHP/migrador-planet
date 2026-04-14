# ADR-029: Estratégia de Re-render do Canvas após Mutações no templateStore

**Status:** Accepted
**Data:** 2026-04-07
**Autor:** @dev Dex (spike Story 29.1)
**Impacta:** Stories 29.2, 29.3

---

## Contexto

O `HTMLCanvas.vue` exibe o template HTML em um `<iframe>`. Quando o operador edita propriedades no Inspector, arrasta elementos no Canvas ou modifica a árvore de estrutura, o `templateStore` é atualizado corretamente — mas o HTML no iframe permanece inalterado. O loop visual de edição está quebrado (GAPs 1, 2, 3 do gap-analysis-frontend-v3.md).

É necessário definir como propagar mutações do `templateStore` para o Canvas visual.

---

## Opções Consideradas

### Opção A — Trigger Backend (round-trip HTTP)
Mutação no `templateStore` → debounce → `POST /generate` ou endpoint novo → backend regenera HTML → `generationStore.templateDraft` atualizado → watcher existente no Canvas dispara.

**Análise dos endpoints disponíveis:**

| Endpoint | Tipo | Input | Output | Usável? |
|----------|------|-------|--------|---------|
| `POST /generate` | Async (retorna `jobId`) | `mappingFields` (não documentTree) | HTML via polling | ❌ Não serve — async, input errado |
| `POST /analyze` | Async SSE (1-30 min) | PDF + XSD | Full pipeline | ❌ Não serve — muito pesado |
| `POST /preview` | Sync | `jobId` (não documentTree) | HTML completo | ❌ Não serve — lê job cache, não re-gera |
| `POST /auto-fix` | Async + LLM | Tree patches | Fixes | ❌ Não serve |

**Conclusão:** Não existe endpoint synchronous que aceite `documentTree` e retorne HTML. Criar um exigiria novo backend work fora do escopo do Epic 29.

---

### Opção B — Geração HTML Completa no Frontend
Implementar motor de geração HTML em TypeScript que observe `templateStore` e regenere todo o HTML a cada mutação.

**Análise:**
- `generateHtmlFromStore()` já existe em `codeStore.ts` (linha 61) mas é um **scaffold simplificado** (apenas estrutura header/flow/footer com comentários, sem posicionamento absoluto dos elementos)
- Reimplementar a lógica completa do `stage5_template_generation.py` em TypeScript seria ~3-5x o escopo estimado do epic

**Conclusão:** Válida para futuro mas fora do escopo do MVP.

---

### Opção C (escolhida) — HTML String Patching no Frontend

Patch cirúrgico do HTML existente em `generationStore.templateDraft.html` após cada mutação do `templateStore`.

**Base técnica:**
1. O HTML gerado pelo `stage5_template_generation.py` já tem `data-node-id="{nodeId}"` em todos os elementos bindáveis
2. Posições são inline: `style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px"`
3. `injectTemplateCSS()` em `codeStore.ts` (linha 130) já usa o mesmo padrão — patch direto em `generationStore.templateDraft.css`
4. O watcher em `HTMLCanvas.vue` (linha 521) já observa `generationStore.templateDraft` e dispara full re-render

**Fluxo:**
```
templateStore.moveElement(id, dx, dy)
  → atualiza node.properties.x, node.properties.y  [já funciona]
  → chama generationStore.patchNodePosition(id, x, y, w, h)  [NOVO]
    → regex replace em templateDraft.html: data-node-id="${id}" → style atualizado
  → HTMLCanvas watcher dispara → iframe re-renderiza  [já funciona]
```

---

## Decisão

**Opção C — HTML String Patching** (variante da Opção B, escopo mínimo)

### Justificativa

| Critério | Opção A | Opção B | Opção C (escolhida) |
|----------|---------|---------|---------------------|
| Esforço | Alto (novo endpoint backend) | Alto (motor HTML completo) | **Baixo (regex patch)** |
| Latência | 200-800ms (network) | 0ms | **0ms** |
| Consistência com backend | Alta | Baixa (divergência) | **Alta (HTML original preservado)** |
| Cobertura de mutações | Total | Total | **Parcial (move/resize/text — MVP)** |
| Risco de regressão | Médio | Alto | **Baixo** |
| Padrão já existente | Não | Parcial | **Sim (`injectTemplateCSS`)** |

### Limitações conhecidas (aceitas para MVP)

- **Mutações estruturais** (adicionar/remover nós): o patch não se aplica — canvas mostrará HTML desatualizado até o próximo `loadTemplateDraft` do backend. Aceitável no MVP pois estas operações são menos frequentes.
- **Nós sem `data-node-id`**: elementos do tipo `rect`, `line`, `image`, `chart` no stage5 não têm `data-node-id`. Para esses, o patch não atualizará o visual. Será documentado no Dev Notes de 29.2.

---

## Interface de Integração

### Nova função em `generation.ts`

```typescript
// frontend/src/stores/generation.ts

/**
 * Patcha a posição/tamanho de um nó no templateDraft.html existente.
 * Busca por data-node-id="${nodeId}" e substitui o atributo style com as novas coordenadas.
 * Padrão análogo a injectTemplateCSS() em codeStore.ts.
 */
patchNodeGeometry(nodeId: string, x: number, y: number, width: number, height: number): void {
  if (!this.templateDraft?.html) return
  const newStyle = `position:absolute;left:${x}px;top:${y}px;width:${width}px;height:${height}px`
  // Regex: encontra data-node-id="nodeId" ... style="..." e substitui o style
  const regex = new RegExp(
    `(data-node-id="${escapeRegex(nodeId)}"[^>]*?)style="[^"]*"`,
    'g'
  )
  const patched = this.templateDraft.html.replace(regex, `$1style="${newStyle}"`)
  if (patched !== this.templateDraft.html) {
    this.templateDraft = { ...this.templateDraft, html: patched }
  }
}

/**
 * Patcha o conteúdo textual de um nó no templateDraft.html.
 * Busca por data-node-id="${nodeId}">...texto...</span> e substitui o conteúdo.
 */
patchNodeText(nodeId: string, text: string): void {
  if (!this.templateDraft?.html) return
  const regex = new RegExp(
    `(<[^>]*data-node-id="${escapeRegex(nodeId)}"[^>]*>)[^<]*(</[^>]+>)`,
    'g'
  )
  const patched = this.templateDraft.html.replace(regex, `$1${escapeHtml(text)}$2`)
  if (patched !== this.templateDraft.html) {
    this.templateDraft = { ...this.templateDraft, html: patched }
  }
}
```

### Trigger em `templateStore.ts`

```typescript
// Após moveElement() e resizeElement():
// 1. Atualizar node.properties (já feito)
// 2. Chamar generationStore.patchNodeGeometry(id, newX, newY, newW, newH)

// Após updateNodeProperty(nodeId, 'text', value):
// 1. Atualizar node.properties (já feito)
// 2. Chamar generationStore.patchNodeText(nodeId, value as string)
```

### Watcher existente em `HTMLCanvas.vue` (linha 521)

```typescript
// Não requer mudança — já observa generationStore.templateDraft
watch(
  () => generationStore.templateDraft,
  async () => { /* full re-render já implementado */ }
)
```

### Store que é atualizado

`generationStore.templateDraft.html` (patch direto, sem debounce — operação síncrona e barata)

---

## Consequências

### Positivas
- Re-render após `moveElement`/`resizeElement` em tempo real (0ms latência)
- Sem novo backend endpoint (zero scope creep no backend)
- Consistência com HTML original do backend (apenas coordenadas são atualizadas)
- Padrão de patch já validado por `injectTemplateCSS()`

### Negativas / Mitigações
- Nós sem `data-node-id`: canvas não atualiza visualmente para esses tipos. **Mitigação:** documentar tipos afetados, aceito para MVP
- Mutações estruturais (add/remove): canvas fica desatualizado. **Mitigação:** aceito para MVP — operações estruturais são raras em sessão de edição normal
- Regex frágil para HTML muito complexo: **Mitigação:** testar com Boleto Bancário (maior template real disponível)

---

## Arquivos impactados

| Arquivo | Mudança |
|---------|---------|
| `frontend/src/stores/generation.ts` | Adicionar `patchNodeGeometry()` e `patchNodeText()` |
| `frontend/src/stores/templateStore.ts` | `moveElement()`, `resizeElement()`, `updateNodeProperty()` chamam funções de patch |
| `frontend/src/organisms/HTMLCanvas.vue` | Sem mudança (watcher já existe) |

---

## Referências

- Gap analysis: `docs/architecture/gap-analysis-frontend-v3.md` (GAPs 1, 2, 3)
- Epic: `docs/stories/epic-29-editor-loop-closure.md`
- Padrão análogo: `frontend/src/stores/codeStore.ts` linha 130 (`injectTemplateCSS`)
- Stage5 HTML format: `backend/services/stages/stage5_template_generation.py` linha 401
