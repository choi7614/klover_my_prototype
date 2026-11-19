import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import 'pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css';
import '@/styles/globals.css';
import logo from '@brand/klover-logo.svg';
import { SuggestionReader } from '../suggestion-reader';
import { syntheticBody, SyntheticSuggestionsClient } from '../testing/synthetic-client';

const client = new SyntheticSuggestionsClient();

function Preview() {
  const [rows, setRows] = useState(client.rows);
  const [fail, setFail] = useState(false);
  return <main className="min-h-screen bg-background text-foreground">
    <div className="flex flex-wrap items-center justify-between gap-4 border-b border-warning-border bg-warning-subtle px-6 py-3 text-caption text-warning">
      <span>합성 데이터 검사 전용 · 실제 메일·캘린더·OS 알림과 연결하지 않았습니다.</span>
      <label className="flex items-center gap-2"><input type="checkbox" checked={fail} onChange={event => {
        client.failApprovals = event.target.checked;
        setFail(event.target.checked);
      }} />등록 실패 검사</label>
    </div>
    <header className="flex items-center gap-6 border-b border-border px-6 py-4">
      <img src={logo} alt="Klover" className="w-28" /><p className="text-body text-muted-foreground">메일 읽기 · AI 제안</p>
    </header>
    <div className="border-b border-border px-6 py-6">
      <h1 className="text-heading font-bold">[합성 안내] 결산 리뷰 회의</h1>
      <p className="mt-2 text-body text-muted-foreground">가상 발신자 · fixture@example.invalid</p>
    </div>
    <SuggestionReader mailId="synthetic-mail" body={syntheticBody} suggestions={rows} client={client}
      calendarReady calendars={[{ id: 'synthetic-work', label: '업무 (합성 캘린더)' }]}
      onChange={row => setRows(current => current.map(item => item.suggestion_id === row.suggestion_id ? row : item))} />
  </main>;
}

createRoot(document.getElementById('root')!).render(<Preview />);
