import { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import 'pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css';
import './preview.css';
import { SearchPage } from '../../src/renderer/features/search/search-page';
import { SyntheticSearchClient } from './synthetic-client';

function Preview() {
  const client = useMemo(() => new SyntheticSearchClient(), []);
  const [selection, setSelection] = useState('');
  return <>
    <div className="border-b border-warning-border bg-warning-subtle px-6 py-2 text-caption text-warning">
      F3 독립 검사 · 합성 데이터 · 앱 미통합
      {selection && <span role="status"> · {selection}</span>}
    </div>
    <SearchPage client={client} identityKey="synthetic-user:synthetic-account"
      initialQuery="지난달 예산 관련 메일"
      navigation={{
        openMail: ({ mail_id }) => setSelection(`메일 열기 계약: ${mail_id}`),
        openDraft: ({ mail_id }) => setSelection(`초안 열기 계약: ${mail_id}`),
        backToInbox: () => setSelection('받은편지함 이동 계약'),
      }} />
  </>;
}

createRoot(document.getElementById('root')!).render(<Preview />);
