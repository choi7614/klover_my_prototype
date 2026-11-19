import { createRoot } from 'react-dom/client';
import { useState } from 'react';
import './harness.css';
import { ProfilePage, ReplyDraftPage } from '@/features/profile-draft';
import { SyntheticF2Client, SYNTHETIC_MAIL } from './synthetic-client';

const client = new SyntheticF2Client();
client.failAI = new URLSearchParams(location.search).get('ai') === 'unavailable';
client.includeReference = new URLSearchParams(location.search).get('references') === 'yes';

function Harness() {
  const [screen, setScreen] = useState(location.hash === '#reply' ? 'reply' : 'profile');
  const [failure, setFailure] = useState(client.failAI);
  return <div className="flex h-screen min-h-0 min-w-[1280px] flex-col">
    <header className="flex h-20 shrink-0 items-center gap-4 border-b bg-background px-6">
      <span className="text-heading font-bold text-primary">klover</span>
      <span className="flex-1 text-caption text-muted-foreground">합성 응답 화면 검사 · 실제 AI·계정·발송 미연결</span>
      <button type="button" onClick={() => { setScreen('profile'); location.hash = 'profile'; }} className="rounded-md border px-3 py-2 text-caption">S09 프로필</button>
      <button type="button" onClick={() => { setScreen('reply'); location.hash = 'reply'; }} className="rounded-md border px-3 py-2 text-caption">S06 초안</button>
      <label className="text-caption"><input type="checkbox" checked={failure} onChange={e => { client.failAI = e.target.checked; setFailure(e.target.checked); }} /> 합성 AI 실패</label>
    </header>
    <div className="min-h-0 flex-1">{screen === 'profile'
      ? <ProfilePage client={client} onExit={() => setScreen('reply')} />
      : <ReplyDraftPage client={client} mailId={SYNTHETIC_MAIL.mail_id} onExit={() => setScreen('profile')} />}</div>
  </div>;
}

createRoot(document.getElementById('root')!).render(<Harness />);
