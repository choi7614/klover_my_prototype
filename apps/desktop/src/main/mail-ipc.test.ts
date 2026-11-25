// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import type { IpcMain, IpcMainInvokeEvent, WebContents } from 'electron';
import { developmentRendererURL, registerMailReadIPC } from './mail-ipc';
import { mailCategoryCountsChannel, mailChannels, mailSyncChannel } from '../shared/mail-read';

function setup() {
  const frame = { url: 'file:///app/renderer/index.html#/mail/inbox' };
  const contents = { mainFrame: frame, isDestroyed: () => false } as unknown as WebContents;
  const event = { sender: contents, senderFrame: frame } as unknown as IpcMainInvokeEvent;
  const handlers = new Map<string, (event: IpcMainInvokeEvent, ...args: unknown[]) => unknown>();
  const ipc = {
    handle: vi.fn((channel, listener) => handlers.set(channel, listener)),
    removeHandler: vi.fn(channel => handlers.delete(channel)),
  } as unknown as Pick<IpcMain, 'handle' | 'removeHandler'>;
  const client = { session: vi.fn().mockResolvedValue({ ok: true, data: {} }), inbox: vi.fn(), detail: vi.fn(), sync: vi.fn(), categoryCounts: vi.fn().mockResolvedValue({ ok: true, data: { total: 0, counts: {} } }) };
  const connected = vi.fn();
  const dispose = registerMailReadIPC(ipc, contents, 'file:///app/renderer/index.html', client, connected);
  return { frame, contents, event, handlers, client, connected, dispose };
}
describe('제한된 메일 IPC', () => {
  it('개발 환경 변수도 지정한 로컬 화면만 허용한다', () => {
    expect(developmentRendererURL('http://127.0.0.1:5173')).toBe('http://127.0.0.1:5173/');
    for (const url of [undefined, 'https://outside.invalid', 'http://localhost:8000', 'file:///tmp/other.html', 'http://localhost:5173/other', 'http://user:pass@localhost:5173', 'http://localhost:5173/?a=1']) {
      expect(developmentRendererURL(url)).toBeUndefined();
    }
  });
  it('등록된 세 조회와 검증된 인수만 호출하고 성공한 계정 연결 후 창을 전환한다', async () => {
    const s = setup();
    expect([...s.handlers.keys()]).toEqual([...Object.values(mailChannels), mailSyncChannel, mailCategoryCountsChannel]);
    await s.handlers.get(mailChannels.session)!(s.event);
    s.handlers.get(mailChannels.inbox)!(s.event, { limit: 20, cursor: 'opaque' });
    s.handlers.get(mailChannels.detail)!(s.event, 'safe-mail-id');
    expect(s.client.session).toHaveBeenCalledOnce();
    expect(s.connected).toHaveBeenCalledOnce();
    expect(s.client.inbox).toHaveBeenCalledWith({ limit: 20, cursor: 'opaque' });
    expect(s.client.detail).toHaveBeenCalledWith('safe-mail-id');
    s.dispose();
    expect(s.handlers.size).toBe(0);
  });
  it('다른 창·하위 프레임·다른 URL은 파일·서버에 접근하지 못한다', async () => {
    const s = setup();
    for (const event of [
      { ...s.event, sender: {} },
      { ...s.event, senderFrame: { url: s.frame.url } },
      { ...s.event, senderFrame: null },
    ]) {
      expect(await s.handlers.get(mailChannels.session)!(event as IpcMainInvokeEvent)).toMatchObject({ ok: false });
    }
    for (const url of ['https://outside.invalid/index.html', 'file:///another/index.html', 'file:///app/renderer/index.html?untrusted=1']) {
      s.frame.url = url;
      expect(await s.handlers.get(mailChannels.session)!(s.event)).toMatchObject({ ok: false });
    }
    expect(s.client.session).not.toHaveBeenCalled();
  });
  it('추가 인수·URL·파일 경로·임의 헤더·범위 밖 페이지 요청을 거부한다', async () => {
    const s = setup();
    expect(await s.handlers.get(mailChannels.session)!(s.event, 'secret-file')).toMatchObject({ ok: false });
    for (const query of [null, [], { limit: 0 }, { limit: 101 }, { cursor: 42 }, { category: 'unknown' }, { category: 3 }, { box: 'trash' }, { box: 'sent', category: 'meeting' }, { url: 'http://outside.invalid' }, { headers: {} }]) {
      expect(await s.handlers.get(mailChannels.inbox)!(s.event, query)).toMatchObject({ ok: false });
    }
    for (const id of ['../token', 'http://outside.invalid', '', 'x'.repeat(129), { path: 'file' }]) {
      expect(await s.handlers.get(mailChannels.detail)!(s.event, id)).toMatchObject({ ok: false });
    }
    expect(s.client.session).not.toHaveBeenCalled();
    expect(s.client.inbox).not.toHaveBeenCalled();
    expect(s.client.detail).not.toHaveBeenCalled();
  });
  it('분류 필터는 7개 분류 값만 서버 요청에 전달하고, 건수 조회는 인수를 받지 않는다', async () => {
    const s = setup();
    await s.handlers.get(mailChannels.inbox)!(s.event, { limit: 20, category: 'meeting' });
    expect(s.client.inbox).toHaveBeenCalledWith({ limit: 20, category: 'meeting' });
    await s.handlers.get(mailChannels.inbox)!(s.event, { limit: 20, box: 'sent' });
    expect(s.client.inbox).toHaveBeenLastCalledWith({ limit: 20, box: 'sent' });
    expect(await s.handlers.get(mailCategoryCountsChannel)!(s.event)).toMatchObject({ ok: true });
    expect(await s.handlers.get(mailCategoryCountsChannel)!(s.event, 'extra')).toMatchObject({ ok: false });
    expect(await s.handlers.get(mailCategoryCountsChannel)!({ ...s.event, senderFrame: null } as IpcMainInvokeEvent)).toMatchObject({ ok: false });
    expect(s.client.categoryCounts).toHaveBeenCalledOnce();
  });
  it('새 메일 가져오기는 신뢰한 화면의 인수 없는 요청만 서버에 전달한다', async () => {
    const s = setup();
    s.handlers.get(mailSyncChannel)!(s.event);
    expect(s.client.sync).toHaveBeenCalledOnce();
    expect(await s.handlers.get(mailSyncChannel)!(s.event, { url: 'http://outside.invalid' })).toMatchObject({ ok: false });
    expect(await s.handlers.get(mailSyncChannel)!({ ...s.event, sender: {} } as unknown as IpcMainInvokeEvent)).toMatchObject({ ok: false });
    expect(s.client.sync).toHaveBeenCalledOnce();
  });
});
