// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import type { IpcMain, IpcMainInvokeEvent, WebContents } from 'electron';
import { registerF2IPC } from './f2-ipc';
import { f2Channel, f2Operations } from '../shared/f2-bridge';

function setup() {
  const frame = { url: 'file:///app/renderer/index.html#/settings/profile' };
  const contents = { mainFrame: frame, isDestroyed: () => false } as unknown as WebContents;
  const event = { sender: contents, senderFrame: frame } as unknown as IpcMainInvokeEvent;
  const handlers = new Map<string, (event: IpcMainInvokeEvent, ...args: unknown[]) => unknown>();
  const ipc = {
    handle: vi.fn((channel, listener) => handlers.set(channel, listener)),
    removeHandler: vi.fn(channel => handlers.delete(channel)),
  } as unknown as Pick<IpcMain, 'handle' | 'removeHandler'>;
  const client = { call: vi.fn().mockResolvedValue({ ok: true, data: {} }) };
  const dispose = registerF2IPC(ipc, contents, 'file:///app/renderer/index.html', client);
  return { frame, contents, event, handlers, client, dispose };
}

describe('제한된 F2 IPC', () => {
  it('정해진 10개 동작만 등록하고 발송 통로는 없다', () => {
    const s = setup();
    expect([...s.handlers.keys()]).toEqual(f2Operations.map(f2Channel));
    expect(s.handlers.size).toBe(10);
    expect([...s.handlers.keys()].some(channel => /send/i.test(channel))).toBe(false);
    s.dispose();
    expect(s.handlers.size).toBe(0);
  });

  it('동작별 인수 모양이 맞을 때만 서버를 부른다', async () => {
    const s = setup();
    await s.handlers.get(f2Channel('profile'))!(s.event);
    await s.handlers.get(f2Channel('saveProfile'))!(s.event, { name: '합성' });
    await s.handlers.get(f2Channel('reviseDraft'))!(s.event, 'draft-1', { action: 'shorter' });
    expect(s.client.call.mock.calls).toEqual([
      ['profile', undefined, undefined],
      ['saveProfile', undefined, { name: '합성' }],
      ['reviseDraft', 'draft-1', { action: 'shorter' }],
    ]);
    const rejected = [
      [f2Channel('profile'), ['extra']],
      [f2Channel('saveProfile'), []],
      [f2Channel('saveProfile'), [['array']]],
      [f2Channel('mail'), ['../secret']],
      [f2Channel('draft'), [{ id: 'x' }]],
      [f2Channel('saveDraft'), ['draft-1']],
      [f2Channel('saveDraft'), ['bad id', {}]],
      [f2Channel('preview'), [{ text: 'x'.repeat(200_001) }]],
    ] as const;
    for (const [channel, args] of rejected) {
      expect(await s.handlers.get(channel)!(s.event, ...args)).toMatchObject({ ok: false, error: { code: 'invalid_request' } });
    }
    expect(s.client.call).toHaveBeenCalledTimes(3);
  });

  it('다른 화면·하위 프레임에서 온 요청은 거부한다', async () => {
    const s = setup();
    const outside = { sender: s.contents, senderFrame: { url: 'https://outside.invalid/' } } as unknown as IpcMainInvokeEvent;
    const subframe = { sender: s.contents, senderFrame: { url: s.frame.url } } as unknown as IpcMainInvokeEvent;
    for (const event of [outside, subframe]) {
      expect(await s.handlers.get(f2Channel('profile'))!(event)).toMatchObject({ ok: false, error: { code: 'invalid_request' } });
    }
    expect(s.client.call).not.toHaveBeenCalled();
  });
});
