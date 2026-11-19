import { readFile } from 'node:fs/promises';
import { defineConfig, type Plugin } from 'vite';
import { rendererConfig } from './vite.shared';

function reviewProxy(): Plugin {
  return {
    name: 'f4-synthetic-review-proxy',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use('/__f4_review', async (request, response) => {
        const path = request.url || '';
        const method = request.method || '';
        const permitted = (method === 'POST' && path === '/reports/weekly')
          || (method === 'GET' && /^\/reports\/weekly\/(options|[A-Za-z0-9_-]+(?:\/excluded)?)$/.test(path))
          || (method === 'PATCH' && /^\/reports\/weekly\/[A-Za-z0-9_-]+$/.test(path));
        if (!permitted || (request.headers.origin && !['http://127.0.0.1:5174', 'http://localhost:5174'].includes(request.headers.origin))) {
          response.writeHead(403); response.end(); return;
        }
        try {
          const file = process.env.F4_REVIEW_TOKEN_FILE;
          if (!file) throw new Error('검토 토큰 미설정');
          const token = (await readFile(file, 'utf8')).trim();
          const chunks: Buffer[] = [];
          let size = 0;
          for await (const chunk of request) {
            size += chunk.length;
            if (size > 262144) throw new Error('검토 요청 크기 초과');
            chunks.push(chunk);
          }
          const upstream = await fetch(`http://127.0.0.1:8014${path}`, {
            method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
            body: ['POST', 'PATCH'].includes(method) ? Buffer.concat(chunks) : undefined,
            signal: AbortSignal.timeout(35000),
          });
          response.writeHead(upstream.status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
          response.end(await upstream.text());
        } catch {
          response.writeHead(503, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
          response.end(JSON.stringify({ error: { code: 'storage_unavailable', message: '검토 서버 연결을 확인하세요.' } }));
        }
      });
    },
  };
}

export default defineConfig({
  ...rendererConfig,
  plugins: [...(rendererConfig.plugins || []), reviewProxy()],
  server: { host: '127.0.0.1', port: 5174, strictPort: true },
});
