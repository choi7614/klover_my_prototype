// F2 프로필·답장 초안 서버 호출. main에서만 쓴다. 토큰은 화면으로 넘기지 않는다.
import { readLocalAPI, type LocalAPIConfiguration } from './mail-client';
import { f2Failure, f2Routes, type F2Operation, type F2Result } from '../shared/f2-bridge';

const MAX_RESPONSE = 2_000_000;
// 초안 생성·다시 쓰기는 AI 응답을 기다리므로 더 길게 기다린다.
const SLOW: ReadonlySet<F2Operation> = new Set(['preview', 'createDraft', 'reviseDraft']);

function serverError(value: unknown): { code: string; message: string } | null {
  if (!value || typeof value !== 'object') return null;
  const error = (value as { error?: unknown }).error;
  if (!error || typeof error !== 'object') return null;
  const { code, message } = error as { code?: unknown; message?: unknown };
  if (typeof code !== 'string' || typeof message !== 'string' || !/^[a-z_]{1,64}$/.test(code)) return null;
  return { code, message: message.slice(0, 300) };
}

export class F2APIClient {
  constructor(private readonly configuration: LocalAPIConfiguration, private readonly fetcher: typeof fetch = fetch) {}

  async call(operation: F2Operation, id?: string, body?: Record<string, unknown>): Promise<F2Result> {
    const route = f2Routes[operation];
    const local = await readLocalAPI(this.configuration);
    if (!local) return f2Failure('configuration');
    // 서버 생성 제한 120초 뒤의 오류 응답까지 받을 여유를 둔다.
    const signal = AbortSignal.timeout(SLOW.has(operation) ? 150000 : 15000);
    let response: Response;
    try {
      response = await this.fetcher(new URL(route.path(id), local.base), {
        method: route.method,
        headers: {
          Authorization: `Bearer ${local.token}`, Accept: 'application/json',
          ...(body ? { 'Content-Type': 'application/json' } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
        redirect: 'error', cache: 'no-store', signal,
      });
    } catch { return f2Failure(signal.aborted ? 'timeout' : 'connection'); }
    let payload: unknown;
    try {
      const text = await response.text();
      if (text.length > MAX_RESPONSE) return f2Failure('invalid_response');
      payload = JSON.parse(text);
    } catch {
      if (signal.aborted) return f2Failure('timeout');
      return response.ok ? f2Failure('invalid_response') : f2Failure('unavailable');
    }
    if (!response.ok) {
      // 서버가 만든 {error:{code,message}}만 그대로 전달한다. 그 밖의 내용은 넘기지 않는다.
      const error = serverError(payload);
      return error ? { ok: false, error } : f2Failure(response.status === 422 ? 'invalid_request' : 'unavailable');
    }
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) return f2Failure('invalid_response');
    return { ok: true, data: payload };
  }
}
