# Migrador Planetexpress → HTML/Knockout.js
## Product Requirements Document (PRD) — v3.0

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-03-02 | 1.0 | Versão inicial | Morgan + Atlas |
| 2026-03-09 | 1.3–2.2 | Iterações de UI wizard (ver prd-v2.3-archived.md) | Morgan |
| 2026-03-14 | 2.3 | Última versão wizard; XSD obrigatório; arquivada | Morgan |
| 2026-03-16 | 3.0 | **Reescrita completa**: paradigma wizard 5 telas → editor unificado com 5 regiões; alinhado com wireframe v5.3; novos FRs (cobertura, área de testes, sync view, layout types, multi-documento, diff); tela de exportar removida; console removido; upload de dados XML/JSON restaurado como opcional | Morgan |

---

## Goals and Background Context

### Goals

- Eliminar a dependência do planetexpress, ferramenta proprietária com custo de licença elevado e sem suporte moderno
- Automatizar a migração de 21–100 templates de documentos para HTML + Knockout.js
- Gerar templates HTML dinâmicos a partir de entradas obrigatórias (PDFs preenchidos + contrato de campos XSD) com dados opcionais (XML/JSON)
- Reduzir custo operacional com licenciamento de ferramentas de terceiros
- Aumentar flexibilidade técnica e integração com sistemas e pipelines modernos
- Garantir fidelidade visual dos documentos migrados em relação aos originais do planetexpress

### Background Context

A empresa utiliza o **planetexpress** — ferramenta proprietária de geração de documentos com IDE visual (similar ao Word) — para produzir documentos em formato `.pp7`. O custo de licenciamento, a dificuldade de integração com sistemas modernos e a perspectiva de depreciação da ferramenta motivam a migração.

A infraestrutura de destino já existe: um motor interno **PDF Template** que consome HTML + Knockout.js alimentado por JSON. O objetivo deste projeto é criar uma **ferramenta migradora (web app)** que leia PDFs gerados pelo planetexpress, identifique campos dinâmicos via matching com IA, e produza templates HTML/Knockout.js prontos para uso na nova infraestrutura.

---

## Modelo de Navegação

> **Mudança v3.0:** O paradigma wizard de 5 telas separadas (Upload → Campos → Layout → Geração → Exportar) foi substituído por um **editor unificado com 5 regiões**. A Tela de Exportar foi eliminada — exportar é um botão na toolbar do editor. A Tela de Progresso (Analyzing) é uma tela intermediária dedicada entre Upload e Editor.

### Fluxo de Telas

```
HOME → UPLOAD → ANALYZING (progresso) → EDITOR (destino final)
                     ↑ cancelar              │
                     └───────────────────────┘
                                             │
    HOME ← Abrir Projeto (.json) ───────────→ EDITOR
```

| Tela | Função |
|------|--------|
| **Home** | Tela inicial: Novo Template ou Abrir Projeto salvo. Acesso a Bibliotecas. |
| **Upload** | Upload de PDFs (1 obrigatório, 3-5 recomendado) + XSD (obrigatório) + dados XML/JSON (opcional). Nome do template. |
| **Analyzing** | Tela de progresso dedicada. Pipeline 8 blocos / 23 estágios. Sem Canvas parcial. Auto-navega para Editor ao concluir. |
| **Editor** | Interface principal unificada com 5 regiões: toolbar, painel esquerdo (3 abas), centro (4 abas), inspetor hierárquico, painel inferior (2 abas). |

---

## Requirements

### Functional Requirements

#### Entradas

- **FR1:** O sistema deve aceitar upload de **múltiplos arquivos PDF** preenchidos como entrada (mínimo 1 obrigatório, recomendado 3-5); ao iniciar a análise, o pipeline (FR35) processa todos os PDFs enviados: extrai conteúdo de cada um (FR3), clusteriza páginas por similaridade de layout criando Layout Types (FR37), seleciona páginas representativas por cluster, e alimenta o Analisador Multi-Documento (FR40) para detecção de campos opcionais, seções condicionais e variações de layout; com 1 PDF o pipeline funciona sem comparação entre documentos

- **FR2:** O sistema deve aceitar upload de um arquivo XSD como entrada obrigatória junto com os PDFs; a partir do XSD, o sistema extrai nomes de campos, tipos e obrigatoriedade (`minOccurs="0"` = opcional) para construir a árvore de campos; os nomes dos campos do XSD definem os nomes canônicos usados nos `data-bind` do Knockout.js no template gerado; o conjunto mínimo e obrigatório para iniciar a análise é **1 PDF + XSD**

- **FR2a:** O sistema deve aceitar upload **opcional** de um arquivo de dados (XML ou JSON) com dados reais de exemplo; dados reais melhoram a detecção automática de tipos e formatos e servem de dataset inicial na Área de Testes (FR42); aceita 1 arquivo XML ou JSON

- **FR2b:** O sistema deve gerar automaticamente um conjunto de dados de exemplo a partir do XSD, criando valores sintéticos coerentes com os tipos e nomes dos campos; o resultado é utilizado como `exemplo.js` para teste do template e como dataset sintético na Área de Testes

#### Motor de Matching

- **FR3:** O sistema deve extrair texto, posicionamento, fontes, estrutura de tabelas e imagens do PDF _(inalterado)_

- **FR4:** O sistema deve realizar matching automático com IA entre valores encontrados no PDF e campos do XSD, com suporte a correspondência semântica (Vision AI + pgvector embeddings), normalização de formatos (moeda BR, datas, CEP, telefone) e reconhecimento de texto contextual ao redor do valor _(inalterado)_

- **FR5:** Quando o matching retornar múltiplos candidatos para um mesmo trecho do PDF, o sistema deve apresentar a lista de opções ao operador para escolha manual _(inalterado)_

- **FR6:** Para campos formatados (ex: `"R$ 1.234,56"` → `1234.56`, `"15 de Janeiro de 2025"` → `"15/01/2025"`), o sistema deve tentar desnormalizar automaticamente; se incerto, deve apresentar ao operador opções de tipo de formatação e gerar a função correspondente no `base.js` _(inalterado)_

#### Tela de Progresso (Analyzing)

- **FR35:** Ao clicar "Iniciar Análise" no Upload, o sistema deve navegar para uma **tela de progresso dedicada** que exibe o pipeline de análise em 8 blocos lógicos / 23 estágios com indicadores visuais (✅ concluído, 🔄 em progresso, ○ pendente), barra de progresso geral com percentual, resumo parcial atualizado em tempo real (PDFs processados, páginas, layouts detectados), tempo estimado e botão Cancelar que interrompe o pipeline e retorna ao Upload; ao finalizar todos os blocos, o sistema navega **automaticamente** para o Editor sem intervenção do operador

  **Pipeline de 8 blocos:**
  1. Aquisição (upload PDFs + XSD, análise de PDFs)
  2. Descoberta de Layout (esqueleto, agrupamento, representativas, impressão digital, registro)
  3. Inteligência (alinhamento, análise multi-exemplo, estabilidade, variantes, normalização)
  4. Tabelas (detecção e estruturação)
  5. Semântica (análise de significado)
  6. Visão (análise visual por IA)
  7. Mapeamento (matching campos XSD ↔ PDF)
  8. Validação (verificação de integridade)

#### Editor Unificado — Estrutura

- **FR36:** O sistema deve apresentar um **editor unificado com 5 regiões** como interface principal de trabalho:
  1. **Barra de ferramentas** (topo): nome do template, indicadores de Confiança e Cobertura (clicáveis com popover), seletor de Layout Type, toggles (Modo Cobertura, Modo Diff, Snap, Auto Fix), botões Salvar e Exportar
  2. **Painel esquerdo** (2 abas permanentes + 1 contextual): Estrutura (árvore hierárquica do documento), Campos (lista de campos do XSD com status de mapeamento); quando a aba Código está ativa no painel central, uma terceira aba **Arquivos** (explorador de arquivos do template) aparece automaticamente no painel esquerdo
  3. **Painel central** (4 abas): Canvas HTML (WYSIWYG live do template), PDF Referência (PDF original via PDF.js), Código (Monaco Editor multi-arquivo), Sincronizar (split view Canvas + PDF)
  4. **Inspetor hierárquico** (direita): painel contextual com 4 níveis (Página, Seção, Componente, Elemento)
  5. **Painel inferior** (2 abas): Dados de Teste e Relatório
  - Adicionalmente, o **Analisador Multi-Documento** aparece como seção entre o painel central e o inferior quando múltiplos PDFs foram enviados

#### Layout Types

- **FR37:** O sistema deve **clusterizar** as páginas de PDFs grandes por similaridade de layout, criando **Layout Types** (ex: Capa, Transações, Resumo); o operador edita um template por Layout Type via seletor na toolbar; ao trocar de Layout Type, a Árvore de Estrutura, o Canvas, a Confiança e a Cobertura atualizam para o layout selecionado; cada Layout Type possui métricas independentes; o seletor é oculto quando apenas 1 Layout Type é detectado

#### Árvore de Estrutura

- **FR38:** O painel esquerdo (aba Estrutura) deve exibir a **hierarquia do documento** como template: `Document > Header > Flow > Footer > elementos`; cada nó exibe ícone de tipo (📄 Document, 📦 Seção, 🔤 Texto, 📋 Tabela, 📊 Gráfico, 🖼 Imagem), nome e binding (ex: `→ {{cliente}}`); elementos opcionais marcados com ⚠; clicar seleciona no Canvas e abre Inspetor; drag & drop reordena; clique direito abre menu contextual (adicionar, agrupar, duplicar, remover, mover entre seções); cada Layout Type tem sua própria árvore

#### Inspetor Hierárquico (4 níveis)

- **FR39:** O painel inspetor (direita) deve adaptar-se ao **nível do nó selecionado** na Árvore de Estrutura:

  | Nível | Nó selecionado | Propriedades |
  |-------|---------------|-------------|
  | 1 — Página | Document (raiz) | Tamanho (A4/Letter/Custom), orientação, margens, alturas header/footer, grid, colunas detectadas |
  | 2 — Seção | Header, Flow, Footer, seções opcionais | Altura, fundo, padding, repetição por página, travar seção, visibilidade (sempre/condicional/escondido) |
  | 3 — Componente | Tabela, Gráfico, Container, Imagem | Data source, colunas/datasets, paginação, dimensões, âncora, manter junto, camada, visibilidade |
  | 4 — Elemento | Campo de texto, rótulo, ícone | Posição X/Y, tamanho, tipografia (fonte, tamanho, peso, cor, entrelinha), espaçamento, tipo de campo, binding, âncora, visibilidade, camada, travar |

  **Propriedade Visibilidade** (todos os níveis): 3 opções — Sempre visível (padrão, sem wrapper), Condicional (expande construtor `SE [campo] [operador] [valor]` com suporte a E/OU, gera `<!-- ko if: expressão -->`), Escondido (elemento omitido do HTML final). Campos detectados como opcionais pela Matriz de Variação já vêm pré-preenchidos como Condicional.

  **Tipos de campo suportados** (nível 4): Texto, Número, Moeda (BRL), Data, CPF, CNPJ, Percentual, Telefone, Personalizado (máscara livre ou função JS). Cada tipo com regras de formato e pré-visualização instantânea (Entrada → Saída).

#### Analisador Multi-Documento

- **FR40:** Quando múltiplos PDFs são enviados, o sistema deve exibir um **Analisador Multi-Documento** com lista de PDFs (base/variação), **Matriz de Variação** (campo × documento → ✔/✖) e detecção automática:
  - ✔ em todos → campo obrigatório
  - ✔ em alguns → campo opcional (gera `<!-- ko if: campo -->`)
  - Campos adjacentes com mesmo padrão → seção opcional (agrupados automaticamente com `<!-- ko if -->`)
  - ✔ em apenas 1 → seção condicional
  - Linhas variáveis em tabelas → layout dinâmico (foreach com contagem variável)
  - Seção oculta quando apenas 1 PDF foi enviado

#### Modo Diff

- **FR41:** O sistema deve oferecer **Modo Diff** (toggle na toolbar) que compara páginas representativas do mesmo Layout Type entre documentos lado a lado com destaque automático: 🟩 verde (igual), 🟨 amarelo (diferente posição), 🟥 vermelho (novo/ausente); inclui resumo de inferências (campos opcionais, seções condicionais, variações de layout); operador pode confirmar/rejeitar inferências

#### Área de Testes

- **FR42:** O painel inferior deve oferecer uma **Área de Testes** com 2 abas:

  **Aba "Dados de Teste":**
  - Lista de datasets (um ativo por vez); aceita upload de XML ou JSON; validação automática contra XSD
  - Indicadores de status: ✓ validado, ⚠ aviso (campos opcionais ausentes), ✕ inválido
  - **Gerador de dados sintéticos** a partir do XSD: `synthetic_small` (1 linha), `synthetic_medium` (10 linhas), `synthetic_large` (100+ linhas) — foco em variação do tamanho de loops
  - Resumo do dataset selecionado: campos, loops, tamanho, status
  - "Editar Dataset..." abre modal com Monaco Editor
  - "Aplicar no Canvas" renderiza o template com o dataset ativo em tempo real
  - "Testar Todos" executa todos os datasets em sequência; resultado na aba Relatório
  - **Limite MVP:** máximo 5 datasets por template
  - Datasets incluídos opcionalmente no Export (pasta `test_data/`)

  **Aba "Relatório":**
  - Tabela resumo: dataset × páginas × cobertura × status (✓ OK, ⚠ Aviso, ❌ Erro)
  - Matriz de cobertura por elemento: quais elementos do template aparecem em cada dataset

#### Canvas HTML

- **FR7:** _(reescrito)_ O painel central (aba Canvas HTML) deve renderizar o **HTML real do template** dentro de um iframe isolado como pré-visualização WYSIWYG live; o Canvas **não é o PDF original** — é o resultado renderizado do template com dados de exemplo; suporta scroll contínuo vertical com páginas empilhadas (gap e sombra entre elas), paginação dinâmica calculada pelo espaço disponível (altura da página − header − footer), linhas de quebra de página visíveis, lazy rendering (máx 5 páginas visíveis, demais sob demanda), zoom (50-125%), guias visuais (margens, limites Header/Flow/Footer, colunas, snap lines)

  **Interação no Canvas:**
  - Clicar seleciona elemento (destaca na Árvore + abre Inspetor)
  - Arrastar move elemento (atualiza posição no store)
  - Redimensionar via handles nas bordas
  - Seleção hierárquica: quando elemento aninhado, popup para escolher nível (Texto > Célula > Linha > Tabela)
  - Canvas **não** permite criar elementos desenhando — novos elementos são adicionados via Árvore de Estrutura ou Bibliotecas

- **FR8:** O operador deve poder mapear manualmente campos não reconhecidos automaticamente associando trechos do PDF a campos da árvore de campos na UI; a aba Campos no painel esquerdo lista todos os campos do XSD por tipo com status (🟩 mapeado, 🟥 não mapeado, 🟨 não confirmado); arrastar campo da lista para a Árvore de Estrutura cria binding _(expandido)_

#### Condicionais

- **FR9:** O operador deve poder marcar blocos de conteúdo como condicionais via propriedade Visibilidade no Inspetor (nível 2, 3 ou 4), com construtor visual `SE [campo] [operador] [valor]` suportando condições compostas (E/OU); gera `<!-- ko if: expressão --> ... <!-- /ko -->` no HTML; campos detectados como opcionais pelo Analisador Multi-Documento já vêm pré-configurados como condicionais _(expandido)_

#### Salvar e Retomar

- **FR10:** O sistema deve permitir salvar e retomar sessões completas via botão 💾 Salvar na toolbar do editor; serializa estado completo (estrutura, bindings, configurações de página, regras) como JSON para download; **não inclui** PDFs originais nem assets binários; restaurável via Home → Abrir Projeto, que navega direto para o Editor _(expandido)_

#### Loops e Tabelas

- **FR11:** O sistema deve classificar todos os elementos do documento como **fixos** (tamanho e posição estáticos) ou **dinâmicos** (podem crescer conforme dados); classificação usa padrões visuais repetidos no PDF e campos declarados como array no XSD; elementos dinâmicos recebem tratamento automático: `<!-- ko foreach -->`, paginação (FR12), replicação header/footer (FR13), reposicionamento (FR15) _(inalterado)_

- **FR12:** _(reescrito)_ O sistema deve detectar conteúdo dinâmico que pode ultrapassar o limite de página e aplicar paginação automática. A paginação opera em **duas camadas complementares**:

  **Camada 1 — Layout Engine (editor, tempo de edição):** calcula a paginação no Canvas em tempo real usando o algoritmo `remainingSpace = bodyHeight - headerHeight - footerHeight`; elementos são posicionados sequencialmente; page break é inserido quando o conteúdo não cabe; tabelas quebram por linhas com cabeçalho repetido (`<thead>` replicado). O Canvas simula a paginação exatamente como o template final será renderizado.

  **Camada 2 — Template gerado (runtime, motor PDF Template):** o `base.js` gerado inclui funções de paginação (`quebrarTabelaEntrePaginas()`, `criarNovaPagina()`) que reproduzem a mesma lógica do Layout Engine em runtime, garantindo que o motor PDF Template renderize o HTML pré-paginado com resultado idêntico ao Canvas do editor.

  O operador configura os parâmetros de paginação (altura máxima, cabeçalho repetido, mínimo de linhas por página) via **Inspetor de Componente** (nível 3 — Tabela).

#### Cabeçalho, Rodapé e Imagens

- **FR13:** O sistema deve detectar automaticamente elementos repetidos entre páginas do PDF como candidatos a cabeçalho/rodapé; no editor, Header e Footer são seções estruturais na Árvore de Estrutura com propriedade "Repetir em cada página" no Inspetor de Seção; o operador confirma ou corrige via Inspetor _(expandido)_

- **FR14:** O sistema deve extrair automaticamente imagens embutidas no PDF para a pasta `assets/`; no Inspetor de Imagem (nível 3), o operador pode substituir, baixar ou remover; dimensões, escala e alinhamento configuráveis _(expandido)_

#### Reposicionamento Dinâmico

- **FR15:** O sistema deve identificar automaticamente elementos fixos posicionados abaixo de conteúdo dinâmico e gerar chamadas `reposicionarElementoFixo()` no `base.js`; o operador confirma ou marca manualmente via Inspetor _(inalterado)_

#### Geração do Output

- **FR16:** O sistema deve gerar `index.html` com `<body data-bind="with: {ChaveRaizJSON}">`, bindings Knockout (`data-bind="text:"`, `data-bind="html:"`) e placeholder `var data = ##TEMPLATE_DATA##;` _(inalterado)_

- **FR17:** O sistema deve gerar `css/style.css` com dimensões de página em polegadas (padrão A4: `8.27in × 11.69in`) e layout fiel ao PDF original _(inalterado)_

- **FR18:** O sistema deve gerar `js/base.js` com funções de inicialização Knockout, formatações de campos calculados, format strings customizados e lógica de paginação dinâmica _(inalterado)_

- **FR19:** O sistema deve gerar `exemplo.js` com a estrutura JSON de dados de exemplo para teste do template _(inalterado)_

- **FR20:** _(reescrito)_ O sistema deve disponibilizar o download do output como arquivo `.zip` via botão **📦 Exportar na toolbar do editor** (sem tela de exportar separada); o ZIP contém: `template/` (index.html, css/style.css, js/base.js, js/exemplo.js, assets/); ao clicar Exportar, se houver datasets na Área de Testes, o sistema exibe checkbox "Incluir datasets de teste" (padrão: desmarcado) — quando marcado, adiciona `test_data/` ao ZIP com os datasets validados; a geração e download ocorrem diretamente

#### Format String Customizado

- **FR21:** O operador deve poder definir format strings customizados combinando múltiplos campos JSON (ex: `"{Logradouro}, {Numero} - {Bairro}"`) para campos que no PDF aparecem como texto concatenado, gerando função computada no `base.js` com autocomplete de campos na UI _(inalterado)_

#### Paginação

- **FR22:** O sistema deve suportar configuração de tamanho de página (A4, Carta, dimensões customizadas) via Inspetor de Página (nível 1); orientação (retrato/paisagem) e margens configuráveis; alturas de Header e Footer reservam espaço fixo; Área de Conteúdo calculada automaticamente _(expandido)_

#### Validação

- **FR23:** O sistema deve executar validação técnica de compatibilidade com o motor PDF Template automaticamente antes do Export, verificando: placeholder de dados (`##TEMPLATE_DATA##`), presença de `ko.applyBindings`, integridade dos `data-bind` em relação ao XSD, referências de assets; se houver erro bloqueante, exibe mensagem e bloqueia export _(inalterado na essência)_

#### Editor de Código

- **FR24:** _(reescrito)_ O painel central (aba Código) deve oferecer **Monaco Editor multi-arquivo** com:
  - Abas de arquivo: `index.html`, `style.css`, `base.js`, `exemplo.js`
  - Explorador de Arquivos no painel esquerdo (aba Arquivos, ativa automaticamente ao entrar na aba Código) mostrando a estrutura do pacote do template
  - Syntax highlighting para HTML/CSS/JS, auto-indentação, formatação, numeração de linhas, busca
  - Avisos em áreas críticas: seções estruturais (header, footer, flow) exibem marcadores `⚠ SEÇÃO ESTRUTURAL` alertando que edições podem afetar paginação
  - Detecção de erros inline: HTML inválido, bindings não existentes no XSD, erros de sintaxe em tempo real
  - **Sincronização bidirecional**: editar no código atualiza a estrutura (stores); editar na estrutura/inspetor regenera o código
  - **Fonte da verdade**: sempre a estrutura (stores Pinia), nunca o HTML; o código é representação editável
  - Seleção bidirecional: clicar numa linha seleciona o nó na Árvore; selecionar na Árvore rola o código
  - Validação ao salvar: rejeita e exibe erro se sintaxe ou estrutura inválidos
  - **Regras MVP:** ✅ editar arquivos existentes | ❌ criar/deletar/renomear arquivos

#### Edição Visual (WYSIWYG)

- **FR25:** O operador deve poder interagir diretamente com elementos no Canvas HTML — clicar para selecionar, arrastar para reposicionar, redimensionar via handles; as alterações são refletidas automaticamente nos stores (Pinia) e consequentemente no código-fonte; seleção hierárquica permite escolher nível quando elementos estão aninhados _(expandido)_

#### Gráficos

- **FR26:** O sistema deve detectar canvas de gráficos no PDF; no editor, gráficos são componentes na Árvore de Estrutura com Inspetor de Gráfico (nível 3) contendo: tipo de gráfico (Barras, Linhas, Pizza, Rosca, Área, Empilhado), vinculação de dados (rótulos + datasets com campo, rótulo, cor), dimensões, estilo (legenda, grade, animação, rótulos dos eixos), pré-visualização no Inspetor; confiança alta (≥60%) → tipo pré-selecionado; confiança baixa (<60%) → operador seleciona manualmente; fallback para imagem estática (PNG); múltiplos datasets suportados; gera `<canvas>` + configuração Chart.js no `base.js`; bibliotecas referenciadas em `../Bibliotecas/js/` _(expandido)_

#### Fontes e Estilos Customizados

- **FR27:** Ao detectar fontes não-padrão no PDF, o sistema executa cascata: (1) verifica catálogo local (`../Bibliotecas/`); (2) usa IA para identificar e buscar em repositórios públicos; (3) oferece upload manual; o Inspetor de Elemento exibe fonte detectada com fallback e botão upload quando não encontrada _(inalterado)_

- **FR27a:** O sistema deve oferecer gestão do catálogo de Bibliotecas acessível **apenas pela Home**, com três abas (Fontes, CSS, JS); cada aba exibe lista de arquivos com nome, tamanho e botão remover; botão contextual para adicionar com filtro de extensão _(inalterado)_

#### Sync View

- **FR28:** _(novo)_ O painel central (aba Sincronizar) deve oferecer **split view** com Canvas (template gerado) à esquerda e PDF (documento original) à direita; scroll sincronizado; seleção sincronizada (clicar no Canvas destaca bounding box correspondente no PDF); âncoras de layout como marcadores conectando visualmente estrutura ao original; integra com Modo Cobertura; usa página representativa do Layout Type ativo; zoom independente por painel

#### PDF Referência

- **FR43:** _(novo)_ O painel central (aba PDF Referência) deve renderizar o **PDF original** da página representativa do Layout Type ativo via PDF.js; inclui seletor de documento (dropdown com todos os PDFs enviados), navegação entre páginas, indicador de cluster ("Página representativa de N páginas"); quando o Modo Cobertura está ativo, exibe overlays: 🟦 azul (bloco de texto detectado), 🟩 verde (campo detectado e mapeado), 🟥 vermelho (campo detectado mas não mapeado), 🟨 amarelo (detectado pela IA mas não confirmado), 🟪 roxo (tabela detectada), 📊 laranja (gráfico detectado); zoom independente do Canvas

#### Sistema de Cobertura

- **FR29:** _(novo)_ O sistema deve calcular e exibir **percentual de cobertura** (elementos mapeados vs detectados) na toolbar do editor, clicável para popover com breakdown por tipo:
  - Campos mapeados: N de M
  - Tabelas mapeadas: N de M
  - Imagens mapeadas: N de M
  - Gráficos mapeados: N de M
  - **Thresholds:** ≥95% completo (✅), 80-95% revisão recomendada (⚠️), <80% análise incompleta (🔴)
  - **Modo Cobertura** (toggle na toolbar): no Canvas HTML destaca elementos com binding (🟩 verde), sem binding (🟥 vermelho), não confirmados (🟨 amarelo), tabelas (🟪 roxo), seções opcionais (🟧 laranja tracejado), gráficos (📊 laranja sólido); no PDF Referência destaca detecções da IA com overlay correspondente
  - Cobertura é **por Layout Type** — atualiza ao trocar layout
  - Cobertura **atualiza em tempo real** conforme operador mapeia/desmapeia
  - Cálculo **ponderado** por tipo de elemento
  - **Escopo MVP:** ✔ percentual + popover + modo cobertura + por Layout Type | ✖ por zona, histórico, analytics

#### Tematização Condicional

- **FR30:** O operador deve poder definir regras de aparência condicional vinculadas a campos do JSON — o sistema gera no `base.js` as funções correspondentes; a propriedade Visibilidade no Inspetor cobre o caso condicional (mostrar/ocultar); para variações de estilo (cor, imagem, logo), configurável via Inspetor _(inalterado)_

#### Código de Barras

- **FR31:** O sistema deve detectar elementos de código de barras no PDF e oferecer binding correspondente via JsBarcode CDN; configurável no Inspetor _(inalterado)_

#### SVG Inline

- **FR32:** O sistema deve detectar imagens vetoriais (SVG) no PDF e oferecer incorporação como SVG inline no `index.html` _(inalterado)_

#### Confiança Expandida

- **FR33:** _(expandido)_ O sistema deve calcular e exibir **pontuação de confiança** na toolbar do editor, clicável para popover com breakdown de **5 fatores**:
  - Estabilidade de Layout (%)
  - Detecção de Âncoras (%)
  - Qualidade do Grid (%)
  - Variabilidade de Campos (%)
  - Concordância da Visão (%)
  - **Thresholds:** ≥95% aprovado (✅), 80-95% revisão recomendada (⚠️), <80% revisão humana necessária (🔴)
  - Confiança é **por Layout Type**

#### Auto-correção por IA

- **FR34:** O operador pode acionar "🔧 Auto Fix" na toolbar para que a IA tente corrigir divergências; ajustes apresentados individualmente (aceitar/rejeitar); após aplicação, confiança e cobertura recalculam automaticamente _(expandido — botão agora na toolbar)_

---

### Conceitos Alterados (v2.3 → v3.0)

| Conceito | v2.3 | v3.0 |
|----------|------|------|
| **Navegação** | Wizard 5 telas | Editor unificado com 5 regiões |
| **Exportar** | Tela 5 dedicada | Botão na toolbar → ZIP direto |
| **Preview** | PDF esquerda, HTML direita (layout fixo) | 4 abas centrais: Canvas, PDF, Código, Sincronizar |
| **Console** | Painel dedicado (implícito) | Removido — feedback contextual via badges na Árvore, overlays no Canvas, avisos inline no Inspetor, toast temporários |
| **Upload dados** | Removido na v2.3 | Restaurado como **opcional** (terceira dropzone) |
| **Fonte de verdade** | template.json | **Stores Pinia** — template.json é apenas para Save/Export |
| **Paginação** | base.js no client | **Layout Engine no editor** calcula; PDF engine só renderiza HTML pré-paginado; Canvas simula paginação = mesmo engine do export |
| **Layout Types** | Não existia | PDFs clusterizados por similaridade; template por Layout Type |
| **Árvore de Estrutura** | Não existia | Painel esquerdo com hierarquia Document > Header > Flow > Footer |
| **Inspetor** | Não existia | 4 níveis hierárquicos com propriedades contextuais |

---

### Non-Functional Requirements

- **NFR1:** A ferramenta deve ser hospedável em servidor interno ou cloud privado, acessível via browser sem instalação para o operador; execução puramente local é suportada mas não obrigatória _(inalterado)_

- **NFR2:** A interface web deve funcionar no browser sem instalações complexas para o operador _(inalterado)_

- **NFR3:** O motor de matching com IA deve atingir precisão mínima de 80% em documentos com XSD bem estruturado _(inalterado)_

- **NFR4:** O sistema deve processar um PDF de até 50 páginas em menos de 60 segundos _(inalterado)_

- **NFR5:** O HTML gerado deve reproduzir visualmente o layout original com fidelidade suficiente para aprovação operacional no Canvas HTML e na aba Sincronizar _(ajustado)_

- **NFR6:** O sistema deve suportar caminhos aninhados no XSD/JSON (ex: `cliente.endereço.cidade`) nos bindings gerados _(inalterado)_

- **NFR7:** O arquivo `.zip` de output deve ser autocontido — abrindo `index.html` localmente com os dados de `exemplo.js` deve renderizar o documento corretamente no browser _(inalterado)_

---

## User Interface Design Goals

### Overall UX Vision

Editor unificado de uso interno — interface limpa, orientada a tarefa. Tela Home com acesso a novo template ou projeto salvo. Tela Upload para inputs. Tela de Progresso para pipeline. Editor como destino final com 5 regiões de trabalho simultâneo.

### Key Interaction Paradigms

- **Editor unificado** — 5 regiões sempre acessíveis, sem navegação entre telas durante edição
- **Canvas WYSIWYG live** — o que o operador vê é exatamente o que o template final produz
- **Árvore de Estrutura como superfície principal** — hierarquia editável do documento
- **Inspetor hierárquico contextual** — propriedades mudam conforme nível selecionado
- **Feedback visual direto** — badges, overlays, inline warnings (sem console dedicado)
- **Modo Cobertura/Diff** — toggles para análise visual sem sair do editor

### Core Screens

| # | Tela | Descrição |
|---|------|-----------|
| 0 | **Home** | Cards: Novo Template + Abrir Projeto; botão Bibliotecas |
| 1 | **Upload** | Dropzones: PDFs (múltiplos) + XSD + Dados (opcional); Nome do template; botão Iniciar Análise |
| — | **Analyzing** | Tela de progresso: 8 blocos / 23 estágios; auto-navega para Editor |
| 2 | **Editor** | 5 regiões: toolbar, painel esquerdo (3 abas), centro (4 abas), inspetor (4 níveis), inferior (2 abas) + Analisador Multi-Documento |
| — | **Bibliotecas** | Modal global: componentes HTML/Knockout reutilizáveis organizados por categoria |

### Accessibility

Nenhuma (uso interno, operadores técnicos)

### Branding

Nenhuma — interface utilitária sem identidade visual específica

### Target Device and Platforms

Web app — desktop apenas, Chrome/Edge modernos; acessível via URL de servidor interno ou cloud privado

---

## Technical Assumptions

### Repository Structure

Monorepo — projeto único com `/backend` e `/frontend` separados por pasta

### Service Architecture

Aplicação web com dois componentes deployados em servidor (interno ou cloud):
- **Backend** (Python + FastAPI): parsing de PDF via PyMuPDF, motor de matching com IA via OpenRouter (multi-provider), geração de HTML/CSS/JS, geração de ZIP
- **Frontend** (Vue 3 + TypeScript + Pinia): interface de editor, Canvas HTML (iframe), PDF.js, Monaco Editor, export; servido como build estático pelo próprio backend

### Testing Requirements

Unit + Integration — foco em:
- Motor de matching (precisão de identificação de campos)
- Gerador de output HTML/CSS/JS (fidelidade estrutural)
- Normalização de formatos (datas, moedas, CEP)
- Área de Testes (validação de datasets contra XSD)

### Additional Technical Assumptions

- Knockout.js `3.4.2` é a versão alvo
- `knockout.mapping.js` deve ser compatível com o output gerado
- Placeholder `##TEMPLATE_DATA##` deve ser preservado exatamente no HTML gerado
- `../Bibliotecas/js/` é o caminho relativo compartilhado das libs Knockout (fora da pasta do template)
- `../Bibliotecas/css/` é o caminho relativo compartilhado das bibliotecas CSS
- Bibliotecas JS compartilhadas: `Chart.min.js`, `chartjs-plugin-datalabels.min.js`, `knockout-3.4.2.js`, `knockout.mapping.js`
- CDNs externas permitidas: JsBarcode via `https://cdn.jsdelivr.net/jsbarcode/`
- Nomenclatura de pasta de fontes: `fonts/` (padrão); `fontes/` variação legada aceita
- IA para matching: OpenRouter (multi-provider) — definido pela arquitetura v5.0
- Dimensão padrão de página: A4 (`8.27in × 11.69in`), configurável
- **Fonte de verdade:** Stores Pinia — template.json é serialização para Save/Export
- **Paginação:** Layout Engine no editor calcula; PDF engine renderiza HTML pré-paginado
- **Limitações conhecidas do MVP:**
  - Loops aninhados e tabelas com `colspan`/`rowspan` não suportados — requerem ajuste manual
  - Editor de código: editar arquivos existentes apenas (sem criar/deletar/renomear)
  - Área de Testes: máximo 5 datasets por template
  - Cobertura: sem análise por zona, histórico ou analytics
  - Cobertura: sem Coverage Diff visual no Canvas por dataset (futuro)

---

## Epic List

| # | Epic | Goal |
|---|------|------|
| 1 | Foundation & Pipeline Básico | Infraestrutura, upload multi-PDF, pipeline de análise, matching básico, geração de output |
| 2 | Editor Unificado & Matching Inteligente | Editor 5 regiões, Canvas WYSIWYG, Árvore de Estrutura, Inspetor hierárquico, matching IA, Layout Types |
| 3 | Documentos Avançados — Loops, Paginação, Gráficos | Foreach, quebra de página, header/footer multi-página, gráficos Chart.js, reposicionamento dinâmico |
| 4 | Cobertura, Testes & Análise Multi-Documento | Sistema de cobertura, área de testes, analisador multi-documento, Modo Diff, Sync View, confiança expandida |

> **Nota:** Os epics serão detalhados em stories separadas pelo @sm (River). A estrutura acima é o guia de alto nível para planejamento.

---

## Wireframe Reference

Wireframe detalhado: `docs/wireframes/wireframes-mid-fi.md` (v5.3)

O wireframe v5.3 é a **fonte de verdade para a UI** e contém:
- Wireframes ASCII de todas as telas e estados
- Anotações detalhadas de cada região/componente
- Inventário completo de componentes (átomos, moléculas, organismos, templates)
- Árvore de componentes para implementação
- Estados do editor (ciclo de vida)
- Diagrama de fluxo

---

## Checklist Results

> _(A ser preenchido após execução do pm-checklist)_

---

## Next Steps

### Story Creation

> @sm — Com base neste PRD v3.0 e no wireframe v5.3, criar stories para os 4 epics definidos. O paradigma mudou de wizard para editor unificado — stories devem refletir a nova estrutura de 5 regiões.

### Architecture Alignment

> @architect — Verificar alinhamento do PRD v3.0 com a arquitetura v5.0. Pontos de atenção: Layout Engine para paginação no editor, Pinia como fonte de verdade, pipeline de 23 estágios, OpenRouter como provider IA.
