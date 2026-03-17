# Wireframes Mid-Fidelity — Migrador Planetexpress → HTML/Knockout.js

**Projeto:** Migrador Planetexpress → HTML/Knockout.js
**Fidelidade:** Mid-Fidelity
**Agente:** @ux-design-expert (Uma)
**Data:** 2026-03-15 (v5 — Canvas HTML + Árvore de Estrutura, alinhado com docs/UI specs)
**Telas:** 1 home + 1 upload + 1 editor (central) + 1 modal global (Bibliotecas)

---

## Tela 0 — Home

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Migrador Planetexpress                              [📚 Bibliotecas]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────────────────────┐   ┌──────────────────────────────┐      │
│   │        ➕ Novo Template       │   │       📂 Abrir Projeto       │      │
│   │                              │   │                              │      │
│   │  Iniciar migração de um      │   │  Retomar projeto salvo       │      │
│   │  novo documento PDF          │   │  (.json)                     │      │
│   │                              │   │                              │      │
│   │      [ Começar → ]           │   │      [ Carregar arquivo ]    │      │
│   └──────────────────────────────┘   └──────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Anotações:**
- Tela inicial da ferramenta
- **Novo Template** → vai para Tela 1 (Upload)
- **Abrir Projeto** → abre seletor de arquivo; carrega `.json` salvo; restaura estado completo e navega direto para o Editor
- **Bibliotecas** → abre modal global com componentes/snippets reutilizáveis

---

## Tela 1 — Upload

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Migrador Planetexpress                              [📚 Bibliotecas]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Nome do Template                                                           │
│  [________________________________________________________]                │
│                                                                             │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │      📄 PDFs de Exemplo         │  │        📋 Schema XSD            │  │
│  │                                 │  │                                 │  │
│  │  Arraste PDFs aqui              │  │  Arraste o XSD aqui            │  │
│  │  ou clique para selecionar      │  │  ou clique para selecionar     │  │
│  │                                 │  │                                 │  │
│  │  ┌──────────────────────┐       │  │                                 │  │
│  │  │ Doc1.pdf         [🗑️] │       │  │  schema.xsd ✅                 │  │
│  │  │ Doc2.pdf         [🗑️] │       │  │                                 │  │
│  │  │ Doc3.pdf         [🗑️] │       │  │                                 │  │
│  │  └──────────────────────┘       │  │                                 │  │
│  │                                 │  │                                 │  │
│  │  📊 3 PDFs (recomendado: 3-5)   │  │                                 │  │
│  │  💡 Quanto mais PDFs, melhor    │  │                                 │  │
│  │     a detecção de campos        │  │                                 │  │
│  │     opcionais e variações       │  │                                 │  │
│  └─────────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │      📊 Arquivo de Dados (opcional)                                  │  │
│  │                                                                      │  │
│  │  Arraste um XML ou JSON com dados reais aqui                        │  │
│  │  ou clique para selecionar                                          │  │
│  │                                                                      │  │
│  │  dados_exemplo.xml ✅                                               │  │
│  │                                                                      │  │
│  │  💡 Dados reais melhoram a detecção automática de tipos e formatos  │  │
│  │     e servirão de exemplo para o template                           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  💡 Envie ao menos 1 PDF + XSD para continuar                              │
│                                                                             │
│  [← Voltar]                                        [ Iniciar Análise → ]   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Anotações:**
- **Nome do Template** — identificador do projeto (ex: "Extrato_Bancario")
- **PDFs** — dropzone aceita múltiplos arquivos; 1 obrigatório, 3-5 recomendado
- **XSD** — obrigatório; define nomes canônicos dos campos para data-bind Knockout
- **Dados (XML/JSON)** — opcional; arquivo com dados reais de exemplo
  - Melhora detecção automática de tipos e formatos
  - Serve de exemplo para o template
  - Aceita 1 arquivo XML ou JSON
- **Hints contextuais:**
  - Sem arquivos: "Envie ao menos 1 PDF + XSD para continuar"
  - 1 PDF: "💡 Adicionar mais PDFs melhora a detecção de variações"
  - PDF sem XSD: botão desabilitado
  - PDF+XSD sem dados: "💡 Adicionar dados reais melhora a detecção de tipos e formatos"
- **Iniciar Análise** → navega para Tela de Progresso (analyzing)
- **Voltar** → retorna à Home

---

## Tela 2 — Editor (Página Central)

O Editor é a interface principal da aplicação. O operador edita a **estrutura do template** (árvore + inspetor) e vê o **resultado renderizado** no Canvas HTML central.

### Modelo Mental

```
Operador edita ESTRUTURA          Canvas mostra RESULTADO
(Árvore + Inspetor)               (HTML renderizado live)
         │                                 ↑
         ↓                                 │
   stores (Pinia) ──→ HTML Generator ──→ iframe
         ↑                                 │
         └──── clique / arrastar / resize ──┘
```

O Canvas não é o PDF original — é a **pré-visualização live do HTML final** que será produzido pelo template. O PDF original é referência secundária acessível via aba.

### Interação no Canvas

O Canvas permite interação direta com os elementos renderizados:

- **Clicar** num elemento → seleciona na Árvore de Estrutura + abre no Inspetor
- **Arrastar** um elemento selecionado → move (atualiza posição no store)
- **Redimensionar** via handles nas bordas → ajusta tamanho (atualiza dimensões no store)
- **Seleção hierárquica** — quando o elemento clicado está aninhado (ex: texto dentro de célula dentro de tabela), aparece um popup para escolher o nível:

```
┌─────────────────────┐
│ Selecionar elemento: │
│                     │
│  🔤 Texto           │
│  📊 Célula          │
│  📋 Linha           │
│  📋 Tabela          │
└─────────────────────┘
```

O Canvas **não** permite criar elementos novos desenhando. Novos elementos são adicionados via Árvore de Estrutura ou Bibliotecas.

### 5 Regiões do Editor

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. BARRA DE FERRAMENTAS                                                     │
├────────────┬────────────────────────────────────────────┬───────────────────┤
│            │                                            │                   │
│ 2. PAINEL  │   3. CANVAS / PDF / CÓDIGO / SINCRONIZAR   │  4. INSPETOR      │
│ ESQUERDO   │      (4 abas)                              │  HIERÁRQUICO      │
│ (2 abas)   │                                            │                   │
├────────────┴────────────────────────────────────────────┴───────────────────┤
│ 5a. ANALISADOR MULTI-DOCUMENTO                                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5b. PAINEL INFERIOR  [ Dados de Teste ] [ Relatório ]                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### Estado: Analyzing (Tela de Progresso)

Quando o operador clica "Iniciar Análise" no Upload, navega para esta tela de progresso dedicada.
O Editor **não abre** até o pipeline finalizar — não há render parcial.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Extrato_Bancario                                      [📚 Bibliotecas] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                      Analisando documentos...                               │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                                                                     │  │
│   │  ✅ Bloco 1/8 — Aquisição                                         │  │
│   │      ✅ Upload PDFs + XSD                                          │  │
│   │      ✅ Análise de PDFs                                            │  │
│   │                                                                     │  │
│   │  ✅ Bloco 2/8 — Descoberta de Layout                              │  │
│   │      ✅ Construtor de Esqueleto                                    │  │
│   │      ✅ Agrupamento de Layouts                                     │  │
│   │      ✅ Seleção de Representativas                                 │  │
│   │      ✅ Impressão Digital                                          │  │
│   │      ✅ Consulta ao Registro                                       │  │
│   │                                                                     │  │
│   │  🔄 Bloco 3/8 — Inteligência                                      │  │
│   │      ✅ Alinhamento de Layout                                      │  │
│   │      🔄 Análise Multi-Exemplo...                                   │  │
│   │      ○ Estabilidade                                                │  │
│   │      ○ Variantes                                                   │  │
│   │      ○ Normalização                                                │  │
│   │                                                                     │  │
│   │  ○ Bloco 4/8 — Tabelas                                            │  │
│   │  ○ Bloco 5/8 — Semântica                                          │  │
│   │  ○ Bloco 6/8 — Visão                                              │  │
│   │  ○ Bloco 7/8 — Mapeamento                                         │  │
│   │  ○ Bloco 8/8 — Validação                                          │  │
│   │                                                                     │  │
│   │  ████████████░░░░░░░░░░░░░░░░  35%                                 │  │
│   │                                                                     │  │
│   │  Tempo estimado: ~30 segundos                                      │  │
│   │                                                                     │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│   📊 Resumo parcial                                                        │
│   PDFs: 3 documentos   │   Páginas: 285   │   Layouts detectados: --       │
│                                                                             │
│   [← Cancelar]                                                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Anotações:**
- **Tela de progresso dedicada** — NÃO é o Editor; não há Canvas nem Árvore de Estrutura visíveis
- Pipeline de 23 stages organizado em 8 blocos lógicos com indicadores ✅ 🔄 ○
- **Barra de progresso geral** mostra percentual total
- **Resumo parcial** atualiza conforme dados ficam disponíveis (ex: "Layouts detectados: 3" aparece após Bloco 2)
- **Cancelar** interrompe o pipeline e retorna ao Upload
- Ao finalizar todos os blocos, navega **automaticamente** para o Editor em estado "editing" com tudo pronto
- Operador não precisa clicar nada para avançar — a transição é automática

---

### Estado: Editing (Principal)

Estado normal de trabalho. Todas as 5 regiões visíveis. O operador edita a estrutura do template via Árvore + Inspetor e vê o resultado no Canvas HTML.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Extrato_Bancario    │ Confiança: 91% │ Cobertura: 93%                 │
│  Layout: [ Transações ▼ ] (285 pgs em 3 docs)                             │
│  [ 🗺️ Cobertura ] [ 🔀 Diff ] [ 🧲 Snap ] [ 🔧 Auto Fix ] [ 💾 Salvar ] [ 📦 Exportar ] │
├──────────────┬──────────────────────────────────────┬─────────────────────┤
│ [Estrutura]  │ [ 🖥️ Canvas ] [ 📄 PDF ] [ </> Código ] [ 🔗 Sincronizar ] │ INSPETOR │
│ [Campos]     │                                      │                     │
│──────────────│  ┌──────────────────────────────┐    │ Inspetor de Seção   │
│ 📄 Document  │  │                              │    │ Tipo: Cabeçalho     │
│ ├ 📦 Header  │  │  ╔══════════════════════╗    │    │                     │
│ │ ├ 🖼 Logo  │  │  ║ PÁGINA 1             ║    │    │ Altura: [120] px    │
│ │ ├ 🔤 Cli.  │  │  ║                      ║    │    │ Fundo: [#FFFFFF]    │
│ │ └ 🔤 CPF   │  │  ║ [LOGO] EXTRATO CONTA ║    │    │ Padding: [10] px    │
│ ├ 📦 Flow    │  │  ║ Cliente: João Silva   ║    │    │ Repetir cada pg:    │
│ │ ├ 📋 Tab.  │  │  ║ CPF: 123.456.789-00  ║    │    │ [ ✔ ]               │
│ │ │ ├ data   │  │  ║──────────────────────║    │    │                     │
│ │ │ ├ desc   │  │  ║ Data │Descr. │ Valor ║    │    │ Visibilidade        │
│ │ │ └ valor  │  │  ║ 01/01│Compra │ 100   ║    │    │ [ Sempre visível ▼ ]│
│ │ └ 📊 Graf. │  │  ║ 02/01│Compra │ 200   ║    │    │                     │
│ ├ 📦 Footer  │  │  ║ 03/01│Compra │ 300   ║    │    │                     │
│ │ └ 🔤 Pg#   │  │  ║──────────────────────║    │    │                     │
│ └ ···        │  │  ║ Página 1 de 3        ║    │    │                     │
│              │  │  ╚══════════════════════╝    │    │                     │
│              │  │         ↕ gap entre páginas   │    │                     │
│              │  │  ╔══════════════════════╗    │    │                     │
│              │  │  ║ PÁGINA 2             ║    │    │                     │
│              │  │  ║                      ║    │    │                     │
│              │  │  ║ [LOGO] EXTRATO CONTA ║    │    │                     │
│              │  │  ║ Cliente: João Silva   ║    │    │                     │
│              │  │  ║──────────────────────║    │    │                     │
│              │  │  ║ 04/01│Compra │ 150   ║    │    │                     │
│              │  │  ║ 05/01│Compra │ 250   ║    │    │                     │
│              │  │  ║                      ║    │    │                     │
│              │  │  ║ [GRÁFICO VENDAS]     ║    │    │                     │
│              │  │  ║──────────────────────║    │    │                     │
│              │  │  ║ Página 2 de 3        ║    │    │                     │
│              │  │  ╚══════════════════════╝    │    │                     │
│              │  │                              │    │                     │
│              │  │  🔍 [ - 100% + ]             │    │                     │
│              │  └──────────────────────────────┘    │                     │
├──────────────┴──────────────────────────────────────┴─────────────────────┤
│ ANALISADOR MULTI-DOCUMENTO                                                │
│ Doc1.pdf ✔ base │ Doc2.pdf ✔ variação │ Doc3.pdf ✔ variação              │
│ Matriz de Variação: cliente ✔✔✔ │ cpf ✔✔✔ │ telefone ✖✔✖ (opcional) │..│
├─────────────────────────────────────────────────────────────────────────────┤
│ [ Dados de Teste ]  [ Relatório ]                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ Datasets:                                   │ Resumo: sample.xml            │
│ ● sample.xml     ✓  Validado   [🗑️]       │ Campos: cliente, cpf, valor.. │
│   large.xml      ✓  Validado   [🗑️]       │ Loops:  transacoes (2 itens)  │
│   vip.json       ⚠  1 aviso    [🗑️]       │ Status: ✓ Validado            │
│   synthetic_sm   ✓  Gerado     [🗑️]       │                               │
│                                             │ [Aplicar] [▶ Testar] [Editar] │
│ [ Upload Dataset ]  [ Gerar Sintético ]     │                               │
└─────────────────────────────────────────────┴───────────────────────────────┘
```

**Anotações do Canvas — Paginação Real:**
- **Scroll contínuo vertical** — páginas empilhadas com gap e sombra entre elas (não usa navegação ◀ ▶)
- **Cada página** renderiza `cabeçalho` + `fluxo` + `rodapé` como divs separadas dentro de um container `.page`
- **Cabeçalho e rodapé repetem** automaticamente em cada página
- **Dimensões padrão** — A4 (794×1123px), margens configuráveis no Inspetor de Página
- **Paginação dinâmica** — calculada pelo espaço disponível no fluxo (altura da página − cabeçalho − rodapé)
- **Desempenho** — renderiza no máximo 5 páginas; páginas adicionais carregam sob demanda (lazy rendering) conforme o operador rola
- **Dados de exemplo** — usa o XML/JSON enviado no Upload ou dados sintéticos gerados a partir do XSD para simular a paginação
- **Interação** — clicar seleciona, arrastar move, handles redimensionam; não permite criar elementos desenhando

---

### Aba Código (Editor de Código)

Quando o operador seleciona a aba `</> Código`, o painel esquerdo troca para o **Explorador de Arquivos** do template e o painel central exibe o editor de código (Monaco Editor):

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [Estrutura]  │ [ 🖥️ Canvas ] [ 📄 PDF ] [ </> Código ] [ 🔗 Sincronizar ] │ INSPETOR │
│ [Campos]     │                                                             │          │
│ [Arquivos]  ◄│  index.html  │  style.css  │  base.js                      │ Inspetor │
│──────────────│  ┌──────────────────────────────────────────────┐           │ de       │
│ 📁 Template  │  │  1  <div class="header">                    │           │ Elemento │
│ ├ 📄 index   │  │  2    <img src="logo.png" />                │           │          │
│ │    .html  ◄│  │  3    <span data-bind="text:               │           │ Binding: │
│ ├ 📁 css     │  │  4      cliente.nome"></span>               │           │ [cliente │
│ │ └ 📄 style │  │  5    <span data-bind="text:               │           │  .nome]  │
│ │    .css    │  │  6      cliente.cpf"></span>                │           │          │
│ ├ 📁 js      │  │  7  </div>                                  │           │ Tipo:    │
│ │ └ 📄 base  │  │  8  ⚠ <!-- SEÇÃO ESTRUTURAL: header -->    │           │ [texto]  │
│ │    .js     │  │  9  <div class="flow">                      │           │          │
│ ├ 📁 assets  │  │ 10    <table data-bind="foreach:           │           │          │
│ │ ├ 🖼 logo  │  │ 11      movimentos">                        │           │          │
│ │ │  .png    │  │ 12      <tr>                                 │           │          │
│ │ └ 📁 fonts │  │ 13        <td data-bind="text: data"></td>  │           │          │
│ └ 📄 exemplo │  │ 14        <td data-bind="text: desc"></td>  │           │          │
│      .js     │  │ 15        <td data-bind="text: valor"></td> │           │          │
│              │  │ 16      </tr>                                │           │          │
│              │  │ 17    </table>                               │           │          │
│              │  │ 18  </div>                                   │           │          │
│              │  │                                              │           │          │
│              │  │  ⚠ campo "telefone" não encontrado no XSD   │           │          │
│              │  └──────────────────────────────────────────────┘           │          │
└──────────────┴─────────────────────────────────────────────────────────────┴──────────┘
```

**Anotações do Editor de Código:**
- **Explorador de Arquivos** — ao entrar na aba Código, o painel esquerdo adiciona a aba `[Arquivos]` mostrando a estrutura do pacote do template (index.html, css/, js/, assets/)
- **Abas de arquivo** — cada arquivo aberto aparece como aba no topo do editor (index.html, style.css, base.js); clicar no Explorador abre o arquivo em nova aba
- **Monaco Editor** — syntax highlighting para HTML/CSS/JS, auto-indentação, formatação, numeração de linhas, busca
- **Edição multi-arquivo:**
  - `index.html` — layout do template, bindings Knockout, seções estruturais
  - `css/style.css` — estilos visuais (fontes, espaçamentos, cores)
  - `js/base.js` — funções auxiliares (formatCPF, formatDate, formatCurrency)
  - `js/exemplo.js` — dados de exemplo para preview
  - `assets/` — somente visualização (imagens, fontes); não editável
- **Regras de edição (MVP):**
  - ✅ Editar arquivos existentes (HTML, CSS, JS)
  - ❌ Criar novos arquivos
  - ❌ Deletar arquivos
  - ❌ Renomear arquivos
- **Avisos em áreas críticas** — seções estruturais (header, footer, flow) exibem marcadores `⚠ SEÇÃO ESTRUTURAL` alertando que edições podem afetar a paginação
- **Detecção de erros inline** — HTML inválido, bindings que não existem no XSD, erros de sintaxe são destacados em tempo real no editor
- **Sincronização bidirecional** — editar no código atualiza a estrutura (stores); editar na estrutura/inspetor regenera o código
- **Fonte da verdade** — sempre a estrutura (stores), nunca o HTML; o código é uma representação editável da estrutura
- **Fluxo Modo Visual:** estrutura → gerador HTML → Canvas
- **Fluxo Modo Código:** edição HTML → parser → atualiza estrutura → re-renderiza Canvas
- **Validação ao salvar** — valida sintaxe HTML, bindings Knockout e integridade da estrutura; rejeita e exibe erro se inválido
- **Seleção bidirecional** — clicar numa linha do código seleciona o nó correspondente na Árvore; selecionar na Árvore rola o código até o trecho correspondente
- **Uso típico** — bindings complexos, lógica condicional (`visible:`), ajustes avançados de CSS, funções de formatação em JS

---

### Aba Sincronizar (Vista Sincronizada)

Quando o operador seleciona a aba `🔗 Sincronizar`, o painel central divide em dois lado a lado — Canvas à esquerda e PDF à direita — com scroll e seleção sincronizados:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [Estrutura]  │ [ 🖥️ Canvas ] [ 📄 PDF ] [ </> Código ] [ 🔗 Sincronizar ] │ INSPETOR │
│ [Campos]     │                                                             │          │
│──────────────│  ┌─────────────────────┬─────────────────────┐              │ Inspetor │
│ 📄 Document  │  │  CANVAS (template)  │  PDF (original)     │              │ de       │
│ ├ 📦 Header  │  │                     │                     │              │ Elemento │
│ │ ├ 🖼 Logo  │  │  ╔═══════════════╗  │  ╔═══════════════╗  │              │          │
│ │ ├ 🔤 Cli.  │  │  ║ [LOGO]        ║  │  ║ [LOGO]        ║  │              │ Binding: │
│ │ └ 🔤 CPF   │  │  ║ EXTRATO CONTA ║  │  ║ EXTRATO CONTA ║  │              │ [cliente │
│ ├ 📦 Flow    │  │  ║ Cliente:      ║  │  ║ Cliente: João  ║  │              │  .nome]  │
│ │ ├ 📋 Tab.  │  │  ║  {{nome}}     ║  │  ║ Silva          ║  │              │          │
│ │ └ 📊 Graf. │  │  ║ CPF:          ║  │  ║ CPF:           ║  │              │          │
│ ├ 📦 Footer  │  │  ║  {{cpf}}      ║  │  ║ 123.456.789-00 ║  │              │          │
│ └ ···        │  │  ║───────────────║  │  ║────────────────║  │              │          │
│              │  │  ║ Data │ Valor  ║  │  ║ 01/01 │ 100    ║  │              │          │
│              │  │  ║ {{d}}│ {{v}}  ║  │  ║ 02/01 │ 200    ║  │              │          │
│              │  │  ╚═══════════════╝  │  ╚═══════════════╝  │              │          │
│              │  │                     │                     │              │          │
│              │  │  🔍 [ - 100% + ]    │  🔍 [ - 100% + ]   │              │          │
│              │  └─────────────────────┴─────────────────────┘              │          │
└──────────────┴─────────────────────────────────────────────────────────────┴──────────┘
```

**Anotações da Vista Sincronizada:**
- **Split view** — Canvas (template gerado) à esquerda, PDF (documento original) à direita
- **Scroll sincronizado** — rolar um painel rola o outro automaticamente
- **Seleção sincronizada** — clicar num elemento no Canvas destaca o bounding box correspondente no PDF (usa coordenadas detectadas pelo pipeline de visão)
- **Âncoras de layout** — pontos de referência detectados pelo pipeline (títulos, cabeçalhos de tabela, logos) aparecem como marcadores em ambos os painéis, conectando visualmente a estrutura do template ao documento original
- **Integra com Modo Cobertura** — quando ativo, Canvas mostra campos mapeados (verde) e não mapeados (vermelho); PDF mostra bounding boxes da IA
- **Usa página representativa** do Layout Type ativo
- **Zoom independente** — cada painel tem seu próprio controle de zoom

---

**Anotações da Barra de Ferramentas:**
- **Nome do template** — nome definido no Upload
- **Confiança** — clicável; abre popover com o breakdown dos 5 fatores:

```
┌──────────────────────────────────────┐
│ 🎯 Pontuação de Confiança: 91%      │
│                                      │
│ Estabilidade de Layout  ████████░ 89%│
│ Detecção de Âncoras     █████████░ 94%│
│ Qualidade do Grid       ████████░ 88%│
│ Variabilidade de Campos █████████░ 93%│
│ Concordância da Visão   █████████░ 92%│
│                                      │
│ Nível: ⚠️ Revisão Recomendada (80-95%)│
└──────────────────────────────────────┘
```

  - Níveis: ✅ Aprovado (95-100%) │ ⚠️ Revisão Recomendada (80-95%) │ 🔴 Revisão Humana (<80%)
  - Fecha ao clicar fora
- **Cobertura** — clicável; abre popover com breakdown por tipo de componente:

```
┌──────────────────────────────────────┐
│ 🗺️ Cobertura do Template: 93%       │
│                                      │
│ Campos mapeados:      18 de 20       │
│ Tabelas mapeadas:      2 de 2        │
│ Imagens mapeadas:      3 de 4        │
│ Gráficos mapeados:     1 de 1        │
│                                      │
│ Nível: ⚠️ Revisão Recomendada (80-95%)│
└──────────────────────────────────────┘
```

  - Níveis: ✅ Completo (≥95%) │ ⚠️ Revisão Recomendada (80-95%) │ 🔴 Análise Incompleta (<80%)
  - Cobertura é **por Layout Type** — ao trocar layout no seletor, o percentual e breakdown atualizam automaticamente
  - Cobertura **atualiza em tempo real** conforme o operador mapeia/desmapeia elementos
  - Em análise multi-documento, cobertura reflete a completude do template considerando todos os PDFs do cluster
  - Fecha ao clicar fora
- **Seletor de Layout Type** — dropdown com Layout Types detectados pela clusterização (ex: Capa, Transações, Resumo); cada layout tem seu próprio template; trocar alterna o Canvas, Árvore de Estrutura, **Confiança e Cobertura** (cada layout tem métricas independentes). **Oculto quando apenas 1 Layout Type detectado.**
- **Modo Cobertura** — toggle; no Canvas HTML destaca elementos mapeados/não mapeados; na aba PDF Referência destaca detecções da IA
- **Modo Diff** — toggle que ativa comparação de páginas representativas do Layout Type ativo entre documentos
- **Snap** — toggle de alinhamento magnético (ativo por padrão); ao arrastar/redimensionar elementos no Canvas, alinham às linhas de grade, colunas detectadas e bordas de outros elementos
- **Auto Fix** — normalização automática de espaçamento, grid, fontes
- **Salvar** — salva projeto como JSON (estado do editor, restaurável via Home → Abrir Projeto)
- **Exportar** — gera e baixa ZIP diretamente com template final (index.html, style.css, base.js, exemplo.js, assets/)

---

**Anotações do Painel Esquerdo — Aba "Estrutura":**

A Árvore de Estrutura mostra a **hierarquia do documento** como template:

```
📄 Document
├ 📦 Header          (repete cada página)
│ ├ 🖼 Logo
│ ├ 🔤 Cliente → {{cliente}}
│ └ 🔤 CPF → {{cpf}}
├ 📦 Flow            (conteúdo dinâmico, paginação automática)
│ ├ 📋 Tabela movimentos → {{movimentos}}
│ │ ├ data
│ │ ├ descricao
│ │ └ valor
│ ├ 📊 Gráfico vendas → {{vendasMensais}}
│ └ 🔤 Total → {{valorTotal}}
└ 📦 Footer          (repete cada página)
  └ 🔤 Página → {{pageNum}}
```

- **Ícones de tipo:** 📄 Document, 📦 Container/Seção, 🔤 Texto, 📋 Tabela, 📊 Gráfico, 🖼 Imagem
- **Bindings** — exibidos ao lado do nome (ex: `→ {{cliente}}`)
- **Elementos opcionais** — marcados com ⚠ (ex: `🔤 telefone ⚠`)
- **Click** → seleciona no Canvas + abre Inspetor correspondente
- **Drag & Drop** → reordenar elementos dentro da árvore (ex: mover gráfico acima da tabela)
- **Clique direito** → menu contextual:
  - "Adicionar elemento"
  - "Agrupar em seção"
  - "Duplicar"
  - "Remover"
  - "Mover para Header / Flow / Footer"
- Cada Layout Type tem sua própria árvore; trocar o Layout Type na toolbar atualiza a árvore

---

**Anotações do Painel Esquerdo — Aba "Campos":**

Lista todos os campos do XSD organizados por tipo, com status de mapeamento:

```
📋 Campos
 ├ cliente       🟩 mapeado
 ├ cpf           🟩 mapeado
 ├ telefone      🟥 não mapeado  ⚠
 ├ valorTotal    🟩 mapeado
 └ endereco      🟨 não confirmado

📊 Tabelas
 └ movimentos    🟩 mapeado

📈 Gráficos
 └ vendas        🟩 mapeado

📐 Seções
 ├ contato ⚠     (telefone + email)
 └ parcelas ⚠    (parcela_valor + parcela_data)

🖼️ Recursos
 ├ logo          🟩 mapeado
 └ assinatura    🟩 mapeado
```

- Útil para verificar "quais campos do XSD ainda não mapeei?"
- **Click** → localiza o elemento na Árvore de Estrutura + destaca no Canvas + abre Inspetor
- **Drag** → arrastar campo da lista para a Árvore de Estrutura para criar binding

---

**Anotações do Centro — Aba "Canvas HTML":**

O Canvas renderiza o **HTML real do template** dentro de um iframe isolado:

```
template.json → HTML Generator → HTML + CSS + Knockout bindings → iframe
```

- **WYSIWYG** — o que o operador vê no Canvas é exatamente o que o template final vai produzir
- **iframe** — isola CSS do template do CSS do editor (sem interferência)
- **Páginas visíveis verticalmente** — quando o conteúdo excede 1 página, o Canvas mostra múltiplas páginas empilhadas com quebra visível
- **Linhas de quebra de página** — `--- QUEBRA DE PÁGINA ---` mostram onde a paginação vai acontecer baseado nos dados atuais
- **Click** → seleciona elemento (destaca na Árvore + abre Inspetor)
- **Drag** → reposicionar elemento (atualiza template.json → re-renderiza Canvas)
- **Resize** → ajustar tamanho de elemento (handles nos cantos)
- **Zoom** — controles `[- 100% +]` no rodapé do Canvas (50% a 125%)
- **Scroll** — vertical dentro do iframe
- **Guias visuais** — margens da página, limites Header/Flow/Footer, colunas detectadas, snap lines
- **Sobreposições quando Modo Cobertura ativo:**
  - 🟩 Verde = campo com binding definido
  - 🟥 Vermelho = elemento na árvore mas sem binding
  - 🟨 Amarelo = detectado pela IA mas não confirmado
  - 🟪 Roxo = tabela mapeada
  - 🟧 Laranja (borda tracejada) = seção opcional
  - 📊 Laranja (borda sólida + ícone) = gráfico

---

**Anotações do Centro — Aba "PDF Referência":**

Mostra o **PDF original** da página representativa do Layout Type ativo:

```
┌──────────────────────────────────────────────┐
│  PDF Referência — Layout: Transações         │
│  Documento: [ Doc1.pdf ▼ ]  Página: 2/100   │
│  Página representativa de 285 páginas        │
├──────────────────────────────────────────────┤
│                                              │
│  Cliente: João Silva                         │
│  CPF: 123.456.789-00                         │
│                                              │
│  ┌────┬──────────┬──────┐                    │
│  │Data│Descrição │Valor │                    │
│  ├────┼──────────┼──────┤                    │
│  │01/01│Compra A │ 100  │                    │
│  │02/01│Compra B │ 200  │                    │
│  └────┴──────────┴──────┘                    │
│                                              │
│  [ÁREA DO GRÁFICO]                           │
│                                              │
│  🔍 [← →]  [ - 100% + ]                     │
└──────────────────────────────────────────────┘
```

- **Propósito:** referência visual para o operador comparar o template com o documento original
- Renderizado via **PDF.js**
- **Seletor de documento** — dropdown com todos os PDFs enviados
- **Página representativa** — sistema seleciona a melhor página do cluster; operador pode navegar outras
- **Indicador de cluster** — "Página representativa de 285 páginas" mostra que o template cobre muitas páginas
- **Sobreposições quando Modo Cobertura ativo:**
  - 🟦 Azul = bloco de texto detectado
  - 🟩 Verde = campo detectado e mapeado no template
  - 🟥 Vermelho = campo detectado mas não mapeado
  - 🟨 Amarelo = detectado pela IA mas não confirmado pelo operador
  - 🟪 Roxo = tabela detectada
  - 📊 Laranja = gráfico detectado

---

**Anotações do Painel Inspetor (Hierárquico):**

O Inspetor muda de acordo com o **nível do nó selecionado** na Árvore de Estrutura:

| Nível | Nó selecionado | Inspetor mostra |
|-------|---------------|-----------------|
| **1 — Página** | `Document` (raiz) | Inspetor de Página: tamanho, orientação, margens, alturas header/footer |
| **2 — Seção** | `Header`, `Flow`, `Footer` | Inspetor de Seção: altura, fundo, padding, repetição, visibilidade |
| **3 — Componente** | Tabela, Gráfico, Container, Imagem | Inspetor de Componente: data source, colunas, paginação, estilo, dimensões |
| **4 — Elemento** | Campo de texto, rótulo, ícone | Inspetor de Elemento: posição, tamanho, tipografia, cor, binding, visibilidade |

---

**Inspetor Nível 1 — Inspetor de Página (nó Document):**

```
┌─────────────────────────────────────┐
│ Inspetor de Página                  │
├─────────────────────────────────────┤
│ Tamanho da Página                   │
│ [ A4 ▼ ]                            │
│ Largura: [210] mm  Altura: [297] mm │
│                                     │
│ Orientação                          │
│ (●) Retrato  ( ) Paisagem          │
│                                     │
│ Margens                             │
│ Superior: [20] mm                   │
│ Inferior: [20] mm                   │
│ Esquerda: [15] mm                   │
│ Direita:  [15] mm                   │
│                                     │
│ Altura do Header: [120] px          │
│ Altura do Footer: [80] px           │
│                                     │
│ Área de Conteúdo (calculada):       │
│ 642 px                              │
│                                     │
│ Grid                                │
│ [ ✔ Exibir grid ]  Tamanho: [8] px  │
│                                     │
│ Colunas Detectadas                  │
│ Coluna 1: X = 80 px                │
│ Coluna 2: X = 450 px               │
│ [ 🔒 Travar colunas como guias ]   │
└─────────────────────────────────────┘
```

**Anotações:**
- Aparece quando o operador clica no nó `Document` na Árvore de Estrutura ou quando nenhum elemento está selecionado
- **Tamanho** — A4, Letter, Custom (campos largura/altura habilitados)
- **Margens** — definem os limites visuais no Canvas (guias de margem)
- **Alturas Header/Footer** — reservam espaço fixo no topo e rodapé de cada página
- **Área de Conteúdo** — calculada automaticamente: Altura página - Header - Footer - Margens
- **Grid** — ativa sobreposição de grade no Canvas para alinhamento manual
- **Colunas detectadas** — colunas identificadas pelo pipeline de layout; ao travar, viram snap guides

---

**Inspetor Nível 2 — Inspetor de Seção (Header / Flow / Footer):**

```
┌─────────────────────────────────────┐
│ Inspetor de Seção: Header           │
├─────────────────────────────────────┤
│ Tipo: Header                        │
│                                     │
│ Altura: [120] px                    │
│                                     │
│ Fundo                               │
│ Cor: [#FFFFFF]  Imagem: [nenhuma]   │
│                                     │
│ Padding                             │
│ Sup: [10]  Inf: [10]               │
│ Esq: [15]  Dir: [15]               │
│                                     │
│ Repetir em cada página              │
│ [ ✔ ]                               │
│                                     │
│ 🔒 Travar seção                     │
│ [ ] (impede mover elementos p/ fora)│
│                                     │
│ Visibilidade                        │
│ [ Sempre visível ▼ ]               │
└─────────────────────────────────────┘
```

**Inspetor de Seção: Flow:**

```
┌─────────────────────────────────────┐
│ Inspetor de Seção: Flow             │
├─────────────────────────────────────┤
│ Tipo: Flow (Conteúdo Dinâmico)      │
│                                     │
│ Espaçamento vertical: [12] px       │
│                                     │
│ Padding                             │
│ Sup: [10]  Inf: [10]               │
│ Esq: [15]  Dir: [15]               │
│                                     │
│ Permitir quebras de página          │
│ [ ✔ ]                               │
│                                     │
│ Visibilidade                        │
│ [ Sempre visível ▼ ]               │
└─────────────────────────────────────┘
```

**Anotações:**
- **Header/Footer** — possuem altura fixa e opção "Repetir em cada página"
- **Flow** — não tem altura fixa (expande com conteúdo); possui controle de espaçamento vertical e quebras de página
- **Travar seção** — impede arrastar elementos para fora do container (útil para manter logo sempre no Header)
- Também inclui seções opcionais criadas pelo operador (ex: seção "contato")

---

**Inspetor Nível 2 — Inspetor de Seção Opcional (agrupamento de campos):**

```
┌─────────────────────────────────────┐
│ Inspetor de Seção: contato          │
├─────────────────────────────────────┤
│ Nome: contato                       │
│                                     │
│ Campos agrupados:                   │
│  ├ telefone                         │
│  └ email                            │
│                                     │
│ Visibilidade                        │
│ [ Condicional ▼ ]                   │
│ ┌─────────────────────────────────┐ │
│ │ SE [telefone ▼] [existe ▼]     │ │
│ │ OU [email ▼]    [existe ▼]     │ │
│ └─────────────────────────────────┘ │
│ [ + Condição ]                      │
│ Código:                             │
│ <!-- ko if: telefone || email -->   │
│                                     │
│ Presença nos docs:                  │
│  Doc1: ✔  Doc2: ✖  Doc3: ✔  Doc4: ✖│
│                                     │
│ [ Desagrupar seção ]                │
│ [ Remover do template ]             │
└─────────────────────────────────────┘
```

**Inspetor de Seção opcional com regra de valor:**

```
┌─────────────────────────────────────┐
│ Inspetor de Seção: parcelamento     │
├─────────────────────────────────────┤
│ Nome: parcelamento                  │
│                                     │
│ Campos agrupados:                   │
│  ├ parcela_valor                    │
│  ├ parcela_data                     │
│  └ parcela_numero                   │
│                                     │
│ Visibilidade                        │
│ [ Condicional ▼ ]                   │
│ ┌─────────────────────────────────┐ │
│ │ SE [parcelas ▼] [> ▼] [1     ] │ │
│ └─────────────────────────────────┘ │
│ Código:                             │
│ <!-- ko if: parcelas() > 1 -->      │
│                                     │
│ Presença nos docs:                  │
│  Doc1: ✔  Doc2: ✖  Doc3: ✔  Doc4: ✔│
│                                     │
│ [ Desagrupar seção ]                │
│ [ Remover do template ]             │
└─────────────────────────────────────┘
```

**Anotações do Inspetor de Seção Opcional:**
- **Seção** = agrupamento lógico de campos que aparecem/desaparecem juntos
- Detectadas automaticamente pelo Analisador Multi-Documento quando múltiplos campos adjacentes compartilham o mesmo padrão de presença/ausência
- Operador pode criar seções manualmente selecionando elementos na Árvore e clicando "Agrupar em seção"
- **"Desagrupar seção"** → desfaz o agrupamento, campos voltam a ser independentes
- A Visibilidade da seção aplica o wrapper `<!-- ko if -->` ao bloco inteiro (não campo a campo)
- No Canvas, seções opcionais aparecem com **borda tracejada laranja** 🟧

---

**Inspetor Nível 3 — Inspetor de Componente: Tabela**

```
┌─────────────────────────────────────┐
│ Inspetor de Componente: Tabela      │
├─────────────────────────────────────┤
│ Nome: movimentos                    │
│ Fonte de dados: [ movimentos ▼ ]   │
│                                     │
│ Colunas                             │
│ ┌───────────┬────────┬───────────┐ │
│ │ Campo     │Largura │ Alinhamento│ │
│ ├───────────┼────────┼───────────┤ │
│ │ data      │  15%   │ esquerda  │ │
│ │ descricao │  60%   │ esquerda  │ │
│ │ valor     │  25%   │ direita   │ │
│ └───────────┴────────┴───────────┘ │
│                                     │
│ Linha                               │
│ Altura da linha: [28] px            │
│ Padding: [4] px                     │
│                                     │
│ Paginação                           │
│ [ ✔ ] Permitir quebra de página    │
│ [ ✔ ] Repetir cabeçalho           │
│ Mínimo linhas por página: [3]      │
│                                     │
│ Âncora                              │
│ [ Fluxo ▼ ]                        │
│                                     │
│ Manter junto                        │
│ [ ] Manter bloco inteiro na página │
│                                     │
│ Ordenação (opcional)                │
│ Campo: [ nenhum ▼ ]                │
│                                     │
│ Visibilidade                        │
│ [ Sempre visível ▼ ]               │
│                                     │
│ Camada                              │
│ [↑ Frente] [↓ Trás]               │
│                                     │
│ 🔒 Travar elemento                  │
│ [ ]                                 │
│                                     │
│ [ Remover do template ]             │
└─────────────────────────────────────┘
```

**Anotações do Inspetor de Tabela:**
- **Fonte de dados** — dropdown com arrays do XSD (ex: `movimentos`, `pagamentos`)
- **Colunas** — campos internos da array; largura em % ou px; alinhamento por coluna
- **Paginação** — controla comportamento quando tabela excede a página:
  - "Repetir cabeçalho" → cabeçalho da tabela reaparece em cada nova página
  - "Mínimo linhas" → evita páginas com apenas 1-2 linhas órfãs
  - Linhas nunca quebram no meio (regra automática)
- **Âncora** — Top (fixo no topo), Fluxo (segue conteúdo), Bottom (fixo no rodapé)
- **Manter junto** — quando ativo, tabela inteira fica na mesma página (se couber); se não couber, move para próxima página
- **Camada** — z-order (Frente/Trás) para quando elementos se sobrepõem
- **Travar** — impede mover/redimensionar acidentalmente no Canvas

---

**Inspetor Nível 3 — Inspetor de Componente: Gráfico (confiança alta):**

```
┌─────────────────────────────────────┐
│ Inspetor de Componente: Gráfico     │
├─────────────────────────────────────┤
│ Nome: vendasMensais                 │
│ Confiança: 87% 🟩                   │
│                                     │
│ Tipo de Gráfico                     │
│ [ Barras ▼ ]                        │
│                                     │
│ Vinculação de Dados                 │
│ Rótulos: [ meses ▼ ]               │
│ ┌─────────────────────────────────┐ │
│ │ Dataset 1                       │ │
│ │ Rótulo: Vendas                  │ │
│ │ Campo:  [ vendas ▼ ]            │ │
│ │ Cor:    [🟦]                    │ │
│ └─────────────────────────────────┘ │
│ [ + Adicionar dataset ]            │
│                                     │
│ Dimensões                           │
│ Largura: [400] px                   │
│ Altura:  [200] px                   │
│                                     │
│ ▼ Estilo                            │
│ Legenda:  [ ✔ Ativa ]              │
│ Grade:    [ ✔ Ativa ]              │
│ Animação: [ ✔ Ativa ]              │
│ Rótulos dos eixos:                  │
│  X: [Mês____________]              │
│  Y: [Valor (R$)_____]              │
│                                     │
│ Pré-visualização                    │
│ ┌─────────────────────────────────┐ │
│ │ Jan  ███                        │ │
│ │ Fev  ██████                     │ │
│ │ Mar  ████                       │ │
│ └─────────────────────────────────┘ │
│                                     │
│ Âncora                              │
│ [ Fluxo ▼ ]                        │
│                                     │
│ Manter junto                        │
│ [ ✔ ] Manter bloco na página       │
│                                     │
│ Visibilidade                        │
│ [ Sempre visível ▼ ]               │
│                                     │
│ [ Remover do template ]             │
└─────────────────────────────────────┘
```

**Inspetor de Gráfico com múltiplos datasets:**

```
┌─────────────────────────────────────┐
│ Inspetor de Componente: Gráfico     │
├─────────────────────────────────────┤
│ Nome: receitaVsDespesa              │
│ Confiança: 82% 🟩                   │
│                                     │
│ Tipo de Gráfico                     │
│ [ Linhas ▼ ]                        │
│                                     │
│ Vinculação de Dados                 │
│ Rótulos: [ meses ▼ ]               │
│ ┌─────────────────────────────────┐ │
│ │ Dataset 1                       │ │
│ │ Rótulo: Vendas                  │ │
│ │ Campo:  [ vendas ▼ ]            │ │
│ │ Cor:    [🟦]              [🗑️]  │ │
│ ├─────────────────────────────────┤ │
│ │ Dataset 2                       │ │
│ │ Rótulo: Despesas                │ │
│ │ Campo:  [ despesas ▼ ]          │ │
│ │ Cor:    [🟥]              [🗑️]  │ │
│ └─────────────────────────────────┘ │
│ [ + Adicionar dataset ]            │
│                                     │
│ Pré-visualização                    │
│ ┌─────────────────────────────────┐ │
│ │ 200 ─── · ── ·                  │ │
│ │ 150 ── · ──── ·── ·             │ │
│ │ 100 · ────────────── ·          │ │
│ │     Jan  Fev  Mar  Abr          │ │
│ │     ── Vendas  ·· Despesas      │ │
│ └─────────────────────────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

**Inspetor de Gráfico (confiança baixa):**

```
┌─────────────────────────────────────┐
│ Inspetor de Componente: Gráfico     │
├─────────────────────────────────────┤
│ Nome: grafico_1                     │
│ Confiança: 45% 🟥                   │
│                                     │
│ ⚠ Tipo não identificado            │
│ Selecione o tipo de gráfico:        │
│ ○ Barras    ○ Linhas   ○ Pizza     │
│ ○ Rosca     ○ Área     ○ Empilhado │
│ ○ Imagem estática (fallback)       │
│                                     │
│ Vinculação de Dados                 │
│ (configurar após selecionar tipo)   │
│                                     │
└─────────────────────────────────────┘
```

**Anotações do Inspetor de Gráfico:**
- Gráficos são reconstruídos como componentes **Chart.js dinâmicos**, não como imagens estáticas
- **Tipos de gráfico suportados:**

| Tipo | Descrição |
|------|-----------|
| Barras | Gráfico de barras verticais |
| Linhas | Gráfico de linhas com pontos |
| Pizza | Gráfico circular (setores) |
| Rosca | Gráfico circular com furo central |
| Área | Gráfico de linhas com preenchimento |
| Barras Empilhadas | Barras com múltiplos datasets empilhados |

- **Vinculação de dados** — dropdowns listam campos do XSD que são arrays (ex: `meses`, `vendas`, `despesas`)
- **Múltiplos datasets** — botão "+ Adicionar dataset" permite sobrepor séries no mesmo gráfico
- **Pré-visualização** — renderização simplificada (ASCII) dentro do Inspetor; o resultado real aparece no Canvas
- **Confiança baixa** (< 60%) — operador precisa selecionar tipo manualmente
- **Fallback estático** — quando gráfico é complexo demais, exporta como PNG (evitar quando possível)
- **Manter junto** — gráficos devem ficar na mesma página por padrão (ativado)

**Código gerado no template final:**

```html
<!-- HTML -->
<canvas id="vendasMensais" width="400" height="200"></canvas>

<!-- JavaScript (base.js) -->
new Chart(document.getElementById('vendasMensais'), {
  type: 'bar',
  data: {
    labels: data.meses,
    datasets: [{
      label: 'Vendas',
      data: data.vendas,
      backgroundColor: '#4A90D9'
    }]
  }
});
```

---

**Inspetor Nível 3 — Inspetor de Componente: Imagem**

```
┌─────────────────────────────────────┐
│ Inspetor de Componente: Imagem      │
├─────────────────────────────────────┤
│ Nome: logo                          │
│ Origem: assets/logo.png             │
│                                     │
│ Dimensões                           │
│ Largura: [200] px                   │
│ Altura:  [60] px                    │
│                                     │
│ Escala                              │
│ (●) Ajustar  ( ) Conter  ( ) Estic.│
│                                     │
│ Alinhamento                         │
│ ( ) Esquerda (●) Centro ( ) Direita│
│                                     │
│ Âncora                              │
│ [ Topo ▼ ]                          │
│                                     │
│ [ 📤 Substituir imagem ]            │
│ [ 📥 Baixar asset ]                │
│ [ 🗑️ Remover ]                     │
└─────────────────────────────────────┘
```

---

**Inspetor Nível 3 — Inspetor de Componente: Container**

```
┌─────────────────────────────────────┐
│ Inspetor de Componente: Container   │
├─────────────────────────────────────┤
│ Nome: info_cliente                  │
│                                     │
│ Layout                              │
│ (●) Vertical  ( ) Horizontal       │
│                                     │
│ Espaçamento entre itens: [8] px    │
│                                     │
│ Padding                             │
│ Sup: [10]  Inf: [10]               │
│ Esq: [15]  Dir: [15]               │
│                                     │
│ Alinhamento                         │
│ ( ) Esquerda (●) Centro ( ) Direita│
│                                     │
│ Âncora                              │
│ [ Fluxo ▼ ]                        │
│                                     │
│ Manter junto                        │
│ [ ✔ ] Manter bloco na página       │
│                                     │
│ Visibilidade                        │
│ [ Sempre visível ▼ ]               │
└─────────────────────────────────────┘
```

---

**Inspetor Nível 4 — Inspetor de Elemento (campo de texto):**

```
┌─────────────────────────────────────┐
│ Inspetor de Elemento: cliente       │
├─────────────────────────────────────┤
│ Vínculo: text: cliente              │
│ Confiança: 95% 🟩                   │
│                                     │
│ Posição                             │
│ X: [120] px   Y: [80] px           │
│                                     │
│ Tamanho                             │
│ Largura: [200] px                   │
│ Altura:  [ Auto ▼ ]                │
│                                     │
│ Tipografia                          │
│ Fonte: [ Roboto ▼ ]                │
│ Tamanho: [12] px                    │
│ Peso: [ Bold ▼ ]                   │
│ Cor: [#000000]                      │
│ Entrelinha: [1.4]                   │
│                                     │
│ Alinhamento                         │
│ (●) Esq  ( ) Centro  ( ) Dir      │
│                                     │
│ Espaçamento                         │
│ Padding: S[4] I[4] E[0] D[0]      │
│ Margem:  S[0] I[8] E[0] D[0]      │
│                                     │
│ Texto                               │
│ (●) Quebrar  ( ) Truncar  ( ) Exp. │
│                                     │
│ Tipo de Campo                       │
│ [ Texto ▼ ]                         │
│                                     │
│ Âncora                              │
│ [ Topo ▼ ]                          │
│                                     │
│ Visibilidade                        │
│ [ Sempre visível ▼ ]               │
│                                     │
│ Camada                              │
│ [↑ Frente] [↓ Trás]               │
│                                     │
│ 🔒 Travar elemento                  │
│ [ ]                                 │
│                                     │
│ [ Remover do template ]             │
└─────────────────────────────────────┘
```

**Inspetor de Elemento — campo opcional (Condicional):**

```
┌─────────────────────────────────────┐
│ Inspetor de Elemento: telefone      │
├─────────────────────────────────────┤
│ Vínculo: text: telefone             │
│ Confiança: 72% 🟨                   │
│                                     │
│ Posição                             │
│ X: [120] px   Y: [140] px          │
│                                     │
│ Tamanho                             │
│ Largura: [200] px                   │
│ Altura:  [ Auto ▼ ]                │
│                                     │
│ Tipografia                          │
│ Fonte: [ Roboto ▼ ]                │
│ Tamanho: [11] px                    │
│ Peso: [ Normal ▼ ]                 │
│ Cor: [#000000]                      │
│                                     │
│ Tipo de Campo                       │
│ [ Telefone ▼ ]                      │
│                                     │
│ Regras de Formato                   │
│ Máscara: (XX) XXXXX-XXXX           │
│                                     │
│ Pré-visualização                    │
│ Entrada: 11999998888                │
│ Saída:   (11) 99999-8888           │
│                                     │
│ Visibilidade                        │
│ [ Condicional ▼ ]                   │
│ ┌─────────────────────────────────┐ │
│ │ SE [telefone ▼] [existe ▼]     │ │
│ └─────────────────────────────────┘ │
│ Código: <!-- ko if: telefone -->    │
│                                     │
│ Presença nos docs:                  │
│  Doc1: ✖  Doc2: ✔  Doc3: ✖  Doc4: ✔│
│                                     │
│ [ Remover do template ]             │
└─────────────────────────────────────┘
```

**Inspetor de Elemento — campo com tipo Moeda:**

```
┌─────────────────────────────────────┐
│ Inspetor de Elemento: valorTotal    │
├─────────────────────────────────────┤
│ Vínculo: text: valorTotal           │
│ Confiança: 95% 🟩                   │
│                                     │
│ Posição                             │
│ X: [350] px   Y: [280] px          │
│                                     │
│ Tamanho                             │
│ Largura: [150] px                   │
│ Altura:  [ Auto ▼ ]                │
│                                     │
│ Tipografia                          │
│ Fonte: [ Roboto ▼ ]                │
│ Tamanho: [12] px  Peso: [ Bold ▼ ] │
│                                     │
│ Tipo de Campo                       │
│ [ Moeda ▼ ]                         │
│                                     │
│ Regras de Formato                   │
│ Moeda: BRL                          │
│ Casas decimais: 2                   │
│ Separador de milhar: .              │
│                                     │
│ Pré-visualização                    │
│ Entrada: 1200.5                     │
│ Saída:   R$ 1.200,50               │
│                                     │
│ Visibilidade                        │
│ [ Sempre visível ▼ ]               │
│                                     │
│ [ Remover do template ]             │
└─────────────────────────────────────┘
```

**Inspetor de Elemento — fonte não encontrada:**

```
┌─────────────────────────────────────┐
│ Inspetor de Elemento: titulo        │
├─────────────────────────────────────┤
│ Vínculo: text: titulo               │
│                                     │
│ Tipografia                          │
│ Fonte: [ Univers ▼ ]  ⚠ Não encontrada │
│ Fallback: Helvetica                 │
│ [ 📤 Upload TTF/OTF ]              │
│                                     │
│ Tamanho: [16] px  Peso: [ Bold ▼ ] │
│ Cor: [#333333]                      │
│                                     │
│ ...                                 │
└─────────────────────────────────────┘
```

**Anotações do Inspetor de Elemento:**
- **Posição X/Y** — coordenadas relativas ao container pai (Header, Flow, Footer)
- **Tamanho** — Largura fixa, %, ou Auto; Altura fixa ou Auto (expande com conteúdo)
- **Tipografia** — fonte extraída automaticamente do PDF; se não disponível, mostra fallback + botão upload
- **Texto** — Quebrar (wrap), Truncar (clip), Expandir (auto-expand container)
- **Tipo de Campo** — define formatação do dado (ver tabela de tipos abaixo)
- **Âncora** — Topo (fixo), Fluxo (segue conteúdo), Rodapé (fixo embaixo)
- **Camada** — z-order para sobreposição de elementos
- **Travar** — impede movimentação/redimensionamento acidental

---

**Propriedade Visibilidade:**

Todos os elementos, seções e componentes possuem a propriedade **Visibilidade** com 3 opções:

| Valor | Comportamento | Código Knockout gerado |
|-------|--------------|----------------------|
| **Sempre visível** | Elemento sempre presente no HTML (padrão) | Nenhum wrapper |
| **Condicional** | Expande mini-construtor SE/condição | `<!-- ko if: expressão -->` |
| **Escondido** | Elemento omitido do template final | Elemento removido do HTML |

- Quando o operador seleciona **"Condicional"**, aparece um mini-construtor inline:
  - `SE [ campo ▼ ] [ operador ▼ ] [ valor ]`
  - **Operadores:** `existe`, `não existe`, `=`, `≠`, `>`, `<`
  - **Campos no dropdown:** todos os campos do XSD
  - Condições compostas com **E/OU** via botão `[ + Condição ]`
- **Código gerado** — linha somente leitura mostrando o binding Knockout resultante
- **Pré-preenchido** — campos detectados como opcionais pela Matriz de Variação já vêm com Visibilidade = Condicional
- **Pré-visualização** — ao alterar visibilidade, o Canvas atualiza mostrando o efeito

**Exemplo — Condicional com expressão composta:**

```
│ Visibilidade                        │
│ [ Condicional ▼ ]                   │
│ ┌─────────────────────────────────┐ │
│ │ SE [desconto ▼] [> ▼] [0     ] │ │
│ │  E [tipo ▼]     [= ▼] [VIP   ] │ │
│ └─────────────────────────────────┘ │
│ [ + Condição ]                      │
│ Código: <!-- ko if: desconto() > 0  │
│         && tipo() === 'VIP' -->     │
```

---

**Tipos de campo suportados:**

| Tipo | Regras de formato | Exemplo |
|------|-------------------|---------|
| `Texto` | Nenhuma | João Silva |
| `Número` | Casas decimais, separador | 1.200 |
| `Moeda` | Moeda, decimais, separador milhar | R$ 1.200,50 |
| `Data` | Formato (dd/mm/aaaa, aaaa-mm-dd) | 01/01/2026 |
| `CPF` | Máscara XXX.XXX.XXX-XX | 123.456.789-00 |
| `CNPJ` | Máscara XX.XXX.XXX/XXXX-XX | 12.345.678/0001-90 |
| `Percentual` | Decimais, símbolo | 15,5% |
| `Telefone` | Máscara (XX) XXXXX-XXXX | (11) 99999-8888 |
| `Personalizado` | Máscara livre ou função JS | Definido pelo operador |

- **Pré-visualização instantânea** — ao trocar Tipo ou Regras, mostra Entrada → Saída em tempo real
- **Personalizado** permite máscara (padrão de caracteres) ou função JavaScript

---

**Anotações do Analisador Multi-Documento:**
- Lista dos PDFs enviados com status (base/variação)
- **Matriz de Variação** — tabela completa mostrando presença (✔) ou ausência (✖) de cada campo por documento:

```
┌──────────────────────────────────────────────────────────────────────┐
│ MATRIZ DE VARIAÇÃO                                                   │
├──────────────┬───────┬───────┬───────┬───────┬───────────────────────┤
│ Campo        │ Doc1  │ Doc2  │ Doc3  │ Doc4  │ Detecção              │
├──────────────┼───────┼───────┼───────┼───────┼───────────────────────┤
│ cliente      │  ✔    │  ✔    │  ✔    │  ✔    │ campo obrigatório     │
│ cpf          │  ✔    │  ✔    │  ✔    │  ✔    │ campo obrigatório     │
│ telefone     │  ✖    │  ✔    │  ✖    │  ✔    │ ⚠ campo opcional      │
│ email        │  ✖    │  ✔    │  ✖    │  ✔    │ ⚠ campo opcional      │
│ endereco     │  ✔    │  ✔    │  ✖    │  ✔    │ ⚠ campo opcional      │
│ desconto     │  ✖    │  ✖    │  ✔    │  ✖    │ ⚠ seção condicional   │
│ aviso_atraso │  ✔    │  ✖    │  ✖    │  ✖    │ ⚠ seção condicional   │
├──────────────┴───────┴───────┴───────┴───────┴───────────────────────┤
│ Detecções automáticas:                                               │
│  • 2 campos opcionais → geram <!-- ko if: campo -->                 │
│  • 1 seção opcional detectada: "contato" (telefone + email)         │
│    → mesma presença ✖✔✖✔ → agrupados com <!-- ko if -->            │
│  • 2 seções condicionais → geram <!-- ko if: secao -->              │
│  • 1 variação de layout (tabela movimentos: 3-7 linhas)             │
└──────────────────────────────────────────────────────────────────────┘
```

- **Detecção automática** baseada na Matriz de Variação:
  - ✔ em todos → **campo obrigatório**
  - ✔ em alguns → **campo opcional** (gera `<!-- ko if: campo -->`)
  - Campos adjacentes com mesmo padrão → **seção opcional** (agrupados automaticamente)
  - ✔ em apenas 1 → **seção condicional**
  - Linhas variáveis em tabelas → **layout dinâmico** (foreach com contagem variável)
- Aparece apenas quando múltiplos PDFs foram enviados (1 PDF = seção oculta)

**Feedback do sistema (sem console dedicado):**
- Avisos de campos não mapeados → badges ⚠ na Árvore de Estrutura e aba Campos
- Fontes faltando → aviso inline no Inspetor de Elemento (com botão upload)
- Erros de renderização → coluna "Detalhes" na aba Relatório + toast temporário
- Inconsistências → badges na Árvore + overlay no Canvas (modo cobertura)

**Anotações do Painel Inferior — 2 abas:**

**Aba "Dados de Teste":**

```
┌───────────────────────────────────────┬──────────────────────────────────────┐
│ Datasets:                             │ Resumo: sample.xml                   │
│                                       │                                      │
│ ● sample.xml     ✓  Validado   [🗑️] │ Campos:  cliente, cpf, valorTotal    │
│   large.xml      ✓  Validado   [🗑️] │ Loops:   transacoes (2 itens)        │
│   vip.json       ⚠  1 aviso    [🗑️] │ Tamanho: 1.2 KB                     │
│   synthetic_sm   ✓  Gerado     [🗑️] │ Status:  ✓ Validado contra XSD      │
│                                       │                                      │
│ [ Upload Dataset ]                    │ [ Aplicar no Canvas ]                │
│ [ Gerar Sintético ]                   │ [ ▶ Testar Todos ]                   │
│                         Máx: 5        │ [ Editar Dataset... ]                │
└───────────────────────────────────────┴──────────────────────────────────────┘
```

- **Lista de datasets** — esquerda; um ativo por vez (●); clicar seleciona e mostra resumo
- **Upload Dataset** — aceita XML ou JSON; valida automaticamente contra o XSD do projeto
- **Indicadores de status:**
  - ✓ Validado — dataset válido contra XSD
  - ⚠ Aviso — válido mas com campos opcionais ausentes
  - ✕ Inválido — não passa na validação XSD (mostra erros no resumo)
- **Gerar Sintético** — gera datasets automaticamente a partir do XSD:
  - `synthetic_small` — 1 linha de transação (testa template mínimo)
  - `synthetic_medium` — 10 linhas (testa paginação simples)
  - `synthetic_large` — 100+ linhas (testa overflow e lazy rendering)
  - MVP: foco em variação do tamanho de loops (foreach)
- **Resumo do dataset** — visão compacta: campos presentes, quantidade de itens nos loops, tamanho do arquivo, status de validação. Não carrega o JSON inteiro no painel.
- **"Editar Dataset..."** — abre modal com Monaco Editor em tela cheia para edição confortável de datasets grandes (centenas de transações)
- **Aplicar no Canvas** — renderiza o template com o dataset ativo; Canvas atualiza em tempo real
- **Testar Todos** — executa todos os datasets habilitados em sequência; resultado aparece na aba Relatório
- **Operações por dataset:** selecionar (●), deletar (🗑️), desabilitar (clique secundário)
- **Limite MVP:** máximo 5 datasets por template

**Aba "Relatório":**

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ RELATÓRIO DE TESTES                                     [ ▶ Testar Todos ]  │
├──────────────┬────────┬────────────┬─────────┬───────────────────────────────┤
│ Dataset      │ Páginas│ Cobertura  │ Status  │ Detalhes                      │
├──────────────┼────────┼────────────┼─────────┼───────────────────────────────┤
│ sample.xml   │   1    │   95%      │  ✓ OK   │                               │
│ large.xml    │   5    │   92%      │  ⚠ Aviso│ Footer colisão pg 4           │
│ vip.json     │   2    │   96%      │  ✓ OK   │                               │
│ synthetic_lg │  12    │   90%      │  ✓ OK   │                               │
├──────────────┴────────┴────────────┴─────────┴───────────────────────────────┤
│ Cobertura por elemento:                                                      │
│ Elemento         │ sample │ large │ vip  │ synthetic                         │
│ Header           │   ✓    │   ✓   │  ✓   │    ✓                             │
│ Cliente Info     │   ✓    │   ✓   │  ✓   │    ✓                             │
│ Seção VIP        │   ✕    │   ✕   │  ✓   │    ✕                             │
│ Tabela Transações│   ✓    │   ✓   │  ✓   │    ✓                             │
│ Footer           │   ✓    │   ✓   │  ✓   │    ✓                             │
├──────────────────┴────────┴───────┴──────┴───────────────────────────────────┤
│ Legenda: ✓ Renderizado │ ✕ Não renderizado │ Amarelo = parcial               │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Tabela superior** — resumo: dataset × páginas × cobertura × status
- **Tabela inferior** — cobertura por elemento: quais elementos do template aparecem em cada dataset
- **Status:** ✓ OK, ⚠ Aviso (renderizou com problemas), ❌ Erro (falha de renderização)
- Executado via botão "▶ Testar Todos" (disponível nas abas Dados e Relatório)

---

### Estado: Modo Cobertura ATIVO

Toggle ativado na barra de ferramentas. Funciona nas duas abas:

**No Canvas HTML:**
```
┌──────────────────────────────────────────────────────────────────────────┐
│  CANVAS HTML — Modo Cobertura                        Cobertura: 93%     │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ██ [LOGO] EXTRATO DE CONTA ████████████████████████   🟩 mapeado      │
│  ██ Cliente: João Silva ████████████████████████████   🟩 mapeado      │
│  ██ CPF: 123.456.789-00 ███████████████████████████   🟩 mapeado      │
│  ██ Telefone: (vazio) ██████████████████████████████   🟥 sem binding  │
│  ██ Endereço: Rua X ██████████████████████████████   🟨 não confirmado│
│                                                                          │
│  ┌────────────────────────────────────────────┐                          │
│  │  Tabela movimentos                  🟩     │                          │
│  │  ██████████████████████████████████████    │                          │
│  └────────────────────────────────────────────┘                          │
│                                                                          │
│  [ Destacar Campos Faltantes ]                                           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**No PDF Referência:**
```
┌──────────────────────────────────────────────────────────────────────────┐
│  PDF REFERÊNCIA — Modo Cobertura                                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🟦 [bloco de texto detectado]                                          │
│  🟩 Cliente: João Silva           (detectado + mapeado no template)     │
│  🟩 CPF: 123.456.789-00          (detectado + mapeado)                  │
│  🟥 Telefone: (11) 99999-8888    (detectado, NÃO mapeado)              │
│  🟨 Observação: texto livre       (detectado IA, não confirmado)        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Anotações:**
- **No Canvas** — mostra se os elementos do template têm binding definido (verde) ou faltam (vermelho)
- **No PDF** — mostra o que a IA detectou no documento original e se foi mapeado no template
- **"Destacar Campos Faltantes"** → filtra a aba Campos para mostrar só os não mapeados
- Pontuação de cobertura atualiza em tempo real conforme operador corrige mapeamentos
- Cobertura usa **cálculo ponderado** por tipo de elemento (campos de texto, tabelas, imagens têm pesos diferentes)

**Escopo MVP do Sistema de Cobertura:**
- ✔ Percentual de cobertura no header do editor (popover com breakdown)
- ✔ Toggle Modo Cobertura na toolbar (overlay verde/vermelho no Canvas e PDF)
- ✔ Cobertura por Layout Type (atualiza ao trocar layout)
- ✖ Cobertura por zona do documento (não no MVP)
- ✖ Histórico de cobertura (não no MVP)
- ✖ Analytics de cobertura (não no MVP)

---

### Estado: Modo Diff ATIVO

Toggle ativado na barra de ferramentas. Compara **páginas representativas do mesmo Layout Type** entre documentos:

```
┌──────────────────────────────────────────────────────────────────────────┐
│  MODO DIFF — Layout: Transações                                          │
│  Comparar: [ Doc1 (pg 2) ▼ ]  vs  [ Doc3 (pg 2) ▼ ]                   │
├─────────────────────────────┬────────────────────────────────────────────┤
│  Doc1 — Representativa      │  Doc3 — Representativa                    │
│                              │                                          │
│  Cliente: João               │  Cliente: Maria                         │
│  CPF: 123.456.789-00         │  CPF: 987.654.321-00                    │
│  ───────────────             │  Telefone: 11 99999-9999     🟥 NOVO     │
│                              │  ───────────────                        │
│  ┌──────────────────┐        │  ┌──────────────────┐                   │
│  │ Data │ Valor     │        │  │ Data │ Valor     │                   │
│  │ 01/01│ 100       │        │  │ 01/01│ 150       │  🟨 DIFERENTE    │
│  │ 02/01│ 200       │        │  │ 02/01│ 200       │  🟩 IGUAL        │
│  └──────────────────┘        │  │ 03/01│ 300       │  🟥 NOVO         │
│                              │  └──────────────────┘                   │
│                              │                                          │
├──────────────────────────────┴──────────────────────────────────────────┤
│ Resultado:                                                               │
│  • telefone → campo opcional (ausente no Doc1)                          │
│  • movimentos → linhas variáveis (3 no Doc1, 5 no Doc3)                │
│  • ⚠ Mudança de layout detectada:                                       │
│    Tabela movimentos deslocou 20px para baixo em Doc3                   │
└──────────────────────────────────────────────────────────────────────────┘
```

**Anotações:**
- Compara **páginas representativas do mesmo Layout Type** entre documentos (não PDFs inteiros)
- Seletor de Layout Type na toolbar filtra quais páginas representativas são comparáveis
- Destaque automático:
  - 🟩 Verde = elemento igual (mesma posição e conteúdo)
  - 🟨 Amarelo = existe nos dois mas posição diferente
  - 🟥 Vermelho = existe em um mas não no outro
- **Resultado** — resumo das inferências: campos opcionais, seções condicionais, linhas variáveis, mudanças de layout
- Operador pode confirmar/rejeitar inferências

---

### Ação: Exportar (dentro do Editor)

Quando o operador clica "📦 Exportar" na barra de ferramentas:
- Gera o ZIP diretamente e inicia o download (sem modal)
- Pacote contém:
  - `template/` — index.html, css/style.css, js/base.js, js/exemplo.js, assets/
  - `test_data/` (opcional) — datasets de teste usados na validação (sample.xml, etc.)
- Recomendação no wireframe: antes de exportar, operador deve verificar Cobertura ≥95% e executar "▶ Testar Todos" na aba Relatório

---

### Ação: Salvar (dentro do Editor)

Quando o operador clica "💾 Salvar":
- Serializa estado completo do editor como **JSON**
- Download automático do arquivo `.json`
- Inclui: template.json (estrutura), referências de assets, configurações de página, bindings, regras
- **NÃO inclui** PDFs originais, assets binários (estes são re-extraídos se necessário)
- Restaurável via Home → Abrir Projeto

**Diferença Salvar vs Exportar:**

| Ação | Formato | Conteúdo | Propósito |
|------|---------|----------|-----------|
| **Salvar** | .json | Estado do editor | Retomar trabalho depois |
| **Exportar** | .zip | HTML + CSS + JS + assets | Template final para sistemas externos |

---

---

## Modal Global — Bibliotecas

```
┌──────────────────────────────────────────────────────────────────────────┐
│  📚 Bibliotecas de Componentes                                 [ ✕ ]    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  🔍 Buscar: [________________________________]                          │
│                                                                          │
│  Headers                                                                 │
│  ├── Header simples (logo + título)                                      │
│  ├── Header com dados do cliente                                         │
│  └── Header bancário padrão                                              │
│                                                                          │
│  Footers                                                                 │
│  ├── Footer com paginação                                                │
│  ├── Footer com assinatura                                               │
│  └── Footer legal (termos)                                               │
│                                                                          │
│  Tabelas                                                                 │
│  ├── Tabela simples (3 cols)                                             │
│  ├── Tabela com subtotais                                                │
│  └── Tabela agrupada                                                     │
│                                                                          │
│  [ Inserir no Template ]                                                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

**Anotações:**
- Acessível de qualquer tela via botão [📚 Bibliotecas] no cabeçalho
- Componentes HTML/Knockout reutilizáveis organizados por categoria
- "Inserir no Template" adiciona o trecho selecionado à Árvore de Estrutura
- FUTURO: permitir que operadores salvem seus próprios trechos

---

## Diagrama de Fluxo

```
┌──────┐     ┌──────────┐     ┌──────────────┐     ┌─────────────────────────────────┐
│ HOME │ ──→ │  UPLOAD   │ ──→ │  ANALYZING   │ ──→ │            EDITOR               │
│      │     │           │     │  (tela de     │auto │                                 │
│ Novo │     │ PDFs+XSD  │     │  progresso)   │     │  ┌──────────────┐              │
│ Abrir│     │ Nome tmpl │     │              │     │  │   Editing     │ ← principal  │
│      │     │           │     │  pipeline     │     │  │ Canvas + Árv. │              │
└──────┘     └──────────┘     │  23 etapas    │     │  │ + Inspetor    │              │
   ↑            ↑ cancelar     │  8 blocos     │     │  └──────┬───────┘              │
   │            └──────────────┘              │     │         │                        │
   │                                           │     │    ┌────┴────┬────────┬──────┐ │
   │     Abrir Projeto ───────────────────────│────│→ ↓         ↓           ↓    │ │
   │     (restaura .json)                      │     │  Modo    Modo       Exportar │ │
   │                                           │     │  Cobert. Diff     (ZIP direto)│ │
   │                                           │     └─────────────────────────────────┘
   │
   └──────────── 💾 Salvar (projeto .json para retomar depois)
```

---

## Inventário de Componentes

### Átomos
| Componente | Uso |
|-----------|-----|
| Button | Ações (Salvar, Exportar, Aplicar, Voltar) |
| Badge | Confiança %, Cobertura %, status |
| Toggle | Modo Cobertura, Modo Diff, Snap |
| Input | Nome do template, busca bibliotecas, valores numéricos |
| ProgressBar | Fatores de confiança, progresso do pipeline |
| Icon | Árvore de estrutura (📄📦🔤📋📊🖼), status |
| Tooltip | Dicas contextuais |
| ColorPicker | Cor de texto, cor de fundo, cor de dataset |
| ZoomControl | Zoom do Canvas (50-125%) |

### Moléculas
| Componente | Composição | Uso |
|-----------|-----------|-----|
| DropzoneCard | Dropzone + lista arquivos + dicas | Upload de PDFs e XSD |
| StructureTreeNode | Ícone + nome + binding + badge | Nó na Árvore de Estrutura |
| FieldNavItem | Ícone + nome + badge status | Item na aba Campos |
| VariationRow | Campo + ✔/✖ por documento | Matriz de Variação |
| InspectorField | Rótulo + valor + ação | Propriedades no Inspetor |

| DatasetItem | Nome + status badge + botão deletar | Item na lista de datasets |
| TestReportRow | Dataset + páginas + cobertura + status | Linha do relatório de testes |
| CoverageMatrixRow | Elemento + ✓/✕ por dataset | Cobertura por elemento no relatório |
| LayoutTypeTab | Nome + contador páginas | Seletor de Layout Type na toolbar |
| ConfidenceFactor | Rótulo + ProgressBar + % | Fatores da Pontuação de Confiança |
| SectionOverlay | Borda tracejada + rótulo seção | Seção opcional no Canvas |
| AnchorSelector | Dropdown (Topo/Fluxo/Rodapé) | Seleção de âncora no Inspetor |
| PositionControl | Label + X + Y inputs | Posição do elemento |
| SizeControl | Label + L + A inputs | Tamanho do elemento |
| FontWarning | Nome fonte + fallback + botão upload | Fonte não encontrada |
| FileTreeItem | Ícone + nome arquivo | Lista de arquivos na Exportação |
| PageBreakLine | Linha tracejada + rótulo | Quebra de página no Canvas |

### Organismos
| Componente | Função |
|-----------|--------|
| TopToolbar | Ações globais: layout type, modos, preview, salvar, exportar |
| StructureTree | Aba esquerda — hierarquia Document > Header > Flow > Footer |
| FieldNavigator | Aba esquerda — lista de campos/tabelas/gráficos/seções/recursos |
| HTMLCanvas | Centro (aba Canvas) — iframe com HTML real renderizado do template |
| PDFReference | Centro (aba PDF) — PDF.js com página representativa do cluster |
| CodeEditor | Centro (aba Código) — Monaco Editor com syntax highlighting HTML/CSS/JS |
| SyncView | Centro (aba Sincronizar) — split view Canvas + PDF com scroll sincronizado |
| FileExplorer | Aba esquerda (ativa na aba Código) — estrutura de arquivos do template |
| InspectorPanel | Direita — Inspetor hierárquico (Página/Seção/Componente/Elemento) |
| PageInspector | Inspetor nível 1: tamanho página, margens, grid, colunas |
| SectionInspector | Inspetor nível 2: Header/Flow/Footer + seções opcionais |
| ComponentInspector | Inspetor nível 3: Tabela/Gráfico/Container/Imagem |
| ElementInspector | Inspetor nível 4: posição, tamanho, tipografia, binding, visibilidade |
| MultiDocAnalyzer | Matriz de Variação + status dos documentos |
| TestDataPanel | Aba "Dados de Teste" — lista datasets + editor + aplicar + testar todos |
| DatasetList | Lista de datasets com status (✓/⚠/✕), seleção e operações |
| DatasetEditor | Editor JSON/XML do dataset ativo com syntax highlighting |
| SyntheticGenerator | Gerador de datasets sintéticos a partir do XSD (small/medium/large) |
| TestReportPanel | Aba "Relatório" — tabela resumo + matriz cobertura por elemento |
| CoverageOverlay | Sobreposição colorida no Canvas e PDF |
| DiffViewer | Lado a lado de páginas representativas no Modo Diff |
| ConfidencePopover | Popover clicável na toolbar — breakdown dos 5 fatores de confiança |
| BibliotecasModal | Biblioteca de componentes reutilizáveis |

### Templates (Layouts)
| Layout | Uso |
|--------|-----|
| HomeLayout | Tela 0 — cards centralizados |
| UploadLayout | Tela 1 — dropzones + ações |
| EditorLayout | Tela 2 — 5 regiões (toolbar, painel esquerdo com 3 abas, centro com 4 abas, inspetor, inferior) |
| ModalLayout | Modal de Bibliotecas |

---

## Estados do Editor (Ciclo de vida)

| Estado | Descrição | Transição |
|--------|-----------|-----------|
| `uploading` | Operador seleciona PDFs + XSD | → `analyzing` (clica Iniciar) |
| `analyzing` | Tela de progresso dedicada — pipeline em execução, sem Editor | → `editing` (auto ao concluir) |
| `editing` | Trabalho principal: Árvore + Canvas + Inspetor | → `testing`, `exporting`, `saving` |
| `testing` | Painel inferior ativo com "▶ Testar Todos" em execução | → `editing` (auto ao concluir) |
| `exporting` | Gerando ZIP para download | → `editing` (auto) |
| `saving` | Salvando projeto .json | → `editing` (auto) |

---

## Árvore de Componentes (Implementação)

```
App
├── HomePage
│   ├── HomeHeader
│   └── ProjectCards
├── UploadPage
│   ├── UploadHeader
│   ├── TemplateNameInput
│   ├── PDFDropzone
│   ├── XSDDropzone
│   ├── DataDropzone (XML/JSON opcional)
│   └── UploadActions
├── TemplateEditor
│   ├── TopToolbar
│   │   ├── TemplateInfo (nome, confidence, coverage)
│   │   ├── LayoutTypeSelector (tabs/dropdown de layout types)
│   │   └── ToolbarActions (coverage, diff, snap, autofix, preview, save, export)
│   ├── LeftPanel
│   │   ├── StructureTree (aba Estrutura)
│   │   │   ├── DocumentNode
│   │   │   ├── SectionNode (Header, Flow, Footer)
│   │   │   ├── ComponentNode (Table, Chart, Container, Image)
│   │   │   └── ElementNode (Text, Field, Label)
│   │   ├── FieldNavigator (aba Campos)
│   │   │   ├── FieldList
│   │   │   ├── TableList
│   │   │   ├── ChartList
│   │   │   ├── SectionList
│   │   │   └── AssetList
│   │   └── FileExplorer (aba Arquivos — ativa na aba Código)
│   │       ├── FileTreeNode
│   │       └── FileIcon
│   ├── CenterPanel
│   │   ├── HTMLCanvas (aba Canvas)
│   │   │   ├── CanvasIframe
│   │   │   ├── OverlayLayer
│   │   │   ├── SnapGuides
│   │   │   ├── PageBreakLines
│   │   │   ├── SelectionTool
│   │   │   ├── HierarchyPopup
│   │   │   ├── ContextMenu
│   │   │   └── ZoomControls
│   │   ├── PDFReference (aba PDF)
│   │   │   ├── PDFRenderer (PDF.js)
│   │   │   ├── PDFOverlayLayer
│   │   │   ├── DocSwitcher
│   │   │   └── PageNavigator
│   │   ├── CodeEditor (aba Código)
│   │   │   ├── MonacoEditor
│   │   │   ├── FileTabs (index.html, style.css, base.js)
│   │   │   └── InlineErrorMarkers
│   │   └── SyncView (aba Sincronizar)
│   │       ├── SyncCanvas
│   │       ├── SyncPDF
│   │       └── AnchorMarkers
│   ├── InspectorPanel
│   │   ├── PageInspector (nível 1)
│   │   ├── SectionInspector (nível 2)
│   │   ├── ComponentInspector (nível 3)
│   │   │   ├── TableInspector
│   │   │   ├── ChartInspector
│   │   │   ├── ContainerInspector
│   │   │   └── ImageInspector
│   │   └── ElementInspector (nível 4)
│   │       ├── PositionControls
│   │       ├── SizeControls
│   │       ├── TypographyControls
│   │       ├── FieldTypeSelector
│   │       ├── VisibilityControl
│   │       ├── AnchorSelector
│   │       └── LayerControls
│   ├── MultiDocAnalyzer
│   │   ├── DocumentList
│   │   └── VariationMatrix
│   └── BottomPanel (2 abas)
│       ├── TestDataPanel (aba Dados de Teste)
│       │   ├── DatasetList
│       │   ├── DatasetEditor
│       │   └── SyntheticGenerator
│       └── TestReportPanel (aba Relatório)
├── ConfidencePopover
├── CoveragePopover
└── BibliotecasModal
```

---

*Wireframes gerados por @ux-design-expert (Uma) | Projeto: Migrador Planetexpress*
*v5 — Atualizado 2026-03-15: Canvas HTML + Árvore de Estrutura + Inspetor Hierárquico (4 níveis), alinhado com docs/UI specs (19 documentos)*
*v5.1 — Atualizado 2026-03-16: Tela de progresso separada (Analyzing); Upload de dados XML/JSON (opcional); Paginação real no Canvas (scroll contínuo, lazy rendering); Interação no Canvas (selecionar/mover/redimensionar + seleção hierárquica); Editor de Código multi-arquivo (Monaco + Explorador de Arquivos + abas HTML/CSS/JS + avisos áreas críticas + erros inline); Vista Sincronizada (split Canvas+PDF); Popover de Confiança e Cobertura na toolbar; Remoção dos modais de Exportar e Preview; Modelo mental corrigido (stores Pinia, não template.json)*
*v5.2 — Atualizado 2026-03-16: Sistema de Cobertura completo — thresholds (≥95%/80-95%/<80%) no popover; cobertura por Layout Type; atualização em tempo real; cálculo ponderado; cobertura multi-documento; escopo MVP documentado*
*v5.3 — Atualizado 2026-03-16: Área de Testes expandida (Opção B — Painel Inferior) — 2 abas (Dados de Teste, Relatório); Console removido (feedback contextual via badges, overlays, toast e inspetor); gestão de datasets (upload, deletar, desabilitar, selecionar ativo); validação contra XSD; gerador de dados sintéticos (small/medium/large); Auto Test Mode (testar todos); relatório com tabela resumo + matriz cobertura por elemento; datasets incluídos no Export; limite MVP 5 datasets; estado `testing` no ciclo de vida*
*Próximo passo: atualizar PRD e architecture docs para refletir modelo Canvas HTML*
