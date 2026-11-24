// F1 분석 표시용 화면 어댑터. main/preload 통로(patches/F1/06) 전에는 없고, 없으면 AI 표시 없이 원래 목록을 보여 준다.
import type { AnalysisErrorCode, AnalysisRetryResult, F1Bridge, MailAnalysisBatch } from '../../../shared/f1-bridge';

export class AnalysisClientError extends Error {
  constructor(readonly code: AnalysisErrorCode | 'connection', message: string) { super(message); }
}

export interface MailAnalysisClient {
  batch(mailIds: string[]): Promise<MailAnalysisBatch>;
  retry(mailId: string): Promise<AnalysisRetryResult>;
}

async function unwrap<T>(pending: Promise<{ ok: true; data: T } | { ok: false; error: { code: AnalysisErrorCode; message: string } }>): Promise<T> {
  let result;
  try { result = await pending; }
  catch { throw new AnalysisClientError('connection', 'AI 분석 결과를 불러오지 못했습니다. 서버 실행 상태를 확인해 주세요.'); }
  if (!result || typeof result !== 'object') throw new AnalysisClientError('invalid_response', 'AI 분석 응답을 확인할 수 없습니다.');
  if (!result.ok) throw new AnalysisClientError(result.error.code, result.error.message);
  return result.data;
}

export function createAnalysisIPCClient(bridge: F1Bridge): MailAnalysisClient {
  return {
    batch: mailIds => unwrap(bridge.batch(mailIds)),
    retry: mailId => unwrap(bridge.retry(mailId)),
  };
}
