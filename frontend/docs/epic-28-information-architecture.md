# Epic 28 — Arquitetura de Informação: Por que 2 abas e como se relacionam

**Autor:** @ux-design-expert (Uma)
**Data:** 2026-04-01

---

## A verdade central que as duas abas compartilham

Existe um fato central no sistema: **um elemento do template está vinculado a um campo XSD**.

```
   Template (HTML)              Binding               Dados (XSD)
   ─────────────────            ───────               ───────────
   <span id="text-47">   →   node.binding    →   data.vencimento
        "30/03/2026"                =                 (campo no schema)
   </span>            "data.vencimento"
```

Esse mesmo fato aparece nas **duas abas de formas diferentes**, porque o operador pode chegar a ele por dois caminhos diferentes:

---

## As duas perspectivas

```
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│         ABA ESTRUTURA           │     │          ABA CAMPOS             │
│                                 │     │                                 │
│  Lente: TEMPLATE                │     │  Lente: DADOS XSD               │
│  Pergunta: "Como o documento    │     │  Pergunta: "Todos os dados que  │
│   está organizado?"             │     │   o documento precisa estão     │
│                                 │     │   cobertos?"                    │
│  Unidade: nó HTML               │     │  Unidade: campo XSD             │
│  (section, container, text...)  │     │  (data.vencimento, cliente.nome)│
│                                 │     │                                 │
│  📦 section-header              │     │  🟩 Vencimento                  │
│    · 🔤 text-47                 │     │     data.vencimento             │
│        → {{data.vencimento}}    │     │                                 │
│    · 🔤 text-12                 │     │  🟩 Valor Cobrado               │
│        → {{data.valor_cobrado}} │     │     data.valor_cobrado          │
│    · 🔤 text-33                 │     │                                 │
│        (sem binding)            │     │  🟥 Beneficiário                │
│                                 │     │     data.beneficiario           │
│  📦 section-body                │     │                                 │
│    · 📋 table-01                │     │  🔴 cliente.nome                │
│        (tabela de detalhes)     │     │     (XSD sem PDF match)         │
└─────────────────────────────────┘     └─────────────────────────────────┘
         Você usa quando...                       Você usa quando...
    "Quero reorganizar o layout"            "Quero checar se todos os dados
    "Quero ver o que cada seção              do boleto estão sendo exibidos"
     renderiza"                             "Quero corrigir um campo
    "Quero mover um elemento"               mapeado errado"
```

---

## Por que as duas abas são necessárias

### Aba Estrutura — perspectiva do template
- O template tem **dezenas de nós** (sections, containers, text, tables, images)
- A **maioria não tem binding** (são estruturais: layouts, bordas, cabeçalhos fixos)
- O operador precisa ver a hierarquia completa para entender a composição do documento
- Nós sem binding são tão importantes quanto os com binding aqui

### Aba Campos — perspectiva dos dados
- O XSD define **quais campos o documento deve exibir**
- O operador precisa confirmar que **todos os campos estão cobertos**
- A pergunta é: "tem algum dado faltando?" — não "tem algum elemento faltando"
- O foco é no campo de dados, não no elemento HTML

**Exemplo prático com um boleto:**

| O que o operador quer saber | Aba certa |
|-----------------------------|-----------|
| "O header tem logo e código de barras?" | Estrutura |
| "Onde está a tabela de detalhes?" | Estrutura |
| "O valor do boleto está sendo exibido?" | Campos |
| "Tem campos XSD que não aparecem em lugar nenhum?" | Campos |
| "Esse campo está mapeado pro XSD certo?" | Campos → Inspector |
| "Quero mover a data de vencimento para cima" | Estrutura |

---

## O problema ATUAL (antes do Epic 28)

Cada aba tem a perspectiva certa, mas **nenhuma permite agir** quando encontra um problema:

```
Aba Campos encontra um problema:           Aba Estrutura encontra um problema:
──────────────────────────────             ──────────────────────────────────
🟥 Beneficiário — sem vínculo              🔤 text-33 — sem binding

O operador quer corrigir.                  O operador quer vincular.
Pode? NÃO.                                 Pode? SIM, mas só via:
  • Drag não funciona (tab mutual exclusion)  • context menu → só "Remover"
  • Binding no inspector é read-only          • Não tem "Trocar binding"
  • Precisa trocar de aba                     • Binding read-only no inspector

→ Operador abandona a tarefa ou           → Operador remove e refaz
  faz 5 passos entre 2 abas               manualmente via drag (dead code)
```

---

## A solução do Epic 28 — O Inspector como bridge

A resolução não é fundir as abas. Cada aba tem um propósito claro e distinto. A solução é **tornar o Inspector acionável** — ele é o único painel sempre visível, independente de qual aba está ativa.

```
ANTES:                              DEPOIS (Epic 28):

Aba Campos  →  problema             Aba Campos  →  clica campo
                  ↓                                    ↓
           precisa ir p/ Estrutura              Inspector atualiza
                  ↓                                    ↓
           Estrutura → remove        Inspector: campo Binding EDITÁVEL
                  ↓                                    ↓
           volta p/ Campos           dropdown de XSD → seleciona → feito
           arrasta (não funciona)    ──── zero troca de aba ────
```

---

## Como as 3 superfícies funcionam juntas após o Epic 28

```
┌────────────────────┬──────────────────────────┬───────────────────────────┐
│   LEFT PANEL       │       CANVAS             │   INSPECTOR (sempre vis.) │
│                    │                          │                           │
│  ABA: CAMPOS       │   [template renderizado] │   NODO SELECIONADO:       │
│  ─────────────     │                          │   text-47                 │
│  🟩 Vencimento  ───┼──────────────────────────┼─► ┌───────────────────┐  │
│  🟥 Beneficiário   │   [text-47 highlighted]  │   │ BINDING           │  │
│  🟨 Valor Cobr. ───┼──────────────────────────┼─► │ [🟩 data.venc. ▾]│  │
│                    │                          │   │               [✕] │  │
│  ── XSD SEM MATCH──│                          │   └───────────────────┘  │
│  🔴 cliente.nome   │                          │   → trocar aqui           │
│                    │                          │   → remover aqui          │
└────────────────────┴──────────────────────────┴───────────────────────────┘

  Clica campo          Elemento destaca            Inspector atualiza
  na aba Campos        no canvas                   com binding editável
```

```
┌────────────────────┬──────────────────────────┬───────────────────────────┐
│   LEFT PANEL       │       CANVAS             │   INSPECTOR (sempre vis.) │
│                    │                          │                           │
│  ABA: ESTRUTURA    │   [template renderizado] │   NODO SELECIONADO:       │
│  ─────────────     │                          │   section-header          │
│  📦 section-header │                          │                           │
│    🔤 text-47  ────┼──────────────────────────┼─► ┌───────────────────┐  │
│       🟩 data.v.   │   [text-47 highlighted]  │   │ BINDING           │  │
│    🔤 text-33      │                          │   │ [🟥 sem binding ▾]│  │
│       🟥 (vazio)   │                          │   │                   │  │
│  📦 section-body   │                          │   └───────────────────┘  │
│    📋 table-01     │                          │   → vincular aqui         │
│                    │                          │                           │
└────────────────────┴──────────────────────────┴───────────────────────────┘

  Clica nó             Elemento destaca            Inspector com binding
  na aba Estrutura     no canvas                   editável (mesmo componente)
```

**O binding editor no Inspector funciona igual nas duas abas.** O operador usa a aba que faz sentido para sua tarefa — e corrige no Inspector sem sair dela.

---

## Jornadas de uso completas

### Jornada 1 — "Checar se todos os campos do boleto estão cobertos"
**Entrada: aba Campos (perspectiva de dados)**

```
1. Abrir aba Campos
   ┌─────────────────────────────────────────┐
   │ 📊 Mapeamento  23/55 PDF · 8 XSD 🔴    │  ← vê imediatamente: 8 campos XSD sem match
   ├─────────────────────────────────────────┤
   │ 🟩 Vencimento          data.vencimento  │  ✓ ok
   │ 🟩 Valor Cobrado       data.valor_cob.  │  ✓ ok
   │ 🟨 Beneficiário        3 candidatos ⚡  │  ← precisa resolver
   │ 🟥 Competência         sem vínculo      │  ← precisa vincular
   │ ─── XSD sem match ─────────────────── │
   │ 🔴 cliente.nome        XSD obrigatório  │  ← não está no PDF
   └─────────────────────────────────────────┘

2. Clica em "🟨 Beneficiário"
   → Canvas destaca o elemento visual
   → Inspector mostra: Binding [🟨 3 candidatos ⚡]
   → Modal de ambiguidade abre com os 3 candidatos e scores
   → Seleciona "beneficiario.nome (87%)" → confirma
   → Campo muda para 🟩

3. Clica em "🟥 Competência"
   → Inspector mostra: Binding [🟥 sem vínculo ▾]
   → Clica no dropdown → digita "comp" → aparece "data.competencia"
   → Seleciona → campo muda para 🟩

4. Inspeciona "🔴 cliente.nome"
   → Tooltip: "Este campo XSD não tem correspondência no PDF"
   → Operador decide: campo não existe neste boleto, ignorar

5. Resultado: 25/55 → 25/55 PDF, 7 XSD 🔴 (1 resolvido)
```

**Nunca precisou abrir a aba Estrutura.**

---

### Jornada 2 — "Reorganizar o layout — mover a data de vencimento para o header"
**Entrada: aba Estrutura (perspectiva de template)**

```
1. Abrir aba Estrutura
   📦 section-body
     · 🔤 text-47 → {{data.vencimento}}    ← está no body, quero mover pro header
     · 📋 table-01

2. Arrastar text-47 de section-body para section-header
   (drag dentro da própria aba Estrutura — funciona hoje)

3. Verifica no canvas que ficou na posição certa

4. Resultado: elemento movido, binding data.vencimento mantido
```

**Nunca precisou abrir a aba Campos.**

---

### Jornada 3 — "Cliquei num elemento no canvas, quero saber qual campo XSD ele renderiza"
**Entrada: canvas (manipulação direta)**

```
1. Clica no elemento "30/03/2026" no canvas
   → Inspector atualiza: text-47, Binding [🟩 data.vencimento ▾]
   → Sem abrir nenhuma aba, já sei a resposta

2. Se quiser trocar: clica no dropdown do Binding no Inspector
   → Lista todos os XSD paths disponíveis
   → Seleciona outro → feito
```

**Nem precisou abrir nenhuma aba.**

---

### Jornada 4 — "Quero vincular arrastando — modo visual"
**Entrada: aba Campos + canvas (drag direto)**

```
1. Abrir aba Campos
   Vê: 🟥 Competência — sem vínculo

2. Arrastar "🟥 Competência" do painel esquerdo
   → Mouse vai para o canvas (painel central, painel diferente — fisicamente possível)
   → Passa over do elemento "000" no canvas → elemento ganha outline azul "solte aqui"

3. Solta sobre o elemento "000"
   → mappingStore.mapField(element.id, "data.competencia")
   → Campo muda para 🟩
   → Binding aparece no Inspector
```

---

## O que cada superfície resolve

```
┌──────────────────┬────────────────────────────────────────────────────┐
│ Superfície        │ Para que serve                                     │
├──────────────────┼────────────────────────────────────────────────────┤
│ Aba CAMPOS       │ "Tenho todos os dados cobertos?"                   │
│                  │ → visão de cobertura XSD                          │
│                  │ → encontrar campos não mapeados / ambíguos         │
│                  │ → ver campos XSD sem match no PDF                  │
├──────────────────┼────────────────────────────────────────────────────┤
│ Aba ESTRUTURA    │ "Como o documento está organizado?"                │
│                  │ → visão hierárquica do template                    │
│                  │ → reorganizar layout (drag de nós)                 │
│                  │ → ver o que cada seção / container renderiza       │
├──────────────────┼────────────────────────────────────────────────────┤
│ INSPECTOR        │ "Quero agir sobre este elemento/campo"             │
│ (sempre visível) │ → trocar binding (dropdown editável)              │
│                  │ → remover binding                                  │
│                  │ → editar propriedades visuais do nó               │
├──────────────────┼────────────────────────────────────────────────────┤
│ CANVAS           │ "Quero trabalhar visualmente"                      │
│                  │ → clicar para selecionar elemento                  │
│                  │ → receber drop de campo da aba Campos (28.4)       │
│                  │ → ver o resultado visual em tempo real             │
└──────────────────┴────────────────────────────────────────────────────┘
```

---

## O que muda em cada parte (Epic 28 stories)

```
                    ANTES                          DEPOIS
                    ─────                          ──────

ABA CAMPOS
  Nome do campo     "30/03/2026" (raw PDF)         "Vencimento" (semântico)    [28.2]
  Subtítulo         (nenhum)                        "30/03/2026" (tooltip)     [28.2]
  XSD sem match     invisível                       🔴 "XSD obrigatório"       [28.2]
  Campo ambíguo     clique → nada                   clique → modal de escolha  [28.3]
  Campo unmapped    clique → inspector, sem ação    clique → inspector → edit  [28.1]
  Drag campo        vai para lugar nenhum           vai para canvas            [28.4]
  Header count      "25 de 55 mapeados"             "25/55 PDF · 8 XSD 🔴"    [28.2]

INSPECTOR
  Binding           read-only ("data.vencimento")   dropdown editável          [28.1]
  Remover binding   não existe (só na Estrutura)    botão ✕ inline             [28.1]
  Status binding    não existe                      badge 🟩🟥🟨               [28.1]

ABA ESTRUTURA
  Binding inline    → {{data.vencimento}} (texto)   sem mudança — já funciona  [—]
  Remover binding   context menu → "Remover"        sem mudança — já funciona  [—]
  Drag de nós       funciona                        sem mudança                [—]

CANVAS
  Drop de campo     silencioso (nada acontece)      vincula ao elemento        [28.4]
  Drop feedback     nenhum                          outline azul "solte aqui"  [28.4]
```

---

## Fluxo de dados: o que conecta tudo

```
BACKEND (pipeline)
  field_mappings[]:
    { block_id, xsd_field_path, name (raw PDF), status, candidates }
  validation_result.unmapped_xsd_fields[]     ← hoje descartado
          │
          ▼
SESSION.TS (reconcileFieldBindings — já implementado)
  Para cada field_mapping:
    → acha o TreeNode pelo block_id
    → seta node.binding = xsd_field_path
    → seta fieldNavItem.nodeId = node.id
          │
          ├──► templateStore.flatNodes (TreeNode[])
          │         ↑ consumido pela aba Estrutura (StructureTreeNode)
          │
          └──► mappingStore.fieldNavItems (FieldNavItem[])
                    ↑ consumido pela aba Campos (FieldNavigator)
                    ↑ filtrado/buscado no BindingEditor (Inspector) [28.1]
```

O `node.binding` é a **fonte única de verdade**. Quando o operador muda um binding pelo Inspector:

```
Inspector: onBindingChange("data.vencimento") [28.1]
  → templateStore.updateNodeProperty(node.id, 'binding', 'data.vencimento')
  → mappingStore.mapField(node.id, 'data.vencimento')
        ↓
  Aba Estrutura: StructureTreeNode reage (computed de node.binding)
  Aba Campos: FieldNavItem reage (status muda para 🟩)
  Inspector: badge atualiza para 🟩
  Canvas: elemento continua no mesmo lugar, binding mudou
```

**Uma ação no Inspector → as duas abas ficam sincronizadas automaticamente.**

---

## Stories revisadas (sequência final)

| Story | O que faz | Por que nesta ordem |
|-------|-----------|---------------------|
| **28.1** — Inspector binding editável | Torna o Inspector acionável — é o bridge entre as duas abas | Pivô: desbloqueia todas as jornadas |
| **28.2** — Nomes semânticos + XSD visíveis | Torna a aba Campos legível e completa | Depende de session.ts estável |
| **28.3** — Modal de ambiguidade | Resolve o último fluxo bloqueado na aba Campos | Depende de FieldNavigator estável |
| **28.4** — Drag campo → canvas | Adiciona o caminho visual (alternativo, não substitui) | Independente; pode ser última |

---

*— Uma, desenhando com empatia 💝*
*IA v3 — define propósito de cada superfície antes de detalhar interações*
