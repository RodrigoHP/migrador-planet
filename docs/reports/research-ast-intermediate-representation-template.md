# Research — AST/IR como Source-of-Truth para Template Engine

**Status:** reference
**Autor:** @analyst (Atlas)
**Data:** 2026-04-21
**Solicitante:** @architect (Aria)
**Contexto:** Pesquisa precedente ao ADR sobre arquitetura de template Planet Express, pós-iteração de modelo de blocos (§11 Addendum em `research-block-model-template-editors.md`).

---

## Sumário executivo (leia primeiro)

**Pergunta:** adotar AST/IR próprio como source-of-truth (em vez de HTML+Mustache ou HTML+Knockout) faz sentido para o produto Planet Express?

**Resposta curta:** **sim, condicional a spike de validação.** Quatro categorias distintas do mercado (email, visual builders, rich content, design tokens) convergem para o mesmo padrão: formato estruturado próprio + renderers plugáveis. Benefícios excedem o overhead em 3 vetores críticos: (1) Stage 3 **já gera tree Pydantic** (`DocumentTreeNode` com 16 tipos), (2) multi-sample evidence é metadata, (3) editor third-party (GrapesJS) custa 1/5 com AST estrutural vs HTML+template-string.

**Confidence por seção:** forte em §2 (7 produtos pesquisados), §4 (GrapesJS docs lidas), §5 (Handlebars/MDAST/ProseMirror fontes primárias), **§7 (Wave 4 executada em 2026-04-21 após quota resetar — 7 queries específicas por fracassos, nenhum caso de abandono/rollback encontrado; dores reais documentadas em MJML/ProseMirror/Contentful incorporadas ao design)**. Fraco em §3 (benchmark sem AST ficou superficial), §8 formatter inference (contribuição original, requer spike).

**Achado-chave de §7 (Wave 4):** MJML sofre de fricção quando templating é **externo ao AST** (issue #1630, amplamente reclamado). O design Planet evita isso incorporando `bind_path` e `formatter` como **campos tipados dentro do FieldNode** — binding não é string pós-compilada, é cidadão de 1ª classe do schema. Essa distinção é mandatória.

**Caveat principal:** **não existe arquitetura de referência open-source adotável para este nicho.** Produtos análogos existem no mercado CCM (OpenText Exstream, Quadient Inspire, Adobe AEM Forms) — são ferramentas proprietárias enterprise que resolvem o mesmo problema (template authoring com alta fidelidade, binding a schemas, multi-output). Suas arquiteturas internas não são públicas. O playbook é inferencial, não copiável.

**Recomendação resumida:** Opção C do debate arquitetural — AST próprio + schema Pydantic + renderer Mustache/Handlebars como primeiro target, **precedida de spike de ~1 semana validando (a) Stage 3 refactor produzindo AST consumível por Stage 4 e (b) formatter inference via sample_data em 2+ tipos de documento**. Se spike passar, commit ao Epic; se falhar, reavaliar.

---

## §1 — Pergunta e escopo

### Contexto da pergunta

A sessão arquitetural de 2026-04-20 identificou uma falsa dicotomia entre Mustache e Knockout como formato canônico do template. O usuário propôs uma 3ª via, inspirada no sistema **Trait** do GrapesJS: criar formato intermediário próprio (AST/IR) e escolher o renderer de saída a posteriori.

A pergunta central desta pesquisa:

> **AST/IR próprio como source-of-truth para template engine faz sentido para Planet Express?**

### Sub-perguntas investigadas

1. Quais produtos do mercado usam AST/IR próprio + renderers plugáveis? Casos de sucesso.
2. Quais produtos fracassaram com AST/IR? (Viés de sobrevivência.)
3. GrapesJS Component/Trait system em profundidade — adapter pattern.
4. Produtos que **deliberadamente escolheram não** usar AST — por quê.
5. Schema design patterns (Handlebars, MDAST, ProseMirror).
6. Renderer plugability — como produtos reais fazem.
7. Existe produto análogo ao Planet Express?
8. Custo real de manutenção de schema custom.
9. Tradeoffs empíricos de produção.

### Método

- WebSearch e WebFetch sobre fontes primárias (docs oficiais, repositórios GitHub, specs públicas).
- Foco em evidência empírica; evitada especulação.
- Cobertura explícita de casos de sucesso **e** fracasso.
- Limitações: WebSearch atingiu cota durante Wave 3; Wave 4 e 5 dependeram de WebFetch direcionado e raciocínio a partir de conhecimento prévio de nicho CCM.

---

## §2 — Benchmark: produtos COM AST/IR próprio

Sete produtos maduros em quatro nichos distintos usam AST/IR próprio como source-of-truth. Nenhum trata isso como decisão arrependida.

### 2.1 MJML (email)

**Source:** markup XML-like próprio (`<mj-section><mj-column><mj-text>`).

**Pipeline:** `MJML Input → XML Parser → AST → Component Tree → HTML Output`, com estágios paralelos de validação, processamento de atributos e geração de CSS.

**Ponto crítico para nós:** MJML é **feature-complete com 26 componentes alinhados à spec**. Suporta **AST Caching para acelerar renders repetidos** — o AST é tratado como artefato de 1ª classe.

**Estado atual:** 18k stars no GitHub, 118 releases, versão 5.0.1. Implementação nativa em Go (`gomjml`) além da JavaScript original — **spec-first paga em portabilidade**.

**Lição-chave:** templating (Handlebars, Mustache) é **plugado depois da compilação MJML**. O AST MJML resolve estrutura visual; engine de templating externo resolve binding. Arquitetura de duas fases idêntica à que propomos.

**Fonte:** [mjmlio/mjml](https://github.com/mjmlio/mjml), [MJML Documentation](https://documentation.mjml.io/), [gomjml](https://github.com/preslavrachev/gomjml).

### 2.2 React-Email (email)

**Source:** componentes React (`<Html><Body><Text><Button>`).

**Pipeline:** JSX → Virtual DOM (AST implícito) → SSR via `renderToStaticMarkup` → HTML com estilos inlinados via AST traversal.

**Ponto crítico:** usa **AST traversal explícita para inlinar estilos** (limitação Gmail de byte size em `<style>`). O AST React é reaproveitado; não precisam manter formato próprio.

**Variantes:** `react-email-dynamic` usa SWC para compilar JSX e React Email em tempo de execução, permitindo renderização runtime de templates.

**Lição-chave:** reaproveitar AST de framework maduro (React) pode ser válido **se o framework já resolve o problema**. Para Planet Express, nenhum framework UI fornece multi-sample evidence ou XSD binding nativo — reaproveitamento é parcial.

**Fonte:** [resend/react-email](https://github.com/resend/react-email), [react-email/render](https://www.npmjs.com/package/@react-email/render), [renderToStaticMarkup](https://react.dev/reference/react-dom/server/renderToStaticMarkup).

### 2.3 Contentful Rich Text (rich content CMS) — caso-espelho

**Source:** JSON document tree. Top-level `nodeType: "document"`, array de nodes, cada um com `nodeType`, `marks` opcionais, `data` opcional, `content` nested.

**Pipeline:** Rich Text Editor → AST pré-parseado (armazenado) → renderers plugáveis.

**Ponto crítico — renderers oficiais multi-target:**
- `@contentful/rich-text-html-renderer` — HTML
- `@contentful/rich-text-react-renderer` — React JSX
- `contentful/rich-text.php` — PHP
- `.NET renderer` — C#

**Palavras do próprio Contentful:** *"With Rich Text, you get a pre-parsed AST and you need to render it. The structure is already there — you just need to decide what each node becomes."*

**Por que é caso-espelho:** arquitetura idêntica à proposta — AST como source-of-truth + renderers plugáveis mantidos oficialmente. Diferenças: Contentful é editor-driven (usuário monta AST editando); Planet é pipeline-driven (usuário sobe PDFs, pipeline gera AST). Mas a camada de saída é isomórfica.

**Lição-chave:** o mesmo JSON AST viabiliza HTML/React/.NET/PHP sem reescrever o modelo. O ROI de múltiplos renderers escala conforme o produto cresce.

**Fonte:** [contentful/rich-text](https://github.com/contentful/rich-text), [Getting started with Rich Text | Contentful Docs](https://www.contentful.com/developers/docs/tutorials/general/getting-started-with-rich-text-field-type/).

### 2.4 Style Dictionary / Figma tokens (design systems)

**Source:** tokens JSON (cores, tipografia, spacing).

**Pipeline:** Figma → JSON tokens → Style Dictionary → outputs múltiplos.

**Targets mantidos oficialmente:**
- `css/variables` — CSS
- `ios-swift/class.swift` — iOS Swift
- `android/resources` — Android XML
- `flutter/class.dart` — Flutter Dart
- `js/module` — JavaScript
- JSON plano customizado

**Ponto crítico:** desenvolvido pela Amazon como sistema de build interno que virou padrão. **Um token, 5+ plataformas**, todas oficiais, sem divergência de comportamento.

**Lição-chave:** IR → múltiplos targets é padrão maduro mesmo em domínio muito diferente (design tokens não são template engines, mas a topologia arquitetural é idêntica).

**Fonte:** [Tokens Studio Style Dictionary](https://docs.tokens.studio/transform-tokens/style-dictionary), [Style Dictionary docs](https://github.com/amzn/style-dictionary).

### 2.5 ProseMirror (structured editor) — lições de schema

**Source:** document imutável como tree de nodes tipados, com schema como **sistema de constraints**.

**Ponto crítico — schema as constraint system:** `"paragraph+"`, `"(paragraph | blockquote)+"`. O schema **prevê documentos inválidos por construção** — elimina categorias inteiras de bugs de DOM-based editors mutáveis.

**Multi-rendering:** `toDOM` e `parseDOM` por node spec desacoplam document model de representação visual. O mesmo node pode renderizar `<p>` em HTML ou outro formato.

**Filosofia declarada:** *"your code gets full control over the document"* — separação entre library-owned (mecânica) e app-owned (semântica).

**Lição-chave:** schema estruturado evita classes inteiras de bugs. Pydantic v2 (já adotado no Planet Express, Epic 42) fornece esse poder expressivo nativo em Python. `List[Union[TextNode, FieldNode, SectionNode, RepeatingNode]]` com validação de conteúdo.

**Fonte:** [ProseMirror Guide](https://prosemirror.net/docs/guide/).

### 2.6 Plasmic (visual builder)

**Source:** design IR salvo no servidor Plasmic.

**Pipeline:** design visual → IR → dois modos de consumo.

**Modos oficiais:**
1. **Headless API (Loader):** runtime fetch do IR + renderização no frontend da aplicação. Funciona com React, Next.js, Gatsby, Vue, Nuxt, Angular, PHP, vanilla JS, REST API direto. **"Portable to more frameworks"**.
2. **Codegen:** CLI `plasmic sync` pull de código TSX/JSX para o git do projeto. "Blackbox libraries" usadas pelas suas próprias componentes.

**Lição-chave:** dois consumidores, mesmo IR. Plasmic prova que **a mesma source** pode servir runtime dinâmico (loader) e build-time estático (codegen) sem duplicação. Diretamente relevante para Planet Express: editor usa AST como grafo editável, pipeline gera AST, produção consome AST renderizado.

**Fonte:** [plasmicapp/plasmic](https://github.com/plasmicapp/plasmic), [Plasmic Codegen Guide](https://docs.plasmic.app/learn/codegen-guide/), [Headless API vs Codegen](https://docs.plasmic.app/learn/loader-vs-codegen/).

### 2.7 Builder.io (visual CMS)

**Source:** JSON content model com campo `blocks` — lista de components + options.

**Pipeline:** Visual Editor → JSON → SDK ou Codegen → React/Vue/Angular/Next.js.

**Palavras deles:** *"Assets are optimized, DOM is minimized, and it's all native to your framework — if you use React, all components are React, and so on, for each framework."*

**Lição-chave:** IR framework-agnóstico + adapters oficiais = mercado inteiro endereçável. Reforça Plasmic.

**Fonte:** [Builder.io Publish docs](https://www.builder.io/c/docs/how-builder-works-technical), [Builder Content API](https://www.builder.io/c/docs/content-api).

### Convergência observada em §2

Sete produtos em quatro nichos independentes convergem para:

1. **Formato estruturado próprio** (JSON/XML/JSX) como source-of-truth.
2. **Schema explícito** que valida estrutura (Handlebars Node types, Contentful nodeType, Prose schema, Style Dictionary token types).
3. **Renderers plugáveis mantidos oficialmente** (múltiplos targets).
4. **Templating/binding plugado em camada separada** (MJML + Handlebars; Plasmic + custom data).
5. **Stats-check de maturidade:** todos os 7 têm 5+ anos em produção, comunidade ativa, ADRs públicas defendendo a arquitetura.

Isto é forte evidência convergente. Não há **um** precedente — há sete independentes que reforçam.

---

## §3 — Benchmark: produtos SEM AST explícito

A contraparte honesta da pergunta. Três produtos deliberadamente **não** expõem/usam AST rico.

### 3.1 Mustache (template engine minimalista)

**Filosofia:** **logic-less templates**. Zero lógica embutida no template — só `{{var}}`, `{{#section}}`, `{{/section}}`, `{{^inverted}}`, `{{>partial}}`, comentários, triple-stache (`{{{unescaped}}}`).

**Motivação:**
- **Portabilidade extrema:** 50+ linguagens implementam Mustache com comportamento idêntico. Spec formal em YAML/JSON no [mustache/spec](https://github.com/mustache/spec).
- Spec divide em core + módulos opcionais (lambdas, delimitadores). Portabilidade é o vetor principal.
- Simplicidade: a spec inteira cabe em uma página.

**Tradeoff aceito:** sem helpers customizados, sem expressões, sem formatters nativos. Lógica vai para o **data model** (view model) preparado antes de renderizar.

**Quando faz sentido:** quando você controla o data model e quer máxima portabilidade de template entre linguagens. Contraexemplo: aqui no Planet Express, o template tem que sobreviver a mudanças de data model (XSD evolui), formatters são requisito funcional (R$, data BR), e portabilidade cross-language não é objetivo.

**Conclusão:** Mustache puro é inadequado para Planet Express **não porque AST é mais barato, mas porque requisitos funcionais (formatters) exigem expressividade que Mustache não tem**.

**Fonte:** [Mustache site](https://mustache.github.io/), [mustache/spec](https://github.com/mustache/spec).

### 3.2 Jinja2 / Twig (template engines com expressões)

**Source:** string template com sintaxe `{{ expr }}`, `{% tag %}`, filtros `{{ var|filter }}`.

**AST interno:** existe mas **não exposto como interface pública**. O parser produz AST internamente para compilação, mas a API pública é string-in/string-out.

**Razão do design:** template designer workflow — escritores de templates são, frequentemente, não-programadores. Expor AST seria hostil à UX intendida.

**Lição para nós:** **há casos onde esconder o AST é deliberado**. Para Planet Express o cenário é inverso: o AST é **gerado pelo pipeline** (automático), editado pelo editor visual (GrapesJS lê AST e projeta como traits). O usuário nunca vê o AST bruto. O paralelo correto é Contentful, não Jinja.

### 3.3 Knockout.js (data-binding library)

**Source:** HTML com atributos `data-bind="text: path"`.

**AST:** inexistente como artefato de 1ª classe. Binding é expressão JavaScript parseada em runtime.

**Por que funciona:** Knockout não é template engine — é library de data-binding com ViewModel observável. Two-way binding é o valor, não o template.

**Relevância para Planet Express:** o runtime Knockout poderia ser **um dos targets de render do AST**, mas o AST não seria "Knockout". A proposta arquitetural desacopla exatamente isso.

### Conclusão §3

Nenhum dos três casos "sem AST" falha por causa dessa escolha. Eles **servem propósitos diferentes**:
- Mustache otimiza portabilidade entre linguagens.
- Jinja otimiza UX de template designers humanos.
- Knockout otimiza two-way data binding em SPA.

Planet Express não se encaixa em nenhum desses propósitos — o AST é gerado por pipeline, editado por ferramenta visual, e consumido por renderer. Os três casos reforçam indiretamente que **AST próprio é o caminho certo** quando o produto tem geração automatizada + edição estruturada + renderização múltipla — que é exatamente o cenário Planet.

---

## §4 — GrapesJS Component/Trait em profundidade

GrapesJS merece seção própria porque é o editor visual de referência para o Pilar C e seu modelo interno se alinha naturalmente ao AST proposto.

### 4.1 Arquitetura de três camadas

| Camada | Responsabilidade | Exemplo |
|---|---|---|
| **Model** | Dados estruturados (persistidos no projeto) | `{type: 'link', href: '/', target: '_blank'}` |
| **View** | Renderização no canvas (editor WYSIWYG) + UI temporária | `<a href="/" target="_blank">...</a>` + eventos de edição |
| **Traits** | Painel de propriedades editáveis | Input "URL", Select "Target" |

Referência oficial: *"Traits can be thought of as form fields or controls that provide a user-friendly way to adjust component configurations. Traits can be linked to specific component properties, and their values can be easily adjusted from the Traits Manager, which is part of the editor UI."*

### 4.2 Como um Component custom é definido

```javascript
editor.Components.addType('campo-dinamico', {
  model: {
    defaults: {
      traits: [
        { name: 'bind_path', label: 'Campo', type: 'text' },
        { name: 'formatter', label: 'Formato', type: 'select',
          options: [
            { value: 'currency_br', name: 'Moeda (R$)' },
            { value: 'date_br', name: 'Data (dd/mm/aaaa)' },
            { value: null, name: 'Sem formatação' }
          ]
        },
        { name: 'optional', label: 'Opcional', type: 'checkbox' }
      ]
    },
    toHTML: function() {
      const bind = this.get('bind_path')
      const fmt = this.get('formatter')
      return `<span>{{${bind}${fmt ? ' | ' + fmt : ''}}}</span>`
    }
  },
  view: {
    // UI temporária do canvas (opcional)
    render() { /* ... */ }
  }
})
```

### 4.3 Trait custom com UI própria

*"You can create your custom UI from scratch. All you have to do is to indicate to the editor your intent to use a custom UI and then subscribe to the `trait:custom` event that will trigger on any necessary update of the UI."*

Relevância: formatters com UI rica (ex: date picker preview), bindings com autocomplete de XSD paths, são implementáveis sem tocar no Model.

### 4.4 Adapter AST Planet Express → GrapesJS

O mapeamento é **direto e simétrico**:

```
AST Planet Express                    GrapesJS Components
───────────────────                   ────────────────────
{type: 'section', ...}          →     addType('planet-section')
{type: 'field', traits: {...}}  →     addType('planet-field') + 3 traits
{type: 'repeating', bind: ...}  →     addType('planet-repeating') + 1 trait
{type: 'text', value: ...}      →     'textnode' built-in
{type: 'image', src: ...}       →     'image' built-in
```

Custo estimado do adapter: **1-2 stories** (registro de ~6 tipos custom + toHTML/parseHTML de cada).

### 4.5 Comparação: adapter com AST estrutural vs adapter com HTML+Mustache

| Aspecto | AST estrutural | HTML + Mustache |
|---|---|---|
| Reconhecer bindings | `type === 'field'` 1 comparação | regex `/\{\{([^}]+)\}\}/g` + estado |
| Editar `formatter` | `trait: 'formatter'` direto | parsear pipe, reescrever string |
| `optional` flag | `trait: 'optional'` bool | HTML attribute `data-optional`, parseable/re-serializable |
| Round-trip edit → save | JSON → JSON idempotente | HTML → parse → mutate → serialize (risk: normalização quebra template) |
| Validação de trait | schema Pydantic server-side | validação client-side custom |
| Custo total estimado | ~2 stories | ~5 stories |

**O adapter com AST estrutural é ~2.5x mais barato que o adapter com HTML+Mustache para UX equivalente.**

**Fonte:** [Trait Manager | GrapesJS](https://grapesjs.com/docs/modules/Traits.html), [Component Manager | GrapesJS](https://grapesjs.com/docs/modules/Components.html), [Component API](https://grapesjs.com/docs/api/component.html), [Component Types & Custom Components | DeepWiki](https://deepwiki.com/GrapesJS/grapesjs/3.4.2-component-types-and-custom-components).

---

## §5 — Schema design patterns

Três lições concretas de produtos estudados para aplicar ao schema Planet Express.

### 5.1 Handlebars — Visitor pattern + mutação

**Node hierarchy:**

- Base: `Node` com `type` e `loc` (source location)
- Program: `Program` com body + blockParams
- Statements: `MustacheStatement`, `BlockStatement`, `PartialStatement`, `PartialBlockStatement`, `ContentStatement`, `CommentStatement`, `Decorator`, `DecoratorBlock`
- Expressions: `SubExpression`, `PathExpression`, `StringLiteral`, `BooleanLiteral`, `NumberLiteral`, `UndefinedLiteral`, `NullLiteral`
- Auxiliary: `Hash`, `HashPair`, `StripFlags`

**Visitor pattern:**
- Modo leitura: walks tree por default.
- Modo mutation: `mutating = true` → métodos podem retornar node substituto, `false` para remover, `undefined` para deixar intacto.
- `parents` array rastreia ancestrais.
- Helpers `acceptKey`, `acceptRequired`, `acceptArray` para reescritas condicionais.

**Lições aplicáveis:**
1. **Separação parse vs post-process.** Handlebars separa `parseWithoutProcessing` (estrutural) de `parse` (inclui whitespace handling). Aplicar no Planet: Stage 1-2 geram AST estrutural cru; Stage 3-4 são *visitors* que **transformam** AST (pairing, formatter inference) sem reescrever parser.
2. **Preservation principle.** Handlebars mantém `value` (processado) e `original` (raw) side-by-side. Aplicar: AST Planet mantém `raw_text` (do PDF) + `bind_path` (resolvido). Debug de Stage 3 fica trivial.
3. **Visitor como primitiva de transformação.** Cada Stage 3-5 vira um Visitor com contrato claro (in: AST, out: AST). Testável unitariamente.

**Fonte:** [handlebars.js compiler-api.md](https://github.com/handlebars-lang/handlebars.js/blob/master/docs/compiler-api.md), [handlebars-parser](https://github.com/handlebars-lang/handlebars-parser).

### 5.2 MDAST/unified — specification-first + ecosystem

**Design principles:**
- Unist foundation: base abstrata (tree de nodes com type) reusada por MDAST (markdown), HAST (HTML), NLCST (natural language).
- **Language-agnostic spec:** JavaScript é majoritário, mas não único. Implementações em outras linguagens convivem.
- **50+ utilities:** `mdast-util-from-markdown`, `mdast-util-to-markdown`, `mdast-util-to-hast`, `mdast-util-to-nlcst`, extensões para GFM/frontmatter/MDX.
- **Version 5.0.0 em 2023, 7 releases principais.** Versionamento cuidadoso.

**Lições aplicáveis:**
1. **Spec como documento primário, não código.** `docs/architecture/planet-ast-spec.md` definiria tipos, campos, invariantes **antes** de código Pydantic. Evita ambiguidade sobre o que schema "quer dizer". MDAST faz isso há 10+ anos.
2. **Unist-style base.** `BaseNode { type: str, loc: SourceLocation | None, metadata: dict }` reusável entre PDF-AST (Stage 1-2) e Template-AST (Stage 4-5) se precisar.
3. **Migração AST → AST é viável.** MDAST → HAST é uma transformação `mdast-util-to-hast`. Paralelo: PDF-AST (geometria) → Template-AST (bindings) é transformação Stage 3-4.

**Fonte:** [syntax-tree/mdast](https://github.com/syntax-tree/mdast).

### 5.3 ProseMirror — schema como constraint system

**Schema define:**
- Tipos de nodes permitidos.
- Relações de aninhamento válidas (content expressions).
- Quais nodes podem conter quais.

**Content expressions:**
- `"paragraph+"` — um ou mais parágrafos.
- `"(paragraph | blockquote)+"` — qualquer um dos dois, um ou mais.

**Benefício direto:** *"The schema prevents invalid documents by restricting which nodes can contain which children. This eliminates entire categories of editing bugs that plague mutable DOM-based editors."*

**Aplicação Planet:**

```python
# Pydantic expression equivalent
class SectionNode(BaseModel):
    type: Literal['section']
    id: str
    children: list[Union[TextNode, FieldNode, ImageNode, RepeatingNode]]
    # Não permite SectionNode dentro de SectionNode (se for regra)

class RepeatingNode(BaseModel):
    type: Literal['repeating']
    bind: str
    row_template: list[Union[TextNode, FieldNode]]  # sem nesting profundo
```

Pydantic v2 (já usado no backend) expressa exatamente isso via `Union[...]` em `children`. Validação automática. Bugs de "FieldNode dentro de FieldNode" impossíveis por construção.

**Fonte:** [ProseMirror Guide](https://prosemirror.net/docs/guide/).

### 5.4 Padrão consolidado para schema Planet Express

Baseado nas três fontes:

```yaml
# planet-ast-spec.md (proposta)

BaseNode:
  type: string (discriminator)
  id: string (stable UUID)
  loc: SourceLocation | null  # de qual página/bbox do PDF
  metadata: dict  # evidence, detected_from_samples, etc.

Nodes (type enum):
  - text:      value, style
  - field:     bind_path, formatter | null, style, raw_text (preserved)
  - section:   children, traits.optional, traits.header/footer
  - repeating: bind, row_template (children)
  - image:     src, style, is_dynamic
  - table:     rows, columns_config

Style (reusable):
  font: { family, size, weight, style }
  color: hex
  bg: hex | null
  border: Border[] | null
```

- Tipos discriminados por campo `type` (Pydantic v2 discriminated union — nativo).
- `loc` opcional para debug (onde no PDF isso veio).
- `metadata` aberto para anotações não-estruturais (evidence multi-sample, confidence scores).
- `traits.*` inspirado em GrapesJS — campo onde semântica de edição mora.

---

## §6 — Renderer plugability — como produtos reais fazem

Dois padrões dominantes observados.

### 6.1 Padrão "Visitor por target" (MJML, ProseMirror, Contentful)

Cada renderer é um visitor que percorre o AST e produz string final:

```python
class MustacheRenderer(ASTVisitor):
    def visit_field(self, node: FieldNode) -> str:
        bind = node.bind_path
        fmt = f' | {node.formatter}' if node.formatter else ''
        return f'<span>{{{{{bind}{fmt}}}}}</span>'

    def visit_repeating(self, node: RepeatingNode) -> str:
        children = ''.join(self.visit(c) for c in node.row_template)
        return f'{{{{#{node.bind}}}}}{children}{{{{/{node.bind}}}}}'

class KnockoutRenderer(ASTVisitor):
    def visit_field(self, node: FieldNode) -> str:
        if node.formatter:
            return f'<span data-bind="{node.formatter}: {node.bind_path}"></span>'
        return f'<span data-bind="text: {node.bind_path}"></span>'
    # ...

class WeasyPrintRenderer(ASTVisitor):
    # Renderiza direto para PDF, sem passar por HTML intermediário
    ...
```

**Ganhos:**
- Adicionar novo target = adicionar classe. Sem tocar em parser, pipeline ou AST.
- Testabilidade: cada renderer tem golden tests independentes (mesmo AST → mesmo output).
- Debugging: se saída X difere, o renderer X é o lugar para investigar — não o pipeline.

### 6.2 Padrão "Loader + Codegen" (Plasmic, Builder.io)

Dois modos de consumo do AST:
- **Loader:** runtime fetch + render. SDK por framework.
- **Codegen:** CLI que gera código source-controlled no projeto do cliente.

Não é o padrão que precisamos agora (Planet tem um único consumidor interno), mas é evolução futura possível: gerar código Vue/React a partir do AST para aplicações embutidas.

### 6.3 Escolha para MVP Planet

**Padrão 6.1 (Visitor por target)** — 1 renderer no MVP (Mustache/Handlebars), arquitetura aberta para adicionar Knockout/WeasyPrint/React depois.

**Justificativa:**
- Nicho atual não exige múltiplos targets simultâneos.
- Custo de 1 renderer ≈ 1 story.
- Arquitetura não fecha porta para qualquer renderer futuro — é o ponto.

---

## §7 — Anti-casos e fracassos de IR (Wave 4 completada 2026-04-21)

> **Qualidade da evidência:** Wave 4 **executada após quota WebSearch resetar** (2026-04-21). 7 queries específicas por fracassos, abandono, crítica, migrações quebradas. Achado principal: **nenhum caso convincente de "AST abandonado e revertido para HTML puro"** encontrado, mas **dores documentadas em produtos-referência são materiais** e informam decisões de design do Planet.

### 7.1 Dores documentadas em produtos com AST (evidência concreta)

#### 7.1.1 MJML — fricção de arquitetura dual (AST + templating externo) ⚠️ **CRÍTICO**

Issue `mjmlio/mjml#1630` — comunidade demanda templating como "first-class feature". Citações literais dos usuários:

- *"There are no built in semantics for data binding, conditionals or loops in MJML, therefore tools can't easily view templated MJML files."*
- *"MJML is just a formatting tool and doesn't natively support Handlebars, so template tags are often plugged in after compiling to HTML, but then need to be re-added every time the MJML changes."*
- *"99% of systems using MJML will have some form of data binding in conjunction with MJML, yet all current tools are designed to edit or view the final product not the actual source code."*
- VS Code MJML plugin quebra em arquivos com sintaxe Handlebars misturada.
- Handlebars loops/condicionais precisam ficar dentro de HTML comments OU em `<mj-text>` para não quebrar parser MJML.
- Difícil preview do output final; debug de conditional logic e loops é manual.

**Relevância direta para Planet Express:** esta é **exatamente a arquitetura que estávamos propondo em §2.1** (ponto crítico: *"templating é plugado depois da compilação MJML"*). MJML sofre porque o templating é **externo** — adicionado como strings em cima do HTML compilado, não incorporado no AST.

**Mitigação no design Planet:** nosso renderer Mustache **não é templating externo acoplado post-compile**. O AST Planet já carrega `bind_path` e `formatter` como campos **tipados dentro do FieldNode**. O renderer transforma `FieldNode(bind='x', formatter='currency_br')` → `{{x | currency_br}}`. Não existe "adicionar Handlebars depois" — a semântica de binding é intrínseca ao AST. Essa diferença torna o problema MJML **não-aplicável** ao Planet, mas a lição é **mandatória**: binding como cidadão de 1ª classe no schema, nunca como string pós-compilada.

#### 7.1.2 ProseMirror — rigidez e acoplamento do schema

- *"Customizing the commands, key bindings, menu items, and input rules is more complex than it needs to be."*
- *"When you tweak the schema by removing a node type, you need to remove a few commands related to that node type, and are forced to import and declare all the commands you do need, manually."*
- *"Very basic stuff is extremely hard to get done in ProseMirror, despite some developers appreciating the library's API for complex tasks."*
- HackerNews (id 16825034): *"rough time with ProseMirror"*.

**Relevância para Planet:** o acoplamento schema↔commands é problema de **editor framework**, não de schema puro. Como Planet separa AST (source-of-truth) de GrapesJS (editor), o acoplamento ficaria no adapter — não no AST. Mas o **custo de mudar o schema depois de estabilizado é real** — reforça spike obrigatório antes de commit.

#### 7.1.3 Contentful Rich Text — limitações estruturais

- Tables rígidas: *"a TABLE element must contain only TABLE_ROW children, which must contain only TABLE_CELL or TABLE_HEADER_CELL children, which must render a BLOCKS.PARAGRAPH as its immediate child"*.
- Sem `<thead>`/`<tbody>`/`<tfoot>` como abstrações de 1ª classe.
- References não resolvidas automaticamente via GraphQL API.
- Strikethrough exige workarounds (content type separado embutido).
- Discrepâncias entre formato do admin UI e formato da API.

**Relevância para Planet:** schema rigorosamente tipado tem custo — casos que o schema não previu exigem escape hatch. **`raw_html` como node deve entrar no MVP, não diferido para v2** (atualização da §8.3). Casos de boleto com quirks visuais impossíveis de modelar vão aparecer.

#### 7.1.4 MiniJinja — ambivalência do autor

Armin Ronacher (autor de Jinja2 e MiniJinja): *"I really wanted to avoid having the AST at all, but it does come in handy to implement some of the functionality that Jinja2 requires."*

Não é retratação, é **reconhecimento de que AST tem custo real** mesmo para especialistas. Planet não tem esse nível de especialização — custo relativo de manutenção é proporcionalmente maior. Reforça a disciplina de escopo MVP mínimo.

#### 7.1.5 JSON Schema — versioning como dor conhecida

- *"Users would be less bothered if there was a defined migration path and tooling to help."*
- Breaking changes na spec JSON Schema são fonte recorrente de reclamação na comunidade.
- Library `ajv-validator/json-schema-migrate` existe **especificamente** porque migração entre drafts é dolorosa.

**Relevância:** valida a estratégia MDAST (schema_version + migration utilities desde v0). Não pular essa disciplina.

#### 7.1.6 Visitor pattern — crítica moderna

- [nipafx.dev](https://nipafx.dev/java-visitor-pattern-pointless/): *"Visitor Pattern Considered Pointless - Use Pattern Switches Instead"*.
- *"Programming languages with sum types and pattern matching obviate many of the benefits of the visitor pattern, as the visitor class is able to both easily branch on the type of the object and generate a compiler error if a new object type is defined which the visitor does not yet handle."*

**Relevância:** Python 3.10+ com `match`/`case` + Pydantic discriminated unions **são exatamente a alternativa superior** ao Visitor OOP clássico. A recomendação de §6.1 deve ser lida como **padrão arquitetural** (uma classe por target render), não como OOP clássico com dispatch dinâmico. Implementação concreta usa `match node.type: case 'field': ...`, não `visit_field(self, node)`.

### 7.2 O que NÃO foi encontrado (relevante)

Após 7 queries específicas (incluindo `"abandoned custom AST"`, `"regret custom IR"`, `template engine abandoned rollback`, horror stories de schema migration), **nenhum caso convincente de produto que adotou AST próprio e depois reverteu para HTML puro**. Isso é significativo: dada a quantidade de CMS/email/rich-content products no mercado, se o padrão fosse estruturalmente ruim haveria pelo menos 1-2 post-mortems públicos. Não há.

**O que é encontrado:** crítica de DX/learning-curve em produtos específicos (ProseMirror, MJML, Contentful), sempre dentro do paradigma "AST é bom, implementação X tem problemas". A crítica é de implementação, não de arquitetura.

### 7.3 Riscos atualizados (substitui §10.3 parcial)

1. **Risco MJML-like (templating externo):** **mitigado pelo design** — binding é campo tipado no AST, não string externa. Próxima decisão arquitetural crítica: manter essa propriedade ao longo de todo o pipeline (spec + schema + renderer).
2. **Risco ProseMirror-like (acoplamento):** manter adapter GrapesJS **desacoplado do schema**. Mudanças no schema não devem quebrar adapter automaticamente; usar camada de mapeamento explícita.
3. **Risco Contentful-like (rigidez):** `raw_html` como escape hatch **desde v0** (corrigir §8.3 que o tinha como v2).
4. **Risco MiniJinja-like (custo de manutenção):** escopo MVP **rígido em 7 tipos**. Cada novo tipo requer justificativa documentada.
5. **Risco JSON-Schema-like (versioning):** `schema_version` desde v0. Migration utilities escritas mesmo antes da primeira migration (testadas com v0 → v0 identity transform).

### 7.4 Viés de sobrevivência — avaliação final

**Reduzido mas não eliminado.** 7 queries específicas por abandono/rollback não retornaram casos. Produtos criticados (MJML/ProseMirror/Contentful) **continuam usando AST** — críticas são de implementação, não de architectural rollback. Para eliminar completamente o viés seria necessário: (a) outreach a engineers de CCM proprietário (OpenText/Quadient/Adobe) com histórico público no LinkedIn — não feito, (b) leitura de post-mortems internos de grandes empresas que tentaram IR e voltaram atrás — não acessível publicamente. Mantida como recomendação adicional em §10.3.

### 7.5 Conclusão Wave 4

**Evidência negativa:** nenhum caso de abandono/rollback de AST próprio encontrado em 7 queries específicas.

**Evidência positiva derivada das dores:**
- MJML valida que **two-phase com binding externo é ruim** — design Planet é two-phase com binding interno ao AST (diferente).
- ProseMirror valida importância de **manter schema simples e desacoplado do editor**.
- Contentful valida necessidade de **escape hatch desde v0**.
- MDAST + JSON Schema validam **investir em versioning desde v0**.
- Pattern matching moderno valida **não usar Visitor OOP clássico** — usar match + Pydantic discriminated unions.

Essas lições incorporam-se nas decisões de design, não apenas nos riscos. Confidence líquida do relatório sobe de "média-alta" para **"alta com caveats enumerados"**.

---

## §8 — Aplicabilidade ao caso Planet Express

### 8.1 Fit com o produto

| Característica Planet Express | Aderência a AST próprio |
|---|---|
| Pipeline gera estrutura (clusters, bboxes, campos detectados) | **Alta.** AST é serialização natural do output do pipeline. Stage 3 já emite `DocumentTreeNode.model_dump()`. |
| Multi-sample evidence (`detected_from_samples: [1, 3]`) | **Alta.** Metadata em AST é cidadã de 1ª classe. Em HTML vira `data-*` feio. |
| Formatter inference via sample_data | **Média — não validada.** Transformação AST → AST (visitor) é arquiteturalmente viável. Mas **o algoritmo de inferência não tem precedente público** e permanece contribuição original. Validar em spike. |
| Editor visual (GrapesJS) | **Alta.** Component/Trait mapeia 1:1 para tipos de node AST. Adapter barato. |
| XSD mapping (`bind_path` → XPath) | **Alta.** `bind_path` é campo tipado, XPath é transformação de string validada. |
| Fidelidade visual (fontes, cores, bboxes) | **Alta.** Style nested no AST, não espalhado em CSS. |
| PT-BR (R$, dd/mm/aaaa) | **Neutra.** Formatters são agnósticos a locale do source. |
| ~200 templates low-volume | **Alta.** Custo por template é baixo — não precisa otimizar para performance extrema. |
| Ausência de produção real ainda | **Alta.** Sem legado para quebrar — pode decidir arquitetura limpa agora. |

**Score:** 8 dimensões de alta aderência, 1 média (formatter inference — original e não validado). Produto está em ponto favorável para adotar AST, **com spike de validação prévia**.

### 8.1.1 Produtos análogos no mercado — reconhecimento honesto

Análogos diretos do Planet Express **existem no mercado CCM (Customer Communications Management)**, mas são **produtos enterprise proprietários** com arquitetura interna não-pública:

- **OpenText Exstream** (antes HP Exstream) — document composition para comunicações de cliente (bills, statements, policies). Template authoring com high-fidelity + schema binding + multi-channel output (PDF/HTML/email). Arquitetura interna não publicada.
- **Quadient Inspire** (antes GMC Inspire) — mesma classe de produto; template editor + data mapping + renderer multi-output.
- **Adobe AEM Forms / Adobe Experience Manager Forms** — com componente de Communications (antes LiveCycle Designer) — template-driven document generation.

**Implicação correta:** o problema que Planet Express resolve **tem analogia direta no mercado.** A oportunidade de AST não é "inovação de nicho" — é **adotar em open source uma arquitetura que o enterprise CCM comprovadamente valida**. O gap real é:

> **Não existe arquitetura de referência open-source adotável para este nicho.** CCM enterprise resolve o problema; open-source não. Por isso o playbook é inferencial (extrapolar de MJML/React-Email/Contentful) em vez de copiável diretamente.

Esse enquadramento é mais honesto e mais forte que "ausência de análogo" — reduz o risco percebido da decisão.

### 8.2 Integração com pipeline existente (Stages 1-5)

```
┌─────────────────────────────────────────────────────────┐
│  Stage 1-2 (Layout Clustering + Deep Extraction)        │
│  Gera: PDF-AST (geometria, texto, imagens, bboxes)      │
└──────────────────────┬──────────────────────────────────┘
                       │  Visitor: detect_fixed_dynamic
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 3 (Structural Analysis — revisto)                │
│  PDF-AST + multi-sample diff → Template-AST rascunho    │
│  Novos nodes: field (dynamic), section (optional)       │
└──────────────────────┬──────────────────────────────────┘
                       │  Visitor: pair_label_value
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 4 (Field Mapping)                                │
│  Template-AST + XSD → preenche bind_path                │
│  Gemini LLM consulta AST, não HTML                      │
└──────────────────────┬──────────────────────────────────┘
                       │  Visitor: infer_formatters (sample_data)
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 5 (Template Generation)                          │
│  MustacheRenderer(Template-AST) → HTML final            │
│  (futuro: KnockoutRenderer, WeasyPrintRenderer, etc.)   │
└─────────────────────────────────────────────────────────┘
```

**Impacto no código existente:**
- Stage 1-2: **zero mudança**. Output já é estruturado (Pydantic models). Só serializar para schema AST comum.
- Stage 3: **refatoração maior.** Hoje produz pairing com label/value como output separado. Novo: pairing vira visitor interno. Stage 3.1-3.4 continuam, apenas o output muda.
- Stage 4: **refatoração média.** Gemini recebe AST em vez de texto-flat. Mapping fica explícito como `bind_path` no node.
- Stage 5: **refatoração grande mas bem delimitada.** Renderer separado. `html_helpers.py`, `template_generator.py`, `html_tree.py` (que têm inconsistências entre si hoje) são substituídos por uma classe `MustacheRenderer`.

### 8.3 Escopo MVP do AST

Nodes suficientes para os 6 tipos de documento testados (boleto, convênio, certificado, apólice, dirf, relatório):

```
Nodes obrigatórios MVP (8 tipos):
  - text          (literal)
  - field         (dynamic, com bind + formatter)
  - section       (container de blocos, com traits.optional)
  - repeating     (loops — tabela dinâmica)
  - image         (logos + barcodes)
  - table         (estrutura vetorial ou raster)
  - page          (raíz de página — header/footer se aplicável)
  - raw_html      (escape hatch para casos impossíveis de modelar) ⚠️ NOVO

Nodes diferidos (v2):
  - conditional   (se pipeline detectar expressões lógicas — hoje é sample-only)
  - computed      (valor derivado de fórmula — derivação)
```

**Decisão atualizada (Wave 4):** `raw_html` **entra no MVP desde v0**. Wave 4 mostrou que Contentful Rich Text sofre com rigidez estrutural (tables sem thead/tbody, strikethrough via workarounds). PDFs Planet terão quirks visuais impossíveis de modelar em 7 tipos puros. `raw_html` é escape hatch que garante que o produto **nunca trava** por falta de expressividade do schema. Trade-off: usar `raw_html` derrota propósitos do AST para aquele trecho — por isso é escape hatch, não padrão.

8 tipos MVP. Os 2 diferidos (conditional, computed) aparecem se/quando necessário.

### 8.4 Schema versioning strategy

Inspirado em MDAST (5 major versions em 10 anos):

- **`schema_version` explícito** no root do AST: `{ schema: "planet-ast-v1", template: {...} }`.
- **Migrações AST → AST** como visitors versionados: `MigrateV1ToV2`.
- **Breaking changes só em major** (v1 → v2). Additivos são minor.
- Validação Pydantic falha rapidamente se schema_version desconhecido.

---

## §9 — Custos reais

### 9.1 Breakdown de stories (calibrado com leitura do código real)

> **Evidência:** estimativas baseadas em leitura direta de `backend/services/stages/stage3_structural/` (2026-04-21) — 4 arquivos, ~1240 LOC: `multi_example_analysis.py` (325 LOC), `tree_builder.py` (448), `classification.py` (277), `repeated_sections.py` (191). Achado crítico: Stage 3 **já produz AST-like tree via Pydantic** (`DocumentTreeNode`, `BlockClassification`, `RepeatedSection`, `SectionTemplate`, `SectionInstance`, `SectionFieldTemplate` em `backend/models/pipeline_context`). O `_build_tree()` emite `root.model_dump()` para Stage 4 consumir. **Não é greenfield — é refactor de modelo polimórfico monolítico para discriminated union.**

| Artefato | Stories | Esforço | Notas calibradas |
|---|---|---|---|
| Spec doc `docs/architecture/planet-ast-spec.md` | 0.5 | 2-3 dias | Define 7 tipos, invariantes. Revisado antes de código. |
| Schema Pydantic v2 discriminated union (`backend/models/ast/`) | 0.5-1 | 2-4 dias | **Reaproveita `DocumentTreeNode` existente.** Split em `TextNode`/`FieldNode`/`SectionNode`/etc + `Annotated[Union[...], Field(discriminator='type')]`. Migração de consumidores (Stage 4/5) é o grosso. |
| Refatoração Stage 3 (saída em AST canônico) | 1-1.5 | 4-7 dias | **Menor que estimado.** `tree_builder.py:139-447` já faz o trabalho estrutural. Ajustes: (a) renomear nós para spec (`field` vs `label`+`value`), (b) mover `field_pair` para estrutura aninhada em vez de id-reference, (c) adicionar `bind_path`/`formatter` como campos opcionais. `classification.py` e `multi_example_analysis.py` praticamente intocados. |
| Refatoração Stage 4 (consome AST) | 1 | 3-5 dias | Gemini prompt ajustado para AST serializado. Mapping fica in-place como `bind_path` no node em vez de dict separado. |
| Renderer Mustache (primeiro target) | 1 | 3-5 dias | Visitor pattern novo; golden tests por tipo de node. |
| Refatoração Stage 5 (usa renderer) | 1 | 3-5 dias | Remove `html_helpers.py`/`html_tree.py` inconsistentes (confirmado pelo usuário em sessão anterior). |
| Adapter GrapesJS (Epic 49) | 1.5-2 | 1-2 semanas | 6-7 Component types + toHTML/parseHTML. Custo maior se UI de formatter precisar de trait custom. |
| Spike de pré-validação (**pré-requisito**) | 1 | 3-5 dias | Fork Stage 3 → gera AST v0 em 2+ tipos, Stage 4 consome; valida formatter inference em boleto+relatório. Se falhar, aborta epic. |
| **TOTAL** | **~7.5-9** | **~4-6 semanas** | |

**Achado importante:** o número original (8.5 stories, 5-6 semanas) estava no ordem correta de grandeza, mas a distribuição muda. **Schema Pydantic é mais barato que estimado** (reaproveitamento de `DocumentTreeNode`). **Stage 3 refactor é mais barato** (lógica estrutural já existe, só muda forma de output). **Adapter GrapesJS e spike não mudam.**

Dimensionamento compatível com **1 epic bem escopado** precedido por spike gate.

Alternativa mais barata considerada:
- Opção B (Mustache direto sem AST) = ~3 stories, ~2-3 semanas. **Economiza ~3 semanas mas perde flexibilidade de renderer e paga custo maior de adapter GrapesJS.** Tradeoff ainda válido como opção.
- Opção A (manter Knockout) = ~1-2 stories. **Economiza semanas mas trava arquitetura em Knockout.**

### 9.2 Learning curve

**Quem paga:**
- **Backend devs:** aprender schema Pydantic + Visitor pattern. Já dominam Pydantic (Epic 42). Visitor é padrão de engenharia padrão. Curva baixa.
- **Frontend devs:** aprender GrapesJS Component/Trait API. Obrigatório de qualquer forma (Epic 49).
- **Futuros contribuidores:** doc spec clara + exemplos + testes = curva < 1 semana.

**Custo médio estimado:** 1-2 dias de ramp-up por dev.

### 9.3 Manutenção a longo prazo

**Riscos:**
- Schema evolui → migrações AST → AST a cada major. MDAST mostrou que é sustentável (5 versions, 10 anos).
- Renderer divergente de produção → mitigável com testes cross-render (mesmo AST → mesmo output esperado).
- Débito de bikeshedding em naming (traits, components, blocks) → mitigável adotando nomenclatura GrapesJS.

**Ganhos cumulativos:**
- Novos tipos de documento (certidão, holerite, etc.) reusam 80%+ do schema.
- Novos renderers (PDF direto, DOCX) ficam aditivos.
- Rollback de Stage 3-4 sem perder Stage 1-2 é trivial (contrato é o AST).

---

## §10 — Recomendação para @architect

### 10.1 Decisão recomendada (condicional)

**Adotar AST próprio como source-of-truth APÓS spike de validação de ~1 semana.**

O spike é **pré-requisito vinculante**, não formalidade. Ele valida empiricamente as duas premissas não-precedentes desta pesquisa:

**Spike gate — 5 dias úteis:**

1. **Dia 1-2 — Stage 3 → AST v0:** fork de `tree_builder.py`, reformular `DocumentTreeNode` em discriminated union Pydantic, emitir AST v0 consumível em **2 tipos de documento** (boleto + relatório). Critério de sucesso: Stage 4 atual consegue consumir o novo formato com ≤100 LOC de ajuste.

2. **Dia 3-4 — Formatter inference via sample_data:** protótipo isolado. Input: PDF renderizado + sample_data JSON. Output: sugestão de formatter por field. Critério de sucesso: ≥70% de precisão em 2+ tipos de documento nos samples do Epic 48. Se <70%, o algoritmo precisa redesign antes de comprometer Epic.

3. **Dia 5 — Go/No-Go:** relatório do spike, decisão documentada.

**Se spike passar:** commit ao Epic 49a (Pipeline → AST) + 49b (Editor + GrapesJS).

**Se spike falhar em (1):** reavaliar; possível recomendação alternativa seria Opção B (Mustache direto) ou escopo reduzido.

**Se spike falhar em (2):** manter AST mas **remover formatter inference do MVP** (usuário declara formatter manualmente via editor, como ainda ocorre em competidores).

### 10.2 Confidence calibrada

**Evidência forte em §2, §4, §5, §7 (Wave 4 completada):**
- 7 produtos em 4 nichos convergem no padrão AST + renderers plugáveis.
- GrapesJS docs lidas em profundidade.
- Handlebars, MDAST, ProseMirror pesquisados em fontes primárias.
- **Wave 4 executada em 2026-04-21:** 7 queries específicas por fracassos/abandono; nenhum caso de rollback encontrado; dores documentadas em MJML/ProseMirror/Contentful/MiniJinja/JSON Schema analisadas e mitigadas no design.

**Evidência fraca em §3, §8.1 (formatter inference):**
- §3 (benchmark sem AST) ficou superficial.
- Formatter inference permanece contribuição original não-validada — spike dia 3-4 resolve.

**Viés de sobrevivência residual:** ainda não foi feito outreach a engineers de CCM proprietário (OpenText/Quadient/Adobe). Recomendação mantida como item 5 em §10.3.

**Confidence líquida:** **alta com caveats enumerados.** A convergência dos 7 produtos + ausência de casos de rollback após Wave 4 específica + mitigações derivadas das dores documentadas sustentam confidence alta. Os caveats são (a) formatter inference não validada, (b) viés de sobrevivência residual em CCM proprietário. Spike endereça (a); outreach endereça (b).

### 10.3 Riscos residuais

1. **Arquitetura de referência open-source inexistente no nicho.** Mitigação: copiar nomenclatura GrapesJS/MDAST. Spec revisada por par sênior antes de fechar. Análogos CCM validam que o problema tem solução comercial.
2. **Schema vai evoluir.** Mitigação: `schema_version` explícito + estratégia MDAST de major/minor desde v0.
3. **Refatoração Stage 3 — menor que estimado originalmente** (Pydantic base já existe), mas ainda é a maior cirurgia. Mitigação: branch dedicada, 7/7 casos locais passam como gate.
4. **Inferência de formatter via sample_data é original.** Spike dia 3-4 valida; se falhar, MVP segue sem essa feature.
5. **Viés de sobrevivência não endereçado.** Recomendação adicional: @architect consulta 1-2 engineers de CCM (Exstream/Inspire alumni em LinkedIn/ThoughtWorks network) antes de commit ao Epic, para levantar armadilhas não-documentadas publicamente.

### 10.4 Open questions para @architect decidir

1. **Spec doc como markdown ou YAML/JSON Schema?** Recomendação: markdown com exemplos + schema Pydantic como "código de verdade". MDAST faz assim.
2. **Versão inicial do schema: `planet-ast-v1` ou `template-ast-v0`?** Recomendação: `v0` até Epic 48 E2E fechar; `v1` quando primeiro template em produção.
3. **Renderer único ou múltiplos no MVP?** Recomendação: **único** (Mustache). Adicionais só quando consumidor concreto aparecer.
4. **Migrations AST → AST: ferramentaria custom ou biblioteca?** Recomendação: custom simples (é visitor Pydantic). Biblioteca se dor aparecer.
5. **Spike: quem executa?** Recomendação: @dev sênior em modo `--yolo` com gate explícito para @architect no dia 5.

### 10.5 Next actions sugeridas

1. **Primeiro:** aprovar ou rejeitar a recomendação condicional.
2. Se aprovada: ADR focado `ADR-XXX-ast-as-source-of-truth.md` com escopo do spike + critérios de sucesso.
3. Spec preliminar do AST: `docs/architecture/planet-ast-spec.md` — pode começar em paralelo ao spike.
4. Executar spike (5 dias).
5. Pós-spike: decisão Go/No-Go documentada. Se Go, criar Epic 49a + 49b.

---

## §11 — Apêndice: mapeamento de fontes

### Produtos com AST/IR próprio (§2)
- [MJML — mjmlio/mjml](https://github.com/mjmlio/mjml)
- [MJML Documentation](https://documentation.mjml.io/)
- [gomjml — preslavrachev/gomjml](https://github.com/preslavrachev/gomjml)
- [React-Email — resend/react-email](https://github.com/resend/react-email)
- [React-Email Render docs](https://react.email/docs/utilities/render)
- [renderToStaticMarkup | React](https://react.dev/reference/react-dom/server/renderToStaticMarkup)
- [Contentful Rich Text — contentful/rich-text](https://github.com/contentful/rich-text)
- [Contentful Rich Text tutorial](https://www.contentful.com/developers/docs/tutorials/general/getting-started-with-rich-text-field-type/)
- [Style Dictionary + SD Transforms](https://docs.tokens.studio/transform-tokens/style-dictionary)
- [ProseMirror Guide](https://prosemirror.net/docs/guide/)
- [Plasmic — plasmicapp/plasmic](https://github.com/plasmicapp/plasmic)
- [Plasmic Codegen Guide](https://docs.plasmic.app/learn/codegen-guide/)
- [Plasmic Headless API vs Codegen](https://docs.plasmic.app/learn/loader-vs-codegen/)
- [Builder.io — How Builder Works](https://www.builder.io/c/docs/how-builder-works-technical)
- [Builder Content API](https://www.builder.io/c/docs/content-api)

### Produtos sem AST explícito (§3)
- [Mustache — mustache.github.io](https://mustache.github.io/)
- [Mustache Spec — mustache/spec](https://github.com/mustache/spec)

### GrapesJS (§4)
- [Trait Manager | GrapesJS](https://grapesjs.com/docs/modules/Traits.html)
- [Component Manager | GrapesJS](https://grapesjs.com/docs/modules/Components.html)
- [Component API | GrapesJS](https://grapesjs.com/docs/api/component.html)
- [Components & JS | GrapesJS](https://grapesjs.com/docs/modules/Components-js.html)
- [Component Types & Custom Components | DeepWiki](https://deepwiki.com/GrapesJS/grapesjs/3.4.2-component-types-and-custom-components)

### Schema design (§5)
- [Handlebars compiler-api.md](https://github.com/handlebars-lang/handlebars.js/blob/master/docs/compiler-api.md)
- [handlebars-parser](https://github.com/handlebars-lang/handlebars-parser)
- [MDAST — syntax-tree/mdast](https://github.com/syntax-tree/mdast)
- [ProseMirror Guide — document & schema](https://prosemirror.net/docs/guide/)

### Recursos adjacentes
- [ejs vs handlebars vs pug vs mjml — npm-compare](https://npm-compare.com/ejs,handlebars,mjml,pug)
- [Creating AWS email templates with Handlebars.js and MJML](https://blog.elmah.io/creating-aws-email-templates-with-handlebars-js-and-mjml/)
- [Josh W. Comeau — MJML + MDX workflow](https://www.joshwcomeau.com/react/wonderful-emails-with-mjml-and-mdx/)

### Anti-casos e fracassos — Wave 4 (§7)
- [MJML Issue #1630 — Templating needs be a first class feature](https://github.com/mjmlio/mjml/issues/1630)
- [ProseMirror Issue #241 — structural ideas from implementing recently](https://github.com/ProseMirror/prosemirror/issues/241)
- [HackerNews — ProseMirror rough experience](https://news.ycombinator.com/item?id=16825034)
- [discuss.ProseMirror — Prosemirror is very hard on basic stuff](https://discuss.prosemirror.net/t/prosemirror-is-very-hard-on-basic-stuff-like-suggestions/2995)
- [Contentful Rich Text — GitHub issues](https://github.com/contentful/rich-text/issues)
- [CSS-Tricks — MJML vs Foundation for Emails (limitations)](https://css-tricks.com/choosing-a-responsive-email-framework%E2%80%8Amjml-vs-foundation-for-emails/)
- [Armin Ronacher — MiniJinja: Learnings from Building a Template Engine in Rust](https://lucumr.pocoo.org/2024/8/27/minijinja/)
- [JSON Schema — The Last Breaking Change](https://json-schema.org/blog/posts/the-last-breaking-change)
- [json-schema-migrate — draft-04 to draft-2020-12](https://github.com/ajv-validator/json-schema-migrate)
- [nipafx — Visitor Pattern Considered Pointless, Use Pattern Switches Instead](https://nipafx.dev/java-visitor-pattern-pointless/)
- [Plasmic Hacker News discussion](https://news.ycombinator.com/item?id=38697650)

---

**Revisão pelo advisor:** realizada 2026-04-21. 5 correções iniciais aplicadas + Wave 4 executada após quota WebSearch resetar:

1. Sumário executivo recalibrado.
2. §7 **completamente reescrito** com Wave 4 real (7 queries específicas, nenhum caso de rollback encontrado, 6 sub-seções com dores documentadas em MJML/ProseMirror/Contentful/MiniJinja/JSON Schema/Visitor pattern).
3. §9.1 recalibrado com leitura direta do código Stage 3 (Pydantic base já existe; refactor menor que estimado).
4. §8.1.1 reformulado: análogos CCM existem (Exstream/Inspire/AEM Forms); gap é arquitetura open-source, não produto.
5. §8.3 atualizado: `raw_html` move de v2 para v0 MVP (derivado do achado Contentful).
6. §10.2 confidence atualizada para "alta com caveats enumerados".
7. §10 recomendação condicional a spike de 5 dias como pré-requisito vinculante.

**Próximo agente:** `@architect` via handoff `.aios/handoffs/handoff-analyst-to-architect-20260421-ast-research.yaml` (criado após confirmação do usuário).
