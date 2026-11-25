import { useEffect, useState } from 'react';
import { CheckCircle2, Loader2, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { AIProvider, AIState, AIPurpose, ClaudeModel } from '../../../shared/ai-bridge';

type Outcome = { status: 'running' | 'ok' | 'fail'; title: string; detail?: string; at?: string };
const clock = () => new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false });

/** 저장·연결 검사 결과를 누른 버튼 바로 아래에 색과 아이콘으로 보여 준다. */
function OutcomeBox({ outcome }: { outcome: Outcome | undefined }) {
  if (!outcome) return null;
  const tone = outcome.status === 'ok' ? 'border-success bg-success-subtle text-success'
    : outcome.status === 'fail' ? 'border-danger-border bg-danger-subtle text-danger' : 'border-input bg-muted text-foreground';
  const Icon = outcome.status === 'ok' ? CheckCircle2 : outcome.status === 'fail' ? XCircle : Loader2;
  return <div role={outcome.status === 'fail' ? 'alert' : 'status'} className={cn('flex items-start gap-2 rounded-leaf-sm border px-3 py-2', tone)}>
    <Icon className={cn('mt-0.5 size-4 shrink-0', outcome.status === 'running' && 'animate-spin')} aria-hidden="true" />
    <div className="min-w-0"><p className="font-semibold">{outcome.title}{outcome.at && <span className="ml-2 text-caption font-normal opacity-80">{outcome.at} 확인</span>}</p>
      {outcome.detail && <p className="mt-0.5 text-caption text-foreground">{outcome.detail}</p>}</div>
  </div>;
}

const labels: Record<AIPurpose, string> = { draft: '답장 초안·수정', search: '자연어 검색·답변', weekly_report: '주간 보고서' };
/** 섹션 제목 옆의 한눈에 보는 연결 상태. 이번 화면에서 검사한 결과만 표시한다. */
function ConnectionBadge({ outcome, keySet }: { outcome: Outcome | undefined; keySet?: boolean }) {
  const tone = outcome?.status === 'ok' ? 'bg-success-subtle text-success' : outcome?.status === 'fail' ? 'bg-danger-subtle text-danger' : 'bg-muted text-muted-foreground';
  const text = outcome?.status === 'ok' ? `연결됨${outcome.at ? ` · ${outcome.at}` : ''}` : outcome?.status === 'fail' ? '연결 실패' : outcome?.status === 'running' ? '검사 중…'
    : keySet === false ? '키 미등록' : '아직 검사하지 않음';
  return <span className={cn('inline-flex h-6 items-center rounded-leaf-sm px-2 text-caption font-medium', tone)}>{text}</span>;
}

export function AISettingsPage() {
  const [state, setState] = useState<AIState | null>(null);
  const [model, setModel] = useState('');
  const [key, setKey] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  // 저장한 값(기준). 화면에서 바꾼 값과 달라지면 '저장 안 한 변경'으로 보고, 검사 전에 먼저 저장한다.
  const [saved, setSaved] = useState<{ consent: boolean; model: string } | null>(null);
  const [outcomes, setOutcomes] = useState<Partial<Record<'save' | 'models' | AIProvider, Outcome>>>({});
  const setOutcome = (name: 'save' | 'models' | AIProvider, outcome: Outcome | undefined) => setOutcomes(previous => ({ ...previous, [name]: outcome }));
  // 이 키로 쓸 수 있는 모델 목록(불러온 뒤에만 보인다).
  const [models, setModels] = useState<ClaudeModel[]>([]);
  useEffect(() => { let live = true; void window.klover?.ai?.get().then(r => { if (!live) return; if (r.ok) { setState(r.data); setModel(r.data.claude_model); setSaved({ consent: r.data.external_consent, model: r.data.claude_model }); } else setMessage(r.error.message); }).catch(() => { if (live) setMessage('서버 연결을 확인하세요.'); }); return () => { live = false; }; }, []);
  /** 저장하고 성공 여부를 돌려준다. */
  async function save(): Promise<boolean> {
    if (!state || !window.klover?.ai) return false;
    setBusy(true); setOutcome('save', { status: 'running', title: '저장하는 중…' });
    const typedKey = Boolean(key.trim());
    try {
      const r = await window.klover.ai.save({ mode: state.mode ?? "hybrid", defaults: state.defaults, external_consent: state.external_consent, ...(key.trim() ? { api_key: key.trim() } : {}), ...(model.trim() !== state.claude_model ? { claude_model: model.trim() } : {}) });
      setKey('');
      if (r.ok) {
        setState(r.data); setSaved({ consent: r.data.external_consent, model: r.data.claude_model });
        setOutcomes({ save: { status: 'ok', title: 'AI 설정을 저장했습니다. 키는 서버에 암호화해 보관합니다.', detail: typedKey ? "저장됐는지는 'Claude 연결 검사'로 확인해 보세요." : undefined, at: clock() } });
        return true;
      }
      setOutcome('save', { status: 'fail', title: '저장하지 못했어요.', detail: r.error.message });
    } catch { setKey(''); setOutcome('save', { status: 'fail', title: '저장하지 못했어요.', detail: '앱과 서버 연결을 확인하세요.' }); }
    finally { setBusy(false); }
    return false;
  }
  /** 저장한 키로 쓸 수 있는 모델을 불러와 고르게 한다. 모델 이름을 모를 때 쓴다. */
  async function loadModels() {
    if (!window.klover?.ai) return;
    if (claudeDirty && !(await save())) return;
    setBusy(true); setOutcome('models', { status: 'running', title: '쓸 수 있는 모델을 불러오는 중…' });
    try {
      const r = await window.klover.ai.models();
      if (r.ok) {
        setModels(r.data.models);
        const current = model.trim();
        const usable = r.data.models.some(item => item.id === current);
        setOutcome('models', r.data.models.length === 0
          ? { status: 'fail', title: '쓸 수 있는 모델이 없어요', detail: '이 키로 조회되는 모델이 없습니다. 키 발급자에게 모델 사용 권한을 확인해 달라고 하세요.', at: clock() }
          : { status: 'ok', title: `이 키로 쓸 수 있는 모델 ${r.data.models.length}개를 불러왔어요`, at: clock(),
              detail: usable ? `지금 모델(${current})은 사용할 수 있어요.` : `지금 모델(${current})은 목록에 없어요. 아래에서 다른 모델을 고르세요.` });
      } else setOutcome('models', { status: 'fail', title: '모델 목록을 불러오지 못했어요', detail: r.error.message, at: clock() });
    } catch { setOutcome('models', { status: 'fail', title: '모델 목록을 불러오지 못했어요', detail: '앱과 서버 연결을 확인하세요.', at: clock() }); }
    finally { setBusy(false); }
  }
  async function check(provider: AIProvider) {
    if (!window.klover?.ai) return;
    const name = provider === 'claude' ? 'Claude' : '로컬 AI';
    // 키·모델·허용 여부를 바꾸고 저장하지 않았다면, 검사는 저장된 값으로 하므로 먼저 저장한다.
    if (provider === 'claude' && claudeDirty && !(await save())) return;
    setBusy(true); setOutcome(provider, { status: 'running', title: `${name} 연결 검사 중…`, detail: provider === 'ollama' ? '로컬 모델은 처음 실행할 때 시간이 걸릴 수 있어요.' : undefined });
    try {
      const r = await window.klover.ai.check(provider);
      setOutcome(provider, r.ok
        ? { status: 'ok', title: `${name} 연결 확인 완료`, detail: provider === 'claude' ? `키와 모델(${state?.claude_model ?? ''})로 응답을 받았어요.` : '로컬 모델이 응답했어요.', at: clock() }
        : { status: 'fail', title: `${name} 연결에 실패했어요`, detail: r.error.message, at: clock() });
    } catch { setOutcome(provider, { status: 'fail', title: `${name} 연결을 확인하지 못했어요`, detail: '앱과 서버 연결을 확인하세요.', at: clock() }); }
    finally { setBusy(false); }
  }
  const claudeDirty = Boolean(state && saved && (key.trim() !== '' || model.trim() !== saved.model || state.external_consent !== saved.consent));
  return <main className="mx-auto max-w-3xl space-y-5 p-8 text-body text-foreground">
    <h1 className="text-heading font-bold">AI 설정</h1>
    <p>자동 분류·태그·요약·임베딩·할 일 제안은 로컬 AI로 처리합니다. 아래 기능만 제공자를 선택합니다.</p>
    {!state ? <p role="status">{message || '설정을 불러오는 중…'}</p> : <>
      <label className="flex gap-2"><input type="checkbox" checked={state.mode === 'local_only'} disabled={busy} onChange={e => setState({ ...state, mode: e.target.checked ? 'local_only' : 'hybrid' })} />AI 로컬 전용 모드 (저장 후 적용)</label><p className="text-caption text-muted-foreground">로컬 전용 모드는 저장된 Claude 선택과 관계없이 로컬로 처리하며, 기존 키와 선택 설정은 보존합니다.</p>
      <fieldset disabled={busy || state.mode === 'local_only'} className="space-y-3">{(Object.keys(labels) as AIPurpose[]).map(p => <label key={p} className="flex items-center justify-between gap-4">{labels[p]}<select aria-label={labels[p]} className="rounded-md border border-input bg-background p-2" value={state.defaults[p]} onChange={e => setState({ ...state, defaults: { ...state.defaults, [p]: e.target.value as AIProvider } })}><option value="ollama">로컬 AI (Ollama)</option><option value="claude">Claude API</option></select></label>)}</fieldset>
      <section className="space-y-3 rounded-leaf bg-background p-4 shadow-card"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold">Claude 연결</h2><ConnectionBadge outcome={outcomes.claude} keySet={state.claude_key_set} /></div>
        <p>키: {state.claude_key_set ? '등록됨 (값은 표시하지 않음)' : '미등록'} · 모델: {state.claude_model}</p>
        <label className="block">Claude 모델 ID<input aria-label="Claude 모델 ID" value={model} onChange={e => setModel(e.target.value)} disabled={busy} maxLength={200} className="mt-1 block w-full rounded-md border border-input bg-background p-2" /></label>
        <p className="text-caption text-muted-foreground">Anthropic Console에서 계정에 제공되는 모델 ID를 입력하세요. 바꾸면 세 생성 기능에 공통 적용합니다. 모델 이름을 모르면 키를 저장한 뒤 아래 버튼으로 내 키로 쓸 수 있는 모델을 불러와 고르세요.</p>
        <div className="flex flex-wrap items-center gap-3"><Button variant="secondary" disabled={busy || state.mode === "local_only"} onClick={() => void loadModels()}>{claudeDirty ? '저장하고 ' : ''}쓸 수 있는 모델 불러오기</Button>
          {models.length > 0 && <select aria-label="쓸 수 있는 Claude 모델" className="max-w-full rounded-md border border-input bg-background p-2" disabled={busy}
            value={models.some(item => item.id === model.trim()) ? model.trim() : ''} onChange={e => setModel(e.target.value)}>
            <option value="" disabled>모델 고르기</option>{models.map(item => <option key={item.id} value={item.id}>{item.name} ({item.id})</option>)}</select>}</div>
        <OutcomeBox outcome={outcomes.models} />
        <label className="block">Claude API 키 등록·교체<input aria-label="Claude API 키 등록·교체" autoComplete="off" spellCheck={false} type="password" maxLength={512} value={key} onChange={e => setKey(e.target.value)} disabled={busy} className="mt-1 block w-full rounded-md border border-input bg-background p-2" /></label>
        <p className="text-caption text-muted-foreground">빈칸으로 저장하면 기존 키를 유지합니다. 키를 채팅에 붙여넣지 마세요.</p>
        <p>Claude를 쓰면 답장은 선택 메일·프로필, 검색은 질문과 필요한 검색 결과, 보고서는 대상 업무 메일·분석·프로필이 Anthropic으로 전송됩니다. Claude 구독과 별도의 API 사용료가 발생합니다.</p>
        <label className="flex gap-2"><input type="checkbox" checked={state.external_consent} disabled={busy} onChange={e => setState({ ...state, external_consent: e.target.checked })} />외부 전송과 비용 안내를 확인했으며 Claude 사용을 허용합니다.</label>
        <p className="text-caption text-muted-foreground">Claude 요청 실패 시 로컬로 한 번 재시도합니다. 실제 처리 AI를 결과에 표시합니다. 연결 검사도 소량의 API 요금이 발생하며 메일은 보내지 않습니다.</p>
        <div className="flex flex-wrap items-center gap-3"><Button variant="secondary" disabled={busy || state.mode === "local_only"} onClick={() => void check('claude')}>{claudeDirty ? '저장하고 Claude 연결 검사' : 'Claude 연결 검사'}</Button>
          {claudeDirty && <span className="text-caption text-muted-foreground">저장하지 않은 변경이 있어 먼저 저장한 뒤 검사합니다.</span>}</div>
        <OutcomeBox outcome={outcomes.claude} />
      </section>
      <section className="space-y-3 rounded-leaf bg-background p-4 shadow-card"><div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold">로컬 AI (Ollama)</h2><ConnectionBadge outcome={outcomes.ollama} /></div>
        <p>로컬 모델 설정: {state.local_configured ? '있음' : '서버 .env의 OLLAMA_MODEL 확인 필요'}</p>
        <div><Button variant="secondary" disabled={busy} onClick={() => void check('ollama')}>로컬 연결 검사</Button></div>
        <OutcomeBox outcome={outcomes.ollama} />
      </section>
      <div className="flex flex-wrap items-center gap-3"><Button disabled={busy} onClick={() => void save()}>설정 저장</Button><span className="text-caption text-muted-foreground">기능별 기본값·로컬 전용·키·허용 여부를 저장합니다.</span></div>
      <OutcomeBox outcome={outcomes.save} />
      {message && <p role="status">{message}</p>}
    </>}
  </main>;
}
