# Handoff — Stage 4 Field Mapping: O Que Foi Feito, o Problema Real e Onde Queremos Chegar

**Data:** 2026-04-26  
**Para:** Próximo agente (Architect, Analyst ou novo Dev) que vai repensar o Pilar B  
**Autor:** Equipe Epic 48  

---

## 1. Contexto do Produto (leia primeiro)

O Migrador Planet **não extrai dados de PDFs**. Ele cria **templates reutilizáveis**.

O usuário sobe 3+ PDFs de exemplo do mesmo tipo de documento → o pipeline detecta quais campos mudam entre instâncias (dinâmicos) e quais são fixos → gera um template HTML com placeholders `{{campo}}` mapeados para um XSD → esse template é usado depois para gerar documentos preenchidos com dados reais.

**O entregável é o template, não os dados.**

```
PDF₁  ┐
PDF₂  ├─→ Pipeline → Template HTML com {{ClienteTelefone}}, {{NomeCliente}}, etc.
PDF₃  ┘              + Mapeamento: campo_visual → XSD path
```

O XSD é o schema de dados que o motor Planet Express usa para preencher os templates. É fixo por tipo de documento.

---

## 2. O Que o Stage 4 Precisa Fazer

Dado um par `(label, value)` extraído do PDF pelo Stage 3, descobrir qual campo do XSD esse par representa.

```
label = "TELEFONE",  value = "(19) 98189-4732"  →  Propostas.Propostas.ClienteTelefone
label = "Benefício",  value = "608.882,69"       →  Propostas.Propostas.DadosSeguros.DadosSeguros.ValorBeneficio
label = "(R$)",       value = "368,95"            →  ???  ← este é o problema
```

O XSD do documento testado (PosicaoConsolidada) tem **68 paths**. O pipeline extrai ~25 pares dinâmicos por documento. O Stage 4 tem que casar cada par com o path correto.

---

## 3. O Que Foi Feito (Histórico Completo)

### Abordagem escolhida

Enviar os pares ao LLM Gemini Flash com o contexto da seção e a lista de paths XSD candidatos. O LLM retorna um score por candidato. O par é mapeado ao path com maior score acima de um threshold.

```
pairs_json + scoped_xsd_paths → Gemini Flash → {pair_index: [{path, score}]}
```

### Root Causes identificados e corrigidos (RC-A → RC-I)

| RC | Problema | Fix | Story |
|----|----------|-----|-------|
| RC-A | Body text ("0800 771 5472") chegava ao LLM e roubava `ClienteTelefone` | `_is_body_text_pair()` ativada para filtrar texto corrido | 48.21 |
| RC-B | Seções recebiam 4 paths errados em vez de 68 | `SECTION_MATCH_MIN_SCORE` 0.3 → 0.65 | 48.20 |
| RC-C | Mesmo path XSD atribuído a múltiplos layouts | `used_paths` movido para fora do loop de layout | 48.13 |
| RC-D | Pares inline chegavam sem `label_text` separado | Stage 4 passou a ler nós `field/label/value` do document tree | 48.17 |
| RC-F | Seção matchava nó XSD wrapper, filhos eram complexos (não folhas) | `_expand_child_paths()` para expandir wrappers até folhas reais | 48.18 |
| RC-G | Índice local do LLM (0,1,2...) colidiia com `original_index` entre seções | `_local_idx_map` remap posição LLM → original_index | 48.19 |
| RC-H | Section scoping recebia paths de seção XSD errada | Mesmo fix que RC-B (manifestação diferente do mesmo problema) | 48.20 |
| RC-I | INSCRIÇÃO→ClienteCpf, 368,95→ValorIOF, body text→ClienteTelefone | Constraints no prompt + filtro body text | 48.21 |

### Evolução da métrica scalar_coverage

| Momento | Coverage | Observação |
|---------|----------|-----------|
| Início Epic 48 | ~0.31 | Muitos bugs empilhados |
| Após RC-C + RC-D | ~0.53 | Dedup + inline pairs |
| Após RC-F | ~0.64 | Wrapper expansion |
| Após RC-G | ~0.64 | Index collision corrigido |
| Após RC-H | **0.84** | Threshold section match corrigido — melhor resultado |
| Após RC-I (precisão) | 0.76 | Tradeoff: removeu 3 false positives, perdeu 2 mapeamentos |

### Estado atual (último E2E — job `3b57c785`, 2026-04-26)

- **scalar_coverage = 0.76 (19/25)** — abaixo do gate 0.80
- 5/5 stages técnicos funcionam (clustering, estrutura, HTML gerado)
- O Stage 5 gera HTML com `<repeat>` e `{{campos}}` — esse parte está OK
- O problema está em QUANTOS e QUAIS campos chegam mapeados ao Stage 5

**Campos mapeados corretamente (determinísticos, nunca erram):**

| Campo | Label/Sinal | XSD Path |
|-------|-------------|----------|
| CEP | formato cep | `CEP` |
| Telefone | label "TELEFONE" | `PP.ClienteTelefone` |
| Email | label "E-MAIL" no valor | `PP.ClienteEmail` |
| Endereço | label "ENDEREÇO DE RELACIONAMENTO" | `PP.ClienteEndereco` |
| Forma Pagamento | label "FORMA DE PAGAMENTO" | `PP.FormaPagamento` |
| Nº Certificado | label "Certificado/" | `DS.NumeroCertificado` |
| Benefício | label "Benefício" | `DS.ValorBeneficio` |
| Apólice | label "Apólice" | `PP.PropostaNumero` |
| Plano | valor "PLANO: ..." | `PP.Plano` |
| Contribuição | label "Contribuição" | `DS.ValorPremioContricuicao` |

**Campos com problema estrutural (não se resolve com prompt):**

| Campo | Problema |
|-------|----------|
| `368,95` com label `(R$)` | Label não discrimina — pode ser 5 campos monetários diferentes. O LLM adivinha. |
| `591,70  27/11/2023` | Bloco composto: 1 valor + 1 data misturados num único par. Stage 3 não separou. |
| `INSCRIÇÃO 1124669542800` | Não existe `ClienteInscricao` no XSD. Mapeia para o mais próximo (errado). |
| `Rio de Janeiro, 5 de março de 2026` | Composto: cidade + data em 1 bloco. 2 campos XSD diferentes. |

**Campos que Stage 3 classificou como estáticos (não chegam ao Stage 4):**

| Campo XSD | Por quê não aparece |
|-----------|-------------------|
| `NomeCliente` | Stage 3 viu em todos os PDFs (mesmo cliente) → classificou como fixo |
| `ClienteCpf` | Mesma razão — PDFs de teste eram do mesmo cliente |
| `ClienteDataNascimento` | Mesma razão |

---

## 4. O Problema Real (não os bugs)

**Os bugs foram todos corrigidos. O problema que sobrou não é um bug.**

A abordagem atual pressupõe que `(label + valor)` é informação suficiente para identificar um campo XSD. Não é — para ~30% dos campos.

Três situações onde a abordagem falha estruturalmente:

**a) Label genérica ou ausente**  
`(R$)` como label pode ser ValorPremioContricuicao, ValorPremioLiquido, ValorIOF, ValorBeneficio, ValorReservaAcumulada. Sem contexto adicional, qualquer mapeamento é uma aposta.

**b) Blocos compostos que Stage 3 não dividiu**  
`"591,70  27/11/2023"` é dois campos em um. O Stage 4 só pode mapear para um XSD path. O outro dado se perde.

**c) Non-determinismo do LLM**  
A mesma entrada produz resultados diferentes a cada run. scalar_coverage variou entre 0.72 e 0.84 com o mesmo código e os mesmos PDFs. Para um produto de template authoring, isso é inaceitável.

**A raiz disso tudo:**  
Estamos usando LLM como se ele tivesse contexto que não tem. O Gemini não sabe a posição do campo na página, não sabe quais outros campos estão na mesma linha de tabela, não sabe que 368,95 está na coluna "Prêmio Líquido" da tabela de seguros. Ele só tem `label + value + nome da seção`.

---

## 5. Onde Queremos Chegar

### O objetivo real do Pilar B

> **Todo campo dinâmico visível no PDF deve ter um binding XSD correto, estável e verificável pelo usuário.**

Isso significa:
- **Correto:** o path XSD é semanticamente o certo (não "o mais próximo disponível")
- **Estável:** rodar o pipeline duas vezes com os mesmos PDFs dá o mesmo resultado
- **Verificável:** o usuário consegue ver no Editor (Pilar C) qual campo visual está ligado a qual XSD path, e pode corrigir se errado

### Métricas alvo

| Métrica | Atual | Alvo |
|---------|-------|------|
| scalar_coverage | 0.76 (instável) | ≥ 0.85 estável (mesmo resultado em 3 runs) |
| Precisão nos mapeados | ~85% | ≥ 95% |
| Campos ambíguos marcados como "needs_review" | 0 | 100% (usuário corrige no Editor) |
| Non-determinismo | alto | zero (campos com sinal claro nunca variam) |

### O que o próximo agente precisa resolver

**Não é** "como fazer o Gemini mapear melhor com um prompt diferente."

**É:** como tornar o binding determinístico para os campos que têm sinal suficiente, e como lidar honestamente com os que não têm (expor ao usuário para revisão, em vez de mapear errado e silenciar).

As perguntas certas para repensar:

1. **Para campos com `detected_format` (telefone, CEP, email, CPF):** por que ainda chamamos o LLM? Esses deveriam mapear por regra determinística.

2. **Para campos com label semântica forte (TELEFONE, ENDEREÇO, FORMA DE PAGAMENTO):** por que o LLM pode errar? Keyword match + lookup table seria suficiente e determinístico.

3. **Para os ~5 campos ambíguos (valores monetários sem label, blocos compostos):** em vez de tentar mapear automaticamente (e errar), marcar como `status: needs_review` e deixar o Editor (Pilar C) ser o mecanismo de resolução.

4. **Para o non-determinismo:** o que está sendo enviado ao LLM que não deveria? O que pode ser resolvido antes do LLM?

5. **Para os blocos compostos:** o Stage 3 deveria separar ou o Stage 4 deveria detectar e dividir?

---

## 6. Arquivos que o Próximo Agente Precisa Conhecer

| Arquivo | O que é |
|---------|---------|
| `backend/services/stages/stage4_mapping/section_matching.py` | Algoritmo central de binding (4.4 + 4.5) |
| `backend/services/stages/stage4_mapping/constants.py` | Thresholds e prompt Gemini |
| `backend/services/stages/stage4_mapping/stage4_field_mapping.py` | Orquestrador dos 7 sub-steps |
| `backend/tests/fixtures/samples/relatorio/PosicaoConsolidada.xsd` | XSD do documento de referência |
| `backend/tests/fixtures/samples/relatorio/ground-truth-posicaoconsolidada.json` | Mapeamento esperado (verdade) |
| `backend/scripts/spike_48_validate_e2e.py` | Script de validação E2E completa |
| `docs/reports/epic-48/e2e-validation-posicao-consolidada.json` | Resultado do último run (0.76) |
| `docs/stories/epics/epic-48-pilar-b-binding-xsd/48.19-48.21.story.md` | Histórico das últimas correções |
| `docs/CURRENT-STATE.md` | Estado geral do projeto |
| `.claude/CLAUDE.md` | Contexto do produto e decisões locked |

---

## 7. O Que NÃO Tentar

Com base em tudo que foi feito:

- **Não ajustar thresholds** (`MINIMUM_MATCH_THRESHOLD`, `HIGH_CONFIDENCE_THRESHOLD`). Já foi tentado. O problema não é threshold, é informação insuficiente.
- **Não adicionar mais constraints no prompt**. RC-I adicionou 2 constraints, cada uma resolveu 1 campo e introduziu instabilidade em outro. Essa abordagem tem retorno decrescente.
- **Não trocar o modelo LLM** sem mudar a arquitetura. GPT-4o, Claude, Gemini Pro — todos terão o mesmo problema estrutural se receberem o mesmo input pobre.
- **Não aumentar o número de passes LLM**. Mais chamadas = mais custo + mais latência + mais variância acumulada.

---

*Este documento é o ponto de partida para o próximo ciclo de trabalho no Pilar B.*  
*Leia em conjunto com `docs/CURRENT-STATE.md` e `.claude/CLAUDE.md` para contexto completo do produto.*
