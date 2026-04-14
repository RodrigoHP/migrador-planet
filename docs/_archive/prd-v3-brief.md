# PRD v3.0 — Brief de Atualização

## Contexto
O wireframe mid-fi evoluiu de v5 para v5.3, mudando o paradigma de "wizard 5 telas separadas" para "editor unificado com 5 regiões". O PRD v2.3 está desatualizado em relação ao wireframe.

**Input primário:** `docs/wireframes/wireframes-mid-fi.md` (v5.3)
**Referência:** `docs/prd-v2.3-archived.md` (FRs que não mudaram)

---

## Deltas: PRD v2.3 → Wireframe v5.3

### MUDANÇAS ESTRUTURAIS (reescrever)

1. **Modelo de navegação:** Wizard 5 telas → Editor unificado com 5 regiões (toolbar, painel esquerdo 2 abas, centro 4 abas, inspetor hierárquico, painel inferior 2 abas). Tela Home e Tela Upload permanecem como telas separadas. Tela de Progresso (Analyzing) é tela intermediária. Editor é destino final.

2. **Tela de Exportar removida:** Tela 5 (score + árvore + preview + botões) → botão "Exportar" na toolbar do editor gera ZIP direto. Preview = Canvas HTML (já é WYSIWYG).

3. **Preview side-by-side (FR7):** Não é mais "PDF esquerda, HTML direita" como layout fixo. Agora são 4 abas centrais: Canvas HTML, PDF Referência, Código (Monaco), Sincronizar (split view). Sync View é o equivalente moderno do side-by-side.

4. **Layout Types:** Conceito novo. PDFs grandes são clusterizados por similaridade de layout. Operador edita um template por Layout Type. Seletor na toolbar. Confiança e Cobertura são por Layout Type.

5. **Árvore de Estrutura:** Painel esquerdo com hierarquia Document > Header > Flow > Footer > elementos. Principal superfície de edição estrutural.

6. **Inspetor Hierárquico (4 níveis):** Página > Seção > Componente > Elemento. Cada nível com propriedades específicas.

7. **Tela de Progresso (Analyzing):** Tela dedicada entre Upload e Editor. Pipeline 8 blocos / 23 estágios. Sem Canvas parcial. Auto-navega para Editor ao concluir.

### FUNCIONALIDADES NOVAS (adicionar FRs)

8. **Sistema de Cobertura:** Percentual de elementos mapeados vs detectados. Popover com breakdown por tipo (campos, tabelas, imagens, gráficos). Thresholds: ≥95% completo, 80-95% revisão, <80% incompleto. Modo Cobertura (toggle): verde/vermelho no Canvas e PDF. Cálculo ponderado. Por Layout Type. Atualiza em tempo real.

9. **Confiança expandida:** Popover com 5 fatores (estabilidade layout, detecção âncoras, qualidade grid, variabilidade campos, concordância visão). Thresholds: ≥95% aprovado, 80-95% revisão, <80% revisão humana. Expande FR33.

10. **Editor de Código como aba:** Monaco Editor multi-arquivo (index.html, style.css, base.js). File Explorer no painel esquerdo. Erros inline. Avisos em áreas críticas (header/footer/flow). Sincronização bidirecional com Canvas. Expande FR24.

11. **Sync View:** Aba "Sincronizar" no centro. Split Canvas + PDF lado a lado. Scroll sincronizado. Seleção sincronizada (clicar Canvas destaca bounding box no PDF). Âncoras de layout como marcadores. Zoom independente.

12. **Área de Testes:** Painel inferior com 2 abas (Dados de Teste + Relatório). Gestão de datasets (upload XML/JSON, validação contra XSD, seleção de ativo). Gerador de dados sintéticos (small/medium/large a partir do XSD). Auto Test Mode. Relatório com tabela resumo + matriz cobertura por elemento. Limite MVP: 5 datasets. Datasets incluídos opcionalmente no Export.

13. **Analisador Multi-Documento:** Upload de múltiplos PDFs. Matriz de Variação (campo × documento → ✔/✖). Detecção automática: campos obrigatórios, opcionais, seções condicionais.

14. **Modo Diff:** Comparação entre documentos por Layout Type. Páginas representativas lado a lado. Destaque: verde (igual), amarelo (diferente), vermelho (novo/ausente).

### CONCEITOS ALTERADOS

15. **Console removido:** Feedback do sistema agora é contextual — badges na Árvore de Estrutura, overlays no Canvas (modo cobertura), avisos inline no Inspetor, toast temporários. Sem console dedicado.

16. **Upload de dados XML/JSON:** PRD v2.3 removeu (FR2a). Wireframe v5.3 restaurou como **opcional** (terceira dropzone). Dados reais melhoram detecção de tipos e servem de exemplo. Reavaliar FR2a.

17. **Fonte de verdade:** Stores Pinia (não template.json). template.json é apenas para Save/Export.

18. **Paginação:** Layout Engine no editor calcula paginação. PDF engine só renderiza HTML pré-paginado. Canvas simula paginação = mesmo engine do export. Algoritmo: remainingSpace = bodyHeight - headerHeight - footerHeight; elementos sequenciais; page break quando não cabe. Tabelas quebram por linhas com cabeçalho repetido.

### FRs QUE NÃO MUDARAM (manter do v2.3)

- FR3, FR4, FR5, FR6 — Motor de matching (extrair, matching IA, múltiplos candidatos, desnormalização)
- FR9 — Condicionais (ko if)
- FR10 — Salvar/retomar projeto .json
- FR11 — Fixos vs dinâmicos
- FR16, FR17, FR18, FR19, FR20 — Geração do output (index.html, style.css, base.js, exemplo.js, ZIP)
- FR21 — Format strings customizados
- FR22 — Tamanho de página
- FR26 — Gráficos (detecção, Chart.js, imagem fixa vs dinâmico)
- FR27, FR27a — Fontes e Bibliotecas
- FR30 — Tematização condicional
- FR31 — Código de barras
- FR32 — SVG inline
- FR33 — Score de fidelidade (expandir com popover de 5 fatores)
- FR34 — Auto-correção IA (expandir com aceitar/rejeitar por sugestão)
- NFR1-NFR7 — Manter

### ESCOPO MVP DO WIREFRAME

- ✔ Cobertura: percentual + popover + modo cobertura + por Layout Type
- ✖ Cobertura: por zona, histórico, analytics
- ✔ Área de Testes: datasets + validação + sintético + relatório (máx 5)
- ✖ Área de Testes: Coverage Diff visual no Canvas por dataset (futuro)
- ✔ Editor de Código: editar arquivos existentes
- ✖ Editor de Código: criar/deletar/renomear arquivos
