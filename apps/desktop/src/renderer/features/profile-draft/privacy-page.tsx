import { useEffect, useState } from 'react';
import { Button } from '../../components/ui/button';
import { Panel } from './controls';
import { problemText, SECTION_LABELS, type F2Client, type ProfileState, type StyleState } from './contracts';

type Snapshot = { saved: ProfileState; style: StyleState };
export function PrivacyPage({ client, onBack }: { client: F2Client; onBack(): void }) {
  const [data, setData] = useState<Snapshot>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [confirm, setConfirm] = useState<'delete' | 'enable' | 'disable'>();
  const [reload, setReload] = useState(0);
  const [stale, setStale] = useState(false);
  useEffect(() => {
    let active = true;
    setBusy(true);
    void Promise.all([client.profile(), client.style()]).then(([saved, style]) => {
      if (active) { setData({ saved, style }); setStale(false); setError(''); }
    }).catch(() => { if (active) { setError('저장 상태를 확인하지 못했어요. 다시 불러와 주세요.'); setStale(true); } })
      .finally(() => { if (active) setBusy(false); });
    return () => { active = false; };
  }, [client, reload]);
  async function execute() {
    if (!data || !confirm || busy) return;
    const action = confirm;
    setConfirm(undefined); setBusy(true); setError(''); setNotice('');
    try {
      const saved = action === 'delete' ? await client.deleteStyle() : await client.saveProfile({
        profile: { ...data.saved.profile, style_learning_enabled: action === 'enable' },
        expected_version: data.saved.version, consent_given: action === 'enable',
      });
      setData({ ...data, saved }); setStale(true);
      const [verified, style] = await Promise.all([client.profile(), client.style()]);
      setData({ saved: verified, style }); setStale(false);
      setNotice(action === 'delete' ? '학습 기록·제외 표현을 삭제하고 동의를 껐어요.' : '학습 동의 설정을 저장했어요.');
    } catch (reason) { setError(`${problemText(reason)} 현재 서버 상태를 다시 불러와 확인해 주세요.`); setStale(true); }
    finally { setBusy(false); }
  }
  const p = data?.saved.profile;
  return <div className="flex h-full min-h-0 bg-background text-foreground">
    <nav aria-label="설정" className="w-[220px] shrink-0 border-r bg-muted p-3">
      <Button variant="secondary" disabled={busy} onClick={onBack}>‹ 내 프로필·문체</Button>
      <p aria-current="page" className="mt-3 rounded-md bg-selected p-3 text-body text-selected-foreground">개인정보·학습 데이터</p>
    </nav>
    <main className="min-w-0 flex-1 space-y-3 overflow-y-auto p-6">
      <h1 className="text-title font-semibold">개인정보·학습 데이터</h1>
      <p role="status">{busy ? '서버 상태 확인 중…' : notice}</p>
      {error && <p role="alert" className="text-danger">{error}</p>}
      <Button variant="secondary" disabled={busy} onClick={() => setReload(n => n + 1)}>다시 불러오기</Button>
      {p && data && <>
        <Panel title="저장된 프로필과 사용 범위">
          <p>{data.saved.exists ? '서버에 저장된 프로필입니다. 이후 초안과 주간 보고에 사용합니다.' : '저장된 프로필이 없어요. 내 프로필·문체에서 먼저 저장해 주세요.'}</p>
          <dl className="space-y-2 whitespace-pre-wrap break-words text-body">
            {Object.entries({ 이름: p.name, 직급: p.title, 소속: p.org, '담당 업무': p.duties, '자주 연락하는 곳': p.frequent_contacts.join(', '), '격식 수준': String(p.formality), '답장 길이': ({ short: '짧게', normal: '보통', long: '자세히' })[p.reply_length], '첫 인사': p.greeting, 마무리: p.closing, 서명: p.signature, '보고 순서': p.report_sections.map(s => SECTION_LABELS[s]).join(' → '), '보고 대상': p.report_recipient, '보고 표현': p.report_style === 'bullet' ? '개조식' : '서술형' }).map(([key, value]) => <div key={key}><dt className="text-muted-foreground">{key}</dt><dd>{value || '없음'}</dd></div>)}
          </dl>
        </Panel>
        <Panel title="문체 학습 동의와 실제 작동 상태">
          <p>저장된 학습 동의: {p.style_learning_enabled ? '켬' : '끔'}</p>
          <p>실제 보낸 메일 수집·문체 학습: 준비 중. 동의를 켜도 수집·학습 작업은 실행되지 않아요.</p>
          <p>기존 저장 기록: 분석 메일 {data.style.analyzed_count}건. 이 숫자는 현재 학습이 실행 중이라는 뜻이 아니에요.</p>
          <p>{p.style_learning_enabled ? '기존 학습 결과가 있으면 초안에 반영될 수 있어요.' : '동의를 끄면 기존 학습 결과를 초안에 사용하지 않아요. 기록은 삭제 전까지 보관돼요.'}</p>
          <Button variant="secondary" disabled={busy || stale || !data.saved.exists} onClick={() => setConfirm(p.style_learning_enabled ? 'disable' : 'enable')}>{p.style_learning_enabled ? '학습 동의 끄기' : '학습 동의 켜기'}</Button>
        </Panel>
        <Panel title="기존 학습 기록·제외 표현">
          <p>사용 가능한 표현: {data.style.phrases.join(' · ') || '없음'}</p>
          <p>문장 특징: {data.style.traits.join(' · ') || '없음'}</p>
          <p>제외 표현: {p.excluded_phrases.join(' · ') || '없음'}</p>
          <Button variant="secondary" disabled={busy || stale} onClick={() => setConfirm('delete')}>학습 기록·제외 표현 삭제</Button>
        </Panel>
        <p className="text-caption text-muted-foreground">키 관리와 외부 전송 동의는 기존 AI 설정에서 관리해 주세요.</p>
      </>}
      {confirm && <section role="alertdialog" aria-labelledby="privacy-confirm" className="rounded-md border bg-card p-4">
        <h2 id="privacy-confirm" className="text-title">{confirm === 'delete' ? '학습 기록과 제외 표현을 삭제할까요?' : '학습 동의를 변경할까요?'}</h2>
        <p>{confirm === 'delete' ? '현재 사용자의 저장된 문체 학습 결과(분석 건수·표현·문장 특징)와 모든 제외 표현을 삭제하고 학습 동의를 끕니다. 되돌릴 수 없어요. 프로필의 기본 정보·문체·서명·보고 양식, 기존 초안, 메일, OAuth 토큰, Claude 키는 유지합니다.' : confirm === 'enable' ? '향후 Klover에서 보낸 메일의 문체 학습에 동의합니다. 현재 수집·학습은 준비 중이며 켜도 새 학습이 시작되지 않아요.' : '기존 학습 결과를 초안에 사용하지 않아요. 저장된 학습 기록과 제외 표현은 보관합니다.'}</p>
        <Button variant="secondary" onClick={() => setConfirm(undefined)}>취소</Button>
        <Button onClick={() => void execute()}>{confirm === 'delete' ? '확인하고 삭제' : '확인하고 저장'}</Button>
      </section>}
    </main>
  </div>;
}
