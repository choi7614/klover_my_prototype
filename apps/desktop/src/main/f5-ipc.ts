import { shell } from 'electron';
import type { IpcMain, WebContents } from 'electron';
import { trustedMailSender } from './mail-ipc';
import { f5Arguments, f5Channel, f5Failure, f5Operations, type F5Operation, type F5Request, type F5Result } from '../shared/f5-bridge';

export interface F5Caller {
  call(operation: F5Operation, request?: F5Request): Promise<F5Result>;
}
/** 신뢰한 화면(main frame)의 요청만, 인수 검사를 통과한 경우에만 서버로 보낸다. */
export function registerF5IPC(ipc: Pick<IpcMain, 'handle' | 'removeHandler'>, contents: WebContents, rendererURL: string, client: F5Caller): () => void {
  for (const operation of f5Operations) {
    ipc.handle(f5Channel(operation), (event, ...args: unknown[]) => {
      if (!trustedMailSender(event, contents, rendererURL)) return f5Failure();
      const parsed = f5Arguments(operation, args);
      if (!parsed) return f5Failure();
      if (operation === 'connectCalendar') {
        return shell.openExternal('http://localhost:8000/auth/google').then(
          () => ({ ok: true, data: { status: 'opened' } }), () => f5Failure('connection'));
      }
      return client.call(operation, parsed);
    });
  }
  return () => f5Operations.forEach(operation => ipc.removeHandler(f5Channel(operation)));
}
