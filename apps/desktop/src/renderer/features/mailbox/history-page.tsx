import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import type { HistoryJob } from '../../../shared/history-bridge';

const historyErrors: Record<string, string> = {
  import_failed: '가져오기를 완료하지 못했어요. 연결을 확인한 뒤 재시도하세요.',
  page_expired: 'Gmail 조회 정보가 만료됐어요. 재개하면 같은 기간을 중복 없이 다시 확인합니다.',
  server_restarted: '서버 재시작으로 중단됐어요. 재개하면 이어서 확인합니다.',
  range_limit: '작업 한도에 도달했어요. 저장된 메일은 보존됩니다. 기간을 줄여 새 작업을 시작하세요.',
};

export function HistoryPage() {
  const [start, setStart] = useState(''); const [end, setEnd] = useState('');
  const [jobs, setJobs] = useState<HistoryJob[]>([]); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function load() {
    try { const r = await window.klover?.history?.list(); if (r?.ok && Array.isArray(r.data)) setJobs(r.data); else setError('가져오기 서버 연결을 확인하세요.'); }
    catch { setError('가져오기 상태를 확인하지 못했어요.'); }
  }
  useEffect(() => { void load(); const timer = setInterval(() => void load(), 3000); return () => clearInterval(timer); }, []);
  async function run(id?: string, action?: 'pause' | 'resume') {
    const api = window.klover?.history; if (!api) return;
    if (!id && !window.confirm(`${start} ~ ${end} 받은편지함 메일을 가져올까요? 로컬 분석을 사용하며 과거 메일이 저장됩니다.`)) return;
    setBusy(true); setError('');
    try { const r = id && action ? await api.action(id, action) : await api.start({ start, end }); if (!r.ok) setError(r.error.message); await load(); }
    catch { setError('요청을 처리하지 못했어요. 저장된 메일은 보존됩니다.'); }
    finally { setBusy(false); }
  }
  return <main className="mx-auto max-w-3xl space-y-4 p-8 text-body">
    <h1 className="text-heading font-bold">과거 메일 가져오기</h1>
    <p>선택한 한국 날짜 범위의 현재 Gmail 받은편지함(INBOX)만 가져옵니다. 보낸 메일·보관함·스팸은 포함하지 않습니다. 최대 366일·작업당 10,000건입니다.</p>
    <p>기존 메일은 중복 저장하지 않습니다. 일반 수신 시작 시점·커서는 보존합니다. 로컬 분석 뒤 검색·보고서에 사용할 수 있으며, 이 작업으로 Claude를 호출하지 않습니다.</p>
    <label className="block">시작일 <input aria-label="가져오기 시작일" type="date" value={start} onChange={e => setStart(e.target.value)} className="rounded border bg-background p-2" /></label>
    <label className="block">종료일 <input aria-label="가져오기 종료일" type="date" value={end} onChange={e => setEnd(e.target.value)} className="rounded border bg-background p-2" /></label>
    <Button disabled={busy || !start || !end || jobs.some(j => j.status === 'running')} onClick={() => void run()}>선택 기간 가져오기</Button>
    {error && <p role="alert">{error}</p>}
    {jobs.map(j => <section key={j.job_id} className="space-y-2 rounded-leaf bg-background p-3 shadow-card"><p>{j.start} ~ {j.end} · {{ running:'가져오는 중', paused:'중단됨', failed:'실패 (부분 저장 보존)', completed:'완료' }[j.status]}</p><p>확인 {j.processed}건 · 새 저장 {j.saved}건 · 중복/제외 {j.skipped}건</p>{j.error && <p>{historyErrors[j.error] ?? historyErrors.import_failed}</p>}<Button variant="secondary" disabled={busy || j.status === 'completed'} onClick={() => void run(j.job_id, j.status === 'running' ? 'pause' : 'resume')}>{j.status === 'running' ? '중단' : '재개·재시도'}</Button></section>)}
    <p className="text-caption text-muted-foreground">중단은 현재 요청이 끝나는 대로 반영됩니다. 서버를 다시 켜면 진행 중 작업은 중단 상태로 복구되며 수동 재개할 수 있습니다.</p>
  </main>;
}
