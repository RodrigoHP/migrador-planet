// ─── Asset Service ────────────────────────────────────────────────────────────
// Handles communication with backend asset endpoints

const BASE_URL = '/api'

export interface AssetResponse {
  filename: string
  path: string
  size: number
  dimensions: { width: number; height: number }
}

export interface AssetInfo {
  filename: string
  path: string
  size: number
  thumbnailUrl: string
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `Erro HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

/**
 * Upload an asset file to the template's assets folder.
 */
export async function uploadAsset(templateId: string, file: File): Promise<AssetResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/templates/${templateId}/assets`, {
    method: 'POST',
    body: form,
  })
  return handleResponse<AssetResponse>(res)
}

/**
 * Delete an asset file from the template's assets folder.
 */
export async function deleteAsset(templateId: string, filename: string): Promise<void> {
  const res = await fetch(
    `${BASE_URL}/templates/${templateId}/assets/${encodeURIComponent(filename)}`,
    { method: 'DELETE' },
  )
  if (!res.ok) {
    let detail = `Erro HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = body.detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }
}

/**
 * List all assets in the template's assets folder.
 */
export async function listAssets(templateId: string): Promise<AssetInfo[]> {
  const res = await fetch(`${BASE_URL}/templates/${templateId}/assets`)
  return handleResponse<AssetInfo[]>(res)
}
