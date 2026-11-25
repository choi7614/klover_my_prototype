// F5 화면 전용 어댑터. main/preload 통로는 patches/F5/ 적용 전까지 없으며, 없으면 '준비 중'을 알린다.
import type { F5BridgeResult, F5Client, SuggestionsIPC } from './types';

async function unwrap<T>(pending: Promise<F5BridgeResult<T>>): Promise<T> {
  let result: F5BridgeResult<T>;
  try { result = await pending; }
  catch { throw new Error('connection'); }
  if (!result || typeof result !== 'object') throw new Error('invalid_response');
  if (!result.ok) throw new Error(typeof result.error?.code === 'string' ? result.error.code : 'unavailable');
  if (!result.data || typeof result.data !== 'object') throw new Error('invalid_response');
  return result.data;
}

export function createSuggestionsIPCClient(bridge: SuggestionsIPC): F5Client {
  return {
    ...(bridge.calendarStatus && bridge.disconnectCalendar ? { calendar: {
      calendarStatus: () => unwrap(bridge.calendarStatus!()),
      ...(bridge.connectCalendar ? { connectCalendar: () => unwrap(bridge.connectCalendar!()) } : {}),
      disconnectCalendar: () => unwrap(bridge.disconnectCalendar!()),
    } } : {}),
    list: query => unwrap(bridge.list(query)),
    get: id => unwrap(bridge.get(id)),
    approve: (id, request) => unwrap(bridge.approve(id, request)),
    dismiss: (id, request) => unwrap(bridge.dismiss(id, request)),
    ...(bridge.reregister ? { reregister: (id: string, request: { version: number }) => unwrap(bridge.reregister!(id, request)) } : {}),
    conflicts: (id, payload) => unwrap(bridge.conflicts(id, payload)),
    todos: query => unwrap(bridge.todos(query)),
    createTodo: request => unwrap(bridge.createTodo(request)),
    updateTodo: (id, request) => unwrap(bridge.updateTodo(id, request)),
  };
}

const unavailable = () => Promise.reject(new Error('suggestions_unavailable'));
export const unavailableSuggestionsClient: F5Client = {
  list: unavailable, get: unavailable, approve: unavailable, dismiss: unavailable, conflicts: unavailable,
  todos: unavailable, createTodo: unavailable, updateTodo: unavailable,
};
