# Wireframes Mid-Fidelity — Migrador Planetexpress → HTML/Knockout.js

**Projeto:** Migrador Planetexpress → HTML/Knockout.js
**Fidelidade:** Mid-Fidelity
**Agente:** @ux-design-expert (Uma)
**Data:** 2026-03-09
**Telas:** 1 home + 5 wizard + 1 modal global (Bibliotecas)

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
- Tela inicial da ferramenta — antecede o wizard
- **Novo Template** → vai para Tela 1 (Upload) do zero
- **Abrir Projeto** → abre seletor de arquivo; carrega `.json` salvo; restaura estado completo e navega direto para a etapa onde o projeto foi salvo
- [📚 Bibliotecas] disponível **apenas aqui** — configuração prévia antes de iniciar um template
- "Novo template" na Tela 5 retorna para esta tela

---

## Componentes Globais

### Wizard Progress Bar (presente em todas as telas)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Migrador Planetexpress                        [💾 Salvar projeto]       │
├─────────────────────────────────────────────────────────────────────────────┤
│   ○──────────○──────────○──────────○──────────○                             │
│  [1.Upload] [2.Campos] [3.Layout] [4.Geração] [5.Exportar]    │
└─────────────────────────────────────────────────────────────────────────────┘
```
> [💾 Salvar projeto] aparece no header a partir da **Tela 2** — na Tela 1 ainda não há configuração para salvar.
> [📚 Bibliotecas] disponível **apenas na Tela 0** — não aparece durante o wizard.

### Progress Bar de Processamento (exibida durante operações longas)
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ⏳ Processando PDF...                                               45%    │
│  ████████████████████████░░░░░░░░░░░░░░░░░░░░░                             │
│  Extraindo texto e posicionamento — página 12 de 27                         │
└─────────────────────────────────────────────────────────────────────────────┘
```
> Diretriz: progress bar sempre visível durante qualquer processamento (NFR4, UX Directive).

---

## Tela 1 — Upload

**Estado base (nenhum arquivo carregado):**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Migrador Planetexpress                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│   ●──────────○──────────○──────────○──────────○                             │
│  [1.Upload] [2.Campos] [3.Layout] [4.Geração] [5.Exportar]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ENTRADA DO DOCUMENTO                                                      │
│   ─────────────────────────────────────────────────────────────────────    │
│                                                                             │
│   ┌──────────────────────────┐  ┌──────────────────────┐  ┌─────────────┐ │
│   │  📄 PDF do Documento  *  │  │  📋 Contrato XSD      │  │  📂 Dados   │ │
│   │                          │  │                      │  │  de Exemplo │ │
│   │  ┌─────────────────────┐ │  │ ┌──────────────────┐ │  │             │ │
│   │  │  Arraste o PDF      │ │  │ │  Arraste o .xsd  │ │  │ ┌─────────┐ │ │
│   │  │  ou clique para     │ │  │ │  ou clique para  │ │  │ │Arraste  │ │ │
│   │  │  selecionar         │ │  │ │  selecionar      │ │  │ │.xml ou  │ │ │
│   │  │  [Selecionar PDF]   │ │  │ │  [Selecionar]    │ │  │ │.json    │ │ │
│   │  └─────────────────────┘ │  │ └──────────────────┘ │  │ │[Selec.] │ │ │
│   └──────────────────────────┘  └──────────────────────┘  │ └─────────┘ │ │
│                                                            └─────────────┘ │
│   ⚠️ Envie ao menos o PDF + XSD  ou  PDF + arquivo de dados para continuar │
│                         [ Analisar Documento → ]  (desabilitado)           │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Estado: PDF + dados carregados (sem XSD)**
```
│   ┌──────────────────────────┐  ┌──────────────────────┐  ┌─────────────┐ │
│   │  📄 PDF do Documento  *  │  │  📋 Contrato XSD      │  │  📂 Dados   │ │
│   │                          │  │                      │  │  de Exemplo │ │
│   │  ✅ documento.pdf        │  │ ┌──────────────────┐ │  │             │ │
│   │     27 pág. | 2.4 MB    │  │ │  Arraste o .xsd  │ │  │ ✅ dados.xml │ │
│   │                          │  │ │  [Selecionar]    │ │  │    16 campos│ │
│   └──────────────────────────┘  │ └──────────────────┘ │  └─────────────┘ │
│                                 └──────────────────────┘                   │
│   💡 Adicionar o XSD permite validar se os dados estão completos e         │
│      identificar campos obrigatórios ausentes antes de prosseguir.         │
│                         [ Analisar Documento → ]                            │
```

**Estado: PDF + XSD carregados (sem dados)**
```
│   ┌──────────────────────────┐  ┌──────────────────────┐  ┌─────────────┐ │
│   │  📄 PDF do Documento  *  │  │  📋 Contrato XSD      │  │  📂 Dados   │ │
│   │                          │  │                      │  │  de Exemplo │ │
│   │  ✅ documento.pdf        │  │  ✅ Schema.xsd        │  │             │ │
│   │     27 pág. | 2.4 MB    │  │     18 campos        │  │ ┌─────────┐ │ │
│   │                          │  │     5 opcionais      │  │ │[Selec.] │ │ │
│   └──────────────────────────┘  └──────────────────────┘  │ └─────────┘ │ │
│                                                            └─────────────┘ │
│   💡 Adicionar dados de exemplo (.xml ou .json) melhora a identificação    │
│      de formatos (moeda, data, CPF...) e reduz campos com baixa confiança. │
│                         [ Analisar Documento → ]                            │
```

**Estado: PDF + XSD + Dados — validação automática OK**
```
│   ✅ documento.pdf        │  ✅ Schema.xsd (18 campos) │  ✅ dados.xml  │
│   ─────────────────────────────────────────────────────────────────────    │
│   ✅ XSD e dados compatíveis — 18 campos | 0 divergências                  │
│                         [ Analisar Documento → ]                            │
```

**Estado: PDF + XSD + Dados — divergência detectada**
```
│   ✅ documento.pdf        │  ✅ Schema.xsd (18)        │  ✅ dados.xml (16) │
│   ─────────────────────────────────────────────────────────────────────    │
│   ⚠️ Divergência detectada entre XSD e dados                               │
│      • "LinkDocumento" — presente no XSD, ausente nos dados               │
│      • "CodigoInterno" — presente nos dados, não declarado no XSD         │
│                                              [Ver detalhes]  [Ignorar →]  │
│                         [ Analisar Documento → ]                            │
```

**Anotações:**
- Mínimo para prosseguir: **PDF + XSD**  ou  **PDF + dados** (.xml ou .json)
- Os três juntos ativam a validação cruzada automática (XSD vs dados)
- Upload pode ser feito em qualquer ordem — validação cruzada dispara quando XSD + dados estiverem presentes simultaneamente
- Cada combinação tem sua dica 💡 específica sugerindo o que falta para melhorar a identificação
- Validação cruzada é não-bloqueante: operador pode ignorar divergências e prosseguir
- Divergências antecipam os 🟡/🔴 que aparecerão na Tela 2
- Ao clicar "Analisar Documento →": exibe progress bar (extração PDF + matching de campos)
- Bibliotecas são gerenciadas na Tela 0 — antes de iniciar o wizard

---

## Tela 2 — Identificação de Campos

> **Princípio:** A IA já fez o mapeamento completo. Tela 2 é um resumo revisável — o operador pode conferir e ajustar qualquer campo livremente, mesmo os que a IA resolveu. Exceções (🟡/🔴) são destacadas mas não bloqueiam se não houver nenhuma. "Confirmar ▶" habilitado assim que não houver pendências obrigatórias.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Migrador Planetexpress                        [💾 Salvar projeto]       │
├─────────────────────────────────────────────────────────────────────────────┤
│   ●──────────●──────────○──────────○──────────○                             │
│  [1.Upload] [2.Campos] [3.Layout] [4.Geração] [5.Exportar]    │
├────────────────────────────────────────┬────────────────────────────────────┤
│   📄 PDF Original          [🔍±] [◀1/27▶]│  📋 De-Para de Campos            │
│                                        │  ──────────────────────────────   │
│                                        │  18 campos  ✅ 15  🟡 2  🔴 1    │
│   ┌────────────────────────────────┐  │  ──────────────────────────────   │
│   │                                │  │                                   │
│   │  São Paulo, 15 de Janeiro      │  │  NomeSegurado   → Texto      [✏️] │
│   │  de 2025                       │  │  DataNascimento  → 📅 Data   [✏️] │
│   │                                │  │  Valor           → 💰 Moeda  [✏️] │
│   │  Prezado(a) Sônia Maria        │  │  Coberturas      → Lista     [✏️] │
│   │  da Silva,                     │  │  Logradouro      → Texto     [✏️] │
│   │                                │  │  + 10 campos...   [Ver todos]     │
│   │  Motivo: Documentação          │  │                                   │
│   │  incompleta                    │  │  ⚠️ Precisamos da sua ajuda       │
│   │                                │  │  ──────────────────────────────   │
│   │  ████ trecho ambíguo ████      │  │  🟡 CPFSegurado                   │
│   │                                │  │  "123.456.789-00"                 │
│   │                                │  │  ● CPFSegurado  ○ CPFSolicitante  │
│   │                                │  │              [Confirmar seleção]  │
│   │                                │  │                                   │
│   │                                │  │  🔴 LinkDocumento                 │
│   │                                │  │  Não encontrado no PDF            │
│   │                                │  │  ┌──────────────────────────────┐ │
│   │                                │  │  │ Buscar campo...            🔍 │ │
│   │                                │  │  └──────────────────────────────┘ │
│   │                                │  │  ou  [Marcar como opcional]       │
│   │                                │  │                                   │
│   │                                │  │  ── Elementos Especiais ────────  │
│   │                                │  │  📊 Gráfico — pág. 3             │
│   │                                │  │  ○ Imagem fixa                   │
│   │                                │  │  ● Dinâmico (vincular dados)     │
│   │                                │  │  Campo: [Selecionar campo... ▼]  │
│   └────────────────────────────────┘  │                                   │
├────────────────────────────────────────┴────────────────────────────────────┤
│  [◀ Voltar]  [↩ Restaurar mapeamento]    [Confirmar ▶]  ⚠️ 2 pendências  │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Anotações:**
- IA chegou com todos os campos mapeados e formatos sugeridos — tela é um resumo revisável
- Todos os campos visíveis na lista, com ícone [✏️] para o operador ajustar qualquer um livremente
- Clicar em qualquer campo → PDF destaca o trecho correspondente; clicar no PDF → destaca o campo
- 🟡 e 🔴 destacados no topo da seção de pendências — são os únicos que exigem atenção
- 🟡 ambíguo: IA tem sugestão mas baixa confiança — operador confirma ou troca
- 🔴 não identificado: operador busca manualmente ou marca como opcional
- Formato em linguagem do documento: Texto, Data, Valor monetário, Lista, Combinação de campos
- "Confirmar ▶" habilitado assim que não houver 🔴 obrigatórios sem resolução
- "Voltar" retorna para Tela 1 (Upload) — exibe aviso: "Voltar ao upload descartará todo o mapeamento atual. Deseja continuar?"
- "Restaurar mapeamento" restaura todos os campos ao estado original da análise da IA sem reprocessar — exibe aviso: "Isso descartará todos os ajustes manuais feitos. Deseja continuar?"
- Da Tela 3, o operador pode voltar aqui para ajustar formatos sem perder o trabalho

---

## Tela 3 — Layout

> **Princípio:** O sistema resolve o máximo automaticamente. Todos os itens são revisáveis via [✏️]. Se não houver pendências, tela é ignorada e fluxo avança direto para Revisão.
>
> **O que é Layout:** decisões de nível de documento feitas **antes** de gerar o HTML — página, fontes a carregar, cabeçalho/rodapé, comportamento de seções dinâmicas, imagens e gráficos. Se algo estiver errado estruturalmente na Tela 4, o ajuste vem aqui.
>
> **O que NÃO é Layout:** margem de um parágrafo, tamanho de fonte de um título, cor de um elemento — isso é CSS e fica na Tela 4.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Migrador Planetexpress                        [💾 Salvar projeto]       │
├─────────────────────────────────────────────────────────────────────────────┤
│   ●──────────●──────────●──────────○──────────○                             │
│  [1.Upload] [2.Campos] [3.Layout] [4.Geração] [5.Exportar]                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  📐 Layout do Documento                                                     │
│  Estrutura visual do template: página, fontes, cabeçalho, rodapé e seções. │
│  Erros estruturais na Tela 4? O ajuste provavelmente está aqui.            │
│                                                                             │
├──────────────────────────┬──────────────────────────────────────────────────┤
│                          │                                                  │
│  ┌────────────────────┐  │  📄 Página                                       │
│  │  ▓▓▓ Cabeçalho ▓▓▓ │  │  ✅ A4  |  8.27in × 11.69in              [✏️]  │
│  │  ────────────────  │  │  ✅ Orientação: Retrato                   [✏️]  │
│  │                    │  │  ✅ Margens: 1in (detectadas)             [✏️]  │
│  │  Conteúdo fixo     │  │                                                  │
│  │                    │  │  ▓ Cabeçalho                                     │
│  │  ┌──────────────┐  │  │  ✅ Logo + título — repete em todas págs  [✏️]  │
│  │  │  ⟳ [Lista 1]│  │  │  ✅ Altura reservada: 1.2in               [✏️]  │
│  │  └──────────────┘  │  │                                                  │
│  │                    │  │  ▓ Rodapé                                        │
│  │  ┌──────────────┐  │  │  ✅ Número de página — repete em todas págs[✏️] │
│  │  │  ⟳ [Lista 2]│  │  │  ✅ Altura reservada: 0.5in               [✏️]  │
│  │  └──────────────┘  │  │                                                  │
│  │                    │  │  🔤 Fontes a carregar                            │
│  │  Conteúdo fixo     │  │  ✅ Helvetica → sentico.css               [✏️]  │
│  │                    │  │  ⚠️ MontserratCustom — não encontrada            │
│  │  ▓▓▓ Rodapé ▓▓▓▓  │  │     Sugestão: Montserrat (Google Fonts 96%)      │
│  └────────────────────┘  │     ● Baixar auto  ○ Upload manual              │
│   A4 | Retrato           │     Salvar: ● Bibliotecas  ○ Só este template   │
│                          │                                                  │
│                          │  ⟳ Seções Dinâmicas                             │
│                          │  ✅ [Lista 1] — comportamento de paginação [✏️] │
│                          │  ✅ [Lista 2] — comportamento de paginação [✏️] │
│                          │                                                  │
│                          │  🖼️ Imagens e SVG                               │
│                          │  ✅ SVG do logo — inline no HTML           [✏️]  │
│                          │  ✅ 3 imagens extraídas → img/             [✏️]  │
│                          │                                                  │
│                          │  📊 Gráficos                                     │
│                          │  ✅ Gráfico pág.3 — Dinâmico              [✏️]  │
│                          │     Campo vinculado: vendas_mensal               │
│                          │     (definido na Tela 2 — Tela 4: tipo/eixos)   │
│                          │                                                  │
├──────────────────────────┴──────────────────────────────────────────────────┤
│  [◀ Voltar]  [↩ Desfazer ajustes]                        [ Avançar → ]      │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Aviso ao clicar [◀ Voltar] (se houver ajustes feitos na Tela 3):**
```
┌──────────────────────────────────────────────┐
│  ⚠️ Voltar para Tela 2                       │
│                                              │
│  Seus ajustes de layout serão perdidos.      │
│  Ao retornar, o layout será regenerado       │
│  com base nos novos campos.                  │
│                                              │
│  [Cancelar]        [Voltar mesmo assim]      │
└──────────────────────────────────────────────┘
```

**Estado da seção Gráficos — quando marcado como "Imagem fixa" na Tela 2:**
```
│  📊 Gráficos                                                              │
│  (nenhum gráfico dinâmico configurado — sem pendências aqui)              │
```

**Estado da seção Gráficos — quando marcado como "Dinâmico" na Tela 2:**
```
│  📊 Gráficos                                                              │
│  ✅ Gráfico pág.3 — Dinâmico                                       [✏️]  │
│     Campo vinculado: vendas_mensal  ✔ (definido na Tela 2)               │
│     ↳ Tipo de gráfico, eixos e cores: configurar na Tela 4               │
```
> Tela 3 apenas confirma o campo já vinculado. Não pede nova decisão.
> Se o campo estiver incorreto: clicar [✏️] abre seletor de campo para corrigir.

**Exemplo: operador clica [✏️] em "Campo vinculado" do gráfico:**
```
│  ✅ Gráfico pág.3 — Campo: vendas_mensal                           [✏️]  │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  Campo vinculado:  [vendas_mensal ▼]   (campos da Tela 2)          │  │
│  │                                          [Salvar]  [Cancelar]      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
```

**Exemplo: operador clica [✏️] em "Tamanho de página"**
```
│  ✅ A4  |  8.27in × 11.69in                                           [✏️] │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ● A4 (8.27in × 11.69in)   ○ Carta (8.5in × 11in)   ○ Customizado │   │
│  │  Largura: [8.27in]   Altura: [11.69in]                             │   │
│  │                                          [Salvar]  [Cancelar]      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
```

**Exemplo: operador clica [✏️] em "[Lista 1] — comportamento de paginação"**
```
│  ✅ [Lista 1] — comportamento de paginação                           [✏️] │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Quebra de página:  ● Automática   ○ Manual                        │   │
│  │  Cabeçalho da tabela repete nas páginas seguintes:  ● Sim  ○ Não  │   │
│  │                                          [Salvar]  [Cancelar]      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
```

**Exemplo: operador clica [✏️] em "Fonte Helvetica"**
```
│  ✅ Helvetica → sentico.css                                           [✏️] │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Carregar via: ● sentico.css  ○ Outra biblioteca  ○ Upload manual  │   │
│  │  [Preview  Aa Bb Cc 123]                                           │   │
│  │                                          [Salvar]  [Cancelar]      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
```

**Anotações:**
- Layout dividido em dois painéis: esquerdo mostra visão estrutural do documento, direito mostra itens configuráveis agrupados por categoria
- Visão estrutural à esquerda dá ao operador referência visual de onde cada elemento aparece no documento
- ✅ resolvido automaticamente — [✏️] disponível para qualquer ajuste
- ⚠️ pendência — requer decisão do operador antes de avançar
- Clicar [✏️] expande o item inline; outros itens permanecem visíveis
- Seções dinâmicas: campo já vem identificado da Tela 2 — aqui só se configura comportamento de paginação
- Fontes: apenas resolução do recurso (de onde carregar) — aplicação de estilo fica na Tela 4
- "Avançar →" dispara geração do HTML/CSS/JS e vai para Tela 4
- Operador pode retornar à Tela 3 a partir da Tela 4 via "◀ Ajustar Layout" — sistema regenera o HTML ao salvar
- Gráficos: decisão "imagem fixa vs dinâmico" + seleção do campo são feitas na Tela 2 — Tela 3 só exibe confirmação do campo vinculado quando dinâmico; se "imagem fixa", gráfico não aparece aqui; detalhes (tipo, eixos, cores Chart.js) ficam na Tela 4
- Nomes [Lista 1] e [Lista 2] são exemplos — na tela real aparecem os nomes dos campos identificados na Tela 2

---

## Tela 4 — Geração

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Migrador Planetexpress                        [💾 Salvar projeto]       │
├─────────────────────────────────────────────────────────────────────────────┤
│   ●──────────●──────────●──────────●──────────○                             │
│  [1.Upload] [2.Campos] [3.Layout] [4.Geração] [5.Exportar]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─── SCORE DE FIDELIDADE ────────────────────────────────────────────────┐ │
│  │  🎯 87%  ████████████████████░░░░  [Detalhes ▼]  [✨ Melhorar com IA] │ │
│  │  "Fonte e espaçamento do rodapé divergem do PDF original."             │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
├──────────────────────────────────┬──────────────────────────────────────────┤
│  📄 PDF Original   [◀ 1/27 ▶]   │  🌐 HTML Gerado     [◀ 1/27 ▶]          │
│  ────────────────────────────    │  ──────────────────────────────────────  │
│                                  │                                          │
│  ┌──────────────────────────┐   │  ┌──────────────────────────────────┐   │
│  │ [Logo]  Mongeral Aegon   │   │  │ [Logo]  Mongeral Aegon           │   │
│  │──────────────────────────│   │  │──────────────────────────────────│   │
│  │ São Paulo, 15 Jan 2025   │   │  │ São Paulo, 15 Jan 2025           │   │
│  │                          │   │  │                                  │   │
│  │ Prezado(a) Sônia Maria   │   │  │ Prezado(a) Sônia Maria           │   │
│  │ da Silva,                │   │  │ da Silva,                        │   │
│  │                          │   │  │                                  │   │
│  │  ┌──────────────────┐   │   │  │  ┌──────────────────────────┐   │   │
│  │  │  [Gráfico PDF]   │   │   │  │  │  📊 Gráfico dinâmico     │   │   │
│  │  │                  │   │   │  │  │  Campo: vendas_mensal     │   │   │
│  │  └──────────────────┘   │   │  │  │  [⚙️ Configurar Chart.js] │   │   │
│  │                          │   │  │  └──────────────────────────┘   │   │
│  │  ─────────────────────   │   │  │  ████ divergência ████           │   │
│  │  Rodapé — pág. 1         │   │  │  Rodapé — pág. 1  (deslocado)   │   │
│  └──────────────────────────┘   │  └──────────────────────────────────┘   │
│                                  │                                          │
│                                  │  [✏️ Editar Código]  [🖱️ Editar Visual]  │
├──────────────────────────────────┴──────────────────────────────────────────┤
│  [◀ Ajustar Layout]                             [ Gerar Output → ]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Estado: [✏️ Editar Código] acionado — painel direito substituído pelo Monaco Editor:**
```
├──────────────────────────────────┬──────────────────────────────────────────┤
│  📄 PDF Original   [◀ 3/27 ▶]   │  ✏️ Editor de Código          [✕ Fechar] │
│                                  │  [index.html] [style.css] [base.js]      │
│  ┌──────────────────────────┐   │  ──────────────────────────────────────  │
│  │ [Logo]  Mongeral Aegon   │   │  1  <div class="page">                   │
│  │ São Paulo, 15 Jan 2025   │   │  2    <div class="cabecalho">            │
│  │                          │   │  3      <img src="./img/logo.png"/>      │
│  │ Prezado(a) Sônia Maria   │   │  4    </div>                             │
│  │                          │   │  5    <div class="corpo">                │
│  └──────────────────────────┘   │  6      <p data-bind="text: Nome">      │
│                                  │  ...                                     │
│                                  │                        [✅ Aplicar →]   │
├──────────────────────────────────┴──────────────────────────────────────────┤
│  [◀ Ajustar Layout]                             [ Gerar Output → ]          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Estado: [🖱️ Editar Visual] acionado — modo edição sobre o painel HTML:**
```
├──────────────────────────────────┬──────────────────────────────────────────┤
│  📄 PDF Original   [◀ 1/27 ▶]   │  🖱️ Modo Edição Visual    [✕ Sair]       │
│                                  │  ──────────────────────────────────────  │
│  ┌──────────────────────────┐   │  ┌──────────────────────────────────┐   │
│  │ [Logo]  Mongeral Aegon   │   │  │ [Logo]  Mongeral Aegon           │   │
│  │ São Paulo, 15 Jan 2025   │   │  │ São Paulo, 15 Jan 2025           │   │
│  │                          │   │  │ ┌──────────────────────────────┐ │   │
│  │ Prezado(a) Sônia Maria   │   │  │ │↕ Prezado(a) Sônia Maria  ↔  │ │   │
│  │                          │   │  │ └──────────────────────────────┘ │   │
│  │  ─────────────────────   │   │  │  Rodapé — pág. 1                 │   │
│  └──────────────────────────┘   │  └──────────────────────────────────┘   │
│                                  │  💡 Clique para selecionar · Arraste    │
│                                  │     para mover · Duplo clique p/ editar │
├──────────────────────────────────┴──────────────────────────────────────────┤
│  [◀ Ajustar Layout]                             [ Gerar Output → ]          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Estado: [⚙️ Configurar Chart.js] acionado — painel direito substituído:**
```
├──────────────────────────────────┬──────────────────────────────────────────┤
│  📄 PDF Original   [◀ 3/27 ▶]   │  ⚙️ Configurar Gráfico — pág. 3   [✕]   │
│                                  │  ──────────────────────────────────────  │
│  ┌──────────────────────────┐   │                                           │
│  │  [Gráfico PDF]           │   │  Campo vinculado: vendas_mensal  (Tela 2) │
│  │                          │   │                                           │
│  └──────────────────────────┘   │  Tipo de gráfico                          │
│                                  │  ● Barra  ○ Linha  ○ Pizza  ○ Donut      │
│                                  │                                           │
│                                  │  Eixo X — rótulos                        │
│                                  │  [mes ▼]  (campos do array)              │
│                                  │                                           │
│                                  │  Eixo Y — valores                        │
│                                  │  [valor ▼]  (campos do array)            │
│                                  │                                           │
│                                  │  Título do gráfico                       │
│                                  │  [Vendas Mensais          ]              │
│                                  │                                           │
│                                  │  Cor principal   [████] #4A90D9          │
│                                  │  Mostrar legenda   ● Sim  ○ Não          │
│                                  │  Rótulos nos pontos  ○ Sim  ● Não        │
│                                  │                                           │
│                                  │  💡 Config avançada: Editar Código       │
│                                  │                                           │
│                                  │  [Cancelar]         [✅ Salvar →]        │
├──────────────────────────────────┴──────────────────────────────────────────┤
│  [◀ Ajustar Layout]                             [ Gerar Output → ]          │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Estado: após salvar — gráfico renderizado no painel HTML:**
```
│  │  ┌──────────────────────────┐   │   │
│  │  │  📊 [preview Chart.js]   │   │   │
│  │  │  Vendas Mensais          │   │   │
│  │  │  ▄▄ ▄▇ ▅▄ ▇▅ ▃▆         │   │   │
│  │  └──────────────────────────┘   │   │
```

**Aviso ao clicar [◀ Ajustar Layout] (sempre):**
```
┌──────────────────────────────────────────────┐
│  ⚠️ Voltar ao Layout                         │
│                                              │
│  O HTML será regenerado ao avançar.          │
│  Edições feitas nesta tela serão perdidas.   │
│                                              │
│  [Cancelar]      [Voltar ao Layout]          │
└──────────────────────────────────────────────┘
```

### Estado: ✨ Melhorar com IA acionado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  ✨ Sugestões da IA — 3 ajustes propostos              [Aceitar Todos] [✕]  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  1. Rodapé — margin-bottom: 8px → 14px                               │ │
│  │     "Corrige deslocamento vertical identificado na página 1"          │ │
│  │                              [✅ Aceitar]  [↩️ Rejeitar]  [✏️ Ajustar] │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  2. Fonte .rodape — font-family: Helvetica → MontserratCustom         │ │
│  │     "Aproxima tipografia do PDF original"                             │ │
│  │                              [✅ Aceitar]  [↩️ Rejeitar]  [✏️ Ajustar] │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  3. .header-logo — width: 120px → 132px                               │ │
│  │     "Corrige proporção do logo identificada na página 1"              │ │
│  │                              [✅ Aceitar]  [↩️ Rejeitar]  [✏️ Ajustar] │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  Após aplicar: score recalculado automaticamente                            │
│                                              [Aplicar Selecionados →]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Anotações:**
- Comparação visual lado a lado: PDF original (esquerda) vs HTML renderizado (direita)
- Divergências destacadas visualmente em laranja/vermelho no painel do HTML (FR33)
- Paginação sincronizada: navegar página no PDF avança a mesma página no HTML e vice-versa
- Score de fidelidade calculado por IA ao entrar na tela — recalcula após cada aplicação de ajuste
- "Melhorar com IA" (FR34): IA propõe ajustes CSS/posicionamento — operador aceita/rejeita por item
- "Editar Código" (FR24): substitui painel direito pelo Monaco Editor com abas index.html / style.css / base.js; PDF permanece à esquerda como referência; [✅ Aplicar] aplica e restaura painel HTML
- "Editar Visual" (FR25): ativa modo edição sobre o próprio painel HTML — layout não muda; elementos clicáveis com handles de resize e reposicionamento; dica contextual no rodapé do painel; [✕ Sair] desativa o modo
- Edições manuais e ajustes IA são cumulativos; output empacotado apenas em "Gerar Output →"
- Gráficos dinâmicos aparecem como placeholder no painel HTML com [⚙️ Configurar Chart.js] — após configurar, renderiza preview com dados do exemplo.js
- Configuração Chart.js (FR26): abre no painel direito substituindo o HTML; campos tipo, eixos, título, cor, legenda; config avançada via Editar Código; PDF permanece visível à esquerda para referência
- [◀ Ajustar Layout] sempre exibe aviso antes de navegar — HTML é regenerado ao avançar de volta, edições desta tela são perdidas
- Tela 3 preserva todos os ajustes anteriores ao retornar — operador pode ir e voltar livremente entre Tela 3 e Tela 4

---

## Tela 5 — Exportar

> **Princípio:** Validação técnica é responsabilidade do sistema, não do operador. Esta tela é um resumo de conclusão — o operador chegou aqui porque tudo funcionou. Erros técnicos bloqueantes são tratados pelo sistema antes de chegar aqui.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Migrador Planetexpress                        [💾 Salvar projeto]       │
├─────────────────────────────────────────────────────────────────────────────┤
│   ●──────────●──────────●──────────●──────────●                             │
│  [1.Upload] [2.Campos] [3.Layout] [4.Geração] [5.Exportar]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ✅ Template gerado com sucesso — CartaInabilitado                          │
│                                                                             │
│  🎯 Fidelidade final: 94%   ██████████████████████░░                       │
│                                                                             │
│  ──────────────────────────────────────────────────────────────────────     │
│                                                                             │
│  📁 CartaInabilitado/              9 arquivos  |  79 KB total               │
│    ├── index.html                                              12 KB        │
│    ├── css/style.css                                            4 KB        │
│    ├── css/fonts.css                                            1 KB        │
│    ├── js/base.js                                               8 KB        │
│    ├── js/graficos.js                                           3 KB        │
│    ├── exemplo.js                                               2 KB        │
│    └── img/  (2 arquivos)                                      77 KB        │
│                                                                             │
│  ──────────────────────────────────────────────────────────────────────     │
│                                                                             │
│  [🔍 Abrir Preview]   [◀ Voltar à Geração]      [ ➕ Novo template ]        │
│                                                                             │
│                                                  [ ⬇️ Baixar ZIP ]          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Anotações:**
- Validação técnica (bindings, estrutura, imagens) executada silenciosamente pelo sistema ao gerar — erros bloqueantes impedem a chegada nesta tela
- Score exibido é o fidelidade final após todos os ajustes feitos na Tela 4
- "Abrir Preview" abre `index.html` + `exemplo.js` em nova aba do browser
- "Voltar à Geração" disponível caso o operador queira fazer mais ajustes — exibe o mesmo aviso de perda de edições
- "Salvar projeto" disponível globalmente no header em todas as telas do wizard — exporta `.json` com estado completo da sessão (mapeamento, layout, Chart.js); permite reabrir via Tela 0
- "Novo template" retorna para Tela 0 — Home
- "Baixar ZIP" sempre habilitado ao chegar nesta tela

---

## Tela 6 — Gestão de Bibliotecas (pré-configuração)

**Estado: Aba Fontes (padrão)**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  📚 Catálogo de Bibliotecas                                          [✕]    │
│  (Fontes e estilos compartilhados — disponíveis para todos os templates)    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [🔤 Fontes]  [🎨 CSS]  [📦 JS]                   [+ Adicionar Arquivo]    │
│  ──────────────────────────────────────────────────────────────────────     │
│                                                                             │
│  ▶ ABA ATIVA: 🔤 Fontes                                                    │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  Aa  Helvetica Neue          sentico.css         23 KB  [🗑️ Remover]  │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  Aa  Open Sans               open-sans.css       18 KB  [🗑️ Remover]  │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  Aa  Montserrat              (baixada agora)      —     [🗑️ Remover]  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ℹ️  Fontes adicionadas aqui ficam disponíveis para detecção automática     │
│     em todos os templates futuros.                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Estado: Aba CSS**
```
│  [🔤 Fontes]  [🎨 CSS]  [📦 JS]                   [+ Adicionar Arquivo]    │
│  ──────────────────────────────────────────────────────────────────────     │
│                                                                             │
│  ▶ ABA ATIVA: 🎨 CSS                                                       │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  📄  sentico.css             sentico.css         23 KB  [🗑️ Remover]  │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  📄  sentico-v2.css          sentico-v2.css      18 KB  [🗑️ Remover]  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ℹ️  Arquivos CSS adicionados aqui ficam disponíveis como referência        │
│     compartilhada em todos os templates futuros.                            │
```

**Estado: Aba JS**
```
│  [🔤 Fontes]  [🎨 CSS]  [📦 JS]                   [+ Adicionar Arquivo]    │
│  ──────────────────────────────────────────────────────────────────────     │
│                                                                             │
│  ▶ ABA ATIVA: 📦 JS                                                        │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │  📦  knockout-3.4.2.js       js/                 89 KB  [🗑️ Remover]  │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  📦  knockout.mapping.js     js/                 12 KB  [🗑️ Remover]  │ │
│  ├───────────────────────────────────────────────────────────────────────┤ │
│  │  📦  Chart.min.js            js/                240 KB  [🗑️ Remover]  │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ℹ️  Bibliotecas JS adicionadas aqui ficam disponíveis como dependência     │
│     compartilhada em todos os templates futuros.                            │
```

**Anotações:**
- Acessível via [📚 Bibliotecas] na **Tela 0 — Home** (pré-configuração antes de iniciar o wizard); não disponível durante o wizard
- Tabs: Fontes | CSS | JS — mesma estrutura de lista em todas as abas
- **[+ Adicionar Arquivo]** contextual pela aba ativa: Fontes aceita `.ttf/.woff/.woff2`, CSS aceita `.css`, JS aceita `.js`; simples file picker, sem formulário extra; arquivo aparece imediatamente na lista após upload

---

## Fluxo de Interação Principal

```
[0. Home]
  ├── [📚 Bibliotecas] → pré-configurar fontes/CSS/JS compartilhados (opcional)
  ├── [➕ Novo Template] → inicia wizard do zero
  └── [📂 Abrir Projeto] → carrega .json salvo → retoma na etapa onde parou
        ↓
[1. Upload]
  ├── PDF (obrigatório) + XSD (opcional) + dados .xml/.json (opcional)
  ├── Mínimo: PDF + XSD  ou  PDF + dados
  └── [Analisar Documento →]
        ↓
[⏳ Progress: Extraindo PDF + Matching de campos]
        ↓
[2. Campos]
  ├── IA pré-preenche mapeamento de-para
  ├── Resolver campos ambíguos (🟡) e não mapeados (🔴)
  ├── Elementos Especiais: decisão imagem fixa vs gráfico dinâmico
  ├── [💾 Salvar projeto] disponível no header
  └── [Confirmar ▶]
        ↓
[3. Layout]  ← ignorada automaticamente se não há decisões pendentes
  ├── Página: tamanho, orientação, margens
  ├── Fontes: catálogo → Google Fonts → upload manual
  ├── Cabeçalho/rodapé: detecção e repetição entre páginas
  ├── Gráficos dinâmicos: confirmação de campo vinculado
  ├── [↩ Desfazer ajustes] restaura estado inicial sem reprocessamento
  ├── [◀ Voltar] → aviso: ajustes serão perdidos ao retornar à Tela 2
  └── [Avançar →]
        ↓
[⏳ Progress: Gerando draft HTML/CSS/JS]
        ↓
[4. Geração]
  ├── Painel esquerdo: PDF original (sempre visível)
  ├── Painel direito intercambiável:
  │     (1) HTML gerado com placeholders de gráficos dinâmicos
  │     (2) Monaco Editor — editar index.html / style.css / base.js
  │     (3) Edição visual WYSIWYG sobre o painel HTML
  │     (4) Config Chart.js — tipo, eixos, título, cor, legenda
  ├── 🎯 Score de fidelidade IA (HTML vs PDF)
  ├── [✨ Melhorar com IA] para correções pontuais
  ├── [◀ Ajustar Layout] → aviso: HTML será regenerado e edições perdidas
  └── [Gerar Output →]
        ↓
[⏳ Progress: Empacotando ZIP + validando]
        ↓
[5. Exportar]
  ├── 🎯 Score de fidelidade final
  ├── Árvore de arquivos gerados
  ├── [🔍 Abrir Preview] → abre index.html + exemplo.js no browser
  ├── [◀ Voltar à Geração] → retorna para ajustes adicionais
  ├── [➕ Novo template] → retorna à Tela 0 (Home)
  └── [⬇️ Baixar ZIP]
```

---

## Inventário de Componentes (Atomic Design)

### Átomos
- Button (Primary, Secondary, Danger, Ghost, Disabled)
- Input (Text, File Upload, Number)
- Toggle / Radio Group
- Badge (success, warning, error, info)
- Progress Bar (linear + percentual)
- Icon
- Tooltip
- Code Tab (aba de arquivo no editor)

### Moléculas
- Upload Dropzone (Icon + Label + Button + Preview info)
- Field Status Item (Badge + Campo + Ação)
- Candidate Dropdown (Label + Select)
- Config Card (Header + Content + Action)
- Font Card (Preview Aa + Nome + Ação)
- Validation Item (Icon + Mensagem)
- File Tree Item (Ícone + Nome + Tamanho)
- Fidelidade Score Bar (Percentual + Barra + Comentário IA + Detalhes)
- Depara Row (Campo PDF + seta + Binding)

### Organismos
- Wizard Progress Bar (5 Steps + Active indicator)
- Processing Progress Bar (Label + Bar + Percentual + Detalhe)
- Upload Panel (dois Dropzones + toggle JSON/XSD)
- Identification Panel (PDF Viewer + Fields Panel bidirecional)
- Config Panel (Resolvidos + Pendentes por decisão humana)
- Revisão Panel (Score Fidelidade + De-Para + Monaco Editor integrado)
- Validation Report (Lista de Validation Items)
- File Tree (estrutura de arquivos do output)
- Bibliotecas Modal (Tabs Fontes/CSS/JS + lista + upload)

### Templates
- Wizard Layout (Header global + Progress 5 etapas + Conteúdo + Footer actions)
- Split Layout (Painel esquerdo + Painel direito)
- Modal Layout (Overlay + Header + Body + Footer)

---

## Espaçamento e Medidas

```
Base unit: 4px

Escala:
- xs:  4px   (separador interno)
- sm:  8px   (padding de elementos pequenos)
- md:  16px  (padding padrão de painéis)
- lg:  24px  (separação entre seções)
- xl:  32px  (margin entre blocos principais)
- 2xl: 48px  (espaçamento de tela)
```

**Dimensões das telas:**
- Mínimo suportado: 1280px × 768px
- Recomendado: 1440px × 900px
- Target: desktop Chrome/Edge modernos

---

*Wireframes gerados por @ux-design-expert (Uma) | Projeto: Migrador Planetexpress*
*Próximo passo: `*create-front-end-spec` para especificação técnica detalhada*
