/**
 * usePreExportValidation — Story 8.2 stub
 *
 * Full implementation in Story 8.5.
 * Currently always returns no blocking errors so export is always allowed.
 */
export interface PreExportError {
  code: string
  message: string
  blocking: boolean
}

export interface PreExportValidationResult {
  hasBlockingErrors: boolean
  errors: PreExportError[]
}

export function usePreExportValidation() {
  /**
   * Validate the current editor state before export.
   * Returns a result object with hasBlockingErrors and errors list.
   * Stub: always passes until Story 8.5 is implemented.
   */
  function validate(): PreExportValidationResult {
    return { hasBlockingErrors: false, errors: [] }
  }

  return { validate }
}
