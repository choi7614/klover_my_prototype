import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Archive, File, Inbox, PenLine, RefreshCw, Search, Send, Settings, SquareCheck, Trash2 } from 'lucide-react';
import logo from '@brand/klover-logo.svg';
import mark from '@brand/klover-mark.svg';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { MailSuggestions } from '../suggestions/mail-suggestions';
import type { F5Client } from '../suggestions/types';
import type { MailAnalysisClient } from '../mail-analysis/client';
import { AiSummaryBox, MailAnalysisLine } from '../mail-analysis/analysis-view';
import { useMailAnalysis } from '../mail-analysis/use-mail-analysis';
import { MAIL_CATEGORIES, mailFailure, type MailCategoryCounts, type MailDetail, type MailError, type MailReadBridge, type MailSession, type MailSummary } from '../../../shared/mail-read';
import type { AnalysisCategory } from '../../../shared/f1-bridge';
import { CATEGORIES } from '../mail-analysis/categories';

const dateFormatter = new Intl.DateTimeFormat('ko-KR', {
  timeZone: 'Asia/Seoul', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
});
const timestamp = (value: string) => dateFormatter.format(new Date(value));
const subject = (value: string) => value || '(제목 없음)';
const isAuthenticationError = (error: MailError) => ['unauthorized', 'forbidden', 'configuration'].includes(error.code);

// 다른 화면(F2·F3)으로의 이동은 해시 경로만 바꾼다. 실제 화면 등록은 공통 App이 맡는다.
const go = (path: string) => { window.location.hash = path; };

export function MailboxPage({ api, session, onDisconnected, initialMailId = null, suggestions, analysis }: {
  api: MailReadBridge; session: MailSession; onDisconnected: (error: MailError) => void;
  /** F1 분류·요약 통로. 없으면 AI 표시 없이 미리보기만 보여 준다. */
  analysis?: MailAnalysisClient;
  /** F5 제안·할 일 통로. 없으면 제안 패널 없이 S03 모양만 보여 준다. */
  suggestions?: F5Client;
  /** 검색 결과 등에서 특정 메일을 열고 들어올 때 처음 선택할 메일 */
  initialMailId?: string | null;
}) {
  const [mails, setMails] = useState<MailSummary[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [listError, setListError] = useState<MailError | null>(null);
  const [selected, setSelected] = useState<string | null>(initialMailId);
  const [detail, setDetail] = useState<MailDetail | null>(null);
  const [detailError, setDetailError] = useState<MailError | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailRetry, setDetailRetry] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<MailError | null>(null);
  const [searchText, setSearchText] = useState('');
  // 왼쪽 '분류' 목록: null이면 받은편지함 전체. 건수는 서버가 센 값이고, 못 읽으면 숫자만 숨긴다.
  const [category, setCategoryFilter] = useState<AnalysisCategory | null>(null);
  const [counts, setCounts] = useState<MailCategoryCounts | null>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const listRequest = useRef(0);
  const busy = useRef(false);
  const mounted = useRef(true);
  const canSync = typeof api.sync === 'function';
  // F1: 목록에 보이는 메일과 선택한 메일의 분류·요약. 근거 메일은 mail_id로만 연결한다.
  const analysisIds = useMemo(() => [...mails.map(mail => mail.mail_id), ...(selected ? [selected] : [])], [mails, selected]);
  const { setCategory, views, state: analysisState, retry: retryAnalysis, retryNotice } = useMailAnalysis(analysis, analysisIds);

  const loadList = useCallback(async (nextCursor: string | null = null) => {
    if (busy.current) return;
    busy.current = true;
    const request = ++listRequest.current;
    setLoading(true);
    setListError(null);
    if (!nextCursor) { setMails([]); setCursor(null); }
    const result = await api.inbox({ limit: 20, cursor: nextCursor, ...(category ? { category } : {}) }).catch(() => mailFailure('connection'));
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
  }, [api, category, onDisconnected]);

  const loadCounts = useCallback(async () => {
    if (!api.categoryCounts) return;
    const result = await api.categoryCounts().catch(() => mailFailure('connection'));
    if (!mounted.current) return;
    if (result.ok) setCounts(result.data);
    else if (isAuthenticationError(result.error)) onDisconnected(result.error);
  }, [api, onDisconnected]);

  useEffect(() => {
    busy.current = false;
    void loadList();
    return () => { ++listRequest.current; busy.current = false; };
  }, [loadList]);

  useEffect(() => {
    mounted.current = true;
    void loadCounts();
    return () => { mounted.current = false; };
  }, [loadCounts]);

  // 새로고침: Gmail에서 새 받은 메일을 가져온 뒤(서버) 저장된 목록을 처음부터 다시 읽는다.
  // 가져오기에 실패하면 기존 목록을 그대로 두고 오류와 다시 시도를 보여 준다.
  const refresh = useCallback(async () => {
    if (syncing || busy.current) return;
    setSyncNotice(null);
    setSyncError(null);
    if (api.sync) {
      setSyncing(true);
      const result = await api.sync().catch(() => mailFailure('connection'));
      if (!mounted.current) return;
      setSyncing(false);
      if (!result.ok) {
        if (isAuthenticationError(result.error)) onDisconnected(result.error);
        else setSyncError(result.error);
        return;
      }
      setSyncNotice(result.data.saved > 0 ? `새 메일 ${result.data.saved}건을 가져왔습니다.` : '새로 도착한 메일이 없습니다.');
    }
    setSelected(null);
    setDetail(null);
    void loadCounts();
    await loadList();
  }, [api, loadCounts, loadList, onDisconnected, syncing]);

  const chooseCategory = (next: AnalysisCategory | null) => {
    if (next === category) return;
    setSelected(null);
    setDetail(null);
    setCategoryFilter(next);
  };
  // 사용자가 메일 분류를 고치면 왼쪽 건수도 새로 읽는다.
  const changeMailCategory = setCategory && (async (mailId: string, next: AnalysisCategory) => {
    try { await setCategory(mailId, next); } finally { void loadCounts(); }
  });

  // S03: 상단 검색창은 누르거나 Ctrl K로 입력하고 Enter로 검색 화면(S07)에 간다.
  useEffect(() => {
    const focusSearch = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        searchInput.current?.focus();
      }
    };
    window.addEventListener('keydown', focusSearch);
    return () => window.removeEventListener('keydown', focusSearch);
  }, []);
  const submitSearch = (event: FormEvent) => {
    event.preventDefault();
    const query = searchText.trim();
    if (query) go(`/search?q=${encodeURIComponent(query)}`);
  };

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
        <form role="search" onSubmit={submitSearch} className="flex h-10 min-w-0 max-w-[720px] flex-1 items-center gap-2 rounded-full border bg-background px-4 focus-within:border-ai focus-within:ring-2 focus-within:ring-ai-border">
          <Search className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <label htmlFor="mailbox-search" className="sr-only">자연어 검색</label>
          <input id="mailbox-search" ref={searchInput} type="search" value={searchText} onChange={event => setSearchText(event.target.value)}
            maxLength={500} placeholder="무엇이든 물어보세요. 예: 지난주 영업기획팀이 보낸 예산 관련 메일"
            className="min-w-0 flex-1 bg-transparent text-body outline-none placeholder:text-muted-foreground" />
          <kbd className="shrink-0 rounded border px-1.5 text-caption text-muted-foreground">Ctrl K</kbd>
          <button type="submit" className="sr-only">검색</button>
        </form>
        <span className="ml-auto truncate text-body" title={session.email}>{session.email}</span>
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-selected text-selected-foreground" aria-hidden="true">{session.email.slice(0, 1).toUpperCase()}</span>
      </header>
      <div className="border-b bg-muted px-5 py-2 text-caption text-muted-foreground">
        프로필과 AI 제공자는 설정에서 변경할 수 있습니다. <a href="#/settings/mail-history" className="underline">과거 메일 가져오기</a> · <a href="#/settings/calendar" className="underline">캘린더 연결</a> · <a href="#/settings/ai" className="underline">AI 설정</a> · 알림 설정은 준비 중입니다. <a className="ml-3 underline underline-offset-2 focus-visible:outline-ring" href="#/onboarding/1">첫 실행 설정 보기</a>
      </div>
      <div className="flex min-h-0 flex-1">
        <aside className="flex w-[220px] shrink-0 flex-col overflow-y-auto bg-sidebar p-3 text-sidebar-foreground" aria-label="메일함">
          <Button disabled className="mb-3 rounded-leaf-sm"><PenLine aria-hidden="true" />새 메일</Button>
          <button type="button" aria-pressed={category === null} onClick={() => chooseCategory(null)}
            className={cn('flex h-[34px] w-full items-center gap-2 rounded-leaf-sm px-3 text-body focus-visible:outline-sidebar-ring',
              category === null ? 'bg-sidebar-primary font-semibold text-sidebar-primary-foreground' : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground')}>
            <Inbox className="size-4" aria-hidden="true" />받은편지함
            {counts && <span className="ml-auto text-caption opacity-80">{counts.total}</span>}
          </button>
          <nav aria-label="분류" className="mt-1 space-y-0.5">
            <p className="px-3 pb-0.5 pt-2 text-caption text-sidebar-muted">분류별 보기</p>
            {MAIL_CATEGORIES.map(key => {
              const active = category === key;
              return <button key={key} type="button" aria-pressed={active} onClick={() => chooseCategory(key)}
                className={cn('flex h-8 w-full items-center gap-2 rounded-leaf-sm px-3 text-body focus-visible:outline-sidebar-ring',
                  active ? 'bg-sidebar-primary font-semibold text-sidebar-primary-foreground' : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground')}>
                <span className={cn('size-2 shrink-0 rounded-full', CATEGORIES[key].dot)} aria-hidden="true" />
                <span className="truncate">{CATEGORIES[key].label}</span>
                {counts && <span className="ml-auto text-caption opacity-80">{counts.counts[key] ?? 0}</span>}
              </button>;
            })}
          </nav>
          {[[Send, '보낸편지함'], [File, '임시보관함'], [Archive, '보관함'], [Trash2, '스팸·휴지통']].map(([Icon, label]) => {
            const Component = Icon as typeof Send;
            return <button key={String(label)} disabled className="flex h-[34px] items-center gap-2 px-3 text-body text-sidebar-muted opacity-60"><Component className="size-4" aria-hidden="true" />{String(label)}</button>;
          })}
          <p className="mt-5 px-3 text-caption text-sidebar-muted">AI 기능</p>
          <a href="#/todos" className="mt-1 flex h-[34px] items-center gap-2 rounded-leaf-sm px-3 text-body text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:outline-sidebar-ring"><SquareCheck className="size-4" aria-hidden="true" />할 일</a>
          <a href="#/report/weekly" className="mt-auto rounded-leaf-sm px-3 py-2 text-body text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:outline-sidebar-ring">주간 보고</a>
          <a href="#/settings" className="mt-2 flex items-center gap-2 rounded-leaf-sm px-3 py-2 text-body text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:outline-sidebar-ring"><Settings className="size-4" aria-hidden="true" />설정</a>
        </aside>
        <section className="flex w-[360px] shrink-0 flex-col bg-canvas max-[1280px]:w-[320px]" aria-label="받은 메일 목록">
          <div className="flex h-11 shrink-0 items-center gap-2 border-b px-4">
            <h1 className="text-body font-semibold">받은편지함{category && <span className="font-normal text-muted-foreground"> · {CATEGORIES[category].label}</span>}</h1>
            <span className="text-caption text-muted-foreground">{mails.length ? `${mails.length}건 불러옴` : ''}</span>
            <Button variant="secondary" className="ml-auto px-2" disabled={loading || syncing} onClick={() => void refresh()} aria-label="목록 새로고침"
              title={canSync ? 'Gmail에서 새 메일 가져오기' : '저장된 메일 목록 다시 불러오기'}><RefreshCw className={cn(syncing && 'animate-spin')} aria-hidden="true" /></Button>
          </div>
          <p className="border-b px-4 py-2 text-caption text-muted-foreground">
            {canSync ? '최신 수신순 · 새로고침하면 Gmail에서 새 메일을 가져옵니다.' : '최신 수신순 · Gmail 가져오기 연결 준비 중이라 저장된 메일만 다시 읽습니다.'}
          </p>
          {syncing && <p role="status" className="border-b bg-muted px-4 py-2 text-caption text-muted-foreground">Gmail에서 새 메일 확인 중…</p>}
          {syncNotice && !syncing && <p role="status" className="border-b px-4 py-2 text-caption text-muted-foreground">{syncNotice}</p>}
          {syncError && <div role="alert" className="border-b px-4 py-3 text-caption text-danger"><p>{syncError.message}</p><Button variant="secondary" className="mt-2" onClick={() => void refresh()}>새 메일 다시 가져오기</Button></div>}
          <div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-2.5" aria-busy={loading}>
            {loading && !mails.length && <div role="status" className="space-y-3 p-2"><span className="sr-only">메일 목록 불러오는 중</span>{[1, 2, 3, 4].map(key => <div key={key} className="h-20 animate-pulse rounded-leaf bg-background" />)}</div>}
            {!loading && !listError && !mails.length && <div className="p-6 text-center"><img src={mark} alt="" className="mx-auto mb-5 size-16" />{category
              ? <><h2 className="text-title font-semibold">이 분류의 메일이 없습니다</h2><p className="mt-3 text-body text-muted-foreground">분석이 끝나지 않은 메일은 아직 분류되지 않아 여기에 보이지 않습니다. 왼쪽에서 받은편지함을 누르면 전체를 볼 수 있습니다.</p></>
              : <><h2 className="text-title font-semibold">받은편지함이 비어 있습니다</h2><p className="mt-3 text-body text-muted-foreground">사용 시작 이후 수신해 저장한 메일이 여기에 표시됩니다. 이전 메일은 가져오지 않습니다.</p></>}</div>}
            {mails.map(mail => <button key={mail.mail_id} onClick={() => setSelected(mail.mail_id)} aria-pressed={selected === mail.mail_id}
              className={cn('block w-full rounded-leaf bg-background p-4 text-left shadow-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring', selected === mail.mail_id && 'ring-2 ring-selected-bar')}>
              <span className="flex items-start gap-2 text-body"><span className={cn('min-w-0 flex-1 truncate', !mail.is_read && 'font-semibold')}>{!mail.is_read && <span className="mr-1.5 inline-block size-1.5 rounded-full bg-primary" aria-label="안 읽음" />}{mail.from_name || mail.from_addr}</span><time className="shrink-0 text-caption text-muted-foreground" dateTime={mail.received_at}>{timestamp(mail.received_at)}</time></span>
              <span className="mt-1 block truncate text-body font-semibold">{subject(mail.subject)}</span>
              {analysis
                ? <MailAnalysisLine view={views[mail.mail_id]} state={analysisState} preview={mail.preview} />
                : <span className="mt-1 line-clamp-2 text-caption text-muted-foreground">{mail.preview}</span>}
            </button>)}
            {listError && <div role="alert" className="p-4 text-body text-danger"><p>{listError.message}</p><Button variant="secondary" className="mt-3" onClick={() => void loadList(mails.length ? cursor : null)}>목록 다시 시도</Button></div>}
            {cursor && !listError && <div className="p-2"><Button variant="secondary" className="w-full" disabled={loading} onClick={() => void loadList(cursor)}>{loading ? '불러오는 중…' : '다음 페이지'}</Button></div>}
          </div>
        </section>
        <div className="flex min-w-0 flex-1 bg-canvas p-2.5 pl-0"><section className="min-w-0 flex-1 overflow-y-auto rounded-leaf-lg bg-background" aria-label="선택한 메일">
          {!selected && <p className="flex h-full items-center justify-center text-body text-muted-foreground">메일을 선택하세요</p>}
          {detailLoading && <div role="status" className="space-y-4 p-7"><span className="sr-only">메일 본문 불러오는 중</span><div className="h-7 animate-pulse rounded-md bg-muted" /><div className="h-40 animate-pulse rounded-md bg-muted" /></div>}
          {detailError && <div role="alert" className="p-7 text-body text-danger"><p>{detailError.message}</p><Button variant="secondary" className="mt-3" onClick={() => setDetailRetry(value => value + 1)}>본문 다시 시도</Button></div>}
          {selected && <div className="sticky top-0 flex h-11 items-center gap-2 rounded-t-leaf-lg border-b bg-background px-5">
            <a href={`#/reply/${encodeURIComponent(selected)}`}
              className="inline-flex h-8 items-center gap-1.5 rounded-leaf-sm bg-ai px-3 text-body font-semibold text-ai-foreground hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              답장 초안 만들기</a>
          </div>}
          {detail && (() => {
            // F1 AI 요약 박스: 이 메일(mail_id)의 분석 결과만 붙인다.
            const aiBox = analysis
              ? <AiSummaryBox view={views[detail.mail_id]} state={analysisState} onRetry={id => void retryAnalysis(id)} retryNotice={retryNotice} onCategoryChange={changeMailCategory} />
              : null;
            return suggestions
              // F5: 제안이 있는 메일만 S04(본문 + 제안 패널)로, 없으면 아래 S03 모양 그대로 보여 준다.
              ? <MailSuggestions key={detail.mail_id} mailId={detail.mail_id} body={detail.body_text} client={suggestions}
                header={<MailHead detail={detail} aiBox={aiBox} />} fallback={<MailArticle detail={detail} aiBox={aiBox} />} />
              : <MailArticle detail={detail} aiBox={aiBox} />;
          })()}
        </section></div>
      </div>
    </main>
  );
}

function MailHead({ detail, aiBox }: { detail: MailDetail; aiBox?: ReactNode }) {
  return <>
    <h2 className="break-words text-heading font-bold">{subject(detail.subject)}</h2>
    <div className="my-4 space-y-1 border-b pb-4 text-body">
      <p><strong>{detail.from_name || detail.from_addr}</strong> <span className="text-muted-foreground">&lt;{detail.from_addr}&gt;</span></p>
      <p className="break-words text-caption text-muted-foreground">받는 사람: {detail.to.map(contact => contact.name ? `${contact.name} <${contact.addr}>` : contact.addr).join(', ') || '—'}</p>
      {detail.cc.length > 0 && <p className="break-words text-caption text-muted-foreground">참조: {detail.cc.map(contact => contact.addr).join(', ')}</p>}
      <time className="block text-caption text-muted-foreground" dateTime={detail.received_at}>{timestamp(detail.received_at)} (한국 시간)</time>
    </div>
    {aiBox}
  </>;
}

function MailArticle({ detail, aiBox }: { detail: MailDetail; aiBox?: ReactNode }) {
  return <article className="mx-auto max-w-[816px] px-7 py-5">
    <MailHead detail={detail} aiBox={aiBox} />
    <div className="whitespace-pre-wrap break-words text-body leading-7" data-testid="mail-text-body">{detail.body_text || '텍스트 본문이 없습니다.'}</div>
  </article>;
}
