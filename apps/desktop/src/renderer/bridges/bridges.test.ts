import { describe, expect, it, vi } from 'vitest';
import { createSearchIPCClient } from './search-ipc-client';
import { createF2IPCClient } from './f2-ipc-client';
import { F2Problem } from '../features/profile-draft';
import { SearchClientError, type SearchEvent } from '../features/search/contracts';
import type { SearchBridge, SearchMessage } from '../../shared/search-bridge';
import type { F2Bridge } from '../../shared/f2-bridge';

const parsed = { type: 'parsed', data: { search_id: 'b'.repeat(32), parsed: { filters: {}, topic: null, expansions: [] }, reference_date: '2026-11-19' } } as SearchEvent;

function fakeSearchBridge(script: (send: (message: SearchMessage) => void) => void) {
  let listener: ((id: string, message: SearchMessage) => void) | null = null;
  let current = '';
  const bridge: SearchBridge = {
    start: vi.fn(async (id: string) => { current = id; queueMicrotask(() => script(message => listener?.(current, message))); return { ok: true as const, data: null }; }),
    cancel: vi.fn().mockResolvedValue(undefined),
    recent: vi.fn().mockResolvedValue({ ok: true, data: [] }),
    onMessage: vi.fn(next => { listener = next; return () => { listener = null; }; }),
  };
  return bridge;
}

describe('화면 쪽 통로 변환기', () => {
  it('검색 단계를 차례로 넘기고 끝나면 멈춘다', async () => {
    const bridge = fakeSearchBridge(send => { send({ kind: 'event', event: parsed }); send({ kind: 'done' }); });
    const events: SearchEvent[] = [];
    for await (const event of createSearchIPCClient(bridge).search({ query: 'x' }, new AbortController().signal)) events.push(event);
    expect(events).toEqual([parsed]);
    expect(bridge.cancel).not.toHaveBeenCalled();
  });

  it('검색 실패와 형식 오류는 SearchClientError로 던진다', async () => {
    const failing = fakeSearchBridge(send => send({ kind: 'error', message: '검색 서버에 연결하지 못했어요.' }));
    await expect((async () => { for await (const _ of createSearchIPCClient(failing).search({ query: 'x' }, new AbortController().signal)) void _; })())
      .rejects.toThrow(new SearchClientError('검색 서버에 연결하지 못했어요.'));
    const malformed = fakeSearchBridge(send => send({ kind: 'event', event: { type: 'parsed', data: {} } }));
    await expect((async () => { for await (const _ of createSearchIPCClient(malformed).search({ query: 'x' }, new AbortController().signal)) void _; })())
      .rejects.toBeInstanceOf(SearchClientError);
  });

  it('화면이 취소하면 main에도 취소를 보낸다', async () => {
    const bridge = fakeSearchBridge(send => send({ kind: 'event', event: parsed }));
    const controller = new AbortController();
    const iterator = createSearchIPCClient(bridge).search({ query: 'x' }, controller.signal)[Symbol.asyncIterator]();
    expect((await iterator.next()).value).toEqual(parsed);
    const pending = iterator.next();
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
    expect(bridge.cancel).toHaveBeenCalledOnce();
  });

  it('F2 실패는 서버 문장 그대로 F2Problem으로 던진다', async () => {
    const call = vi.fn();
    const bridge = new Proxy({}, { get: () => call }) as F2Bridge;
    const client = createF2IPCClient(bridge);
    call.mockResolvedValueOnce({ ok: true, data: { exists: false } });
    await expect(client.profile()).resolves.toEqual({ exists: false });
    call.mockResolvedValueOnce({ ok: false, error: { code: 'ai_unavailable', message: 'AI 연결이 준비되지 않았어요.' } });
    await expect(client.createDraft({ mail_id: 'mail-1' } as never)).rejects.toEqual(new F2Problem('ai_unavailable', 'AI 연결이 준비되지 않았어요.'));
    call.mockRejectedValueOnce(new Error('ipc'));
    await expect(client.style()).rejects.toBeInstanceOf(F2Problem);
  });
});
