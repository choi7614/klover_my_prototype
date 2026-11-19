import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Copy, FileText, Mail, Plus, RefreshCw, Save, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { draftIsValid, reportText, WeeklyReportClientError } from './client';
import type {
  ExcludedMail, ReportItem, ReportMail, ReportPeriod, ReportSection, ReportTemplate,
  WeeklyReportClient, WeeklyReportDocument, WeeklyReportOptions,
} from './types';

const inputClass = 'h-9 rounded-md border border-input bg-background px-3 text-body focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40';
const cloneSections = (sections: ReportSection[]) => sections.map((section) => ({
  ...section, items: section.items.map((item) => ({ ...item, evidence: [...item.evidence] })),
}));
const errorText = (error: unknown) => error instanceof WeeklyReportClientError
  ? error.message : '요청을 처리하지 못했어요. 편집 내용은 보존됩니다.';
const mailDate = (value: string) => new Intl.DateTimeFormat('ko-KR', {
  timeZone: 'Asia/Seoul', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit',
}).format(new Date(value));

function Modal({ title, children, close }: { title: string; children: ReactNode; close: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    element?.showModal();
    return () => element?.close();
  }, []);
  return (
    <dialog ref={dialog} aria-label={title} onCancel={(event) => { event.preventDefault(); close(); }}
      className="m-auto max-h-[85vh] w-[560px] max-w-[94vw] rounded-lg border border-border bg-popover p-0 text-popover-foreground shadow-pop backdrop:bg-foreground/30">
      <div className="flex items-center justify-between border-b px-6 py-4">
        <h2 className="text-title font-semibold">{title}</h2>
        <button type="button" onClick={close} aria-label="닫기" className="rounded p-1 focus-visible:ring-2 focus-visible:ring-ring"><X size={18} /></button>
      </div>
      <div className="max-h-[65vh] overflow-auto p-6">{children}</div>
    </dialog>
  );
}

function MailContents({ mail }: { mail: ReportMail }) {
  return <>
    <h3 className="font-semibold">{mail.subject || '(제목 없음)'}</h3>
    <p className="mt-2 text-caption text-muted-foreground">{mail.from_name || mail.from_addr} → {mail.to.map((contact) => contact.name || contact.addr).join(', ')} · {mailDate(mail.received_at)}</p>
    <pre className="mt-5 whitespace-pre-wrap break-words font-sans text-body leading-7">{mail.body_text}</pre>
  </>;
}

export function WeeklyReportPage({ client, writeClipboard = (text) => navigator.clipboard.writeText(text) }: {
  client: WeeklyReportClient;
  writeClipboard?: (text: string) => Promise<void>;
}) {
  const [options, setOptions] = useState<WeeklyReportOptions | null>(null);
  const [period, setPeriod] = useState<ReportPeriod>({ start: '', end: '' });
  const [template, setTemplate] = useState<ReportTemplate>('profile');
  const [recipient, setRecipient] = useState('');
  const [report, setReport] = useState<WeeklyReportDocument | null>(null);
  const [sections, setSections] = useState<ReportSection[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [confirm, setConfirm] = useState<'open' | 'regenerate' | null>(null);
  const [preview, setPreview] = useState<ReportMail | null>(null);
  const [excluded, setExcluded] = useState<ExcludedMail[] | null>(null);
  const [excludedLoading, setExcludedLoading] = useState(false);
  const mounted = useRef(true);
  const activeClient = useRef(client);
  activeClient.current = client;
  const isCurrentClient = () => mounted.current && activeClient.current === client;
  const dirty = !!report && JSON.stringify(sections) !== JSON.stringify(report.sections);
  const valid = !!report && draftIsValid(report, sections);
  const activeItem = sections.flatMap((section) => section.items).find((item) => item.item_id === selected);

  function display(document: WeeklyReportDocument) {
    setReport(document);
    setSections(cloneSections(document.sections));
    setSelected((previous) => document.sections.some((section) => section.items.some((item) => item.item_id === previous))
      ? previous : document.sections.flatMap((section) => section.items)[0]?.item_id || null);
  }

  useEffect(() => {
    let live = true;
    mounted.current = true;
    setBusy(true);
    setError('');
    setReport(null);
    setSections([]);
    setOptions(null);
    setPreview(null); setExcluded(null); setConfirm(null); setSelected(null);
    setMessage(''); setExcludedLoading(false);
    async function initialize() {
      try {
        const next = await client.options();
        if (!live) return;
        setOptions(next); setPeriod(next.default_period);
        setRecipient(next.profile?.report_recipient || ''); setTemplate('profile');
        if (next.profile && next.remaining_days === 0 && next.profile.report_recipient.trim()) {
          const document = await client.generate({ ...next.default_period, template: 'profile', recipient: next.profile.report_recipient });
          if (live) display(document);
        }
      } catch (error) { if (live) setError(errorText(error)); }
      finally { if (live) setBusy(false); }
    }
    void initialize();
    return () => { live = false; mounted.current = false; };
  }, [client]);

  useEffect(() => {
    if (!dirty) return;
    const preserve = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    window.addEventListener('beforeunload', preserve);
    return () => window.removeEventListener('beforeunload', preserve);
  }, [dirty]);

  async function generate(mode: 'open' | 'regenerate') {
    setConfirm(null); setBusy(true); setError(''); setMessage('');
    try {
      const document = await client.generate({ ...period, template, recipient,
        regenerate: mode === 'regenerate', expected_revision: report?.revision });
      if (isCurrentClient()) { display(document); setMessage(mode === 'regenerate' ? '보고서를 다시 만들었습니다.' : '저장된 보고서 또는 새 결과를 열었습니다.'); }
    } catch (error) { if (isCurrentClient()) setError(errorText(error)); }
    finally { if (isCurrentClient()) setBusy(false); }
  }
  function requestGeneration(mode: 'open' | 'regenerate') {
    if (dirty) setConfirm(mode);
    else void generate(mode);
  }
  function updateItem(id: string, patch: Partial<ReportItem>) {
    setSections((current) => current.map((section) => ({ ...section,
      items: section.items.map((item) => item.item_id === id ? { ...item, ...patch } : item),
    })));
  }
  async function save() {
    if (!report || !valid || busy) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const saved = await client.save(report.report_id, report.revision, sections);
      if (isCurrentClient()) { display(saved); setMessage('편집한 내용을 저장했습니다.'); }
    } catch (error) { if (isCurrentClient()) setError(errorText(error)); }
    finally { if (isCurrentClient()) setBusy(false); }
  }
  async function copy() {
    if (!report || !valid) return;
    try { await writeClipboard(reportText(report, sections)); setMessage('편집한 내용을 복사했습니다.'); }
    catch { setError('복사하지 못했어요. 클립보드 권한을 확인해 주세요. 편집 내용은 보존됩니다.'); }
  }
  async function openExcluded() {
    if (!report) return;
    setExcludedLoading(true); setError('');
    try { const result = await client.excluded(report.report_id); if (isCurrentClient()) setExcluded(result); }
    catch (error) { if (isCurrentClient()) setError(errorText(error)); }
    finally { if (isCurrentClient()) setExcludedLoading(false); }
  }
  const mayGenerate = !busy && !!options?.profile && options.remaining_days === 0
    && !!period.start && !!period.end && period.end >= period.start && !!recipient.trim();

  return <section aria-label="주간 보고" className="flex min-h-[720px] min-w-0 flex-1 flex-col bg-background">
    <div className="flex flex-wrap items-end gap-3 border-b px-6 py-4">
      <div className="mr-2 flex items-center gap-2 pb-2 text-title font-semibold"><FileText className="size-5 text-primary" />주간 보고</div>
      <fieldset className="flex gap-2" disabled={busy}>
        <label className="flex flex-col gap-1 text-caption text-muted-foreground">시작일<input aria-label="시작일" type="date" className={inputClass} value={period.start} onChange={(event) => setPeriod({ ...period, start: event.target.value })} /></label>
        <label className="flex flex-col gap-1 text-caption text-muted-foreground">종료일<input aria-label="종료일" type="date" className={inputClass} value={period.end} onChange={(event) => setPeriod({ ...period, end: event.target.value })} /></label>
      </fieldset>
      <label className="flex flex-col gap-1 text-caption text-muted-foreground">양식<select aria-label="양식" disabled={busy} className={inputClass} value={template} onChange={(event) => setTemplate(event.target.value as ReportTemplate)}>
        <option value="profile">내 양식 ({options?.profile?.report_style === 'prose' ? '서술형' : '개조식'})</option><option value="bullet">개조식</option><option value="prose">서술형</option>
      </select></label>
      <label className="flex min-w-36 flex-col gap-1 text-caption text-muted-foreground">보고 대상<input aria-label="보고 대상" className={inputClass} disabled={busy} value={recipient} onChange={(event) => setRecipient(event.target.value)} /></label>
      <div className="ml-auto flex gap-2">
        <Button variant="secondary" disabled={!mayGenerate} onClick={() => requestGeneration('open')}>보고서 열기</Button>
        <Button variant="secondary" className="border-ai-border bg-ai text-ai-foreground hover:bg-ai-text" disabled={!mayGenerate} onClick={() => requestGeneration('regenerate')}><RefreshCw />다시 만들기</Button>
      </div>
    </div>
    {options?.generation === 'test_double' && <p className="border-b border-warning-border bg-warning-subtle px-6 py-2 text-caption text-warning">검토용 테스트 대역 · 가짜 메일만 사용합니다. 실제 AI 생성 결과가 아닙니다.</p>}
    {error && <div role="alert" className="border-b border-warning-border bg-warning-subtle px-6 py-3 text-body text-warning">{error}</div>}
    {message && <p role="status" className="border-b bg-success-subtle px-6 py-2 text-caption text-success">{message}</p>}
    <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
      <main aria-label="보고서 본문" className="min-w-0 flex-1 px-8 py-6" aria-busy={busy}>
        {!options && busy && <Loading sections={['금주 주요 업무', '진행 중인 업무', '이슈·요청사항', '차주 계획']} />}
        {options && !options.profile && <Empty title="주간 보고 프로필이 없습니다" description="프로필과 보고 양식을 연결한 뒤 다시 열어 주세요." />}
        {options && options.remaining_days > 0 && <Empty title={`사용 1주 후부터 만들 수 있어요 (${options.remaining_days}일 남음)`} description={`${options.available_on}부터 사용할 수 있습니다.`} />}
        {options?.profile && options.remaining_days === 0 && !report && busy && <Loading sections={options.profile.report_sections} />}
        {options?.profile && !busy && !report && (recipient.trim()
          ? <Empty title="보고서를 아직 만들지 못했어요" description="연결 상태를 확인한 뒤 보고서 열기를 눌러 주세요." />
          : <Empty title="보고 대상을 입력해 주세요" description="위 입력란에 보고 대상을 적은 뒤 보고서 열기를 눌러 주세요." />)}
        {report && <>
          <div className="flex flex-wrap items-center justify-between gap-2"><h1 className="text-heading font-bold">{report.title}</h1><span className="text-caption text-muted-foreground">{dirty ? '저장하지 않은 수정 있음' : `저장본 · 버전 ${report.revision}`}</span></div>
          <p className="mt-2 text-caption text-muted-foreground">{report.subtitle} · {report.generation === 'test_double' ? '테스트 대역 결과' : report.generation === 'ai' ? '◆ AI 작성' : '업무 메일 없음'} — 내용을 바로 고칠 수 있어요</p>
          <p className="mt-1 text-caption text-muted-foreground">보고 대상: {report.recipient} · {report.style === 'bullet' ? '개조식' : '서술형'}</p>
          {busy && <p role="status" className="mt-4 text-caption text-ai-text">보고서를 처리하고 있어요. 현재 내용은 결과 확인 전까지 유지합니다.</p>}
          {report.status === 'empty' && <Empty title="이 기간에 주고받은 업무 메일이 없어요" description="다른 기간을 선택하거나 제외된 메일 목록을 확인해 주세요." />}
          {sections.map((section, sectionIndex) => <section key={section.name} className="mt-5">
            <h2 className="mb-2 border-b pb-2 text-title font-bold">{sectionIndex + 1}. {section.name}</h2>
            {!section.items.length && <p className="px-2 py-3 text-caption text-muted-foreground">연결된 보고 항목이 없습니다.</p>}
            {section.items.map((item, itemIndex) => <div key={item.item_id} className={`mb-1 flex items-start gap-2 rounded-sm border p-2 ${selected === item.item_id ? 'border-ai-border bg-ai-subtle' : 'border-transparent'}`}>
              <span className="pt-2 text-muted-foreground">{report.style === 'bullet' ? '·' : ''}</span>
              <textarea aria-label={`항목 내용 ${sectionIndex + 1}-${itemIndex + 1}`} rows={1} disabled={busy}
                className="min-w-0 flex-1 resize-y rounded-sm bg-transparent px-1 py-1 leading-6 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
                value={item.text} onFocus={() => setSelected(item.item_id)} onChange={(event) => updateItem(item.item_id, { text: event.target.value })}
                onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); void save(); } }} />
              <button type="button" aria-label={`항목 ${sectionIndex + 1}-${itemIndex + 1} 근거 ${item.evidence.length}개`} aria-pressed={selected === item.item_id}
                className={`mt-1 h-6 shrink-0 rounded-sm border border-ai-border px-2 text-caption font-semibold focus-visible:ring-2 focus-visible:ring-ring ${selected === item.item_id ? 'bg-ai text-ai-foreground' : 'bg-background text-ai-text'}`}
                onClick={() => setSelected(item.item_id)}>근거 {item.evidence.length}</button>
            </div>)}
            {report.evidence_mails.length > 0 && <button type="button" disabled={busy} className="mt-1 inline-flex items-center gap-1 rounded-sm px-2 py-2 text-caption text-muted-foreground hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring" onClick={() => {
              const item = { item_id: crypto.randomUUID(), text: '', evidence: [] };
              setSections((current) => current.map((section, index) => index === sectionIndex ? { ...section, items: [...section.items, item] } : section)); setSelected(item.item_id);
            }}><Plus size={14} />항목 추가</button>}
          </section>)}
        </>}
      </main>
      <aside aria-label="근거 메일과 포함 범위" className="flex w-full shrink-0 flex-col border-t bg-muted/40 p-5 lg:w-[300px] lg:border-l lg:border-t-0">
        <h2 className="text-body font-semibold">선택한 항목의 근거 메일</h2>
        <p className="mt-2 text-caption text-muted-foreground">{activeItem?.text || '항목 옆 근거 배지를 선택해 주세요.'}</p>
        {activeItem?.evidence.map((id) => {
          const mail = report?.evidence_mails.find((mail) => mail.mail_id === id);
          return mail ? <button key={id} type="button" onClick={() => setPreview(mail)} className="border-b py-4 text-left focus-visible:ring-2 focus-visible:ring-ring">
            <span className="block text-body font-semibold">{mail.subject || '(제목 없음)'}</span>
            <span className="mt-1 block text-caption text-muted-foreground">{mail.from_name || mail.from_addr} → {mail.to.map((contact) => contact.name || contact.addr).join(', ')} · {mailDate(mail.received_at)}</span>
          </button> : null;
        })}
        {activeItem && <details className="mt-4 text-caption"><summary className="cursor-pointer text-ai-text">근거 메일 변경</summary><div className="mt-3 max-h-64 space-y-3 overflow-auto">{report?.evidence_mails.map((mail) => <label key={mail.mail_id} className="flex items-start gap-2">
          <input type="checkbox" disabled={busy} checked={activeItem.evidence.includes(mail.mail_id)} onChange={(event) => updateItem(activeItem.item_id, { evidence: event.target.checked ? [...activeItem.evidence, mail.mail_id] : activeItem.evidence.filter((id) => id !== mail.mail_id) })} />{mail.subject}
        </label>)}</div></details>}
        <div className="mt-auto pt-10">
          <h2 className="mb-3 text-body font-semibold">포함 범위</h2>
          <dl className="space-y-3 text-caption">
            <div className="flex justify-between gap-2"><dt>기간 내 메일</dt><dd className="font-semibold tabular-nums">{report ? `${report.scope.total}건` : '—'}</dd></div>
            <div className="flex justify-between gap-2"><dt>업무로 묶인 메일</dt><dd className="font-semibold tabular-nums">{report ? `${report.scope.grouped}건 (${report.scope.groups}개 업무)` : '—'}</dd></div>
            <div className="flex justify-between gap-2"><dt>제외 (뉴스레터·공지)</dt><dd className="font-semibold tabular-nums">{report ? `${report.scope.excluded}건` : '—'}</dd></div>
          </dl>
          <button type="button" disabled={!report || excludedLoading || busy} onClick={() => void openExcluded()} className="mt-4 rounded-sm text-caption font-semibold text-ai-text focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40">{excludedLoading ? '제외 목록을 불러오는 중…' : '제외된 메일 보기 ›'}</button>
        </div>
      </aside>
    </div>
    <footer className="flex flex-wrap items-center gap-3 border-t px-6 py-3">
      <Button variant="secondary" disabled={!report || !valid || busy} onClick={() => void copy()}><Copy />복사</Button>
      <span className="text-caption text-muted-foreground">{dirty && !valid ? '항목 내용과 근거를 1건 이상 연결해 주세요.' : '본문을 고친 뒤 Enter 또는 저장을 누르세요.'}</span>
      <Button className="ml-auto" disabled={!dirty || !valid || busy} onClick={() => void save()}><Save />변경 내용 저장</Button>
    </footer>
    {confirm && <Modal title={confirm === 'regenerate' ? '다시 만들기 전 확인' : '다른 보고서를 열기 전 확인'} close={() => setConfirm(null)}>
      <p>저장하지 않은 수정 내용이 있습니다. 계속하면 새 결과로 바뀝니다. 요청이 실패하면 현재 편집 내용은 그대로 보존합니다.</p>
      <div className="mt-6 flex justify-end gap-2"><Button variant="secondary" onClick={() => setConfirm(null)}>편집 계속하기</Button><Button onClick={() => void generate(confirm)}>계속 진행</Button></div>
    </Modal>}
    {preview && <Modal title="근거 메일 원문" close={() => setPreview(null)}><MailContents mail={preview} /></Modal>}
    {excluded && <Modal title="제외된 메일" close={() => setExcluded(null)}>
      <p className="mb-4 text-caption text-muted-foreground">공지·뉴스레터로 분류된 {excluded.length}건입니다. 사용자 수정 분류를 우선합니다.</p>
      {excluded.map((item) => <details key={item.mail.mail_id} className="border-b py-3"><summary className="cursor-pointer text-body font-semibold">{item.mail.subject} <span className="text-caption font-normal text-muted-foreground">· {item.reason === 'notice' ? '공지' : '뉴스레터·광고'}</span></summary><div className="pt-3"><MailContents mail={item.mail} /></div></details>)}
    </Modal>}
  </section>;
}

function Loading({ sections }: { sections: string[] }) {
  return <div role="status"><p className="text-body text-ai-text">한 주의 메일을 정리하고 있어요…</p>{sections.map((name) => <div key={name} className="mt-7"><h2 className="border-b pb-2 font-semibold">{name}</h2><div className="mt-4 h-4 w-4/5 rounded bg-muted" /><div className="mt-3 h-4 w-3/5 rounded bg-muted" /></div>)}</div>;
}
function Empty({ title, description }: { title: string; description: string }) {
  return <div className="flex min-h-52 flex-col items-center justify-center gap-3 px-4 py-10 text-center"><span className="rounded-lg bg-selected p-4 text-primary"><Mail className="size-8" /></span><h2 className="text-title font-semibold">{title}</h2><p className="text-body text-muted-foreground">{description}</p></div>;
}
