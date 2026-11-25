import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { HistoryPage } from './history-page';
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });
it('기간 선택·명시적 시작·진행·중단을 연결한다', async () => {
  let jobs: unknown[] = [];
  const history = {
    list: vi.fn(async () => ({ ok: true, data: jobs })),
    start: vi.fn(async () => { jobs = [{ job_id: 'synthetic', start: '2020-01-01', end: '2020-01-03', status: 'running', saved: 1, skipped: 0, processed: 1 }]; return { ok: true, data: jobs[0] }; }),
    action: vi.fn(async () => ({ ok: true, data: {} })),
  };
  vi.stubGlobal('klover', { history }); vi.spyOn(window, 'confirm').mockReturnValue(true);
  render(<HistoryPage />);
  await waitFor(() => expect(history.list).toHaveBeenCalled());
  expect(history.start).not.toHaveBeenCalled();
  expect(screen.getByRole('button', { name: '선택 기간 가져오기' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('가져오기 시작일'), { target: { value: '2020-01-01' } });
  fireEvent.change(screen.getByLabelText('가져오기 종료일'), { target: { value: '2020-01-03' } });
  fireEvent.click(screen.getByRole('button', { name: '선택 기간 가져오기' }));
  await screen.findByText(/새 저장 1건/);
  expect(history.start).toHaveBeenCalledWith({ start: '2020-01-01', end: '2020-01-03' });
  fireEvent.click(screen.getByRole('button', { name: '중단' }));
  await waitFor(() => expect(history.action).toHaveBeenCalledWith('synthetic', 'pause'));
});
it('시작 확인 취소는 수집 요청을 만들지 않는다', async () => {
  const start = vi.fn(); vi.stubGlobal('klover', { history: { list: async () => ({ ok: true, data: [] }), start } });
  vi.spyOn(window, 'confirm').mockReturnValue(false); render(<HistoryPage />);
  fireEvent.change(screen.getByLabelText('가져오기 시작일'), { target: { value: '2020-01-01' } });
  fireEvent.change(screen.getByLabelText('가져오기 종료일'), { target: { value: '2020-01-03' } });
  fireEvent.click(screen.getByRole('button', { name: '선택 기간 가져오기' }));
  expect(start).not.toHaveBeenCalled();
});
