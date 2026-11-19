import type { IpcMain, WebContents } from 'electron';
import { trustedMailSender } from './mail-ipc';
import { f2Arguments, f2Channel, f2Failure, f2Operations, type F2Operation, type F2Result } from '../shared/f2-bridge';

export interface F2Caller {
  call(operation: F2Operation, id?: string, body?: Record<string, unknown>): Promise<F2Result>;
}

/** F2 통로 등록. 신뢰한 화면에서 온, 모양이 맞는 요청만 서버로 보낸다. 발송 통로는 없다. */
export function registerF2IPC(
  ipc: Pick<IpcMain, 'handle' | 'removeHandler'>, contents: WebContents, rendererURL: string, client: F2Caller,
): () => void {
  for (const operation of f2Operations) {
    ipc.handle(f2Channel(operation), (event, ...args: unknown[]) => {
      if (!trustedMailSender(event, contents, rendererURL)) return f2Failure('invalid_request');
      const parsed = f2Arguments(operation, args);
      if (!parsed) return f2Failure('invalid_request');
      return client.call(operation, parsed.id, parsed.body);
    });
  }
  return () => f2Operations.forEach(operation => ipc.removeHandler(f2Channel(operation)));
}
