import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { PrivacyPage } from './privacy-page';
import { ProfilePage } from './profile-page';
import { ReplyDraftPage } from './reply-draft-page';
import type { F2Client } from './contracts';

/** 통합 설정 이동. 실제 기능이 연결된 경로만 제공한다. */
export function F2ProfileRoute({ client, mailboxPath }: { client: F2Client; mailboxPath: string }) {
  const navigate = useNavigate();
  return <ProfilePage client={client} onExit={() => void navigate(mailboxPath)} onNavigate={target => {
    const paths = { home: '/settings', ai: '/settings/ai', history: '/settings/mail-history', profile: '/settings/profile', 'weekly-report': '/report/weekly', privacy: '/settings/privacy', calendar: '/settings/calendar' };
    if (target in paths) void navigate(paths[target as keyof typeof paths]);
  }} />;
}

export function F2ReplyRoute({ client, mailboxPath }: { client: F2Client; mailboxPath: string }) {
  const navigate = useNavigate();
  const { mailId } = useParams();
  const [params] = useSearchParams();
  const draftId = params.get('draft') ?? undefined;
  if (!mailId || !/^[A-Za-z0-9_-]{1,128}$/.test(mailId)) {
    return <p role="alert" className="p-6 text-body">메일을 먼저 선택해 주세요.</p>;
  }
  if (draftId && !/^[A-Za-z0-9_-]{1,128}$/.test(draftId)) {
    return <p role="alert" className="p-6 text-body">임시 저장된 초안 주소를 확인해 주세요.</p>;
  }
  return <ReplyDraftPage autoGenerate={false} client={client} mailId={mailId} draftId={draftId} onExit={() => void navigate(mailboxPath)} />;
}

export function F2PrivacyRoute({ client }: { client: F2Client }) {
  const navigate = useNavigate();
  return <PrivacyPage client={client} onBack={() => void navigate('/settings/profile')} />;
}
