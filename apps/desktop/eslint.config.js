import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['out/**', 'node_modules/**', 'playwright-report/**', 'test-results/**', '*.config.*.mjs'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  { languageOptions: { globals: globals.node } },
  {
    files: ['src/renderer/**/*.{ts,tsx}'],
    languageOptions: { globals: globals.browser },
  },
  {
    files: ['scripts/smoke-electron.mjs', 'scripts/smoke-mail-read.mjs'],
    languageOptions: { globals: { ...globals.node, ...globals.browser } },
  },
);
