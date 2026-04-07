# Auditoria: Fontes Customizadas + Estilos

**Data:** 2026-04-07
**Status Geral:** 🟡 Parcial

---

## O que foi planejado

**FR27** — Ao detectar fontes não-padrão no PDF, o sistema executa cascata: (1) verifica catálogo local (`../Bibliotecas/`); (2) usa IA para identificar e buscar em repositórios públicos; (3) oferece upload manual. O Inspetor de Elemento exibe fonte detectada com fallback e botão upload quando não encontrada.

**FR27a** — Gestão do catálogo de Bibliotecas acessível apenas pela Home, com três abas (Fontes, CSS, JS); cada aba exibe lista de arquivos com nome, tamanho e botão remover; botão contextual para adicionar com filtro de extensão.

Fonte: `docs/prd-v3.md` FR27, FR27a.

---

## Frontend — Status de Implementação

**useFontCascade.ts** (`frontend/src/composables/useFontCascade.ts`) — **Implementado:**
- Cascata de 3 etapas: (1) mapa de normalização (Helvetica → Arial, etc.); (2) catálogo local via `useBibliotecas()` (IndexedDB); (3) chamada ao backend `/api/font-identify` com IA
- `FONT_NORMALIZATION_MAP` com ~8 entradas (Helvetica, Times, Courier e variantes)
- Retorna `FontCascadeResult` com status `found | fallback | not_found` e sugestões com similaridade
- Graceful fallback: se backend indisponível, retorna `not_found` sem erro

**FontWarning.vue** (`frontend/src/molecules/FontWarning.vue`) — **Implementado:**
- Exibe alerta quando `status === 'not_found'`
- Mostra fonte detectada (vermelho) e fallback (neutro)
- Botão "Upload fonte" com file input aceita `.ttf,.otf,.woff,.woff2`
- Emite evento `upload: [file: File]` — integração com Bibliotecas a cargo do consumidor

**Inspector de Elemento:** Não verificado se FontWarning e useFontCascade estão integrados ao FieldInspector/ElementInspector — a cadeia de uso precisa ser confirmada.

---

## Backend — Status de Implementação

**stage2_deep_extraction.py** (`backend/services/stages/stage2_deep_extraction.py`):
- Extrai fontes via PyMuPDF: `font_name`, extraído de `span["font"]` por bloco
- `FONT_MAP` expandido (~50 fontes PDF → CSS): Helvetica, Arial, Times, Courier, Calibri, Cambria, Verdana, Tahoma, Georgia, Trebuchet e variantes Bold/Italic
- Campos extraídos: `font_name` (string), inferência de `is_bold`/`is_italic` pelo nome (ex: contém "-Bold", "-BoldItalic")
- `font_size` extraído do `span["size"]`

**stage5_template_generation.py** (linhas 770-800):
- CSS gerado com `font-family` real (não hardcoded Arial): `.f-{safe_class} { font-family: '{clean_name}', sans-serif; font-size: {fs}pt; }`
- Strip de prefixo subset PDF (`re.sub(r"^[A-Z]{6}\+", "", font_name)`) — ex: `ABCDEF+Helvetica` → `Helvetica`
- **Bug corrigido**: geração usa font_name real, não Arial hardcoded

**font.py** (`backend/routers/font.py`) — **Implementado:**
- `POST /api/font-identify` recebe `font_name` e retorna sugestões de fontes alternativas
- Usa OpenRouter (Claude Haiku por padrão) com prompt de tipografia
- Fallback sem IA: regras por categoria (serif, mono, sans-serif genérico)
- Retorna array de `FontSuggestion` com `name`, `similarity`, `source`

**O que falta no backend:**
- Font-face embedding: o pipeline não gera regras `@font-face` com arquivos de fonte. CSS gerado usa apenas `font-family` com fallbacks de sistema — fontes customizadas carregadas via Bibliotecas precisariam de `@font-face` no style.css gerado.
- Integração Bibliotecas → Export: se o operador carregou uma fonte via Bibliotecas, o export ZIP não inclui automaticamente essa fonte nem gera `@font-face`.

---

## Gaps Identificados

| # | Gap | Severidade | Escopo | Referência |
|---|-----|-----------|--------|-----------|
| 1 | Font-face embedding ausente: CSS gerado não inclui `@font-face` para fontes carregadas via Bibliotecas | 🔴 Crítico | Backend | FR27 |
| 2 | FontWarning e useFontCascade não integrados ao FieldInspector/ElementInspector — não verificado se o warning aparece na UI real | 🟡 Importante | Frontend | FR27 |
| 3 | Export ZIP não inclui arquivos de fonte do catálogo Bibliotecas | 🟡 Importante | Backend/Frontend | FR27a |
| 4 | `FONT_NORMALIZATION_MAP` limitado a ~8 entradas — fontes corporativas brasileiras não cobertas | 🟢 Menor | Frontend | FR27 |
| 5 | `is_bold` e `is_italic` inferidos apenas pelo nome da fonte, sem fallback para flags do PDF (`span["flags"]`) | 🟢 Menor | Backend | FR3 |

---

## Backlog Gerado

1. **Geração de @font-face no CSS** — Extender `stage5_template_generation.py` para gerar regras `@font-face` quando o template usa fontes carregadas via Bibliotecas. Incluir arquivos de fonte no ZIP de export.
2. **Integrar FontWarning no ElementInspector** — Verificar e conectar `useFontCascade` ao campo de fonte no Inspetor de Elemento; exibir `FontWarning` quando fonte não encontrada.
3. **Expandir FONT_NORMALIZATION_MAP** — Adicionar fontes corporativas BR comuns (Bradesco Sans, Itaú Display, etc.) e variantes PS (ex: `Helvetica-PS`, `ArialMT-Bold`).
4. **Upload de fonte via FontWarning → Bibliotecas** — Garantir que o evento `upload` do FontWarning persista a fonte no IndexedDB via `useBibliotecas.addFile()` e re-execute a cascata.
5. **is_bold/is_italic via flags PyMuPDF** — Usar `span["flags"] & 2^4` (bold) e `span["flags"] & 2^1` (italic) como fonte primária, nome como fallback.

---

## Status Geral

🟡 Parcial — A extração de fontes no backend, a cascata de fallback no frontend e o endpoint de identificação por IA estão implementados. A lacuna crítica é a ausência de `@font-face` embedding e a não inclusão de arquivos de fonte no ZIP de export, o que torna fontes customizadas inoperantes no template final.
