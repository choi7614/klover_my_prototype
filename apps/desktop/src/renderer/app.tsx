import { useCallback, useEffect, useMemo, useState } from 'react';
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom';
import { OnboardingStartPage } from './features/onboarding/onboarding-start-page';
import { MailboxRoute, SearchRoute, unavailableSearchClient } from './features/mailbox/routes';
import { Button } from './components/ui/button';
import { mailFailure, type MailError, type MailSession } from '../shared/mail-read';
import { F2ProfileRoute, F2ReplyRoute, unavailableF2Client, type F2Client } from './features/profile-draft';
import type { SearchClient } from './features/search/contracts';
import { createF2IPCClient } from './bridges/f2-ipc-client';
import { createSearchIPCClient } from './bridges/search-ipc-client';
import { WeeklyReportPage } from './features/weekly-report/weekly-report-page';
import { createWeeklyReportIPCClient, unavailableWeeklyReportClient } from './features/weekly-report/ipc-client';
import { createSuggestionsIPCClient, unavailableSuggestionsClient } from './features/suggestions/ipc-client';
import { TodoListPage } from './features/suggestions/todo-list';

export function App({ f2Client, searchClient }: { f2Client?: F2Client; searchClient?: SearchClient } = {}) {
  const api = window.klover?.mail;
  // main/preload 통로가 있으면 실제 서버에 연결하고, 없으면(테스트·브라우저 미리보기) '준비 부족'을 보여 준다.
  const f2Bridge = window.klover?.f2;
  const searchBridge = window.klover?.search;
  const weeklyReportBridge = window.klover?.weeklyReport;
  const suggestionsBridge = window.klover?.suggestions;
  // F5 통로가 없으면 메일 읽기는 S03 모양 그대로, 할 일 화면은 '준비 중'을 보여 준다.
  const suggestions = useMemo(() => suggestionsBridge ? createSuggestionsIPCClient(suggestionsBridge) : undefined, [suggestionsBridge]);
  const weeklyReport = useMemo(() => weeklyReportBridge ? createWeeklyReportIPCClient(weeklyReportBridge) : unavailableWeeklyReportClient, [weeklyReportBridge]);
  const f2 = useMemo(() => f2Client ?? (f2Bridge ? createF2IPCClient(f2Bridge) : unavailableF2Client), [f2Client, f2Bridge]);
  const search = useMemo(() => searchClient ?? (searchBridge ? createSearchIPCClient(searchBridge) : unavailableSearchClient), [searchClient, searchBridge]);
  const [session, setSession] = useState<MailSession | null>(null);
  const [error, setError] = useState<MailError | null>(null);
  const [loading, setLoading] = useState(Boolean(api));
  const [retry, setRetry] = useState(0);
  const disconnected = useCallback((reason: MailError) => { setSession(null); setError(reason); }, []);
  useEffect(() => {
    if (!api) return;
    let active = true;
    setLoading(true);
    setSession(null);
    setError(null);
    void api.session().catch(() => mailFailure('connection')).then(result => {
      if (!active) return;
      setLoading(false);
      if (result.ok) {
        setSession(result.data);
        if (retry > 0) window.location.hash = '/mail/inbox';
      }
      else setError(result.error);
    });
    return () => { active = false; };
  }, [api, retry]);
  if (loading) return <main role="status" className="flex min-h-screen items-center justify-center bg-background text-body text-muted-foreground">계정 연결 확인 중…</main>;
  const notice = error ? <div role="alert" className="mt-3 text-caption text-warning"><p>{error.message}</p><Button variant="secondary" className="mt-2" onClick={() => setRetry(value => value + 1)}>메일함 연결 다시 확인</Button></div> : undefined;
  const mailboxPath = session ? '/mail/inbox' : '/onboarding/1';
  return (
    <HashRouter>
      <Routes>
        <Route path="/onboarding/1" element={<><OnboardingStartPage connectionNotice={notice} />{session && <a href="#/mail/inbox" className="fixed bottom-5 left-6 rounded-md bg-primary p-3 text-body text-primary-foreground">연결된 받은편지함 열기</a>}</>} />
        {session && api && <Route path="/mail/inbox/:mailId?" element={<MailboxRoute api={api} session={session} onDisconnected={disconnected} suggestions={suggestions} />} />}
        {session && <Route path="/search" element={<SearchRoute client={search} session={session} />} />}
        {session && <Route path="/todos" element={<TodoListPage key={session.account_id} client={suggestions ?? unavailableSuggestionsClient} />} />}
        {session && <Route path="/report/weekly" element={<WeeklyReportPage key={session.account_id} client={weeklyReport} />} />}
        <Route path="/settings/profile" element={<F2ProfileRoute client={f2} mailboxPath={mailboxPath} />} />
        <Route path="/reply/:mailId" element={<F2ReplyRoute client={f2} mailboxPath={mailboxPath} />} />
        <Route path="*" element={<Navigate to={session ? '/mail/inbox' : '/onboarding/1'} replace />} />
      </Routes>
    </HashRouter>
  );
}
