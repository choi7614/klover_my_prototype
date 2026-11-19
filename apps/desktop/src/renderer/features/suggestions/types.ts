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
