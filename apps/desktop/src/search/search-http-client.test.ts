import { afterEach, describe, expect, it, vi } from 'vitest';
import { readSearchEvent } from '../renderer/features/search/contracts';
import { createSearchHTTPClient } from './search-http-client';

afterEach(() => vi.unstubAllGlobals());

async function collect(client: ReturnType<typeof createSearchHTTPClient>) {
  const events = [];
  for await (const event of client.search({ query: '예산' }, new AbortController().signal)) events.push(event);
  return events;
}

describe('F3 Node HTTP 전송 경계', () => {
  it.each(['https://outside.invalid/', 'http://outside.invalid/', 'http://localhost/private', 'http://user:pass@localhost/'])('외부 또는 잘못된 주소를 거부한다: %s', (url) => {
    expect(() => createSearchHTTPClient(url, 'synthetic-token')).toThrow();
  });

  it('한국어 UTF-8와 줄 경계가 나뉜 스트림을 읽고 인증은 Node 요청에만 넣는다', async () => {
    const event = { type: 'error', data: { code: 'parser_unavailable', message: '해석 연결 준비 중' } };
    const encoded = new TextEncoder().encode(`${JSON.stringify(event)}\n`);
    const fetch = vi.fn<typeof globalThis.fetch>(async () => new Response(new ReadableStream({ start(controller) {
      for (const byte of encoded) controller.enqueue(new Uint8Array([byte]));
      controller.close();
    } }), { headers: { 'content-type': 'application/x-ndjson' } }));
    vi.stubGlobal('fetch', fetch);
    expect(await collect(createSearchHTTPClient('http://127.0.0.1:8000/', 'synthetic-token'))).toEqual([event]);
    expect(fetch.mock.calls[0][1]).toMatchObject({
      redirect: 'error', cache: 'no-store', headers: { Authorization: 'Bearer synthetic-token' },
    });
  });

  it('잘린/잘못된 JSON과 비공개 서버 오류를 성공으로 전달하지 않는다', async () => {
    for (const body of ['{"private":"synthetic-private"', 'synthetic-private\n']) {
      vi.stubGlobal('fetch', async () => new Response(body, { headers: { 'content-type': 'application/x-ndjson' } }));
      await expect(collect(createSearchHTTPClient('http://localhost/', 'test'))).rejects.not.toThrow('synthetic-private');
    }
    vi.stubGlobal('fetch', async () => new Response('synthetic-private-token', { status: 500 }));
    await expect(collect(createSearchHTTPClient('http://localhost/', 'test'))).rejects.not.toThrow('synthetic-private');
  });

  it('잘못된 날짜·중복 결과 번호를 거부한다', () => {
    expect(() => readSearchEvent({ type: 'parsed', data: {
      search_id: 'a'.repeat(32), reference_date: '2026-11-19',
      parsed: { topic: '예산', expansions: [], filters: { period: { start: 'invalid', end_before: '2026-11-19' } } },
    } })).toThrow();
    expect(() => readSearchEvent({ type: 'results', data: { results: [{}], partial: [], semantic_enabled: false, truncated: false } })).toThrow();
  });
});
