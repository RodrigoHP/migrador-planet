/**
 * useFileSystem — File picker composable using File System Access API
 * with fallback to <input type="file">
 */

type LocalFilePickerAcceptType = {
  description?: string
  accept: Record<string, string[]>
}

const hasFileSystemAccess = 'showOpenFilePicker' in window

async function pickFile(
  types: LocalFilePickerAcceptType[],
): Promise<{ file: File; buffer: ArrayBuffer } | null> {
  let file: File | null = null

  if (hasFileSystemAccess) {
    try {
      const [handle] = await window.showOpenFilePicker({ types, multiple: false })
      if (!handle) return null
      file = await handle.getFile()
    } catch (e: any) {
      if (e.name === 'AbortError') return null
      throw e
    }
  } else {
    file = await pickViaInput(types)
  }

  if (!file) return null
  const buffer = await file.arrayBuffer()
  return { file, buffer }
}

function pickViaInput(types: LocalFilePickerAcceptType[]): Promise<File | null> {
  return new Promise((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    const allExts = types.flatMap((t) => Object.values(t.accept).flat())
    input.accept = allExts.join(',')
    input.onchange = () => resolve(input.files?.[0] ?? null)
    input.oncancel = () => resolve(null)
    input.click()
  })
}

export function useFileSystem() {
  async function pickPDF() {
    return pickFile([{ description: 'PDF', accept: { 'application/pdf': ['.pdf'] } }])
  }

  async function pickXSD() {
    return pickFile([{ description: 'XSD', accept: { 'text/xml': ['.xsd'] } }])
  }

  async function pickData() {
    return pickFile([
      {
        description: 'JSON / XML',
        accept: { 'application/json': ['.json'], 'text/xml': ['.xml'] },
      },
    ])
  }

  return { pickPDF, pickXSD, pickData, hasFileSystemAccess }
}
