# Relatorio de Debito Tecnico
**Projeto:** Migrador Planet Express
**Data:** 2026-04-09
**Versao:** 1.0

---

## Executive Summary (1 pagina max)

### Situacao Atual

O Migrador Planet Express e uma ferramenta interna que converte documentos PDF gerados pelo motor Planet Express em templates HTML reutilizaveis. Utilizado diariamente pelas equipes de operacoes, o sistema automatiza um processo que anteriormente era manual e propenso a erros -- upload do PDF, analise automatizada via inteligencia artificial, edicao visual no canvas interativo e exportacao do template final. A ferramenta opera com backend Python (FastAPI), frontend Vue 3, banco de dados PostgreSQL (Supabase) e cache Redis.

A avaliacao tecnica identificou **73 debitos tecnicos unicos** acumulados ao longo do desenvolvimento acelerado do produto. Destes, **6 sao criticos** e **19 de alta prioridade**, concentrados principalmente em seguranca de dados e infraestrutura de qualidade de codigo. O sistema funciona, mas opera sem protecoes fundamentais: qualquer usuario autenticado pode acessar, modificar ou deletar dados de outros usuarios; dependencias de terceiros estao desatualizadas e sem patches de seguranca; e nao ha verificacoes automaticas de qualidade no codigo.

Ignorar esses debitos nao significa que o sistema para de funcionar hoje -- significa que cada dia que passa aumenta a probabilidade de um incidente de seguranca, perda de dados ou falha silenciosa que comprometa a confianca dos usuarios e a capacidade da equipe de evoluir o produto. O custo de resolver agora e previsivel e controlado; o custo de resolver apos um incidente e exponencialmente maior.

### Numeros Chave

| Metrica | Valor |
|---------|-------|
| Total de Debitos | 73 |
| Debitos Criticos | 6 |
| Debitos Alta Prioridade | 19 |
| Debitos Medio/Baixo | 48 |
| Esforco Total Estimado | ~297 horas |
| Esforco Efetivo (excluindo deferidos) | ~215 horas |
| Custo Estimado (R$150/h) | R$ 32.250 |
| Areas Afetadas | 9 (Sistema, DB, Redis, Frontend, UX, Acessibilidade, Seguranca, Performance, Testes) |

### Recomendacao

Recomendamos fortemente a aprovacao de um investimento de **R$ 32.250** (215 horas de trabalho) distribuido em **4 ondas ao longo de 8-12 semanas**. A primeira onda (R$ 4.275, 1 semana) elimina vulnerabilidades criticas de seguranca e riscos de perda de dados. Adiar essa primeira onda expoe a organizacao a um risco de exposicao de dados avaliado em ate R$ 150.000 em custos de resposta a incidente, sem contar danos reputacionais. O retorno sobre o investimento e claro: por cada R$ 1 investido agora, evitam-se ate R$ 5 em custos futuros de correcao emergencial, retrabalho e perda de produtividade.

---

## Analise de Custos

### Custo de RESOLVER

| Categoria | Horas | Custo (R$150/h) |
|-----------|-------|-----------------|
| Seguranca e Acesso a Dados | 28,5h | R$ 4.275 |
| Infraestrutura de Qualidade (linters, hooks, deps) | 24h | R$ 3.600 |
| Protecoes do Frontend (erros, acessibilidade) | 14h | R$ 2.100 |
| Refatoracao de Componentes Centrais | 46h | R$ 6.900 |
| Testes, Performance e Polimento | 47h | R$ 7.050 |
| Itens Deferidos (baixa prioridade) | 82h | R$ 12.300 |
| **TOTAL (efetivo, sem deferidos)** | **215h** | **R$ 32.250** |
| **TOTAL (com deferidos)** | **297h** | **R$ 44.550** |

### Custo de NAO RESOLVER (Risco Acumulado)

| Risco | Probabilidade | Impacto | Custo Potencial |
|-------|---------------|---------|-----------------|
| **Exposicao de dados entre usuarios** -- Qualquer usuario autenticado acessa dados de todos os outros (RLS aberta, sem isolamento por usuario) | Alta (70%) | Critico | R$ 100.000 - R$ 200.000 (resposta a incidente, notificacoes, compliance, retrabalho) |
| **Vulnerabilidade de seguranca explorada** -- Dependencias com patches nao aplicados (32MB vendoradas), XSS no frontend, headers de seguranca ausentes | Media (40%) | Alto | R$ 50.000 - R$ 100.000 (investigacao, correcao emergencial, downtime) |
| **Perda de dados por falha silenciosa** -- Jobs ficam em estado "fantasma" apos restart; limpeza de arquivos incompleta; resultados sobrescrevem cancelamentos | Media (35%) | Medio | R$ 20.000 - R$ 40.000 (recuperacao manual, reprocessamento, perda de confianca) |
| **Queda de produtividade da equipe** -- Sem linting, sem testes E2E, sem verificacoes automaticas; cada nova funcionalidade demora mais e tem mais bugs | Alta (80%) | Medio | R$ 30.000 - R$ 60.000/ano (velocidade reduzida em ~25%, retrabalho recorrente) |
| **Abandono do sistema pelos usuarios** -- Tela branca em erros, perda de trabalho nao salvo, interface inconsistente entre sistemas operacionais | Baixa (20%) | Alto | R$ 40.000 - R$ 80.000 (retorno ao processo manual, retreinamento, ferramenta alternativa) |
| **EXPOSICAO TOTAL ESTIMADA** | | | **R$ 150.000 - R$ 350.000/ano** |

---

## Impacto no Negocio

### Seguranca

O sistema apresenta **11 debitos de seguranca**, cobrindo 7 das 10 categorias OWASP Top 10. Os mais graves:

- **Isolamento de dados inexistente:** Todas as tabelas do banco de dados tem politicas de acesso configuradas como "qualquer um pode tudo". Nao existe separacao por usuario. Na pratica, qualquer pessoa com acesso ao sistema pode ver, editar ou apagar o trabalho de outros. Isso afeta 100% dos dados armazenados.
- **Chave administrativa exposta:** O backend usa uma chave com privilegios totais para todas as operacoes, inclusive as que nao precisam. Se essa chave vazar, o atacante tem acesso irrestrito a todos os dados e arquivos.
- **Componentes desatualizados:** 32MB de bibliotecas de terceiros estao copiadas dentro do projeto sem receber atualizacoes de seguranca. O servidor de desenvolvimento tem uma vulnerabilidade conhecida de travessia de caminho.

**Custo de correcao: R$ 4.275 (28,5h) | Custo de incidente: R$ 100.000+**

### Confiabilidade

O sistema armazena o estado dos trabalhos em **3 locais diferentes** (memoria, Redis, banco de dados) sem garantia de sincronizacao. Isso significa:

- **Jobs fantasmas:** Apos um reinicio do servidor, trabalhos que estavam em andamento ficam presos em estado "executando" para sempre. A funcao de recuperacao existe no codigo mas nunca e chamada.
- **Sobrescrita silenciosa:** Um trabalho cancelado pelo usuario pode ter seu resultado sobrescrito para "concluido" sem aviso, gerando confusao sobre o estado real.
- **Limpeza incompleta:** Ao deletar um trabalho, arquivos em subdiretorios (PDFs, screenshots, thumbnails) ficam orfaos no armazenamento, consumindo espaco indefinidamente.

**Custo de correcao: R$ 1.200 (8h para mitigacao imediata) | Risco: perda de dados e inconsistencia crescente**

### Produtividade da Equipe

A ausencia de ferramentas automaticas de qualidade impacta diretamente a velocidade de desenvolvimento:

- **Sem verificacao automatica de codigo:** Nenhum linter ou formatador configurado (Python ou JavaScript). Cada desenvolvedor segue seu proprio estilo, gerando inconsistencias e bugs sutis.
- **80 pontos de "qualquer tipo vale"** no TypeScript -- locais onde o compilador nao verifica tipos, permitindo erros que so aparecem em producao.
- **Sem testes automatizados de ponta a ponta:** O fluxo critico (Upload, Analise, Edicao, Exportacao) nunca foi testado de forma automatizada num navegador real.
- **Arquivos monoliticos:** Componentes centrais com 900-2.000 linhas de codigo misturam multiplas responsabilidades, tornando qualquer alteracao arriscada e demorada.

**Estimativa de impacto:** Cada nova funcionalidade leva ~25% mais tempo do que deveria. Em um ano com 10 funcionalidades significativas, isso equivale a ~250h de retrabalho evitavel (R$ 37.500).

### Experiencia do Usuario

Os usuarios enfrentam problemas que afetam diretamente sua confianca no sistema:

- **Tela branca sem explicacao:** Quando ocorre um erro nao tratado, o sistema simplesmente para de funcionar sem mostrar nenhuma mensagem. O usuario nao sabe se perdeu seus dados ou o que fazer.
- **Perda de trabalho nao salvo:** Nao existe confirmacao ao sair da pagina com alteracoes pendentes. Um clique acidental no botao "voltar" ou fechamento da aba perde todo o trabalho em andamento.
- **Icones inconsistentes:** O toolbar usa emojis que renderizam de forma diferente em Windows, Mac e Linux, dando aparencia amadora e causando confusao.
- **Acessibilidade limitada:** Modais nao prendem o foco do teclado (violacao de padrao WCAG 2.1), contraste insuficiente em textos secundarios, e imagens sem descricao alternativa.
- **Sem feedback de progresso:** Exportacao de templates nao mostra nenhum indicador de carregamento -- o usuario clica e nao sabe se funcionou ate o download iniciar.

**Custo de correcao: R$ 2.100 (14h) para protecoes essenciais | Impacto: confianca e retencao de usuarios**

---

## Timeline Recomendado

### Wave 1: Quick Wins + Seguranca (1 semana) -- R$ 4.275

Itens de baixo esforco e alto impacto que eliminam os riscos mais graves imediatamente.

| Item | Descricao em linguagem de negocio | Horas |
|------|-----------------------------------|-------|
| Protecao contra bypass de autenticacao | Impedir que modo de teste seja ativado acidentalmente em producao | 0,5h |
| Recuperacao de trabalhos apos reinicio | Ativar funcao existente que recupera jobs interrompidos | 0,5h |
| Correcao de vulnerabilidade do servidor | Aplicar patch de seguranca ja disponivel | 0,5h |
| Rastreamento de alteracoes em jobs | Garantir que a data de atualizacao e registrada automaticamente | 1h |
| Validacao de status de trabalhos | Impedir que valores invalidos sejam gravados no banco | 1h |
| Criacao automatica de armazenamento | Configurar buckets de arquivos nas migracoes do banco | 1h |
| Protecao contra injecao de codigo (XSS) | Sanitizar conteudo HTML exibido na biblioteca de componentes | 2h |
| **Isolamento de dados por usuario** | Adicionar identificacao de proprietario a todos os registros | 12h |
| Controle de acesso baseado em proprietario | Restringir leitura/escrita apenas aos dados do proprio usuario | 4h |
| Separacao de credenciais administrativas | Usar chave administrativa apenas onde estritamente necessario | 4h |
| Cabecalhos de seguranca HTTP | Adicionar protecoes padrao contra ataques comuns (CSP, HSTS) | 2h |

### Wave 2: Infraestrutura de Qualidade (2-3 semanas) -- R$ 3.600

Estabelecer verificacoes automaticas que previnem a entrada de novos debitos.

| Item | Descricao em linguagem de negocio | Horas |
|------|-----------------------------------|-------|
| Remocao de bibliotecas embutidas | Usar gerenciador de pacotes padrao para receber atualizacoes de seguranca | 4h |
| Verificacao automatica de codigo Python | Detectar erros e inconsistencias automaticamente no backend | 4h |
| Verificacao automatica de codigo Frontend | Detectar erros e inconsistencias automaticamente na interface | 4h |
| Verificacoes pre-envio de codigo | Bloquear envio de codigo que nao passa nas verificacoes | 2h |
| Eliminacao de brechas de tipo no Frontend | Reduzir de 80 para menos de 20 os pontos sem verificacao de tipo | 6h |
| Registro de operacoes privilegiadas | Rastrear quem fez o que para fins de auditoria e investigacao | 4h |

### Wave 3: Protecoes e Refatoracao (3-4 semanas) -- R$ 9.000

Proteger o usuario contra erros e depois simplificar componentes complexos.

| Item | Descricao em linguagem de negocio | Horas |
|------|-----------------------------------|-------|
| Tela de erro amigavel | Mostrar mensagem clara em vez de tela branca quando algo falha | 4h |
| Confirmacao de saida com trabalho pendente | Perguntar antes de fechar a pagina se ha alteracoes nao salvas | 2h |
| Navegacao por teclado em dialogos | Garantir que modais funcionem corretamente para usuarios de teclado | 4h |
| Sistema de notificacoes global | Centralizar mensagens de sucesso, erro e aviso para o usuario | 3h |
| Correcao de contraste de texto | Ajustar cores para atender padrao de acessibilidade WCAG AA | 1h |
| Simplificacao de componentes centrais | Decompor 3 componentes de 900-1.200 linhas em modulos menores | 18h |
| Tipagem do pipeline de processamento | Garantir contratos formais entre as etapas do processamento de PDF | 12h |
| Unificacao do armazenamento de estado | Eliminar inconsistencias entre os 3 locais onde o estado e gravado | 8h |
| Operacoes assincronas no banco | Eliminar bloqueios no processamento simultaneo de requisicoes | 9h |

### Wave 4: Testes e Polimento (2-3 semanas) -- R$ 7.050

Garantir qualidade de longo prazo e polimento da experiencia do usuario.

| Item | Descricao em linguagem de negocio | Horas |
|------|-----------------------------------|-------|
| Testes automatizados de ponta a ponta | Simular o fluxo completo do usuario em navegador real | 16h |
| Icones profissionais | Substituir emojis por icones consistentes em todos os sistemas | 2h |
| Indicador de progresso na exportacao | Mostrar feedback visual durante a geracao do template | 2h |
| Unificacao de cores e estilos | Garantir consistencia visual em todo o sistema | 2h |
| Indicadores de foco acessiveis | Melhorar visibilidade da navegacao por teclado | 3h |
| Otimizacao de desfazer/refazer | Eliminar travamentos ao usar desfazer em documentos grandes | 6h |
| Testes de componentes visuais | Cobrir componentes mais usados com testes automatizados | 18h |

---

## ROI da Resolucao

| Investimento | Retorno Esperado |
|--------------|------------------|
| **R$ 4.275** (Wave 1 -- Seguranca) | Eliminacao de risco de exposicao de dados avaliado em R$ 100.000-200.000. **ROI: 23x-47x** |
| **R$ 3.600** (Wave 2 -- Qualidade) | Reducao de 25% no tempo de desenvolvimento de novas funcionalidades. Em 12 meses com equipe de 2 devs: economia de ~R$ 37.500/ano. **ROI: 10x no primeiro ano** |
| **R$ 2.100** (Wave 3A -- Protecoes UX) | Eliminacao de perda de trabalho do usuario e telas brancas. Reducao estimada de 40% em chamados de suporte relacionados a erros. **ROI: 3x-5x** |
| **R$ 15.225** (Waves 3B-4 -- Refatoracao e Testes) | Reducao de 50% no tempo de correcao de bugs. Base de testes E2E previne regressoes. Componentes menores permitem onboarding 2x mais rapido. **ROI: 2x-3x em 18 meses** |
| **TOTAL: R$ 32.250** | **Economia projetada: R$ 80.000-150.000 em 18 meses. ROI medio: 3x-5x** |

**Nota sobre custo de inacao:** Cada mes sem resolver a Wave 1 (seguranca) e um mes com exposicao total de dados. Se um incidente ocorrer antes da correcao, o custo de resposta emergencial e tipicamente 3-5x maior do que a correcao planejada, alem de custos intangiveis (confianca, reputacao, moral da equipe).

---

## Proximos Passos

1. [ ] **Aprovar investimento da Wave 1** (R$ 4.275, 28,5h) -- correcoes criticas de seguranca
2. [ ] **Alocar desenvolvedor(es)** para a Wave 1 na proxima sprint
3. [ ] **Executar Wave 1** -- priorizar DB-012 e DB-016 (quick wins, 1h total) seguidos de DB-002 (isolamento de dados, 12h)
4. [ ] **Validar seguranca pos-Wave 1** -- testar isolamento de dados entre usuarios e headers de seguranca
5. [ ] **Aprovar investimento das Waves 2-4** (R$ 27.975) com base nos resultados da Wave 1
6. [ ] **Habilitar Dependabot no GitHub** (30 minutos) -- quick win para monitoramento continuo de vulnerabilidades
7. [ ] **Estabelecer metricas de acompanhamento** -- velocidade de entrega, taxa de bugs, tempo de resposta a incidentes
8. [ ] **Revisao trimestral** -- reavaliar debitos deferidos (82h, R$ 12.300) conforme evolucao do produto

---

## Anexos

- [Avaliacao Tecnica Completa (73 debitos detalhados)](../prd/technical-debt-assessment.md)
- [8 Padroes Cross-Cutting identificados (CC-001 a CC-008)](../prd/technical-debt-assessment.md#2-cross-cutting-debts)
- [Visao Consolidada de Seguranca (OWASP Top 10)](../prd/technical-debt-assessment.md#3-security-consolidated-view)
- [Grafo de Dependencias entre Debitos](../prd/technical-debt-assessment.md#7-dependencias-entre-debitos)
- [5 Gaps Adicionais identificados por QA](../prd/technical-debt-assessment.md#4-gaps-adicionais-identificados-por-qa)
