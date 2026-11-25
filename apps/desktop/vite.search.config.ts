// F3 독립 검사 전용. F0 진입점/라우터/빌드 설정을 바꾸지 않는다.
import { fileURLToPath, URL } from 'node:url';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';
import { rendererConfig } from './vite.shared';

export default defineConfig({
  root: fileURLToPath(new URL('./tests/f3', import.meta.url)),
  plugins: [react(), tailwindcss()],
  resolve: rendererConfig.resolve,
  server: { host: '127.0.0.1', port: 5183, strictPort: true },
  build: { outDir: '../../../../artifacts/f3-preview', emptyOutDir: false },
});
