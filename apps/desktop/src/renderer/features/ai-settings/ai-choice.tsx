import { useEffect, useState } from 'react';
import type { AIChoice, AIPurpose, AIState } from '../../../shared/ai-bridge';

export function AIChoiceControl({ purpose, value, onChange, disabled = false }: { purpose: AIPurpose; value: AIChoice; onChange(value: AIChoice): void; disabled?: boolean }) {
  const [state, setState] = useState<AIState | null>(null);
  useEffect(() => { let active = true; void window.klover?.ai?.get().then(r => { if (active && r.ok) setState(r.data); }).catch(() => undefined); return () => { active = false; }; }, []);
  const current = state?.mode === 'local_only' ? 'ollama' : value === 'default' ? state?.defaults[purpose] : value;
  return <div className="flex flex-col gap-1 text-caption">
    <label>이번 요청의 AI <select aria-label="이번 요청의 AI" disabled={disabled} value={value} onChange={e => onChange(e.target.value as AIChoice)} className="rounded-md border border-input bg-background px-2 py-1 text-foreground">
      <option value="default">기본 설정{state ? ` (${state.mode !== 'local_only' && state.defaults[purpose] === 'claude' ? 'Claude' : '로컬'})` : ''}</option>
      <option value="ollama">로컬 AI</option><option value="claude" disabled={state?.mode === "local_only"}>Claude API</option>
    </select></label>
    {current === 'claude' && <span className="text-muted-foreground">필요한 메일·프로필이 Anthropic으로 전송되며 API 요금이 발생합니다.{!state?.external_consent && ' AI 설정에서 사용을 허용하세요.'}</span>}
    <a href="#/settings/ai" className="text-ai-text underline">AI 설정</a>
  </div>;
}
