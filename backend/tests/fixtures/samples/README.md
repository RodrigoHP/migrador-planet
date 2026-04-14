# Samples — PDFs de Domínio Real

> ⚠️ **Esta pasta está no `.gitignore` — os PDFs NÃO sobem para o GitHub.**
> Contêm dados reais de produção (CPF, valores financeiros, dados de beneficiários).
> Para obter as amostras: copie manualmente de `D:\Downloads\Exemplos` para esta pasta.

PDFs reais do motor Planet Express organizados por tipo de documento.

**Uso:** rodar o pipeline manualmente, auditar o Pilar A, validar novos stages.
**NÃO usar como fixtures de pytest** — não têm ground truth definido. Para testes automatizados, usar `clustering_ground_truth_real/`.

## Estrutura

```
samples/
  boleto/          ← boletos bancários (corporate, individual, VG)
  certificado/     ← certificados de previdência/seguro (Hinode, Prevcom, VI)
  relatorio/       ← relatórios e extratos (posição consolidada, beneficiário, previdência)
  dirf/            ← declarações DIRF
  apolice/         ← apólices de seguro
```

## Arquivos

| Tipo | Arquivo | Observações |
|------|---------|-------------|
| boleto | `BoletoCorporateMercantil.pdf` | Boleto corporate com tabela raster |
| boleto | `BoletoIndividual_05220.pdf` | Boleto individual — **criptografado** (senha: `05220`) |
| boleto | `BoletoIndividual_05220_unlocked.pdf` | Idem, descriptografado para uso no pipeline |
| boleto | `BoletoVg.pdf` | Boleto VG |
| certificado | `CertificadoHinode.pdf` | Certificado Hinode |
| certificado | `CertificadoPrevcom.pdf` | Certificado Prevcom |
| certificado | `CertificadoPrevidencia.pdf` | Certificado Previdência |
| certificado | `CertificadoVI.pdf` | Certificado VI |
| certificado | `CertiticadoPrevidencia.pdf` | Certificado Previdência (variante) |
| relatorio | `PosicaoConsolidada.pdf` | Posição consolidada |
| relatorio | `PrevidenciaExtrato.pdf` | Extrato de previdência |
| relatorio | `RelatorioBeneficiario.pdf` | Relatório beneficiário |
| relatorio | `RelatorioPosicaoConsolidada.pdf` | Relatório posição consolidada |
| dirf | `DirfInformaFinanceiro.pdf` | DIRF — informe financeiro |
| apolice | `ApoliceVg.pdf` | Apólice VG |

## Pilar A — Validação pendente

Os tipos `certificado`, `relatorio`, `dirf` e `apolice` ainda não foram testados contra o pipeline.
Baseline medido apenas para `boleto` (Epic 43: 17% → projeção ≥80%).

Para rodar auditoria: `python backend/scripts/audit_boleto_pillar_a.py`
