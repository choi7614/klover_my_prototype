import { useCallback, useEffect, useState } from 'react';
import { HashRouter, Navigate, Route, Routes } from 'react-router-dom';
import { OnboardingStartPage } from './features/onboarding/onboarding-start-page';
import { MailboxPage } from './features/mailbox/mailbox-page';
import { Button } from './components/ui/button';
import { mailFailure, type MailError, type MailSession } from '../shared/mail-read';
import { F2ProfileRoute, F2ReplyRoute, unavailableF2Client, type F2Client } from './features/profile-draft';

// F2 서버 연결 통로(main/preload IPC)는 아직 없다. 기본값은 '준비 부족' 클라이언트다.
export function App({ f2Client = unavailableF2Client }: { f2Client?: F2Client } = {}) {
  const api = window.klover?.mail;
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
        {session && api && <Route path="/mail/inbox" element={<MailboxPage api={api} session={session} onDisconnected={disconnected} />} />}
        <Route path="/settings/profile" element={<F2ProfileRoute client={f2Client} mailboxPath={mailboxPath} />} />
        <Route path="/reply/:mailId" element={<F2ReplyRoute client={f2Client} mailboxPath={mailboxPath} />} />
        <Route path="*" element={<Navigate to={session ? '/mail/inbox' : '/onboarding/1'} replace />} />
      </Routes>
    </HashRouter>
  );
}
