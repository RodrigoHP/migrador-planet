# ADR-001: Manter o nivel page intermediario na arvore estrutural

- **Status:** Accepted
- **Date:** 2026-04-08
- **Story:** 38.7
- **Decision Maker:** @architect (Aria)

## Context

A arvore estrutural gerada pelo `stage3_structural_analysis.py` inclui um nivel intermediario `page` entre `document` e os blocos `header/flow/footer`. A hierarquia atual eh:

```
document > page > header/flow/footer > sections > elements
                > line (drawn elements)
                > rect (drawn elements)
```

A proposta era avaliar se este nivel poderia ser removido para simplificar para:

```
document > header/flow/footer > sections > elements
```

## Decision

**NO-GO: Manter o nivel `page`.**

O nivel `page` NAO eh um wrapper inerte -- possui semantica propria e funcionalidades criticas que nao podem ser replicadas sem refactor extenso e risco de regressao.

## Analysis

### 1. Backend: stage3_structural_analysis.py

O `page` node eh criado em `_build_tree()` (linha 1477-1486) como filho unico de `document`. Ele serve como container para:

- **Zones** (header, flow, footer) -- filhos de `page`, NAO de `document`
- **Drawn lines** (linhas horizontais/verticais) -- adicionados diretamente a `page` (linhas 1766-1774)
- **Drawn rects** (retangulos preenchidos/backgrounds) -- adicionados diretamente a `page` (linhas 1777-1784)

As linhas e retangulos sao irmaos das zones, NAO filhos delas. Sem `page`, esses elementos precisariam de outro container ou seriam mesclados com as zones de forma incoerente.

### 2. Backend: stage5_template_generation.py

O `page` node tem tratamento especifico (linhas 226-239):

- **Z-ordering:** Ordena filhos como `rects > zones > lines` para replicar a ordem de pintura do PDF (fills, text, borders). Esta logica depende de `page` ser o container de TODOS os tipos de filhos.
- **Renderiza como `<div class="page-content">`** -- que eh um contrato entre backend e frontend.
- O `document` node renderiza como `<div class="page page-{name}" data-layout-type="...">` -- container externo da folha.

A separacao `document` -> `.page[data-layout-type]` wrapper e `page` -> `.page-content` inner eh essencial para multi-page.

### 3. Frontend: HTMLCanvas.vue

O `pages` computed (linhas 289-328) faz parsing do HTML gerado:

- Busca `[data-layout-type]` (gerado por `document`)
- Dentro deles, busca `.page-content` (gerado por `page`) para separar paginas fisicas em iframes individuais
- **Multi-page PDFs** produzem N `.page-content` dentro de 1 `[data-layout-type]`, e cada um vira uma `CanvasPage` separada
- A mesma logica existe em `SyncView.vue` (linhas 281-287)

Sem `.page-content`, o mecanismo de splitting multi-page quebraria completamente.

### 4. Frontend: usePagination.ts

**Nenhuma dependencia do nivel `page` da arvore.** O composable trabalha com `LayoutElement[]` e `PageConfig` genericos. A paginacao eh calculada por alturas de elementos, nao por nodos da arvore.

### 5. Frontend: StructureTree.vue

**Nenhuma dependencia especifica do tipo `page`.** Renderiza a arvore genericamente via `StructureTreeNode`.

### 6. CSS Contract

A classe `.page` tem estilo critico em `_BASE_CSS_RESET`:
```css
.page {
  position: relative;
  box-sizing: border-box;
  background: #ffffff;
  overflow: hidden;
  width: 794px;
  height: 1123px;
}
```

E dimensoes sao sobrescritas dinamicamente baseadas no tamanho real da pagina do PDF.

## Components That Depend on `page`

| Component | Dependency Type | Removal Cost |
|-----------|----------------|--------------|
| `stage3_structural_analysis.py` `_build_tree()` | Structural: container para zones + drawn elements | Alto: refactor de toda a construcao da arvore |
| `stage5_template_generation.py` `_tree_to_html()` | Semantic: z-ordering (rects > zones > lines) + renderiza `.page-content` | Alto: perda de z-ordering e contrato frontend |
| `HTMLCanvas.vue` `pages` computed | Contract: split `.page-content` para multi-page | Critico: quebraria visualizacao multi-page |
| `SyncView.vue` parsing | Contract: mesma logica de split `.page-content` | Critico: quebraria Sync View |
| CSS `.page` class | Styling: dimensoes, overflow, position | Medio: poderia ser renomeado mas nao removido |

## Risks of Removal

1. **Multi-page display broken:** HTMLCanvas.vue e SyncView.vue dependem do contrato `.page-content` para separar paginas em iframes individuais
2. **Z-ordering lost:** A logica de renderizar rects antes de zones antes de lines seria perdida ou precisaria ser reimplementada em cada zone
3. **Drawn elements orphaned:** Linhas e retangulos que sao irmaos das zones (nao filhos) nao teriam container
4. **CSS cascade broken:** A classe `.page` fornece `position: relative` + `overflow: hidden` que ancora todos os elementos `position: absolute` filhos

## Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Mover drawn elements para dentro das zones | Incorreto: linhas/rects podem cruzar zonas (header-to-flow borders) |
| Fazer `document` assumir papel de `page` | Conflito: `document` ja renderiza o wrapper `[data-layout-type]`, nao pode renderizar `.page-content` tambem |
| Criar novo mecanismo de multi-page sem `.page-content` | Custo desproporcional: seria reescrever HTMLCanvas e SyncView sem ganho funcional |

## Consequences

### Positive
- Estabilidade mantida: zero risco de regressao
- Contrato backend-frontend preservado
- Multi-page display continua funcionando

### Negative
- Arvore continua com 1 nivel extra de nesting
- StructureTree mostra `page` como no visivel (pode ser ocultado com filtro de display)

### Recommendation
Se no futuro a simplificacao visual for desejada, a abordagem recomendada eh **ocultar o `page` node na UI** (StructureTree.vue) sem remover da arvore interna. Isso daria a experiencia de `document > header/flow/footer` sem quebrar a semantica.
