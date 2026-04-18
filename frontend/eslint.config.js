import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import tseslint from 'typescript-eslint'
import eslintConfigPrettier from 'eslint-config-prettier'

export default [
  // Base JS recommended rules
  js.configs.recommended,

  // TypeScript recommended rules
  ...tseslint.configs.recommended,

  // Vue 3 recommended rules
  ...pluginVue.configs['flat/recommended'],

  // Prettier — disables conflicting ESLint rules
  eslintConfigPrettier,

  // Global settings
  {
    files: ['**/*.{ts,tsx,vue}'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
        ecmaVersion: 'latest',
        sourceType: 'module',
      },
    },
    rules: {
      // Relax rules for gradual adoption
      '@typescript-eslint/no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      '@typescript-eslint/no-explicit-any': 'warn',
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'off',
      // Allow defineProps/defineEmits without import
      'no-undef': 'off',
      // Allow \/ in template literals (used to prevent <script> tag parsing)
      'no-useless-escape': 'warn',
      // Allow pre-declared variables that are assigned in all branches
      'no-useless-assignment': 'warn',
      // Disallow console.log/warn/info in production code (console.error allowed)
      'no-console': ['warn', { allow: ['error'] }],
    },
  },

  // Test files — relax strict rules (any and unused vars are common in test helpers)
  {
    files: ['**/*.spec.ts', '**/*.spec.tsx', '**/*.test.ts'],
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': 'off',
    },
  },

  // Ignore patterns
  {
    ignores: [
      'dist/**',
      'node_modules/**',
      'public/**',
      '*.config.js',
      '*.config.ts',
      'e2e/**',
    ],
  },
]
