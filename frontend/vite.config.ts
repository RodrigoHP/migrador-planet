import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { resolve } from 'path'

export default defineConfig({
  plugins: [
    tailwindcss(),
    vue(),
  ],
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
  build: {
    rollupOptions: {
      output: {
        // PERF-003: Split Monaco into sub-chunks so language workers are loaded lazily.
        // monaco-core: editor UI + minimal runtime (always needed when Monaco opens)
        // monaco-languages: language-specific features (CSS, JSON, HTML, TS) — heavy, lazy
        // monaco-workers: worker infrastructure — deferred until editor activates language
        manualChunks(id) {
          if (id.includes('monaco-editor')) {
            if (
              id.includes('/language/') ||
              id.includes('/languages/') ||
              id.includes('/_deps/') ||
              id.includes('colorize') ||
              id.includes('tokenization') ||
              id.includes('css/cssWorker') ||
              id.includes('json/jsonWorker') ||
              id.includes('html/htmlWorker') ||
              id.includes('ts/tsWorker') ||
              id.includes('typescript/tsWorker')
            ) {
              return 'monaco-languages'
            }
            if (id.includes('worker') || id.includes('Worker')) {
              return 'monaco-workers'
            }
            return 'monaco-core'
          }
          if (id.includes('pdfjs-dist')) return 'pdfjs'
          if (id.includes('chart.js')) return 'chartjs'
          return undefined
        },
      },
    },
  },
})
