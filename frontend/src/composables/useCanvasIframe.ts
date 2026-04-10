/**
 * Story 40.6 — FE-002: Iframe srcdoc builder and page parsing for HTMLCanvas.
 *
 * Extracted from HTMLCanvas.vue to reduce component LOC.
 */
import { computed } from 'vue'
import { useGenerationStore } from '@/stores/generation'
import { useTemplateStore } from '@/stores/templateStore'
import { generateAllBorderOverrides } from '@/utils/borderStyleGenerator'

// ─── Page Sizes ─────────────────────────────────────────────────────────────

const PAGE_SIZES: Record<string, { width: number; height: number }> = {
  A4: { width: 794, height: 1123 },
  Letter: { width: 816, height: 1056 },
}

// ─── Types ──────────────────────────────────────────────────────────────────

export interface CanvasPage {
  pageNum: number
  html: string
  css: string
}

// ─── Interaction Script ─────────────────────────────────────────────────────

const CANVAS_INTERACTION_SCRIPT = `
<script>
(function() {
  function getAncestorIds(el) {
    var ids = [];
    var current = el;
    while (current && current !== document.body) {
      if (current.dataset && current.dataset.nodeId) {
        ids.push(current.dataset.nodeId);
      } else if (current.id) {
        ids.push(current.id);
      }
      current = current.parentElement;
    }
    return ids;
  }

  function getRelativeBox(el) {
    var rect = el.getBoundingClientRect();
    var bodyRect = document.body.getBoundingClientRect();
    return {
      x: rect.left - bodyRect.left,
      y: rect.top - bodyRect.top,
      width: rect.width,
      height: rect.height
    };
  }

  document.addEventListener('click', function(e) {
    var target = e.target;
    if (!target || target === document.body || target === document.documentElement) return;
    var el = target;
    while (el && el !== document.body) {
      var nodeId = (el.dataset && el.dataset.nodeId) ? el.dataset.nodeId : el.id;
      if (nodeId) {
        var box = getRelativeBox(el);
        var ancestorIds = getAncestorIds(el);
        window.parent.postMessage({
          type: 'canvas-element-clicked',
          elementId: nodeId,
          boundingBox: box,
          ancestorIds: ancestorIds,
          ctrlKey: e.ctrlKey,
          shiftKey: e.shiftKey
        }, '*');
        break;
      }
      el = el.parentElement;
    }
  }, true);

  function reportAllBoxes() {
    var els = document.querySelectorAll('[data-node-id], [id]');
    els.forEach(function(el) {
      var nodeId = (el.dataset && el.dataset.nodeId) ? el.dataset.nodeId : el.id;
      if (!nodeId) return;
      var box = getRelativeBox(el);
      if (box.width === 0 && box.height === 0) return;
      window.parent.postMessage({
        type: 'canvas-element-bbox',
        elementId: nodeId,
        boundingBox: box
      }, '*');
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', reportAllBoxes);
  } else {
    setTimeout(reportAllBoxes, 50);
  }
})();
<\/script>`

// ─── Composable ─────────────────────────────────────────────────────────────

export function useCanvasIframe() {
  const generationStore = useGenerationStore()
  const templateStore = useTemplateStore()

  const pageSize = computed(() => {
    const sizeKey = (templateStore.documentTree?.root?.properties?.pageSize as string) ?? 'A4'
    return PAGE_SIZES[sizeKey] ?? PAGE_SIZES['A4']!
  })

  const pageWidth = computed(() => pageSize.value.width)
  const pageHeight = computed(() => pageSize.value.height)

  const borderOverrideCss = computed(() => {
    return generateAllBorderOverrides(templateStore.flatNodes)
  })

  const pages = computed<CanvasPage[]>(() => {
    const draft = generationStore.templateDraft
    if (!draft) return []

    const css = (draft.css ?? '') + borderOverrideCss.value
    const html = draft.html ?? ''

    const parser = typeof DOMParser !== 'undefined' ? new DOMParser() : null
    if (!parser) {
      return [{ pageNum: 1, html, css }]
    }

    const doc = parser.parseFromString(`<div id="_root">${html}</div>`, 'text/html')
    const pageEls = doc.querySelectorAll('[data-layout-type]')

    if (pageEls.length === 0) {
      if (html) {
        if (import.meta.env.DEV)
          console.warn('[HTMLCanvas] Nenhum elemento [data-layout-type] encontrado no HTML gerado.')
      }
      return [{ pageNum: 1, html, css }]
    }

    const result: CanvasPage[] = []
    pageEls.forEach((el) => {
      const pageContents = el.children
        ? Array.from(el.children).filter((child) => child.classList?.contains('page-content'))
        : []
      if (pageContents.length > 1) {
        pageContents.forEach((pageContent) => {
          const wrapper = el.cloneNode(false) as Element
          wrapper.appendChild(pageContent.cloneNode(true))
          result.push({ pageNum: result.length + 1, html: wrapper.outerHTML, css })
        })
      } else {
        result.push({ pageNum: result.length + 1, html: el.outerHTML, css })
      }
    })
    return result
  })

  function buildPageSrcdoc(html: string, css: string): string {
    return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { overflow: hidden; }
${css}
</style>
</head>
<body>${html}
${CANVAS_INTERACTION_SCRIPT}
</body>
</html>`
  }

  /** Returns the page number that contains the element with the given node ID */
  function findPageForElement(id: string): number | null {
    for (const page of pages.value) {
      if (page.html.includes(`data-node-id="${id}"`)) return page.pageNum
    }
    return null
  }

  /** Scrolls the canvas to the page that belongs to the given layout type ID */
  function findPageForLayoutId(layoutId: string): number | null {
    const page = pages.value.find((p) => p.html.includes(`data-layout-type="${layoutId}"`))
    return page ? page.pageNum : null
  }

  return {
    pageWidth,
    pageHeight,
    pages,
    buildPageSrcdoc,
    findPageForElement,
    findPageForLayoutId,
  }
}
