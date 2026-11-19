import type { IpcMain, WebContents } from 'electron';
import { trustedMailSender } from './mail-ipc';
import { validMailId } from '../shared/mail-read';
import { analysisFailure, f1Channels, validBatchIds, type F1Bridge } from '../shared/f1-bridge';

/** 신뢰한 화면(main frame)의 요청만, 인수 검사를 통과한 경우에만 서버로 보낸다. */
export function registerF1IPC(ipc: Pick<IpcMain, 'handle' | 'removeHandler'>, contents: WebContents, rendererURL: string, client: F1Bridge): () => void {
  ipc.handle(f1Channels.batch, (event, ...args: unknown[]) => {
    if (!trustedMailSender(event, contents, rendererURL) || args.length !== 1 || !validBatchIds(args[0])) return analysisFailure('invalid_request');
    return client.batch([...args[0]]);
  });
  ipc.handle(f1Channels.retry, (event, ...args: unknown[]) => {
    if (!trustedMailSender(event, contents, rendererURL) || args.length !== 1 || !validMailId(args[0])) return analysisFailure('invalid_request');
    return client.retry(args[0]);
  });
  return () => Object.values(f1Channels).forEach(channel => ipc.removeHandler(channel));
}
