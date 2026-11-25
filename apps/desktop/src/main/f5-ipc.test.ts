// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import { shell } from 'electron';
vi.mock('electron', () => ({ shell: { openExternal: vi.fn(async () => {}) } }));
import type { IpcMain, IpcMainInvokeEvent, WebContents } from 'electron';
import { registerF5IPC } from './f5-ipc';
import { f5Arguments, f5Channel, f5Operations, f5Routes } from '../shared/f5-bridge';

describe('F5 제안·할 일 통로', () => {
  it('여덟 동작만 등록하고 신뢰한 main frame의 요청만 처리한다', async () => {
    const frame = { url: 'file:///app/index.html#/todos' };
    const contents = { mainFrame: frame, isDestroyed: () => false } as unknown as WebContents;
    const event = { sender: contents, senderFrame: frame } as unknown as IpcMainInvokeEvent;
    const handlers = new Map<string, (event: IpcMainInvokeEvent, ...args: unknown[]) => unknown>();
    const ipc = { handle: (channel: string, listener: (event: IpcMainInvokeEvent, ...args: unknown[]) => unknown) => handlers.set(channel, listener), removeHandler: (channel: string) => handlers.delete(channel) } as unknown as Pick<IpcMain, 'handle' | 'removeHandler'>;
    const client = { call: vi.fn(async () => ({ ok: true as const, data: {} })) };
    const dispose = registerF5IPC(ipc, contents, 'file:///app/index.html', client);
    expect([...handlers.keys()]).toEqual(f5Operations.map(f5Channel));
    expect([...handlers.keys()].some(channel => channel.includes('event'))).toBe(false);
    await handlers.get(f5Channel('list'))!(event, { mail_id: 'm1' });
    expect(client.call).toHaveBeenCalledWith('list', { query: 'mail_id=m1' });
    const other = { sender: contents, senderFrame: { url: 'https://outside.invalid' } } as unknown as IpcMainInvokeEvent;
    expect(await handlers.get(f5Channel('get'))!(other, 'id')).toMatchObject({ ok: false });
    const subframe = { sender: contents, senderFrame: { url: frame.url } } as unknown as IpcMainInvokeEvent;
    expect(await handlers.get(f5Channel('approve'))!(subframe, 'id', { version: 1 })).toMatchObject({ ok: false });
    expect(await handlers.get(f5Channel('approve'))!(event, 'id', {})).toMatchObject({ ok: false });
    expect(client.call).toHaveBeenCalledTimes(1);
    expect(await handlers.get(f5Channel('connectCalendar'))!(other)).toMatchObject({ ok: false });
    expect(shell.openExternal).not.toHaveBeenCalled();
    expect(await handlers.get(f5Channel('connectCalendar'))!(event, 'https://outside.invalid')).toMatchObject({ ok: false });
    expect(shell.openExternal).not.toHaveBeenCalled();
    await handlers.get(f5Channel('connectCalendar'))!(event);
    expect(shell.openExternal).toHaveBeenCalledWith('http://localhost:8000/auth/google');
    dispose(); expect(handlers.size).toBe(0);
  });
  it('승인·무시는 version이 있어야 하고 정해진 필드만 보낸다', () => {
    expect(f5Arguments('approve', ['s1', { version: 0 }])).toBeNull();
    expect(f5Arguments('approve', ['s1', { version: 1, user_id: 'other' }])).toBeNull();
    expect(f5Arguments('approve', ['s1', { version: 1, payload: 'text' }])).toBeNull();
    expect(f5Arguments('approve', ['s1', { version: 2, payload: { title: 'x' } }])).toEqual({ id: 's1', body: { version: 2, payload: { title: 'x' } } });
    expect(f5Arguments('dismiss', ['s1', { version: 1, payload: {} }])).toBeNull();
    expect(f5Arguments('dismiss', ['s1', { version: 3 }])).toEqual({ id: 's1', body: { version: 3 } });
    // 다시 등록은 version만 받고 내용(payload)은 받지 않는다.
    expect(f5Arguments('reregister', ['s1', { version: 3, payload: {} }])).toBeNull();
    expect(f5Arguments('reregister', ['s1', { version: 3 }])).toEqual({ id: 's1', body: { version: 3 } });
    expect(f5Routes.reregister.path({ id: 's1' })).toBe('/suggestions/s1/reregister');
    expect(f5Arguments('approve', ['s1', { version: 1, payload: { title: 'x'.repeat(30000) } }])).toBeNull();
  });
  it('경로 조작·소유자 주입·허용하지 않은 조회 조건을 거부한다', () => {
    expect(f5Arguments('get', ['../secret'])).toBeNull();
    expect(f5Arguments('get', ['a/b'])).toBeNull();
    expect(f5Arguments('list', [{ notified: false }])).toBeNull();
    expect(f5Arguments('list', [{ status: 'executing' }])).toBeNull();
    expect(f5Arguments('list', [{ limit: 101 }])).toBeNull();
    expect(f5Arguments('list', [{ mail_id: 'm1', status: 'pending', limit: 50, cursor: 'c&x=1' }])).toEqual({ query: 'status=pending&limit=50&cursor=c%26x%3D1&mail_id=m1' });
    expect(f5Arguments('todos', [{ mail_id: 'm1' }])).toBeNull();
    expect(f5Arguments('todos', [{}])).toEqual({ query: '' });
    expect(f5Arguments('todos', [])).toBeNull();
    expect(f5Routes.list.path({ query: '' })).toBe('/suggestions');
    expect(f5Routes.approve.path({ id: 's1' })).toBe('/suggestions/s1/approve');
  });
  it('할 일 추가·수정 인수의 모양과 크기를 검사한다', () => {
    expect(f5Arguments('createTodo', [{ title: '할 일', request_id: 'r-1' }])).toEqual({ body: { title: '할 일', request_id: 'r-1' } });
    expect(f5Arguments('createTodo', [{ title: ' ', request_id: 'r-1' }])).toBeNull();
    expect(f5Arguments('createTodo', [{ title: 'x'.repeat(301), request_id: 'r-1' }])).toBeNull();
    expect(f5Arguments('createTodo', [{ title: 'a', request_id: 'r-1', due: '11/20' }])).toBeNull();
    expect(f5Arguments('createTodo', [{ title: 'a', request_id: 'r-1', account_id: 'x' }])).toBeNull();
    expect(f5Arguments('updateTodo', ['t1', { version: 1 }])).toBeNull();
    expect(f5Arguments('updateTodo', ['t1', { version: 1, status: 'deleted' }])).toBeNull();
    expect(f5Arguments('updateTodo', ['t1', { version: 1, status: 'completed' }])).toEqual({ id: 't1', body: { version: 1, status: 'completed' } });
  });
});
