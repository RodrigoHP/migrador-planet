import { ref } from 'vue'
import { useLayoutStore } from '@/stores/layout'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

export interface BibliotecaCatalogItem {
  name: string
  versions: string[]
  activeVersion: string
}

export function useBibliotecas() {
  const layout = useLayoutStore()
  const catalog = ref<BibliotecaCatalogItem[]>([])
  const isLoading = ref(false)

  async function fetchCatalog() {
    isLoading.value = true
    try {
      const res = await fetch(`${API_BASE}/bibliotecas/catalog`)
      if (!res.ok) throw new Error('Failed to fetch catalog')
      catalog.value = await res.json()
    } finally {
      isLoading.value = false
    }
  }

  function updateVersion(name: string, version: string) {
    layout.bibliotecasVersions = { ...layout.bibliotecasVersions, [name]: version }
  }

  return { catalog, isLoading, fetchCatalog, updateVersion }
}
