// 승인 전 기능 전용 계약. 공통 생성 타입에 반영할 패치는 별도 제공한다.
export type ReportPeriod = { start: string; end: string };
export type ReportStyle = 'bullet' | 'prose';
export type ReportTemplate = 'profile' | ReportStyle;
export type ReportMail = {
  mail_id: string;
  subject: string;
  from_addr: string;
  from_name: string;
  to: { addr: string; name: string; org?: string }[];
  received_at: string;
  body_text: string;
};
export type ReportItem = { item_id: string; text: string; evidence: string[] };
export type ReportSection = { name: string; items: ReportItem[] };
export type ReportProfile = {
  name: string;
  title: string;
  org: string;
  report_sections: string[];
  report_recipient: string;
  report_style: ReportStyle;
};
export type ReportScope = { total: number; grouped: number; groups: number; excluded: number };
export type WeeklyReportDocument = {
  ai_execution?: unknown;
  report_id: string;
  revision: number;
  period: ReportPeriod;
  title: string;
  subtitle: string;
  recipient: string;
  style: ReportStyle;
  sections: ReportSection[];
  scope: ReportScope;
  evidence_mails: ReportMail[];
  status: 'ready' | 'empty';
  generation: 'ai' | 'test_double' | 'none';
  partial_period?: boolean;
  collection_started_at?: string | null;
  created_at: string;
  updated_at: string;
};
export type WeeklyReportOptions = {
  default_period: ReportPeriod;
  profile: ReportProfile | null;
  remaining_days: number;
  available_on: string;
  generation: 'ai' | 'test_double' | 'unavailable';
};
export type GenerateReportRequest = ReportPeriod & {
  ai_provider?: import('../../../shared/ai-bridge').AIChoice;
  template: ReportTemplate;
  recipient: string;
  regenerate?: boolean;
  expected_revision?: number;
};
export type ExcludedMail = { mail: ReportMail; reason: 'notice' | 'newsletter' };
export interface WeeklyReportClient {
  options(): Promise<WeeklyReportOptions>;
  generate(request: GenerateReportRequest): Promise<WeeklyReportDocument>;
  get(id: string): Promise<WeeklyReportDocument>;
  excluded(id: string): Promise<ExcludedMail[]>;
  save(id: string, revision: number, sections: ReportSection[]): Promise<WeeklyReportDocument>;
}

export type WeeklyReportBridgeResult<T> = { ok: true; data: T } | {
  ok: false; error: { code: string; message: string };
};
export interface WeeklyReportIPC {
  options(): Promise<WeeklyReportBridgeResult<WeeklyReportOptions>>;
  generate(request: GenerateReportRequest): Promise<WeeklyReportBridgeResult<WeeklyReportDocument>>;
  get(id: string): Promise<WeeklyReportBridgeResult<WeeklyReportDocument>>;
  excluded(id: string): Promise<WeeklyReportBridgeResult<ExcludedMail[]>>;
  save(id: string, revision: number, sections: ReportSection[]): Promise<WeeklyReportBridgeResult<WeeklyReportDocument>>;
}
