export type AIProvider = 'ollama' | 'claude';
export type AIChoice = 'default' | AIProvider;
export type AIPurpose = 'draft' | 'search' | 'weekly_report';
export type AIState = { mode?: 'local_only' | 'hybrid'; defaults: Record<AIPurpose, AIProvider>; external_consent: boolean; claude_key_set: boolean; local_configured: boolean; claude_model: string };
export type AIUpdate = { mode?: 'local_only' | 'hybrid'; defaults: AIState['defaults']; external_consent: boolean; api_key?: string; clear_key?: boolean; claude_model?: string };
export type AIResult<T> = { ok: true; data: T } | { ok: false; error: { code: string; message: string } };
export interface AIBridge {
  get(): Promise<AIResult<AIState>>;
  save(update: AIUpdate): Promise<AIResult<AIState>>;
  check(provider: AIProvider): Promise<AIResult<{ status: 'reachable'; provider: AIProvider }>>;
}
export const validProvider = (v: unknown): v is AIProvider => v === 'ollama' || v === 'claude';
export function readAIState(value: unknown): AIState {
  const s = value as AIState;
  if (!s || !s.defaults || !['draft', 'search', 'weekly_report'].every(p => validProvider(s.defaults[p as AIPurpose]))
    || typeof s.external_consent !== 'boolean' || typeof s.claude_key_set !== 'boolean'
    || typeof s.local_configured !== 'boolean' || typeof s.claude_model !== 'string') throw new Error('AI 설정 응답 오류');
  // 알 수 없는 필드(비밀키 포함)를 renderer로 전달하지 않는다.
  return { mode: s.mode, defaults: { draft: s.defaults.draft, search: s.defaults.search, weekly_report: s.defaults.weekly_report },
    external_consent: s.external_consent, claude_key_set: s.claude_key_set, local_configured: s.local_configured, claude_model: s.claude_model };
}
