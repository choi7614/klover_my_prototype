import { describe, expect, it, vi } from 'vitest';
import { createSuggestionsIPCClient, unavailableSuggestionsClient } from './ipc-client';
import type { SuggestionsIPC } from './types';

function bridge(overrides: Partial<SuggestionsIPC> = {}): SuggestionsIPC {
  const ok = vi.fn(async () => ({ ok: true as const, data: { items: [] } }));
  return { list: ok, get: ok, approve: ok, dismiss: ok, conflicts: ok, todos: ok, createTodo: ok, updateTodo: ok, ...overrides } as unknown as SuggestionsIPC;
}

describe('F5 화면 IPC 어댑터', () => {
  it('성공 봉투의 data만 돌려주고 인수를 그대로 전달한다', async () => {
    const value = bridge();
    const client = createSuggestionsIPCClient(value);
    expect(await client.list({ mail_id: 'm1' })).toEqual({ items: [] });
    await client.approve('s1', { version: 2 });
    expect(value.approve).toHaveBeenCalledWith('s1', { version: 2 });
  });
  it('실패 코드·연결 예외·잘못된 응답을 Error 코드로 바꾼다', async () => {
    const client = createSuggestionsIPCClient(bridge({
      get: vi.fn(async () => ({ ok: false as const, error: { code: 'stale_version', message: 'x' } })),
      dismiss: vi.fn(async () => { throw new Error('secret detail'); }),
      todos: vi.fn(async () => null as never),
    }));
    await expect(client.get('s1')).rejects.toThrow('stale_version');
    await expect(client.dismiss('s1', { version: 1 })).rejects.toThrow('connection');
    await expect(client.todos({})).rejects.toThrow('invalid_response');
  });
  it('통로가 없으면 준비 중 오류만 낸다', async () => {
    await expect(unavailableSuggestionsClient.list({})).rejects.toThrow('suggestions_unavailable');
  });
});
