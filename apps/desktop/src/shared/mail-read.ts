import type { components } from '@klover/api-types';

export type MailSession = components['schemas']['LocalSession'];
export type MailSummary = components['schemas']['MailSummary'];
export type MailDetail = components['schemas']['MailDetail'];
export type MailPage = components['schemas']['MailPage'];
// 서버 MailSyncResult와 같은 형식. 공유 타입 재생성(패치 04) 뒤에는 components 타입으로 바꿀 수 있다.
export type MailSyncResult = { saved: number; skipped: number; mode: 'initial' | 'history' | 'rescan'; token_refreshed: boolean };
export type InboxQuery = { limit?: number; cursor?: string | null };
export type MailErrorCode = 'configuration' | 'unauthorized' | 'forbidden' | 'unavailable' |
  'not_found' | 'invalid_request' | 'invalid_response' | 'connection' | 'sync_in_progress' | 'gmail_unavailable';
export type MailError = { code: MailErrorCode; message: string };
export type MailResult<T> = { ok: true; data: T } | { ok: false; error: MailError };
export interface MailReadBridge {
  session(): Promise<MailResult<MailSession>>;
  inbox(query?: InboxQuery): Promise<MailResult<MailPage>>;
  detail(mailId: string): Promise<MailResult<MailDetail>>;
  /** Gmail 새 받은 메일 가져오기(POST /mails/sync). main/preload 연결 전에는 없을 수 있다. */
  sync?(): Promise<MailResult<MailSyncResult>>;
}

export const mailChannels = {
  session: 'klover:mail:session', inbox: 'klover:mail:inbox', detail: 'klover:mail:detail',
} as const;
// 새 메일 가져오기 통로. 조회 통로와 따로 두어 main/preload 연결(패치 02) 전후 모두 기존 조회가 그대로 동작한다.
export const mailSyncChannel = 'klover:mail:sync';

const messages: Record<MailErrorCode, string> = {
  configuration: '메일 API 연결 설정을 확인해 주세요. 서버 실행 안내의 앱 환경 변수가 필요합니다.',
  unauthorized: '메일 API 인증을 확인해 주세요. 기존 API 토큰 파일과 서버 설정이 일치해야 합니다.',
  forbidden: '메일 조회가 허용되지 않았습니다. 로컬 메일 API 실행 상태를 확인해 주세요.',
  unavailable: '연결 계정 또는 메일 저장소를 확인할 수 없습니다. 서버 상태를 확인해 주세요.',
  not_found: '메일을 찾을 수 없습니다. 목록을 새로고침해 주세요.',
  invalid_request: '메일 조회 요청을 확인해 주세요.',
  invalid_response: '메일 응답을 확인할 수 없습니다. 서버 버전을 확인해 주세요.',
  connection: '메일 서버에 연결할 수 없습니다. 서버 실행과 앱의 로컬 주소를 확인한 뒤 다시 시도해 주세요.',
  sync_in_progress: '이미 새 메일을 가져오고 있습니다. 잠시 후 다시 시도해 주세요.',
  gmail_unavailable: 'Gmail에서 새 메일을 가져오지 못했습니다. 기존 메일은 그대로입니다. 네트워크를 확인한 뒤 다시 시도하고, 계속 실패하면 Google 연결을 다시 확인해 주세요.',
};

export function mailFailure(code: MailErrorCode): { ok: false; error: MailError } {
  return { ok: false, error: { code, message: messages[code] } };
}

export function validMailId(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);
}

export function validInboxQuery(value: unknown): value is InboxQuery {
  if (value === undefined) return true;
  if (value === null || typeof value !== 'object' || Array.isArray(value)) return false;
  const query = value as Record<string, unknown>;
  return Object.keys(query).every(key => key === 'limit' || key === 'cursor') &&
    (query.limit === undefined || (Number.isInteger(query.limit) && Number(query.limit) >= 1 && Number(query.limit) <= 100)) &&
    (query.cursor === undefined || query.cursor === null ||
      (typeof query.cursor === 'string' && query.cursor.length > 0 && query.cursor.length <= 1024));
}

export function validSyncResult(value: unknown): value is MailSyncResult {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const row = value as Record<string, unknown>;
  const count = (item: unknown) => Number.isInteger(item) && Number(item) >= 0;
  return count(row.saved) && count(row.skipped) && ['initial', 'history', 'rescan'].includes(String(row.mode)) &&
    typeof row.token_refreshed === 'boolean';
}
