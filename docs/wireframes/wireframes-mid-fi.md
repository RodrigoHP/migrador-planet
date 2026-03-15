# Wireframes Mid-Fidelity — Migrador Planetexpress → HTML/Knockout.js

**Projeto:** Migrador Planetexpress → HTML/Knockout.js
**Fidelidade:** Mid-Fidelity
**Agente:** @ux-design-expert (Uma)
**Data:** 2026-03-15 (v3 — alinhado com Arquitetura v5.0)
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
│  ⏳ Analisando documento...                                          45%    │
│  ████████████████████████░░░░░░░░░░░░░░░░░░░░░                             │
│  Etapa 9/23 — Multi-Example Layout Analysis — página 12 de 27              │
│  Bloco 3/8: Layout Intelligence                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```
> Diretriz: progress bar sempre visível durante qualquer processamento (NFR4, UX Directive).
> Pipeline de 23 stages em 8 blocos (arch v5.0):
> Bloco 1: Document Acquisition (Upload, PDF Parsing + Text Reconstruction + Font/Image Extraction)
> Bloco 2: Layout Discovery (Skeleton Builder + Grid Detection, Clustering, Page Selection, Fingerprint, Registry Lookup)
> Bloco 3: Layout Intelligence (Alignment, Multi-Example Analysis, Stability, Variant Detection, Normalization)
> Bloco 4: Table Intelligence (Table Identity, Continuation Detection)
> Bloco 5: Layout Semantics (Zone Detection, Anchor Detection)
> Bloco 6: Vision Interpretation (Vision Analysis, Vision Self-Check)
> Bloco 7: Data Mapping (Field Mapping, Format Detection, Confidence Scoring + Template Confidence)
> Bloco 8: Validation + Template Generation (Consistency Validation, HTML + CSS + Knockout Generation)
> A progress bar mostra etapa atual, bloco ativo e sub-progresso (e.g., páginas processadas).

---

## Tela 1 — Upload

> **Arquitetura v5.0:** Com Vision AI + semantic matching + pgvector, o sistema infere formatos diretamente do PDF sem precisar de dados de exemplo. O XSD é obrigatório porque define os nomes canônicos dos campos usados como `data-bind` no Knockout.js. **Multi-PDF recomendado** (1 obrigatório, 3-5 ideal) — quanto mais exemplos, melhor a detecção de labels vs valores dinâmicos e blocos condicionais.

**Estado base (nenhum arquivo carregado):**
```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Migrador Planetexpress                                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│   ●──────────○──────────○──────────○──────────○                             │
│  [1.Upload] [2.Campos] [3.Layout] [4.Geração] [5.Exportar]                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ENTRADA DO DOCUMENTO                                                      │
│   ─────────────────────────────────────────────────────────────────────    │
│                                                                             │
│   ┌──────────────────────────────────────────────┐  ┌────────────────────┐ │
│   │  📄 PDFs do Documento  *                      │  │  📋 Contrato XSD * │ │
│   │  (1 obrigatório · 3-5 recomendado)            │  │                    │ │
│   │  ┌──────────────────────────────────────────┐ │  │  ┌──────────────┐ │ │
│   │  │  Arraste os PDFs de exemplo              │ │  │  │  Arraste o   │ │ │
│   │  │  ou clique para selecionar               │ │  │  │  .xsd        │ │ │
│   │  │                                          │ │  │  │              │ │ │
│   │  │      [Selecionar PDFs]                   │ │  │  │ [Selecionar] │ │ │
│   │  └──────────────────────────────────────────┘ │  │  └──────────────┘ │ │
│   │  💡 Quanto mais PDFs de exemplo, melhor a      │  │                    │ │
│   │     detecção de campos e blocos condicionais   │  │                    │ │
│   └──────────────────────────────────────────────┘  └────────────────────┘ │
│                                                                             │
│   ⚠️ Envie ao menos 1 PDF e o XSD do documento para continuar              │
│                         [ Analisar Documento → ]  (desabilitado)            │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Estado: 1 PDF carregado (falta XSD)**
```
│   ┌──────────────────────────────────────────────┐  ┌────────────────────┐ │
│   │  📄 PDFs do Documento  *                      │  │  📋 Contrato XSD * │ │
│   │                                                │  │                    │ │
│   │  ✅ documento.pdf          27 pág. | 2.4 MB   │  │  ┌──────────────┐ │ │
│   │                            [🗑️]               │  │  │  Arraste o   │ │ │
│   │                                                │  │  │  .xsd        │ │ │
│   │  💡 Adicione mais 2-4 PDFs do mesmo tipo       │  │  │ [Selecionar] │ │ │
│   │     para melhorar a detecção                   │  │  └──────────────┘ │ │
│   │                 [+ Adicionar PDFs]             │  │                    │ │
│   └──────────────────────────────────────────────┘  └────────────────────┘ │
│   ⚠️ Falta o contrato XSD. O XSD define os campos do template final.      │
│                         [ Analisar Documento → ]  (desabilitado)           │
```

**Estado: 3 PDFs + XSD carregados — ideal para análise**
```
│   ┌──────────────────────────────────────────────┐  ┌────────────────────┐ │
│   │  📄 PDFs do Documento  *  (3 arquivos)        │  │  📋 Contrato XSD * │ │
│   │                                                │  │                    │ │
│   │  ✅ fatura_jan.pdf         12 pág. | 1.1 MB [🗑️]│  │  ✅ Schema.xsd    │ │
│   │  ✅ fatura_fev.pdf         12 pág. | 1.0 MB [🗑️]│  │     18 campos    │ │
│   │  ✅ fatura_mar.pdf         14 pág. | 1.3 MB [🗑️]│  │     5 opcionais  │ │
│   │                                                │  │                    │ │
│   │  ✅ 3 PDFs — detecção multi-example ativa      │  │                    │ │
│   │                 [+ Adicionar PDFs]             │  │                    │ │
│   └──────────────────────────────────────────────┘  └────────────────────┘ │
│                                                                             │
│   ✅ PDFs e XSD carregados — pronto para análise                            │
│                         [ Analisar Documento → ]                            │
```

**Estado: 1 PDF + XSD — mínimo funcional**
```
│   ┌──────────────────────────────────────────────┐  ┌────────────────────┐ │
│   │  📄 PDFs do Documento  *  (1 arquivo)         │  │  📋 Contrato XSD * │ │
│   │                                                │  │                    │ │
│   │  ✅ documento.pdf          27 pág. | 2.4 MB [🗑️]│  │  ✅ Schema.xsd    │ │
│   │                                                │  │     18 campos    │ │
│   │  💡 Adicione mais PDFs do mesmo tipo para      │  │     5 opcionais  │ │
│   │     ativar detecção de variantes e condicionais│  │                    │ │
│   │                 [+ Adicionar PDFs]             │  │                    │ │
│   └──────────────────────────────────────────────┘  └────────────────────┘ │
│                                                                             │
│   ✅ PDF e XSD carregados — pronto para análise (1 PDF = detecção básica)   │
│                         [ Analisar Documento → ]                            │
```

**Anotações:**
- **PDF obrigatório (1 mínimo, 3-5 recomendado) + XSD obrigatório** para prosseguir (PRD v2.3, FR2)
- **Multi-PDF:** dropzone aceita múltiplos PDFs do mesmo tipo de documento; cada PDF listado individualmente com botão [🗑️] para remover
- Com 1 PDF: pipeline funcional mas sem variant detection nem multi-example analysis (Vision AI assume toda inferência)
- Com 3-5 PDFs: multi-example layout analysis ativa — detecta labels vs valores dinâmicos, blocos condicionais (<!-- ko if: -->), estabilidade de layout
- Hint contextual muda conforme quantidade: 1 PDF = "adicione mais para melhorar detecção"; 3+ PDFs = "detecção multi-example ativa"
- XSD define os nomes canônicos dos campos que viram `data-bind="text: campo"` no Knockout.js
- Vision AI + pgvector inferem formatos (moeda, data, CPF) diretamente do PDF — não há necessidade de dados de exemplo
- `exemplo.js` é gerado automaticamente a partir do XSD na etapa de exportação (FR2b)
- Ao clicar "Analisar Documento →": exibe progress bar (pipeline de 23 stages em 8 blocos — ver Progress Bar acima)
- Bibliotecas são gerenciadas na Tela 0 — antes de iniciar o wizard

---

## Tela 2 — Identificação de Campos

> **Princípio:** A IA (Vision AI + pgvector semantic matching) já fez o mapeamento completo dos campos do XSD para regiões do PDF. Tela 2 é um resumo revisável com anotação interativa via **Konva.js** sobre PDF.js — o operador pode conferir e ajustar qualquer campo livremente, inclusive desenhando/redimensionando regiões sobre o PDF. Exceções (🟡/🔴) são destacadas mas não bloqueiam se não houver nenhuma. "Confirmar ▶" habilitado assim que não houver pendências obrigatórias.
>
> **Arquitetura v5.0:** Painel esquerdo usa PDF.js + camada Konva.js (canvas interativo sobreposto). O operador pode desenhar retângulos, redimensionar regiões e associar campos do XSD clicando na região. **Coverage Mode** disponível — overlay visual mostrando cobertura do mapeamento. Com multi-PDF, campos têm indicador de **estabilidade** (STABLE/VARIABLE/OPTIONAL).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  🔄 Migrador Planetexpress                        [💾 Salvar projeto]       │
├─────────────────────────────────────────────────────────────────────────────┤
│   ●──────────●──────────○──────────○──────────○                             │
│  [1.Upload] [2.Campos] [3.Layout] [4.Geração] [5.Exportar]                 │
├────────────────────────────────────────┬────────────────────────────────────┤
│  📄 PDF + Anotações  [🔍±] [◀1/27▶]    │  📋 De-Para de Campos            │
│  ──────────────────────────────────    │  ──────────────────────────────   │
│  🖌 Modo: [✋ Navegar] [▭ Desenhar]   │  18 campos  ✅ 15  🟡 2  🔴 1    │
│  [🗺️ Coverage Mode]                   │  Cobertura: 93%                   │
│                                        │  ──────────────────────────────   │
│   ┌────────────────────────────────┐  │                                   │
│   │                                │  │  NomeSegurado   → Texto      [✏️] │
│   │  São Paulo, 15 de Janeiro      │  │  DataNascimento  → 📅 Data   [✏️] │
│   │  de 2025                       │  │  Valor           → 💰 Moeda  [✏️] │
│   │                                │  │  Coberturas      → Lista     [✏️] │
│   │  Prezado(a) ┌─── ▭ ───────┐   │  │  Logradouro      → Texto     [✏️] │
│   │             │ Sônia Maria │   │  │  + 10 campos...   [Ver todos]     │
│   │  da Silva,  │ ←campo→     │   │  │                                   │
│   │             └─────────────┘   │  │  ⚠️ Precisamos da sua ajuda       │
│   │                                │  │  ──────────────────────────────   │
│   │  Motivo: Documentação          │  │  🟡 CPFSegurado                   │
│   │  incompleta                    │  │  "123.456.789-00"                 │
│   │                                │  │  Confiança: 62%                   │
│   │  ┌──── ▭ ─────────────────┐   │  │  ● CPFSegurado  ○ CPFSolicitante  │
│   │  │ 123.456.789-00  (🟡)   │   │  │              [Confirmar seleção]  │
│   │  └────────────────────────┘   │  │                                   │
│   │                                │  │  🔴 LinkDocumento                 │
│   │  ┌──── ▭ ─────── (🔴) ──┐   │  │  Não encontrado no PDF            │
│   │  │  ?  região não mapeada │   │  │  [▭ Desenhar região no PDF]       │
│   │  └───────────────────────┘   │  │  ou  [Marcar como opcional]       │
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

**Estado: operador desenha nova região para campo 🔴 não mapeado:**
```
│   ┌────────────────────────────────┐  │  🔴 LinkDocumento                 │
│   │                                │  │  Região selecionada:              │
│   │  ┌──── ▭ ── (desenhando) ──┐  │  │  bbox: [120, 450, 380, 470]       │
│   │  │ ╔═══════════════════════╗│  │  │  Texto detectado: "www.mongeral"  │
│   │  │ ║   ← arraste │ resize ║│  │  │                                   │
│   │  │ ╚═══════════════════════╝│  │  │  Vincular a: [LinkDocumento ▼]   │
│   │  └─────────────────────────┘  │  │           [✅ Confirmar vínculo]  │
│   └────────────────────────────────┘  │                                   │
```

**Estado: campo selecionado na lista destaca região no PDF:**
```
│   ┌────────────────────────────────┐  │                                   │
│   │  Prezado(a) ┌──── ▭ ─────┐   │  │  NomeSegurado  →  ✅ Texto   [✏️] │
│   │             │████████████│   │  │  ← selecionado (borda azul)       │
│   │  da Silva,  │ highlight  │   │  │     bbox: [150, 200, 400, 220]    │
│   │             └────────────┘   │  │     Confiança: 94%                │
│   └────────────────────────────────┘  │                                   │
```

**Anotações:**
- **Konva.js** fornece camada interativa sobre PDF.js: retângulos com handles de resize, drag, cores por status (verde=✅, amarelo=🟡, vermelho=🔴)
- Modo **Navegar** (padrão): clicar em região existente → seleciona campo na lista; clicar no campo na lista → destaca região no PDF
- Modo **Desenhar**: operador desenha retângulo sobre o PDF para mapear campo 🔴 não identificado → popup pede qual campo do XSD vincular
- Vision AI + pgvector fizeram o matching semântico dos campos do XSD com regiões do PDF — a tela exibe o resultado
- **Confiança** vem do semantic matching: ≥80% = ✅, 50-79% = 🟡, <50% ou não encontrado = 🔴
- Formato inferido pela Vision AI diretamente do texto do PDF: Texto, Data, Valor monetário, Lista, Combinação de campos
- "Confirmar ▶" habilitado assim que não houver 🔴 obrigatórios sem resolução
- "Voltar" retorna para Tela 1 (Upload) — exibe aviso: "Voltar ao upload descartará todo o mapeamento atual. Deseja continuar?"
- "Restaurar mapeamento" restaura todos os campos ao estado original da análise da IA sem reprocessar — exibe aviso: "Isso descartará todos os ajustes manuais feitos. Deseja continuar?"
- Da Tela 3, o operador pode voltar aqui para ajustar formatos sem perder o trabalho
- **Coverage Mode** (toggle [🗺️]): ativa overlay visual sobre o PDF — 🟢 Verde = elemento mapeado, 🔴 Vermelho = não mapeado, 🟡 Amarelo = detectado mas não confirmado. Exibe "Cobertura: 93%" no painel direito. Útil para identificar rapidamente áreas do PDF que faltam mapear.
- **Estabilidade** (multi-PDF): quando 3+ PDFs carregados, cada campo exibe badge de estabilidade — `STABLE` (presente em todos, mesma posição), `VARIABLE` (presente em todos, conteúdo muda), `OPTIONAL` (presente em alguns). Com 1 PDF, badges não aparecem.

**Estado: Coverage Mode ativado:**
```
│   ┌────────────────────────────────┐  │  📋 De-Para de Campos            │
│   │  [🗺️ Coverage Mode: ATIVO]     │  │  Cobertura: 93% (17/18 campos)  │
│   │                                │  │  ──────────────────────────────   │
│   │  ┌──── 🟢 ─────────────────┐  │  │  🟢 Mapeados: 15                │
│   │  │ São Paulo, 15 Janeiro   │  │  │  🟡 Não confirmados: 2           │
│   │  └─────────────────────────┘  │  │  🔴 Não mapeados: 1              │
│   │                                │  │                                   │
│   │  ┌──── 🟢 ──────┐            │  │                                   │
│   │  │ Sônia Maria  │            │  │                                   │
│   │  └──────────────┘            │  │                                   │
│   │                                │  │                                   │
│   │  ┌──── 🟡 ──────────────┐    │  │                                   │
│   │  │ 123.456.789-00 (62%) │    │  │                                   │
│   │  └──────────────────────┘    │  │                                   │
│   │                                │  │                                   │
│   │  ┌──── 🔴 ──────────────┐    │  │                                   │
│   │  │ ? (sem mapeamento)   │    │  │                                   │
│   │  └──────────────────────┘    │  │                                   │
│   └────────────────────────────────┘  │                                   │
```

---

## Tela 3 — Layout

> **Princípio:** O sistema resolve o máximo automaticamente. Todos os itens são revisáveis via [✏️]. Se não houver pendências, tela é ignorada e fluxo avança direto para Revisão.
>
> **O que é Layout:** decisões de nível de documento feitas **antes** de gerar o HTML — página, fontes a carregar, cabeçalho/rodapé, comportamento de seções dinâmicas, imagens, gráficos e **grid structure**. Se algo estiver errado estruturalmente na Tela 4, o ajuste vem aqui.
>
> **O que NÃO é Layout:** margem de um parágrafo, tamanho de fonte de um título, cor de um elemento — isso é CSS e fica na Tela 4.
>
> **Arquitetura v5.0:** Grid Detection (stage 3a) detectou a estrutura de colunas/rows e gerará CSS Grid em vez de `position:absolute`. Font Extraction (stage 2c) mapeou fontes do PDF para CSS equivalentes.

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
│  │                    │  │  📐 Grid Detectado                                │
│  │  Conteúdo fixo     │  │  ✅ 2 colunas × 3 rows (label + valor)    [✏️]  │
│  │                    │  │     CSS: grid-template-columns: 150px 1fr       │
│  │  ▓▓▓ Rodapé ▓▓▓▓  │  │  ✅ Tabela: 5 colunas (auto-fit)          [✏️]  │
│  └────────────────────┘  │                                                  │
│   A4 | Retrato           │  🔤 Fontes (extraídas do PDF → CSS)              │
│                          │  ✅ Helvetica-Bold → Arial, bold, 12px    [✏️]  │
│                          │     Origem: sentico.css                          │
│                          │  ✅ Helvetica → Arial, normal, 10px       [✏️]  │
│                          │     Origem: sentico.css                          │
│                          │  ⚠️ MontserratCustom — não encontrada            │
│                          │     Sugestão: Montserrat (Google Fonts 96%)      │
│                          │     ● Baixar auto  ○ Upload manual              │
│                          │     Salvar: ● Bibliotecas  ○ Só este template   │
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
- **Grid Detectado** (v5.0 stage 3a): Grid Detection analisou coordenadas X/Y e detectou estrutura de colunas/rows. O operador pode ajustar via [✏️] (ex: mudar de 2 para 3 colunas). CSS Grid é gerado em vez de `position:absolute` — melhor fidelidade e responsividade.
- **Fontes** (v5.0 stage 2c): Font Extraction mapeou cada fonte do PDF para CSS equivalente (family, size, weight). Exibe preview do mapeamento com origem do arquivo. Resolução do recurso (de onde carregar) — aplicação de estilo no CSS gerado
- "Avançar →" dispara geração do HTML/CSS/JS (stage 23: HTML + CSS Grid + Knockout) e vai para Tela 4
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
│  🎯 Confiança do Template: 94%   ██████████████████████░░  [Detalhes ▼]    │
│                                                                             │
│  ┌─── Detalhes (expandido) ─────────────────────────────────────────────┐  │
│  │  Layout Stability:    96%  ████████████████████░   (blocos estáveis) │  │
│  │  Anchor Detection:    98%  ████████████████████░   (labels corretos) │  │
│  │  Grid Quality:        91%  ██████████████████░░░   (CSS Grid gerado) │  │
│  │  Field Variability:   93%  ██████████████████░░░   (campos dinâmicos)│  │
│  │  Vision Agreement:    90%  █████████████████░░░░   (Vision Self-Check│  │
│  └──────────────────────────────────────────────────────────────────────┘  │
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
- **Template Confidence Score** (v5.0 stage 21 agregado): score composto por 5 fatores — Layout Stability, Anchor Detection, Grid Quality, Field Variability, Vision Agreement. [Detalhes ▼] expande para mostrar cada fator individualmente com barra de progresso.
- Níveis: 95-100% = auto-approved (verde), 80-95% = review recommended (amarelo), <80% = human review required (vermelho)
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
  ├── PDFs (1 obrigatório, 3-5 recomendado) + XSD (obrigatório)
  ├── Multi-PDF: ativa multi-example analysis, variant detection, stability classification
  ├── XSD define campos canônicos para data-bind no Knockout.js
  └── [Analisar Documento →]
        ↓
[⏳ Progress: Pipeline 23 stages em 8 blocos — Acquisition → Discovery → Intelligence → Tables → Semantics → Vision → Mapping → Generation]
        ↓
[2. Campos]
  ├── Vision AI + pgvector semantic matching pré-preenche mapeamento XSD → regiões PDF
  ├── Konva.js: anotação interativa sobre PDF.js — desenhar/redimensionar regiões
  ├── [🗺️ Coverage Mode]: overlay verde/vermelho/amarelo sobre PDF + score de cobertura
  ├── Com multi-PDF: badges de estabilidade (STABLE/VARIABLE/OPTIONAL) por campo
  ├── Resolver campos ambíguos (🟡) e não mapeados (🔴)
  ├── Elementos Especiais: decisão imagem fixa vs gráfico dinâmico
  ├── [💾 Salvar projeto] disponível no header
  └── [Confirmar ▶]
        ↓
[3. Layout]  ← ignorada automaticamente se não há decisões pendentes
  ├── Grid Detectado: colunas × rows → CSS Grid (editável)
  ├── Página: tamanho, orientação, margens
  ├── Fontes: PDF font → CSS mapping (family, size, weight) + catálogo
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
  ├── 🎯 Template Confidence Score (5 fatores: stability, anchors, grid, fields, vision)
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
- Upload Dropzone (Icon + Label + Button + Preview info + multi-file list)
- Field Status Item (Badge + Campo + Ação)
- Candidate Dropdown (Label + Select)
- Config Card (Header + Content + Action)
- Font Card (Preview Aa + Nome + Ação)
- Validation Item (Icon + Mensagem)
- File Tree Item (Ícone + Nome + Tamanho)
- Fidelidade Score Bar (Percentual + Barra + Comentário IA + Detalhes)
- Template Confidence Card (Score agregado + 5 fatores expandíveis)
- Coverage Score Badge (percentual + cor)
- Stability Badge (STABLE/VARIABLE/OPTIONAL)
- Grid Info Card (colunas × rows + CSS preview)
- Font Mapping Row (PDF font → CSS family + size + weight + origem)
- Depara Row (Campo PDF + seta + Binding)

### Organismos
- Wizard Progress Bar (5 Steps + Active indicator)
- Processing Progress Bar (Label + Bar + Percentual + Detalhe)
- Upload Panel (Dropzone multi-PDF + Dropzone XSD, ambos obrigatórios)
- Identification Panel (PDF.js + Konva.js annotation layer + Fields Panel bidirecional)
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
*v3 — Atualizado 2026-03-15: alinhado com Arquitetura v5.0 (Multi-PDF, Grid Detection, Font Extraction→CSS, Coverage Mode, Template Confidence Score, 23 stages/8 blocos)*
*Próximo passo: `*create-front-end-spec` para especificação técnica detalhada*
