import type { IpcMain, WebContents } from 'electron';
import { trustedMailSender } from './mail-ipc';
import { readLocalAPI, type LocalAPIConfiguration } from './mail-client';
import { createSearchHTTPClient } from '../search/search-http-client';
import { SearchClientError, type SearchClient, type SearchRequest } from '../renderer/features/search/contracts';
import {
  searchChannels, searchConfigurationMessage, searchConnectionMessage, validSearchRequest, validSearchRequestId,
  type SearchBridgeResult, type SearchMessage,
} from '../shared/search-bridge';

/** 요청마다 토큰을 새로 읽어 F3 검색 클라이언트를 만든다. 실패하면 null. */
export type SearchClientFactory = () => Promise<SearchClient | null>;

export function localSearchClientFactory(configuration: LocalAPIConfiguration): SearchClientFactory {
  return async () => {
    const local = await readLocalAPI(configuration);
    if (!local) return null;
    try { return createSearchHTTPClient(local.base.href, local.token); } catch { return null; }
  };
}

const MAX_RUNNING = 4;
const failure = (message: string) => ({ ok: false as const, message });
const errorText = (error: unknown) => error instanceof SearchClientError ? error.message : searchConnectionMessage;

/** F3 검색 통로 등록. 신뢰한 화면에서 온 요청만 받고, 단계 결과를 같은 화면으로만 보낸다. */
export function registerSearchIPC(
  ipc: Pick<IpcMain, 'handle' | 'removeHandler'>, contents: WebContents, rendererURL: string, factory: SearchClientFactory,
): () => void {
  const running = new Map<string, AbortController>();
  const send = (requestId: string, message: SearchMessage) => {
    if (!contents.isDestroyed()) contents.send(searchChannels.message, requestId, message);
  };

  ipc.handle(searchChannels.start, async (event, ...args: unknown[]): Promise<SearchBridgeResult<null>> => {
    if (!trustedMailSender(event, contents, rendererURL) || args.length !== 2 ||
        !validSearchRequestId(args[0]) || !validSearchRequest(args[1])) return failure('검색 요청을 확인해 주세요.');
    const [requestId, request] = args as [string, SearchRequest];
    if (running.has(requestId)) return failure('검색 요청을 확인해 주세요.');
    // 오래된 검색이 쌓이지 않도록 가장 먼저 시작한 검색부터 취소한다.
    while (running.size >= MAX_RUNNING) {
      const [oldest, controller] = running.entries().next().value as [string, AbortController];
      controller.abort();
      running.delete(oldest);
    }
    const client = await factory();
    if (!client) return failure(searchConfigurationMessage);
    const controller = new AbortController();
    running.set(requestId, controller);
    void (async () => {
      try {
        for await (const frame of client.search(request, controller.signal)) {
          if (controller.signal.aborted) return;
          send(requestId, { kind: 'event', event: frame });
        }
        if (!controller.signal.aborted) send(requestId, { kind: 'done' });
      } catch (error) {
        if (!controller.signal.aborted) send(requestId, { kind: 'error', message: errorText(error) });
      } finally {
        if (running.get(requestId) === controller) running.delete(requestId);
      }
    })();
    return { ok: true, data: null };
  });

  ipc.handle(searchChannels.cancel, (event, ...args: unknown[]) => {
    if (!trustedMailSender(event, contents, rendererURL) || args.length !== 1 || !validSearchRequestId(args[0])) return;
    running.get(args[0])?.abort();
    running.delete(args[0]);
  });

  ipc.handle(searchChannels.recent, async (event, ...args: unknown[]): Promise<SearchBridgeResult<unknown>> => {
    if (!trustedMailSender(event, contents, rendererURL) || args.length) return failure('검색 요청을 확인해 주세요.');
    const client = await factory();
    if (!client) return failure(searchConfigurationMessage);
    try { return { ok: true, data: await client.recent(AbortSignal.timeout(10000)) }; }
    catch (error) { return failure(errorText(error)); }
  });

  return () => {
    running.forEach(controller => controller.abort());
    running.clear();
    [searchChannels.start, searchChannels.cancel, searchChannels.recent].forEach(channel => ipc.removeHandler(channel));
  };
}
