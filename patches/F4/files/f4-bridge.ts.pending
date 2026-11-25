// 제안: 정해진 F4 동작만 main/preload에 공개한다. 토큰·주소·소유자는 공개하지 않는다.
import type { WeeklyReportIPC } from '../renderer/features/weekly-report/types';

export type F4Bridge = Readonly<WeeklyReportIPC>;
export type F4Operation = 'options' | 'generate' | 'get' | 'excluded' | 'save';
export type F4Result = { ok: true; data: unknown } | { ok: false; error: { code: string; message: string } };
export const f4Operations: F4Operation[] = ['options', 'generate', 'get', 'excluded', 'save'];
export const f4Channel = (operation: F4Operation) => `klover:weekly-report:${operation}`;
export const f4Routes: Record<F4Operation, { method: 'GET' | 'POST' | 'PATCH'; path: (id?: string) => string }> = {
  options: { method: 'GET', path: () => '/reports/weekly/options' },
  generate: { method: 'POST', path: () => '/reports/weekly' },
  get: { method: 'GET', path: id => `/reports/weekly/${encodeURIComponent(id ?? '')}` },
  excluded: { method: 'GET', path: id => `/reports/weekly/${encodeURIComponent(id ?? '')}/excluded` },
  save: { method: 'PATCH', path: id => `/reports/weekly/${encodeURIComponent(id ?? '')}` },
};
export function f4Failure(code = 'invalid_request'): F4Result {
  return { ok: false, error: { code, message: '주간 보고 요청과 연결 상태를 확인해 주세요.' } };
}
function validId(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);
}
function validBody(value: unknown): value is Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  try { return JSON.stringify(value).length <= 200000; } catch { return false; }
}
export function f4Arguments(operation: F4Operation, args: unknown[]): { id?: string; body?: Record<string, unknown> } | null {
  if (operation === 'options') return args.length === 0 ? {} : null;
  if (operation === 'get' || operation === 'excluded') return args.length === 1 && validId(args[0]) ? { id: args[0] } : null;
  if (operation === 'generate') {
    if (args.length !== 1 || !validBody(args[0])) return null;
    const allowed = new Set(['start', 'end', 'template', 'recipient', 'regenerate', 'expected_revision']);
    return Object.keys(args[0]).every(key => allowed.has(key)) ? { body: args[0] } : null;
  }
  if (args.length !== 3 || !validId(args[0]) || !Number.isSafeInteger(args[1]) || (args[1] as number) < 1 || !Array.isArray(args[2])) return null;
  const body = { expected_revision: args[1], sections: args[2] };
  return validBody(body) ? { id: args[0], body } : null;
}
