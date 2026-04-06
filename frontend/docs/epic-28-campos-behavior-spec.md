# Aba Campos — Especificação Completa de Comportamento

**Autor:** @ux-design-expert (Uma)
**Data:** 2026-04-01
**Complementa:** epic-28-information-architecture.md + epic-28-field-mapping-interaction-spec.md

---

## 1. Estrutura base da nova aba Campos

```
┌─────────────────────────────────────────────────────────────┐
│  HEADER FIXO (não scrolla)                                  │
│  ─────────────────────────────────────────────────────────  │
│  📊 Mapeamento                                              │
│  2 críticos · 3 sem vínculo · 1 ambíguo · 49 ok            │
│  ████████████████░░░░  83%  (55 campos PDF)                 │
│                                                             │
│  [🔍 Buscar campo...        ]  [Filtrar ▼]                  │
├─────────────────────────────────────────────────────────────┤
│  CORPO SCROLLÁVEL                                           │
│                                                             │
│  ─── 🔴 XSD obrigatório sem match (2) ──────────────────   │
│  ─── 🟥 Sem vínculo (3) ────────────────────────────────   │
│  ─── 🟨 Ambíguo (1) ────────────────────────────────────   │
│  ─── 🟩 Mapeados ▶ 49 campos ───────────────── (colapsado) │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Fluxo: carregamento inicial

### 2a — Pipeline com resultado normal

```
Usuário abre documento → pipeline roda → resultado carregado
  ↓
session.ts:
  reconcileFieldBindings() → conecta block_id → node.binding
  loadPipelineFields()     → popula fieldNavItems com status

Aba Campos recebe:
  • 55 fieldNavItems com status (mapped/unmapped/unconfirmed)
  • N unmapped_xsd_fields (XSD obrigatórios sem PDF match)
  ↓
FieldNavigator computa grupos:
  xsdOnly  = items com isXsdOnly=true         → topo, grupo 🔴
  unmapped = items com status='unmapped'       → grupo 🟥
  ambiguous= items com status='unconfirmed'    → grupo 🟨
  mapped   = items com status='mapped'         → grupo 🟩 (colapsado)

Grupos com 0 itens: não aparecem (sem "Sem vínculo (0)")
```

**Estado visual inicial — exemplo boleto com problemas:**

```
📊 Mapeamento
2 críticos · 3 sem vínculo · 1 ambíguo · 49 ok
████████████████░░░░  83%

🔍 Buscar...   [Filtrar ▼]

─── 🔴 XSD obrigatório (2) ──────────────────────────────────
  🔴  cliente.nome
      Obrigatório no schema — não detectado no PDF    [ⓘ]
  🔴  cliente.documento
      Obrigatório no schema — não detectado no PDF    [ⓘ]

─── 🟥 Sem vínculo (3) ──────────────────────────────────────
  🟥  Competência         PDF: "000"           [Vincular →]
  🟥  Agência             PDF: "0001-9"        [Vincular →]
  🟥  Conta               PDF: "12345-6"       [Vincular →]

─── 🟨 Ambíguo (1) ──────────────────────────────────────────
  🟨  Beneficiário        PDF: "BANCO DO B..." [Resolver ⚡]
      3 candidatos disponíveis

─── 🟩 Mapeados ▶ 49 campos ─────────────────────────────────
```

### 2b — Pipeline sem XSD fornecido

```
Usuário abre documento sem schema XSD
  ↓
unmapped_xsd_fields = [] (vazio)
fieldNavItems têm path = '' ou path = nome do PDF
  ↓
Aba Campos:
  • Grupo 🔴 não aparece (sem XSD = sem campos obrigatórios)
  • Grupo 🟥 e 🟨 aparecem normalmente
  • Header: "0 críticos" não aparece — só "3 sem vínculo · 49 ok"
  • Nota: "⚠ Schema XSD não fornecido. Vinculações baseadas apenas no PDF."
```

### 2c — Pipeline sem campos (documento em branco)

```
field_mappings = []
  ↓
Estado vazio:
  📊 Mapeamento
  Nenhum campo detectado

  ─────────────────────────────────────────────────
    📭 O pipeline não detectou campos de dados.
       Verifique o arquivo PDF ou rode novamente.
  ─────────────────────────────────────────────────
```

### 2d — Carregando (pipeline em andamento)

```
Pipeline ainda processando:
  📊 Mapeamento
  Analisando campos...
  ████████████████████ carregando

  ─── Aguardando resultado do pipeline ────────────
  [skeleton loader — linhas cinza animadas]
```

---

## 3. Fluxo: clicar em campo sem vínculo (🟥)

```
ESTADO INICIAL:
┌─────────────────────────────────────────────────────────────┐
│ 🟥  Competência         PDF: "000"           [Vincular →]   │
└─────────────────────────────────────────────────────────────┘

Usuário CLICA no item (qualquer área exceto o botão [Vincular]):

RESULTADO:
  1. Item fica selecionado (highlight azul)
  2. Canvas: elemento "000" fica destacado com outline azul
     (scroll automático para posição no canvas se necessário)
  3. Inspector atualiza:
     ┌──────────────────────────────────────────┐
     │ Inspetor de Elemento: Competência        │
     │ ────────────────────────────────────────│
     │ ▼ Dados                                 │
     │   BINDING                               │
     │   [🟥 Sem vínculo XSD ▾]    ← editável  │
     │                                         │
     │   TIPO DE CAMPO                         │
     │   texto                                 │
     └──────────────────────────────────────────┘

Usuário clica no [🟥 Sem vínculo XSD ▾] no Inspector:
  → Dropdown abre com todos os XSD paths
  → Busca: digita "comp" → filtra para "data.competencia"
  → Seleciona "data.competencia"
  → node.binding = "data.competencia"
  → fieldNavItem.status = 'mapped'

RESULTADO NO PAINEL:
  Item sai do grupo 🟥 → vai para grupo 🟩 (animação fade-out do grupo)
  Contagem atualiza: "2 críticos · 2 sem vínculo · 1 ambíguo · 50 ok"
  Progressbar: 84% (50/55 * 100... mas progressbar usa só PDF fields)
```

---

## 4. Fluxo: botão [Vincular →] inline

O botão `[Vincular →]` é um atalho — evita ir ao Inspector.

```
Usuário clica em [Vincular →] direto na linha 🟥:
  → Mesmo que clicar no item + abrir dropdown no inspector
  → DIFERENÇA: o dropdown abre INLINE na linha, não no inspector
```

**Dropdown inline no item 🟥:**

```
─── 🟥 Sem vínculo (3) ──────────────────────────────────────
  🟥  Competência         PDF: "000"
  ┌───────────────────────────────────────────────────────┐
  │ 🔍 Buscar XSD path...                                 │
  ├───────────────────────────────────────────────────────┤
  │   data.competencia                                    │  ← highlight
  │   data.competencia_referencia                         │
  │   data.data_competencia                               │
  └───────────────────────────────────────────────────────┘
  🟥  Agência             PDF: "0001-9"        [Vincular →]
  🟥  Conta               PDF: "12345-6"       [Vincular →]
```

Selecionar → fecha dropdown → item migra para 🟩.

**Nota de design:** O dropdown inline usa o mesmo componente `BindingEditor` da Story 28.1. Não criar dois componentes — o BindingEditor pode ser usado inline no item E no inspector.

---

## 5. Fluxo: resolver campo ambíguo (🟨)

```
ESTADO INICIAL:
  🟨  Beneficiário        PDF: "BANCO DO B..." [Resolver ⚡]
      3 candidatos disponíveis

Usuário clica no item OU em [Resolver ⚡]:
  → Canvas destaca o elemento "BANCO DO BRASIL S.A."
  → Inspector atualiza mostrando o nó com status 🟨
  → Modal de ambiguidade abre:

┌─────────────────────────────────────────────────────────────┐
│  ⚡ Resolver Ambiguidade                                ✕   │
│  Campo PDF: "BANCO DO BRASIL S.A."                          │
│  Qual campo XSD é o correto?                                │
│ ─────────────────────────────────────────────────────────── │
│  ● beneficiario.nome           ████████░░ 87%               │
│  ○ beneficiario.razao_social   ███████░░░ 72%               │
│  ○ cedente.nome                █████░░░░░ 51%               │
│  ○ banco.nome                  ███░░░░░░░ 34%               │
│ ─────────────────────────────────────────────────────────── │
│  ○ Nenhum — deixar sem mapeamento                           │
│ ─────────────────────────────────────────────────────────── │
│                    [Cancelar]    [Confirmar →]              │
└─────────────────────────────────────────────────────────────┘

Usuário confirma "beneficiario.nome":
  → modal fecha
  → item: 🟨 → 🟩
  → migra para grupo 🟩
  → header: "0 ambíguos" desaparece do summary
  → "... · 1 ambíguo · ..." → "... · 50 ok"
```

---

## 6. Fluxo: campo 🔴 XSD obrigatório (clique no ⓘ)

```
🔴  cliente.nome
    Obrigatório no schema — não detectado no PDF    [ⓘ]

Usuário clica no item:
  → NÃO seleciona elemento no canvas (não há elemento PDF)
  → NÃO abre inspector de nó (não há nó vinculado)
  → Abre tooltip/popover informativo inline:

  ┌─────────────────────────────────────────────────┐
  │ ℹ️  XSD Obrigatório — Sem correspondência no PDF │
  │                                                  │
  │  O schema exige o campo "cliente.nome" mas       │
  │  ele não foi detectado no PDF original.          │
  │                                                  │
  │  Possíveis ações:                                │
  │  • O PDF não contém este dado — ignorar          │
  │  • Criar um elemento no template e vincular      │
  │    manualmente (vá para aba Estrutura)           │
  │                                                  │
  │  [Ignorar para este template]   [Fechar]         │
  └─────────────────────────────────────────────────┘

Se usuário clica "Ignorar":
  → campo sai do grupo 🔴
  → header: "1 crítico" → desaparece se era o último
  → campo NÃO vai para 🟩 (não foi resolvido, foi descartado)
  → campo some da lista (ou vai para grupo opcional colapsado)
```

---

## 7. Fluxo: busca

```
Usuário digita "venc" no campo de busca:

ANTES:
  🟥 Sem vínculo (3): Competência, Agência, Conta
  🟩 Mapeados (49): Vencimento, Valor, ...

DEPOIS:
  🟩 Vencimento    PDF: "30/03/2026"    ← único match no nome semântico
                                           ou no XSD path "data.vencimento"

  ─── sem mais resultados ────────────────────────────────
```

**Regras de busca:**
- Busca por: nome semântico + XSD path + raw PDF text (qualquer dos três)
- Case insensitive, substring
- "venc" encontra: "Vencimento", "data.vencimento", "data_vencimento_boleto"
- Grupos mantidos mas apenas com os itens que fazem match
- Grupos vazios após filtro: não aparecem
- Sem resultados: estado vazio "Nenhum campo encontrado para 'venc'"
- Limpar busca: ✕ no campo → volta ao estado completo

**Busca + grupo 🟩 colapsado:**
```
Se busca encontra algo dentro do grupo 🟩 colapsado:
  → grupo 🟩 abre automaticamente para mostrar o match
  → não recolhe ao limpar busca (permanece como estava)
```

---

## 8. Fluxo: filtro rápido

```
[Filtrar ▼] abre:
  ┌─────────────────────────┐
  │ ✓ Todos                 │
  │ ─────────────────────── │
  │ ○ Apenas com problemas  │  ← oculta grupo 🟩
  │ ○ Apenas mapeados       │  ← mostra só 🟩
  │ ─────────────────────── │
  │ ○ XSD obrigatórios 🔴   │
  │ ○ Sem vínculo 🟥        │
  │ ○ Ambíguos 🟨           │
  │ ─────────────────────── │
  │ Tipo: [Todos ▼]         │  ← mantém filtro por tipo como SUB-FILTRO
  └─────────────────────────┘
```

**"Apenas com problemas"** é o filtro mais usado — o operador quer ver só o que precisa resolver.

---

## 9. Fluxo: expandir grupo 🟩 (campos mapeados)

```
ESTADO INICIAL:
  ─── 🟩 Mapeados ▶ 49 campos ──── (colapsado)

Usuário clica no header do grupo:
  ─── 🟩 Mapeados ▼ 49 campos ──── (expandido)
    🟩  Vencimento       data.vencimento    → section-header > text-47
    🟩  Valor Cobrado    data.valor_cobrado → section-header > text-12
    🟩  CNPJ Benefic.    beneficiario.cnpj  → section-body > text-03
    ... (49 itens, scrollável)

Cada item mapeado exibe:
  🟩  [Nome semântico]   [XSD path truncado]   [breadcrumb do nó]

O breadcrumb "section-header > text-47" é clicável:
  → seleciona o nó na árvore Estrutura (muda para aba Estrutura? NÃO)
  → seleciona o nó no Inspector
  → destaca no canvas
  → usuário permanece na aba Campos
```

**Campo mapeado tem ação de "desvincular":**
```
Hover em campo 🟩:
  🟩  Vencimento    data.vencimento    section-header > text-47    [⚙ ▼]

Clica [⚙ ▼]:
  ┌────────────────────────────┐
  │ Trocar vínculo...          │
  │ Remover vínculo            │
  └────────────────────────────┘

"Remover vínculo":
  → campo muda para 🟥
  → migra para grupo 🟥
  → contagem atualiza
  → inspector atualiza (binding removido)
```

---

## 10. Fluxo: arrastar campo para o canvas (28.4)

```
Usuário está na aba Campos
Vê: 🟥 Conta    PDF: "12345-6"    [Vincular →]

Usuário segura e arrasta o item "🟥 Conta":
  → cursor muda para grab
  → item fica translúcido (opacity 0.5) na lista

Mouse entra no Canvas (painel central):
  → canvas entra em "modo drop" (overlay sutil)
  → elementos com binding disponível ficam com outline pontilhado

Mouse passa sobre elemento "12345-6" no canvas:
  → esse elemento recebe highlight azul sólido
  → tooltip: "Soltar para vincular como data.conta"
      (preview do XSD path que será vinculado)

Usuário SOLTA sobre o elemento:
  → mappingStore.mapField(elementId, field.path)
  → item: 🟥 → 🟩 (animação rápida)
  → canvas: outline azul → outline verde breve → normal
  → inspector: binding atualiza

Usuário SOLTA sobre área vazia do canvas (sem elemento):
  → cursor era "no-drop" (não acontece nada)
  → item volta para a lista sem mudança

Usuário CANCELA (Escape ou solta fora):
  → item volta para posição original
  → canvas sai do "modo drop"
```

---

## 11. Fluxo: campo selecionado e canvas destaca

```
Usuário clica em 🟩 Vencimento no grupo expandido:

LEFT PANEL (aba Campos):
  Item fica highlighted (fundo azul escuro)

CENTER PANEL (canvas):
  Elemento "30/03/2026" fica com outline azul
  Se elemento estiver fora da viewport:
    → canvas faz scroll automático até o elemento
    → pulso de animação para chamar atenção

RIGHT PANEL (inspector):
  Título: "Inspetor de Elemento: Vencimento"
  Binding: [🟩 data.vencimento ▾]  ✕
  (campos de tipografia, cor, etc.)

SINCRONISMO:
  Se usuário clicar num elemento no canvas:
    → item correspondente na lista TAMBÉM fica highlighted
    → se item estiver no grupo 🟩 colapsado: grupo abre automaticamente
    → lista faz scroll até o item
```

---

## 12. Fluxo: resolver TODOS os problemas (estado de sucesso)

```
Usuário resolve o último problema pendente:

ANTES:
  🟥 Sem vínculo (1): Conta

DEPOIS DE VINCULAR:
  Grupo 🟥 desaparece (fade out)
  Animação de conclusão no header:

  📊 Mapeamento
  ✅ Todos os campos mapeados!
  ████████████████████  100%    ← barra cheia verde

  ─── 🟩 Mapeados ▶ 55 campos ──────────────────────────────

Estado persistente — não pisca nem desaparece.
O operador pode clicar no grupo 🟩 para fazer revisão final.
```

---

## 13. Fluxo: XSD não disponível (sem schema)

```
session.ts não recebeu unmapped_xsd_fields
field_mappings não têm xsd_field_path

Aba Campos:
  📊 Mapeamento
  ⚠ Schema XSD não fornecido
  3 sem vínculo · 49 ok
  ────────────────────  85%

  ─── 🟥 Sem vínculo (3) ─────────────────────────────
  🟥  000              PDF: "000"          [Vincular →]
      (nome = raw PDF text, sem semântica)

  [Vincular →] → abre dropdown mas lista está VAZIA:
  ┌───────────────────────────────────────────────────┐
  │ 🔍 Buscar XSD path...                             │
  │ ─────────────────────────────────────────────────│
  │ (XSD não disponível — nenhum path carregado)      │
  └───────────────────────────────────────────────────┘

  Botão [Vincular →] disabled com tooltip:
  "Schema XSD não carregado. Forneça um arquivo .xsd para habilitar."
```

---

## 14. Fluxo: contagem no header atualiza em tempo real

O header é um componente computado reativo — atualiza sem reload:

```
Evento: mapField() ou removeBinding() ou resolveAmbiguous()
  ↓
mappingStore.fieldNavItems recomputa
  ↓
Header summary recomputa:
  críticos  = fieldNavItems.filter(f => f.isXsdOnly).length
  unmapped  = fieldNavItems.filter(f => f.status === 'unmapped' && !f.isXsdOnly).length
  ambiguous = fieldNavItems.filter(f => f.status === 'unconfirmed').length
  mapped    = fieldNavItems.filter(f => f.status === 'mapped').length
  ↓
Progressbar: mapped / (mapped + unmapped + ambiguous)
  (XSD críticos não contam — são alertas, não campos PDF)
```

**Visibilidade dos badges no summary:**
- Badge só aparece se o valor > 0
- "0 críticos" não aparece — o badge simplesmente desaparece
- Se tudo ok: só mostra "55 ok" sem pontos negativos

---

## 15. Edge cases

### Campo com binding inválido (XSD path não existe mais)

```
node.binding = "data.campo_removido_do_xsd"
→ fieldNavItem.status = 'unmapped' (o path não está em flat_paths)
→ aparece como:
  🟥  Nome do campo   PDF: "valor"   ⚠ binding inválido   [Corrigir →]
→ [Corrigir →] = [Vincular →] com aviso de que o path anterior não existe
```

### Dois campos PDF vinculados ao mesmo XSD path

```
text-47 → data.vencimento
text-52 → data.vencimento  ← duplicado!

→ ambos aparecem em 🟩 mas com aviso visual:
  🟩  Vencimento (×2)   data.vencimento   ⚠ duplicado
→ hover mostra: "2 elementos vinculados ao mesmo campo"
→ isso não é necessariamente erro (pode ser intencional para repetição em header/footer)
→ não bloqueia, apenas informa
```

### Campo opcional sem binding

```
isOptional = true, status = 'unmapped'
→ aparece no grupo 🟥 mas com badge diferente:
  🟡  Observações   PDF: "—"   (opcional)   [Vincular →]
→ cor âmbar (não vermelho) para distinguir de obrigatório
→ progressbar não é afetada por campos opcionais sem binding
→ summary: "1 opcional" como categoria separada (menor destaque)
```

---

## 16. Componentes novos para Story 28.2 (revisada)

| Componente | Tipo | Responsabilidade |
|-----------|------|-----------------|
| `FieldNavigator.vue` | Organismo | Reescrever lógica de grupos: STATUS em vez de TYPE |
| `FieldNavGroup.vue` | Molécula | Novo — grupo colapsável com header (🔴/🟥/🟨/🟩) |
| `FieldNavItem.vue` | Molécula | Evoluir — 2 linhas (semântico + PDF), botão inline |
| `FieldNavSummary.vue` | Molécula | Novo — header com badges e progressbar |
| `XsdOnlyField.vue` | Molécula | Novo — item especial para campos 🔴 (sem nó) |

**FieldNavGroup props:**
```typescript
interface Props {
  status: 'xsd-only' | 'unmapped' | 'unconfirmed' | 'mapped'
  fields: FieldNavItem[]
  defaultCollapsed?: boolean  // true para grupo 🟩
}
```

---

## 17. O que NÃO muda na Story 28.2

- O drag de campos para o canvas permanece via `FieldNavItem` (draggable)
- A seleção click→canvas→inspector permanece o mesmo fluxo
- O `BindingEditor` do Inspector (28.1) permanece como é — o botão [Vincular →] usa o mesmo componente
- O modal de ambiguidade (28.3) permanece igual — `[Resolver ⚡]` só aciona ele

---

*— Uma, desenhando com empatia 💝*
*Behavior spec v1 — 17 fluxos + edge cases para Story 28.2 redesenhada*
