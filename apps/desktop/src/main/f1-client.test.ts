// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer, type RequestListener, type Server } from 'node:http';
import type { AddressInfo } from 'node:net';
import { F1APIClient } from './f1-client';

const token = 'S'.repeat(43);
const view = {
  mail_id: 'mail-1', analysis_status: 'done', category: 'work_request', ai_category: 'work_request', user_label: null,
  summary: '합성 요약입니다.', needs_reply: true, action_items: [{ text: '자료 송부', due: '2026-10-16' }],
  priority: 'high', priority_reason: '합성 이유', has_events: false, evidence_spans: [], failure_code: null,
};
let directory: string;
let file: string;
const servers: Server[] = [];
async function listen(handler: RequestListener): Promise<string> {
  const server = createServer(handler);
  servers.push(server);
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve));
  return `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
}
beforeEach(async () => {
  directory = await mkdtemp(join(tmpdir(), 'klover-f1-test-'));
  file = join(directory, 'mail-api-token');
  await writeFile(file, token + '\n', { mode: 0o600 });
});
afterEach(async () => {
  await Promise.all(servers.splice(0).map(server => new Promise<void>(resolve => { server.closeAllConnections(); server.close(() => resolve()); })));
  await rm(directory, { recursive: true, force: true });
});

describe('main 전용 F1 분석 API', () => {
  it('묶음 조회는 ids를 쿼리로 보내고 예상 밖 필드를 버린다', async () => {
    const seen: { url?: string; auth?: string; method?: string }[] = [];
    const base = await listen((request, response) => {
      seen.push({ url: request.url, auth: request.headers.authorization, method: request.method });
      response.setHeader('Content-Type', 'application/json');
      response.end(JSON.stringify({ items: [{ ...view, body_text: '원문' }], auto_analysis: 'ready', token: 'x' }));
    });
    const result = await new F1APIClient({ baseURL: base, tokenFile: file }).batch(['mail-1', 'mail-2']);
    expect(seen).toEqual([{ url: '/mails/analysis/batch?ids=mail-1&ids=mail-2', auth: `Bearer ${token}`, method: 'GET' }]);
    expect(result.ok && result.data.auto_analysis).toBe('ready');
    expect(result.ok && result.data.items[0]).not.toHaveProperty('body_text');
    expect(result.ok && result.data).not.toHaveProperty('token');
  });
  it('다시 시도는 POST로 보내고 서버 오류 코드를 화면 오류로 바꾼다', async () => {
    const statuses: [number, object][] = [
      [202, { mail_id: 'mail-1', analysis_status: 'pending' }],
      [503, { error: { code: 'analysis_unavailable', message: 'x' } }],
      [409, { error: { code: 'already_analyzed', message: 'x' } }],
      [404, { error: { code: 'not_found', message: 'x' } }],
      [503, { error: { code: 'service_unavailable', message: 'x' } }],
    ];
    const methods: string[] = [];
    const base = await listen((request, response) => {
      methods.push(`${request.method} ${request.url}`);
      const [status, body] = statuses.shift()!;
      response.statusCode = status;
      response.setHeader('Content-Type', 'application/json');
      response.end(JSON.stringify(body));
    });
    const client = new F1APIClient({ baseURL: base, tokenFile: file });
    expect(await client.retry('mail-1')).toEqual({ ok: true, data: { mail_id: 'mail-1', analysis_status: 'pending' } });
    for (const code of ['analysis_unavailable', 'already_analyzed', 'not_found', 'unavailable']) {
      expect(await client.retry('mail-1')).toMatchObject({ ok: false, error: { code } });
    }
    expect(methods[0]).toBe('POST /mails/mail-1/analysis/retry');
  });
  it('잘못된 인수·설정·응답은 서버에 보내지 않거나 거절한다', async () => {
    const base = await listen((_request, response) => { response.end(JSON.stringify({ items: [{ ...view, mail_id: 'other' }], auto_analysis: 'ready' })); });
    const client = new F1APIClient({ baseURL: base, tokenFile: file });
    expect(await client.batch([])).toMatchObject({ ok: false, error: { code: 'invalid_request' } });
    expect(await client.retry('../x')).toMatchObject({ ok: false, error: { code: 'invalid_request' } });
    expect(await client.batch(['mail-1'])).toMatchObject({ ok: false, error: { code: 'invalid_response' } });
    expect(await new F1APIClient({ baseURL: base }).batch(['mail-1'])).toMatchObject({ ok: false, error: { code: 'configuration' } });
    expect(await new F1APIClient({ baseURL: 'http://127.0.0.1:9', tokenFile: file }).batch(['mail-1'])).toMatchObject({ ok: false, error: { code: 'connection' } });
  });
});
