import type { Config } from 'tailwindcss'
import forms from '@tailwindcss/forms'

/**
 * Tailwind CSS v4 — design tokens live in main.css @theme (SSOT).
 * This config provides content paths and plugins only.
 * Do NOT duplicate color/spacing tokens here — edit @theme in main.css instead.
 */
export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  plugins: [forms],
} satisfies Config
