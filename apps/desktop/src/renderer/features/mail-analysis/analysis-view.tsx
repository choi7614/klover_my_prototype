import { useEffect, useRef, useState } from 'react';
import { AnalysisClientError } from './client';
import { cn } from '@/lib/utils';
import type { AnalysisCategory, AutoAnalysisState, MailAnalysisView } from '../../../shared/f1-bridge';
import { CATEGORIES, PRIORITY_LABELS, STATUS_TAGS, TAG_BASE } from './categories';
import type { RetryNotice } from './use-mail-analysis';

const weekdays = ['일', '월', '화', '수', '목', '금', '토'];

function parts(due: string) {
  const [year, month, day] = due.split('-').map(Number);
  return { year, month, day };
}
/** 목록 태그: "10/16" */
export function shortDate(due: string): string {
  const { month, day } = parts(due);
  return `${month}/${day}`;
}
/** 요약 박스: "10/16(금)" — 날짜만 있는 값이라 시간대 영향 없이 요일을 계산한다. */
export function dayDate(due: string): string {
  const { year, month, day } = parts(due);
  return `${shortDate(due)}(${weekdays[new Date(Date.UTC(year, month - 1, day)).getUTCDay()]})`;
}
export function earliestDue(view: MailAnalysisView): string | null {
  const dates = view.action_items.map(item => item.due).filter((due): due is string => Boolean(due)).sort();
  return dates[0] ?? null;
}
/** 목록 한 줄 요약 = summary 첫 문장 */
export function firstSentence(summary: string): string {
  const line = summary.split('\n')[0].trim();
  const match = /^(.+?[.!?。])(\s|$)/.exec(line);
  return match ? match[1] : line;
}

function waitingText(state: AutoAnalysisState | null): string {
  if (state === 'ready') return 'AI가 분석하고 있어요…';
  if (state === 'external_blocked') return '외부 AI 설정이라 실제 메일은 분석하지 않아요';
  return 'AI 연결 전이라 분석을 기다리고 있어요';
}

function failureText(code: string | null): string {
  // 서버가 보낸 임의 문자열은 화면에 노출하지 않고 고정 안내만 사용한다.
  switch (code) {
    case 'invalid_response': return 'AI 응답의 형식 또는 근거 위치를 검증하지 못했어요.';
    case 'provider_error': return '로컬 AI 호출에 실패했어요. 연결 또는 응답 시간을 확인해 주세요.';
    case 'embedding_error': return '검색용 데이터 생성에 실패했어요. 로컬 임베딩 모델 설정을 확인해 주세요.';
    case 'input_too_large': return '메일이 자동 분석 길이 제한을 초과했어요. 원문은 그대로 읽을 수 있어요.';
    default: return '분석 실패 원인을 확인하지 못했어요. 원문은 그대로 읽을 수 있어요.';
  }
}

export function CategoryTag({ category }: { category: keyof typeof CATEGORIES }) {
  const item = CATEGORIES[category];
  return <span className={cn(TAG_BASE, item.tag)}>{item.label}</span>;
}

function Tags({ view }: { view: MailAnalysisView }) {
  const due = earliestDue(view);
  if (!view.category && !view.needs_reply && !due) return null;
  return <span className="mt-1.5 flex flex-wrap gap-1" data-testid="analysis-tags">
    {view.category && <CategoryTag category={view.category} />}
    {view.needs_reply && <span className={cn(TAG_BASE, STATUS_TAGS.needs_reply.tag)}>{STATUS_TAGS.needs_reply.label}</span>}
    {due && <span className={cn(TAG_BASE, STATUS_TAGS.due.tag)}>{STATUS_TAGS.due.label(shortDate(due))}</span>}
  </span>;
}

/** S03 메일 한 줄의 요약·태그 자리. 분석 결과가 없으면 미리보기를 그대로 보여 준다. */
export function MailAnalysisLine({ view, state, preview }: { view?: MailAnalysisView; state: AutoAnalysisState | null; preview: string }) {
  if (!view) return <span className="mt-1 line-clamp-2 text-caption text-muted-foreground">{preview}</span>;
  if (view.analysis_status === 'done' && view.summary) {
    return <>
      <span className="mt-1 block truncate text-caption text-ai-text">{firstSentence(view.summary)}</span>
      <Tags view={view} />
    </>;
  }
  const failed = view.analysis_status === 'failed';
  return <>
    <span className="mt-1 line-clamp-1 text-caption text-muted-foreground">{preview}</span>
    <span className="mt-1 block truncate text-caption text-muted-foreground">
      {failed ? '요약을 만들지 못했어요' : <>{waitingText(state)}</>}
    </span>
    {!failed && state === 'ready'
      ? <span className="mt-1.5 flex gap-1" aria-hidden="true"><span className="h-5 w-14 animate-pulse rounded-sm bg-muted" /><span className="h-5 w-12 animate-pulse rounded-sm bg-muted" /></span>
      : <Tags view={view} />}
  </>;
}

/** S03 AI 요약 박스와 분류 줄. 대기·실패 상태도 같은 자리에 보여 준다. 원문은 박스 아래에 그대로 있다. */
export function AiSummaryBox({ view, state, onRetry, retryNotice, onCategoryChange }: {
  onCategoryChange?: (mailId: string, category: AnalysisCategory) => Promise<void>;
  view?: MailAnalysisView; state: AutoAnalysisState | null; onRetry: (mailId: string) => void; retryNotice: RetryNotice | null;
}) {
  if (!view) return null;
  if (view.analysis_status === 'failed') {
    const canRetry = state === 'ready';
    return <div className="mb-4" data-testid="ai-summary-failed">
      <p className="flex items-center gap-2 rounded-md bg-muted px-4 py-2 text-caption text-muted-foreground">
        요약을 만들지 못했어요
        <span aria-hidden="true">·</span>
        <button type="button" disabled={!canRetry} onClick={() => onRetry(view.mail_id)}
          title={canRetry ? undefined : 'AI가 연결되면 다시 시도할 수 있어요'}
          className="font-semibold text-ai-text underline-offset-2 hover:underline disabled:cursor-not-allowed disabled:text-muted-foreground disabled:no-underline focus-visible:outline-ring">다시 시도</button>
      </p>
      <p className="mt-2 text-caption text-muted-foreground">{failureText(view.failure_code)}</p>
      {retryNotice?.mailId === view.mail_id && <p role="alert" className="mt-2 text-caption text-danger">{retryNotice.message}</p>}
    </div>;
  }
  if (view.analysis_status !== 'done' || !view.summary) {
    if (state !== 'ready') {
      return <p className="mb-4 rounded-md bg-muted px-4 py-2 text-caption text-muted-foreground" data-testid="ai-summary-waiting">
        {waitingText(state)}. 원문은 아래에 그대로 있어요.
      </p>;
    }
    return <div role="status" className="mb-4 space-y-3 rounded-leaf bg-ai-subtle px-4 py-3.5" data-testid="ai-summary-loading">
      <p className="text-body font-semibold text-ai-text">AI가 분석하고 있어요…</p>
      <div className="h-4 w-4/5 animate-pulse rounded-sm bg-ai-border" />
      <div className="h-4 w-3/5 animate-pulse rounded-sm bg-ai-border" />
    </div>;
  }
  const action = view.action_items[0];
  const due = earliestDue(view);
  return <div className="mb-4">
    <section aria-label="AI 요약" className="rounded-leaf bg-ai-subtle px-4 py-3.5" data-testid="ai-summary-box">
      <p className="text-body font-semibold text-ai-text">AI 요약</p>
      <p className="mt-2 whitespace-pre-wrap text-body">{view.summary}</p>
      {(action || due || view.priority) && <p className="mt-3 flex flex-wrap gap-x-5 gap-y-1 border-t border-ai-border pt-3 text-caption">
        {action && <span><span className="text-muted-foreground">내가 할 일 </span><strong>{action.text}</strong>{view.action_items.length > 1 && <span className="text-muted-foreground"> 외 {view.action_items.length - 1}건</span>}</span>}
        {due && <span><span className="text-muted-foreground">마감 </span><strong>{dayDate(due)}</strong></span>}
        {view.priority && <span><span className="text-muted-foreground">우선순위 </span><strong>{PRIORITY_LABELS[view.priority]}</strong>{view.priority_reason && <span className="text-muted-foreground"> · {view.priority_reason}</span>}</span>}
      </p>}
    </section>
    {view.category && (onCategoryChange ? <CategoryControl key={view.mail_id} view={view} onChange={onCategoryChange} /> : <p className="mt-2 flex items-center gap-2 text-caption text-muted-foreground">분류 <CategoryTag category={view.category} /></p>)}
  </div>;
}

function CategoryControl({ view, onChange }: { view: MailAnalysisView; onChange: (id: string, category: AnalysisCategory) => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const active = useRef(true);
  const inFlight = useRef(false);
  useEffect(() => { active.current = true; return () => { active.current = false; }; }, []);
  async function change(category: AnalysisCategory) {
    if (inFlight.current || category === view.category) return;
    inFlight.current = true; setBusy(true); setNotice(''); setError('');
    try { await onChange(view.mail_id, category); if (active.current) setNotice('분류를 저장했어요. 같은 발신자의 다음 분석에 참고합니다.'); }
    catch (error) { if (active.current) setError(error instanceof AnalysisClientError ? error.message : '분류를 저장하지 못했어요. 현재 분류를 다시 확인한 뒤 시도해 주세요.'); }
    finally { inFlight.current = false; if (active.current) setBusy(false); }
  }
  return <div className="mt-3 space-y-1 text-caption">
    <label className="flex flex-wrap items-center gap-2">메일 분류
      <select aria-label="메일 분류" value={view.category ?? ''} disabled={busy} onChange={e => void change(e.target.value as AnalysisCategory)} className="h-9 rounded-md border border-input bg-background px-3 text-body text-foreground focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50">
        {Object.entries(CATEGORIES).map(([key, value]) => <option key={key} value={key}>{value.label}</option>)}
      </select><span className="text-muted-foreground">{busy ? '저장 중…' : '분류가 다르면 변경해 주세요.'}</span>
    </label>
    {notice && <p role="status" className="text-muted-foreground">{notice}</p>}
    {error && <p role="alert" className="text-danger">{error}</p>}
  </div>;
}
