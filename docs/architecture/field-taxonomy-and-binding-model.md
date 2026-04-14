# Taxonomia de Campos e Modelo de Binding

**Status:** `current`
**Dono:** `@architect`
**Criado:** 2026-04-14
**Atualizar quando:** decisão sobre terminologia ou modelo de binding mudar

> Este documento captura os conceitos discutidos e os gaps identificados antes do Pilar C (Editor).
> Leia antes de qualquer epic que toque em Stage 3 classificação, Stage 4 binding ou editor visual.

---

## O problema atual — terminologia inconsistente

O pipeline usa termos diferentes em cada stage para descrever conceitos relacionados.
Isso cria confusão ao implementar, ao debugar e ao construir o editor.

### Mapa do que existe hoje

| Stage | Termos usados | Significado real |
|-------|--------------|-----------------|
| Stage 3 — classificação de bloco | `label`, `dynamic`, `semi_dynamic`, `likely_dynamic`, `static`, `header`, `footer_text` | 7 termos para 2 conceitos (papel + variabilidade) |
| Stage 3 — nó na árvore | `label`, `value` | Papel estrutural do bloco |
| Stage 4 — resultado do binding | `xsd_field_path` preenchido ou vazio | Estado do binding — implícito |
| Stage 5 — HTML gerado | `data-status="unmapped"`, `data-bind="text: Campo"`, texto literal | 3 representações diferentes do estado |

### O problema central

**`dynamic` (classificação Stage 3) ≠ `value` (nó árvore) ≠ "dinâmico no template" (Stage 5).**

Um bloco classificado como `dynamic` vira nó `value` na árvore — mas pode terminar como
texto fixo no HTML se o Stage 4 não encontrar `xsd_field_path`. São conceitos distintos
que hoje compartilham o mesmo rótulo.

---

## Os 3 eixos corretos

Todo elemento de texto em um documento tem três dimensões independentes:

### Eixo 1 — Papel Estrutural

Responde: *qual é a função deste texto no documento?*

| Termo | Definição | Exemplo |
|-------|-----------|---------|
| `label` | Texto estrutural do documento — nomeia um campo. **Sempre fixo.** Nunca vira `{{Campo}}` | `"Nome:"`, `"Vencimento"`, `"Beneficiário"` |
| `value` | Conteúdo do campo — o dado em si. **Candidato a dinâmico.** | `"Rodrigo Agape"`, `"10/08/2019"`, `"RJ"` |

**Regra:** label é sempre fixo por definição. Só values participam do binding.

### Eixo 2 — Variabilidade (detectada por multi-sample)

Responde: *este texto muda entre instâncias do mesmo template?*

| Termo | Definição | Como detectar |
|-------|-----------|--------------|
| `fixed` | Mesmo texto em todas as instâncias | Multi-sample: texto idêntico nos N PDFs |
| `varies` | Texto diferente entre instâncias | Multi-sample: texto diferente nos N PDFs |

**Com single-sample:** não é possível detectar variabilidade com certeza.
O pipeline usa heurísticas (padrões de data, CPF, moeda, comprimento > 30 chars).

**Com multi-sample (3+ PDFs):** a comparação direta elimina a necessidade de heurísticas.
Um value `fixed` no multi-sample provavelmente é um dado estrutural do template (ex: nome da empresa).
Um value `varies` no multi-sample é candidato direto a `{{Campo}}`.

### Eixo 3 — Estado do Binding

Responde: *este campo está vinculado a um campo do contrato de dados?*

| Termo | Definição | No template |
|-------|-----------|------------|
| `bound` | Tem `xsd_field_path` — vinculado ao contrato | `{{Campo}}` / `data-bind="text: Campo"` |
| `unbound` | Value identificado mas sem campo XSD atribuído | Texto fixo com `data-status="unbound"` |
| `fixed` | Label ou value estruturalmente fixo | Texto literal, sem marcação de binding |

---

## Como os 3 eixos se combinam

```
Todo bloco de texto no documento:

  papel = label  →  sempre FIXED, nunca participa de binding
                    renderizado como texto literal

  papel = value  →  variabilidade: fixed | varies
                    estado binding: bound | unbound

    value + fixed  + unbound  →  texto literal (dado estrutural do template)
    value + varies + unbound  →  data-status="unbound" (operador precisa vincular)
    value + varies + bound    →  {{Campo}} no template ← estado ideal
    value + fixed  + bound    →  possível (campo fixo mapeado ao XSD — raro mas válido)
```

---

## Fluxo do pipeline mapeado aos 3 eixos

```
Stage 3 — define PAPEL + VARIABILIDADE
  ├── Heurística (single-sample): endsWith(":") → label; patterns, len > 30 → dynamic
  ├── Multi-sample: blocos que variam → varies; blocos iguais → fixed
  └── Pairing espacial: conecta label ao value adjacente (acima/direita)

Stage 4 — define ESTADO DO BINDING
  ├── Recebe pares (label_text, value_block_id)
  ├── Usa label_text como hint para Gemini encontrar campo XSD
  └── Resultado: xsd_field_path preenchido (bound) ou vazio (unbound)

Stage 5 — renderiza baseado nos 3 eixos
  ├── label → texto literal
  ├── value + bound → {{Campo}} / data-bind
  └── value + unbound → texto com data-status="unbound"
```

---

## O que o Editor (Pilar C) precisa expor

O operador não precisa entender os termos internos do pipeline. O editor deve expor
uma interface simples baseada nos 3 eixos:

### Estados visíveis no canvas

```
🔒 Fixo        → texto que não muda (label OU value estruturalmente fixo)
🔗 Vinculado   → {{Campo}} — bound ao contrato
⚠️ Não vínculado → value detectado mas sem campo XSD — operador precisa agir
```

### Ação do operador para vincular

```
1. Clica no elemento no canvas (status: ⚠️ Não vínculado)
2. Inspetor mostra: texto atual, tipo detectado (value/varies)
3. Operador abre "Vincular a campo"
4. Vê árvore do XSD filtrada (campos compatíveis com o tipo do valor)
5. Seleciona o campo → xsd_field_path salvo
6. Elemento vira {{Campo}} no canvas
```

### Ação para tornar um fixo em dinâmico

```
1. Clica em elemento com status 🔒 Fixo
2. Inspetor mostra: "Este campo está marcado como fixo"
3. Operador seleciona "Tornar dinâmico"
4. Fluxo de vinculação acima
```

---

## Gaps identificados — pendente de decisão

### Gap 1 — Terminologia não normalizada entre stages

**Problema:** `dynamic` (Stage 3) ≠ `value` (árvore) ≠ `bound` (Stage 5).
**Decisão pendente:** Adotar os 3 eixos deste documento como vocabulário canônico.
**Impacto:** Stage 3, Stage 4, Stage 5, Editor, API contracts.

### Gap 2 — `static` vs `fixed` vs `label` — termos sobrepostos

**Problema:** Stage 3 usa `static` para blocos que não variam no multi-sample, mas
labels também são estáticos. São conceitos diferentes com mesmo nome.
**Decisão pendente:** `static` → substituir por `fixed` no vocabulário. Labels são
`fixed` por definição de papel, não de variabilidade.

### Gap 3 — `data-status="unmapped"` não distingue "não tentou" de "tentou e não achou"

**Problema:** um elemento `unmapped` pode ser:
  a) Value que o Stage 4 tentou mapear e não encontrou campo XSD correspondente
  b) Value que nunca participou do matching (não foi emparelhado no Stage 3)
  c) Value de coleção (repeated_section) que tem binding diferente
**Decisão pendente:** `data-status` precisa de valores mais granulares:
  `unbound-no-pair` / `unbound-no-match` / `unbound-list-item`

### Gap 4 — Formato de saída inconsistente: Knockout.js vs Mustache

**Problema:** campos escalares usam `data-bind="text: Campo"` (Knockout.js),
mas campos dentro de `<repeat>` usam `{{Campo}}` (Mustache).
O motor de geração espera um formato só.
**Decisão pendente:** definir qual formato o motor de geração consome e padronizar
todo o Stage 5 para esse formato.

### Gap 5 — Path relativo dentro de `<repeat>`

**Problema:** dentro de `<repeat data-list="Root.Segurados.Segurado[]">`, o binding
deve ser relativo (`data-bind="text: Nome"`), não absoluto
(`data-bind="text: Root.Segurados.Segurado.Nome"`).
**Decisão pendente:** Stage 5 deve extrair o segmento final do path quando renderizar
dentro de um repeat element.

### Gap 6 — `detect_repeated_sections` pode criar falsos positivos

**Problema:** o algoritmo agrupa blocos com fingerprint similar (x0, largura, nº palavras).
Campos escalares diferentes mas com a mesma largura podem ser agrupados como coleção.
**Decisão pendente:** adicionar condição de que os blocos agrupados devem representar
o MESMO conjunto de campos repetidos (não campos diferentes que casualmente têm mesma largura).

---

## O que NÃO é gap — fundamentos que estão corretos

- Labels e values SÃO blocos separados nos PDFs Planet Express (confirmado empiricamente)
- O pairing espacial (direita + abaixo) funciona para os padrões desses PDFs
- Com multi-sample, a variabilidade é detectada diretamente por comparação — não precisa de heurística
- O contrato XSD é o que CONFIRMA que um value é dinâmico — `value` é só candidato

---

## Referências

- Modelo template + contrato: `docs/architecture/template-data-contract-model.md`
- Implementação Stage 3 pairing: `backend/services/stages/stage3_structural/classification.py`
- Implementação Stage 4 binding: `backend/services/stages/stage4_mapping/section_matching.py`
- Implementação Stage 5 rendering: `backend/services/stages/stage5_template/html_helpers.py`
