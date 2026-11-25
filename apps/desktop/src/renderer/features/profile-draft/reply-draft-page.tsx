import { AIExecutionNotice } from '../ai-settings/ai-execution';
import { AIChoiceControl } from '../ai-settings/ai-choice';
import type { AIChoice } from '../../../shared/ai-bridge';
import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Skeleton } from './controls';
import { EvidenceBody, preserveEvidence } from './evidence';
import { ReferencePreview } from './reference-preview';
import { problemText, type Draft, type DraftAction, type Evidence, type F2Client, type MailDetail, type Profile } from './contracts';

export interface ReplyDraftPageProps {
  client: F2Client;
  autoGenerate?: boolean;
  mailId: string;
  draftId?: string;
  onExit(): void;
  onOpenMail?(mailId: string): void;
  onManualReply?(mailId: string, body: string): void;
  confirm?(message: string): boolean | Promise<boolean>;
}

const PROFILE_LABELS: Record<string, string> = {
  'profile.greeting': '첫 인사', 'profile.closing': '마무리', 'profile.signature': '서명', 'profile.phrase': '학습 표현',
};

export function ReplyDraftPage({ client, mailId, draftId, autoGenerate = true, onExit, onOpenMail, onManualReply, confirm = window.confirm.bind(window) }: ReplyDraftPageProps) {
  const [provider, setProvider] = useState<AIChoice>('default');
  const [original, setOriginal] = useState<MailDetail | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [body, setBody] = useState('');
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [manual, setManual] = useState(false);
  const [reference, setReference] = useState<string | null>(null);
  const edits = useRef(0);
  const mounted = useRef(true);
  const lifecycle = useRef(0);
  const mirror = useRef<HTMLDivElement>(null);
  const bodyRef = useRef('');
  const initialRequest = useRef<{ client: F2Client; mailId: string; draftId?: string; promise: Promise<Draft> } | null>(null);
  const dirty = Boolean(draft && body !== draft.body);

  useEffect(() => {
    mounted.current = true;
    lifecycle.current++;
    let active = true;
    setBusy(true); setError(''); setNotice(''); setOriginal(null); setProfile(null); setEvidence([]); setManual(false); setDraft(null); setBody(''); bodyRef.current = ''; edits.current = 0;
    client.mail(mailId).then(mail => { if (active) setOriginal(mail); }).catch(error => { if (active) setError(problemText(error)); });
    client.profile().then(state => { if (active) setProfile(state.profile); }).catch(() => { /* 초안 API가 프로필 준비 부족을 설명한다. */ });
    if (!draftId && !autoGenerate) {
      setBusy(false);
      return () => { active = false; mounted.current = false; lifecycle.current++; };
    }
    const revision = edits.current;
    // StrictMode의 effect 재실행이 같은 초안을 두 번 생성하지 않게 한다.
    const previous = initialRequest.current;
    if (!previous || previous.client !== client || previous.mailId !== mailId || previous.draftId !== draftId) {
      initialRequest.current = { client, mailId, draftId, promise: draftId ? client.draft(draftId) : client.createDraft({ mail_id: mailId }) };
    }
    const initial = initialRequest.current!.promise;
    initial.then(result => {
      if (!active) return;
      if (result.mail_id !== mailId) throw new Error('초안과 원본 메일이 다릅니다.');
      setDraft(result);
      if (edits.current === revision) { setBody(result.body); bodyRef.current = result.body; setEvidence(result.evidence); }
    }).catch(error => { if (active) setError(problemText(error)); }).finally(() => { if (active) setBusy(false); });
    return () => { active = false; mounted.current = false; lifecycle.current++; };
  }, [client, mailId, draftId, autoGenerate]);

  useEffect(() => {
    if (!dirty && !(!draft && body)) return;
    const prevent = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', prevent);
    return () => window.removeEventListener('beforeunload', prevent);
  }, [dirty, draft, body]);

  function edit(value: string) {
    const previousBody = bodyRef.current;
    setEvidence(current => preserveEvidence(previousBody, value, current));
    bodyRef.current = value; setBody(value); edits.current++; setNotice('');
  }

  function accept(result: Draft, revision: number) {
    setDraft(result);
    if (edits.current === revision) {
      setBody(result.body); bodyRef.current = result.body; setEvidence(result.evidence); setManual(false);
    } else {
      setNotice('생성 중 수정한 내용을 보존했어요. 현재 내용을 임시 저장할 수 있어요.');
    }
  }

  async function generate(action: DraftAction = 'rewrite', direction?: string) {
    if (busy) return;
    if ((dirty || (manual && body)) && !await confirm('고친 내용이 바뀔 수 있어요. 현재 내용을 기준으로 다시 만들까요?')) return;
    const revision = edits.current;
    const epoch = lifecycle.current;
    setBusy(true); setError(''); setNotice('');
    try {
      const result = draft
        ? await client.reviseDraft(draft.draft_id, { action, body: bodyRef.current, expected_version: draft.version, direction, ai_provider: provider })
        : await client.createDraft({ mail_id: mailId, direction, ai_provider: provider });
      if (mounted.current && lifecycle.current === epoch) accept(result, revision);
    } catch (error) { if (mounted.current && lifecycle.current === epoch) setError(problemText(error)); }
    finally { if (mounted.current && lifecycle.current === epoch) setBusy(false); }
  }

  async function save(): Promise<boolean> {
    if (!draft || busy) return false;
    const revision = edits.current;
    const epoch = lifecycle.current;
    setBusy(true); setError('');
    try {
      const result = await client.saveDraft(draft.draft_id, { body: bodyRef.current, expected_version: draft.version });
      if (!mounted.current || lifecycle.current !== epoch) return false;
      accept(result, revision);
      if (edits.current !== revision) return false;
      setNotice('임시 저장했어요. 메일은 발송되지 않았어요.');
      return true;
    } catch (error) { if (mounted.current && lifecycle.current === epoch) setError(problemText(error)); return false; }
    finally { if (mounted.current && lifecycle.current === epoch) setBusy(false); }
  }

  async function leave() {
    if (dirty && !await save()) return;
    if (!draft && body && !await confirm('아직 임시 저장할 수 없어요. 작성 내용을 버리고 나갈까요?')) return;
    onExit();
  }

  const profileSources = [...new Set(evidence.filter(e => e.source.startsWith('profile.')).map(e => PROFILE_LABELS[e.source]))];
  const referenceIds = new Set(evidence.filter(e => e.source.startsWith('mail:')).map(e => e.source.slice(5)));
  const references = draft?.references.filter(reference => referenceIds.has(reference.mail_id)) ?? [];

  return <div className="flex h-full min-h-0 bg-canvas text-foreground" data-testid="reply-draft-page">
    <aside aria-label="원본 메일" className="flex w-[420px] shrink-0 flex-col gap-4 overflow-y-auto bg-canvas p-6">
      <Button variant="secondary" className="self-start" disabled={busy} onClick={() => void leave()}>‹ 받은편지함</Button>
      <h2 className="text-caption text-muted-foreground">원본 메일</h2>
      {original ? <>
        <div><h1 className="text-title font-semibold">{original.subject}</h1><p className="mt-1 text-caption text-muted-foreground">{original.from_name || original.from_addr} · {new Date(original.received_at).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })}</p></div>
        <p className="whitespace-pre-wrap text-body leading-7">{original.body_text}</p>
        <div className="rounded-leaf bg-ai-subtle p-3 text-body"><h3 className="mb-2 font-semibold text-ai-text">요청사항</h3><p className="text-caption text-muted-foreground">요청사항 분석 연결이 준비되지 않았어요. 원본 내용을 확인해 주세요.</p></div>
      </> : <Skeleton label="원본 메일을 불러오고 있어요" />}
    </aside>
    <section aria-label="답장 초안" className="m-2.5 ml-0 flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden rounded-leaf-lg bg-background">
      <div className="flex min-h-11 items-center gap-4 border-b px-6 text-body"><span className="w-16 text-caption text-muted-foreground">받는 사람</span>{original?.from_name || original?.from_addr || '확인 중'}</div>
      <div className="flex min-h-11 items-center gap-4 border-b px-6 text-body"><span className="w-16 text-caption text-muted-foreground">제목</span>{original ? `RE: ${original.subject}` : '확인 중'}</div>
      <div className="flex min-h-16 flex-wrap items-center gap-2 border-b px-6 py-3" aria-label="답장 방향">
        <AIChoiceControl purpose="draft" value={provider} onChange={setProvider} disabled={busy} />
        {!draft && <Button disabled={busy} onClick={() => void generate()}>초안 만들기</Button>}
        <h2 className="mr-1 text-body font-semibold text-ai-text">답장 방향</h2>
        {draft?.directions.map(direction => <button type="button" key={direction} aria-pressed={direction === draft.selected_direction} disabled={busy} onClick={() => void generate('rewrite', direction)} className={`min-h-8 rounded-full border border-ai-border px-3 text-caption focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40 ${direction === draft.selected_direction ? 'bg-ai text-ai-foreground' : 'bg-ai-subtle text-ai-text'}`}>{direction}</button>)}
        {profile && <span className="ml-auto text-caption text-muted-foreground">격식 {profile.formality} · 길이 {{ short: '짧게', normal: '보통', long: '자세히' }[profile.reply_length]}</span>}
      </div>
      <AIExecutionNotice value={draft?.ai_execution} />
      {error && <div role="alert" className="flex flex-wrap items-center gap-3 border-b bg-warning-subtle px-6 py-3 text-caption"><p className="flex-1">{error}</p><Button variant="secondary" disabled={busy} onClick={() => void generate()}>다시 시도</Button><Button variant="secondary" disabled={busy} onClick={() => { setManual(true); onManualReply?.(mailId, bodyRef.current); }}>직접 쓰기</Button></div>}
      <div className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        {busy && !body && !manual ? <div className="p-6"><p className="mb-4 text-body text-ai-text">답장 초안을 만들고 있어요…</p><p className="mb-4 text-caption text-muted-foreground">로컬 AI는 시간이 걸릴 수 있어요. 최대 2분 동안 기다립니다.</p><Skeleton label="초안 생성 중" /></div>
          : <div className="relative min-h-56 flex-1">
            <div ref={mirror} aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden whitespace-pre-wrap break-words px-6 py-5 text-[15px] leading-[26px]"><EvidenceBody body={body} evidence={evidence} />{'\n'}</div>
            <textarea aria-label="답장 본문" maxLength={25000} spellCheck={false} value={body} onChange={e => edit(e.target.value)} onScroll={e => { if (mirror.current) mirror.current.scrollTop = e.currentTarget.scrollTop; }} className="relative h-full min-h-56 w-full resize-none whitespace-pre-wrap break-words bg-transparent px-6 py-5 text-[15px] leading-[26px] text-transparent caret-foreground selection:bg-ai-highlight selection:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring" />
          </div>}
        {(profileSources.length > 0 || references.length > 0) && <div className="mx-6 mb-3 rounded-md border bg-muted px-4 py-3 text-caption">
          <h3 className="mb-1 font-semibold">이 초안에 반영된 것 <span className="font-normal text-muted-foreground">(밑줄 친 부분)</span></h3>
          {profileSources.length > 0 && <p>프로필: {profileSources.join(', ')}</p>}
          {references.length > 0 && <div className="mt-1">참고한 메일: {references.map(reference => <span key={reference.mail_id} className="mr-3"><button type="button" className="text-ai-text underline" onClick={() => { if (onOpenMail) onOpenMail(reference.mail_id); else setReference(reference.mail_id); }}>{reference.subject}</button> ({new Date(reference.received_at).toLocaleDateString('ko-KR', { timeZone: 'Asia/Seoul' })})</span>)}</div>}
        </div>}
      </div>
      <footer className="shrink-0 border-t px-6 py-3">
        <p role="status" className="mb-2 text-caption text-muted-foreground">{notice || (busy && draft ? '고치고 있어요. 현재 본문은 계속 편집할 수 있어요.' : '초안은 자동 발송되지 않아요. 실제 발송 연결은 이번 범위에 포함되지 않아요.')}</p>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" disabled={busy || !draft} onClick={() => void generate('shorter')}>더 짧게</Button>
          <Button variant="secondary" disabled={busy || !draft} onClick={() => void generate('politer')}>더 정중하게</Button>
          <Button variant="secondary" disabled={busy || !draft} onClick={() => void generate('rewrite')}>다시 쓰기</Button>
          <div className="flex-1" />
          <Button variant="secondary" disabled={busy || !draft} onClick={() => void save()}>임시 저장</Button>
          <Button disabled title="발송은 F0 연결 후 사용자 승인으로만 실행할 수 있어요.">보내기</Button>
        </div>
      </footer>
    </section>
    {reference && <ReferencePreview key={reference} client={client} mailId={reference} onClose={() => setReference(null)} />}
  </div>;
}
