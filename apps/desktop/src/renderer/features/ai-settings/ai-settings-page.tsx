import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import type { AIProvider, AIState, AIPurpose } from '../../../shared/ai-bridge';

const labels: Record<AIPurpose, string> = { draft: '답장 초안·수정', search: '자연어 검색·답변', weekly_report: '주간 보고서' };
export function AISettingsPage() {
  const [state, setState] = useState<AIState | null>(null);
  const [model, setModel] = useState('');
  const [key, setKey] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  useEffect(() => { let live = true; void window.klover?.ai?.get().then(r => { if (!live) return; if (r.ok) { setState(r.data); setModel(r.data.claude_model); } else setMessage(r.error.message); }).catch(() => { if (live) setMessage('서버 연결을 확인하세요.'); }); return () => { live = false; }; }, []);
  async function save() {
    if (!state || !window.klover?.ai) return;
    setBusy(true); setMessage('');
    try {
      const r = await window.klover.ai.save({ mode: state.mode ?? "hybrid", defaults: state.defaults, external_consent: state.external_consent, ...(key.trim() ? { api_key: key.trim() } : {}), ...(model.trim() !== state.claude_model ? { claude_model: model.trim() } : {}) });
      setKey('');
      if (r.ok) { setState(r.data); setMessage('AI 설정을 저장했습니다. 키는 서버에 암호화해 보관합니다.'); }
      else setMessage(r.error.message);
    } catch { setKey(''); setMessage('설정을 저장하지 못했어요.'); }
    finally { setBusy(false); }
  }
  async function check(provider: AIProvider) {
    if (!window.klover?.ai) return;
    setBusy(true); setMessage('연결 검사 중… 로컬 모델은 처음 실행할 때 시간이 걸릴 수 있어요.');
    try { const r = await window.klover.ai.check(provider); setMessage(r.ok ? `${provider === 'claude' ? 'Claude' : '로컬 AI'} 연결 확인 완료` : r.error.message); }
    catch { setMessage('연결을 확인하지 못했어요.'); }
    finally { setBusy(false); }
  }
  return <main className="mx-auto max-w-3xl space-y-5 p-8 text-body text-foreground">

    <h1 className="text-heading font-bold">AI 설정</h1>
    <p>자동 분류·태그·요약·임베딩·할 일 제안은 로컬 AI로 처리합니다. 아래 기능만 제공자를 선택합니다.</p>
    {!state ? <p role="status">{message || '설정을 불러오는 중…'}</p> : <>
      <label className="flex gap-2"><input type="checkbox" checked={state.mode === 'local_only'} disabled={busy} onChange={e => setState({ ...state, mode: e.target.checked ? 'local_only' : 'hybrid' })} />AI 로컬 전용 모드 (저장 후 적용)</label><p className="text-caption text-muted-foreground">로컬 전용 모드는 저장된 Claude 선택과 관계없이 로컬로 처리하며, 기존 키와 선택 설정은 보존합니다.</p>
      <fieldset disabled={busy || state.mode === 'local_only'} className="space-y-3">{(Object.keys(labels) as AIPurpose[]).map(p => <label key={p} className="flex items-center justify-between gap-4">{labels[p]}<select aria-label={labels[p]} className="rounded-md border border-input bg-background p-2" value={state.defaults[p]} onChange={e => setState({ ...state, defaults: { ...state.defaults, [p]: e.target.value as AIProvider } })}><option value="ollama">로컬 AI (Ollama)</option><option value="claude">Claude API</option></select></label>)}</fieldset>
      <section className="space-y-3 rounded-lg border p-4"><h2 className="font-semibold">Claude 연결</h2>
        <p>키: {state.claude_key_set ? '등록됨 (값은 표시하지 않음)' : '미등록'} · 모델: {state.claude_model}</p>
        <label className="block">Claude 모델 ID<input aria-label="Claude 모델 ID" value={model} onChange={e => setModel(e.target.value)} disabled={busy} maxLength={200} className="mt-1 block w-full rounded-md border border-input bg-background p-2" /></label>
        <p className="text-caption text-muted-foreground">Anthropic Console에서 계정에 제공되는 모델 ID를 입력하세요. 바꾸면 세 생성 기능에 공통 적용합니다.</p>
        <label className="block">Claude API 키 등록·교체<input aria-label="Claude API 키 등록·교체" autoComplete="off" spellCheck={false} type="password" maxLength={512} value={key} onChange={e => setKey(e.target.value)} disabled={busy} className="mt-1 block w-full rounded-md border border-input bg-background p-2" /></label>
        <p className="text-caption text-muted-foreground">빈칸으로 저장하면 기존 키를 유지합니다. 키를 채팅에 붙여넣지 마세요.</p>
        <p>Claude를 쓰면 답장은 선택 메일·프로필, 검색은 질문과 필요한 검색 결과, 보고서는 대상 업무 메일·분석·프로필이 Anthropic으로 전송됩니다. Claude 구독과 별도의 API 사용료가 발생합니다.</p>
        <label className="flex gap-2"><input type="checkbox" checked={state.external_consent} disabled={busy} onChange={e => setState({ ...state, external_consent: e.target.checked })} />외부 전송과 비용 안내를 확인했으며 Claude 사용을 허용합니다.</label>
        <p className="text-caption text-muted-foreground">Claude 요청 실패 시 로컬로 한 번 재시도합니다. 실제 처리 AI를 결과에 표시합니다. 연결 검사도 소량의 API 요금이 발생하며 메일은 보내지 않습니다.</p>
      </section>
      <div className="flex flex-wrap gap-3"><Button disabled={busy} onClick={() => void save()}>설정 저장</Button><Button variant="secondary" disabled={busy} onClick={() => void check('ollama')}>로컬 연결 검사</Button><Button variant="secondary" disabled={busy || state.mode === "local_only"} onClick={() => void check('claude')}>Claude 연결 검사</Button></div>
      <p className="text-caption text-muted-foreground">키·허용 여부를 변경했다면 먼저 저장한 뒤 연결을 검사하세요. 로컬 모델 설정: {state.local_configured ? '있음' : '서버 .env의 OLLAMA_MODEL 확인 필요'}</p>
      {message && <p role="status">{message}</p>}
    </>}
  </main>;
}
