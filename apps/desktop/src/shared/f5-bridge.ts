// F5 제안·할 일: 정해진 동작만 main/preload에 공개한다. 토큰·주소·소유자는 공개하지 않는다.
// 알림 outbox(/suggestion-events)는 S10 범위라 공개하지 않는다.
import type { SuggestionsIPC } from '../renderer/features/suggestions/types';

export type F5Bridge = Readonly<SuggestionsIPC>;
export type F5Operation = 'list' | 'get' | 'approve' | 'dismiss' | 'conflicts' | 'todos' | 'createTodo' | 'updateTodo' | 'calendarStatus' | 'disconnectCalendar' | 'connectCalendar';
export type F5Result = { ok: true; data: unknown } | { ok: false; error: { code: string; message: string } };
export type F5Request = { id?: string; query?: string; body?: Record<string, unknown> };
export const f5Operations: F5Operation[] = ['list', 'get', 'approve', 'dismiss', 'conflicts', 'todos', 'createTodo', 'updateTodo', 'calendarStatus', 'disconnectCalendar', 'connectCalendar'];
export const f5Channel = (operation: F5Operation) => `klover:suggestions:${operation}`;

const suggestion = (id?: string) => `/suggestions/${encodeURIComponent(id ?? '')}`;
export const f5Routes: Record<F5Operation, { method: 'GET' | 'POST' | 'PATCH'; path: (request: F5Request) => string; page?: true }> = {
  connectCalendar: { method: 'POST', path: () => '/calendar/connect' },
  calendarStatus: { method: 'GET', path: () => '/calendar/connection' },
  disconnectCalendar: { method: 'POST', path: () => '/calendar/disconnect' },
  list: { method: 'GET', path: ({ query }) => `/suggestions${query ? `?${query}` : ''}`, page: true },
  get: { method: 'GET', path: ({ id }) => suggestion(id) },
  approve: { method: 'POST', path: ({ id }) => `${suggestion(id)}/approve` },
  dismiss: { method: 'POST', path: ({ id }) => `${suggestion(id)}/dismiss` },
  conflicts: { method: 'POST', path: ({ id }) => `${suggestion(id)}/conflicts` },
  todos: { method: 'GET', path: ({ query }) => `/todos${query ? `?${query}` : ''}`, page: true },
  createTodo: { method: 'POST', path: () => '/todos' },
  updateTodo: { method: 'PATCH', path: ({ id }) => `/todos/${encodeURIComponent(id ?? '')}` },
};

export function f5Failure(code = 'invalid_request'): F5Result {
  return { ok: false, error: { code, message: 'AI 제안·할 일 요청과 연결 상태를 확인해 주세요.' } };
}

function record(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value) && Object.getPrototypeOf(value) === Object.prototype;
}
function validId(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);
}
function validVersion(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) >= 1;
}
function small(value: unknown, limit = 20000) {
  try { return JSON.stringify(value).length <= limit; } catch { return false; }
}
function onlyKeys(value: Record<string, unknown>, keys: string[]) {
  return Object.keys(value).every(key => keys.includes(key));
}
function validTitle(value: unknown) {
  return typeof value === 'string' && value.trim().length > 0 && value.length <= 300;
}
function validDate(value: unknown) {
  return value === null || (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value));
}

// 목록 조회 조건은 서버가 허용한 이름·값만 쿼리 문자열로 만든다(소유자·notified는 받지 않는다).
function listQuery(value: unknown, statuses: string[], extra: string[] = []): string | null {
  if (!record(value) || !onlyKeys(value, ['status', 'limit', 'cursor', ...extra])) return null;
  const parameters = new URLSearchParams();
  if (value.status !== undefined) {
    if (typeof value.status !== 'string' || !statuses.includes(value.status)) return null;
    parameters.set('status', value.status);
  }
  if (value.limit !== undefined) {
    if (!Number.isSafeInteger(value.limit) || (value.limit as number) < 1 || (value.limit as number) > 100) return null;
    parameters.set('limit', String(value.limit));
  }
  if (value.cursor !== undefined) {
    if (typeof value.cursor !== 'string' || !value.cursor || value.cursor.length > 512) return null;
    parameters.set('cursor', value.cursor);
  }
  if (extra.includes('mail_id') && value.mail_id !== undefined) {
    if (!validId(value.mail_id)) return null;
    parameters.set('mail_id', value.mail_id);
  }
  return parameters.toString();
}

/** IPC 인수를 동작별로 검사한다. 맞지 않으면 null(서버를 호출하지 않는다). */
export function f5Arguments(operation: F5Operation, args: unknown[]): F5Request | null {
  switch (operation) {
    case 'connectCalendar':
    case 'calendarStatus':
    case 'disconnectCalendar': return args.length === 0 ? {} : null;
    case 'list': {
      const query = args.length === 1 ? listQuery(args[0], ['pending', 'approved', 'dismissed'], ['mail_id']) : null;
      return query === null ? null : { query };
    }
    case 'todos': {
      const query = args.length === 1 ? listQuery(args[0], ['open', 'completed']) : null;
      return query === null ? null : { query };
    }
    case 'get':
      return args.length === 1 && validId(args[0]) ? { id: args[0] } : null;
    case 'approve': {
      const [id, body] = args;
      if (args.length !== 2 || !validId(id) || !record(body) || !onlyKeys(body, ['version', 'payload']) || !validVersion(body.version)) return null;
      if (body.payload !== undefined && (!record(body.payload) || !small(body.payload))) return null;
      return { id, body: body.payload === undefined ? { version: body.version } : { version: body.version, payload: body.payload } };
    }
    case 'dismiss': {
      const [id, body] = args;
      if (args.length !== 2 || !validId(id) || !record(body) || !onlyKeys(body, ['version']) || !validVersion(body.version)) return null;
      return { id, body: { version: body.version } };
    }
    case 'conflicts': {
      const [id, body] = args;
      if (args.length !== 2 || !validId(id) || !record(body) || !small(body)) return null;
      return { id, body };
    }
    case 'createTodo': {
      const [body] = args;
      if (args.length !== 1 || !record(body) || !onlyKeys(body, ['title', 'due', 'request_id', 'mail_id'])) return null;
      if (!validTitle(body.title) || !validId(body.request_id) || (body.due !== undefined && !validDate(body.due))
        || (body.mail_id !== undefined && body.mail_id !== null && !validId(body.mail_id))) return null;
      return { body };
    }
    case 'updateTodo': {
      const [id, body] = args;
      if (args.length !== 2 || !validId(id) || !record(body) || !onlyKeys(body, ['version', 'title', 'due', 'status']) || !validVersion(body.version)) return null;
      if ((body.title !== undefined && !validTitle(body.title)) || (body.due !== undefined && !validDate(body.due))
        || (body.status !== undefined && body.status !== 'open' && body.status !== 'completed')) return null;
      if (Object.keys(body).length < 2) return null;
      return { id, body };
    }
  }
}
