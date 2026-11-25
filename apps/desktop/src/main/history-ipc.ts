import type { IpcMain, WebContents } from 'electron';
import { readLocalAPI, type LocalAPIConfiguration } from './mail-client';
import { localRequest } from './local-api';
import { trustedMailSender } from './mail-ipc';
import { readHistoryJob, type HistoryResult } from '../shared/history-bridge';
const failure = (): HistoryResult => ({ ok: false, error: { code: 'history_failed', message: '가져오기 상태·기간·서버 연결을 확인하세요. 기존 메일은 보존됩니다.' } });
export function registerHistoryIPC(ipc: IpcMain, contents: WebContents, rendererURL: string, config: LocalAPIConfiguration) {
  const channels = ['list', 'start', 'action'] as const;
  channels.forEach(op => ipc.handle(`klover:history:${op}`, async (event, ...args: unknown[]): Promise<HistoryResult> => {
    if (!trustedMailSender(event, contents, rendererURL)) return failure();
    let path = '/mail-history'; let body: unknown;
    if (op === 'list') { if (args.length) return failure(); }
    else if (op === 'start') {
      const range = args[0] as { start?: unknown; end?: unknown } | undefined;
      if (args.length !== 1 || !range || Object.keys(range).length !== 2 || ![range.start, range.end].every(v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v))) return failure();
      body = range;
    } else {
      if (args.length !== 2 || typeof args[0] !== 'string' || !/^[a-f0-9]{32}$/.test(args[0]) || !['pause', 'resume'].includes(String(args[1]))) return failure();
      path += `/${args[0]}/${args[1]}`;
    }
    const local = await readLocalAPI(config); if (!local) return failure();
    try {
      const { url, init } = localRequest(local, { method: op === 'list' ? 'GET' : 'POST', path, body: body as object | undefined, timeoutMs: 15000 });
      const response = await fetch(url, init);
      const text = await response.text();
      if (!response.ok || text.length > 100000) return failure();
      const payload: unknown = JSON.parse(text);
      if (op === 'list') {
        if (!Array.isArray(payload) || payload.length > 20) return failure();
        return { ok: true, data: payload.map(readHistoryJob) };
      }
      return { ok: true, data: readHistoryJob(payload) };
    } catch { return failure(); }
  }));
  return () => channels.forEach(op => ipc.removeHandler(`klover:history:${op}`));
}
