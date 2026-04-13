# Ground Truth — Rationale de Clustering

## Criado por
@dev (Dex) em modo YOLO — 2026-04-13 — Story 44.1

## Escopo do dataset

| Métrica | Valor |
|---|---|
| PDFs distintos | 7 |
| Templates distintos | 3 |
| Páginas rotuladas | 9 |
| Ideal (spec AC1) | 30-50 páginas |
| Gap documentado | Spike com dataset mínimo; ver seção Limitações |

## PDFs utilizados

Todos os PDFs são documentos reais do usuário (Rodrigo Magina), obtidos de D:/Downloads.
Não são PDFs do sistema Planet Express em produção, mas são documentos típicos do domínio:
boletos bancários brasileiros vetoriais, gerados por motor, sem scan.

## Decisões de rotulagem

### Cluster A — Boleto 2ª via Sicoob

**Arquivos:** `boleto-2via-sample1.pdf`, `boleto-2via-sample2.pdf`, `boleto-2via-sample3.pdf`

**Por que mesmo cluster:** Os 3 PDFs têm layout idêntico:
- Header: "Número do Documento / Cliente / Cód. Beneficiário" (mesmas posições Y)
- Corpo: tabela de parcelas com mesmas colunas
- Rodapé: linha de barcode + dados bancários Sicoob
- Emitidos pelo mesmo sistema (cód. beneficiário 3747/1118)

Os valores diferem (datas, montantes, nomes de parcelas) mas a estrutura é idêntica.
Isso é exatamente o cenário principal de sucesso para o pipeline: mesmo template, instâncias diferentes.

### Cluster B_page0 / B_page1 — Relação de Boletos de Convênios

**Arquivos:** `convenio-sample1.pdf` (2 págs), `convenio-sample2.pdf` (2 págs)

**Decisão limítrofe — por que subdividir B:**

A relação de convênios tem 2 páginas por PDF. A página 0 é mais densa (tabela completa),
enquanto a página 1 é mais esparsa (apenas rodapé/resumo). O baseline de clustering
usa posições Y dos blocos para medir similaridade. As duas páginas têm distribuições de blocos
suficientemente diferentes para que o clustering page-level as separe.

Optamos por rotular como B_page0 e B_page1 separadamente porque:
1. O pipeline trabalha em page-level (cada página é uma unidade)
2. Se um clustering põe pgs 0 de ambos PDFs no mesmo cluster e pgs 1 no outro, isso é **correto**
3. Se um clustering põe todos os 4 em um único cluster, seria **sub-clustering** (penalizado por completeness)

**Cenário de teste:** Um clustering correto deve produzir:
- Cluster para {convenio-sample1 pg0, convenio-sample2 pg0}
- Cluster para {convenio-sample1 pg1, convenio-sample2 pg1}

### Cluster C — Boleto de Condomínio

**Arquivos:** `boleto-condominio-sample1.pdf`, `boleto-condominio-sample2.pdf`

**Por que separado de A:** Layout completamente diferente:
- Header: "INFORMAÇÕES DE PAGAMENTO / Discriminação das Verbas" (vs "Número do Documento" no A)
- Emissor diferente (condomínio vs Sicoob)
- Estrutura de blocos diferente (mais colunas no template C)

Os dois samples de fevereiro e março de 2025 têm mesmo layout estrutural, apenas valores de data/montante diferem.
São claramente mesmo cluster.

## Limitações do dataset

1. **Volume baixo:** 9 páginas vs 30-50 do ideal. Insuficiente para análise estatística robusta.
   Recomendação: expandir com PDFs Planet Express reais em iteração 2 do spike.

2. **PDFs não são Planet Express:** Os PDFs aqui são documentos reais mas não do sistema em produção.
   O sistema Planet Express gera boletos com estrutura ligeiramente diferente.
   Risco: métricas podem não generalizar para PDFs de produção.

3. **Sem casos de edge-case extremos:** Dataset não cobre rotação, páginas com tabelas expandidas
   (diferente row count), ou mistura de tipos em um único PDF.

4. **Labels B_page0/B_page1 são subjetivos:** A fronteira entre "mesmas páginas de um template"
   e "layouts suficientemente diferentes" é fuzzy. Com PDFs de produção reais, um humano
   poderia classificar as 4 páginas de convênio como um único cluster.

## Resultado esperado de um clustering perfeito

Dado o ground truth acima, um clustering ideal produz:

```
Cluster 1: boleto-2via-sample1 pg0, boleto-2via-sample2 pg0, boleto-2via-sample3 pg0 → label A
Cluster 2: convenio-sample1 pg0, convenio-sample2 pg0 → label B_page0  
Cluster 3: convenio-sample1 pg1, convenio-sample2 pg1 → label B_page1
Cluster 4: boleto-condominio-sample1 pg0, boleto-condominio-sample2 pg0 → label C
```

ARI=1.0, Homogeneity=1.0, Completeness=1.0 = clustering perfeito.
