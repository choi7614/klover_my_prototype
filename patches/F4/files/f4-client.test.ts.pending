// @vitest-environment node
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { F4APIClient } from './f4-client';

let directory: string;
let file: string;
const token = 'T'.repeat(43);
beforeEach(async () => {
  directory = await mkdtemp(join(tmpdir(), 'klover-f4-client-'));
  file = join(directory, 'synthetic-token');
  await writeFile(file, token, { mode: 0o600 });
});
afterEach(async () => { await rm(directory, { recursive: true, force: true }); });

describe('제안 F4 main HTTP 경계', () => {
  it('고정 경로·메서드·토큰을 main에서만 사용한다', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}'));
    const result = await new F4APIClient({ tokenFile: file }, fetcher).call('generate', undefined, { recipient: '팀장' });
    expect(result).toEqual({ ok: true, data: {} });
    const [url, options] = fetcher.mock.calls[0];
    expect(url.href).toBe('http://127.0.0.1:8000/reports/weekly');
    expect(options).toMatchObject({ method: 'POST', redirect: 'error', cache: 'no-store', body: '{"recipient":"팀장"}' });
    expect(options.headers.Authorization).toBe(`Bearer ${token}`);
    expect(options.headers.Origin).toBeUndefined();
    expect(options.signal).toBeInstanceOf(AbortSignal);
    expect(JSON.stringify(result)).not.toContain(token);
  });
  it('외부 주소 설정은 호출 전에 거부한다', async () => {
    const fetcher = vi.fn();
    expect(await new F4APIClient({ tokenFile: file, baseURL: 'https://outside.invalid' }, fetcher).call('options')).toMatchObject({ ok: false, error: { code: 'configuration' } });
    expect(fetcher).not.toHaveBeenCalled();
  });
  it('서버·네트워크 예외의 원문을 노출하지 않는다', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ error: { code: 'ai_failed', message: token + file } }), { status: 502 })).mockRejectedValueOnce(new Error(token + file));
    const client = new F4APIClient({ tokenFile: file }, fetcher);
    const results = [await client.call('generate'), await client.call('get', 'id')];
    expect(results[0]).toMatchObject({ ok: false, error: { code: 'ai_failed' } });
    expect(results[1]).toMatchObject({ ok: false, error: { code: 'connection' } });
    expect(JSON.stringify(results)).not.toContain(token);
    expect(JSON.stringify(results)).not.toContain(file);
  });
  it('제외 목록의 배열과 잘못된 응답을 구분한다', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(new Response('[]')).mockResolvedValueOnce(new Response('[]')).mockResolvedValueOnce(new Response('null'));
    const client = new F4APIClient({ tokenFile: file }, fetcher);
    expect(await client.call('excluded', 'id')).toEqual({ ok: true, data: [] });
    expect(await client.call('get', 'id')).toMatchObject({ ok: false, error: { code: 'invalid_response' } });
    expect(await client.call('options')).toMatchObject({ ok: false });
  });
});
