// F1 분석 결과 표시 통로. 정해진 동작(묶음 조회·다시 시도)만 main/preload에 공개한다.
// 토큰·주소·소유자는 공개하지 않는다. 서버 응답은 여기 검사기로 새 객체를 만들어 넘긴다(예상 밖 필드 차단).
import { validMailId } from './mail-read';

export type AnalysisCategory = 'work_request' | 'meeting' | 'approval' | 'report_share' | 'notice' | 'external' | 'newsletter';
export type AnalysisStatus = 'pending' | 'done' | 'failed';
/** ready=분석 가능, not_configured=AI 미설정, external_blocked=외부 AI라 실제 메일은 분석 안 함, not_connected=서버 조립 전 */
export type AutoAnalysisState = 'ready' | 'not_configured' | 'external_blocked' | 'not_connected';

export type MailAnalysisView = {
  mail_id: string;
  analysis_status: AnalysisStatus;
  /** 화면에 보일 분류(사용자 수정 우선) */
  category: AnalysisCategory | null;
  summary: string | null;
  needs_reply: boolean | null;
  action_items: { text: string; due: string | null }[];
  priority: 'high' | 'normal' | 'low' | null;
  priority_reason: string | null;
  failure_code: string | null;
};
export type MailAnalysisBatch = { items: MailAnalysisView[]; auto_analysis: AutoAnalysisState };
export type AnalysisRetryResult = { mail_id: string; analysis_status: 'pending' };
export type AnalysisErrorCode = 'invalid_request' | 'invalid_response' | 'connection' | 'unauthorized' | 'not_found' |
  'analysis_unavailable' | 'already_analyzed' | 'unavailable' | 'configuration';
export type AnalysisResult<T> = { ok: true; data: T } | { ok: false; error: { code: AnalysisErrorCode; message: string } };

export type CategoryUpdated = { mail_id: string; user_label: AnalysisCategory; effective_category: AnalysisCategory };

export interface F1Bridge {
  setCategory(mailId: string, category: AnalysisCategory): Promise<AnalysisResult<CategoryUpdated>>;
  /** 목록에 보이는 메일들의 분석 결과(최대 100건). 다른 소유자·없는 메일은 빠진다. */
  batch(mailIds: string[]): Promise<AnalysisResult<MailAnalysisBatch>>;
  /** 실패한 분석 다시 시도. AI가 연결되지 않았으면 analysis_unavailable. */
  retry(mailId: string): Promise<AnalysisResult<AnalysisRetryResult>>;
}

export const f1Channels = { batch: 'klover:analysis:batch', retry: 'klover:analysis:retry', setCategory: 'klover:analysis:setCategory' } as const;
export const MAX_BATCH = 100;

const messages: Record<AnalysisErrorCode, string> = {
  invalid_request: 'AI 분석 요청을 확인해 주세요.',
  invalid_response: 'AI 분석 응답을 확인할 수 없습니다. 서버 버전을 확인해 주세요.',
  connection: 'AI 분석 결과를 불러오지 못했습니다. 서버 실행 상태를 확인해 주세요.',
  unauthorized: '메일 API 인증을 확인해 주세요.',
  not_found: '메일을 찾을 수 없습니다. 목록을 새로고침해 주세요.',
  analysis_unavailable: 'AI가 연결되지 않아 지금은 다시 분석할 수 없습니다. 메일 원문은 그대로입니다.',
  already_analyzed: '이미 분석을 마친 메일입니다.',
  unavailable: 'AI 분석 결과를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.',
  configuration: '메일 API 연결 설정을 확인해 주세요.',
};

export function analysisFailure(code: AnalysisErrorCode): { ok: false; error: { code: AnalysisErrorCode; message: string } } {
  return { ok: false, error: { code, message: messages[code] } };
}

export function validBatchIds(value: unknown): value is string[] {
  return Array.isArray(value) && value.length >= 1 && value.length <= MAX_BATCH && value.every(validMailId);
}

const categories: readonly string[] = ['work_request', 'meeting', 'approval', 'report_share', 'notice', 'external', 'newsletter'];
const states: readonly string[] = ['ready', 'not_configured', 'external_blocked', 'not_connected'];

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('response');
  return value as Record<string, unknown>;
}
function optionalText(value: unknown, max: number): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'string' || value.length > max) throw new Error('response');
  return value;
}
function oneOf<T extends string>(value: unknown, allowed: readonly string[]): T | null {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'string' || !allowed.includes(value)) throw new Error('response');
  return value as T;
}

export function parseAnalysisView(value: unknown): MailAnalysisView {
  const row = record(value);
  if (!validMailId(row.mail_id)) throw new Error('response');
  const status = oneOf<AnalysisStatus>(row.analysis_status, ['pending', 'done', 'failed']);
  if (!status) throw new Error('response');
  const items = row.action_items ?? [];
  if (!Array.isArray(items) || items.length > 100) throw new Error('response');
  const needsReply = row.needs_reply ?? null;
  if (needsReply !== null && typeof needsReply !== 'boolean') throw new Error('response');
  return {
    mail_id: row.mail_id,
    analysis_status: status,
    category: oneOf<AnalysisCategory>(row.category, categories),
    summary: optionalText(row.summary, 1000),
    needs_reply: needsReply,
    action_items: items.map(item => {
      const entry = record(item);
      const due = optionalText(entry.due, 10);
      if (due !== null && !/^\d{4}-\d{2}-\d{2}$/.test(due)) throw new Error('response');
      const text = optionalText(entry.text, 2000);
      if (!text) throw new Error('response');
      return { text, due };
    }),
    priority: oneOf<'high' | 'normal' | 'low'>(row.priority, ['high', 'normal', 'low']),
    priority_reason: optionalText(row.priority_reason, 500),
    failure_code: optionalText(row.failure_code, 64),
  };
}

export function parseAnalysisBatch(value: unknown, requested: string[]): MailAnalysisBatch {
  const page = record(value);
  if (!Array.isArray(page.items) || page.items.length > requested.length) throw new Error('response');
  const auto = oneOf<AutoAnalysisState>(page.auto_analysis, states);
  if (!auto) throw new Error('response');
  const items = page.items.map(parseAnalysisView);
  // 요청한 메일의 결과만 받는다(근거 mail_id가 다른 결과를 섞지 않는다).
  if (items.some(item => !requested.includes(item.mail_id))) throw new Error('response');
  return { items, auto_analysis: auto };
}

export function parseRetryResult(value: unknown, mailId: string): AnalysisRetryResult {
  const row = record(value);
  if (row.mail_id !== mailId || row.analysis_status !== 'pending') throw new Error('response');
  return { mail_id: mailId, analysis_status: 'pending' };
}

export function validCategory(value: unknown): value is AnalysisCategory {
  return typeof value === 'string' && categories.includes(value);
}
export function parseCategoryUpdated(value: unknown, mailId: string, category: AnalysisCategory): CategoryUpdated {
  const row = record(value);
  if (row.mail_id !== mailId || row.user_label !== category || row.effective_category !== category) throw new Error('response');
  return { mail_id: mailId, user_label: category, effective_category: category };
}
