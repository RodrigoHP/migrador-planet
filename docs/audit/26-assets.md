# Auditoria: Assets (Imagens Embutidas)

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR14** — O sistema deve extrair automaticamente imagens embutidas no PDF para a pasta `assets/`; no Inspetor de Imagem (nível 3), o operador pode substituir, baixar ou remover; dimensões, escala e alinhamento configuráveis.

**FR20** — O ZIP de export deve incluir pasta `assets/` com as imagens do template.

**FR23** — Validação pré-export verifica referências de assets antes de gerar ZIP.

**FR32** — Imagens vetoriais (SVG) detectadas no PDF devem ser incorporadas como SVG inline no `index.html`.

Fonte: `docs/prd-v3.md` FR14, FR20, FR23, FR32.

---

## Frontend — Status de Implementação

**AssetGallery.vue** (`frontend/src/molecules/AssetGallery.vue`) — **Implementado:**
- Grid de thumbnails com estado loading / erro / vazio
- Clique em item emite evento `select` com `AssetInfo`
- `loadAssets()` público via `defineExpose` para refresh manual
- `formatSize()` formata B, KB, MB

**assetService.ts** (`frontend/src/services/assetService.ts`) — **Implementado:**
- `uploadAsset(templateId, file)` — POST multipart
- `deleteAsset(templateId, filename)` — DELETE
- `listAssets(templateId)` — GET, retorna array com `thumbnailUrl` e `dataUri`

**O que falta no frontend:**
- Inspetor de Imagem (nível 3) **não confirmado** — FR14 exige que o inspetor permita substituir, baixar e remover assets; AssetGallery existe como componente mas não foi verificado se está integrado ao FieldInspector para nós de imagem
- **Download individual** de asset não implementado no frontend (assetService não tem função download)
- Configuração de **dimensões, escala e alinhamento** no inspetor de imagem não verificada
- SVG inline (FR32) não confirmado no Canvas — geração de `<svg>` inline vs `<img>` para vetoriais

---

## Backend — Status de Implementação

**routers/assets.py** (`backend/routers/assets.py`) — **Implementado:**
- `POST /api/templates/{id}/assets` — upload com validação de MIME (PNG, JPG, WEBP, SVG), tamanho máx 5 MB, nome seguro (anti path-traversal)
- `DELETE /api/templates/{id}/assets/{filename}` — remoção com path validation
- `GET /api/templates/{id}/assets` — listagem com `thumbnailUrl` (signed URL) + `dataUri` (base64 inline)
- Extração de dimensões via Pillow para imagens raster; SVG sem dimensões (0×0 retornado)

**Extração automática do PDF (FR14):**
- Pipeline (stage2 ou stage5) extrai imagens embutidas — não verificado diretamente; necessário confirmar se `stage2_deep_extraction.py` faz extração de imagens e persiste em `assets/`
- Se não implementado, assets só chegam via upload manual — FR14 exige extração **automática**

**Inclusão no ZIP (FR20):**
- `useExport.ts` (frontend) gerencia a geração do ZIP — necessário verificar se inclui o conteúdo da pasta `assets/` automaticamente
- `usePreExportValidation.ts` (FR23) valida referências de assets — implementação a confirmar

**O que falta no backend:**
- Extração automática de imagens do PDF para `assets/` (a confirmar — pode estar implementada no pipeline mas não verificada)
- SVG: backend retorna dimensões 0×0 para SVG; sem endpoint para retornar SVG como inline string
- Sem endpoint para download individual de asset (GET de arquivo único)

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Extração automática de imagens do PDF para `assets/` não confirmada no pipeline | 🔴 Crítico | Backend | FR14 |
| 2 | Inspetor de Imagem (nível 3) com substituir/baixar/remover não verificado como integrado ao FieldInspector | 🔴 Crítico | Frontend | FR14 |
| 3 | SVG inline (FR32) não verificado — pipeline pode estar gerando `<img>` em vez de `<svg>` | 🟡 Importante | Backend | FR32 |
| 4 | Download individual de asset sem endpoint dedicado (GET /assets/{filename} retorna lista, não arquivo) | 🟡 Importante | Backend | FR14 |
| 5 | Dimensões SVG retornam 0×0 pelo backend — sem parsing de viewBox | 🟡 Importante | Backend | FR14 |
| 6 | Configuração de dimensões, escala e alinhamento no inspetor de imagem não confirmada | 🟡 Importante | Frontend | FR14 |
| 7 | Inclusão automática de `assets/` no ZIP de export não verificada | 🟡 Importante | Frontend/Backend | FR20 |

---

## Backlog Gerado

1. **Confirmar extração automática de imagens no pipeline** — Verificar `stage2_deep_extraction.py` e `stage5_template_generation.py` para extração e persistência de imagens em `assets/`. Implementar se ausente.
2. **Integrar AssetGallery ao Inspetor de Imagem** — Garantir que nós de imagem na árvore abrам o AssetGallery no inspetor (nível 3) com ações substituir/baixar/remover.
3. **Endpoint GET de download individual** — `GET /api/templates/{id}/assets/{filename}` retornando o arquivo para download.
4. **Dimensões SVG via viewBox** — Parsear `viewBox` do SVG para retornar width/height reais.
5. **SVG inline no template** — Verificar e implementar geração de `<svg>` inline no `index.html` para vetoriais detectados (FR32).
6. **Verificar inclusão de assets/ no ZIP** — Auditar `useExport.ts` e o endpoint de export para confirmar que pasta `assets/` é incluída no ZIP.

---

## Status Geral

🟡 Parcial — A infraestrutura de upload/listagem/remoção de assets está sólida (backend router + frontend service + AssetGallery). Os gaps críticos são: (1) extração automática do PDF não confirmada, (2) integração do AssetGallery ao inspetor de imagem não verificada. O sistema pode estar operando apenas com upload manual, sem a extração automática exigida pelo FR14.
