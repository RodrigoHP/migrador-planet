/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}

interface SaveFilePickerOptions {
  suggestedName?: string
  types?: Array<{ description?: string; accept: Record<string, string | string[]> }>
}

interface OpenFilePickerOptions {
  types?: Array<{ description?: string; accept: Record<string, string | string[]> }>
  multiple?: boolean
}

interface Window {
  showSaveFilePicker(options?: SaveFilePickerOptions): Promise<FileSystemFileHandle>
  showOpenFilePicker(options?: OpenFilePickerOptions): Promise<FileSystemFileHandle[]>
}
