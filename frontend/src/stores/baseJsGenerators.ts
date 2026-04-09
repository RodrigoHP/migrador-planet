/**
 * baseJsGenerators.ts — Story 9.5
 *
 * Generates JavaScript function bodies for the exported base.js file.
 * These functions mirror the Layout Engine algorithm from usePagination,
 * allowing runtime page-breaking to match the Canvas preview.
 */

/**
 * Generate the `quebrarTabelaEntrePaginas` function as a JavaScript string
 * to be injected into the exported base.js.
 *
 * The function mirrors the Layout Engine algorithm from usePagination:
 * - Iterates table rows top-to-bottom
 * - When accumulated height exceeds maxHeight, inserts a page break
 * - Repeats <thead> in each new page segment when repeatHeader=true
 */
export function generateQuebraTabelaFn(): string {
  return [
    '/**',
    ' * quebrarTabelaEntrePaginas — gerado por migrador-planet Story 9.5',
    ' * Quebra uma tabela em segmentos de página.',
    ' *',
    ' * @param {HTMLTableElement} tableEl   - elemento <table> a quebrar',
    ' * @param {number}           maxHeight - altura máxima disponível por página (px)',
    ' * @param {object}           [options]',
    ' * @param {boolean}          [options.repeatHeader=true]  - repetir <thead> em cada página',
    ' * @param {number}           [options.minRows=3]          - mínimo de linhas por segmento',
    ' * @returns {HTMLTableElement[]} array de segmentos de tabela',
    ' */',
    'function quebrarTabelaEntrePaginas(tableEl, maxHeight, options) {',
    '  var opts = Object.assign({ repeatHeader: true, minRows: 3 }, options || {});',
    '  var thead = tableEl.querySelector("thead");',
    '  var tbody = tableEl.querySelector("tbody");',
    '  if (!tbody) return [tableEl];',
    '  var rows = Array.from(tbody.querySelectorAll("tr"));',
    '  if (rows.length === 0) return [tableEl];',
    '  var headerHeight = thead ? thead.getBoundingClientRect().height : 0;',
    '  var availableHeight = maxHeight - headerHeight;',
    '  var segments = [];',
    '  var currentRows = [];',
    '  var currentHeight = 0;',
    '  rows.forEach(function(row) {',
    '    var rowHeight = row.getBoundingClientRect().height;',
    '    if (currentHeight + rowHeight > availableHeight && currentRows.length >= opts.minRows) {',
    '      segments.push(currentRows.slice());',
    '      currentRows = [row];',
    '      currentHeight = rowHeight;',
    '    } else {',
    '      currentRows.push(row);',
    '      currentHeight += rowHeight;',
    '    }',
    '  });',
    '  if (currentRows.length > 0) {',
    '    if (currentRows.length < opts.minRows && segments.length > 0) {',
    '      segments[segments.length - 1] = segments[segments.length - 1].concat(currentRows);',
    '    } else {',
    '      segments.push(currentRows);',
    '    }',
    '  }',
    '  return segments.map(function(segRows, idx) {',
    '    var newTable = tableEl.cloneNode(false);',
    '    if (thead && (idx === 0 || opts.repeatHeader)) {',
    '      newTable.appendChild(thead.cloneNode(true));',
    '    }',
    '    var newTbody = document.createElement("tbody");',
    '    segRows.forEach(function(r) { newTbody.appendChild(r.cloneNode(true)); });',
    '    newTable.appendChild(newTbody);',
    '    return newTable;',
    '  });',
    '}',
  ].join('\n')
}

/**
 * Generate the `reposicionarElementoFixo` function as a JavaScript string
 * to be injected into the exported base.js.
 *
 * The function repositions a fixed element below a dynamic reference element,
 * mirroring the Canvas Layout Engine repositioning logic from usePagination.
 *
 * @returns {string} JavaScript function source code
 */
export function generateReposicionarElementoFixoFn(): string {
  return [
    '/**',
    ' * reposicionarElementoFixo — gerado por migrador-planet Story 9.6',
    ' * Reposiciona um elemento fixo abaixo de um elemento de referência dinâmico.',
    ' *',
    ' * @param {HTMLElement} el          - elemento fixo a reposicionar',
    ' * @param {HTMLElement} referenceEl - elemento de referência (conteúdo dinâmico)',
    ' */',
    'function reposicionarElementoFixo(el, referenceEl) {',
    '  if (!el || !referenceEl) return;',
    "  var gap = parseInt(el.dataset.gap || '0', 10);",
    "  el.style.top = (referenceEl.offsetTop + referenceEl.offsetHeight + gap) + 'px';",
    '}',
  ].join('\n')
}

/**
 * Generate the `applyConditionalStyle` function as a JavaScript string
 * to be injected into the exported base.js.
 *
 * The function evaluates conditional style rules at runtime and applies
 * CSS properties (color, background, image src, etc.) to elements based
 * on data field values.
 *
 * @param rulesJson - JSON-serialized array of StyleRule objects to embed in the generated code
 * @returns JavaScript function source code (ES5, no dependencies)
 */
export function generateApplyConditionalStyleFn(rulesJson: string): string {
  return [
    '/**',
    ' * applyConditionalStyle — gerado por migrador-planet Story 38.2',
    ' * Aplica estilos condicionais a elementos baseado em regras e dados de campo.',
    ' *',
    ' * @param {object} data - objeto com valores dos campos (knockout observables unwrapped)',
    ' */',
    'function applyConditionalStyle(data) {',
    '  var rules = ' + rulesJson + ';',
    '  if (!rules || !rules.length || !data) return;',
    '  var elements = document.querySelectorAll("[data-conditional-style]");',
    '  for (var ei = 0; ei < elements.length; ei++) {',
    '    var el = elements[ei];',
    '    var elRuleIds = (el.getAttribute("data-conditional-style") || "").split(",");',
    '    for (var ri = 0; ri < elRuleIds.length; ri++) {',
    '      var ruleIdx = parseInt(elRuleIds[ri], 10);',
    '      if (isNaN(ruleIdx) || ruleIdx < 0 || ruleIdx >= rules.length) continue;',
    '      var rule = rules[ruleIdx];',
    '      if (!rule || !rule.fieldPath || !rule.property) continue;',
    '      var fieldVal = data[rule.fieldPath];',
    '      if (typeof fieldVal === "function") fieldVal = fieldVal();',
    '      var match = false;',
    '      var op = rule.operator;',
    '      var cmpVal = rule.value;',
    '      if (op === "===" || op === "==") {',
    '        match = String(fieldVal) === String(cmpVal);',
    '      } else if (op === "!==" || op === "!=") {',
    '        match = String(fieldVal) !== String(cmpVal);',
    '      } else if (op === ">") {',
    '        match = Number(fieldVal) > Number(cmpVal);',
    '      } else if (op === ">=") {',
    '        match = Number(fieldVal) >= Number(cmpVal);',
    '      } else if (op === "<") {',
    '        match = Number(fieldVal) < Number(cmpVal);',
    '      } else if (op === "<=") {',
    '        match = Number(fieldVal) <= Number(cmpVal);',
    '      } else if (op === "contains") {',
    '        match = String(fieldVal).indexOf(String(cmpVal)) !== -1;',
    '      } else if (op === "notEmpty") {',
    '        match = !!fieldVal;',
    '      } else if (op === "empty") {',
    '        match = !fieldVal;',
    '      }',
    '      if (match) {',
    '        var prop = rule.property;',
    '        var pVal = rule.propertyValue;',
    '        if (prop === "color") {',
    '          el.style.color = pVal;',
    '        } else if (prop === "background") {',
    '          el.style.backgroundColor = pVal;',
    '        } else if (prop === "image") {',
    '          var imgs = el.querySelectorAll("img");',
    '          for (var ii = 0; ii < imgs.length; ii++) {',
    '            imgs[ii].setAttribute("src", pVal);',
    '          }',
    '          if (imgs.length === 0 && el.tagName === "IMG") {',
    '            el.setAttribute("src", pVal);',
    '          }',
    '        } else if (prop === "visibility") {',
    '          el.style.visibility = pVal;',
    '        } else if (prop === "border-color") {',
    '          el.style.borderColor = pVal;',
    '        } else if (prop === "font-weight") {',
    '          el.style.fontWeight = pVal;',
    '        } else if (prop === "text-decoration") {',
    '          el.style.textDecoration = pVal;',
    '        } else if (prop === "opacity") {',
    '          el.style.opacity = pVal;',
    '        }',
    '      }',
    '    }',
    '  }',
    '}',
  ].join('\n')
}

/**
 * Generate the `criarNovaPagina` function as a JavaScript string
 * to be injected into the exported base.js.
 */
export function generateCriarNovaPaginaFn(): string {
  return [
    '/**',
    ' * criarNovaPagina — gerado por migrador-planet Story 9.5',
    ' * Cria um novo elemento de página no container de documento.',
    ' *',
    ' * @param {HTMLElement} container - elemento container do documento',
    ' * @param {number}      pageNum   - número da nova página',
    ' * @returns {HTMLElement} elemento de página criado',
    ' */',
    'function criarNovaPagina(container, pageNum) {',
    '  var page = document.createElement("div");',
    '  page.className = "page";',
    '  page.setAttribute("data-page", String(pageNum));',
    '  container.appendChild(page);',
    '  return page;',
    '}',
  ].join('\n')
}
