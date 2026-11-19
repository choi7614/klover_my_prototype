// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import type { IpcMain, IpcMainInvokeEvent, WebContents } from 'electron';
import { registerF4IPC } from './f4-ipc';
import { f4Arguments, f4Channel, f4Operations } from '../shared/f4-bridge';

describe('제안 F4 통로', () => {
  it('다섯 동작만 등록하고 신뢰한 main frame의 요청만 처리한다', async () => {
    const frame = { url: 'file:///app/index.html#/report/weekly' };
    const contents = { mainFrame: frame, isDestroyed: () => false } as unknown as WebContents;
    const event = { sender: contents, senderFrame: frame } as unknown as IpcMainInvokeEvent;
    const handlers = new Map<string, (event: IpcMainInvokeEvent, ...args: unknown[]) => unknown>();
    const ipc = { handle: (channel: string, listener: (event: IpcMainInvokeEvent, ...args: unknown[]) => unknown) => handlers.set(channel, listener), removeHandler: (channel: string) => handlers.delete(channel) } as unknown as Pick<IpcMain, 'handle' | 'removeHandler'>;
    const client = { call: vi.fn(async () => ({ ok: true as const, data: {} })) };
    const dispose = registerF4IPC(ipc, contents, 'file:///app/index.html', client);
    expect([...handlers.keys()]).toEqual(f4Operations.map(f4Channel));
    await handlers.get(f4Channel('options'))!(event);
    expect(client.call).toHaveBeenCalledTimes(1);
    const other = { sender: contents, senderFrame: { url: 'https://outside.invalid' } } as unknown as IpcMainInvokeEvent;
    expect(await handlers.get(f4Channel('get'))!(other, 'id')).toMatchObject({ ok: false });
    const subframe = { sender: contents, senderFrame: { url: frame.url } } as unknown as IpcMainInvokeEvent;
    expect(await handlers.get(f4Channel('get'))!(subframe, 'id')).toMatchObject({ ok: false });
    expect(client.call).toHaveBeenCalledTimes(1);
    dispose(); expect(handlers.size).toBe(0);
  });
  it('소유자 주입·임의 주소·잘못된 저장 인수를 거부한다', () => {
    expect(f4Arguments('generate', [{ user_id: 'other' }])).toBeNull();
    expect(f4Arguments('get', ['../secret'])).toBeNull();
    expect(f4Arguments('options', ['extra'])).toBeNull();
    expect(f4Arguments('save', ['id', 0, []])).toBeNull();
    expect(f4Arguments('save', ['id', 1, []])).toEqual({ id: 'id', body: { expected_revision: 1, sections: [] } });
    expect(f4Arguments('generate', [{}])).toEqual({ body: {} });
  });
});
