/**
 * usePagination — Story 9.5
 *
 * Layout Engine: calcula quebras de página no Canvas em tempo real.
 * Algoritmo: iterar elementos top-to-bottom, rastrear currentY,
 * inserir quebra quando conteúdo excede bodyHeight.
 */
import { ref, computed } from 'vue'

// ─── Types ──────────────────────────────────────────────────────────────────

export type PageSize = 'A4' | 'letter' | 'custom'
export type PageOrientation = 'portrait' | 'landscape'

export interface PageConfig {
  size: PageSize
  orientation: PageOrientation
  /** mm */
  marginTop: number
  /** mm */
  marginBottom: number
  /** mm */
  marginLeft: number
  /** mm */
  marginRight: number
  /** px */
  headerHeight: number
  /** px */
  footerHeight: number
  /** custom only — mm */
  customWidth?: number
  /** custom only — mm */
  customHeight?: number
}

export interface LayoutElement {
  id: string
  /** height in px */
  height: number
  type?: string
  /** Story 33.7: when true, element moves to next page as a whole if it doesn't fit */
  keepTogether?: boolean
}

export interface PageBreak {
  /** index in elements array AFTER which the break occurs */
  afterIndex: number
  /** page number that starts AFTER this break (1-based) */
  newPage: number
  /** visual label */
  label: string
}

export interface PaginationResult {
  pageBreaks: PageBreak[]
  pageCount: number
  remainingSpace: number
}

// ─── Header/Footer section descriptor ───────────────────────────────────────

export interface HeaderFooterSection {
  id: string
  /** 'header' or 'footer' */
  role: 'header' | 'footer'
  /** height in px */
  height: number
  /** whether this section repeats on every page */
  repeat: boolean
}

export interface HeaderFooterPageLayout {
  /** page number (1-based) */
  page: number
  /** header section ids repeated on this page (empty if not repeating) */
  headerIds: string[]
  /** footer section ids repeated on this page (empty if not repeating) */
  footerIds: string[]
}

// ─── Page dimension constants (mm → px at 96dpi: 1mm ≈ 3.7795px) ──────────

export const MM_TO_PX = 3.7795

export const PAGE_SIZES_MM: Record<Exclude<PageSize, 'custom'>, { width: number; height: number }> = {
  A4: { width: 210, height: 297 },
  letter: { width: 216, height: 279 },
}

export function getPageDimensionsPx(config: PageConfig): { width: number; height: number } {
  let widthMm: number
  let heightMm: number

  if (config.size === 'custom') {
    widthMm = config.customWidth ?? 210
    heightMm = config.customHeight ?? 297
  } else {
    const dims = PAGE_SIZES_MM[config.size]
    widthMm = dims.width
    heightMm = dims.height
  }

  if (config.orientation === 'landscape') {
    ;[widthMm, heightMm] = [heightMm, widthMm]
  }

  return {
    width: Math.round(widthMm * MM_TO_PX),
    height: Math.round(heightMm * MM_TO_PX),
  }
}

export function calcBodyHeight(config: PageConfig): number {
  const { height: totalPx } = getPageDimensionsPx(config)
  const marginTopPx = config.marginTop * MM_TO_PX
  const marginBottomPx = config.marginBottom * MM_TO_PX
  return Math.max(0, totalPx - config.headerHeight - config.footerHeight - marginTopPx - marginBottomPx)
}

export function calcRemainingSpace(config: PageConfig): number {
  return calcBodyHeight(config)
}

// ─── calculateRemainingSpace helper ─────────────────────────────────────────

/**
 * Calculate the available body space after subtracting header and footer heights.
 * Useful when header/footer heights are known independently of the page config.
 *
 * @param bodyHeight  - total usable body height in px (from calcBodyHeight)
 * @param headerHeight - header height in px to subtract additionally
 * @param footerHeight - footer height in px to subtract additionally
 */
export function calculateRemainingSpace(
  bodyHeight: number,
  headerHeight: number,
  footerHeight: number,
): number {
  return Math.max(0, bodyHeight - headerHeight - footerHeight)
}

// ─── Header/Footer layout builder ────────────────────────────────────────────

/**
 * Build a per-page layout describing which header/footer sections repeat on each page.
 *
 * For each page in [1..pageCount], returns the list of header/footer section ids
 * that should appear on that page. Sections with `repeat=true` appear on every page.
 * Sections with `repeat=false` appear only on page 1.
 *
 * @param sections   - array of HeaderFooterSection descriptors
 * @param pageCount  - total number of pages
 * @returns array of HeaderFooterPageLayout, one per page
 */
export function buildHeaderFooterLayout(
  sections: HeaderFooterSection[],
  pageCount: number,
): HeaderFooterPageLayout[] {
  const headers = sections.filter((s) => s.role === 'header')
  const footers = sections.filter((s) => s.role === 'footer')

  const layout: HeaderFooterPageLayout[] = []
  for (let page = 1; page <= pageCount; page++) {
    const headerIds = headers
      .filter((s) => s.repeat || page === 1)
      .map((s) => s.id)
    const footerIds = footers
      .filter((s) => s.repeat || page === 1)
      .map((s) => s.id)
    layout.push({ page, headerIds, footerIds })
  }
  return layout
}

// ─── Reposition fixed element (mirrors base.js reposicionarElementoFixo) ────

export interface FixedElementDescriptor {
  id: string
  /** top position in px (from layout) */
  top: number
  /** height in px */
  height: number
  /** gap below reference element in px (mirrors data-gap attribute) */
  gap?: number
}

export interface DynamicElementDescriptor {
  id: string
  /** top position in px (computed by layout engine) */
  top: number
  /** height in px */
  height: number
}

/**
 * Calculate the repositioned top value for a fixed element that should appear
 * below a dynamic reference element. Mirrors `reposicionarElementoFixo` in base.js.
 *
 * @param fixedEl     - descriptor of the fixed element
 * @param referenceEl - descriptor of the dynamic reference element
 * @returns new top value in px for fixedEl
 */
export function repositionFixedElement(
  fixedEl: FixedElementDescriptor,
  referenceEl: DynamicElementDescriptor,
): number {
  const gap = fixedEl.gap ?? 0
  return referenceEl.top + referenceEl.height + gap
}

// ─── Core pagination algorithm ───────────────────────────────────────────────

export function calculatePageBreaks(
  elements: LayoutElement[],
  config: PageConfig,
): PaginationResult {
  const bodyHeight = calcBodyHeight(config)
  const pageBreaks: PageBreak[] = []
  let currentY = 0
  let pageCount = 1

  for (let i = 0; i < elements.length; i++) {
    const el = elements[i]!
    if (currentY + el.height > bodyHeight && currentY > 0) {
      // Insert page break before this element
      pageCount++
      pageBreaks.push({
        afterIndex: i - 1,
        newPage: pageCount,
        label: `--- QUEBRA DE PÁGINA --- (Página ${pageCount})`,
      })
      currentY = el.height
    } else if (el.keepTogether && currentY > 0 && currentY + el.height > bodyHeight) {
      // Story 33.7: keepTogether — move entire block to next page
      pageCount++
      pageBreaks.push({
        afterIndex: i - 1,
        newPage: pageCount,
        label: `--- QUEBRA DE PÁGINA --- (Página ${pageCount})`,
      })
      currentY = el.height
    } else {
      currentY += el.height
    }
  }

  return {
    pageBreaks,
    pageCount,
    remainingSpace: Math.max(0, bodyHeight - currentY),
  }
}

// ─── Composable ──────────────────────────────────────────────────────────────

const DEFAULT_CONFIG: PageConfig = {
  size: 'A4',
  orientation: 'portrait',
  marginTop: 10,
  marginBottom: 10,
  marginLeft: 10,
  marginRight: 10,
  headerHeight: 0,
  footerHeight: 0,
}

export function usePagination(initialConfig?: Partial<PageConfig>) {
  const pageConfig = ref<PageConfig>({ ...DEFAULT_CONFIG, ...initialConfig })
  const elements = ref<LayoutElement[]>([])

  // ─── Derived state ──────────────────────────────────────────────────────
  const bodyHeight = computed(() => calcBodyHeight(pageConfig.value))

  const remainingSpace = computed(() => calcRemainingSpace(pageConfig.value))

  const paginationResult = computed<PaginationResult>(() =>
    calculatePageBreaks(elements.value, pageConfig.value),
  )

  const pageBreaks = computed(() => paginationResult.value.pageBreaks)
  const currentPageCount = computed(() => paginationResult.value.pageCount)

  // ─── Actions ────────────────────────────────────────────────────────────

  function setPageConfig(config: Partial<PageConfig>) {
    pageConfig.value = { ...pageConfig.value, ...config }
  }

  function setElements(newElements: LayoutElement[]) {
    elements.value = newElements
  }

  function addElement(el: LayoutElement) {
    elements.value = [...elements.value, el]
  }

  function clearElements() {
    elements.value = []
  }

  // ─── Watch config and auto-recalculate (reactive via computed) ──────────
  // No explicit watcher needed — paginationResult is computed from pageConfig + elements

  return {
    pageConfig,
    elements,
    bodyHeight,
    remainingSpace,
    pageBreaks,
    currentPageCount,
    paginationResult,
    setPageConfig,
    setElements,
    addElement,
    clearElements,
    // exported pure functions for testing
    calcBodyHeight,
    calcRemainingSpace,
    calculatePageBreaks,
    calculateRemainingSpace,
    getPageDimensionsPx,
    buildHeaderFooterLayout,
    repositionFixedElement,
  }
}
