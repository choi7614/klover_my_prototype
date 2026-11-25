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

describe('Calendar 연결 (메일 화면용 compact)', () => {
  const base = { email: 'synthetic@example.invalid', calendars: [] };
  it('연결돼 있으면 메일 화면에 아무것도 보이지 않지만 상태는 알려 준다', async () => {
    const onChange = vi.fn();
    const client = { calendarStatus: vi.fn(async () => ({ ...base, status: 'connected' })), disconnectCalendar: vi.fn() };
    const { container } = render(<CalendarConnectionPanel compact client={client} onChange={onChange} />);
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ status: 'connected' })));
    expect(container).toBeEmptyDOMElement();
  });
  it('동의가 필요할 때만 짧은 안내와 버튼을 보여 주고 설명 문장은 줄인다', async () => {
    const client = { calendarStatus: vi.fn(async () => ({ ...base, status: 'calendar_not_connected' })), disconnectCalendar: vi.fn(), connectCalendar: vi.fn(async () => ({ status: 'opened' })) };
    render(<CalendarConnectionPanel compact client={client} />);
    await screen.findByText('캘린더 추가 동의가 필요해요.');
    expect(screen.getByRole('button', { name: 'Google Calendar 추가 동의' })).toBeInTheDocument();
    expect(screen.queryByText(/같은 Google 계정으로 추가 권한/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '캘린더 연결 해제' })).not.toBeInTheDocument();
  });
  it('확인에 실패하면 연결됨으로 보이지 않고 실패를 알린다', async () => {
    const client = { calendarStatus: vi.fn(async () => { throw new Error('connection'); }), disconnectCalendar: vi.fn() };
    render(<CalendarConnectionPanel compact client={client} />);
    await screen.findByText('캘린더 연결을 확인하지 못했어요.');
    expect(screen.queryByText('캘린더 연결됨')).not.toBeInTheDocument();
  });
});
