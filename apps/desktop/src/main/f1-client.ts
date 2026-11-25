// F1 분석 결과 표시 통로의 main 쪽 HTTP 클라이언트. 토큰은 main에서만 읽고, 응답은 검사기로 새로 만든다.
import { readLocalAPI, type LocalAPIConfiguration } from './mail-client';
import { localRequest } from './local-api';
import { validMailId } from '../shared/mail-read';
import {
  analysisFailure, validCategory, parseCategoryUpdated, type AnalysisCategory, type CategoryUpdated, parseAnalysisBatch, parseRetryResult, validBatchIds,
  type AnalysisResult, type AnalysisRetryResult, type F1Bridge, type MailAnalysisBatch,
} from '../shared/f1-bridge';

export class F1APIClient implements F1Bridge {
  constructor(private readonly configuration: LocalAPIConfiguration, private readonly fetcher: typeof fetch = fetch) {}

  private async request<T>(path: string, parse: (value: unknown) => T, method: 'GET' | 'POST' | 'PATCH' = 'GET', body?: object): Promise<AnalysisResult<T>> {
    const local = await readLocalAPI(this.configuration);
    if (!local) return analysisFailure('configuration');
    try {
      const { url, init } = localRequest(local, { method, path, body, timeoutMs: 10000 });
      const response = await this.fetcher(url, init);
      if (!response.ok) {
        let code: unknown;
        try { code = ((await response.json()) as { error?: { code?: unknown } })?.error?.code; } catch { code = undefined; }
        switch (response.status) {
          case 401: case 403: return analysisFailure('unauthorized');
          case 404: return analysisFailure('not_found');
          case 409: return analysisFailure('already_analyzed');
          case 422: return analysisFailure('invalid_request');
          case 503: return analysisFailure(code === 'analysis_unavailable' ? 'analysis_unavailable' : 'unavailable');
          default: return analysisFailure('unavailable');
        }
      }
      try { return { ok: true, data: parse(await response.json()) }; }
      catch { return analysisFailure('invalid_response'); }
    } catch { return analysisFailure('connection'); }
  }

  setCategory(mailId: string, category: AnalysisCategory): Promise<AnalysisResult<CategoryUpdated>> {
    if (!validMailId(mailId) || !validCategory(category)) return Promise.resolve(analysisFailure('invalid_request'));
    return this.request(`/mails/${encodeURIComponent(mailId)}/category`, value => parseCategoryUpdated(value, mailId, category), 'PATCH', { category });
  }

  batch(mailIds: string[]): Promise<AnalysisResult<MailAnalysisBatch>> {
    if (!validBatchIds(mailIds)) return Promise.resolve(analysisFailure('invalid_request'));
    const parameters = new URLSearchParams();
    mailIds.forEach(id => parameters.append('ids', id));
    return this.request(`/mails/analysis/batch?${parameters}`, value => parseAnalysisBatch(value, mailIds));
  }

  retry(mailId: string): Promise<AnalysisResult<AnalysisRetryResult>> {
    if (!validMailId(mailId)) return Promise.resolve(analysisFailure('invalid_request'));
    return this.request(`/mails/${encodeURIComponent(mailId)}/analysis/retry`, value => parseRetryResult(value, mailId), 'POST');
  }
}
