// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { chmod, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createServer, type Server, type RequestListener } from 'node:http';
import type { AddressInfo } from 'node:net';
import { MailAPIClient, localAPIURL } from './mail-client';

const token = 'S'.repeat(43);
const session = { user_id: 'user-test', account_id: 'account-test', email: 'demo@example.invalid', sync_started_at: '2026-11-19T00:00:00+09:00' };
const summary = { mail_id: 'mail-1', subject: '합성 메일', from_addr: 'sender@example.invalid', from_name: '발신자', preview: '미리보기', received_at: '2026-11-19T01:00:00+09:00', is_read: false, analysis_status: 'pending' };
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
  directory = await mkdtemp(join(tmpdir(), 'klover-main-test-'));
  file = join(directory, 'mail-api-token');
  await writeFile(file, token + '\n', { mode: 0o600 });
});
afterEach(async () => {
  await Promise.all(servers.splice(0).map(server => new Promise<void>(resolve => { server.closeAllConnections(); server.close(() => resolve()); })));
  await rm(directory, { recursive: true, force: true });
});

describe('main 전용 메일 API', () => {
  it.each(['https://localhost:8000', 'http://outside.invalid', 'http://127.0.0.1.evil.invalid', 'http://user:secret@localhost', 'http://localhost/path', 'http://localhost/?token=bad', 'file:///tmp/secret'])('외부·다른 프로토콜·인증·경로 주소를 거부한다: %s', url => {
    expect(() => localAPIURL(url)).toThrow();
  });
  it('로컬 HTTP 주소와 기본 주소를 허용한다', () => {
    expect(localAPIURL().origin).toBe('http://127.0.0.1:8000');
    expect(localAPIURL('http://[::1]:8010').hostname).toBe('[::1]');
    expect(localAPIURL('http://localhost:8010').port).toBe('8010');
  });
  it('실제 Node HTTP 요청은 Origin 없이 토큰을 붙이고 필요한 데이터만 반환한다', async () => {
    const requests: { path: string; authorization: string | undefined; origin: string | undefined; method: string | undefined }[] = [];
    const baseURL = await listen((request, response) => {
      requests.push({ path: request.url!, authorization: request.headers.authorization, origin: request.headers.origin, method: request.method });
      response.setHeader('Content-Type', 'application/json');
      const value = request.url === '/auth/session' ? { ...session, token, access_token: token } : request.url?.startsWith('/mails?')
        ? { items: [{ ...summary, token }], next_cursor: null, token }
        : { ...summary, to: [], cc: [], body_text: '<img src="https://outside.invalid/x">텍스트', body_html: '<script>bad()</script>', token };
      response.end(JSON.stringify(value));
    });
    const client = new MailAPIClient({ baseURL, tokenFile: file });
    const account = await client.session();
    const page = await client.inbox({ limit: 20, cursor: 'opaque?x=/&q=1' });
    const mail = await client.detail('mail-1');
    expect(account).toEqual({ ok: true, data: session });
    expect(page).toEqual({ ok: true, data: { items: [summary], next_cursor: null } });
    expect(mail.ok && mail.data.body_text).toContain('<img');
    expect(JSON.stringify([account, page, mail])).not.toContain(token);
    expect(mail.ok && Object.keys(mail.data)).not.toContain('body_html');
    expect(requests).toHaveLength(3);
    expect(requests.every(request => request.authorization === `Bearer ${token}` && !request.origin && request.method === 'GET')).toBe(true);
    expect(new URL(requests[1].path, baseURL).searchParams.get('cursor')).toBe('opaque?x=/&q=1');
    expect(await readFile(file, 'utf8')).toBe(token + '\n');
  });
  it('분류 필터는 category 값으로 서버에 전달하고, 분류별 건수는 알려진 값만 넘긴다', async () => {
    const paths: string[] = [];
    const baseURL = await listen((request, response) => {
      paths.push(request.url!);
      response.setHeader('Content-Type', 'application/json');
      response.end(JSON.stringify(request.url === '/mails/category-counts'
        ? { total: 5, counts: { meeting: 2, notice: 1 }, token }
        : { items: [summary], next_cursor: null }));
    });
    const client = new MailAPIClient({ baseURL, tokenFile: file });
    expect((await client.inbox({ limit: 20, category: 'meeting' })).ok).toBe(true);
    expect(new URL(paths[0], baseURL).searchParams.get('category')).toBe('meeting');
    expect((await client.inbox({ limit: 20 })).ok).toBe(true);
    expect(new URL(paths[1], baseURL).searchParams.has('category')).toBe(false);
    const counts = await client.categoryCounts();
    expect(counts).toEqual({ ok: true, data: { total: 5, counts: { meeting: 2, notice: 1 } } });
    expect(JSON.stringify(counts)).not.toContain(token);
  });
  it('분류 값이 잘못됐거나 건수 응답이 이상하면 네트워크 호출 없이 또는 오류로 처리한다', async () => {
    const fetcher = vi.fn();
    expect((await new MailAPIClient({ tokenFile: file }, fetcher).inbox({ category: 'unknown' } as never)).ok).toBe(false);
    expect(fetcher).not.toHaveBeenCalled();
    for (const body of [{ total: -1, counts: {} }, { total: 1, counts: { other: 1 } }, { total: 1, counts: { meeting: 'x' } }, { counts: {} }, []]) {
      const bad = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 200 }));
      expect(await new MailAPIClient({ tokenFile: file }, bad).categoryCounts()).toMatchObject({ ok: false, error: { code: 'invalid_response' } });
    }
  });
  it('인수와 파일이 잘못되면 네트워크를 호출하지 않는다', async () => {
    const fetcher = vi.fn();
    const client = new MailAPIClient({ tokenFile: file }, fetcher);
    expect((await client.detail('../secret')).ok).toBe(false);
    expect((await client.inbox({ limit: 101 })).ok).toBe(false);
    expect((await client.inbox({ cursor: 'x'.repeat(1025) })).ok).toBe(false);
    expect((await client.inbox({ headers: { Authorization: 'bad' } } as never)).ok).toBe(false);
    await chmod(file, 0o644);
    expect(await client.session()).toMatchObject({ ok: false, error: { code: 'configuration' } });
    expect(await new MailAPIClient({ tokenFile: 'relative-path' }, fetcher).session()).toMatchObject({ ok: false, error: { code: 'configuration' } });
    expect(fetcher).not.toHaveBeenCalled();
  });
  it.each([[401, 'unauthorized'], [403, 'forbidden'], [404, 'not_found'], [422, 'invalid_request'], [503, 'unavailable']])('서버 오류 %s의 원문을 노출하지 않는다', async (status, code) => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { message: token + file } }), { status: Number(status) }));
    const result = await new MailAPIClient({ tokenFile: file }, fetcher).session();
    expect(result).toMatchObject({ ok: false, error: { code } });
    expect(JSON.stringify(result)).not.toContain(token);
    expect(JSON.stringify(result)).not.toContain(file);
    expect(fetcher.mock.calls[0][1]).toMatchObject({ method: 'GET', redirect: 'error', cache: 'no-store' });
    expect(fetcher.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
  });
  it('응답 형식 오류와 네트워크 예외를 일반 오류로 전달한다', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ token })))
      .mockRejectedValueOnce(new Error(token + file));
    const client = new MailAPIClient({ tokenFile: file }, fetcher);
    expect(await client.session()).toMatchObject({ ok: false, error: { code: 'invalid_response' } });
    const result = await client.session();
    expect(result).toMatchObject({ ok: false, error: { code: 'connection' } });
    expect(JSON.stringify(result)).not.toContain(token);
  });
  it('리디렉션에 인증 토큰을 전달하지 않는다', async () => {
    let leaked = false;
    const other = await listen((_request, response) => { leaked = true; response.end('{}'); });
    const baseURL = await listen((_request, response) => { response.writeHead(302, { Location: other }); response.end(); });
    expect(await new MailAPIClient({ baseURL, tokenFile: file }).session()).toMatchObject({ ok: false, error: { code: 'connection' } });
    expect(leaked).toBe(false);
  });
  it('새 메일 가져오기는 POST로 요청하고 건수만 반환하며 409·502를 구분한다', async () => {
    const requests: { path?: string; method?: string; origin?: string }[] = [];
    let status = 200;
    const baseURL = await listen((request, response) => {
      requests.push({ path: request.url, method: request.method, origin: request.headers.origin });
      response.statusCode = status;
      response.setHeader('Content-Type', 'application/json');
      response.end(JSON.stringify(status === 200
        ? { saved: 2, skipped: 1, mode: 'history', token_refreshed: false, token, subject: '숨김' }
        : { error: { code: 'x', message: '서버 문구' } }));
    });
    const client = new MailAPIClient({ baseURL, tokenFile: file });
    const result = await client.sync();
    expect(result).toEqual({ ok: true, data: { saved: 2, skipped: 1, mode: 'history', token_refreshed: false } });
    expect(JSON.stringify(result)).not.toContain(token);
    expect(requests).toEqual([{ path: '/mails/sync', method: 'POST', origin: undefined }]);
    status = 409;
    expect(await client.sync()).toMatchObject({ ok: false, error: { code: 'sync_in_progress' } });
    status = 502;
    expect(await client.sync()).toMatchObject({ ok: false, error: { code: 'gmail_unavailable' } });
    status = 503;
    expect(await client.sync()).toMatchObject({ ok: false, error: { code: 'unavailable' } });
  });
  it('새 메일 가져오기 응답 형식이 다르면 일반 오류로 전달한다', async () => {
    const baseURL = await listen((_request, response) => { response.setHeader('Content-Type', 'application/json'); response.end(JSON.stringify({ saved: '2' })); });
    expect(await new MailAPIClient({ baseURL, tokenFile: file }).sync()).toMatchObject({ ok: false, error: { code: 'invalid_response' } });
  });
});
