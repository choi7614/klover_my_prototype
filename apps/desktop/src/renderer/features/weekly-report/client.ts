import type {
  GenerateReportRequest, ReportSection, WeeklyReportClient, WeeklyReportDocument,
  WeeklyReportOptions, ExcludedMail,
} from './types';

// F0에서 제한된 Electron IPC를 제공하면 이 포트에 연결한다. Renderer는 토큰을 받지 않는다.
export type WeeklyReportTransport = (request: {
  method: 'GET' | 'POST' | 'PATCH';
  path: string;
  body?: unknown;
}) => Promise<{ status: number; body: unknown }>;

const messages: Record<string, string> = {
  report_unavailable: '주간 보고 연결이 아직 준비되지 않았습니다.',
  session_unavailable: '연결된 메일 계정을 확인해 주세요.',
  analysis_not_ready: '분석 대기·실패 메일을 먼저 확인해 주세요. 기존 내용은 보존됩니다.',
  profile_missing: '주간 보고 프로필과 양식을 먼저 연결해 주세요.',
  profile_incomplete: '보고 대상을 입력해 주세요.',
  ai_unavailable: '보고서 AI가 아직 연결되지 않았습니다.',
  ai_failed: '보고서를 만들지 못했어요. 기존 내용은 보존됩니다.',
  invalid_report: '생성 결과의 섹션과 항목을 확인하지 못했습니다. 기존 내용은 보존됩니다.',
  invalid_evidence: '모든 항목에 대상 업무 메일 근거를 연결해 주세요.',
  report_conflict: '저장본이 변경되었습니다. 편집 내용을 보존했어요. 저장본을 확인해 주세요.',
  report_not_ready: '서버를 최신 버전으로 업데이트하고 다시 실행해 주세요.',
  not_found: '보고서를 찾을 수 없습니다.',
  unauthenticated: '앱의 연결 계정을 확인해 주세요.',
  storage_unavailable: '보고서 저장소에 연결할 수 없어요. 편집 내용은 보존됩니다.',
  validation_error: '기간·양식과 모든 항목의 내용·근거를 확인해 주세요.',
};

export class WeeklyReportClientError extends Error {
  constructor(public code: string) {
    super(messages[code] || '요청을 처리하지 못했어요. 기존 내용은 보존됩니다.');
  }
}

export function createWeeklyReportClient(transport: WeeklyReportTransport): WeeklyReportClient {
  async function call<T>(method: 'GET' | 'POST' | 'PATCH', path: string, body?: unknown): Promise<T> {
    let response;
    try { response = await transport({ method, path, body }); }
    catch { throw new WeeklyReportClientError('unreachable'); }
    if (response.status < 200 || response.status >= 300) {
      const payload = response.body as { error?: { code?: string } } | null;
      throw new WeeklyReportClientError(payload?.error?.code || 'unknown');
    }
    return response.body as T;
  }
  const path = (id: string) => `/reports/weekly/${encodeURIComponent(id)}`;
  return {
    options: () => call<WeeklyReportOptions>('GET', '/reports/weekly/options'),
    generate: (request: GenerateReportRequest) => call<WeeklyReportDocument>('POST', '/reports/weekly', request),
    get: (id) => call<WeeklyReportDocument>('GET', path(id)),
    excluded: (id) => call<ExcludedMail[]>('GET', `${path(id)}/excluded`),
    save: (id, revision, sections) => call<WeeklyReportDocument>('PATCH', path(id), { expected_revision: revision, sections }),
  };
}

export function draftIsValid(report: WeeklyReportDocument, sections: ReportSection[]): boolean {
  const ids = new Set(report.evidence_mails.map((mail) => mail.mail_id));
  const itemIds = new Set<string>();
  return sections.length === report.sections.length && sections.every((section, index) =>
    section.name === report.sections[index].name && section.items.every((item) => {
      if (!item.text.trim() || !item.evidence.length || new Set(item.evidence).size !== item.evidence.length
        || item.evidence.some((id) => !ids.has(id)) || itemIds.has(item.item_id)) return false;
      itemIds.add(item.item_id);
      return true;
    })) && (ids.size === 0 || itemIds.size > 0);
}

export function reportText(report: WeeklyReportDocument, sections: ReportSection[]): string {
  return [report.title, report.subtitle, `대상 기간: ${report.period.start} ~ ${report.period.end} · 조회 ${report.scope.total}건`, ...(report.partial_period ? ['일부 기간 자료: 사용 시작 이후 확보된 메일만 반영'] : []), `보고 대상: ${report.recipient}`, '',
    ...sections.flatMap((section, index) => [
      `${index + 1}. ${section.name}`,
      ...section.items.map((item) => `${report.style === 'bullet' ? ' - ' : ''}${item.text}`), '',
    ]),
  ].join('\n');
}
