import { readLocalAPI, type LocalAPIConfiguration } from './mail-client';
import { localRequest, MAX_RESPONSE_CHARS } from './local-api';
import { f5Failure, f5Routes, type F5Operation, type F5Request, type F5Result } from '../shared/f5-bridge';

/** main 전용 F5 HTTP 경계. 토큰은 여기서만 읽고, 정해진 경로·메서드로만 루프백 서버를 호출한다. */
export class F5APIClient {
  constructor(private readonly configuration: LocalAPIConfiguration, private readonly fetcher: typeof fetch = fetch) {}
  async call(operation: F5Operation, request: F5Request = {}): Promise<F5Result> {
    const local = await readLocalAPI(this.configuration);
    if (!local) return f5Failure('configuration');
    const route = f5Routes[operation];
    try {
      const { url, init } = localRequest(local, { method: route.method, path: route.path(request), body: request.body, timeoutMs: operation === 'approve' || operation === 'reregister' ? 30000 : 15000 });
      const response = await this.fetcher(url, init);
      const text = await response.text();
      if (text.length > MAX_RESPONSE_CHARS) return f5Failure('invalid_response');
      const payload: unknown = text ? JSON.parse(text) : null;
      if (!response.ok) {
        const code = (payload as { error?: { code?: unknown } } | null)?.error?.code;
        return f5Failure(typeof code === 'string' && /^[a-z_]{1,64}$/.test(code) ? code : response.status === 404 ? 'not_found' : 'unavailable');
      }
      if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return f5Failure('invalid_response');
      if (route.page && !Array.isArray((payload as { items?: unknown }).items)) return f5Failure('invalid_response');
      return { ok: true, data: payload };
    } catch { return f5Failure('connection'); }
  }
}
