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

it('설정 첫 화면에서 다섯 설정을 찾고 공통 메뉴에서 현재 위치를 확인한다', async () => {
  connected();
  window.location.hash = '/settings';
  render(<App f2Client={new SyntheticF2Client()} />);
  await screen.findByRole('heading', { name: /^설정$/ });
  for (const path of ['/settings/profile', '/settings/ai', '/settings/calendar', '/settings/mail-history', '/settings/privacy']) {
    expect(document.querySelector(`main a[href="#${path}"]`)).toBeInTheDocument();
  }
  fireEvent.click(document.querySelector('main a[href="#/settings/profile"]')!);
  await screen.findByDisplayValue('홍길동');
  fireEvent.click(screen.getByRole('button', { name: '설정 전체' }));
  await screen.findByRole('heading', { name: /^설정$/ });
});
it('프로필 편집 중 다른 설정 이동을 취소하면 편집값이 보존된다', async () => {
  connected();
  const confirmation = vi.spyOn(window, 'confirm').mockReturnValue(false);
  window.location.hash = '/settings/profile';
  render(<App f2Client={new SyntheticF2Client()} />);
  await screen.findByDisplayValue('홍길동');
  fireEvent.change(screen.getByLabelText('이름'), { target: { value: '저장 전 이름' } });
  fireEvent.click(screen.getByRole('button', { name: 'AI 설정' }));
  expect(confirmation).toHaveBeenCalled();
  expect(window.location.hash).toBe('#/settings/profile');
  expect(screen.getByLabelText('이름')).toHaveValue('저장 전 이름');
  confirmation.mockRestore();
});
