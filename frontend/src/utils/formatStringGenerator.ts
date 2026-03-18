/**
 * Format String Generator — Story 7.8
 * Generates Knockout computed observables from format strings and style rules.
 */

export interface StyleRule {
  fieldPath: string
  operator: string
  value: string
  property: 'color' | 'background' | 'image' | 'visibility'
  propertyValue: string
}

/**
 * Parse fields from a format string.
 * Returns array of field paths found in {…} tokens (respecting \{ and \} escapes).
 */
export function parseFormatFields(formatString: string): string[] {
  const fields: string[] = []
  // Match {fieldPath} but not \{
  const regex = /(?<!\\)\{([^}]+)\}/g
  let match: RegExpExecArray | null
  while ((match = regex.exec(formatString)) !== null) {
    const field = match[1]
    if (field !== undefined) fields.push(field)
  }
  return fields
}

/**
 * Generate a Knockout computed function body from a format string.
 *
 * Example:
 *   input:  "{Logradouro}, {Numero} - {Bairro}"
 *   output: "ko.computed(function() { return data.Logradouro() + \", \" + data.Numero() + \" - \" + data.Bairro(); })"
 */
export function generateFormatComputed(formatString: string): string {
  if (!formatString.trim()) return ''

  // Split by field tokens, keeping track of literal parts and fields
  // We use a custom parser to handle \{ and \} as escaped literals
  const parts: string[] = []
  let current = ''
  let i = 0

  while (i < formatString.length) {
    if (formatString[i] === '\\' && i + 1 < formatString.length && (formatString[i + 1] === '{' || formatString[i + 1] === '}')) {
      // Escaped brace — treat as literal
      current += formatString[i + 1]
      i += 2
    } else if (formatString[i] === '{') {
      // Start of field token
      const end = formatString.indexOf('}', i + 1)
      if (end === -1) {
        // Unclosed brace — treat as literal
        current += formatString[i]
        i++
      } else {
        const fieldPath = formatString.slice(i + 1, end)
        if (current !== '') {
          parts.push(JSON.stringify(current))
          current = ''
        }
        parts.push(`data.${fieldPath}()`)
        i = end + 1
      }
    } else {
      current += formatString[i]
      i++
    }
  }

  if (current !== '') {
    parts.push(JSON.stringify(current))
  }

  if (parts.length === 0) return ''

  const body = parts.join(' + ')
  return `ko.computed(function() { return ${body}; })`
}

/**
 * Generate Knockout style bindings from an array of style rules.
 *
 * Example output:
 *   data-bind="style: { color: data.Status() === 'active' ? 'green' : '' }"
 */
export function generateStyleBindings(rules: StyleRule[]): string {
  if (rules.length === 0) return ''

  const activeRules = rules.filter((r) => r.fieldPath && r.operator && r.property)
  if (activeRules.length === 0) return ''

  // Group by CSS property to combine multiple rules for same property
  const cssPropertyMap: Record<string, string[]> = {}

  for (const rule of activeRules) {
    const condition = buildCondition(rule)
    const cssKey = toCssProperty(rule.property)
    const trueValue = buildPropertyValue(rule)

    const expression = `${condition} ? ${trueValue} : ''`
    if (!cssPropertyMap[cssKey]) cssPropertyMap[cssKey] = []
    cssPropertyMap[cssKey]!.push(expression)
  }

  const styleEntries = Object.entries(cssPropertyMap).map(([cssProp, exprs]) => {
    // If multiple rules for same property, use the last one (simplest approach)
    return `${cssProp}: ${exprs[exprs.length - 1]}`
  })

  return `data-bind="style: { ${styleEntries.join(', ')} }"`
}

function buildCondition(rule: StyleRule): string {
  const fieldAccess = `data.${rule.fieldPath}()`
  const safeValue = isNumeric(rule.value) ? rule.value : JSON.stringify(rule.value)

  switch (rule.operator) {
    case '==':
    case '===':
      return `${fieldAccess} === ${safeValue}`
    case '!=':
    case '!==':
      return `${fieldAccess} !== ${safeValue}`
    case '>':
      return `${fieldAccess} > ${safeValue}`
    case '>=':
      return `${fieldAccess} >= ${safeValue}`
    case '<':
      return `${fieldAccess} < ${safeValue}`
    case '<=':
      return `${fieldAccess} <= ${safeValue}`
    case 'contains':
      return `String(${fieldAccess}).includes(${JSON.stringify(rule.value)})`
    case 'notEmpty':
      return `!!${fieldAccess}`
    case 'empty':
      return `!${fieldAccess}`
    default:
      return `${fieldAccess} === ${safeValue}`
  }
}

function buildPropertyValue(rule: StyleRule): string {
  if (rule.property === 'visibility') {
    // visibility expects 'visible' or 'hidden'
    return JSON.stringify(rule.propertyValue || 'hidden')
  }
  return JSON.stringify(rule.propertyValue)
}

function toCssProperty(property: StyleRule['property']): string {
  switch (property) {
    case 'color':
      return 'color'
    case 'background':
      return 'background'
    case 'image':
      return 'backgroundImage'
    case 'visibility':
      return 'visibility'
    default:
      return property
  }
}

function isNumeric(value: string): boolean {
  return value !== '' && !isNaN(Number(value))
}
