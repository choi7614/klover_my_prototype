// 기능 전용 어댑터. 공통 main/preload는 patches/F4/ 적용 전까지 바꾸지 않는다.
import { WeeklyReportClientError } from './client';
import type { WeeklyReportBridgeResult, WeeklyReportClient, WeeklyReportIPC } from './types';

async function unwrap<T>(pending: Promise<WeeklyReportBridgeResult<T>>): Promise<T> {
  let result: WeeklyReportBridgeResult<T>;
  try { result = await pending; }
  catch { throw new WeeklyReportClientError('unreachable'); }
  if (!result || typeof result !== 'object') throw new WeeklyReportClientError('invalid_response');
  if (!result.ok) throw new WeeklyReportClientError(result.error.code);
  return result.data;
}

export function createWeeklyReportIPCClient(bridge: WeeklyReportIPC): WeeklyReportClient {
  return {
    options: () => unwrap(bridge.options()),
    generate: (request) => unwrap(bridge.generate(request)),
    get: (id) => unwrap(bridge.get(id)),
    excluded: (id) => unwrap(bridge.excluded(id)),
    save: (id, revision, sections) => unwrap(bridge.save(id, revision, sections)),
  };
}

const unavailable = () => Promise.reject(new WeeklyReportClientError('report_unavailable'));
export const unavailableWeeklyReportClient: WeeklyReportClient = {
  options: unavailable, generate: unavailable, get: unavailable, excluded: unavailable, save: unavailable,
};
