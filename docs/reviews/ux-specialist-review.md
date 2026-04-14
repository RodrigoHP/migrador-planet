# UX Specialist Review

**Reviewer:** @ux-design-expert (Uma)
**Date:** 2026-04-09
**Input:** `docs/prd/technical-debt-DRAFT.md` (Sections 3, 5, 6, 7) + `docs/frontend/frontend-spec.md`

---

## Debitos Validados

| ID | Debito | Severidade Original | Severidade Ajustada | Horas | Impacto UX | Design Review? | Notas |
|----|--------|---------------------|---------------------|-------|------------|----------------|-------|
| FE-001 | AnalyzingPage.vue 1,195 LOC | HIGH | HIGH | 8h | MEDIO -- usuarios nao veem, mas bugs no stepper/checkpoint impactam confianca | Nao | Extrair state machine para composable eh correto. Decomposicao de sub-views por estado (initializing, running, checkpoint, completed, failed) melhora testabilidade sem impacto visual. |
| FE-002 | HTMLCanvas.vue 913 LOC | HIGH | HIGH | 6h | ALTO -- canvas eh o core da experiencia do editor. Bugs aqui sao imediatamente visiveis | Nao | Concordo. Zoom/scroll, drag/drop, iframe mgmt e keyboard sao responsabilidades distintas. |
| FE-003 | session.ts 534 LOC (= SYS-006) | HIGH | HIGH | 4h | MEDIO -- impacta indiretamente via bugs de carregamento de dados | Nao | Confirmo duplicata com SYS-006. Manter FE-003 como primario. |
| FE-004 | Mixed store API styles | MEDIUM | LOW | 4h | BAIXO -- zero impacto no usuario. Pura questao de DX/consistencia interna | Nao | Rebaixo para LOW. Nao eh UX debt, eh DX debt. Ambos estilos funcionam identicamente para o usuario. |
| FE-005 | ConfidenceBadge duplicado | LOW | LOW | 1h | BAIXO -- pode causar inconsistencia visual se os dois componentes divergirem | Nao | Validado. Remover o atom e manter o molecule (que inclui ConfidenceBadgeMetric). |
| FE-006 | HelloWorld.vue presente | LOW | LOW | 5min | NENHUM | Nao | Validado trivial. |
| FE-007 | Sem barrel export composables | LOW | LOW | 30min | NENHUM | Nao | Nao eh UX debt. DX only. Validado. |
| FE-008 | Design tokens duplicados (CSS + Tailwind) | MEDIUM | MEDIUM | 2h | MEDIO -- drift causa inconsistencia visual real entre componentes | Sim | Risco concreto: dev altera valor em um lugar e esquece o outro. Manter MEDIUM. |
| FE-009 | CSS approach inconsistente | LOW | LOW | 2h | BAIXO -- inconsistencia eh interna, resultado visual eh o mesmo | Nao | Validado. |
| UX-001 | Sem toast store global | MEDIUM | MEDIUM | 3h | ALTO -- stores e services nao conseguem notificar o usuario de erros/sucesso. Ex: erro de save silencioso | Nao | Confirmado via codigo: `AppToast.vue` usa `defineExpose({ show, dismiss })`, acoplando toasts a hierarquia de componentes. |
| UX-002 | Sem responsive/mobile | LOW | LOW | 16h+ | BAIXO -- editor eh desktop-only by design (canvas, drag/drop, inspector panels). Paginas pre-editor (Login, Home, Upload) poderiam se beneficiar, mas escopo eh grande | Sim | Ver resposta na Secao 5. Manter como LOW mas com nota de que pode ser descartado do catalogo. |
| UX-003 | Sem dark mode | LOW | LOW | 16h+ | BAIXO -- nice-to-have, nao impacta funcionalidade | Sim | Ver resposta na Secao 5. Pode ser descartado do catalogo de debitos. |
| UX-004 | Sem skeleton screens no editor | LOW | LOW | 4h | MEDIO -- paineis vazios causam flash of empty content, mas o carregamento via pipeline result eh rapido | Nao | Validado. Baixa prioridade porque o editor so abre apos pipeline completo (dados ja disponiveis). |
| UX-005 | Emoji icons no toolbar | MEDIUM | MEDIUM | 2h | ALTO -- confirmado no codigo: TopToolbar usa emojis literais (mapa, setas, ima, regua). Renderiza diferente em Windows vs Mac vs Linux. Fonte inconsistente com restante do app que usa lucide-vue-next | Nao | Fix simples: substituir 4 emojis por icones lucide equivalentes. |
| A11Y-001 | Sem focus trap em modais | HIGH | HIGH | 4h | ALTO -- violacao WCAG 2.1 SC 2.4.3 (Focus Order). Usuarios de teclado/screen reader ficam presos ou perdidos | Nao | `@vueuse/core` v14.2.1 ja eh dependencia. `useFocusTrap` eh a abordagem recomendada. |
| A11Y-002 | Sem focus indicators customizados | MEDIUM | MEDIUM | 3h | MEDIO -- browser defaults sao suficientes na maioria dos casos, mas inconsistentes em backgrounds escuros (toolbar, inspector headers) | Sim | Recomendo focus ring com `outline: 2px solid var(--color-primary-600)` + offset. |
| A11Y-003 | Contraste Neutral-500 | MEDIUM | MEDIUM | 1h | MEDIO -- 4.48:1 vs 4.5:1 exigido. Margem pequena mas eh uma violacao tecnica de WCAG AA | Nao | Ver resposta na Secao 5 sobre cor substituta. |
| A11Y-004 | Alt texts ausentes | LOW | LOW | 2h | BAIXO -- impacta screen readers em contextos especificos (PDF viewer thumbnails, canvas placeholders) | Nao | Validado. |
| SEC-001 | v-html XSS em BibliotecaComponentList | HIGH | HIGH | 2h | ALTO -- XSS eh impacto direto no usuario. Confirmado: `v-html="item.previewHtml"` na linha 14 sem sanitizacao | Nao | DOMPurify eh a melhor abordagem (mais leve que iframe sandboxed, preserva estilos). |
| SEC-002 | dompurify vulneravel (transitiva) | MEDIUM | MEDIUM | 1h | BAIXO -- risco transitivo via monaco-editor, nao exposto diretamente ao usuario | Nao | Validado. |
| SEC-003 | Vite vulneravel | HIGH | HIGH | 30min | BAIXO -- dev-only, mas fix eh trivial | Nao | Validado. `npm audit fix` resolve. |
| PERF-001 | Sem tree virtualization | MEDIUM | MEDIUM | 8h | MEDIO -- depende do tamanho tipico dos documentos. Ver resposta na Secao 5 | Nao | Pode ser deprioritizado se docs tipicos <100 nodes. |
| PERF-002 | JSON.stringify undo snapshots (= SYS-022) | MEDIUM | MEDIUM | 6h | ALTO -- undo/redo eh operacao frequente no editor. Frame drops durante undo = experiencia degradada perceptivel | Nao | Confirmo duplicata com SYS-022. |
| PERF-003 | Monaco bundle size | LOW | LOW | 2h | BAIXO -- impacta initial load mas Monaco ja eh chunked separadamente | Nao | Validado. |
| TEST-001 | Sem framework E2E (= SYS-020) | HIGH | HIGH | 16h | ALTO (indireto) -- sem E2E, regressoes em flows criticos passam despercebidas e impactam usuario | Nao | Confirmo duplicata com SYS-020. |
| TEST-002 | Atoms 88% sem testes | MEDIUM | MEDIUM | 6h | MEDIO -- atoms sao base da UI, regressao em Button ou ProgressBar cascateia | Nao | Validado. |
| TEST-003 | Molecules 55% sem testes | MEDIUM | MEDIUM | 12h | MEDIO -- similar a TEST-002 | Nao | Validado. |
| TEST-004 | LoginPage sem testes | LOW | LOW | 2h | BAIXO -- flow simples (redirect to Supabase OAuth) | Nao | Validado. |

---

## Debitos Removidos (False Positives / Not UX)

Nenhum debito removido. Todos os 26 debitos frontend da Secao 3 do DRAFT sao legitimos, embora FE-004 tenha sido rebaixado de MEDIUM para LOW por ser puramente DX sem impacto UX.

---

## Debitos Adicionados

| ID | Debito | Severidade | Impacto UX | Horas | Design Review? | Fonte |
|----|--------|-----------|------------|-------|----------------|-------|
| UX-006 | **Sem error boundary global** -- `app.config.errorHandler` ausente em `main.ts`. Erro nao capturado = tela em branco sem feedback ao usuario. Parcialmente coberto por SYS-012 mas o impacto UX merece destaque proprio. | HIGH | ALTO -- usuario perde todo o trabalho sem explicacao | 4h | Nao | Cross-ref SYS-012, validado no frontend-spec |
| UX-007 | **Sem confirmacao de saida com alteracoes pendentes** -- Nao ha `beforeunload` handler ou rota guard para prevenir perda de trabalho ao fechar aba/navegar. Editor complexo sem "unsaved changes" dialog. | HIGH | ALTO -- perda de dados do usuario | 2h | Nao | Novo, identificado na analise cross-cutting |
| UX-008 | **Console.log em producao** -- 10 chamadas em 6 arquivos de producao (SYS-009). Do ponto de vista UX, poluicao de console expoe internals ao usuario tecnico e sugere falta de polimento. | LOW | BAIXO | 2h | Nao | Cross-ref SYS-009 |
| UX-009 | **Sem indicador de loading em operacoes de save/export** -- Export trigger no TopToolbar nao mostra estado de progresso entre click e download completo. | MEDIUM | MEDIO -- usuario nao sabe se export esta em andamento | 2h | Nao | Novo, identificado via analise de TopToolbar |
| UX-010 | **Sem mensagem de erro contextual em upload** -- File validation errors em UploadPage sao genericas. Poderiam informar tipo esperado, tamanho maximo, e acao sugerida. | LOW | BAIXO -- funcional mas melhoravel | 2h | Nao | Novo, identificado via frontend-spec Sec 5.2 |

---

## Cross-Cutting Review

### CC-004: Oversized Components / God Objects

**Validacao UX:** CONCORDO com a identificacao. Do ponto de vista UX, os componentes oversized afetam a experiencia indiretamente:

- **FE-001 (AnalyzingPage):** Risco alto de bugs no stepper/checkpoint UX. A pagina de analise eh o "momento de espera" do usuario -- bugs aqui causam abandono. Recomendo decomposicao em sub-componentes por estado (`AnalyzingInitializing`, `AnalyzingRunning`, `AnalyzingCheckpoint`, `AnalyzingCompleted`, `AnalyzingFailed`), cada um com seu template e logica isolados.

- **FE-002 (HTMLCanvas):** Risco critico. O canvas eh onde o usuario passa 90% do tempo. Code tangling entre zoom, scroll, drag e keyboard torna dificil debugar problemas de interacao. Recomendo: `useCanvasZoom`, `useCanvasDrag` (ja existe parcialmente), `useCanvasIframe` como composables separados.

- **FE-003/SYS-006 (session.ts):** A refatoracao nao afeta UX diretamente, mas o `loadFromPipelineResult` monolitico eh a ponte entre pipeline e editor -- erros aqui causam "editor carrega com dados incompletos" que eh UX-degradante.

**Impacto UX consolidado:** MEDIO-ALTO. A decomposicao reduz probabilidade de bugs user-facing em areas criticas.

### CC-005: Undo/Redo Performance

**Validacao UX:** CONCORDO e ELEVO a prioridade. Undo/redo eh uma das operacoes mais frequentes em qualquer editor visual. O padrao atual (JSON.stringify full tree) causa:

1. **Frame drops perceptiveis** durante Ctrl+Z/Y em documentos com 50+ elementos
2. **Limite artificial de 20 snapshots** que pode ser insuficiente para sessoes longas de edicao
3. **GC pauses** que se manifestam como micro-freezes durante edicao contìnua

**Recomendacao:** Command pattern com deltas (armazenar apenas as mudancas, nao a arvore completa). Isso permite undo stack ilimitado com footprint de memoria constante. Alternativa mais simples: structural sharing via Immer.

---

## Respostas ao Architect

### 1. FE-001: AnalyzingPage decomposition

**Recomendacao: composable + sub-componentes.**

- State machine como composable `useAnalyzingStateMachine()` -- nao como store, porque o estado eh local da pagina (nao compartilhado com outros componentes).
- Cada estado (initializing, running, checkpoint, completed, failed) como sub-componente proprio renderizado via `<component :is="currentStateComponent">`.
- O composable expoe `currentState`, `transition(event)`, `canTransition(event)`.
- Isso reduz AnalyzingPage de ~1,195 LOC para ~200 LOC (orquestracao + router puro).

### 2. FE-002: HTMLCanvas decomposition

**Recomendacao: composables para logica, sub-componentes para rendering.**

| Responsabilidade | Extrair para | Tipo |
|-----------------|-------------|------|
| Zoom/scroll | `useCanvasZoom` composable | Logica (ja parcialmente existe) |
| Drag/drop | `useCanvasDrag` composable | Logica |
| Iframe lifecycle | `useCanvasIframe` composable | Logica + DOM |
| Keyboard shortcuts | `useCanvasKeyboard` composable | Logica (ja existe) |
| Page rendering | `CanvasPage.vue` sub-componente | Rendering |
| Selection overlay | `CanvasSelectionOverlay.vue` sub-componente | Rendering (ja existe) |

Target: HTMLCanvas.vue reduzido a ~300 LOC (composicao de composables e sub-componentes).

### 3. UX-001: Toast store global

**Recomendacao: toast store + suporte a acao.**

- Criar `useToastStore` Pinia store com API: `show(message, variant, options?)`, `dismiss(id)`.
- `options` deve suportar: `action?: { label: string, callback: () => void }` para toast com acao (ex: "Undo" apos delete).
- `duration?: number` (default 4000ms, 0 = persistente).
- O `AppToast` atual ja tem a UI correta -- apenas precisa consumir do store em vez de `defineExpose`.
- Notification center (lista de historico) NAO eh necessario neste momento. Toasts sao suficientes para o tipo de aplicacao (editor).
- Inline alerts devem continuar sendo usados para erros persistentes (como o `ErrorCard` na AnalyzingPage).

### 4. UX-002 + UX-003: Mobile e Dark mode

**Mobile (UX-002):** O editor eh desktop-only by design. Canvas com drag/drop, inspector panels, e Monaco editor nao sao viaveis em mobile. Recomendo:
- **MANTER no catalogo como LOW** mas marcar como "deferred - desktop-only product decision"
- **Quick win:** tornar Login, Home, e Upload responsivos (3-4h) como melhoria separada, sem tocar no editor

**Dark mode (UX-003):** Recomendo **REMOVER do catalogo de debitos** para este produto. Razoes:
- Custo alto (16h+ para 136 componentes)
- Editor visual de templates PDF tem forte dependencia de cores precisas (preview deve refletir output impresso)
- Dark mode em editor de documentos pode confundir a percepcao de cores dos templates
- Nao ha demanda reportada de usuarios

### 5. A11Y-001: Focus trap

**Confirmo `useFocusTrap` do `@vueuse/core` (v14.2.1, ja instalado).** Razoes:
- Zero dependencias adicionais
- API composable nativa Vue 3
- Suporta `returnFocusOnDeactivate` (essencial para modais)
- Suporta `allowOutsideClick` (util para modais com overlay dismissivel)

`vue-focus-lock` seria alternativa aceitavel, mas adiciona dependencia desnecessaria quando `@vueuse/core` ja esta no projeto.

**Implementacao:** Criar composable wrapper `useModalFocusTrap(modalRef)` que encapsula `useFocusTrap` + `onMounted/onBeforeUnmount` lifecycle, e aplicar nos 4 modais identificados.

### 6. A11Y-003: Neutral-500 ajuste

**Recomendacao: Neutral-600 (#525252).**

| Cor | Hex | Contraste em branco | WCAG AA | Uso |
|-----|-----|---------------------|---------|-----|
| Neutral-500 (atual) | #737373 | 4.48:1 | FAIL | Hint text, timestamps |
| **Neutral-600** | **#525252** | **7.1:1** | **PASS AAA** | Recomendado |
| Neutral-550 (custom) | #636363 | 5.5:1 | PASS AA | Alternativa mais sutil |

7.1:1 NAO eh excessivo para hint text. WCAG AAA exige 7:1, e hint text eh frequentemente lido por usuarios com baixa visao. Neutral-600 eh a escolha correta -- mantém hierarquia visual (mais leve que o body text em Neutral-800/900) enquanto passa todos os niveis de WCAG.

### 7. PERF-001: Tree virtualization

**Contexto de producao:** Documentos tipicos do Planet Express sao faturas, boletos, e relatorios com 20-80 elementos. Documentos complexos (tabelas grandes, multi-pagina) podem chegar a 150-200 nodes.

**Recomendacao:** Deprioritizar para MEDIUM-LOW. O threshold de 200+ nodes citado no debito eh raro mas possivel. Recomendo:
- Monitorar: adicionar `performance.mark` no render da StructureTree para medir tempo real
- Trigger: se render time >100ms em >5% dos docs, implementar virtualizacao
- Implementacao futura: `@tanstack/vue-virtual` (ja recomendado no DRAFT)

### 8. SEC-001: v-html em BibliotecaComponentList

**DOMPurify eh a abordagem recomendada**, nao iframe sandboxed. Razoes:
- Preview de componente precisa herdar estilos do contexto (fontes, cores, spacing) -- iframe isolaria isso
- DOMPurify com config restritiva (`ALLOWED_TAGS: ['div', 'span', 'p', 'table', 'tr', 'td', 'th', 'img', 'svg', 'path']`) remove scripts sem perder layout
- Performance: DOMPurify eh sync e leve vs iframe que requer document creation
- Nota: DOMPurify ja seria necessario de qualquer forma para SEC-002 (upgrade da versao transitiva do monaco)

### 9. FE-004: Padronizacao de store API

**Composition API eh a recomendacao**, mas com ressalvas:
- Risco de regressao: BAIXO se cada store for migrado individualmente com testes existentes (stores tem ~100% coverage)
- Prioridade: LOW -- nao ha impacto funcional, ambos estilos coexistem bem no Pinia 3
- Abordagem: migrar por oportunidade (ao tocar um store para outra task), nao como iniciativa dedicada
- **Rebaixei para LOW na tabela de validacao** por este motivo

### 10. TEST-002 + TEST-003: Prioridade de testes

**Atoms prioritarios (por frequencia de uso e risco):**
1. `Button` -- usado em toda a app, suporta variants/loading/disabled
2. `ProgressBar` -- usado na AnalyzingPage, rendering condicional
3. `ColorPicker` -- interacao complexa (input + preview)
4. `ConfidenceBadge` -- logica de threshold/variants

**Molecules prioritarios (por complexidade e impacto):**
1. `InspectorField` -- base de todo o inspector panel
2. `InspectorInput` / `InspectorSelect` -- inputs especializados
3. `BindingEditor` -- logica de binding complexa
4. `ContextMenu` -- interacao keyboard + mouse
5. `BorderEditor` -- inputs compostos (4 lados + unidade)

Criterio: priorizar componentes com (a) logica condicional interna, (b) eventos/emits criticos, (c) uso em areas core do editor.

---

## Recomendacoes de Design

### 1. Error Boundary UX Pattern

Para UX-006 (error boundary ausente), recomendo:
- `app.config.errorHandler` captura erro e exibe `ErrorRecoveryOverlay` (full-screen overlay com mensagem amigavel, botao "Recarregar" e botao "Reportar")
- Persistir estado do editor em IndexedDB a cada 30s (auto-save) para que reload recupere trabalho
- Mostrar "Recuperamos seu trabalho" toast apos reload com dados recuperados

### 2. Unsaved Changes Guard

Para UX-007 (sem confirmacao de saida):
- `beforeunload` event listener quando `templateStore.isDirty` == true
- Vue Router `beforeEach` guard com dialog "Tem alteracoes nao salvas. Deseja sair?"
- Visual: indicador sutil no titulo da pagina (ponto ou asterisco) quando ha mudancas pendentes

### 3. Emoji to Icon Migration (UX-005)

Mapeamento de substituicao para TopToolbar:

| Emoji atual | Significado | Icone lucide recomendado |
|-------------|-----------|--------------------------|
| mapa | Field mapping overlay | `Map` |
| setas | Sync view | `ArrowLeftRight` |
| ima | Snap to grid | `Magnet` |
| regua | Rulers/guides | `Ruler` |

### 4. Toast Store Architecture (UX-001)

```
useToastStore (Pinia)
  state: toasts: ToastItem[]
  actions: show(msg, variant, opts?), dismiss(id)
  
AppToast.vue
  setup: const store = useToastStore()
  watch: store.toasts -> render stack
  
Any store/service:
  const toast = useToastStore()
  toast.show('Salvo com sucesso', 'success')
  toast.show('Erro ao exportar', 'error', { action: { label: 'Retry', cb: retryExport } })
```

---

## Ordem de Resolucao Recomendada (UX perspective)

Priorizada por impacto no usuario final, com dependencias respeitadas.

### Sprint 1 -- Quick Wins de Seguranca e Acessibilidade (9.5h)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 1 | SEC-003 | Vite patch | 0.5h | Fix trivial, risco de seguranca dev |
| 2 | SEC-001 | v-html XSS | 2h | Risco de seguranca user-facing |
| 3 | A11Y-001 | Focus trap em modais | 4h | Violacao WCAG, fix independente |
| 4 | A11Y-003 | Neutral-500 -> Neutral-600 | 1h | Violacao WCAG, 1 linha de CSS |
| 5 | UX-005 | Emoji -> lucide icons | 2h | Inconsistencia visual cross-platform |

### Sprint 2 -- Resiliencia e Notificacoes (11h)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 6 | UX-007 | Unsaved changes guard | 2h | Prevencao de perda de dados |
| 7 | UX-006 | Error boundary global | 4h | Prevencao de tela branca |
| 8 | UX-001 | Toast store global | 3h | Habilita notificacoes de stores |
| 9 | UX-009 | Loading indicator export | 2h | Feedback em operacao critica |

### Sprint 3 -- Refatoracao de Componentes Core (18h)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 10 | FE-003 | session.ts refactor | 4h | Precede FE-001, reduz God Object |
| 11 | FE-001 | AnalyzingPage decomposicao | 8h | Componente mais oversized |
| 12 | FE-002 | HTMLCanvas decomposicao | 6h | Core do editor |

### Sprint 4 -- Performance e Testes (22h)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 13 | PERF-002/SYS-022 | Undo/redo command pattern | 6h | Performance perceptivel no editor |
| 14 | TEST-001/SYS-020 | E2E framework + smoke tests | 16h | Safety net para tudo acima |

### Sprint 5 -- Polish e Consistencia (14h)

| # | ID | Debito | Horas | Justificativa |
|---|-----|--------|-------|---------------|
| 15 | A11Y-002 | Focus indicators customizados | 3h | Completar a11y foundation |
| 16 | FE-008 | Unificar design tokens | 2h | Prevenir drift visual |
| 17 | TEST-002 | Testes atoms prioritarios | 6h | 4 atoms criticos |
| 18 | SEC-002 | dompurify upgrade | 1h | Seguranca transitiva |
| 19 | FE-005 | Consolidar ConfidenceBadge | 1h | Eliminar duplicata |
| 20 | FE-006 | Remover HelloWorld.vue | 5min | Limpeza trivial |

### Deferidos (nao agendar agora)

| ID | Debito | Razao |
|----|--------|-------|
| UX-002 | Responsive/mobile | Desktop-only product decision. Quick win (Login/Home/Upload) pode ser feito por oportunidade |
| UX-003 | Dark mode | Removido do catalogo -- nao eh debito para editor de templates PDF |
| UX-004 | Skeleton screens | Baixo impacto -- editor carrega dados apos pipeline completo |
| PERF-001 | Tree virtualization | Monitorar primeiro, implementar sob demanda |
| PERF-003 | Monaco bundle | Ja separado em chunk, ganho marginal |
| FE-004 | Padronizar store API | Migrar por oportunidade, nao como iniciativa |
| FE-007 | Barrel export composables | DX trivial, fazer quando tocar no diretorio |
| FE-009 | CSS approach consistencia | Cosmetics, nao priorizar |
| TEST-003 | Molecules untested | Apos atoms, por oportunidade |
| TEST-004 | LoginPage tests | Flow simples (OAuth redirect) |
| A11Y-004 | Alt texts | Baixo impacto, fazer por oportunidade |
| UX-008 | Console.log prod | Cross-ref SYS-009, polimento |
| UX-010 | Erros contextuais upload | Nice-to-have |

---

**Esforco total estimado (Sprints 1-5):** ~74.5h
**Esforco deferido:** ~65h+
**Total do catalogo FE/UX ajustado:** 31 debitos (26 originais + 5 adicionados)
**Duplicatas confirmadas:** SYS-022=PERF-002, SYS-020=TEST-001, SYS-006=FE-003, SYS-007 inclui FE-006
