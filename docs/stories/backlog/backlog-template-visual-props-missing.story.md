# Backlog: Template HTML — Propriedades visuais faltando (cor, font_size, linhas)

**Origem:** RCA `rca-2026-03-31-template-no-bold-no-position`
**Data:** 2026-03-31
**Severidade:** Medium (bold + position já corrigidos; restam cor/tamanho/linhas)

## Contexto

O fix do RCA corrigiu `bbox` (position:absolute) e `is_bold`/`font_weight` (negrito).
Stage 5 gera CSS correto para cor/fonte/linhas, mas as classes geradas nunca são
aplicadas nos spans HTML porque Stage 3 não propaga esses atributos para os tree nodes.

## Problemas pendentes

### 1. Cor do texto (`color`)
- Stage 2 extrai `color` (int RGB) por bloco
- Stage 3 **não propaga** `color` para tree nodes
- Stage 5 gera `.c-000000 { color: #000000; }` mas nenhum span tem essa classe
- **Fix:** propagar `color` no Stage 3; aplicar classe `.c-{hex}` no span no Stage 5

### 2. Tamanho de fonte (`font_size`)
- Stage 2 extrai `font_size` por bloco
- Stage 3 **não propaga** `font_size`
- Stage 5 gera `.f-helvetica { font-size: 10pt; }` mas sem conexão aos spans
- **Fix:** propagar `font_size`; aplicar como `font-size:{N}px` inline ou via classe

### 3. Nome da fonte (`font_name`)
- Stage 2 extrai `font_name` por bloco
- Stage 3 **não propaga** `font_name`
- Stage 5 gera `.f-helvetica { font-family: Helvetica; }` sem aplicar nos spans
- **Fix:** propagar `font_name`; aplicar classe `.f-{safe_name}` no span

### 4. Linhas separadoras (`drawn_elements`)
- Stage 2 extrai `drawn_elements` tipo `line` com bbox e stroke_color
- Stage 5 gera `.border-line-N { ... }` CSS mas não há nodes HTML correspondentes
- As linhas simplesmente não aparecem no template gerado
- **Fix:** converter `drawn_elements` do tipo `line` em nodes `<div>` posicionados
  na árvore Stage 3 (similar a image/chart/barcode)

## Arquivos afetados

- `backend/services/stages/stage3_structural_analysis.py` — propagar atributos
- `backend/services/stages/stage5_template_generation.py` — aplicar nos spans
- Testes correspondentes nos dois arquivos

## Acceptance Criteria

- [ ] Texto com cor diferente de preto renderiza com `color:` correto no template
- [ ] Texto com font_size diferente renderiza com `font-size:` correto
- [ ] Linhas horizontais do boleto aparecem como `<div>` posicionados absolutamente
- [ ] Todos os testes existentes continuam passando (80 testes)
- [ ] Novos testes de contrato para cada atributo adicionado
