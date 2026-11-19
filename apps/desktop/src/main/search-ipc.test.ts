// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import type { IpcMain, IpcMainInvokeEvent, WebContents } from 'electron';
import { registerSearchIPC } from './search-ipc';
import { SearchClientError, type SearchClient, type SearchEvent } from '../renderer/features/search/contracts';
import { searchChannels, type SearchMessage } from '../shared/search-bridge';

const parsed = { type: 'parsed', data: { search_id: 'a'.repeat(32), parsed: { filters: {}, topic: null, expansions: [] }, reference_date: '2026-11-19' } } as SearchEvent;
const results = { type: 'results', data: { results: [], partial: [], semantic_enabled: false, truncated: false } } as SearchEvent;
const flush = () => new Promise(resolve => setTimeout(resolve, 0));

function setup(client: SearchClient | null) {
  const frame = { url: 'file:///app/renderer/index.html#/search' };
  const sent: [string, SearchMessage][] = [];
  const contents = {
    mainFrame: frame, isDestroyed: () => false,
    send: vi.fn((_channel: string, id: string, message: SearchMessage) => sent.push([id, message])),
  } as unknown as WebContents;
  const event = { sender: contents, senderFrame: frame } as unknown as IpcMainInvokeEvent;
  const handlers = new Map<string, (event: IpcMainInvokeEvent, ...args: unknown[]) => unknown>();
  const ipc = {
    handle: vi.fn((channel, listener) => handlers.set(channel, listener)),
    removeHandler: vi.fn(channel => handlers.delete(channel)),
  } as unknown as Pick<IpcMain, 'handle' | 'removeHandler'>;
  const dispose = registerSearchIPC(ipc, contents, 'file:///app/renderer/index.html', async () => client);
  return { frame, contents, event, handlers, sent, dispose };
}

describe('제한된 검색 IPC', () => {
  it('검색 단계를 받는 순서대로 같은 화면에 보내고 끝을 알린다', async () => {
    const search = vi.fn(async function* () { yield parsed; yield results; });
    const s = setup({ search, recent: vi.fn() });
    expect(await s.handlers.get(searchChannels.start)!(s.event, 'request-0001', { query: '지난주 견적 메일' })).toEqual({ ok: true, data: null });
    await flush();
    expect(search).toHaveBeenCalledWith({ query: '지난주 견적 메일' }, expect.any(AbortSignal));
    expect(s.sent).toEqual([
      ['request-0001', { kind: 'event', event: parsed }],
      ['request-0001', { kind: 'event', event: results }],
      ['request-0001', { kind: 'done' }],
    ]);
    expect(s.contents.send).toHaveBeenCalledWith(searchChannels.message, 'request-0001', { kind: 'done' });
  });

  it('검색 실패는 화면용 문장만 보낸다', async () => {
    const s = setup({
      // eslint-disable-next-line require-yield
      search: async function* () { throw new SearchClientError('검색 서버에 연결하지 못했어요.'); },
      recent: vi.fn(),
    });
    await s.handlers.get(searchChannels.start)!(s.event, 'request-0002', { query: 'x' });
    await flush();
    expect(s.sent).toEqual([['request-0002', { kind: 'error', message: '검색 서버에 연결하지 못했어요.' }]]);
  });

  it('취소하면 서버 요청을 끊고 더 보내지 않는다', async () => {
    let signal: AbortSignal | undefined;
    let release!: () => void;
    const gate = new Promise<void>(resolve => { release = resolve; });
    const s = setup({
      search: async function* (_request, aborted) { signal = aborted; yield parsed; await gate; yield results; },
      recent: vi.fn(),
    });
    await s.handlers.get(searchChannels.start)!(s.event, 'request-0003', { query: 'x' });
    await flush();
    await s.handlers.get(searchChannels.cancel)!(s.event, 'request-0003');
    expect(signal?.aborted).toBe(true);
    release();
    await flush();
    expect(s.sent).toEqual([['request-0003', { kind: 'event', event: parsed }]]);
  });

  it('잘못된 요청·다른 화면·설정 없음은 거부하고, 최근 검색은 결과를 감싸 돌려준다', async () => {
    const recent = vi.fn().mockResolvedValue([]);
    const s = setup({ search: vi.fn(), recent });
    const outside = { sender: s.contents, senderFrame: { url: 'https://outside.invalid/' } } as unknown as IpcMainInvokeEvent;
    for (const args of [['short', { query: 'x' }], ['request-0004', { query: 'x', owner: 'other' }], ['request-0004', { query: 1 }], ['request-0004']]) {
      expect(await s.handlers.get(searchChannels.start)!(s.event, ...args)).toMatchObject({ ok: false });
    }
    expect(await s.handlers.get(searchChannels.start)!(outside, 'request-0004', { query: 'x' })).toMatchObject({ ok: false });
    expect(await s.handlers.get(searchChannels.recent)!(outside)).toMatchObject({ ok: false });
    expect(await s.handlers.get(searchChannels.recent)!(s.event)).toEqual({ ok: true, data: [] });
    const none = setup(null);
    expect(await none.handlers.get(searchChannels.start)!(none.event, 'request-0005', { query: 'x' })).toMatchObject({ ok: false });
    s.dispose();
    expect(s.handlers.size).toBe(0);
  });
});
