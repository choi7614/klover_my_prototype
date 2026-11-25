import { useRef, useState } from 'react';
import { Calendar, Reply, SquareCheck, TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { CalendarOption, CalendarPayload, ConflictResult, Suggestion, SuggestionPayload, SuggestionsClient } from './types';

const inputClass = 'h-9 min-w-0 w-full rounded-md border border-input bg-background px-2 text-body focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40';

function localSeoul(value: string, offset = 540) {
  const stamp = new Date(value);
  if (!Number.isFinite(stamp.getTime())) return '';
  return new Date(stamp.getTime() + offset * 60 * 1000).toISOString().slice(0, 16);
}

function fromSeoul(value: string, zone = '+09:00') {
  return value ? `${value}:00${zone}` : '';
}

const label = { calendar: '일정 등록', todo: '할 일', reply: '회신' };
const Icon = { calendar: Calendar, todo: SquareCheck, reply: Reply };

function verifiedComplete(row: Suggestion) {
  if (row.status !== 'approved' || row.execution_status !== 'succeeded'
    || row.result?.mode !== row.execution_mode) return false;
  if (row.type === 'calendar') return row.execution_mode === 'live' && !!row.result?.external_id;
  if (row.type === 'todo') return row.execution_mode === 'internal' && !!row.result?.todo_id;
  return row.execution_mode === 'internal' && !!row.result?.external_id;
}

function errorMessage(code: unknown) {
  const key = code instanceof Error ? code.message : '';
  return {
    calendar_permission_expired: '캘린더 권한이 만료됐어요. 추가 동의를 확인해 주세요.',
    calendar_registration_failed: '일정 등록이 거절됐어요. 내용을 확인한 뒤 다시 승인해 주세요.',
    calendar_connection_failed: '캘린더 연결에 실패했어요. 다시 확인해 주세요.',
    calendar_selection_required: '현재 계정이 소유한 캘린더를 선택해 주세요.',
    calendar_not_connected: '캘린더 연결을 확인해 주세요. 아직 등록하지 않았어요.',
    calendar_scope_required: '캘린더 쓰기 권한을 확인해 주세요. 아직 등록을 확인하지 못했어요.',
    calendar_result_unknown: '등록 결과를 확인하지 못했어요. 내용을 바꾸지 말고 다시 확인해 주세요.',
    stale_version: '제안 상태가 바뀌었어요. 새로 불러온 내용을 확인해 주세요.',
    execution_in_progress: '이미 처리 중이에요. 잠시 후 상태를 다시 확인해 주세요.',
    reply_executor_not_connected: '답장 초안 기능 연결을 기다리고 있어요.',
  }[key] ?? '처리하지 못했어요. 연결 상태를 확인하고 다시 시도해 주세요.';
}

export function SuggestionCard({ suggestion, client, onChange, onActive, calendarReady = false,
  replyReady = false, emphasized = false, evidenceValid = true, calendars = [] }: {
  suggestion: Suggestion; client: SuggestionsClient; onChange: (row: Suggestion) => void;
  onActive: (id?: string) => void; calendarReady?: boolean; replyReady?: boolean;
  emphasized?: boolean; evidenceValid?: boolean;
  calendars?: CalendarOption[];
}) {
  const row = suggestion;
  const [zone, setZone] = useState('+09:00');
  const zoneOffset = (zone.startsWith('-') ? -1 : 1) * (Number(zone.slice(1, 3)) * 60 + Number(zone.slice(4)));
  const [draft, setDraft] = useState<SuggestionPayload>(row.payload);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [conflict, setConflict] = useState<ConflictResult>();
  const inFlight = useRef(false);
  const conflictSequence = useRef(0);
  const isPending = row.status === 'pending';
  const uncertain = row.execution_status === 'uncertain';
  const disabled = busy || !isPending || row.execution_status === 'executing';
  const canEdit = !disabled && !uncertain;
  const unavailable = row.type === 'calendar' ? !calendarReady : row.type === 'reply' ? !replyReady : false;
  const Glyph = Icon[row.type];
  const displayError = error || (row.last_error ? errorMessage(new Error(row.last_error)) : '');

  function edit(next: SuggestionPayload) {
    setDraft(next);
    setConflict(undefined);
    conflictSequence.current += 1;
    setError('');
  }

  async function handle(action: 'approve' | 'dismiss') {
    if (inFlight.current || disabled || !evidenceValid) return;
    inFlight.current = true;
    setBusy(true);
    setError('');
    try {
      const updated = action === 'approve'
        ? await client.approve(row.suggestion_id, { version: row.version, payload: draft })
        : await client.dismiss(row.suggestion_id, { version: row.version });
      if (updated.suggestion_id !== row.suggestion_id || updated.mail_id !== row.mail_id) throw new Error('invalid_response');
      if (updated.type !== row.type || (updated.status === 'approved' && !verifiedComplete(updated))) throw new Error('invalid_receipt');
      onChange(updated);
      setDraft(updated.payload);
    } catch (failure) {
      setError(errorMessage(failure));
      try {
        const latest = await client.get(row.suggestion_id);
        if (latest.suggestion_id === row.suggestion_id && latest.mail_id === row.mail_id) {
          onChange(latest);
          // 불명확한 실행의 재시도에는 서버에 고정된 입력만 사용한다.
          if (latest.execution_status === 'uncertain') setDraft(latest.payload);
        }
      } catch { /* 오류 안내를 유지하고 기존 본문은 계속 표시한다. */ }
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  async function checkConflicts() {
    if (row.type !== 'calendar' || !('start' in draft)) return;
    const sequence = ++conflictSequence.current;
    try {
      const result = await client.conflicts(row.suggestion_id, draft);
      if (sequence === conflictSequence.current) setConflict(result);
    } catch {
      if (sequence === conflictSequence.current) setError('겹치는 일정을 확인하지 못했어요.');
    }
  }

  const titleId = `suggestion-${row.suggestion_id}`;
  return <article aria-labelledby={titleId} data-testid={`suggestion-${row.type}`}
    onMouseEnter={() => onActive(row.suggestion_id)} onMouseLeave={() => onActive(undefined)}
    onFocus={() => onActive(row.suggestion_id)} onBlur={event => {
      if (!event.currentTarget.contains(event.relatedTarget)) onActive(undefined);
    }}
    className={`rounded-leaf border bg-card p-4 ${emphasized ? 'border-ai-border ring-[3px] ring-ai-subtle' : 'border-border'}`}>
    <h3 id={titleId} className={`mb-3 flex items-center gap-2 text-body font-bold ${row.type === 'calendar' ? 'text-cat-meeting-fg' : row.type === 'todo' ? 'text-cat-work-fg' : 'text-danger'}`}>
      <Glyph size={16} strokeWidth={1.8} aria-hidden />{label[row.type]}
    </h3>
    {row.status === 'dismissed' ? <p role="status" className="text-body text-muted-foreground">무시함</p>
      : verifiedComplete(row)
        ? <p role="status" className="text-body text-success">✓ {row.type === 'calendar' ? '캘린더에 추가했어요' : row.type === 'todo' ? '할 일에 추가했어요' : '답장 초안을 열었어요'}</p>
        : <>
          {'title' in draft && <label className="mb-2 grid gap-1 text-caption text-muted-foreground">제목
            <input className={inputClass} value={draft.title} disabled={!canEdit} maxLength={300}
              onChange={event => edit({ ...draft, title: event.target.value })} />
          </label>}
          {row.type === 'calendar' && 'start' in draft && <>
            <label className="mb-2 grid gap-1 text-caption text-muted-foreground">시간대 (UTC 차이)
              <select className={inputClass} value={zone} disabled={!canEdit} onChange={event => setZone(event.target.value)}>
                {['-12:00', '-08:00', '-07:00', '-05:00', '-04:00', '+00:00', '+01:00', '+02:00', '+05:30', '+08:00', '+09:00', '+10:00', '+12:00', '+14:00'].map(x => <option key={x} value={x}>UTC{x}</option>)}
              </select>
            </label>
            <label className="mb-2 grid gap-1 text-caption text-muted-foreground">시작
              <input type="datetime-local" className={inputClass} value={localSeoul(draft.start, zoneOffset)} disabled={!canEdit}
                onChange={event => edit({ ...draft, start: fromSeoul(event.target.value, zone) })} />
            </label>
            <label className="mb-2 grid gap-1 text-caption text-muted-foreground">종료
              <input type="datetime-local" className={inputClass} value={localSeoul(draft.end, zoneOffset)} disabled={!canEdit}
                onChange={event => edit({ ...draft, end: fromSeoul(event.target.value, zone) })} />
            </label>
            <label className="mb-2 grid gap-1 text-caption text-muted-foreground">장소
              <input className={inputClass} value={draft.location ?? ''} disabled={!canEdit} maxLength={1000}
                onChange={event => edit({ ...draft, location: event.target.value })} />
            </label>
            <label className="mb-2 grid gap-1 text-caption text-muted-foreground">캘린더
              <select className={inputClass} value={draft.calendar_id ?? ''} disabled={!canEdit || !calendarReady}
                onChange={event => edit({ ...draft, calendar_id: event.target.value })}>
                <option value="">캘린더 선택</option>
                {calendars.map(calendar => <option key={calendar.id} value={calendar.id}>{calendar.label}</option>)}
              </select>
            </label>
            <Button variant="secondary" className="mb-2 h-8 w-full px-2 text-caption" disabled={disabled || !calendarReady}
              onClick={() => void checkConflicts()}>겹치는 일정 확인</Button>
          </>}
          {row.type === 'todo' && 'title' in draft && !('start' in draft) && <label className="mb-2 grid gap-1 text-caption text-muted-foreground">마감
            <input type="date" className={inputClass} value={draft.due ?? ''} disabled={!canEdit}
              onChange={event => edit({ ...draft, due: event.target.value || null })} />
          </label>}
          {'reason' in draft && <p className="mb-3 text-body">{draft.reason}</p>}
          {conflict?.status === 'unavailable' && <p className="mb-2 text-caption text-muted-foreground">겹치는 일정을 확인하지 못했어요.</p>}
          {conflict?.status === 'checked' && (conflict.conflicts ?? []).length === 0 && <p className="mb-2 text-caption text-muted-foreground">겹치는 일정이 없습니다.</p>}
          {!!conflict?.conflicts?.length && <div role="status" className="mb-3 flex gap-2 rounded-md border border-warning-border bg-warning-subtle p-2 text-caption text-warning">
            <TriangleAlert size={16} aria-hidden /><span>같은 시간에 {conflict.conflicts.length}건의 일정이 있습니다.</span>
          </div>}
          {row.execution_status === 'simulated' && <p role="status" className="mb-3 text-caption text-ai-text">{row.type === 'calendar' ? '테스트 실행을 확인했어요. 실제 캘린더에는 등록하지 않았어요.' : '테스트 처리를 확인했어요. 실제 할 일에는 추가하지 않았어요.'}</p>}
          {uncertain && <p role="status" className="mb-3 text-caption text-warning">등록 결과를 확인 중이에요. 같은 내용으로 다시 확인할 수 있어요.</p>}
          {row.execution_status === 'executing' && <p role="status" className="mb-3 text-caption text-muted-foreground">처리 중이에요. 상태를 다시 확인해 주세요.</p>}
          {unavailable && <p className="mb-3 text-caption text-muted-foreground">{row.type === 'calendar' ? '캘린더 연결과 쓰기 권한을 확인해 주세요.' : '답장 초안 기능 연결을 기다리고 있어요.'}</p>}
          {!evidenceValid && <p role="alert" className="mb-3 text-caption text-danger">원본 메일의 근거를 확인하지 못했어요. 제안을 다시 불러와 주세요.</p>}
          {displayError && <p role="alert" className="mb-3 text-caption text-danger">{displayError}</p>}
          <div className="flex flex-wrap gap-2">
            <Button variant={row.type === 'calendar' ? 'default' : 'secondary'} className="h-9 flex-1 px-2"
              disabled={disabled || unavailable || !evidenceValid || !validPayload(draft)
                || (row.type === 'calendar' && 'calendar_id' in draft && !calendars.some(calendar => calendar.id === draft.calendar_id))}
              onClick={() => void handle('approve')}>
              {busy ? '처리 중…' : uncertain ? '등록 결과 다시 확인' : row.type === 'calendar' ? '캘린더에 추가' : row.type === 'todo' ? '할 일에 추가' : '회신 초안 만들기'}
            </Button>
            <Button variant="secondary" className="h-9 px-3" disabled={disabled || uncertain || !evidenceValid}
              onClick={() => void handle('dismiss')}>무시</Button>
          </div>
        </>}
  </article>;
}

function validPayload(payload: SuggestionPayload) {
  if ('start' in payload) {
    const calendar = payload as CalendarPayload;
    return !!calendar.title.trim() && !!calendar.calendar_id?.trim()
      && Number.isFinite(Date.parse(calendar.start)) && Date.parse(calendar.end) > Date.parse(calendar.start);
  }
  return 'title' in payload ? !!payload.title.trim() : !!payload.reason.trim();
}
