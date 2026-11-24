import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowDown, ArrowUp, GripVertical, User, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Area, Field, Panel, Segmented, Skeleton } from './controls';
import { EMPTY_STYLE, SECTION_LABELS, problemText, type F2Client, type Preview, type Profile, type ProfileState, type Section } from './contracts';

export interface ProfilePageProps {
  client: F2Client;
  onExit(): void;
  onNavigate?(target: 'weekly-report' | 'accounts' | 'calendar' | 'notifications' | 'privacy'): void;
  confirm?(message: string): boolean | Promise<boolean>;
}

export function ProfilePage({ client, onExit, onNavigate, confirm = window.confirm.bind(window) }: ProfilePageProps) {
  const [saved, setSaved] = useState<ProfileState | null>(null);
  const [draft, setDraft] = useState<Profile | null>(null);
  const [style, setStyle] = useState(EMPTY_STYLE);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [previewError, setPreviewError] = useState('');
  const [previewBusy, setPreviewBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [consentGiven, setConsentGiven] = useState(false);
  const [contact, setContact] = useState('');
  const [reload, setReload] = useState(0);
  const dragSection = useRef<Section | null>(null);
  const dirty = Boolean(saved && draft && JSON.stringify(saved.profile) !== JSON.stringify(draft));

  useEffect(() => {
    let active = true;
    Promise.all([client.profile(), client.style()]).then(([profile, learned]) => {
      if (active) { setSaved(profile); setDraft(profile.profile); setStyle(learned); setError(''); }
    }).catch(error => { if (active) setError(problemText(error)); });
    return () => { active = false; };
  }, [client, reload]);

  useEffect(() => {
    if (!draft) return;
    let active = true;
    setPreview(null); setPreviewError(''); setPreviewBusy(true);
    const timer = window.setTimeout(() => {
      client.preview({ profile: draft }).then(result => { if (active) setPreview(result); })
        .catch(error => { if (active) setPreviewError(problemText(error)); })
        .finally(() => { if (active) setPreviewBusy(false); });
    }, 1000);
    return () => { active = false; window.clearTimeout(timer); };
  }, [client, draft]);

  useEffect(() => {
    if (!dirty) return;
    const prevent = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', prevent);
    return () => window.removeEventListener('beforeunload', prevent);
  }, [dirty]);

  function change<K extends keyof Profile>(key: K, value: Profile[K]) {
    setDraft(current => current ? { ...current, [key]: value } : null);
    setNotice('');
  }

  async function leave(target?: Parameters<NonNullable<ProfilePageProps['onNavigate']>>[0]) {
    if (dirty && !await confirm('저장하지 않은 변경이 있어요. 변경을 버리고 나갈까요?')) return;
    if (target) onNavigate?.(target); else onExit();
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    if (!draft || !saved || busy) return;
    setBusy(true); setError('');
    try {
      const state = await client.saveProfile({ profile: draft, expected_version: saved.version, consent_given: consentGiven });
      setSaved(state); setDraft(state.profile); setConsentGiven(false);
      setStyle(await client.style());
      setNotice('저장했어요. 다음 초안부터 반영돼요.');
    } catch (error) { setError(problemText(error)); }
    finally { setBusy(false); }
  }

  async function toggleLearning() {
    if (!draft) return;
    const enabled = !draft.style_learning_enabled;
    const message = enabled
      ? 'Klover에서 보낸 메일만 문체 학습에 사용하는 데 동의하나요? 실제 수집·학습 연결은 준비 중이에요.'
      : "학습 결과를 쓰지 않아요. 기록은 '개인정보·학습 데이터'에서 지울 수 있어요. 끌까요?";
    if (!await confirm(message)) return;
    change('style_learning_enabled', enabled); setConsentGiven(enabled);
  }

  async function deleteLearning() {
    if (!await confirm('현재 사용자의 문체 학습 결과(분석 건수·표현·문장 특징)와 제외 표현을 모두 삭제하고 학습 동의를 끕니다. 되돌릴 수 없어요. 기본 정보·문체·서명·보고 양식, 기존 초안·메일·OAuth 토큰·Claude 키는 유지합니다. 삭제할까요?')) return;
    setBusy(true); setError('');
    try {
      const state = await client.deleteStyle();
      setSaved(state);
      setDraft(current => current ? { ...current, style_learning_enabled: false, excluded_phrases: [] } : state.profile);
      setStyle(EMPTY_STYLE); setConsentGiven(false); setNotice('학습 기록을 삭제하고 학습을 껐어요.');
    } catch (error) { setError(problemText(error)); }
    finally { setBusy(false); }
  }

  function moveSection(from: Section, to: Section) {
    if (!draft || from === to) return;
    const order = draft.report_sections.filter(value => value !== from);
    order.splice(draft.report_sections.indexOf(to), 0, from);
    change('report_sections', order);
  }

  const navigation = [
    ['weekly-report', '주간 보고'], ['accounts', '메일 계정 연결'], ['calendar', '캘린더 연결'],
    ['notifications', '알림·시작 프로그램'], ['privacy', '개인정보·학습 데이터'],
  ] as const;

  return <div className="flex h-full min-h-0 bg-background text-foreground" data-testid="profile-page">
    <nav aria-label="설정" className="flex w-[220px] shrink-0 flex-col gap-1 border-r bg-muted p-3">
      <Button variant="secondary" className="mb-3 justify-start" disabled={busy} onClick={() => void leave()}>‹ 받은편지함</Button>
      <span className="px-2 py-2 text-caption text-muted-foreground">설정</span>
      <div aria-current="page" className="flex h-9 items-center gap-2 rounded-md bg-selected px-3 text-body font-semibold text-selected-foreground"><User className="size-4" />내 프로필·문체</div>
      {navigation.map(([target, label]) => <button type="button" key={target} disabled={!onNavigate || busy} onClick={() => void leave(target)} className="h-9 rounded-md px-3 text-left text-body text-muted-foreground hover:bg-accent disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-ring">{label}</button>)}
    </nav>
    {!draft || !saved ? <div className="flex-1 p-6">{error ? <><p role="alert">{error}</p><Button variant="secondary" onClick={() => setReload(n => n + 1)}>다시 불러오기</Button></> : <Skeleton label="프로필을 불러오고 있어요" />}</div>
      : <form onSubmit={event => void save(event)} className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div data-testid="profile-scroll" className="min-h-0 flex-1 overflow-y-auto">
        <fieldset disabled={busy} className="grid min-w-0 grid-cols-2 content-start gap-3 px-6 py-4">
          <Panel title="기본 정보">
            <div className="grid grid-cols-2 gap-3"><Field label="이름" required maxLength={100} value={draft.name} onChange={e => change('name', e.target.value)} /><Field label="직급" maxLength={200} value={draft.title} onChange={e => change('title', e.target.value)} /></div>
            <Field label="소속" maxLength={200} value={draft.org} onChange={e => change('org', e.target.value)} />
            <Field label="담당 업무" maxLength={2000} value={draft.duties} onChange={e => change('duties', e.target.value)} />
            <div className="flex flex-wrap items-center gap-1.5"><span className="w-full text-caption">자주 연락하는 부서·회사</span>
              {draft.frequent_contacts.map(value => <button type="button" key={value} aria-label={`${value} 연락처 삭제`} onClick={() => change('frequent_contacts', draft.frequent_contacts.filter(v => v !== value))} className="flex items-center gap-1 rounded-full bg-muted px-2 py-1 text-caption">{value}<X className="size-3" /></button>)}
              <input aria-label="새 연락처" maxLength={200} className="h-7 w-28 rounded-md border border-input px-2 text-caption focus-visible:ring-2 focus-visible:ring-ring" value={contact} onChange={e => setContact(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') e.preventDefault(); }} />
              <button type="button" className="rounded-full border border-dashed px-2 py-1 text-caption" disabled={!contact.trim() || draft.frequent_contacts.length >= 30} onClick={() => { const value = contact.trim(); if (value && !draft.frequent_contacts.includes(value)) change('frequent_contacts', [...draft.frequent_contacts, value]); setContact(''); }}>+ 추가</button>
            </div>
          </Panel>
          <Panel title="문체">
            <label className="flex flex-col gap-1 text-caption">격식 수준
              <input aria-label="격식 수준" type="range" min={0} max={100} value={draft.formality} onChange={e => change('formality', Number(e.target.value))} className="h-5 w-full accent-primary focus-visible:ring-2 focus-visible:ring-ring" />
              <span className="flex justify-between text-muted-foreground"><span>편하게</span><span>정중하게 · {draft.formality}</span></span>
            </label>
            <Segmented label="답장 길이" value={draft.reply_length} options={[{ value: 'short', label: '짧게' }, { value: 'normal', label: '보통' }, { value: 'long', label: '자세히' }]} onChange={v => change('reply_length', v)} />
            <div className="grid grid-cols-2 gap-3"><Field label="첫 인사" maxLength={1000} value={draft.greeting} onChange={e => change('greeting', e.target.value)} /><Field label="마무리" maxLength={1000} value={draft.closing} onChange={e => change('closing', e.target.value)} /></div>
            <Area label="서명" maxLength={2000} rows={2} value={draft.signature} onChange={e => change('signature', e.target.value)} />
          </Panel>
          <Panel title="◆ 보낸 메일에서 내 문체 학습" className="col-span-2 border-ai-border">
            <div className="flex items-center gap-3 text-caption">
              <span className="flex-1 text-muted-foreground">{`보낸 메일 수집·학습 연결 준비 중 · 기존 분석 기록 ${style.analyzed_count}건`}</span>
              <button type="button" role="switch" aria-checked={draft.style_learning_enabled} aria-label="문체 학습 동의" onClick={() => void toggleLearning()} className="rounded-full border border-input px-3 py-1 text-body focus-visible:ring-2 focus-visible:ring-ring">{draft.style_learning_enabled ? '동의 켬' : '동의 끔'}</button>
              <button type="button" className="text-danger underline" onClick={() => void deleteLearning()}>학습 기록 삭제</button>
            </div>
            <div className="flex flex-wrap gap-2 text-caption">
              {style.phrases.length || draft.excluded_phrases.length ? [...new Set([...style.phrases, ...draft.excluded_phrases])].map(phrase => {
                const excluded = draft.excluded_phrases.includes(phrase);
                return <button type="button" key={phrase} className="rounded-full border border-ai-border px-3 py-1 text-ai-text" onClick={() => change('excluded_phrases', excluded ? draft.excluded_phrases.filter(p => p !== phrase) : [...draft.excluded_phrases, phrase])}>{phrase} {excluded ? '제외됨 · 되돌리기' : '×'}</button>;
              }) : <span className="text-muted-foreground">저장된 학습 표현이 없어요. 실제 수집·학습은 준비 중이에요.</span>}
            </div>
            <p className="text-caption text-muted-foreground">직접 입력한 문체 설정을 사용합니다. 동의를 켜도 새 보낸 메일 수집·학습은 실행되지 않아요.</p>
            {style.traits.length > 0 && <p className="text-caption">문장 특징: {style.traits.join(', ')}</p>}
          </Panel>
          <Panel title="주간 보고 양식">
            <ol className="grid grid-cols-2 gap-2">
              {draft.report_sections.map((section, index) => <li key={section} draggable onDragStart={() => { dragSection.current = section; }} onDragOver={e => e.preventDefault()} onDrop={e => { e.preventDefault(); if (dragSection.current) moveSection(dragSection.current, section); dragSection.current = null; }} className="flex min-h-8 items-center gap-1 rounded-md border px-2 text-caption">
                <GripVertical aria-hidden="true" className="size-3 shrink-0 text-muted-foreground" /><span className="flex-1">{index + 1}. {SECTION_LABELS[section]}</span>
                <button type="button" disabled={index === 0} aria-label={`${SECTION_LABELS[section]} 위로`} className="disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-ring" onClick={() => moveSection(section, draft.report_sections[index - 1])}><ArrowUp className="size-3" /></button>
                <button type="button" disabled={index === 3} aria-label={`${SECTION_LABELS[section]} 아래로`} className="disabled:opacity-40 focus-visible:ring-2 focus-visible:ring-ring" onClick={() => moveSection(section, draft.report_sections[index + 1])}><ArrowDown className="size-3" /></button>
              </li>)}
            </ol>
            <div className="grid grid-cols-2 gap-3"><Field label="보고 대상" maxLength={200} value={draft.report_recipient} onChange={e => change('report_recipient', e.target.value)} /><Segmented label="표현" value={draft.report_style} options={[{ value: 'bullet', label: '개조식' }, { value: 'prose', label: '서술형' }]} onChange={v => change('report_style', v)} /></div>
          </Panel>
          <Panel title="미리보기">
            <div aria-live="polite" className="min-h-28 flex-1 whitespace-pre-wrap rounded-md border bg-muted p-3 text-body">
              {previewBusy ? <Skeleton label="◆ 예시 답장을 만들고 있어요" /> : previewError ? <p>{previewError}</p> : preview?.body}
            </div>
          </Panel>
        </fieldset>
        </div>
        <footer className="flex shrink-0 items-center gap-3 border-t px-6 py-3">
          <div className="min-w-0 flex-1 text-caption">{error && <p role="alert" className="text-danger">{error}</p>}<p role="status">{notice}</p></div>
          <Button variant="secondary" disabled={!dirty || busy} onClick={() => { setDraft(saved.profile); setConsentGiven(false); setError(''); setNotice('저장 전 변경을 취소했어요.'); }}>취소</Button>
          <Button type="submit" disabled={!dirty || busy} className="min-w-22">{busy ? '저장 중…' : '저장'}</Button>
        </footer>
      </form>}
  </div>;
}
