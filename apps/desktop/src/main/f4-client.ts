import { readLocalAPI, type LocalAPIConfiguration } from './mail-client';
import { localRequest, MAX_RESPONSE_CHARS } from './local-api';
import { f4Failure, f4Routes, type F4Operation, type F4Result } from '../shared/f4-bridge';

export class F4APIClient {
  constructor(private readonly configuration: LocalAPIConfiguration, private readonly fetcher: typeof fetch = fetch) {}
  async call(operation: F4Operation, id?: string, body?: Record<string, unknown>): Promise<F4Result> {
    const local = await readLocalAPI(this.configuration);
    if (!local) return f4Failure('configuration');
    const route = f4Routes[operation];
    try {
      const { url, init } = localRequest(local, { method: route.method, path: route.path(id), body, timeoutMs: operation === 'generate' ? 150000 : 15000 });
      const response = await this.fetcher(url, init);
      const text = await response.text();
      if (text.length > MAX_RESPONSE_CHARS) return f4Failure('invalid_response');
      const payload: unknown = JSON.parse(text);
      if (!response.ok) {
        const code = (payload as { error?: { code?: unknown } } | null)?.error?.code;
        return f4Failure(typeof code === 'string' && /^[a-z_]{1,64}$/.test(code) ? code : 'unavailable');
      }
      if (!payload || typeof payload !== 'object' || (operation === 'excluded') !== Array.isArray(payload)) return f4Failure('invalid_response');
      return { ok: true, data: payload };
    } catch { return f4Failure('connection'); }
  }
}
