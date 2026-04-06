# Epic 28 — UX Audit Completo: Field Mapping

**Autor:** @ux-design-expert (Uma)
**Data:** 2026-04-01
**Metodologia:** Análise de código + fluxo do usuário + mapa de affordances

---

## 1. Diagnóstico Estrutural — A Falha Raiz

### O layout atual

```
┌────────────────────┬──────────────────────────┬───────────────────┐
│   LEFT PANEL       │       CANVAS             │   RIGHT PANEL     │
│                    │                          │                   │
│  [Estrutura|Campos]│   (template visual)      │   Inspector       │
│                    │                          │   (nó selecionado)│
│  → apenas UMA aba  │                          │                   │
│    visível por vez │                          │                   │
└────────────────────┴──────────────────────────┴───────────────────┘
```

**Problema fundamental:** `LeftPanel.vue` renderiza apenas uma aba de cada vez — é um `v-if` / `v-else-if`. Estrutura e Campos **nunca co-existem na tela**.

---

## 2. Inventário de Falhas por Severidade

### 🔴 CRÍTICA — Drag-and-drop é code morto

**O que o código faz:**
- `FieldNavItem.vue` tem `draggable="true"` e seta `dataTransfer` com `drag-type: 'field'`
- `StructureTreeNode.vue` tem `@drop` que detecta `drag-type === 'field'` e emite `drop-field`
- `StructureTree.vue` tem `handleDropField` que chama `mappingStore.mapField`

**O que é impossível na UI:**
- Para arrastar do Campos para a Estrutura, ambos precisariam estar visíveis
- Como estão na mesma `LeftPanel`, quando Campos está ativo a StructureTree **não está no DOM**
- `handleDropField` em `StructureTree` **nunca pode ser acionado** via drag de FieldNavItem

**Conclusão:** O drag-and-drop Campos→Estrutura foi implementado mas é fisicamente impossível de executar. É dead code de interação.

---

### 🔴 CRÍTICA — O usuário não sabe o que cada aba faz

**Aba Estrutura:** Mostra a árvore hierárquica do template HTML (sections, containers, text nodes...). Cada nó JÁ exibe seu binding inline: `→ {{data.vencimento}}` (linha 40-43 de StructureTreeNode.vue). O binding está visível. A ação de remover binding está no **context menu** (right-click).

**Aba Campos:** Mostra a lista plana dos mapeamentos PDF→XSD com status (🟩🟥🟨). O nome exibido é o **raw text do PDF** (`4.978,54`, `30/03/2026`). Clicar seleciona o nó no Inspector (após fix da sessão anterior).

**O problema mental do usuário:**
```
"Quero corrigir o mapeamento do campo Vencimento"
  → Vou na aba Campos? Vejo "30/03/2026" (raw text) — não reconheço
  → Vou na aba Estrutura? Vejo "text-node-47 → {{data.vencimento}}" — não sei qual é o Vencimento
  → Inspector: mostra o nó selecionado com binding read-only
  → Não há nenhum lugar onde eu veja campo + estrutura + posição visual juntos
```

---

### 🔴 CRÍTICA — A aba Campos não serve ao seu propósito declarado

O propósito implícito da aba Campos é "gerenciar mapeamentos campo↔XSD". Mas:

| Ação | Possível na aba Campos? |
|------|------------------------|
| Ver quais campos estão mapeados | ✅ (lista com status) |
| Identificar qual campo é qual | ❌ (raw PDF text sem contexto) |
| Corrigir um mapeamento errado | ❌ (nem drag nem inline edit funcionam) |
| Ver onde o campo está no template | ❌ (precisa clicar → inspector → mas inspector mostra nó, não posição) |
| Remover um binding | ❌ (só na aba Estrutura via context menu) |
| Ver campos XSD que faltam match | ❌ (descartados no frontend) |

**A aba Campos está 1 de 6 — serve apenas para visualizar status.**

---

### 🟡 ALTA — A aba Estrutura duplica gerenciamento de binding sem integrar com Campos

A aba Estrutura já resolve parcialmente o problema:
- `StructureTreeNode` mostra `→ {{data.vencimento}}` inline em cada nó
- Context menu tem "Remover binding"
- Drag de nós para reorganizar estrutura funciona

Mas falta:
- Não há ação "Trocar binding" — só "Remover"
- Não há busca/filtro por binding
- Não há indicação visual de status de cobertura (🟩🟥🟨) nos nós

---

### 🟡 ALTA — Dois painéis competem, nenhum é suficiente

O operador precisa de ambos ao mesmo tempo:
- Da Estrutura: saber ONDE no template está o elemento
- Dos Campos: saber QUAL XSD path está vinculado e se está correto

A arquitetura força uma troca constante de contexto mental sem solução.

---

### 🟡 ALTA — O Inspector está no lugar certo mas sem poder de ação

O Inspector é o único componente que aparece junto com tudo (sempre visível à direita). Ele já recebe o nó selecionado. Mas o campo Binding é read-only.

**O Inspector é o candidato natural para edição de binding** — é o único lugar que não conflita com nenhuma das duas abas.

---

### 🟠 MÉDIA — Nomes sem semântica na aba Campos

`4.978,54`, `000`, `30/03/2026` como nomes de campos. O backend usa `label_text or pdf_text` onde label_text raramente existe. O XSD path (`data.vencimento`) existe mas não é exibido como nome principal.

---

### 🟠 MÉDIA — Campos XSD obrigatórios sem match são invisíveis

`validation_result.unmapped_xsd_fields` calculado no backend, descartado no frontend em `session.ts:178`. O operador não sabe que existem campos XSD que não aparecem no PDF.

---

### 🟠 MÉDIA — Modal de ambiguidade existe no código, nunca abre

`FieldNavItem` emite `open-ambiguous`, `FieldNavigator` não tem handler. Campos 🟨 são inacionáveis.

---

### 🔵 BAIXA — Sem feedback de drop no Canvas

O Canvas não aceita drops de campo (mas o drag para a Estrutura também não funcionava, então isso é consequência da falha crítica).

---

## 3. Mapa Mental — O que o Operador Precisa

```
Tarefa: "Verificar se todos os campos do boleto estão corretamente mapeados"

Informação necessária:
  A. Quais campos XSD o template precisa?
  B. Cada campo está vinculado a qual elemento do template?
  C. O elemento está na posição visual correta no PDF?
  D. O valor renderizado fica correto? (preview)

Sistema atual fornece:
  A → ❌ (unmapped_xsd_fields descartado)
  B → 🟡 (aba Estrutura mostra binding inline, mas não é lista navegável)
  C → ❌ (sem linha direta campo→posição visual)
  D → ❌ (não é escopo do Epic 28)
```

---

## 4. Redesign Proposto — 3 Opções

### Opção A — Evolução Incremental (menor esforço, mantém 2 abas)

**Princípio:** Cada aba fica responsável por sua perspectiva, mas o Inspector se torna o hub de ação.

```
Aba Estrutura          Aba Campos               Inspector (sempre visível)
─────────────          ──────────               ─────────────────────────
Hierarquia do          Lista de XSD paths       Nó selecionado
template               com status               + Binding EDITÁVEL ← 28.1
                                                + Status badge
▸ Reorganizar          ▸ Ver cobertura          ▸ Trocar XSD path
▸ Remover binding      ▸ Resolver ambíguos      ▸ Remover binding
  (context menu)         (modal) ← 28.3         ▸ Navegar para posição
                       ▸ Nomes semânticos ← 28.2
                       ▸ XSD obrigatórios ← 28.2
```

**Fluxo corrigido para "corrigir mapeamento errado":**
```
1. Clicar no campo 🟥/🟨 na aba Campos → Inspector atualiza
2. No Inspector, campo Binding tem dropdown → selecionar XSD correto
3. Feito. 1 clique + 1 seleção. Sem troca de aba.
```

**Esforço:** Médio (28.1 é o pivô; 28.2, 28.3 são melhorias)
**Risco:** Baixo (aditivo, não quebra estrutura atual)
**Limitação residual:** O usuário ainda não vê campo + posição visual juntos

---

### Opção B — Aba Campos Redesenhada como "Mapeamento"

**Princípio:** A aba Campos vira uma tabela de mapeamento bidirecional — cada linha mostra campo XSD + elemento do template (com breadcrumb de localização).

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 Mapeamento   25/55 PDF · 8 XSD 🔴   [Buscar...] [Filtro ▼] │
├─────────────────────────────────────────────────────────────────┤
│ STATUS  CAMPO XSD              ELEMENTO TEMPLATE   AÇÃO         │
├─────────────────────────────────────────────────────────────────┤
│  🟩    data.vencimento         section>text-47     [Trocar] [✕]│
│        Vencimento              "30/03/2026"                     │
│─────────────────────────────────────────────────────────────────│
│  🟥    data.valor_cobrado      (não vinculado)     [Vincular]  │
│        Valor Cobrado                                            │
│─────────────────────────────────────────────────────────────────│
│  🟨    data.beneficiario       section>text-12     [Resolver ⚡]│
│        Beneficiário            "BANCO DO BRASIL"               │
│─────────────────────────────────────────────────────────────────│
│  🔴    cliente.nome            (XSD obrigatório)   [Info]      │
│        XSD sem match no PDF                                    │
└─────────────────────────────────────────────────────────────────┘
```

**Coluna "Elemento Template":**
- Mostra o breadcrumb curto do nó: `section > text-47`
- Clicável → seleciona o nó no Inspector e Canvas
- "Trocar" → abre BindingEditor dropdown inline na linha
- "✕" → remove binding

**Esforço:** Alto (novo componente `FieldMappingTable.vue`, novo layout de linha)
**Risco:** Médio (substitui FieldNavigator.vue)
**Ganho:** O operador vê campo XSD + localização no template em um único lugar

---

### Opção C — Binding Inline na Aba Estrutura

**Princípio:** A aba Estrutura já mostra binding (`→ {{data.vencimento}}`). Evoluir para tornar esse binding editável inline, e adicionar filtro por status.

```
┌─────────────────────────────────────────────────────────────────┐
│ 📄 root                           [Filtrar com binding ▼]      │
│   ▼ 📦 section-header                                          │
│     · 🔤 text-12  BANCO DO B...   [🟨 data.beneficiario    ▾] │  ← editável inline
│     · 🔤 text-47  30/03/2026      [🟩 data.vencimento      ▾] │
│     · 🔤 text-08  4.978,54        [🟩 data.valor_cobrado   ▾] │
│     · 🔤 text-33  000             [🟥 sem binding          ▾] │  ← click para vincular
│   ▼ 📦 section-body                                            │
│     · 📋 table-01                  (sem binding)              │
└─────────────────────────────────────────────────────────────────┘
```

**Esforço:** Alto (StructureTreeNode precisa de dropdown inline)
**Risco:** Alto (adicionar interação em componente recursivo com drag existente)
**Ganho:** Máximo — tudo em um lugar, hierarquia + binding + status

---

## 5. Recomendação

**Para o Epic 28, implementar Opção A agora + preparar para Opção B depois:**

| Story | Tipo | Descrição | Prioridade |
|-------|------|-----------|-----------|
| **28.1** | Inspector | Binding editável no Inspector (BindingEditor.vue) | 🔴 Crítica |
| **28.2** | Campos | Nomes semânticos + XSD obrigatórios visíveis | 🟡 Alta |
| **28.3** | Campos | Modal de resolução de ambiguidade | 🟡 Alta |
| **28.4** | Canvas | Drag de campo para canvas (único drop target viável) | 🟠 Média |
| ~~28.5~~ | ~~Estrutura~~ | ~~Auto-expand ao selecionar via Campos~~ | ❌ CANCELAR |

### Por que cancelar 28.5:
Story 28.5 (auto-expand StructureTree quando seleciona via Campos) é sem sentido — quando o usuário está na aba Campos e clica num campo, ele está **na aba Campos**, não na aba Estrutura. O auto-expand de uma aba que não está visível não oferece valor. Remover do epic.

### Por que 28.4 agora faz sentido:
Com a Estrutura como drop target sendo dead code, o Canvas é o único lugar para onde o drag é fisicamente possível (painel diferente). Funciona: usuário em aba Campos arrasta → solta sobre o elemento visual no canvas.

---

## 6. Fluxo de Uso Corrigido (pós Epic 28 Opção A)

### Antes (5 passos, 2 abas)
```
1. Aba Campos → identificar campo errado (difícil: nome é "30/03/2026")
2. Trocar para aba Estrutura
3. Localizar o nó (difícil: árvore pode estar colapsada)
4. Right-click → Remover binding
5. Voltar para Campos → drag para... onde? (dead code)
```

### Depois (2 passos, 0 trocas de aba)
```
1. Aba Campos → clicar no campo "🟥 Vencimento" (nome semântico)
   → Inspector atualiza com o nó
2. No Inspector → campo Binding → dropdown → selecionar XSD correto
   Feito.
```

### Ou via Canvas (drag)
```
1. Aba Campos → arrastar "🟥 Valor Cobrado"
2. Soltar sobre o elemento visual no canvas
   Feito.
```

---

## 7. Artefatos para Atualizar

- [x] `frontend/docs/epic-28-field-mapping-interaction-spec.md` — reescrever seção de drag e remover 28.5
- [ ] `docs/epics/epic-28-field-mapping-redesign.md` — remover Story 28.5, atualizar justificativa de 28.4
- [ ] `.aios/handoffs/handoff-ux-to-sm-*.yaml` — atualizar com decisões deste audit

---

*— Uma, desenhando com empatia 💝*
*Audit v2 — identifica dead code de interação e reformula sequência de stories*
