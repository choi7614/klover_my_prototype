// F3 검색 통로(main ↔ preload ↔ 화면)의 공통 계약.
// 검색은 서버가 단계별(해석 → 결과 → 답변)로 보내므로, 시작 요청 뒤 main이 단계마다 메시지를 보낸다.

export const searchChannels = {
  start: 'klover:search:start',
  cancel: 'klover:search:cancel',
  recent: 'klover:search:recent',
  message: 'klover:search:message',
} as const;

/** main → 화면: 한 검색 요청의 단계 메시지. event는 화면에서 readSearchEvent로 다시 검사한다. */
export type SearchMessage =
  | { kind: 'event'; event: unknown }
  | { kind: 'error'; message: string }
  | { kind: 'done' };

export type SearchBridgeResult<T> = { ok: true; data: T } | { ok: false; message: string };

export interface SearchBridge {
  start(requestId: string, request: unknown): Promise<SearchBridgeResult<null>>;
  cancel(requestId: string): Promise<void>;
  recent(): Promise<SearchBridgeResult<unknown>>;
  /** 단계 메시지 구독. 반환 함수로 구독을 끝낸다. */
  onMessage(listener: (requestId: string, message: SearchMessage) => void): () => void;
}

export function validSearchRequestId(value: unknown): value is string {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{8,64}$/.test(value);
}

/** 화면이 보낼 수 있는 검색 요청 모양. 세부 조건은 서버가 다시 검사한다. */
export function validSearchRequest(value: unknown): value is { query: string; overrides?: Record<string, unknown>; search_id?: string } {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false;
  const row = value as Record<string, unknown>;
  if (Object.keys(row).some(key => !['query', 'overrides', 'search_id', 'ai_provider'].includes(key))) return false;
  if (row.ai_provider !== undefined && !['default', 'ollama', 'claude'].includes(row.ai_provider as string)) return false;
  if (typeof row.query !== 'string' || row.query.length > 500) return false;
  if (row.search_id !== undefined && (typeof row.search_id !== 'string' || !/^[a-f0-9]{32}$/.test(row.search_id))) return false;
  if (row.overrides !== undefined && (!row.overrides || typeof row.overrides !== 'object' || Array.isArray(row.overrides))) return false;
  try { return JSON.stringify(value).length <= 20_000; } catch { return false; }
}

export const searchConnectionMessage = '검색 서버에 연결하지 못했어요. 서버 실행 상태를 확인한 뒤 다시 시도해 주세요.';
export const searchConfigurationMessage = '검색 연결 설정을 확인해 주세요. 서버 실행 안내의 앱 환경 변수가 필요합니다.';
