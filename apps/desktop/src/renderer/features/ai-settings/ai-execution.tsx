export function AIExecutionNotice({ value }: { value: unknown }) {
  const trace = value as { calls?: { used: string }[]; fallback?: boolean; reason?: string } | undefined;
  if (!Array.isArray(trace?.calls) || !trace.calls.length) return null;
  const providers = [...new Set(trace.calls.map(call => call?.used))]
    .filter(used => used === 'claude' || used === 'ollama')
    .map(used => used === 'claude' ? 'Claude' : '로컬 AI');
  if (!providers.length) return null;
  const reasons: Record<string, string> = {
    claude_not_configured: '키·모델 설정 필요',
    claude_timeout: '응답 시간 초과',
    claude_unreachable: '연결 실패',
    claude_auth_failed: '키·권한 확인 필요',
    claude_rate_limited: '사용 한도 초과',
    claude_model_not_found: '모델 확인 필요',
    claude_bad_request: '요청 설정 확인 필요',
    claude_error: '서비스 오류',
    claude_truncated: '응답 길이 제한',
  };
  return <p role="status" className="px-6 py-2 text-caption text-ai-text">
    실제 처리 AI: {providers.join(' → ')}
    {trace.fallback ? ` · Claude 처리 실패 후 로컬로 재시도 (${reasons[trace.reason ?? ''] ?? 'Claude 요청 실패'})` : ''}
  </p>;
}
