// @vitest-environment node
import { afterEach, expect, it, vi } from 'vitest';
import type { IpcMain, IpcMainInvokeEvent, WebContents } from 'electron';
import { registerHistoryIPC } from './history-ipc';
vi.mock('./mail-client', () => ({ readLocalAPI: vi.fn(async () => ({ base: new URL('http://127.0.0.1:8000'), token: 'synthetic-token' })) }));
afterEach(() => vi.unstubAllGlobals());
it('신뢰 화면·고정 동작만 허용하며 응답의 키·체크포인트를 제거한다', async () => {
  const frame = { url: 'file:///app/index.html#/settings/mail-history' };
  const contents = { mainFrame: frame, isDestroyed: () => false } as unknown as WebContents;
  const event = { sender: contents, senderFrame: frame } as unknown as IpcMainInvokeEvent;
  const handlers = new Map<string, (e: IpcMainInvokeEvent, ...args: unknown[]) => Promise<unknown>>();
  const ipc = { handle: vi.fn((c, fn) => handlers.set(c, fn)), removeHandler: vi.fn(c => handlers.delete(c)) } as unknown as IpcMain;
  const job = { job_id: 'a'.repeat(32), start: '2020-01-01', end: '2020-01-03', status: 'paused', saved: 1, skipped: 0, processed: 1, error: null };
  const fetcher = vi.fn(async () => new Response(JSON.stringify([{ ...job, api_key: 'synthetic-private-key', page_token: 'synthetic-page' }])));
  vi.stubGlobal('fetch', fetcher);
  const dispose = registerHistoryIPC(ipc, contents, 'file:///app/index.html', {});
  expect(await handlers.get('klover:history:list')!(event)).toEqual({ ok: true, data: [job] });
  expect(await handlers.get('klover:history:action')!(event, '../token', 'resume')).toMatchObject({ ok: false });
  expect(await handlers.get('klover:history:action')!({ ...event, senderFrame: { url: 'https://evil.invalid' } } as unknown as IpcMainInvokeEvent, 'a'.repeat(32), 'resume')).toMatchObject({ ok: false });
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect([...handlers.keys()]).toEqual(['klover:history:list', 'klover:history:start', 'klover:history:action']);
  dispose(); expect(handlers.size).toBe(0);
});
