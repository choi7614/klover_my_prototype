import { describe, expect, it, vi } from 'vitest';
import fixture from '../../../../../../fixtures/reports/F4-weekly-report.json';
import { createWeeklyReportIPCClient, unavailableWeeklyReportClient } from './ipc-client';
import type { WeeklyReportDocument, WeeklyReportIPC, WeeklyReportOptions } from './types';

function bridge(): WeeklyReportIPC {
  const document = fixture.document as WeeklyReportDocument;
  return {
    options: vi.fn(async () => ({ ok: true as const, data: fixture.options as WeeklyReportOptions })),
    generate: vi.fn(async () => ({ ok: true as const, data: document })),
    get: vi.fn(async () => ({ ok: true as const, data: document })),
    excluded: vi.fn(async () => ({ ok: true as const, data: [] })),
    save: vi.fn(async () => ({ ok: true as const, data: document })),
  };
}

describe('F4 기능 전송 포트', () => {
  it('정해진 다섯 동작만 전달하며 URL·인증·소유자는 전달하지 않는다', async () => {
    const native = bridge(); const client = createWeeklyReportIPCClient(native);
    await client.options(); await client.get('report-a'); await client.excluded('report-a');
    await client.generate({ start: '2026-10-05', end: '2026-10-09', template: 'profile', recipient: '팀장' });
    await client.save('report-a', 2, fixture.document.sections);
    expect(native.get).toHaveBeenCalledWith('report-a');
    expect(native.save).toHaveBeenCalledWith('report-a', 2, fixture.document.sections);
    expect(native.options).toHaveBeenCalledWith();
  });
  it('실패는 화면의 편집 보존 안내로 전달한다', async () => {
    const native = bridge(); native.get = async () => ({ ok: false, error: { code: 'report_conflict', message: '원문을 넘기지 않음' } });
    await expect(createWeeklyReportIPCClient(native).get('id')).rejects.toThrow('편집 내용을 보존');
  });
  it('연결 전에는 가짜 결과를 만들지 않는다', async () => {
    await expect(unavailableWeeklyReportClient.options()).rejects.toThrow('아직 준비되지');
  });
});
