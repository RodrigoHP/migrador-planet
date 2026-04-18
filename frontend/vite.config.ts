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
        // Monaco não é dividido manualmente — dependências circulares internas
        // do monaco-editor causam TDZ e race condition em qualquer split manual.
        // Monaco já é lazy (defineAsyncComponent + await import()) então Rollup
        // cria chunk(s) naturalmente sem quebrar inicialização.
        manualChunks(id) {
          if (id.includes('pdfjs-dist')) return 'pdfjs'
          if (id.includes('chart.js')) return 'chartjs'
          return undefined
        },
      },
    },
  },
})
