# ADR-030: Estratégia de Superfície de Interação do Editor Visual

**Status:** In Analysis
**Data:** 2026-04-10
**Autores:** @architect Aria + @ux-design-expert Uma + @aios-master Orion
**Contexto:** Sessão de análise estratégica — conversa completa documentada aqui

---

## Contexto do Produto

O migrador-planet é um editor WYSIWYG de templates de documento. O fluxo é:

```
PDF/XSD original
    ↓ pipeline inteligente
HTML/CSS gerado automaticamente (Knockout.js + layout flow em inches)
    ↓ editor visual
Usuário ajusta até ficar idêntico ao PDF
    ↓ export
HTML/CSS final pronto para o motor de renderização PDF
```

**Usuário alvo:** Não-desenvolvedor. Analista de negócio que conhece o documento mas não sabe HTML/CSS.

**Output final obrigatório:** HTML/CSS com estrutura específica — Knockout.js para data binding, CSS em inches (A4: `8.27in × 10.69in`), paginação dinâmica via JS customizado, `##TEMPLATE_DATA##` para injeção de dados.

Exemplos reais em `docs/exemplos/` — 40+ templates de referência.

---

## O Problema

O editor tem dois subsistemas com papéis distintos que estão **incorretamente acoplados**:

```
Subsistema 1 — Lógica de negócio (BEM construído)
  templateStore, mappingStore, coverageStore, layoutStore
  useAlignmentTools, useExport, useClipboard, useGrouping
  field mapping XSD→Knockout, undo/redo, export ZIP
  → Independente de framework. Sólido.

Subsistema 2 — Superfície de interação (PROBLEMA)
  iframe + CanvasSelectionOverlay + postMessage bridge
  → Cria fronteira de documento separado.
  → Torna clique e drag estruturalmente frágeis.
```

### Bugs estruturais (não pontuais) causados pelo iframe

| Bug | Causa raiz | Natureza |
|-----|-----------|---------|
| Click não registra | postMessage assíncrono entre documentos | Estrutural |
| Drag cancela no meio | `onMouseLeave` cruza fronteira do iframe | Estrutural |
| CSS `:has()` frágil | Workaround para `pointer-events` sem fronteira | Estrutural |
| Bugs futuros de interação | Qualquer evento que atravessa a fronteira | Estrutural |

**Conclusão:** Consertar esses bugs individualmente é whack-a-mole. A fronteira do iframe é a fonte, não sintomas isolados.

---

## Inventário do Editor Atual

O editor tem significativo investimento. Funcionalidades implementadas:

### Interação Visual
| Feature | Composable/Componente | Status |
|---------|----------------------|--------|
| Drag com snap magnético + grid + colunas PDF | `useCanvasInteraction.ts` | Funcional mas bugado |
| Resize 8 handles com snap | `useCanvasInteraction.ts` | Funcional mas bugado |
| Click / seleção | `CanvasSelectionOverlay.vue` + postMessage | Bugado |
| Multi-select (Ctrl/Shift) | `useCanvasInteraction.ts` | Funcional |
| Zoom 50-125% + lazy-load páginas | `useCanvas.ts` | Funcional |
| Keyboard shortcuts (Arrow, Ctrl+C/V/D/Z, Delete) | `useCanvasKeyboard.ts` | Funcional |

### Features Únicas do Produto
| Feature | Componente | Status |
|---------|-----------|--------|
| Field mapping XSD → data-bind | `useCanvasDrag.ts` + `mappingStore.ts` | Funcional |
| Coverage overlay (bound/unbound/unconfirmed) | `CoverageOverlay.vue` | Funcional |
| Sync view canvas + PDF lado a lado | `SyncView.vue` | Funcional |
| Diff viewer A vs B | `DiffViewer.vue` | Funcional |
| Export ZIP (index.html + css + js + assets) | `useExport.ts` | Funcional |
| Auto Fix via IA | `autoFixStore.ts` | Funcional |
| Undo/redo command-based (200 steps) | `templateStore.ts` | Funcional |
| Alignment + distribute (6 operações) | `useAlignmentTools.ts` | Funcional |
| Copy/paste/duplicate | `useClipboard.ts` | Funcional |
| Group/ungroup elementos | `useGrouping.ts` | Funcional |
| Layer order (z-index) | `useLayerOrder.ts` | Funcional |
| Inspector panel (5 tipos especializados) | `InspectorPanel.vue` | Funcional |
| Structure tree | `StructureTree.vue` | Funcional |
| Context menu | `CanvasContextMenu.vue` | Funcional |
| Monaco editor (HTML/CSS/JS) | `MonacoTabsInner.vue` | Funcional |
| Hierarchy popup | `HierarchyPopup.vue` | Funcional |

**Total:** 20+ composables, 10+ stores, 30+ componentes.

---

## Opções Avaliadas

### Opção A — Fix cirúrgico dos bugs (iframe permanece)

Corrigir os 3 bugs específicos:
1. Listeners de drag no `document` em vez do overlay div
2. Remover CSS `:has()`, controlar `pointer-events` via estado reativo
3. Investigar e reforçar pipeline postMessage

**Prós:** Rápido (2-3 dias). Zero risco de regressão em features existentes.

**Contras:** Não resolve a causa raiz. Novos bugs de fronteira surgirão com novas features. Dívida técnica estrutural permanece.

**Veredito:** Band-aid. Não recomendado como estratégia final.

---

### Opção B — Shadow DOM (iframe substituído)

Trocar `<iframe srcdoc="...">` por `<div>` com Shadow Root attachado.

```javascript
// Hoje
<iframe srcdoc={pageHtml} sandbox="allow-same-origin allow-scripts" />

// Shadow DOM
const host = document.createElement('div')
const shadow = host.attachShadow({ mode: 'open' })
shadow.innerHTML = pageHtml  // CSS isolado, eventos DOM nativos
```

**O que resolve:**
- Eventos nativos — sem postMessage ✓
- Drag sem boundary — mouseleave não cancela ✓
- pointer-events simples — sem CSS `:has()` ✓
- Bugs futuros de fronteira — eliminados ✓

**Consideração crítica sobre Knockout.js:**

O `base.js` dos templates usa `document.querySelector()` e `document.body.appendChild()` extensivamente. Isso **não funciona** dentro de Shadow DOM.

**Solução:** Separar os dois modos explicitamente:

```
Modo Editor    → renderiza HTML estático sem executar JS
               → Shadow DOM funciona perfeitamente
               → usuário vê estrutura e placeholders

Modo Preview   → executa Knockout + paginação JS
               → mantém iframe sandboxado
               → usuário vê documento com dados reais
```

Essa separação é arquiteturalmente limpa e já existe conceitualmente no produto.

**Prós:** Resolve causa raiz. Preserva 95% do trabalho existente. 1-2 semanas de esforço.

**Contras:** Requer separação explícita Editor vs Preview. Knockout não executa no editor (aceitável — o editor mostra estrutura, não resultado final).

---

### Opção C — GrapesJS Document Builder

Usar GrapesJS como base do editor, substituindo a superfície de interação atual.

**O que GrapesJS entrega nativamente:**
- Drag/resize/snap battle-tested ✓
- Undo/redo built-in ✓
- Style Manager (painel CSS visual) ✓
- Block Manager (biblioteca de seções) ✓
- Trait Manager (propriedades customizadas por componente) ✓
- Export HTML/CSS ✓

**Problema de integração:**

GrapesJS usa seu próprio modelo interno (Component tree + CSS Rules). **Não é compatível com Pinia stores.** O `templateStore`, `mappingStore`, `coverageStore` precisariam ser reescritos ou bridgeados via eventos do GrapesJS.

**O que seria reaproveitado:**

| | Reaproveitamento |
|---|---|
| Backend completo (pipeline, XSD, export) | ✅ 100% |
| Export ZIP logic | ✅ ~60% (adaptação) |
| Field mapping logic | ✅ ~40% (reescrever para API GrapesJS) |
| Stores (templateStore, coverageStore, etc.) | ❌ incompatível |
| Sync view / Diff viewer | ❌ reconstruir do zero |
| Coverage overlay | ❌ reconstruir como plugin |
| Inspector panel especializado | ❌ reconstruir |
| Composables de canvas | ❌ não se aplica |

**Esforço realista:** 3-4 meses para paridade de features.

**Prós:** Experiência de interação superior. Base sólida para futuro. Cada nova feature do editor vem mais barata.

**Contras:** 3-4 meses de rebuild. Alto risco para primeiro produto. Perda de features únicas que levaram meses para construir.

---

## Análise de Viés

> **Preocupação legítima levantada:** o time pode estar defendendo o editor atual por viés de custo afundado — "temos muito aqui, não joga fora" — em vez de escolher a melhor estratégia.

**Resposta honesta do @architect:**

A pergunta correta não é "o que perdemos se trocarmos?" mas sim "se começássemos hoje, o que escolheríamos?"

```
Horizonte 3 meses (primeiro produto, validar mercado)
→ Shadow DOM. Produto funcionando rapidamente.

Horizonte 12 meses (produto validado, escalar)
→ GrapesJS. Investimento justificado por crescimento.
```

O trabalho existente **não é descartável** — o Subsistema 1 (lógica de negócio) é sólido e independente. O que está problemático é só o Subsistema 2 (superfície de interação), que é a menor parte do sistema.

---

## Decisão Recomendada

**Opção B — Shadow DOM, com interface de contrato limpa.**

Não apenas trocar iframe por Shadow DOM, mas aproveitar a mudança para criar uma **abstração explícita** da superfície de interação:

```typescript
// Contrato claro — independente de implementação
interface CanvasSurface {
  onElementClick(cb: (id: string, bbox: BoundingBox) => void): void
  onElementDrag(cb: (id: string, dx: number, dy: number) => void): void
  onElementResize(cb: (id: string, w: number, h: number) => void): void
  onElementHover(cb: (id: string | null) => void): void
  highlightElement(id: string, style: HighlightStyle): void
  clearHighlight(id?: string): void
  renderPage(html: string, css: string): void
  destroy(): void
}

// Implementações intercambiáveis
class ShadowDomSurface implements CanvasSurface { ... }   // agora
class GrapesJsSurface implements CanvasSurface { ... }    // futuro (v2)
```

Com essa interface, uma migração futura para GrapesJS é **semanas, não meses** — apenas trocar a implementação, não o contrato.

---

## Plano de Execução

### Fase 1 — Shadow DOM + interface limpa (2 semanas)

**Epic novo:** `Editor Surface Stabilization`

**Story 1:** Criar `CanvasSurface` interface e `ShadowDomSurface` implementação
- Trocar iframe por Shadow DOM
- Modo Editor: HTML estático sem JS
- Modo Preview: iframe sandboxado com Knockout

**Story 2:** Migrar `CanvasSelectionOverlay` para usar eventos nativos
- Remover postMessage listener
- Remover CSS `:has()` workaround
- Listeners de drag no `document`

**Story 3:** Testes de interação e validação
- Click, drag, resize em todos os tipos de nó
- Regressão de features existentes

### Fase 2 — Validar o produto (2-3 meses)

Com o editor funcionando de forma confiável:
- Descobrir o que realmente importa para o usuário
- Quais features são usadas? O que falta? O que é supérfluo?
- Coletar feedback de uso real

### Fase 3 — Decisão informada sobre GrapesJS (data aberta)

Com dados reais de uso, a decisão de migrar para GrapesJS é baseada em evidência, não em viés. Gatilhos que justificariam a migração:
- Novos tipos de interação que a superfície atual não suporta
- Produto validado e crescendo, justificando investimento de 3-4 meses
- Features de editor que GrapesJS entrega nativamente mas custariam caro custom

---

## Comparativo Final

| Critério | Fix bugs | Shadow DOM | GrapesJS |
|---------|---------|------------|---------|
| Tempo até funcionar | 2-3 dias | 2 semanas | 3-4 meses |
| Features preservadas | 100% | 95% | 20% |
| Resolve causa raiz | ❌ | ✅ | ✅ |
| Qualidade de interação | Baixa | Boa | Excelente |
| Risco | Baixo | Baixo-médio | Alto |
| Preparado para v2 | ❌ | ✅ (com interface) | ✅ |
| **Fase atual** | ❌ | **✅ RECOMENDADO** | ❌ |

---

## Referências

- Conversa de análise estratégica: 2026-04-10 (sessão completa)
- ADR-029: Estratégia de Re-render do Canvas (`adr-canvas-rerender-strategy.md`)
- Inventário do editor: exploração completa realizada em sessão (2026-04-10)
- Templates de referência: `docs/exemplos/` (40+ exemplos)
- GrapesJS Document Builder: ferramenta avaliada como referência de UX
- Agentes participantes: @aios-master (Orion), @ux-design-expert (Uma), @architect (Aria)

---

## Próximos Passos

Quando retornar a esta análise:

1. **Confirmar decisão** com o time — Shadow DOM é a direção?
2. **Abrir Epic** `Editor Surface Stabilization` via `@pm`
3. **Draft stories** via `@sm` (3 stories da Fase 1)
4. **Implementar** via `@dev` com foco na interface `CanvasSurface`
5. **Validar** interação com usuário real após Fase 1

**Critério de sucesso da Fase 1:**
> Usuário não-dev consegue clicar em qualquer elemento, arrastá-lo e redimensioná-lo sem bugs, em qualquer nível de zoom, sem treinamento.
