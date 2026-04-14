# Modelo de Template e Contrato de Dados

**Status:** `current`
**Dono:** `@architect`
**Criado:** 2026-04-14
**Atualizar quando:** decisão sobre modelo de binding ou papel do XSD mudar

---

## O que o Migrador produz

O Migrador não extrai dados — ele gera **templates HTML reutilizáveis**.

Esses templates são consumidos por outra ferramenta (o motor de geração) que os preenche com dados e produz o PDF final. O Migrador é a etapa de **autoria do template**, não de geração do documento.

```
PDFs de exemplo  →  [Migrador]  →  Template HTML
                                        │
                     Dados em produção  ▼
                                   Motor de geração  →  PDF final
```

---

## Contrato de Dados — papel e opcionabilidade

O contrato de dados (XSD, JSON Schema ou equivalente) define **quais campos do template são dinâmicos** e qual é o tipo/nome de cada campo.

O contrato é **opcional**. O pipeline produz um resultado válido com ou sem ele:

| Modo | Resultado | Caso de uso |
|------|-----------|-------------|
| **Sem contrato** | Template 100% estático — todos os valores fixados como no PDF de exemplo | Base para edição manual; entregável válido por si só |
| **Com contrato** | Campos mapeados tornam-se dinâmicos `{{Campo}}`; coleções viram `<repeat>` | Entregável completo, pronto para o motor de geração |

Sem contrato, o operador pode **promover campos manualmente no editor** — selecionando um valor e dizendo "este campo é dinâmico, nome: `{{NomeCampo}}`".

---

## Anatomia de um campo: Label e Value

Em documentos gerados por motor, a maioria dos campos segue o padrão:

```
Nome: Rodrigo Agape
```

Onde:
- **Label** (`"Nome:"`) → **sempre fixo** — é texto estrutural do documento, não muda entre instâncias
- **Value** (`"Rodrigo Agape"`) → **potencialmente dinâmico** — muda a cada instância quando mapeado ao contrato

No template gerado:

```html
<!-- Sem contrato -->
<span class="label">Nome:</span>
<span class="static">Rodrigo Agape</span>

<!-- Com contrato, campo mapeado -->
<span class="label">Nome:</span>
<span class="dynamic" data-field="Nome">{{Nome}}</span>

<!-- Com contrato, campo NÃO mapeado -->
<span class="label">Cor:</span>
<span class="static">Branca</span>
```

### O ponto frágil

O Stage 3 detecta label vs value por **posição espacial** (o bloco à esquerda/acima tende a ser label). Essa heurística pode falhar em:

- Campos sem label explícito (valor isolado no layout)
- Tabelas onde headers se parecem com dados
- Layouts em colunas com proximidade espacial ambígua
- Label e value dentro da mesma caixa de texto no PDF

**Consequência:** se o Stage 3 classifica errado, o Stage 4 tenta mapear o label ao contrato em vez do value — o binding vai para o campo errado ou não ocorre.

**Estratégia de mitigação atual:** Gemini no Stage 4 usa contexto semântico para corrigir erros do Stage 3. Não é 100% confiável.

**Estratégia futura desejável:** usar o próprio contrato para inferir a direção — se `"Nome"` existe no XSD e `"Rodrigo Agape"` não, o label é o match e o value é o dinâmico.

---

## Coleções — Seções Repetidas

Quando o PDF contém dados em lista (tabelas, conjuntos de linhas repetidas), o contrato define um **elemento com cardinalidade > 1**:

```
Estados | Sigla
Rio de Janeiro | RJ
Bahia | BA
```

O template resultante usa `<repeat>` em vez de linhas duplicadas:

```html
<!-- Sem contrato: linhas fixas duplicadas (errado para template) -->
<div>Rio de Janeiro | RJ</div>
<div>Bahia | BA</div>

<!-- Com contrato: loop dinâmico (correto) -->
<repeat data-list="Estados[]" data-count="2">
  <div class="repeat-item">
    <span class="dynamic">{{Estado}}</span>
    <span class="dynamic">{{Sigla}}</span>
  </div>
</repeat>
```

### Implicação de paginação

Uma coleção com N itens pode gerar N páginas ou distribuir N itens em múltiplas páginas. O motor de geração é responsável pela lógica de paginação — o template apenas define **a estrutura de um item da coleção**.

O `data-count` no `<repeat>` indica quantos itens existiam no PDF de exemplo — é informativo, não normativo.

---

## Fluxo de binding no pipeline

```
Stage 3: detect_repeated_sections()
         → RepeatedSection[] no document tree
         → label/value classification em cada bloco

Stage 4: run_list_binding()
         → RepeatedSection + XSD array node → ListBinding
         → FieldMappingEntry: label_text + xsd_field_path

Stage 5: _render_repeat_element()   (para coleções)
         _generate_field_html()     (para campos escalares)
         → <repeat data-list="..."> ou <span data-xsd-path="...">{{Campo}}</span>
```

### Sem XSD no Stage 4

Quando o XSD não é fornecido:
- `ListBinding.xsd_list_path = ""`
- `FieldMappingEntry.xsd_field_path = ""`
- Stage 5 renderiza tudo como `class="static"` (sem `{{}}`)
- `coverage_score.percentage` reflete 0% de binding — esperado

---

## Modos de operação do editor (Pilar C)

| Modo | Contrato | O que o operador faz |
|------|----------|----------------------|
| **Auto** | XSD fornecido | Valida bindings gerados pelo pipeline, ajusta edge cases |
| **Manual** | Sem XSD | Seleciona campos no canvas, nomeia, define como `{{Campo}}` |
| **Misto** | XSD parcial | Aceita auto-binding onde existe, completa manualmente o resto |

O editor deve sempre permitir **promoção de estático → dinâmico** independente do modo.

---

## Referências

- Pipeline de detecção: `docs/architecture/pipeline-real.md`
- Contratos entre stages: `docs/architecture/pipeline-contracts.md`
- Implementação de seções repetidas: `backend/services/stages/stage3_structural/repeated_sections.py`
- Implementação de list binding: `backend/services/stages/stage4_mapping/list_binding.py`
- Implementação de loop rendering: `backend/services/stages/stage5_template/html_tree.py`
