import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ProfilePage } from './profile-page';
import { ReplyDraftPage } from './reply-draft-page';
import type { F2Client } from './contracts';

/** 공통 라우터에 적용 전 패치로만 연결한다. 실제 메일함 경로는 F0가 제공한다. */
export function F2ProfileRoute({ client, mailboxPath }: { client: F2Client; mailboxPath: string }) {
  const navigate = useNavigate();
  return <ProfilePage client={client} onExit={() => void navigate(mailboxPath)} />;
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
  return <ReplyDraftPage client={client} mailId={mailId} draftId={draftId} onExit={() => void navigate(mailboxPath)} />;
}
