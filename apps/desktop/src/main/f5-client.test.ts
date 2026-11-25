// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { F5APIClient } from './f5-client';

let directory: string;
let file: string;
const token = 'T'.repeat(43);
beforeEach(async () => {
  directory = await mkdtemp(join(tmpdir(), 'klover-f5-client-'));
  file = join(directory, 'synthetic-token');
  await writeFile(file, token, { mode: 0o600 });
});
afterEach(async () => { await rm(directory, { recursive: true, force: true }); });

describe('F5 main HTTP 경계', () => {
  it('고정 경로·메서드·토큰을 main에서만 사용한다', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{"suggestion_id":"s1"}'));
    const result = await new F5APIClient({ tokenFile: file }, fetcher).call('approve', { id: 's1', body: { version: 1 } });
    expect(result).toEqual({ ok: true, data: { suggestion_id: 's1' } });
    const [url, options] = fetcher.mock.calls[0];
    expect(url.href).toBe('http://127.0.0.1:8000/suggestions/s1/approve');
    expect(options).toMatchObject({ method: 'POST', redirect: 'error', cache: 'no-store', body: '{"version":1}' });
    expect(options.headers.Authorization).toBe(`Bearer ${token}`);
    expect(JSON.stringify(result)).not.toContain(token);
  });
  it('목록은 쿼리를 붙이고 items 배열을 확인한다', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(new Response('{"items":[],"next_cursor":null}')).mockResolvedValueOnce(new Response('{"items":null}'));
    const client = new F5APIClient({ tokenFile: file }, fetcher);
    expect(await client.call('list', { query: 'mail_id=m1' })).toEqual({ ok: true, data: { items: [], next_cursor: null } });
    expect(fetcher.mock.calls[0][0].href).toBe('http://127.0.0.1:8000/suggestions?mail_id=m1');
    expect(fetcher.mock.calls[0][1]).toMatchObject({ method: 'GET', body: undefined });
    expect(await client.call('todos', { query: '' })).toMatchObject({ ok: false, error: { code: 'invalid_response' } });
  });
  it('외부 주소 설정은 호출 전에 거부한다', async () => {
    const fetcher = vi.fn();
    expect(await new F5APIClient({ tokenFile: file, baseURL: 'https://outside.invalid' }, fetcher).call('get', { id: 's1' })).toMatchObject({ ok: false, error: { code: 'configuration' } });
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('서버 오류 코드만 전달하고 원문·예외를 노출하지 않는다', async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: 'stale_version', message: token + file } }), { status: 409 }))
      .mockResolvedValueOnce(new Response('', { status: 404 }))
      .mockRejectedValueOnce(new Error(token + file));
    const client = new F5APIClient({ tokenFile: file }, fetcher);
    const results = [await client.call('dismiss', { id: 's1', body: { version: 1 } }), await client.call('get', { id: 's1' }), await client.call('get', { id: 's1' })];
    expect(results[0]).toMatchObject({ ok: false, error: { code: 'stale_version' } });
    expect(results[1]).toMatchObject({ ok: false, error: { code: 'not_found' } });
    expect(results[2]).toMatchObject({ ok: false, error: { code: 'connection' } });
    expect(JSON.stringify(results)).not.toContain(token);
    expect(JSON.stringify(results)).not.toContain(file);
  });
});
