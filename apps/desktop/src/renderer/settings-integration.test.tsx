import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { App } from './app';
import { SyntheticF2Client } from '../../tests/f2-harness/synthetic-client';

const session = { email: 'owner@example.invalid', user_id: 'user-test', account_id: 'account-test', sync_started_at: '2026-11-19T00:00:00+09:00' };
afterEach(() => { vi.unstubAllGlobals(); window.location.hash = ''; });
function connected() {
  const calendarStatus = vi.fn().mockResolvedValue({ ok: true, data: { status: 'calendar_not_connected', email: session.email, calendars: [] } });
  vi.stubGlobal('klover', { mail: { session: vi.fn().mockResolvedValue({ ok: true, data: session }) }, suggestions: { calendarStatus, disconnectCalendar: vi.fn(), connectCalendar: vi.fn() } });
  return calendarStatus;
}
it('인증된 설정에서 개인정보·캘린더·주간 보고로 이동하고 미구현 항목은 잠근다', async () => {
  const calendarStatus = connected();
  const client = new SyntheticF2Client();
  window.location.hash = '/settings/profile';
  const view = render(<App f2Client={client} />);
  await screen.findByDisplayValue('홍길동');
  expect(screen.getByRole('button', { name: /알림·시작 프로그램/ })).toBeDisabled();
  expect(screen.getByRole('button', { name: /메일 계정 연결/ })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: '개인정보·학습 데이터' }));
  await screen.findByRole('heading', { name: '개인정보·학습 데이터' });
  fireEvent.click(screen.getByRole('button', { name: '‹ 내 프로필·문체' }));
  await screen.findByDisplayValue('홍길동');
  fireEvent.click(screen.getByRole('button', { name: '캘린더 연결' }));
  await screen.findByRole('heading', { name: 'Google Calendar 연결' });
  expect(calendarStatus).toHaveBeenCalledTimes(1);
  view.unmount();
  window.location.hash = '/settings/profile';
  render(<App f2Client={client} />);
  await screen.findByDisplayValue('홍길동');
  fireEvent.click(screen.getByRole('button', { name: '주간 보고' }));
  await screen.findByRole('region', { name: '주간 보고' });
  expect(window.location.hash).toBe('#/report/weekly');
});
it.each(['/settings/privacy', '/settings/calendar'])('연결 확인 없이 %s 화면을 열 수 없다', async path => {
  window.location.hash = path;
  render(<App />);
  await screen.findByRole('heading', { name: 'Gmail 계정 연결' });
  expect(window.location.hash).toBe('#/onboarding/1');
});
