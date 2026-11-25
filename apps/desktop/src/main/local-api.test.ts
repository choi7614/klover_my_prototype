import { describe, expect, it } from 'vitest';
import { localRequest, MAX_RESPONSE_CHARS } from './local-api';

const local = { base: new URL('http://127.0.0.1:8000'), token: 'synthetic-local-token' };

describe('localRequest', () => {
  it('토큰·리다이렉트 금지·캐시 금지를 항상 붙인다', () => {
    const { url, init, signal } = localRequest(local, { method: 'GET', path: '/mails?limit=1', timeoutMs: 1000 });
    expect(url.href).toBe('http://127.0.0.1:8000/mails?limit=1');
    expect(init).toMatchObject({ method: 'GET', redirect: 'error', cache: 'no-store', body: undefined });
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer synthetic-local-token');
    expect(init.signal).toBe(signal);
  });

  it('본문이 있을 때만 JSON 헤더와 본문을 붙인다', () => {
    const withBody = localRequest(local, { method: 'POST', path: '/x', body: { a: 1 }, timeoutMs: 1000 });
    expect(withBody.init.body).toBe('{"a":1}');
    expect((withBody.init.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    const without = localRequest(local, { method: 'POST', path: '/x', timeoutMs: 1000 });
    expect(without.init.body).toBeUndefined();
    expect(without.init.headers as Record<string, string>).not.toHaveProperty('Content-Type');
  });

  it('주소는 로컬 서버 기준으로만 만든다', () => {
    expect(localRequest(local, { method: 'GET', path: '/a', timeoutMs: 1 }).url.origin).toBe('http://127.0.0.1:8000');
  });

  it('응답 크기 상한은 2,000,000자다', () => {
    expect(MAX_RESPONSE_CHARS).toBe(2_000_000);
  });
});
