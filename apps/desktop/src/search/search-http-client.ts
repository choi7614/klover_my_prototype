// F3 전용 Node 어댑터. F0 main에서만 조립한다. Renderer에 토큰을 전달하지 않는다.
import {
  readRecentSearches, readSearchEvent, SearchClientError, type SearchClient, type SearchRequest,
} from '../renderer/features/search/contracts';

export function createSearchHTTPClient(baseURL: string, token: string): SearchClient {
  const base = new URL(baseURL);
  if (base.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(base.hostname)
    || base.username || base.password || base.search || base.hash || base.pathname !== '/') {
    throw new SearchClientError('로컬 검색 서버 주소를 확인해 주세요.');
  }
  if (!token || token.length > 128 || /[\r\n]/.test(token)) throw new SearchClientError('검색 인증 설정을 확인해 주세요.');
  const headers = { Authorization: `Bearer ${token}` };
  const request = async (path: string, init: RequestInit) => {
    let response: Response;
    try {
      response = await fetch(new URL(path, base), { ...init, redirect: 'error', cache: 'no-store' });
    } catch {
      throw new SearchClientError('검색 서버에 연결하지 못했어요. 다시 시도해 주세요.');
    }
    if (!response.ok) throw new SearchClientError(response.status === 401
      ? '검색 인증 정보를 확인해 주세요.' : '검색 서버에 연결하지 못했어요. 다시 시도해 주세요.');
    return response;
  };
  return {
    async *search(body: SearchRequest, signal: AbortSignal) {
      const response = await request('/search', {
        method: 'POST', headers: { ...headers, 'Content-Type': 'application/json', Accept: 'application/x-ndjson' },
        body: JSON.stringify(body), signal,
      });
      if (!response.body || !response.headers.get('content-type')?.startsWith('application/x-ndjson')) {
        throw new SearchClientError('검색 응답 형식을 확인하지 못했어요.');
      }
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let pending = '';
      let bytes = 0;
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          bytes += value.byteLength;
          if (bytes > 2_000_000) throw new SearchClientError('검색 응답이 너무 큽니다. 조건을 좁혀 주세요.');
          pending += decoder.decode(value, { stream: true });
          let newline: number;
          while ((newline = pending.indexOf('\n')) >= 0) {
            const line = pending.slice(0, newline);
            pending = pending.slice(newline + 1);
            if (line.trim()) {
              let value: unknown;
              try { value = JSON.parse(line); } catch { throw new SearchClientError('검색 응답 형식을 확인하지 못했어요.'); }
              yield readSearchEvent(value);
            }
          }
        }
        pending += decoder.decode();
        if (pending.trim()) throw new SearchClientError('검색 응답이 중간에 끊겼어요.');
      } finally {
        await reader.cancel().catch(() => undefined);
        reader.releaseLock();
      }
    },
    async recent(signal: AbortSignal) {
      const response = await request('/search/recent', { headers, signal });
      return readRecentSearches(await response.json());
    },
  };
}
