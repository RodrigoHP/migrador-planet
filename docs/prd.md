# Migrador Planetexpress → HTML/Knockout.js
## Product Requirements Document (PRD)

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-03-02 | 1.0 | Versão inicial | Morgan + Atlas |
| 2026-03-09 | 1.3 | Tela 1: mínimo PDF+(XSD ou dados); dados aceita .xml/.json; FR2c validação cruzada automática; Story 1.3 atualizada | Morgan (handoff @ux-design-expert) |
| 2026-03-09 | 1.4 | Wizard renomeado: Campos+Layout; Tela 3 novo paradigma (dois painéis, decisões pré-geração); FR26 gráficos em 3 etapas; Tela 2 Elementos Especiais | Morgan (handoff @ux-design-expert) |
| 2026-03-09 | 1.5 | Tela 3: botão [↩ Desfazer ajustes] + aviso modal ao navegar de volta para Tela 2 | Morgan (handoff @ux-design-expert) |
| 2026-03-09 | 1.6 | Tela 4 renomeada Geração; wizard final definido; fluxo de navegação Tela 4↔3; painel direito intercambiável (HTML/Monaco/Visual/Chart.js); FR26 configuração Chart.js detalhada | Morgan (handoff @ux-design-expert) |
| 2026-03-09 | 1.7 | Tela 0 Home adicionada; [💾 Salvar projeto] global no header; FR10 substituído por mecanismo de projeto .json; botões de mapeamento da Tela 2 removidos; Tela 5 atualizada com Novo template | Morgan (handoff @ux-design-expert) |
| 2026-03-09 | 1.8 | [📚 Bibliotecas] removido do header do wizard; acessível apenas na Tela 0 como pré-configuração antes de iniciar template; Tela 6 deixa de ser modal global e passa a ser configuração prévia | Morgan (handoff @ux-design-expert) |
| 2026-03-09 | 1.9 | FR27a atualizado: Tela 6 com três abas (Fontes/CSS/JS), file picker contextual por aba, acesso exclusivo pela Tela 0; wireframes de todas as telas finalizados | Morgan (handoff @ux-design-expert) |
| 2026-03-09 | 2.0 | Tela 2: botão [◀ Voltar] adicionado ao rodapé com aviso de descarte do mapeamento ao retornar à Tela 1 | Morgan (handoff @ux-design-expert) |
| 2026-03-09 | 2.1 | Tela 2: botão [↩ Restaurar mapeamento] adicionado ao rodapé — restaura estado original da IA sem reprocessar, com aviso de descarte dos ajustes manuais | Morgan (handoff @ux-design-expert) |
| 2026-03-09 | 2.2 | NFR1 atualizado: ferramenta pode ser hospedada em servidor (interno ou cloud) e acessada via browser — execução local obrigatória removida; alinhado com decisão de arquitetura do @architect | Morgan (handoff @architect) |

---

## Goals and Background Context

### Goals

- Eliminar a dependência do planetexpress, ferramenta proprietária com custo de licença elevado e sem suporte moderno
- Automatizar a migração de 21–100 templates de documentos para HTML + Knockout.js
- Gerar templates HTML dinâmicos a partir de 2 entradas: PDF preenchido + contrato de campos (XSD e/ou arquivo de dados)
- Reduzir custo operacional com licenciamento de ferramentas de terceiros
- Aumentar flexibilidade técnica e integração com sistemas e pipelines modernos
- Garantir fidelidade visual dos documentos migrados em relação aos originais do planetexpress

### Background Context

A empresa utiliza o **planetexpress** — ferramenta proprietária de geração de documentos com IDE visual (similar ao Word) — para produzir documentos em formato `.pp7`. O custo de licenciamento, a dificuldade de integração com sistemas modernos e a perspectiva de depreciação da ferramenta motivam a migração.

A infraestrutura de destino já existe: um motor interno **PDF Template** que consome HTML + Knockout.js alimentado por JSON. O objetivo deste projeto é criar uma **ferramenta migradora local (web app)** que leia PDFs gerados pelo planetexpress, identifique campos dinâmicos via matching com JSON, e produza templates HTML/Knockout.js prontos para uso na nova infraestrutura.

---

## Requirements

### Functional Requirements

**Entradas**
- **FR1:** O sistema deve aceitar upload de um arquivo PDF preenchido como entrada obrigatória
- **FR2:** O sistema deve aceitar upload de um arquivo de dados como contrato de campos; o arquivo pode estar no formato JSON (`.json`) ou XML (`.xml`) — o sistema detecta o formato automaticamente e extrai os campos e valores para uso no matching; o conjunto mínimo para iniciar a análise é **PDF + arquivo de dados** ou **PDF + XSD** — qualquer uma das combinações é suficiente
- **FR2a:** O sistema deve aceitar upload de um arquivo XSD como alternativa ou complemento ao arquivo de dados; a partir do XSD, o sistema extrai nomes de campos, tipos e obrigatoriedade (`minOccurs="0"` = opcional) para construir a árvore de campos; quando apenas o XSD for fornecido (sem dados), o sistema exibe dica informativa sugerindo envio de dados de exemplo para melhorar a identificação de formatos na etapa seguinte
- **FR2b:** Quando o operador fornecer apenas um XSD (sem arquivo de dados), o sistema deve oferecer a opção de gerar automaticamente um conjunto de dados de exemplo a partir do schema, criando valores sintéticos coerentes com os tipos e nomes dos campos; o resultado é utilizado como `exemplo.js` sem necessidade de um arquivo de dados real
- **FR2c:** Quando o operador fornecer XSD **e** arquivo de dados simultaneamente (em qualquer ordem de upload), o sistema deve executar automaticamente validação cruzada entre os dois assim que ambos estiverem presentes: verificar campos declarados no XSD vs campos presentes nos dados, identificar divergências (campos presentes em um e ausentes no outro) e exibir o resultado na Tela de Upload antes de prosseguir; a validação é não-bloqueante — o operador pode ignorar as divergências e avançar; as divergências detectadas antecipam os campos de baixa confiança (🟡) que aparecerão na Tela de Identificação de Campos

**Motor de Matching**
- **FR3:** O sistema deve extrair texto, posicionamento, fontes, estrutura de tabelas e imagens do PDF
- **FR4:** O sistema deve realizar matching automático com IA entre valores encontrados no PDF e campos do JSON, com suporte a correspondência semântica, normalização de formatos (moeda BR, datas, CEP, telefone) e reconhecimento de texto contextual ao redor do valor
- **FR5:** Quando o matching retornar múltiplos candidatos para um mesmo trecho do PDF, o sistema deve apresentar a lista de opções ao operador para escolha manual
- **FR6:** Para campos formatados (ex: `"R$ 1.234,56"` → `1234.56`, `"15 de Janeiro de 2025"` → `"15/01/2025"`), o sistema deve tentar desnormalizar automaticamente; se incerto, deve apresentar ao operador opções de tipo de formatação e gerar a função correspondente no `base.js`

**UI de Mapeamento Manual**
- **FR7:** O sistema deve apresentar interface web local com preview side-by-side: PDF renderizado à esquerda e HTML gerado à direita
- **FR8:** O operador deve poder mapear manualmente campos não reconhecidos automaticamente associando trechos do PDF a campos da árvore JSON na UI
- **FR9:** O operador deve poder marcar blocos de conteúdo como condicionais na UI, informando o campo e a condição, gerando `<!-- ko if: campo --> ... <!-- /ko -->` no HTML
- **FR10:** O sistema deve permitir salvar e retomar sessões completas via arquivo de projeto `.json`; o botão [💾 Salvar projeto] está disponível globalmente no header em todas as telas do wizard e exporta o estado completo da sessão (mapeamento de campos, decisões de layout, configurações Chart.js); o projeto salvo pode ser reaberto na Tela 0 (Home) via "📂 Abrir Projeto", restaurando o estado completo e navegando direto para a etapa onde foi salvo

**Loops e Tabelas**
- **FR11:** O sistema deve classificar todos os elementos do documento como **fixos** (tamanho e posição estáticos, independente dos dados) ou **dinâmicos** (podem crescer conforme o volume de dados informados); a classificação usa duas fontes: padrões visuais repetidos no PDF e, quando disponível, campos declarados como array no XSD/schema; elementos dinâmicos recebem tratamento automático pelo sistema — geração de `<!-- ko foreach -->`, lógica de paginação (FR12), replicação de cabeçalho/rodapé (FR13) e reposicionamento de elementos fixos abaixo deles (FR15) — sem necessidade de configuração manual para cada caso
- **FR12:** O sistema deve detectar conteúdo dinâmico que pode ultrapassar o limite de altura de página e gerar a lógica de paginação automática correspondente: para seções de conteúdo geral, gera `js/paginacaoAutomatica.js` com overflow detection (scrollHeight) e criação de novas páginas via `criarNovaSheetVazia()`; para tabelas com `foreach`, gera `quebrarTabelaEntrePaginas()` no `base.js` replicando o `<thead>` nas páginas subsequentes; o operador confirma os parâmetros (altura máxima por página, seletores de seção, header e footer de tabela) na UI

**Cabeçalho, Rodapé e Imagens**
- **FR13:** O sistema deve detectar automaticamente elementos repetidos entre páginas do PDF como candidatos a cabeçalho/rodapé de página; o operador confirma ou corrige a marcação — essa etapa é parte integrante do processo de paginação automática (FR12): uma vez confirmados, o cabeçalho e rodapé são inseridos automaticamente em todas as páginas criadas dinamicamente via `criarNovaPagina()` no `base.js`, sem necessidade de intervenção manual adicional
- **FR14:** O sistema deve extrair automaticamente imagens embutidas no PDF para a pasta `img/`; o operador pode substituir ou adicionar imagens complementares na UI

**Reposicionamento Dinâmico**
- **FR15:** O sistema deve identificar automaticamente elementos fixos posicionados abaixo de conteúdo dinâmico e gerar chamadas `reposicionarElementoFixo()` no `base.js`; o operador confirma ou marca manualmente na UI

**Geração do Output**
- **FR16:** O sistema deve gerar `index.html` com `<body data-bind="with: {ChaveRaizJSON}">`, bindings Knockout (`data-bind="text:"`, `data-bind="html:"`) e placeholder `var data = ##TEMPLATE_DATA##;`
- **FR17:** O sistema deve gerar `css/style.css` com dimensões de página em polegadas (padrão A4: `8.27in × 11.69in`) e layout fiel ao PDF original
- **FR18:** O sistema deve gerar `js/base.js` com funções de inicialização Knockout, formatações de campos calculados, format strings customizados e lógica de paginação dinâmica
- **FR19:** O sistema deve gerar `exemplo.js` com a estrutura JSON de dados de exemplo para teste do template
- **FR20:** O sistema deve disponibilizar o download do output como arquivo `.zip` contendo a pasta estruturada completa (`index.html`, `css/`, `img/`, `js/`, `exemplo.js`)

**Format String Customizado**
- **FR21:** O operador deve poder definir format strings customizados combinando múltiplos campos JSON (ex: `"{Logradouro}, {Numero} - {Bairro}"`) para campos que no PDF aparecem como texto concatenado, gerando função computada no `base.js` com autocomplete de campos na UI

**Paginação**
- **FR22:** O sistema deve suportar configuração de tamanho de página (A4, Carta, dimensões customizadas em polegadas)

**Validação**
- **FR23:** O sistema deve executar validação técnica de compatibilidade com o motor PDF Template automaticamente ao clicar "Gerar Output →" na Tela de Geração, verificando silenciosamente: placeholder de dados (`##TEMPLATE_DATA##`), presença de `ko.applyBindings`, integridade dos `data-bind` em relação ao `exemplo.js` e referências de imagens; se a validação passar, o sistema avança para a Tela de Exportar sem interrupção; se houver erro bloqueante, o sistema exibe mensagem de erro contextual na própria Tela de Geração e não avança; a validação não é exposta como relatório ao operador — é um processo interno transparente

**Edição do Output**
- **FR24:** O sistema deve oferecer editor de código embutido (Monaco Editor) integrado à Tela de Geração (etapa 4), no painel direito, para edição manual de `index.html`, `css/style.css` e `js/base.js` gerados antes da geração do output final; deve suportar syntax highlight e alternância entre arquivos via abas; o output só é gerado ao clicar em "Gerar Output →" após eventuais edições
- **FR25:** O sistema deve oferecer edição visual direta no painel de preview — o operador pode clicar em qualquer elemento do HTML renderizado para selecionar, reposicionar (arrastar), redimensionar ou editar o texto; as alterações são refletidas automaticamente no código-fonte dos arquivos gerados

**Gráficos**
- **FR26:** O sistema deve detectar canvas de gráficos no PDF e apresentar cada gráfico ao operador na Tela de Campos (etapa 2) como "Elemento Especial", com decisão binária: (a) **Imagem fixa** — gráfico é exportado como `<img>` estático para `img/`, sem dinamismo; (b) **Dinâmico** — operador seleciona o campo JSON array que alimenta os dados; na Tela de Layout (etapa 3), o sistema confirma o campo vinculado; na Tela de Geração (etapa 4), o operador configura os detalhes do Chart.js (tipo de gráfico, eixos, datasets, cores); o sistema gera `js/graficos.js` com a configuração Chart.js resultante (desabilitando animações e responsividade); as bibliotecas `Chart.min.js` e `chartjs-plugin-datalabels.min.js` são referenciadas a partir de `../Bibliotecas/js/`

**Fontes e Estilos Customizados**
- **FR27:** Ao detectar fontes ou estilos não-padrão no PDF, o sistema executa o seguinte fluxo em cascata: (1) verifica o catálogo local (`../Bibliotecas/`) — se houver match, referencia no `<head>` sem copiar arquivos; (2) se não encontrar no catálogo, usa IA de visão computacional para identificar a fonte a partir do texto renderizado do PDF e busca automaticamente nos repositórios públicos (Google Fonts API, Font Squirrel); se encontrada, apresenta ao operador o resultado com preview de comparação e opção de baixar automaticamente; (3) se não encontrada nos repositórios públicos (ex: fonte proprietária ou corporativa), oferece ao operador a opção de upload manual; em qualquer caso onde o arquivo é obtido (download ou upload), o operador escolhe entre "Salvar no catálogo Bibliotecas" (disponibiliza para templates futuros) ou "Incluir apenas neste template" (empacotado no ZIP)
- **FR27a:** O sistema deve oferecer uma área de gerenciamento do catálogo de Bibliotecas acessível **apenas pela Tela 0 (Home)**, com três abas — **Fontes** (`.ttf/.woff/.woff2`), **CSS** (`.css`) e **JS** (`.js`) — cada uma exibindo lista de arquivos cadastrados com nome, tamanho e botão `[🗑️ Remover]`; o botão `[+ Adicionar Arquivo]` é contextual pela aba ativa e abre file picker com filtro de extensão correspondente; arquivos adicionados ficam disponíveis imediatamente para todos os templates futuros no repositório compartilhado (`../Bibliotecas/`)


**Tematização Condicional**
- **FR30:** O operador deve poder definir regras de aparência condicional vinculadas a campos do JSON — por exemplo, se um campo booleano ou texto assumir determinado valor, o sistema aplica uma variação visual (cor, imagem, logo); o sistema gera no `base.js` as funções correspondentes que aplicam as alterações de estilo em tempo de renderização; a UI deve permitir configurar as regras de forma visual (campo JSON → condição → propriedade visual afetada → valor)

**Código de Barras**
- **FR31:** O sistema deve detectar elementos de código de barras no PDF e oferecer ao operador a opção de gerar o binding correspondente no HTML, referenciando a biblioteca JsBarcode via CDN externa (`https://cdn.jsdelivr.net/jsbarcode/...`); o operador configura o tipo de código (ex: Codabar) e o campo JSON de origem

**SVG Inline**
- **FR32:** O sistema deve detectar imagens vetoriais (SVG) no PDF, especialmente logos e cabeçalhos com gradientes, e oferecer ao operador a opção de incorporá-las como SVG inline no `index.html` (em vez de arquivo externo em `img/`), preservando gradientes e estilos internos

**Score de Fidelidade**
- **FR33:** Na Tela de Geração (etapa 4), o sistema deve calcular e exibir automaticamente um score de fidelidade visual entre o HTML gerado e o PDF original; o score é obtido via avaliação por IA (modelo multimodal ou visão computacional) que compara a renderização do HTML com as páginas do PDF e retorna: (a) percentual geral de fidelidade (ex: `87%`); (b) comentário explicativo sobre as principais divergências (ex: `"Estrutura geral preservada. Fonte e espaçamento da seção de rodapé divergem."`); (c) painel de detalhes acessível sob demanda listando elementos específicos que diferem; o score serve como guia para o operador decidir se edita antes de gerar o output final

**Auto-correção por IA**
- **FR34:** Na Tela de Geração (etapa 4), o operador pode solicitar explicitamente que a IA tente corrigir as divergências identificadas no score de fidelidade (FR33); ao acionar "Melhorar com IA", o sistema envia as divergências detectadas + o HTML/CSS atual para o modelo de IA, que propõe um conjunto de ajustes (posicionamento, espaçamento, fontes, tamanhos); os ajustes são apresentados individualmente ao operador — cada item pode ser aceito, rejeitado ou ajustado manualmente antes de ser aplicado; após aplicação, o score de fidelidade é recalculado automaticamente; este mecanismo é complementar e independente do editor de código (FR24) e do editor visual WYSIWYG (FR25) — o operador pode combinar os três conforme necessário


---

### Non-Functional Requirements

- **NFR1:** A ferramenta deve ser hospedável em servidor interno ou cloud privado, acessível via browser sem instalação para o operador; execução puramente local é suportada mas não obrigatória
- **NFR2:** A interface web deve funcionar no browser sem instalações complexas para o operador
- **NFR3:** O motor de matching com IA deve atingir precisão mínima de 80% em documentos com JSON bem estruturado
- **NFR4:** O sistema deve processar um PDF de até 50 páginas em menos de 60 segundos
- **NFR5:** O HTML gerado deve reproduzir visualmente o layout original com fidelidade suficiente para aprovação operacional no preview side-by-side
- **NFR6:** O sistema deve suportar caminhos aninhados no JSON (ex: `cliente.endereço.cidade`) nos bindings gerados
- **NFR7:** O arquivo `.zip` de output deve ser autocontido — abrindo `index.html` localmente com os dados de `exemplo.js` deve renderizar o documento corretamente no browser

---

## User Interface Design Goals

> _(Esta seção será detalhada pelo @ux-design-expert com base neste PRD)_

### Overall UX Vision
Ferramenta utilitária de uso interno — interface limpa, orientada a tarefa. Tela inicial (Home) com acesso a novo template ou projeto salvo; fluxo wizard de 5 etapas: Upload → Campos → Layout → Geração → Exportar.

### Key Interaction Paradigms
- Fluxo wizard em etapas sequenciais
- Preview side-by-side com interação direta
- Feedback visual imediato do matching (verde / amarelo / vermelho)

### UX Directives (orientações para o @ux-design-expert)
- **Progress bar global** — toda operação de processamento (upload, matching, geração de output, download) deve exibir barra de progresso com indicação da etapa atual e percentual; o operador nunca deve ficar sem feedback visual sobre o andamento de um processo em curso
- **Tela Home** — tela inicial antes do wizard com dois cards: "➕ Novo Template" (inicia wizard do zero) e "📂 Abrir Projeto" (carrega `.json` salvo e retoma da etapa onde parou)
- **Wizard de 5 etapas** — `[1. Upload] [2. Campos] [3. Layout] [4. Geração] [5. Exportar]`; a etapa 3 (Layout) é ignorada automaticamente quando não há itens pendentes de decisão humana
- **[💾 Salvar projeto] global** — disponível no header a partir da **Tela 2** (Campos); ausente na Tela 1 pois não há configuração para salvar nessa etapa; exporta `.json` com estado completo da sessão para retomada via Tela Home
- **[📚 Bibliotecas]** — disponível **apenas na Tela Home** como pré-configuração antes de iniciar um template; gerencia catálogo compartilhado de fontes, CSS e JS; **não aparece no header do wizard** (Telas 1 a 5)
- **Tela de Campos (etapa 2)** — PDF à esquerda + painel de de-para à direita; IA pré-preenche todo o mapeamento; operador revisa e resolve exceções (🟡 ambíguo, 🔴 não encontrado); seção "Elementos Especiais" para elementos visuais como gráficos (decisão: imagem fixa vs dinâmico); rodapé contém [◀ Voltar] (retorna à Tela 1 com aviso de descarte do mapeamento), [↩ Restaurar mapeamento] (restaura todos os campos ao estado original da IA sem reprocessar, com aviso: "Isso descartará todos os ajustes manuais feitos. Deseja continuar?") e [Confirmar ▶]
- **Tela de Layout (etapa 3)** — decisões de nível de documento feitas antes de gerar o HTML: página (tamanho, orientação, margens), fontes a carregar, cabeçalho/rodapé (detecção e repetição entre páginas), comportamento de seções dinâmicas (paginação), imagens/SVG, confirmação de gráficos dinâmicos; dois painéis: esquerdo com visão estrutural do documento, direito com itens configuráveis; tudo resolvido automaticamente com [✏️] disponível para ajuste manual; rodapé contém botão [↩ Desfazer ajustes] que restaura todos os itens ao estado inicial detectado pela IA sem reprocessamento; ao clicar [◀ Voltar] com ajustes feitos, exibir modal de confirmação informando que os ajustes serão perdidos e o layout regenerado ao retornar
- **Tela de Geração (etapa 4)** — comparação visual lado a lado PDF vs HTML + score de fidelidade IA + painel direito intercambiável com 4 estados: (1) HTML padrão com placeholder para gráficos dinâmicos, (2) Monaco Editor substituindo painel direito (FR24), (3) modo edição visual ativado sobre o próprio painel HTML (FR25), (4) configuração Chart.js substituindo painel direito (FR26); PDF permanece sempre visível à esquerda; [◀ Ajustar Layout] sempre exibe aviso antes de navegar — HTML será regenerado e edições perdidas; Tela 3 preserva ajustes ao receber navegação vinda desta tela; sem botão desfazer — [✨ Melhorar com IA] cobre correções e retorno à Tela 3 cobre reset estrutural
- Demais diretrizes a serem detalhadas pelo @ux-design-expert

### Core Screens and Views
0. **Tela Home** — tela inicial com dois cards: "➕ Novo Template" (inicia wizard do zero) e "📂 Abrir Projeto" (carrega `.json` de projeto salvo e retoma na etapa onde foi salvo); [📚 Bibliotecas] acessível **apenas aqui** — pré-configuração de fontes/CSS/JS antes de iniciar um template; não aparece no wizard
1. **Tela de Upload** — três áreas de upload independentes: PDF (obrigatório), XSD (opcional) e arquivo de dados .xml/.json (opcional); mínimo para avançar é PDF + XSD **ou** PDF + dados; quando XSD + dados estão ambos presentes, validação cruzada automática exibe resultado antes do botão "Analisar Documento →"
2. **Tela de Campos** — PDF à esquerda + painel de de-para à direita; IA pré-preenche mapeamento completo; operador revisa campos (todos com [✏️]), resolve exceções (🟡/🔴); seção "Elementos Especiais" para gráficos detectados (decisão: imagem fixa vs dinâmico + campo JSON); rodapé: [◀ Voltar] (retorna à Tela 1 com aviso de descarte), [↩ Restaurar mapeamento] (restaura estado original da IA com aviso de descarte dos ajustes manuais) e [Confirmar ▶]3. **Tela de Layout** — dois painéis: esquerdo com visão estrutural do documento (esqueleto visual), direito com itens configuráveis agrupados por categoria (Página, Cabeçalho, Rodapé, Fontes, Seções Dinâmicas, Imagens/SVG, Gráficos); sistema resolve tudo automaticamente; [✏️] em cada item para ajuste manual; ignorada se não houver pendências; rodapé com [◀ Voltar], [↩ Desfazer ajustes] e [Avançar →]; [↩ Desfazer ajustes] restaura o estado inicial da análise automática sem reprocessamento; [◀ Voltar] com ajustes feitos exibe modal: "Seus ajustes de layout serão perdidos. Ao retornar, o layout será regenerado com base nos novos campos." com opções [Cancelar] e [Voltar mesmo assim]; sem ajustes, navega diretamente sem aviso
4. **Tela de Geração** — comparação visual lado a lado PDF vs HTML + score de fidelidade IA com comentário explicativo; painel direito intercambiável: HTML padrão (gráficos dinâmicos como placeholder com [⚙️ Configurar Chart.js]), Monaco Editor (FR24 — abas index.html/style.css/base.js), modo edição visual WYSIWYG sobre o painel HTML (FR25), painel de configuração Chart.js (FR26 — tipo, eixos, título, cor, legenda); [◀ Ajustar Layout] sempre exibe aviso e navega para Tela 3 preservando ajustes; sem botão desfazer; botão "Gerar Output →" empacota o output
5. **Tela de Exportar** — score de fidelidade final + árvore de arquivos do output; botões: [🔍 Abrir Preview], [◀ Voltar à Geração], [➕ Novo template] (retorna à Tela Home), [⬇️ Baixar ZIP]; [💾 Salvar projeto] disponível no header global
6. **Gestão de Bibliotecas** — modal/tela acessível **apenas pela Tela Home** como pré-configuração; gerencia catálogo compartilhado de fontes, CSS e JS; não disponível durante o wizard

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
- **Backend** (Python + FastAPI): parsing de PDF via PyMuPDF, motor de matching com IA via Anthropic SDK, geração de HTML/CSS/JS, geração de ZIP
- **Frontend** (Vue 3 + TypeScript): interface de mapeamento, preview side-by-side com PDF.js, editor Monaco, export; servido como build estático pelo próprio backend

### Testing Requirements
Unit + Integration — foco em:
- Motor de matching (precisão de identificação de campos)
- Gerador de output HTML/CSS/JS (fidelidade estrutural)
- Normalização de formatos (datas, moedas, CEP)

### Additional Technical Assumptions
- Knockout.js `3.4.2` é a versão alvo
- `knockout.mapping.js` deve ser compatível com o output gerado
- Placeholder `##TEMPLATE_DATA##` deve ser preservado exatamente no HTML gerado
- `../Bibliotecas/js/` é o caminho relativo compartilhado das libs Knockout (fora da pasta do template)
- `../Bibliotecas/css/` é o caminho relativo compartilhado das bibliotecas CSS (`sentico.css`, `sentico-v2.css`)
- Bibliotecas JS compartilhadas identificadas nos templates reais: `Chart.min.js`, `chartjs-plugin-datalabels.min.js` (gráficos), `knockout-3.4.2.js`, `knockout.mapping.js`
- CDNs externas permitidas: JsBarcode via `https://cdn.jsdelivr.net/jsbarcode/`
- Nomenclatura de pasta de fontes: `fonts/` (padrão adotado); `fontes/` é variação legada aceita
- IA para matching: modelo/provedor a definir pelo `@architect`
- Dimensão padrão de página: A4 (`8.27in × 11.69in`), configurável
- **Limitações conhecidas do MVP:** loops aninhados e tabelas com células mescladas (`colspan`/`rowspan`) não são suportados — requerem ajuste manual no `base.js` gerado

---

## Epic List

| # | Epic | Goal |
|---|------|------|
| 1 | Foundation & Pipeline Básico de Migração | Pipeline end-to-end para documentos simples com matching básico e geração completa de output |
| 2 | Matching Inteligente & Workflow Completo do Operador | IA no matching, campos formatados, condicionais, preview side-by-side avançado e edição direta do output (visual + código) |
| 3 | Documentos Avançados — Loops, Paginação e Imagens | Foreach, quebra de página, cabeçalho/rodapé multi-página, reposicionamento dinâmico e validação final |

---

## Epic 1 — Foundation & Pipeline Básico de Migração

**Goal:** Estabelecer a infraestrutura do projeto e entregar um pipeline end-to-end funcional para documentos de N páginas simples (sem loops ou condicionais), permitindo upload de PDF + JSON ou XSD (contrato), geração de dados de exemplo a partir do XSD, matching básico, mapeamento manual, configuração de página e download do template HTML como ZIP.

### Story 1.1 — Project Foundation & Dev Environment

*Como desenvolvedor, quero um projeto monorepo configurado com backend e frontend funcionais, para que a equipe tenha uma base consistente para desenvolvimento.*

**Acceptance Criteria:**
1. Monorepo criado com estrutura `/backend` e `/frontend` separados
2. Backend com servidor local rodando (rota de health-check respondendo)
3. Frontend com página inicial renderizando no browser via `localhost`
4. Scripts de desenvolvimento iniciando ambos simultaneamente
5. `.gitignore`, `README.md` e estrutura de pastas documentados

---

### Story 1.2 — PDF Upload & Extração de Texto Estruturado

*Como operador, quero fazer upload de um PDF preenchido, para que o sistema extraia seu conteúdo textual com posicionamento e estrutura de páginas.*

**Acceptance Criteria:**
1. Endpoint de upload aceita arquivo PDF e retorna confirmação
2. Sistema extrai texto de todas as páginas com coordenadas (x, y), tamanho de fonte e página de origem
3. Sistema identifica agrupamentos visuais (blocos de texto, linhas de tabela) por proximidade de coordenadas
4. Sistema extrai imagens embutidas no PDF e as salva com nomes únicos
5. Resultado da extração retornado como estrutura JSON interna para uso pelo matching engine

---

### Story 1.3 — Upload de Contrato de Campos & Árvore de Campos

*Como operador, quero fazer upload de um arquivo de dados (.json ou .xml) e/ou de um XSD de contrato, para que o sistema construa uma árvore navegável de todos os campos com seus tipos e obrigatoriedade.*

**Acceptance Criteria:**
1. Endpoint de upload aceita arquivo `.json` e retorna confirmação; sistema parseia e constrói lista de todos os campos com caminhos completos (ex: `CartaInabilitado.NomeSolicitante`)
2. Endpoint de upload aceita arquivo `.xml` como alternativa ao JSON; sistema detecta o formato automaticamente e extrai campos e valores equivalentes
3. Suporte a caminhos aninhados de até 5 níveis de profundidade
4. Campos com valor `null` incluídos na árvore e marcados como opcionais
5. Árvore de campos retornada ao frontend para exibição e uso no matching
6. Endpoint de upload aceita arquivo `.xsd` como alternativa ou complemento ao arquivo de dados
7. Sistema parseia o XSD e constrói árvore de campos com nome, tipo (`xs:string`, etc.) e obrigatoriedade (campo marcado como opcional quando `minOccurs="0"`)
8. Quando o input for XSD sem dados, sistema oferece ao operador a opção "Gerar dados de exemplo" — gerando valores sintéticos coerentes com nome e tipo de cada campo para uso como `exemplo.js`
9. Quando XSD + arquivo de dados estiverem ambos presentes (em qualquer ordem de upload), sistema executa validação cruzada automática e retorna lista de divergências (campos em um mas não no outro); resultado exibido na Tela de Upload; operador pode ignorar e avançar

---

### Story 1.4 — Motor de Matching Básico por Valor

*Como sistema, quero comparar automaticamente os textos extraídos do PDF com os valores do JSON, para que o máximo de campos seja identificado sem intervenção manual.*

**Acceptance Criteria:**
1. Matching por igualdade exata entre texto do PDF e valor do JSON (case-insensitive)
2. Matching com normalização básica: remoção de espaços extras, acentuação e pontuação
3. Cada trecho do PDF recebe status: `matched`, `ambiguous` ou `unmatched`
4. Campos `ambiguous` listam todos os candidatos JSON com o caminho completo
5. Resultado retornado com estatísticas (% matched, % ambiguous, % unmatched)

---

### Story 1.5 — UI de Geração e Mapeamento Manual

*Como operador, quero revisar o resultado do matching e mapear manualmente os campos não identificados, para que todos os campos dinâmicos estejam corretamente vinculados antes da geração do template.*

**Acceptance Criteria:**
1. Interface lista todos os campos agrupados por status: `matched` (verde), `ambiguous` (amarelo), `unmatched` (vermelho)
2. Para campos `ambiguous`, operador seleciona candidato JSON em dropdown
3. Para campos `unmatched`, operador digita ou seleciona caminho JSON na árvore
4. Operador pode exportar mapeamento atual como arquivo `.json` de configuração
5. Operador pode importar arquivo `.json` de configuração para restaurar mapeamento anterior
6. Botão "Confirmar Mapeamento" só habilitado quando não há campos `unmatched` sem atribuição

---

### Story 1.6 — Gerador de Output: index.html & style.css

*Como sistema, quero gerar o `index.html` e o `style.css` do template a partir do mapeamento confirmado, para que o documento HTML reproduza o layout e os bindings Knockout corretos.*

**Acceptance Criteria:**
1. `index.html` gerado com `<body data-bind="with: {ChaveRaizJSON}">`
2. Cada campo mapeado gera elemento com `data-bind="text: caminho"` ou `data-bind="html: caminho"`
3. Textos estáticos preservados como conteúdo fixo no HTML
4. `style.css` gerado com `.page { width: 8.27in; height: 11.69in; }` como padrão A4
5. Classes CSS e estrutura de layout refletem o posicionamento extraído do PDF
6. Referências ao Knockout em `../Bibliotecas/js/knockout-3.4.2.js` e `../Bibliotecas/js/knockout.mapping.js` incluídas no `<head>`

---

### Story 1.7 — Gerador de Output: base.js & exemplo.js

*Como sistema, quero gerar o `base.js` e o `exemplo.js` do template, para que o documento HTML inicialize corretamente os bindings Knockout e possua dados de exemplo para teste.*

**Acceptance Criteria:**
1. `base.js` gerado com `inicializarCamposParaBindings()` declarando todos os campos com valor default `''`
2. `base.js` contém `ko.applyBindings(data)` como chamada de inicialização final
3. Placeholder `var data = ##TEMPLATE_DATA##;` incluído no `index.html` antes de `<script src="js/base.js">`
4. `exemplo.js` gerado com a estrutura JSON exata do arquivo de dados enviado pelo operador
5. `base.js` gerado com `ko.bindingHandlers.number` para formatação numérica no padrão BR

---

### Story 1.8 — Configuração de Página, Preview & Download ZIP

*Como operador, quero configurar o tamanho de página, visualizar o template gerado e baixar o output como ZIP, para que eu possa validar e entregar o template migrado.*

**Acceptance Criteria:**
1. Operador pode selecionar tamanho de página: A4 (padrão), Carta ou dimensões customizadas em polegadas
2. Seleção de tamanho atualiza dimensões no `style.css` gerado
3. Botão "Visualizar" abre `index.html` com `exemplo.js` em nova aba do browser
4. Pasta de output gerada com estrutura: `index.html`, `css/style.css`, `js/base.js`, `exemplo.js`, `img/`
5. Imagens extraídas do PDF copiadas para pasta `img/`
6. Botão "Baixar ZIP" gera e faz download do arquivo `.zip` com pasta completa nomeada pelo template

---

## Epic 2 — Matching Inteligente & Workflow Completo do Operador

**Goal:** Evoluir o motor de matching com IA, adicionar suporte a campos formatados com format strings customizados, permitir marcação de blocos condicionais e entregar preview side-by-side completo.

### Story 2.1 — Motor de Matching com IA

*Como sistema, quero usar IA para identificar campos do PDF com base em semântica e contexto, para que o matching vá além da comparação literal e atinja maior precisão em documentos reais.*

**Acceptance Criteria:**
1. Motor envia pares (texto PDF + contexto, árvore JSON) para modelo de IA e recebe sugestões com score de confiança
2. Matching semântico identifica campos mesmo com prefixos fixos (ex: `"Segurado: Sônia"` → `NomeSegurado`)
3. Score retornado por campo: `high` (≥ 0.85), `medium` (0.6–0.84), `low` (< 0.6)
4. Campos com score `low` tratados como `ambiguous` e encaminhados para revisão manual
5. Taxa de matching ≥ 80% em documentos com JSON bem estruturado
6. Fallback para matching básico por valor caso IA esteja indisponível

---

### Story 2.2 — Detecção de Campos Formatados & Geração de Formatadores

*Como sistema, quero detectar campos com formatação especial e gerar as funções correspondentes no `base.js`, para que valores brutos do JSON sejam apresentados corretamente no template.*

**Acceptance Criteria:**
1. Sistema detecta automaticamente: moeda BR, data longa/curta, CEP, telefone/celular
2. Para cada campo formatado, apresenta ao operador: valor no PDF, valor no JSON e tipo inferido para confirmação
3. Operador pode selecionar tipo diferente do inferido em dropdown
4. `base.js` gerado inclui função de formatação específica para cada campo confirmado
5. Campos calculados formatados adicionados ao `data-bind` correspondente no `index.html`
6. Operador pode definir **format string customizado** combinando múltiplos campos JSON (ex: `"{Logradouro}, {Numero} - {Bairro}"`)
7. Format strings com múltiplos campos geram função computada no `base.js` com o `data-bind` correspondente no `index.html`
8. UI de format string oferece autocomplete dos campos disponíveis ao digitar `{`

---

### Story 2.3 — Marcação de Blocos Condicionais na UI

*Como operador, quero marcar blocos de conteúdo como condicionais, para que o template gerado oculte ou exiba seções dinamicamente com base nos dados do JSON.*

**Acceptance Criteria:**
1. Operador pode selecionar qualquer bloco e marcá-lo como condicional na UI
2. Operador informa: campo JSON da condição e tipo (`if` ou `ifnot`)
3. HTML gerado envolve o bloco com `<!-- ko if: campo --> ... <!-- /ko -->` ou `<!-- ko ifnot: campo --> ... <!-- /ko -->`
4. Blocos condicionais destacados visualmente na UI (borda tracejada + ícone)
5. Operador pode remover marcação condicional de bloco já marcado
6. Mapeamento exportado (`.json`) inclui marcações condicionais para reuso

---

### Story 2.4 — Preview Side-by-Side Avançado

*Como operador, quero visualizar o PDF original lado a lado com o HTML gerado, para que eu possa validar a fidelidade visual do template sem sair da ferramenta.*

**Acceptance Criteria:**
1. Painel esquerdo renderiza o PDF original página por página
2. Painel direito renderiza o `index.html` gerado com dados do `exemplo.js` em iframe
3. Ambos os painéis sincronizam a rolagem de página ao navegar
4. Operador pode ajustar zoom independentemente em cada painel
5. Botão "Atualizar Preview" regenera o HTML no painel direito após alterações no mapeamento
6. Preview disponível em qualquer etapa do fluxo após matching inicial concluído

### Story 2.5 — Edição Direta do Output (Visual + Código)

*Como operador, quero editar o template gerado tanto visualmente quanto no código-fonte, para que eu possa fazer ajustes finos sem precisar sair da ferramenta.*

**Acceptance Criteria:**
1. Aba "Editor de Código" disponível no painel direito com Monaco Editor exibindo `index.html`, `style.css` e `base.js` em abas separadas
2. Alterações salvas no editor de código atualizam o preview visual imediatamente (hot reload)
3. No painel de preview, clicar em qualquer elemento o seleciona com borda de seleção destacada
4. Elemento selecionado pode ser reposicionado via drag-and-drop; a alteração de posição é refletida no `style.css` gerado
5. Elemento selecionado exibe handles de redimensionamento; o redimensionamento atualiza as propriedades CSS correspondentes
6. Duplo clique em elemento de texto permite editar o conteúdo ou o `data-bind` diretamente no preview
7. Alterações visuais e de código são sincronizadas bidirecionalmente — editar no código reflete no visual e vice-versa
8. Botão "Resetar para gerado" desfaz todas as edições manuais e restaura o output original do pipeline

---

## Epic 3 — Documentos Avançados — Loops, Paginação e Imagens

**Goal:** Completar o suporte a documentos complexos com foreach, quebra de página, cabeçalho/rodapé multi-página, reposicionamento dinâmico de elementos fixos, extração de imagens e validação de compatibilidade com o motor PDF Template.

> **Nota:** Stories 3.1–3.6 são ativadas conforme necessidade do template — documentos simples podem pular para Story 3.4/3.5.

### Story 3.1 — Detecção de Loops & Geração de Foreach

*Como sistema, quero detectar padrões repetidos no PDF correspondentes a arrays no JSON, para que o template use `<!-- ko foreach -->` para renderizar listas e tabelas dinâmicas.*

**Pré-requisito:** Story 2.3

**Acceptance Criteria:**
1. Sistema identifica grupos de elementos com estrutura visual repetida e os propõe como candidatos a `foreach`
2. Para cada candidato, verifica se existe array correspondente no JSON
3. Operador confirma ou rejeita cada candidato, podendo ajustar o caminho do array JSON
4. HTML gerado envolve o bloco com `<!-- ko foreach: array --> ... <!-- /ko -->`
5. Campos internos gerados com caminhos relativos ao item do array
6. `base.js` gerado inclui `formatarParaArray(data, 'NomeCampo')` para campos que podem vir como singular ou array
7. `exemplo.js` atualizado com array contendo pelo menos 2 itens de exemplo
8. **Limitação conhecida:** loops aninhados não suportados — documentados como ajuste manual

---

### Story 3.2 — Tabelas com Quebra de Página Dinâmica

*Como sistema, quero identificar tabelas dinâmicas que ultrapassam o limite de página e gerar a lógica de quebra no `base.js`, para que documentos com muitas linhas renderizem corretamente em múltiplas páginas.*

**Acceptance Criteria:**
1. Sistema detecta tabelas identificadas como `foreach` como candidatas à quebra de página
2. Operador confirma parâmetros: seletor tabela, header, linha, footer (opcional)
3. `base.js` gerado inclui `quebrarTabelaEntrePaginas()` com os parâmetros confirmados
4. `alturaMaximaGlobal` calculado a partir das dimensões de página configuradas
5. Chamada adicionada em `iniciarRenderizacaoSequencialSincrono()` do `base.js`
6. Preview valida quebra com array de exemplo com linhas suficientes para forçar múltiplas páginas
7. **Limitação conhecida:** tabelas com `colspan`/`rowspan` não suportadas — documentadas como ajuste manual

---

### Story 3.3 — Cabeçalho e Rodapé Multi-página

*Como sistema, quero detectar elementos repetidos em todas as páginas do PDF e replicá-los nas páginas criadas dinamicamente, para que documentos multi-página mantenham identidade visual completa.*

**Acceptance Criteria:**
1. Sistema propõe como candidatos elementos presentes em pelo menos 2 páginas com posição/conteúdo similares
2. Operador confirma ou rejeita, classificando como `cabeçalho` ou `rodapé`
3. Elementos confirmados incorporados na função `criarNovaPagina()` do `base.js`
4. Imagens de fundo repetidas referenciadas em `criarNovaPagina()` via `./img/`
5. `index.html` inclui cabeçalho/rodapé apenas na primeira página — páginas subsequentes herdam via JS
6. Preview valida presença do cabeçalho/rodapé nas páginas criadas dinamicamente

---

### Story 3.4 — Extração de Imagens & Gestão de Assets

*Como operador, quero que as imagens do PDF sejam extraídas para `img/`, com possibilidade de substituir ou adicionar imagens manualmente, para que o template referencie todos os assets corretamente.*

**Acceptance Criteria:**
1. UI lista todas as imagens extraídas com preview em miniatura e nome do arquivo
2. Operador pode substituir qualquer imagem extraída por versão de maior qualidade
3. Operador pode adicionar imagens não presentes no PDF via upload
4. Referências no `index.html` e `base.js` usam caminhos relativos `./img/nome-arquivo`
5. ZIP final inclui todos os arquivos da pasta `img/`

---

### Story 3.5 — Validação de Compatibilidade com Motor PDF Template

*Como operador, quero validar que o template gerado é compatível com o motor PDF Template existente, para que a migração seja concluída com confiança.*

**Acceptance Criteria:**
1. Sistema verifica presença de `var data = ##TEMPLATE_DATA##;` no `index.html`
2. Sistema verifica que `ko.applyBindings(data)` está no `base.js`
3. Sistema verifica que todos os `data-bind` referenciam campos existentes no `exemplo.js`
4. Sistema verifica que caminhos de imagens em `./img/` existem no output
5. Relatório exibido antes do download: OK em verde, alertas em amarelo, erros em vermelho
6. Download ZIP só habilitado sem erros bloqueantes

---

### Story 3.6 — Reposicionamento Dinâmico de Elementos Fixos

*Como sistema, quero identificar automaticamente elementos fixos abaixo de conteúdo dinâmico e gerar a lógica de reposicionamento no `base.js`, para que blocos como assinatura e rodapé apareçam sempre após o conteúdo variável.*

**Acceptance Criteria:**
1. Após identificação de elementos dinâmicos, sistema marca automaticamente elementos fixos com posição Y abaixo de um dinâmico como candidatos a reposicionamento
2. Operador confirma ou rejeita cada candidato; pode marcar manualmente qualquer bloco não detectado
3. Operador pode desmarcar elementos detectados automaticamente
4. `base.js` gerado inclui `reposicionarElementoFixo('.seletor')` para cada elemento confirmado em `iniciarRenderizacaoSequencialSincrono()`
5. Ordem das chamadas respeita a sequência vertical dos elementos no documento (de cima para baixo)
6. Preview com array de tamanhos variados valida que elementos fixos reposicionam corretamente

---

## Checklist Results

> _(A ser preenchido após execução do pm-checklist)_

---

## Next Steps

### UX Expert Prompt

> @ux-design-expert — Com base neste PRD do **Migrador Planetexpress → HTML/Knockout.js**, detalhe o design da interface web local da ferramenta. Foco nas 4 telas principais (Upload, Matching/Geração, Configuração, Export), especialmente na UI de mapeamento manual side-by-side (PDF renderizado à esquerda + árvore JSON + painel de campos). A ferramenta é de uso interno por operadores técnicos — priorize eficiência e clareza sobre estética.

### Architect Prompt

> @architect — Com base neste PRD do **Migrador Planetexpress → HTML/Knockout.js**, defina a arquitetura técnica da solução. Pontos críticos: (1) escolha da biblioteca de parsing de PDF com extração de layout/coordenadas, (2) estratégia de matching com IA — modelo e provider recomendados para uso local, (3) stack do backend (Node.js/Python) e frontend, (4) estrutura do monorepo, (5) estratégia de geração de código JS/HTML/CSS. A ferramenta roda localmente sem cloud. Versão alvo do Knockout.js: 3.4.2.
