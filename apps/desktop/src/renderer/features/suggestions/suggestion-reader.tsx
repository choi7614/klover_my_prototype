import { useState, type ReactNode } from 'react';
import { EvidenceBody, validEvidence } from './evidence-body';
import { SuggestionCard } from './suggestion-card';
import type { CalendarOption, Suggestion, SuggestionsClient } from './types';

export function SuggestionReader({ mailId, body, suggestions, client, onChange,
  calendarReady = false, replyReady = false, loading = false, calendars = [], header }: {
  mailId: string; body: string; suggestions: Suggestion[]; client: SuggestionsClient;
  onChange: (row: Suggestion) => void; calendarReady?: boolean; replyReady?: boolean; loading?: boolean;
  calendars?: CalendarOption[];
  /** 메일 머리(제목·보낸 사람 등). 본문 위에 그대로 표시한다. */
  header?: ReactNode;
}) {
  const [activeId, setActiveId] = useState<string>();
  const order = { calendar: 0, todo: 1, reply: 2 };
  const rows = suggestions.filter(row => row.mail_id === mailId).sort((a, b) => order[a.type] - order[b.type]);
  const firstPending = rows.find(row => row.status === 'pending')?.suggestion_id;
  return <div className="flex min-w-0 flex-col min-[1281px]:flex-row" data-testid="suggestion-reader">
    <section aria-label="메일 본문" className="min-w-0 flex-1 p-6">
      {header}
      <EvidenceBody mailId={mailId} body={body} suggestions={rows} activeId={activeId} />
    </section>
    {(loading || rows.length > 0) && <aside aria-label="AI 제안" className="order-first flex shrink-0 flex-col gap-3 border-b border-border bg-gray-25 p-4 min-[1281px]:order-last min-[1281px]:w-[340px] min-[1281px]:border-b-0 min-[1281px]:border-l">
      <div><h2 className="text-title font-bold text-ai-text">AI 제안 {rows.filter(row => row.status === 'pending').length}건</h2>
        <p className="mt-1 text-caption text-muted-foreground">제안만 하고, 실행은 직접 고릅니다</p></div>
      {loading && <div role="status"><p className="text-body text-ai-text">일정을 확인하고 있어요…</p><div className="mt-3 h-24 rounded-md bg-muted" /></div>}
      {rows.map(row => <SuggestionCard key={row.suggestion_id} suggestion={row} client={client}
        onChange={onChange} onActive={setActiveId} calendarReady={calendarReady} replyReady={replyReady}
        calendars={calendars} emphasized={row.suggestion_id === firstPending} evidenceValid={validEvidence(mailId, body, row.evidence_spans)} />)}
    </aside>}
  </div>;
}
