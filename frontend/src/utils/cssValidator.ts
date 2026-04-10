/**
 * Lightweight CSS validator using regex/heuristics.
 * Story 14.1 — AC5
 */

export interface CssMarker {
  startLineNumber: number
  endLineNumber: number
  startColumn: number
  endColumn: number
  message: string
  severity: 'error' | 'warning'
}

/** Validate CSS string and return markers for errors. */
export function validateCss(css: string): CssMarker[] {
  const markers: CssMarker[] = []
  const lines = css.split('\n')

  // Check unbalanced braces
  let braceDepth = 0
  let lastOpenLine = 0
  for (let i = 0; i < lines.length; i++) {
    for (const ch of lines[i]) {
      if (ch === '{') {
        braceDepth++
        lastOpenLine = i + 1
      } else if (ch === '}') {
        braceDepth--
        if (braceDepth < 0) {
          markers.push({
            startLineNumber: i + 1,
            endLineNumber: i + 1,
            startColumn: 1,
            endColumn: lines[i].length + 1,
            message: 'Unexpected closing brace "}"',
            severity: 'error',
          })
          braceDepth = 0
        }
      }
    }
  }
  if (braceDepth > 0) {
    markers.push({
      startLineNumber: lastOpenLine,
      endLineNumber: lastOpenLine,
      startColumn: 1,
      endColumn: lines[lastOpenLine - 1]?.length ?? 1,
      message: `Unclosed brace — ${braceDepth} opening "{" without matching "}"`,
      severity: 'error',
    })
  }

  // Check for common invalid properties inside rules
  const insideRuleRe = /^\s+([\w-]+)\s*:\s*(.+?)\s*;?\s*$/
  let inRule = false
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (line.includes('{')) inRule = true
    if (line.includes('}')) inRule = false

    if (inRule) {
      const match = insideRuleRe.exec(line)
      if (match) {
        const prop = match[1]
        const value = match[2]
        // Detect missing semicolons on non-last properties
        if (
          value &&
          !line.trimEnd().endsWith(';') &&
          !line.trimEnd().endsWith('{') &&
          !line.trimEnd().endsWith('}')
        ) {
          // Check if next non-empty line is another property (not closing brace)
          const nextLine = lines[i + 1]?.trim()
          if (
            nextLine &&
            nextLine !== '}' &&
            !nextLine.startsWith('/*') &&
            !nextLine.startsWith('//')
          ) {
            markers.push({
              startLineNumber: i + 1,
              endLineNumber: i + 1,
              startColumn: line.length,
              endColumn: line.length + 1,
              message: `Missing semicolon after "${prop}"`,
              severity: 'warning',
            })
          }
        }
      }
    }
  }

  return markers
}

/** Apply CSS validation markers to a Monaco editor model. */
export function applyCssMarkers(
  monaco: typeof import('monaco-editor'),
  model: import('monaco-editor').editor.ITextModel,
  css: string,
): number {
  const markers = validateCss(css)
  const monacoMarkers = markers.map((m) => ({
    startLineNumber: m.startLineNumber,
    endLineNumber: m.endLineNumber,
    startColumn: m.startColumn,
    endColumn: m.endColumn,
    message: m.message,
    severity: m.severity === 'error' ? monaco.MarkerSeverity.Error : monaco.MarkerSeverity.Warning,
  }))
  monaco.editor.setModelMarkers(model, 'css-validator', monacoMarkers)
  return markers.filter((m) => m.severity === 'error').length
}
