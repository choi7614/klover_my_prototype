// @vitest-environment node
import { describe, expect, it, vi } from 'vitest';
import type { IpcMain, IpcMainInvokeEvent, WebContents } from 'electron';
import { registerAIIPC } from './ai-ipc';
import { readAIState } from '../shared/ai-bridge';
vi.mock('./mail-client', () => ({ readLocalAPI: vi.fn(async () => ({ base: new URL('http://127.0.0.1:8000'), token: 'synthetic-local-token' })) }));
const state = { defaults: { draft: 'ollama', search: 'claude', weekly_report: 'ollama' }, external_consent: true, claude_key_set: true, local_configured: true, claude_model: 'synthetic' };
function setup() {
  const frame = { url: 'file:///app/renderer/index.html#/settings/ai' };
  const contents = { mainFrame: frame, isDestroyed: () => false } as WebContents;
  const event = { sender: contents, senderFrame: frame } as unknown as IpcMainInvokeEvent;
  const handlers = new Map<string, (event: IpcMainInvokeEvent, ...args: unknown[]) => Promise<unknown>>();
  const ipc = { handle: vi.fn((ch, cb) => handlers.set(ch, cb)), removeHandler: vi.fn(ch => handlers.delete(ch)) } as unknown as IpcMain;
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ ...state, api_key: 'synthetic-private-key' })));
  const dispose = registerAIIPC(ipc, contents, 'file:///app/renderer/index.html', {}, fetcher);
  return { event, handlers, fetcher, dispose };
}
describe('AI 설정 통로', () => {
  it('신뢰한 화면과 고정 동작만 허용하고 비밀 필드를 응답에서 제거한다', async () => {
    const s = setup();
    expect(await s.handlers.get('klover:ai:get')!(s.event)).toEqual({ ok: true, data: state });
    expect(s.fetcher.mock.calls[0][0].pathname).toBe('/settings/ai');
    expect(JSON.stringify(readAIState({ ...state, api_key: 'synthetic-private-key' }))).not.toContain('synthetic-private-key');
    const foreign = { ...s.event, senderFrame: { url: 'https://evil.invalid' } } as unknown as IpcMainInvokeEvent;
    expect(await s.handlers.get('klover:ai:get')!(foreign)).toMatchObject({ ok: false });
    expect(await s.handlers.get('klover:ai:check')!(s.event, 'https://evil.invalid')).toMatchObject({ ok: false });
    expect(await s.handlers.get('klover:ai:save')!(s.event, { ...state, api_key: 'synthetic' })).toMatchObject({ ok: false });
    expect(s.fetcher).toHaveBeenCalledTimes(1);
    s.dispose(); expect(s.handlers.size).toBe(0);
  });
});
