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
    exclude: ['**/node_modules/**', '**/dist/**', 'e2e/**'],
  },
  build: {
    rollupOptions: {
      output: {
        // PERF-003: Split Monaco into 2 chunks (não 3).
        // monaco-core: editor + workers juntos — devem inicializar na mesma ordem
        //   (separar workers causava race condition: modulepreload carregava em paralelo
        //   e monaco-workers tentava ler serviceIds antes de monaco-core registrar)
        // monaco-languages: language features (CSS, JSON, HTML, TS) — genuinamente lazy
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
