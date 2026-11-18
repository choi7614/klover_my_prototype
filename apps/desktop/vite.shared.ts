import { fileURLToPath, URL } from 'node:url';
import { randomBytes } from 'node:crypto';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import type { UserConfig } from 'vite';

const developmentNonce = randomBytes(24).toString('base64');

export const rendererConfig: UserConfig = {
  root: fileURLToPath(new URL('./src/renderer', import.meta.url)),
  base: './',
  plugins: [
    react(),
    tailwindcss(),
    {
      name: 'klover-development-csp',
      apply: 'serve',
      config() {
        return { html: { cspNonce: developmentNonce } };
      },
      // 개발 서버의 React 새로고침 스크립트만 허용하고, 빌드의 CSP는 그대로 유지한다.
      transformIndexHtml(html) {
        return html
          .replace("script-src 'self'", `script-src 'self' 'nonce-${developmentNonce}'`)
          .replace("style-src 'self'", `style-src 'self' 'nonce-${developmentNonce}'`)
          .replace("connect-src 'self'", "connect-src 'self' ws://127.0.0.1:5173");
      },
    },
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src/renderer', import.meta.url)),
      '@brand': fileURLToPath(new URL('./resources/brand', import.meta.url)),
    },
  },
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
};
