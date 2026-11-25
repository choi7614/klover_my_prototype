import { createRoot } from 'react-dom/client';
import { createWeeklyReportClient } from '../client';
import { WeeklyReportPage } from '../weekly-report-page';
import logo from '@brand/klover-logo.svg';
import 'pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css';
import '@/styles/globals.css';

// 검토 경로 전용. 운영 앱의 진입부·계정·IPC와 연결하지 않는다.
const client = createWeeklyReportClient(async ({ method, path, body }) => {
  const response = await fetch(`/__f4_review${path}`, {
    method,
    headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  return { status: response.status, body: await response.json() };
});
const root = document.getElementById('root');
if (!root) throw new Error('검토 화면을 표시할 영역이 없습니다.');
createRoot(root).render(<>
  <header className="flex h-16 items-center justify-between border-b px-6">
    <img src={logo} alt="Klover" className="h-7" />
    <p className="text-caption text-muted-foreground">S08 주간 보고 · 독립 검토 화면 · hong@example.test</p>
  </header>
  <WeeklyReportPage client={client} />
</>);
