import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { CalendarConnectionPanel } from './calendar-connection';

describe('Calendar 연결', () => {
  it('계정·권한 오류와 명시적 동의·해제를 구분하고 승인하지 않는다', async () => {
    const state = { status: 'connected', email: 'synthetic@example.invalid', calendars: [{ id: 'cal', label: '업무', timezone: 'Asia/Seoul' }] };
    const client = { calendarStatus: vi.fn(async () => state), disconnectCalendar: vi.fn(async () => ({ ...state, status: 'calendar_not_connected', calendars: [] })), connectCalendar: vi.fn(async () => ({ status: 'opened' })) };
    render(<CalendarConnectionPanel client={client} />);
    await screen.findByText('synthetic@example.invalid');
    expect(screen.getByText('업무 · cal · Asia/Seoul')).toBeInTheDocument();
    expect(client.connectCalendar).not.toHaveBeenCalled();
    expect(client.disconnectCalendar).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Google Calendar 추가 동의' }));
    await waitFor(() => expect(client.connectCalendar).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByRole('button', { name: '캘린더 연결 해제' })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: '캘린더 연결 해제' }));
    await screen.findByText('캘린더 추가 동의가 필요해요.');
    expect(client.disconnectCalendar).toHaveBeenCalledTimes(1);
  });
  it('실패를 연결 성공으로 표시하지 않는다', async () => {
    const client = { calendarStatus: vi.fn(async () => { throw new Error('connection'); }), disconnectCalendar: vi.fn() };
    render(<CalendarConnectionPanel client={client} />);
    await screen.findByRole('alert');
    expect(screen.queryByText('캘린더 연결됨')).not.toBeInTheDocument();
  });
});
