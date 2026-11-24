// F2 프로필·답장 초안 통로(main ↔ preload ↔ 화면)의 공통 계약.
// 화면은 정해진 동작 이름과 검증된 ID·본문만 보낸다. 주소·인증·소유자는 main이 정한다.

export type F2Operation =
  | 'profile' | 'saveProfile' | 'style' | 'deleteStyle' | 'preview'
  | 'mail' | 'createDraft' | 'draft' | 'saveDraft' | 'reviseDraft';

/** 각 동작이 받는 인수 모양: none=없음, body=본문, id=ID, idBody=ID+본문 */
export type F2Shape = 'none' | 'body' | 'id' | 'idBody';

export type F2Route = { method: 'GET' | 'PUT' | 'POST' | 'PATCH' | 'DELETE'; path: (id?: string) => string; shape: F2Shape };

// F2-handoff.md의 'F2Client 메서드 ↔ 서버 경로' 표와 같다. 발송 경로는 없다.
export const f2Routes: Record<F2Operation, F2Route> = {
  profile: { method: 'GET', path: () => '/profile', shape: 'none' },
  saveProfile: { method: 'PUT', path: () => '/profile', shape: 'body' },
  style: { method: 'GET', path: () => '/profile/style', shape: 'none' },
  deleteStyle: { method: 'DELETE', path: () => '/profile/style', shape: 'none' },
  preview: { method: 'POST', path: () => '/profile/preview', shape: 'body' },
  mail: { method: 'GET', path: id => `/mails/${encodeURIComponent(id ?? '')}`, shape: 'id' },
  createDraft: { method: 'POST', path: () => '/drafts', shape: 'body' },
  draft: { method: 'GET', path: id => `/drafts/${encodeURIComponent(id ?? '')}`, shape: 'id' },
  saveDraft: { method: 'PATCH', path: id => `/drafts/${encodeURIComponent(id ?? '')}`, shape: 'idBody' },
  reviseDraft: { method: 'POST', path: id => `/drafts/${encodeURIComponent(id ?? '')}/revise`, shape: 'idBody' },
};

export const f2Operations = Object.keys(f2Routes) as F2Operation[];
export const f2Channel = (operation: F2Operation) => `klover:f2:${operation}`;

export type F2Error = { code: string; message: string };
export type F2Result<T = unknown> = { ok: true; data: T } | { ok: false; error: F2Error };

/** preload가 화면에 공개하는 F2 통로. 인수는 main에서 다시 검사한다. */
export type F2Bridge = Readonly<Record<F2Operation, (...args: unknown[]) => Promise<F2Result>>>;

const MAX_BODY = 200_000;

export function validF2Id(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);
}

export function validF2Body(value: unknown): value is Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  try { return JSON.stringify(value).length <= MAX_BODY; } catch { return false; }
}

/** 동작별 인수 모양 검사. 통과하면 [id, body]로 나눠 돌려준다. */
export function f2Arguments(operation: F2Operation, args: unknown[]): { id?: string; body?: Record<string, unknown> } | null {
  switch (f2Routes[operation].shape) {
    case 'none': return args.length === 0 ? {} : null;
    case 'body': return args.length === 1 && validF2Body(args[0]) ? { body: args[0] } : null;
    case 'id': return args.length === 1 && validF2Id(args[0]) ? { id: args[0] } : null;
    case 'idBody': return args.length === 2 && validF2Id(args[0]) && validF2Body(args[1]) ? { id: args[0], body: args[1] } : null;
  }
}

const messages = {
  configuration: '프로필·초안 연결 설정을 확인해 주세요. 서버 실행 안내의 앱 환경 변수가 필요합니다.',
  invalid_request: '요청 내용을 확인해 주세요.',
  invalid_response: '서버 응답을 확인할 수 없어요. 서버 버전을 확인해 주세요.',
  connection: '서버에 연결할 수 없어요. 서버 실행 상태를 확인한 뒤 다시 시도해 주세요.',
  timeout: '응답 대기 시간이 지났어요. 잠시 뒤 다시 시도해 주세요. 편집한 내용은 보존됩니다.',
  unavailable: '요청을 처리하지 못했어요. 입력한 내용은 보존됩니다. 다시 시도해 주세요.',
} as const;

export function f2Failure(code: keyof typeof messages): { ok: false; error: F2Error } {
  return { ok: false, error: { code, message: messages[code] } };
}
