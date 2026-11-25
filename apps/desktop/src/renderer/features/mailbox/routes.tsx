import { useMemo } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { MailboxPage } from './mailbox-page';
import { SearchPage } from '../search/search-page';
import { SearchClientError, type SearchClient, type SearchNavigation } from '../search/contracts';
import { validMailId, type MailError, type MailReadBridge, type MailSession } from '../../../shared/mail-read';
import type { F5Client } from '../suggestions/types';
import type { MailAnalysisClient } from '../mail-analysis/client';

/** `/mail/inbox/:mailId?` — 검색 결과 등에서 특정 메일을 선택한 채로 연다. 공통 App이 등록한다. */
export function MailboxRoute(props: {
  api: MailReadBridge; session: MailSession; onDisconnected: (error: MailError) => void; suggestions?: F5Client;
  /** F1 분류·요약 통로(patches/F1/06 적용 후 App이 넣는다). */
  analysis?: MailAnalysisClient;
}) {
  const { mailId } = useParams();
  const initial = mailId && validMailId(mailId) ? mailId : null;
  return <MailboxPage key={initial ?? 'inbox'} {...props} initialMailId={initial} />;
}

// F3 검색 서버 연결 통로(main/preload IPC)가 생기기 전의 기본값. 가짜 결과 대신 준비 부족을 알린다.
const notReady = () => new SearchClientError('검색 서버 연결을 준비 중이에요. 다음 업데이트에서 연결됩니다.');
export const unavailableSearchClient: SearchClient = {
  // eslint-disable-next-line require-yield
  async *search() { throw notReady(); },
  recent() { return Promise.reject(notReady()); },
};

/** `/search?q=` — S03 상단 검색창 Enter로 들어온다. 결과에서 메일·답장 초안·받은편지함으로 돌아간다. */
export function SearchRoute({ client, session }: { client: SearchClient; session: MailSession }) {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const query = (params.get('q') ?? '').slice(0, 500);
  const navigation = useMemo<SearchNavigation>(() => ({
    // 현재 메일 상세 API는 받은편지함만 읽는다. 보낸 메일은 열기 계약이 생기면 연결한다.
    openMail: ({ mail_id, direction }) => {
      if (direction === 'received' && validMailId(mail_id)) void navigate(`/mail/inbox/${encodeURIComponent(mail_id)}`);
    },
    openDraft: ({ mail_id }) => { if (validMailId(mail_id)) void navigate(`/reply/${encodeURIComponent(mail_id)}`); },
    backToInbox: () => void navigate('/mail/inbox'),
  }), [navigate]);
  return <SearchPage key={query} client={client} identityKey={`${session.user_id}:${session.account_id}`}
    navigation={navigation} initialQuery={query} autoSearch={Boolean(query.trim())} />;
}
