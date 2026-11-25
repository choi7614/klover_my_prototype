import type { IpcMain, WebContents } from 'electron';
import { readLocalAPI, type LocalAPIConfiguration } from './mail-client';
import { localRequest } from './local-api';
import { trustedMailSender } from './mail-ipc';
import { readAIState, readClaudeModels, validProvider, type AIResult } from '../shared/ai-bridge';

const fail = (): AIResult<never> => ({ ok: false, error: { code: 'ai_settings_failed', message: 'AI 설정과 연결 상태를 확인해 주세요.' } });
function serverFailure(text: string): AIResult<never> {
  try {
    const error = (JSON.parse(text) as { error?: { code?: unknown; message?: unknown } }).error;
    if (error && typeof error.code === 'string' && /^[a-z_]{1,64}$/.test(error.code) &&
        typeof error.message === 'string' && error.message.length > 0 && error.message.length <= 600) {
      return { ok: false, error: { code: error.code, message: error.message } };
    }
  } catch { /* 형식이 다르면 아래 일반 안내 */ }
  return fail();
}
export function registerAIIPC(ipc: IpcMain, contents: WebContents, rendererURL: string, configuration: LocalAPIConfiguration, fetcher: typeof fetch = fetch) {
  const channels = ['get', 'save', 'check', 'models'] as const;
  for (const operation of channels) ipc.handle(`klover:ai:${operation}`, async (event, ...args: unknown[]) => {
    if (!trustedMailSender(event, contents, rendererURL)) return fail();
    let body: unknown;
    if (operation === 'get' || operation === 'models') { if (args.length) return fail(); }
    else if (operation === 'check') {
      if (args.length !== 1 || !validProvider(args[0])) return fail();
      body = { provider: args[0] };
    } else {
      if (args.length !== 1 || !args[0] || typeof args[0] !== 'object' || Array.isArray(args[0])) return fail();
      const row = args[0] as Record<string, unknown>;
      if (Object.keys(row).some(k => !['mode', 'defaults', 'external_consent', 'api_key', 'clear_key', 'claude_model'].includes(k))
        || (row.mode !== undefined && !['local_only', 'hybrid'].includes(row.mode as string))
        || typeof row.external_consent !== 'boolean' || !row.defaults || typeof row.defaults !== 'object'
        || Object.keys(row.defaults).length !== 3
        || !['draft', 'search', 'weekly_report'].every(p => validProvider((row.defaults as Record<string, unknown>)[p]))
        || (row.api_key !== undefined && (typeof row.api_key !== 'string' || row.api_key.length > 512))
        || (row.claude_model !== undefined && (typeof row.claude_model !== 'string' || !/^[A-Za-z0-9._:/-]{1,200}$/.test(row.claude_model)))
        || (row.clear_key !== undefined && typeof row.clear_key !== 'boolean')) return fail();
      body = row;
    }
    const local = await readLocalAPI(configuration);
    if (!local) return fail();
    try {
      const { url, init } = localRequest(local, {
        method: operation === 'get' || operation === 'models' ? 'GET' : operation === 'save' ? 'PUT' : 'POST',
        path: operation === 'check' ? '/settings/ai/check' : operation === 'models' ? '/settings/ai/claude-models' : '/settings/ai',
        body: body as object | undefined, timeoutMs: operation === 'check' ? 150000 : operation === 'models' ? 45000 : 15000,
      });
      const response = await fetcher(url, init);
      const text = await response.text();
      if (text.length > 10000) return fail();
      // 서버가 보낸 고정 오류 안내(원인별 문장)는 그대로 화면에 전달한다. 형식이 다르면 일반 안내로 바꾼다.
      if (!response.ok) return serverFailure(text);
      const result: unknown = JSON.parse(text);
      if (operation === 'models') return { ok: true, data: readClaudeModels(result) };
      if (operation !== 'check') return { ok: true, data: readAIState(result) };
      const probe = result as { status?: unknown; provider?: unknown };
      return probe.status === 'reachable' && probe.provider === args[0]
        ? { ok: true, data: { status: 'reachable', provider: probe.provider } } : fail();
    } catch { return fail(); }
  });
  return () => channels.forEach(op => ipc.removeHandler(`klover:ai:${op}`));
}
