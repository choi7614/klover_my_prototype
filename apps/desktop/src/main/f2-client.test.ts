// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer, type Server, type RequestListener } from 'node:http';
import type { AddressInfo } from 'node:net';
import { F2APIClient } from './f2-client';

const token = 'F'.repeat(43);
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
  directory = await mkdtemp(join(tmpdir(), 'klover-f2-test-'));
  file = join(directory, 'mail-api-token');
  await writeFile(file, token + '\n', { mode: 0o600 });
});
afterEach(async () => {
  await Promise.all(servers.splice(0).map(server => new Promise<void>(resolve => { server.closeAllConnections(); server.close(() => resolve()); })));
  await rm(directory, { recursive: true, force: true });
});

describe('main 전용 F2 서버 호출', () => {
  it('동작마다 정해진 방법·경로로 토큰을 붙여 부르고 본문을 JSON으로 보낸다', async () => {
    const seen: { method?: string; url?: string; auth?: string; body: string }[] = [];
    const base = await listen((request, response) => {
      let body = '';
      request.on('data', chunk => { body += chunk; });
      request.on('end', () => {
        seen.push({ method: request.method, url: request.url, auth: request.headers.authorization, body });
        response.writeHead(200, { 'Content-Type': 'application/json' }).end(JSON.stringify({ ok: 'synthetic' }));
      });
    });
    const client = new F2APIClient({ baseURL: base, tokenFile: file });
    await client.call('profile');
    await client.call('saveProfile', undefined, { profile: { name: '합성' } });
    await client.call('deleteStyle');
    await client.call('mail', 'mail-1');
    await client.call('saveDraft', 'draft-1', { body: '본문' });
    await client.call('reviseDraft', 'draft-1', { action: 'shorter' });
    expect(seen.map(row => `${row.method} ${row.url}`)).toEqual([
      'GET /profile', 'PUT /profile', 'DELETE /profile/style', 'GET /mails/mail-1', 'PATCH /drafts/draft-1', 'POST /drafts/draft-1/revise',
    ]);
    expect(seen.every(row => row.auth === `Bearer ${token}`)).toBe(true);
    expect(JSON.parse(seen[1].body)).toEqual({ profile: { name: '합성' } });
    expect(seen[0].body).toBe('');
  });

  it('서버 오류 {error:{code,message}}만 전달하고 다른 내용은 넘기지 않는다', async () => {
    let status = 503;
    let payload: unknown = { error: { code: 'ai_unavailable', message: 'AI 연결이 준비되지 않았어요.' }, secret: 'x' };
    const base = await listen((_request, response) => {
      response.writeHead(status, { 'Content-Type': 'application/json' }).end(typeof payload === 'string' ? payload : JSON.stringify(payload));
    });
    const client = new F2APIClient({ baseURL: base, tokenFile: file });
    expect(await client.call('createDraft', undefined, { mail_id: 'mail-1' })).toEqual({
      ok: false, error: { code: 'ai_unavailable', message: 'AI 연결이 준비되지 않았어요.' },
    });
    payload = { detail: 'stack trace' };
    expect(await client.call('profile')).toMatchObject({ ok: false, error: { code: 'unavailable' } });
    status = 200;
    payload = '[1,2]';
    expect(await client.call('profile')).toMatchObject({ ok: false, error: { code: 'invalid_response' } });
    payload = 'not json';
    expect(await client.call('profile')).toMatchObject({ ok: false, error: { code: 'invalid_response' } });
  });

  it('설정이 없거나 서버에 닿지 않으면 정해진 실패를 돌려준다', async () => {
    expect(await new F2APIClient({ baseURL: 'http://127.0.0.1:9', tokenFile: undefined }).call('profile'))
      .toMatchObject({ ok: false, error: { code: 'configuration' } });
    expect(await new F2APIClient({ baseURL: 'https://outside.invalid', tokenFile: file }).call('profile'))
      .toMatchObject({ ok: false, error: { code: 'configuration' } });
    expect(await new F2APIClient({ baseURL: 'http://127.0.0.1:9', tokenFile: file }).call('profile'))
      .toMatchObject({ ok: false, error: { code: 'connection' } });
  });
});
