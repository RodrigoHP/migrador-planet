import type { Config } from 'tailwindcss'
import forms from '@tailwindcss/forms'

export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: { 600: '#2563EB', 700: '#1D4ED8' },
        success: { 600: '#16A34A' },
        warning: { 500: '#EAB308' },
        error: { 600: '#DC2626' },
        neutral: {
          50: '#FAFAFA',
          100: '#F5F5F5',
          200: '#E5E5E5',
          500: '#737373',
          700: '#404040',
          800: '#262626',
          900: '#171717',
        },
      },
    },
  },
  plugins: [forms],
} satisfies Config
