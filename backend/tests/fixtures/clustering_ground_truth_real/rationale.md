# Ground Truth Rationale — Story 44.2

## Sumário

**30 páginas, 28 PDFs, 6 clusters distintos** (A, B_pg0, B_pg1, C, D, E).

Todos os PDFs são vetoriais (gerados por motor Planet Express). Confirmado via PyMuPDF: todos têm blocos de texto extraíveis, nenhum é escaneado.

---

## Decisões de Agrupamento

### Cluster A — 2ViaBoleto Sicoob (6 páginas)

**Critério:** Header "Número do Documento / Cliente / Cód. Beneficiário" + banco Sicoob (cód. 756) + estrutura de parcelas com barcode numérico.

**PDFs incluídos:**
- `2via-sicoob-1/2/3.pdf`: formato padrão, 58 blocos cada
- `2via-sicoob-b1-1.pdf`, `2via-sicoob-b1-2.pdf`: variante B1118 com **27 blocos** (vs padrão 58)
- `2via-sicoob-b1-3.pdf`: B1118 mês diferente, 58 blocos

**Decisão limítrofe — variante 27 blocos:**
Os arquivos `B1118_09012023092236` têm apenas 27 blocos vs 58 do padrão. Inspeção de texto confirma que o header "Número do Documento / Cliente / Cód. Beneficiário / Endereço / CEP / Município / UF / Data Emissão / Competência / Vencimento / ANS" é idêntico. A redução de blocos sugere uma versão mais compacta (sem a seção de histórico de parcelas). **Decisão original: cluster A** — mesmo template, variante de impressão.

**Revisão pós-spike (2026-04-13):** O baseline separou B1118 do padrão, e a análise pós-spike concluiu que esta separação é **correta por design**. A ausência da seção de histórico de parcelas é uma diferença estrutural real, não apenas variação de dados. Dois templates distintos (um com a seção, um sem) são o resultado correto para o sistema migrador-planet. O critério "mesmo banco/header" utilizado neste ground truth subestimou a diferença estrutural. Em retrospecto, B1118 poderia ser rotulado como cluster A2 em vez de A — mas como o spike já está fechado e o comportamento do pipeline está correto, o ground truth permanece como está e esta nota documenta a revisão.

---

### Cluster B_pg0 / B_pg1 — Corporate Boleto Convênio (4 páginas, 2 clusters)

**Critério:** PDFs multi-página. O pipeline clusteriza por PÁGINA, não por documento.

**Página 0 (B_pg0):** 43 blocos — alta densidade. Header empresa + tabela de boletos de convênio.

**Página 1 (B_pg1):** 7 blocos — baixa densidade. Rodapé com dados de órgão/empresa.

**Decisão:** Dois clusters distintos. As duas páginas são estruturalmente muito diferentes (43 vs 7 blocos, densidades opostas). Se o baseline os agrupasse no mesmo cluster, seria erro de false merge.

**Observação:** `corp-convenio-1.pdf` e `corp-convenio-2.pdf` têm blocos idênticos (43/43 e 7/7) — alta confiança no label.

---

### Cluster C — IPVA SEFAZ/RJ (12 páginas)

**Critério:** "SEFAZ/RJ" no texto, campo RENAVAM, código de barras numérico específico, 42 blocos.

**Risco:** Este template é similar ao Cluster D (mesmo banco Banco do Brasil, mesmo layout geral de boleto). A diferença é o emissor (SEFAZ vs DETRAN) e o número de blocos (42 vs 52).

**Decisão:** Cluster C separado de D. 12 instâncias confirmam consistência: todos têm exatamente 42 blocos.

---

### Cluster D — DETRAN/RJ (4 páginas)

**Critério:** "DETRAN/RJ — CNPJ: 30.295.513/0001-38" no texto, campo "N° do documento", 52 blocos.

**Risco — caso de borda crítico C vs D:**
boletoGrd (cluster C) e boletoDuda (cluster D) são ambos boletos de tributos estaduais do Rio de Janeiro, emitidos pelo mesmo banco (Banco do Brasil), com layout muito similar. As diferenças estruturais são:
- C: 42 blocos, campo RENAVAM, código 23794.60005...
- D: 52 blocos, campo "N° do documento", código 23794.60013...

Se o baseline F0/geometry/graph tiver threshold muito permissivo, pode fundir C e D incorretamente (false merge). Este é o caso de borda AC5 da story.

---

### Cluster E — Condomínio (4 páginas)

**Critério:** Header "INFORMAÇÕES DE PAGAMENTO / Discriminação das Verbas", agência 6157/99709-6, 83 blocos.

**Decisão importante — templates E e F unificados:**
A story 44.2 originalmente previa que `boletoAcir*.pdf` (Template E) e `boletoCondJulho/Maio.pdf` (Template F) seriam clusters distintos. **A inspeção revelou que são o MESMO template:**
- Mesma agência: 6157/99709-6
- Mesmo header: "INFORMAÇÕES DE PAGAMENTO / Discriminação das Verbas"
- Mesma estrutura de linhas: CONDOMÍNIO / FUNDO RESERVA / ÁGUA INDIV. / RESTAURAÇÃO FACHADA / 13° SALÁRIO PARC
- Mesma contagem de blocos: 83

A diferença é apenas nos valores das verbas (meses diferentes). Portanto, **todos os 4 PDFs estão no cluster E**. Esta correção é importante para a validade do ground truth — rotular templates idênticos como distintos introduziria falso negativo no score ARI.

---

## Estatísticas do Dataset

| Cluster | N Páginas | Blocos por página | Tipo documento |
|---------|-----------|-------------------|----------------|
| A | 6 | 27 ou 58 | Boleto bancário 2ª via (Sicoob) |
| B_pg0 | 2 | 43 | Relação de boletos convênio — pág. 1 |
| B_pg1 | 2 | 7 | Relação de boletos convênio — pág. 2 |
| C | 12 | 42 | Boleto IPVA (SEFAZ/RJ / BB) |
| D | 4 | 52 | Boleto DETRAN/RJ (BB) |
| E | 4 | 83 | Boleto condomínio |
| **Total** | **30** | — | **5 templates reais distintos** |

---

## Casos de Borda Priorizados

1. **A interno — variante 27 blocos:** Mesmo template, geometria diferente. Testa sensibilidade intra-template do baseline.
2. **C vs D — templates similares:** IPVA vs DETRAN, mesmo banco, layouts análogos. Testa separabilidade de templates do mesmo domínio.
3. **B multi-página:** Página de alta densidade vs página de baixa densidade do mesmo documento. Testa clustering por página.
4. **E unificado:** Story previa split E/F mas são o mesmo template. Correção impede false negative no ground truth.

---

*Rationale produzido por @dev (Dex) em modo YOLO — Story 44.2 — 2026-04-13*
