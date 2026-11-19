import { useCallback, useEffect, useRef, useState } from 'react';
import { Archive, File, Inbox, PenLine, RefreshCw, Send, Settings, Trash2 } from 'lucide-react';
import logo from '@brand/klover-logo.svg';
import mark from '@brand/klover-mark.svg';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { mailFailure, type MailDetail, type MailError, type MailReadBridge, type MailSession, type MailSummary } from '../../../shared/mail-read';

const dateFormatter = new Intl.DateTimeFormat('ko-KR', {
  timeZone: 'Asia/Seoul', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
});
const timestamp = (value: string) => dateFormatter.format(new Date(value));
const subject = (value: string) => value || '(제목 없음)';
const isAuthenticationError = (error: MailError) => ['unauthorized', 'forbidden', 'configuration'].includes(error.code);

export function MailboxPage({ api, session, onDisconnected }: {
  api: MailReadBridge; session: MailSession; onDisconnected: (error: MailError) => void;
}) {
  const [mails, setMails] = useState<MailSummary[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<MailError | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<MailDetail | null>(null);
  const [detailError, setDetailError] = useState<MailError | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailRetry, setDetailRetry] = useState(0);
  const listRequest = useRef(0);
  const busy = useRef(false);

  const loadList = useCallback(async (nextCursor: string | null = null) => {
    if (busy.current) return;
    busy.current = true;
    const request = ++listRequest.current;
    setLoading(true);
    setListError(null);
    if (!nextCursor) { setMails([]); setCursor(null); setSelected(null); setDetail(null); }
    const result = await api.inbox({ limit: 20, cursor: nextCursor }).catch(() => mailFailure('connection'));
    if (request !== listRequest.current) return;
    busy.current = false;
    setLoading(false);
    if (!result.ok) {
      if (isAuthenticationError(result.error)) onDisconnected(result.error);
      else setListError(result.error);
      return;
    }
    setMails(previous => [...new Map((nextCursor ? [...previous, ...result.data.items] : result.data.items).map(mail => [mail.mail_id, mail])).values()]);
    setCursor(result.data.next_cursor);
  }, [api, onDisconnected]);

  useEffect(() => {
    busy.current = false;
    void loadList();
    return () => { ++listRequest.current; busy.current = false; };
  }, [loadList]);

  useEffect(() => {
    let active = true;
    setDetail(null);
    setDetailError(null);
    setDetailLoading(Boolean(selected));
    if (selected) {
      void api.detail(selected).catch(() => mailFailure('connection')).then(result => {
        if (!active) return;
        setDetailLoading(false);
        if (result.ok) setDetail(result.data);
        else if (isAuthenticationError(result.error)) onDisconnected(result.error);
        else setDetailError(result.error);
      });
    }
    return () => { active = false; };
  }, [selected, api, detailRetry, onDisconnected]);

  return (
    <main className="flex h-screen min-h-[640px] min-w-[1000px] flex-col bg-background">
      <header className="flex h-14 shrink-0 items-center gap-6 border-b px-5">
        <img src={logo} alt="Klover" className="h-[26px] w-[176px] object-contain object-left" />
        <span className="text-caption text-muted-foreground">읽기 전용</span>
        <span className="ml-auto truncate text-body" title={session.email}>{session.email}</span>
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-selected text-selected-foreground" aria-hidden="true">{session.email.slice(0, 1).toUpperCase()}</span>
      </header>
      <div className="border-b bg-muted px-5 py-2 text-caption text-muted-foreground">
        프로필·알림 설정과 AI 기능은 아직 준비 중입니다. <a className="ml-3 underline underline-offset-2 focus-visible:outline-ring" href="#/onboarding/1">첫 실행 설정 보기</a>
      </div>
      <div className="flex min-h-0 flex-1">
        <aside className="flex w-[220px] shrink-0 flex-col border-r bg-sidebar p-3" aria-label="메일함">
          <Button disabled className="mb-3"><PenLine aria-hidden="true" />새 메일</Button>
          <div className="flex h-[34px] items-center gap-2 rounded-md bg-selected px-3 text-body font-semibold text-selected-foreground"><Inbox className="size-4" aria-hidden="true" />받은편지함</div>
          {[[Send, '보낸편지함'], [File, '임시보관함'], [Archive, '보관함'], [Trash2, '스팸·휴지통']].map(([Icon, label]) => {
            const Component = Icon as typeof Send;
            return <button key={String(label)} disabled className="flex h-[34px] items-center gap-2 px-3 text-body text-muted-foreground opacity-40"><Component className="size-4" aria-hidden="true" />{String(label)}</button>;
          })}
          <p className="mt-8 px-3 text-caption text-muted-foreground">AI 기능 · 준비 중</p>
          <button disabled className="mt-auto flex items-center gap-2 px-3 py-2 text-body text-muted-foreground opacity-40"><Settings className="size-4" aria-hidden="true" />설정</button>
        </aside>
        <section className="flex w-[360px] shrink-0 flex-col border-r max-[1280px]:w-[320px]" aria-label="받은 메일 목록">
          <div className="flex h-11 shrink-0 items-center gap-2 border-b px-4">
            <h1 className="text-body font-semibold">받은편지함</h1>
            <span className="text-caption text-muted-foreground">{mails.length ? `${mails.length}건 불러옴` : ''}</span>
            <Button variant="secondary" className="ml-auto px-2" disabled={loading} onClick={() => void loadList()} aria-label="목록 새로고침" title="저장된 메일 목록 다시 불러오기"><RefreshCw aria-hidden="true" /></Button>
          </div>
          <p className="border-b px-4 py-2 text-caption text-muted-foreground">최신 수신순 · 새로고침은 저장된 메일만 조회합니다.</p>
          <div className="min-h-0 flex-1 overflow-y-auto" aria-busy={loading}>
            {loading && !mails.length && <div role="status" className="space-y-3 p-4"><span className="sr-only">메일 목록 불러오는 중</span>{[1, 2, 3, 4].map(key => <div key={key} className="h-20 animate-pulse rounded-md bg-muted" />)}</div>}
            {!loading && !listError && !mails.length && <div className="p-6 text-center"><img src={mark} alt="" className="mx-auto mb-5 size-16" /><h2 className="text-title font-semibold">받은편지함이 비어 있습니다</h2><p className="mt-3 text-body text-muted-foreground">사용 시작 이후 수신해 저장한 메일이 여기에 표시됩니다. 이전 메일은 가져오지 않습니다.</p></div>}
            {mails.map(mail => <button key={mail.mail_id} onClick={() => setSelected(mail.mail_id)} aria-pressed={selected === mail.mail_id}
              className={cn('block w-full border-b border-l-[3px] border-l-background p-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring', selected === mail.mail_id && 'border-l-selected-bar bg-selected')}>
              <span className="flex items-start gap-2 text-body"><span className={cn('min-w-0 flex-1 truncate', !mail.is_read && 'font-semibold')}>{!mail.is_read && <span className="mr-1.5 inline-block size-1.5 rounded-full bg-primary" aria-label="안 읽음" />}{mail.from_name || mail.from_addr}</span><time className="shrink-0 text-caption text-muted-foreground" dateTime={mail.received_at}>{timestamp(mail.received_at)}</time></span>
              <span className="mt-1 block truncate text-body font-semibold">{subject(mail.subject)}</span>
              <span className="mt-1 line-clamp-2 text-caption text-muted-foreground">{mail.preview}</span>
            </button>)}
            {listError && <div role="alert" className="p-4 text-body text-danger"><p>{listError.message}</p><Button variant="secondary" className="mt-3" onClick={() => void loadList(mails.length ? cursor : null)}>목록 다시 시도</Button></div>}
            {cursor && !listError && <div className="p-4"><Button variant="secondary" className="w-full" disabled={loading} onClick={() => void loadList(cursor)}>{loading ? '불러오는 중…' : '다음 페이지'}</Button></div>}
          </div>
        </section>
        <section className="min-w-0 flex-1 overflow-y-auto" aria-label="선택한 메일">
          {!selected && <p className="flex h-full items-center justify-center text-body text-muted-foreground">메일을 선택하세요</p>}
          {detailLoading && <div role="status" className="space-y-4 p-7"><span className="sr-only">메일 본문 불러오는 중</span><div className="h-7 animate-pulse rounded-md bg-muted" /><div className="h-40 animate-pulse rounded-md bg-muted" /></div>}
          {detailError && <div role="alert" className="p-7 text-body text-danger"><p>{detailError.message}</p><Button variant="secondary" className="mt-3" onClick={() => setDetailRetry(value => value + 1)}>본문 다시 시도</Button></div>}
          {detail && <article className="mx-auto max-w-[816px] px-7 py-5">
            <h2 className="break-words text-heading font-bold">{subject(detail.subject)}</h2>
            <div className="my-4 space-y-1 border-b pb-4 text-body">
              <p><strong>{detail.from_name || detail.from_addr}</strong> <span className="text-muted-foreground">&lt;{detail.from_addr}&gt;</span></p>
              <p className="break-words text-caption text-muted-foreground">받는 사람: {detail.to.map(contact => contact.name ? `${contact.name} <${contact.addr}>` : contact.addr).join(', ') || '—'}</p>
              {detail.cc.length > 0 && <p className="break-words text-caption text-muted-foreground">참조: {detail.cc.map(contact => contact.addr).join(', ')}</p>}
              <time className="block text-caption text-muted-foreground" dateTime={detail.received_at}>{timestamp(detail.received_at)} (한국 시간)</time>
            </div>
            <div className="whitespace-pre-wrap break-words text-body leading-7" data-testid="mail-text-body">{detail.body_text || '텍스트 본문이 없습니다.'}</div>
          </article>}
        </section>
      </div>
    </main>
  );
}
