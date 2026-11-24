// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import type { IpcMain, IpcMainInvokeEvent, WebContents } from 'electron';
import { registerF1IPC } from './f1-ipc';
import { f1Channels } from '../shared/f1-bridge';

function setup() {
  const frame = { url: 'file:///app/renderer/index.html#/mail/inbox' };
  const contents = { mainFrame: frame, isDestroyed: () => false } as unknown as WebContents;
  const event = { sender: contents, senderFrame: frame } as unknown as IpcMainInvokeEvent;
  const handlers = new Map<string, (event: IpcMainInvokeEvent, ...args: unknown[]) => unknown>();
  const ipc = {
    handle: vi.fn((channel, listener) => handlers.set(channel, listener)),
    removeHandler: vi.fn(channel => handlers.delete(channel)),
  } as unknown as Pick<IpcMain, 'handle' | 'removeHandler'>;
  const client = { setCategory: vi.fn().mockResolvedValue({ ok: true, data: {} }), batch: vi.fn().mockResolvedValue({ ok: true, data: {} }), retry: vi.fn().mockResolvedValue({ ok: true, data: {} }) };
  const dispose = registerF1IPC(ipc, contents, 'file:///app/renderer/index.html', client);
  return { event, handlers, client, dispose, frame };
}

describe('F1 분석 IPC', () => {
  it('제한 통로만 등록하고 검사한 인수만 전달한다', async () => {
    const s = setup();
    expect([...s.handlers.keys()]).toEqual(Object.values(f1Channels));
    await s.handlers.get(f1Channels.batch)!(s.event, ['mail-1', 'mail-2']);
    expect(s.client.batch).toHaveBeenCalledWith(['mail-1', 'mail-2']);
    await s.handlers.get(f1Channels.retry)!(s.event, 'mail-1');
    expect(s.client.retry).toHaveBeenCalledWith('mail-1');
    for (const args of [[], [[]], [['../x']], [['a'], 'extra'], ['mail-1']]) {
      expect(await s.handlers.get(f1Channels.batch)!(s.event, ...args)).toMatchObject({ ok: false, error: { code: 'invalid_request' } });
    }
    for (const args of [[], ['../x'], ['a', 'b'], [1]]) {
      expect(await s.handlers.get(f1Channels.retry)!(s.event, ...args)).toMatchObject({ ok: false, error: { code: 'invalid_request' } });
    }
    expect(s.client.batch).toHaveBeenCalledTimes(1);
    expect(s.client.retry).toHaveBeenCalledTimes(1);
    await s.handlers.get(f1Channels.setCategory)!(s.event, 'mail-1', 'notice');
    expect(s.client.setCategory).toHaveBeenCalledWith('mail-1', 'notice');
    for (const args of [[], ['../x', 'notice'], ['mail-1', 'custom'], ['mail-1', 'notice', { user_id: 'other' }]]) {
      expect(await s.handlers.get(f1Channels.setCategory)!(s.event, ...args)).toMatchObject({ ok: false });
    }
    expect(s.client.setCategory).toHaveBeenCalledTimes(1);
    s.dispose();
    expect(s.handlers.size).toBe(0);
  });
  it('다른 화면·하위 프레임의 요청은 거절한다', async () => {
    const s = setup();
    const outside = { ...s.event, senderFrame: { url: 'https://outside.invalid/' } } as unknown as IpcMainInvokeEvent;
    expect(await s.handlers.get(f1Channels.batch)!(outside, ['mail-1'])).toMatchObject({ ok: false });
    expect(await s.handlers.get(f1Channels.setCategory)!(outside, 'mail-1', 'notice')).toMatchObject({ ok: false });
    expect(s.client.setCategory).not.toHaveBeenCalled();
    expect(s.client.batch).not.toHaveBeenCalled();
  });
});
