import type { components } from './f5-api';

type Schema = components['schemas'];
export type CalendarPayload = Schema['CalendarPayload'];
export type TodoPayload = Schema['TodoPayload'];
export type ReplyPayload = Schema['ReplyPayload'];
export type EvidenceSpan = Schema['EvidenceSpan'];
export type ConflictResult = Schema['ConflictResult'];
export type Todo = Schema['TodoView'];
type Common = Omit<Schema['SuggestionView'], 'type' | 'payload'>;
export type Suggestion = Common & (
  | { type: 'calendar'; payload: CalendarPayload }
  | { type: 'todo'; payload: TodoPayload }
  | { type: 'reply'; payload: ReplyPayload }
);
export type SuggestionPayload = Suggestion['payload'];
export type CalendarOption = { id: string; label: string };

// F0 main이 구현할 제한된 호출 목록이다. Renderer에 토큰·임의 URL은 전달하지 않는다.
export interface SuggestionsClient {
  get(suggestionId: string): Promise<Suggestion>;
  approve(suggestionId: string, request: { version: number; payload?: SuggestionPayload }): Promise<Suggestion>;
  dismiss(suggestionId: string, request: { version: number }): Promise<Suggestion>;
  conflicts(suggestionId: string, payload: CalendarPayload): Promise<ConflictResult>;
}

export type TodoStatus = Todo['status'];
export type SuggestionListQuery = { mail_id?: string; status?: Suggestion['status']; limit?: number; cursor?: string };
export type TodoListQuery = { status?: TodoStatus; limit?: number; cursor?: string };
export type TodoCreateRequest = { title: string; due?: string | null; request_id: string; mail_id?: string | null };
export type TodoUpdateRequest = { version: number; title?: string; due?: string | null; status?: TodoStatus };
export type Page<T> = { items: T[]; next_cursor?: string | null };

// main/preload가 공개하는 F5 통로 모양. 결과는 성공/실패 봉투로만 받는다(토큰·주소 없음).
export type F5BridgeResult<T> = { ok: true; data: T } | { ok: false; error: { code: string; message: string } };
export interface SuggestionsIPC {
  connectCalendar?(): Promise<F5BridgeResult<{ status: string }>>;
  calendarStatus?(): Promise<F5BridgeResult<CalendarConnection>>;
  disconnectCalendar?(): Promise<F5BridgeResult<CalendarConnection>>;
  list(query: SuggestionListQuery): Promise<F5BridgeResult<Page<Suggestion>>>;
  get(suggestionId: string): Promise<F5BridgeResult<Suggestion>>;
  approve(suggestionId: string, request: { version: number; payload?: SuggestionPayload }): Promise<F5BridgeResult<Suggestion>>;
  dismiss(suggestionId: string, request: { version: number }): Promise<F5BridgeResult<Suggestion>>;
  conflicts(suggestionId: string, payload: CalendarPayload): Promise<F5BridgeResult<ConflictResult>>;
  todos(query: TodoListQuery): Promise<F5BridgeResult<Page<Todo>>>;
  createTodo(request: TodoCreateRequest): Promise<F5BridgeResult<Todo>>;
  updateTodo(todoId: string, request: TodoUpdateRequest): Promise<F5BridgeResult<Todo>>;
}

// 앱 화면이 쓰는 전체 F5 호출. 실패는 Error(message=오류 코드)로 던진다.
export interface F5Client extends SuggestionsClient {
  calendar?: CalendarClient;
  list(query: SuggestionListQuery): Promise<Page<Suggestion>>;
  todos(query: TodoListQuery): Promise<Page<Todo>>;
  createTodo(request: TodoCreateRequest): Promise<Todo>;
  updateTodo(todoId: string, request: TodoUpdateRequest): Promise<Todo>;
}

export type CalendarConnection = { status: string; email: string; calendars: (CalendarOption & { timezone: string })[] };
export interface CalendarClient {
  connectCalendar?(): Promise<{ status: string }>;
  calendarStatus(): Promise<CalendarConnection>;
  disconnectCalendar(): Promise<CalendarConnection>;
}
