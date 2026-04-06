# Story: Reframear layoutTypes como pageTypes — Unificação Semântica

**Status:** Draft  
**Tipo:** Refatoração  
**Prioridade:** Média  
**Origem:** RCA rca-2026-04-06-canvas-no-pagination — achado colateral (Option B implementation)

---

## Contexto

Durante a investigação de paginação do canvas (Option B — scroll contínuo), identificou-se uma inconsistência semântica entre as stories:

- **Stories 6.5 e 9.5** foram especificadas com o modelo correto: _um documento com múltiplas páginas_.
- **Story 7.7** foi especificada com o modelo errado: _múltiplos tipos de documento independentes por sessão_.

O usuário confirmou: a sessão sempre contém **um único tipo de documento**. Múltiplos PDFs = múltiplos exemplos do mesmo documento para aumentar confiança do modelo. Os `layoutTypes` detectados pelo pipeline representam **variantes de página do mesmo documento** (ex: página de cabeçalho, página de transações, página de rodapé/totais).

A implementação atual da Story 7.7 trata cada layout como um template independente com `documentTree` separado. Isso é tecnicamente funcional mas semanticamente incorreto.

---

## O que este refactor faz

### 1. Renomear conceito na UI
- `Layout Type` → `Tipo de Página` em labels, tooltips e títulos visíveis ao usuário
- O seletor no header passa a comunicar "tipos de página deste documento" em vez de "templates"

### 2. Unificar documentTree
- Hoje: uma `documentTree` separada por `layoutId` (`newLayout.documentTree`)
- Proposto: uma única `documentTree` raiz com nós anotados por `page_type`
- Impacto: `StructureTree` e `InspectorPanel` operam no contexto do documento inteiro, não de um layout isolado

### 3. Revisar testes da Story 7.7
- Os testes atuais testam a semântica de "templates independentes"
- Precisam ser reescritos para a semântica correta de "variantes de página"

---

## O que NÃO muda

- **Story 6.5** — canvas com scroll contínuo — já está alinhada, não tocar
- **Story 9.5** — paginação por conteúdo — já está alinhada, não tocar
- **AC #5 da Story 7.7** — ocultar seletor quando há apenas 1 layout — correto em qualquer modelo, manter
- **Mecanismo de `layoutTypes` no pipeline** — continua válido, só a semântica frontend muda

---

## Acceptance Criteria

1. **AC1:** O seletor de layout no header exibe o label "Tipo de Página" (ou "Página X de N") em vez de "Layout"
2. **AC2:** `StructureTree` exibe a árvore do documento inteiro, com nós anotados por `page_type`
3. **AC3:** `InspectorPanel` ao selecionar um elemento em qualquer página mostra suas propriedades corretamente, independente de qual "layout" está ativo
4. **AC4:** Testes da Story 7.7 reescritos para validar semântica de variantes de página
5. **AC5:** Zero regressão nas Stories 6.5, 9.5 e 28.x

---

## Escopo

**IN:**
- Renomear labels UI (`layoutTypes` → `pageTypes` na camada de apresentação)
- Unificar `documentTree` (uma raiz com metadados de `page_type` por nó)
- Reescrever testes da Story 7.7

**OUT:**
- Mudar o backend (pipeline já gera `layoutTypes` corretamente)
- Mudar o comportamento de scroll/navegação (já implementado na Option B)
- Mudar `coverageStore` ou `confidenceStore` (por layout ainda faz sentido)

---

## Dependências

- **Pré-requisito:** Option B implementada (canvas scroll contínuo) ✅
- **Bloqueia:** Nada crítico — pode ser feito em qualquer sprint

---

## Riscos

| Risco | Severidade | Mitigação |
|-------|-----------|-----------|
| `layoutStore` e `templateStore` têm contratos por layout — refatorar pode quebrar stores | ALTO | Migração gradual; manter `layoutStore` mas mudar semântica de "troca de template" para "filtro de tipo de página" |
| Testes existentes da Story 7.7 testam semântica errada | MÉDIO | Reescrever junto com a revisão, não adaptar |
| Scope creep para stories 5.7, 5.8, 7.7 | MÉDIO | Manter escopo cirúrgico — só UI e tree unification |

---

## Change Log

| Data | Autor | Ação |
|------|-------|------|
| 2026-04-06 | @qa (RCA rca-2026-04-06) | Story draft criada como achado colateral da investigação de paginação |
