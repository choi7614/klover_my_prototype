import type { IpcMain, IpcMainInvokeEvent, WebContents } from 'electron';
import { mailCategoryCountsChannel, mailChannels, mailFailure, mailSyncChannel, validInboxQuery, validMailId, type MailReadBridge } from '../shared/mail-read';

export function developmentRendererURL(value: string | undefined): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    if (url.protocol === 'http:' && ['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) &&
        url.port === '5173' && url.pathname === '/' && !url.search && !url.hash && !url.username && !url.password) return url.href;
  } catch { /* 잘못된 개발 주소로 외부 화면을 열지 않는다. */ }
  return undefined;
}

export function trustedMailSender(event: IpcMainInvokeEvent, contents: WebContents, rendererURL: string): boolean {
  if (contents.isDestroyed() || event.sender !== contents || !event.senderFrame || event.senderFrame !== contents.mainFrame) return false;
  try {
    const actual = new URL(event.senderFrame.url);
    const expected = new URL(rendererURL);
    return actual.protocol === expected.protocol && actual.host === expected.host &&
      actual.pathname === expected.pathname && !actual.search && !actual.username && !actual.password;
  } catch { return false; }
}

export function registerMailReadIPC(
  ipc: Pick<IpcMain, 'handle' | 'removeHandler'>, contents: WebContents, rendererURL: string,
  client: MailReadBridge, connected: () => void,
): () => void {
  ipc.handle(mailChannels.session, async (event, ...args: unknown[]) => {
    if (!trustedMailSender(event, contents, rendererURL) || args.length) return mailFailure('invalid_request');
    const result = await client.session();
    if (result.ok && !contents.isDestroyed()) connected();
    return result;
  });
  ipc.handle(mailChannels.inbox, (event, ...args: unknown[]) => {
    if (!trustedMailSender(event, contents, rendererURL) || args.length > 1 || !validInboxQuery(args[0])) return mailFailure('invalid_request');
    return client.inbox(args[0]);
  });
  ipc.handle(mailChannels.detail, (event, ...args: unknown[]) => {
    if (!trustedMailSender(event, contents, rendererURL) || args.length !== 1 || !validMailId(args[0])) return mailFailure('invalid_request');
    return client.detail(args[0]);
  });
  // 새 메일 가져오기: 인수 없이 서버의 POST /mails/sync만 호출한다.
  ipc.handle(mailSyncChannel, (event, ...args: unknown[]) => {
    if (!trustedMailSender(event, contents, rendererURL) || args.length) return mailFailure('invalid_request');
    return client.sync ? client.sync() : mailFailure('unavailable');
  });
  // 분류별 건수: 인수 없이 서버의 GET /mails/category-counts만 호출한다.
  ipc.handle(mailCategoryCountsChannel, (event, ...args: unknown[]) => {
    if (!trustedMailSender(event, contents, rendererURL) || args.length) return mailFailure('invalid_request');
    return client.categoryCounts ? client.categoryCounts() : mailFailure('unavailable');
  });
  return () => [...Object.values(mailChannels), mailSyncChannel, mailCategoryCountsChannel].forEach(channel => ipc.removeHandler(channel));
}
