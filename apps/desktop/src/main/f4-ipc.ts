import type { IpcMain, WebContents } from 'electron';
import { trustedMailSender } from './mail-ipc';
import { f4Arguments, f4Channel, f4Failure, f4Operations, type F4Operation, type F4Result } from '../shared/f4-bridge';

export interface F4Caller {
  call(operation: F4Operation, id?: string, body?: Record<string, unknown>): Promise<F4Result>;
}
export function registerF4IPC(ipc: Pick<IpcMain, 'handle' | 'removeHandler'>, contents: WebContents, rendererURL: string, client: F4Caller): () => void {
  for (const operation of f4Operations) {
    ipc.handle(f4Channel(operation), (event, ...args: unknown[]) => {
      if (!trustedMailSender(event, contents, rendererURL)) return f4Failure();
      const parsed = f4Arguments(operation, args);
      if (!parsed) return f4Failure();
      return client.call(operation, parsed.id, parsed.body);
    });
  }
  return () => f4Operations.forEach(operation => ipc.removeHandler(f4Channel(operation)));
}
