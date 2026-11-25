import { useEffect, useState } from 'react';
import type { AIChoice, AIPurpose, AIState } from '../../../shared/ai-bridge';

export function AIChoiceControl({ purpose, value, onChange, disabled = false }: { purpose: AIPurpose; value: AIChoice; onChange(value: AIChoice): void; disabled?: boolean }) {
  const [state, setState] = useState<AIState | null>(null);
  useEffect(() => { let active = true; void window.klover?.ai?.get().then(r => { if (active && r.ok) setState(r.data); }).catch(() => undefined); return () => { active = false; }; }, []);
  const current = state?.mode === 'local_only' ? 'ollama' : value === 'default' ? state?.defaults[purpose] : value;
  // 한 줄 고정: Claude를 골라도 줄이 늘어나지 않도록 안내는 같은 줄의 짧은 표시로 둔다(자세한 문장은 마우스를 올리면 보인다).
  return <div className="flex min-h-8 items-center gap-2 text-caption">
    <label className="inline-flex items-center gap-2 whitespace-nowrap">이번 요청의 AI <select aria-label="이번 요청의 AI" disabled={disabled} value={value} onChange={e => onChange(e.target.value as AIChoice)} className="h-8 rounded-leaf-sm border border-input bg-background px-2 text-foreground">
      <option value="default">기본 설정{state ? ` (${state.mode !== 'local_only' && state.defaults[purpose] === 'claude' ? 'Claude' : '로컬'})` : ''}</option>
      <option value="ollama">로컬 AI</option><option value="claude" disabled={state?.mode === "local_only"}>Claude API</option>
    </select></label>
    <a href="#/settings/ai" className="inline-flex h-8 shrink-0 items-center whitespace-nowrap rounded-leaf-sm border border-input bg-background px-3 text-ai-text hover:bg-accent focus-visible:outline-ring">AI 설정</a>
    {current === 'claude' && <>
      <span role="note" title="필요한 메일·프로필이 Anthropic으로 전송되며 API 요금이 발생합니다."
        className="inline-flex h-6 shrink-0 items-center whitespace-nowrap rounded-leaf-sm bg-warning-subtle px-2 font-medium text-warning">Anthropic으로 전송 · 요금 발생</span>
      {!state?.external_consent && <span role="note" title="AI 설정에서 Claude 사용을 허용하세요."
        className="inline-flex h-6 shrink-0 items-center whitespace-nowrap rounded-leaf-sm bg-danger-subtle px-2 font-medium text-danger">AI 설정에서 허용 필요</span>}
    </>}
  </div>;
}
