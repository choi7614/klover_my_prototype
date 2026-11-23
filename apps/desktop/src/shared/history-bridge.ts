export type HistoryJob = { job_id: string; start: string; end: string; status: 'running' | 'paused' | 'failed' | 'completed'; saved: number; skipped: number; processed: number; error: string | null };
export type HistoryResult = { ok: true; data: unknown } | { ok: false; error: { code: string; message: string } };
export interface HistoryBridge {
  list(): Promise<HistoryResult>;
  start(range: { start: string; end: string }): Promise<HistoryResult>;
  action(id: string, action: 'pause' | 'resume'): Promise<HistoryResult>;
}
export function readHistoryJob(value: unknown): HistoryJob {
  const row = value as HistoryJob;
  if (!row || typeof row.job_id !== 'string' || !/^[a-f0-9]{32}$/.test(row.job_id)
    || ![row.start, row.end].every(v => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v))
    || !['running', 'paused', 'failed', 'completed'].includes(row.status)
    || ![row.saved, row.skipped, row.processed].every(v => Number.isSafeInteger(v) && v >= 0)) throw new Error('invalid_history_response');
  return { job_id: row.job_id, start: row.start, end: row.end, status: row.status, saved: row.saved, skipped: row.skipped, processed: row.processed,
    error: row.error === null || row.error === undefined ? null : ['import_failed', 'page_expired', 'server_restarted', 'range_limit'].includes(row.error) ? row.error : 'import_failed' };
}
