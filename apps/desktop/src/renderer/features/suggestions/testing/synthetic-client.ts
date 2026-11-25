import type { CalendarPayload, ConflictResult, Suggestion, SuggestionPayload, SuggestionsClient } from '../types';

export const syntheticBody = '합성 메일입니다.\n📅 11월 20일 오후 2시에 테스트 회의를 합니다.\n장소는 테스트 회의실입니다.\n자료를 11월 19일까지 올려 주세요.\n참석 가능 여부를 회신해 주세요.\n<script>실행하면 안 되는 합성 텍스트</script>';

function evidence(quote: string) {
  const points = Array.from(syntheticBody);
  const start = Array.from(syntheticBody.slice(0, syntheticBody.indexOf(quote))).length;
  return [{ mail_id: 'synthetic-mail', start, end: start + Array.from(quote).length, quote: points.slice(start, start + Array.from(quote).length).join('') }];
}

export function syntheticSuggestions(): Suggestion[] {
  const common = {
    mail_id: 'synthetic-mail', body_sha256: 'synthetic-body-validated-by-test',
    status: 'pending' as const, execution_status: 'idle' as const, execution_mode: 'none' as const,
    result: null, last_error: null, version: 1, notified_at: null,
    created_at: '2026-11-19T00:00:00Z', resolved_at: null,
  };
  return [
    { ...common, suggestion_id: 'synthetic-calendar', type: 'calendar', payload: {
      title: '합성 결산 리뷰 회의', start: '2026-11-20T14:00:00+09:00', end: '2026-11-20T15:00:00+09:00',
      location: '테스트 회의실', calendar_id: 'synthetic-work',
    }, evidence_spans: evidence('📅 11월 20일 오후 2시에 테스트 회의를 합니다.') },
    { ...common, suggestion_id: 'synthetic-todo', type: 'todo', payload: { title: '합성 자료 업로드', due: '2026-11-19' }, evidence_spans: evidence('자료를 11월 19일까지 올려 주세요.') },
    { ...common, suggestion_id: 'synthetic-reply', type: 'reply', payload: { reason: '참석 가능 여부 회신' }, evidence_spans: evidence('참석 가능 여부를 회신해 주세요.') },
  ];
}

export class SyntheticSuggestionsClient implements SuggestionsClient {
  rows = syntheticSuggestions();
  failApprovals = false;
  calls: { action: string; id: string; payload?: SuggestionPayload }[] = [];

  async get(id: string) {
    const row = this.rows.find(item => item.suggestion_id === id);
    if (!row) throw new Error('not_found');
    return structuredClone(row);
  }

  async approve(id: string, request: { version: number; payload?: SuggestionPayload }) {
    this.calls.push({ action: 'approve', id, payload: request.payload });
    const row = await this.get(id);
    if (this.failApprovals) throw new Error('calendar_unavailable');
    if (row.type === 'reply') throw new Error('reply_executor_not_connected');
    const updated = {
      ...row, payload: request.payload ?? row.payload, version: row.version + 1,
      execution_status: 'simulated', execution_mode: 'test', result: { mode: 'test', external_id: 'synthetic-only' },
    } as Suggestion;
    this.rows = this.rows.map(item => item.suggestion_id === id ? updated : item);
    return structuredClone(updated);
  }

  async dismiss(id: string, request: { version: number }) {
    this.calls.push({ action: 'dismiss', id });
    const row = await this.get(id);
    const updated = { ...row, status: 'dismissed' as const, version: request.version + 1, resolved_at: '2026-11-19T00:01:00Z' };
    this.rows = this.rows.map(item => item.suggestion_id === id ? updated : item);
    return structuredClone(updated);
  }

  async conflicts(id: string, payload: CalendarPayload): Promise<ConflictResult> {
    this.calls.push({ action: 'conflicts', id });
    return { status: 'checked', request_hash: 'synthetic-only', mode: 'test', conflicts: [{ start: payload.start, end: payload.end, title: '합성 주간회의' }] };
  }
}
