import { fileURLToPath, URL } from 'node:url';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// F0의 앱·라우터·개발 서버 설정을 바꾸지 않는 별도 합성 데이터 화면이다.
export default defineConfig({
  root: fileURLToPath(new URL('..', import.meta.url)),
  plugins: [react(), tailwindcss()],
  resolve: { alias: {
    '@': fileURLToPath(new URL('../src/renderer', import.meta.url)),
    '@brand': fileURLToPath(new URL('../resources/brand', import.meta.url)),
  } },
  server: { host: '0.0.0.0', port: 5175, strictPort: true },
  build: {
    outDir: 'out/f5-preview',
    rollupOptions: { input: fileURLToPath(new URL('./index.html', import.meta.url)) },
  },
});
