// preload의 검색 통로를 F3 화면이 쓰는 SearchClient로 바꾼다.
// 검색 단계(해석 → 결과 → 답변)를 받는 대로 넘기고, 취소하면 main의 서버 요청도 끊는다.
import {
  readRecentSearches, readSearchEvent, SearchClientError, type SearchClient, type SearchEvent, type SearchRequest,
} from '../features/search/contracts';
import { searchConnectionMessage, type SearchBridge, type SearchMessage } from '../../shared/search-bridge';

const abortError = () => new DOMException('검색을 취소했어요.', 'AbortError');

function requestId(): string {
  return crypto.randomUUID().replace(/-/g, '');
}

export function createSearchIPCClient(bridge: SearchBridge): SearchClient {
  return {
    async *search(request: SearchRequest, signal: AbortSignal): AsyncIterable<SearchEvent> {
      if (signal.aborted) throw abortError();
      const id = requestId();
      const queue: SearchMessage[] = [];
      let wake: (() => void) | null = null;
      let finished = false;
      const notify = () => { const resume = wake; wake = null; resume?.(); };
      // 시작 전에 구독해야 빠른 응답의 첫 단계를 놓치지 않는다.
      const unsubscribe = bridge.onMessage((target, message) => {
        if (target !== id) return;
        queue.push(message);
        notify();
      });
      const onAbort = () => notify();
      signal.addEventListener('abort', onAbort);
      try {
        let started;
        try { started = await bridge.start(id, request); }
        catch { throw new SearchClientError(searchConnectionMessage); }
        if (!started.ok) throw new SearchClientError(started.message);
        while (true) {
          if (signal.aborted) throw abortError();
          const message = queue.shift();
          if (!message) { await new Promise<void>(resolve => { wake = resolve; }); continue; }
          if (message.kind === 'done') { finished = true; return; }
          if (message.kind === 'error') { finished = true; throw new SearchClientError(message.message); }
          yield readSearchEvent(message.event);
        }
      } finally {
        signal.removeEventListener('abort', onAbort);
        unsubscribe();
        if (!finished) void bridge.cancel(id).catch(() => undefined);
      }
    },
    async recent(signal: AbortSignal) {
      if (signal.aborted) throw abortError();
      let result;
      try { result = await bridge.recent(); }
      catch { throw new SearchClientError(searchConnectionMessage); }
      if (signal.aborted) throw abortError();
      if (!result.ok) throw new SearchClientError(result.message);
      return readRecentSearches(result.data);
    },
  };
}
