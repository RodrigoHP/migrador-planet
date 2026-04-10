// ─── Image Validation ─────────────────────────────────────────────────────────

export const MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024 // 5 MB

export const ALLOWED_MIME_TYPES = [
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/svg+xml',
] as const

export interface ValidationResult {
  valid: boolean
  errors: string[]
}

/**
 * Load image dimensions from a File using the browser Image API.
 * SVG files are not dimension-checked (they can be any size).
 */
function loadImageDimensions(file: File): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      resolve({ width: img.naturalWidth, height: img.naturalHeight })
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('Não foi possível carregar a imagem para verificar as dimensões.'))
    }
    img.src = url
  })
}

/**
 * Validate an image file before upload.
 * Returns { valid, errors } — errors contains PT-BR messages.
 */
export async function validateImageFile(file: File): Promise<ValidationResult> {
  const errors: string[] = []

  // Validate MIME type
  if (!(ALLOWED_MIME_TYPES as readonly string[]).includes(file.type)) {
    errors.push(`Tipo de arquivo não suportado: "${file.type}". São aceitos: PNG, JPG, WEBP e SVG.`)
  }

  // Validate file size
  if (file.size > MAX_IMAGE_SIZE_BYTES) {
    const sizeMB = (file.size / (1024 * 1024)).toFixed(1)
    errors.push(`Arquivo muito grande: ${sizeMB} MB. O tamanho máximo permitido é 5 MB.`)
  }

  // Validate dimensions (skip SVG — vector, no fixed dimensions)
  if (file.type !== 'image/svg+xml' && errors.length === 0) {
    try {
      const dims = await loadImageDimensions(file)
      if (dims.width < 10 || dims.height < 10) {
        errors.push(
          `Dimensões muito pequenas: ${dims.width}×${dims.height} px. O mínimo é 10×10 px.`,
        )
      }
    } catch {
      errors.push('Não foi possível verificar as dimensões da imagem.')
    }
  }

  return { valid: errors.length === 0, errors }
}
