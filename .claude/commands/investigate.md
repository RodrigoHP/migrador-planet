# /investigate — Root Cause Analysis & Exploratory Investigation

> Metodologia de investigacao profunda de bugs e problemas.
> Portavel: funciona com qualquer LLM (Claude, GPT, Gemini, Codex, Cursor).
> Copie este arquivo para qualquer projeto.

## Principio

**Nunca aplique band-aid.** Todo problema eh investigado ate a origem. Um guard defensivo eh protecao adicional, nunca o fix principal. Cada bug eh uma oportunidade de melhoria — a investigacao sempre produz mais do que entrou.

---

## Como Usar

Forneça um ou mais indicios de erro (screenshot, log, stack trace, descricao) e diga `/investigate` ou "investigue este problema".

---

## Fase 1 — Triagem & Compreensao

**Objetivo:** Entender o que aconteceu e onde.

1. **Reproduzir mentalmente** — Ler o stack trace/log/screenshot. Identificar o ponto exato do crash ou comportamento incorreto.
2. **Mapear o fluxo de dados** — De onde vem o dado que causou o erro? Quem gerou? Quem transformou? Quem consumiu?
3. **Perguntar se falta contexto** — SE voce nao tem informacao suficiente para entender a origem, PERGUNTE ao usuario. Nao assuma. Nao invente. Exemplos:
   - "Qual PDF/input causou esse erro?"
   - "Isso acontece sempre ou so com inputs especificos?"
   - "Houve alguma mudanca recente nessa area?"
4. **Classificar** — O problema eh:
   - **Isolado** — causa clara, ponto unico
   - **Sistemico** — mesmo padrao pode existir em outros lugares
   - **Estrutural** — indica problema de design/arquitetura

**Output da Fase 1:** Declaracao clara do problema + classificacao + mapa do fluxo de dados.

---

## Fase 2 — Investigacao da Origem (Root Cause)

**Objetivo:** Encontrar a causa raiz, nao o sintoma.

1. **Aplicar 5 Whys** — Pergunte "por que?" ate chegar na raiz:
   ```
   Por que crashou? → Porque .get() foi chamado em objeto que era lista
   Por que era lista? → Porque o modulo anterior gerou lista em vez de dict
   Por que gerou lista? → Porque o parser nao normaliza o output
   Por que nao normaliza? → Porque nao existe contrato de output definido
   Por que nao existe contrato? → Decisao de design nao tomada
   ```
2. **Ler o codigo fonte** — Nao confie em suposicoes. Leia o codigo que gera o dado problemático. Leia o codigo que consome. Entenda o contrato implicito.
3. **Verificar docs do projeto** — Existem convencoes, contratos, ou regras que deveriam prevenir isso? Consulte documentacao de arquitetura, contratos entre modulos, e regras do projeto.
4. **Verificar testes existentes** — Existe teste que deveria ter pego isso? Se sim, por que nao pegou? Se nao, isso eh um gap.
5. **Perguntar se necessario** — Se durante a investigacao surgir duvida sobre intencao de design ou comportamento esperado, PERGUNTE ao usuario.

**Output da Fase 2:** Root cause statement claro + evidencia no codigo + por que nao foi pego antes.

---

## Fase 3 — Exploracao Proativa

**Objetivo:** Enquanto investiga, buscar problemas colaterais e oportunidades de melhoria.

1. **Buscar irmaos** — O mesmo padrao problematico existe em outros lugares? Grep/busque no codebase.
2. **Verificar consumidores** — Outros modulos consomem o mesmo dado? Eles tambem sao vulneraveis?
3. **Avaliar cobertura** — As areas afetadas tem testes? Os testes cobrem o cenario que falhou?
4. **Identificar melhorias** — Durante a exploracao, anotar:
   - Codigo que poderia ser mais robusto
   - Contratos implicitos que deveriam ser explicitos
   - Validacoes que faltam nas fronteiras entre modulos
   - Padroes repetidos que poderiam ser abstraidos
5. **Avaliar se eh estrutural** — Se o problema indica falha de design (nao apenas de implementacao), marcar para escalacao arquitetural.

**Output da Fase 3:** Lista de achados colaterais (problemas + melhorias), cada um com localizacao e severidade.

---

## Fase 4 — Solucao

**Objetivo:** Resolver na origem e proteger nos pontos de consumo.

1. **Fix principal** — Corrigir na ORIGEM do dado (onde eh gerado/transformado incorretamente).
2. **Guards defensivos** — Adicionar protecao nos consumidores como camada ADICIONAL (nunca como unico fix).
3. **Testes (OBRIGATORIO)** — Para CADA fix:
   - Teste que reproduz o bug original (DEVE existir, sem excecao)
   - Teste que valida o contrato na origem
   - Testes de regressao para cenarios relacionados
   - SE nao eh possivel testar automaticamente (ex: fix puramente visual), documentar o motivo no relatorio
4. **Validar** — Rodar todos os testes existentes + novos. Zero regressao.

**IMPORTANTE:** Um fix sem teste nao esta completo. Testes sao parte da solucao, nao um passo separado.

**Output da Fase 4:** Codigo implementado + testes + validacao.

---

## Fase 5 — Documentacao & Backlog

**Objetivo:** Documentar tudo para que o conhecimento nao se perca.

### Documentacao de Bugs — Abordagem Hibrida

Antes de produzir o relatorio, classificar cada bug fixado:

| Classificacao | Criterio | Acao |
|--------------|----------|------|
| **Trivial** | 1 arquivo, 1 linha | Sem story. Documentar no relatorio. |
| **Minor** | 1-2 arquivos, fix comportamental | Story retroativa status=Done. |
| **Significativo** | >2 arquivos, muda comportamento | Story criada ANTES do fix (na Fase 4). |

Se multiplos bugs significativos da mesma investigacao: 1 story umbrella com cada bug como AC.

### Relatorio de Investigacao

Produzir um **Relatorio de Investigacao** com:

### 1. Problema Original
- O que foi reportado
- Stack trace / evidencia

### 2. Root Cause
- Causa raiz identificada (com 5 Whys)
- Onde no codigo (arquivo:linha)
- Por que nao foi detectado antes

### 3. Fix Aplicado
- O que foi corrigido na origem
- Guards defensivos adicionados

### 4. Testes Criados (OBRIGATORIO)
Listar cada arquivo de teste criado e o que ele valida:
- `test_file.spec.ts` — Valida que {cenario}
- SE zero testes foram criados: justificativa explicita (ex: "fix puramente visual, nao testavel automaticamente")

### 5. Achados Colaterais (Backlog)
Para cada achado durante a exploracao:

| ID | Tipo | Severidade | Descricao | Localizacao | Acao Sugerida |
|----|------|-----------|-----------|-------------|---------------|
| F-1 | Bug | CRITICAL | ... | arquivo:linha | ... |
| F-2 | Melhoria | MEDIUM | ... | arquivo:linha | ... |
| F-3 | Debt | LOW | ... | arquivo:linha | ... |

### 6. Anti-Pattern Registrado
SE o arquivo `docs/qa/known-anti-patterns.md` existir no projeto, registrar o padrao encontrado:
- ID: AP-{next_id}
- Descricao do padrao problematico
- Regex/grep para buscar no codebase
- Guard esperado
- Severidade
SE o padrao ja existe no registry, apenas adicionar a referencia desta RCA.

### 7. Recomendacoes
- Contratos que deveriam ser formalizados
- Mudancas arquiteturais sugeridas (se aplicavel)

---

## Comportamentos Obrigatorios

Estes comportamentos se aplicam durante TODA a investigacao:

- **PERGUNTE** quando falta informacao — nunca assuma
- **LEIA** o codigo antes de propor solucao — nunca adivinhe
- **BUSQUE** padroes similares no codebase — nunca trate como caso isolado sem verificar
- **DOCUMENTE** achados colaterais durante a exploracao — nunca descarte
- **TESTE** cada fix com teste automatizado — nunca confie em validacao manual
- **ESCALE** se encontrar problema estrutural/arquitetural — nunca ignore
- **CONSULTE** docs do projeto para convencoes existentes — nunca reinvente

---

## Integracao AIOS (opcional)

> Ignore esta secao se nao estiver usando o framework AIOS.
> v3.0: Single executor — o agente que invoca o workflow executa tudo. Escalacoes sao opcionais.

- O executor roda todo o fluxo (triagem → fix → testes → docs → push)
- Escalar problemas estruturais para `@architect` (somente se problema de design identificado)
- Criar stories de backlog para achados colaterais + gerar handoff artifact para o SDC
- Usar `@devops *push` para push (unico agente autorizado para remote)
- Atualizar story file com resultados da investigacao no Change Log
