import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vite';
import { rendererConfig } from './vite.shared';

// 공통 진입점·라우터를 바꾸지 않고 F2만 합성 응답으로 확인한다.
export default defineConfig({
  ...rendererConfig,
  root: fileURLToPath(new URL('./tests/f2-harness', import.meta.url)),
  server: { host: '127.0.0.1', port: 5175, strictPort: true },
});
