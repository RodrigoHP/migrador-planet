/**
 * CSS Completion Provider for Monaco — suggests selectors from the template HTML.
 * Story 14.1 — AC4
 */

import type { Ref } from 'vue'

/** Extract IDs and classes from an HTML string via regex. */
export function extractSelectors(html: string): { ids: string[]; classes: string[] } {
  const ids: string[] = []
  const classes: string[] = []

  // Match id="value"
  const idRe = /\bid=["']([^"']+)["']/g
  let m: RegExpExecArray | null
  while ((m = idRe.exec(html)) !== null) {
    if (!ids.includes(m[1])) ids.push(m[1])
  }

  // Match class="value1 value2"
  const classRe = /\bclass=["']([^"']+)["']/g
  while ((m = classRe.exec(html)) !== null) {
    for (const cls of m[1].split(/\s+/)) {
      const trimmed = cls.trim()
      if (trimmed && !classes.includes(trimmed)) classes.push(trimmed)
    }
  }

  return { ids, classes }
}

/**
 * Register a CSS completion provider that suggests IDs and classes from
 * the template HTML. Returns a disposable.
 */
export function registerCssCompletionProvider(
  monaco: any,
  htmlContentRef: Ref<string>,
): { dispose: () => void } {
  const disposable = monaco.languages.registerCompletionItemProvider('css', {
    triggerCharacters: ['#', '.'],
    provideCompletionItems(model: any, position: any) {
      const textBeforeCursor = model.getValueInRange({
        startLineNumber: position.lineNumber,
        startColumn: 1,
        endLineNumber: position.lineNumber,
        endColumn: position.column,
      })

      const { ids, classes } = extractSelectors(htmlContentRef.value)
      const word = model.getWordUntilPosition(position)
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      }

      const suggestions: any[] = []

      // After '#' — suggest IDs
      if (textBeforeCursor.endsWith('#') || textBeforeCursor.match(/#[\w-]*$/)) {
        for (const id of ids) {
          suggestions.push({
            label: `#${id}`,
            kind: monaco.languages.CompletionItemKind.Value,
            insertText: id,
            range,
            detail: 'Template ID',
          })
        }
      }

      // After '.' — suggest classes
      if (textBeforeCursor.endsWith('.') || textBeforeCursor.match(/\.[\w-]*$/)) {
        for (const cls of classes) {
          suggestions.push({
            label: `.${cls}`,
            kind: monaco.languages.CompletionItemKind.Value,
            insertText: cls,
            range,
            detail: 'Template class',
          })
        }
      }

      return { suggestions }
    },
  })

  return disposable
}
