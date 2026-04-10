/**
 * Story 40.6 — FE-002: Iframe srcdoc builder and page parsing for HTMLCanvas.
 * Story 41.9 — Barcode engine unification: inject JsBarcode inline for WYSIWYG.
 * Story 41.11 — Chart canvas placeholder: replace <canvas> chart nodes with CSS placeholders.
 * Story 42.3 — Canvas SVG inline sync: apply replaceImgWithSvgInline before srcdoc build.
 *
 * Extracted from HTMLCanvas.vue to reduce component LOC.
 */
import { computed } from 'vue'
import { useGenerationStore } from '@/stores/generation'
import { useTemplateStore } from '@/stores/templateStore'
import { generateAllBorderOverrides } from '@/utils/borderStyleGenerator'
import { replaceImgWithSvgInline } from '@/composables/useExport'

// ─── JsBarcode lib cache (module-level, fetched once) ────────────────────────

let _jsBarcodeLib: string | null = null

async function getJsBarcodeLib(): Promise<string> {
  if (_jsBarcodeLib !== null) return _jsBarcodeLib
  try {
    const resp = await fetch('/libs/JsBarcode.all.min.js')
    _jsBarcodeLib = await resp.text()
  } catch {
    _jsBarcodeLib = ''
  }
  return _jsBarcodeLib
}

// Pre-load on module init (fire-and-forget) so the cache is warm by first render.
getJsBarcodeLib()

// ─── Chart Placeholder ──────────────────────────────────────────────────────

/**
 * Story 41.11 — Replace <canvas> elements whose id matches a chart node with
 * a CSS placeholder div that preserves position/dimensions.
 *
 * Pure function — exported for unit testability.
 *
 * @param html         Raw page HTML
 * @param chartNodeIds Map<nodeId, chartType> from templateStore
 * @returns            HTML with matching <canvas> replaced by <div class="chart-placeholder">
 */
export function replaceChartsWithPlaceholders(
  html: string,
  chartNodeIds: Map<string, string>,
): string {
  let result = html
  for (const [nodeId, chartType] of chartNodeIds) {
    const canvasRegex = new RegExp(`<canvas([^>]*id=["']${nodeId}["'][^>]*)>\\s*</canvas>`, 'gi')
    result = result.replace(canvasRegex, (_, attrs) => {
      return `<div class="chart-placeholder" data-chart-type="${chartType}"${attrs}></div>`
    })
  }
  return result
}

const CHART_PLACEHOLDER_CSS = `
.chart-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f4ff;
  border: 1px dashed #c7d2fe;
  box-sizing: border-box;
  overflow: hidden;
}
.chart-placeholder::after {
  content: '📊 ' attr(data-chart-type);
  color: #6b7280;
  font-size: 11px;
  font-family: sans-serif;
  pointer-events: none;
}
`

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
    // AC5: detect barcode nodes and inject JsBarcode inline (from module-level cache)
    const hasBarcodes = /data-type=["']barcode["']/.test(html)
    const jsBarcodeInlineScript =
      hasBarcodes && _jsBarcodeLib ? `<script>${_jsBarcodeLib}<\/script>\n` : ''

    // AC6: barcode init script — renders each barcode div via JsBarcode
    const barcodeInitScript =
      hasBarcodes && _jsBarcodeLib
        ? `\n<script>
document.querySelectorAll('[data-type="barcode"]').forEach(function(el) {
  var format = el.dataset.format || 'CODE128'
  var value = el.dataset.value || '0000000000'
  el.innerHTML = ''
  try { JsBarcode(el, value, { format: format, displayValue: true }) } catch(e) {}
})
<\/script>`
        : ''

    // Story 42.3 — Apply SVG inline for image nodes with svgInline: true (AC3 of 41.10)
    const svgInlineNodes = templateStore
      .getNodesByType('image')
      .filter(
        (n) =>
          n.visibility !== false &&
          n.properties['svgInline'] === true &&
          n.properties['svgInlineContent'],
      )

    const htmlAfterSvg =
      svgInlineNodes.length > 0 ? replaceImgWithSvgInline(html, svgInlineNodes) : html

    // Story 41.11 — Replace <canvas> chart nodes with CSS placeholders
    const chartNodeIds = new Map(
      templateStore
        .getNodesByType('chart')
        .filter((n) => n.visibility !== false)
        .map((n) => [n.id, (n.properties['chartType'] as string) || 'chart']),
    )

    const processedHtml =
      chartNodeIds.size > 0
        ? replaceChartsWithPlaceholders(htmlAfterSvg, chartNodeIds)
        : htmlAfterSvg

    const placeholderCss = chartNodeIds.size > 0 ? CHART_PLACEHOLDER_CSS : ''

    return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
${jsBarcodeInlineScript}<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { overflow: hidden; }
${css}
${placeholderCss}</style>
</head>
<body>${processedHtml}
${CANVAS_INTERACTION_SCRIPT}${barcodeInitScript}
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
