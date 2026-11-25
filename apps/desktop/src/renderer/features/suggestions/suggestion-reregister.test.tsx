import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SuggestionCard } from './suggestion-card';
import { syntheticSuggestions } from './testing/synthetic-client';
import type { Suggestion } from './types';

// 실제로 등록이 끝난 일정 제안(합성)
function registered(externalId = 'event-1', version = 4): Suggestion {
  const base = syntheticSuggestions()[0];
  return { ...base, status: 'approved', execution_status: 'succeeded', execution_mode: 'live',
    result: { mode: 'live', external_id: externalId }, version, resolved_at: '2026-11-19T00:00:00Z' } as Suggestion;
}

function setup(client: Record<string, unknown>, row = registered()) {
  const onChange = vi.fn();
  render(<SuggestionCard suggestion={row} client={client as never} onChange={onChange} onActive={() => undefined} calendarReady calendars={[{ id: 'synthetic-work', label: '업무' }]} />);
  return onChange;
}

describe('지운 일정 다시 추가', () => {
  it('완료한 일정에 다시 추가 버튼이 있고, 누르면 현재 version으로 한 번만 요청한다', async () => {
    const next = registered('event-2', 5);
    const reregister = vi.fn(async () => next);
    const onChange = setup({ reregister, get: vi.fn(), approve: vi.fn(), dismiss: vi.fn(), conflicts: vi.fn() });
    expect(screen.getByText('✓ 캘린더에 추가했어요')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '다시 추가' }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith(next));
    expect(reregister).toHaveBeenCalledTimes(1);
    expect(reregister).toHaveBeenCalledWith('synthetic-calendar', { version: 4 });
    expect(screen.getByText(/다시 추가했어요/)).toBeInTheDocument();
  });

  it('캘린더에 일정이 아직 있으면 서버 거절을 쉬운 말로 알리고 새로 만들지 않는다', async () => {
    const reregister = vi.fn(async () => { throw new Error('calendar_event_exists'); });
    const get = vi.fn(async () => registered());
    const onChange = setup({ reregister, get, approve: vi.fn(), dismiss: vi.fn(), conflicts: vi.fn() });
    fireEvent.click(screen.getByRole('button', { name: '다시 추가' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('아직 구글 캘린더에 이 일정이 있어요');
    expect(screen.getByText('✓ 캘린더에 추가했어요')).toBeInTheDocument();
    await waitFor(() => expect(get).toHaveBeenCalled());
    expect(onChange).toHaveBeenCalledTimes(1); // 최신 상태 다시 읽기만, 다시 등록 성공 처리 아님
  });

  it('서버가 실제 등록을 확인해 주지 않은 응답은 성공으로 표시하지 않는다', async () => {
    const fake = { ...registered('event-2', 5), execution_mode: 'test', result: { mode: 'test', external_id: 'event-2' } };
    const reregister = vi.fn(async () => fake as Suggestion);
    setup({ reregister, get: vi.fn(async () => registered()), approve: vi.fn(), dismiss: vi.fn(), conflicts: vi.fn() });
    fireEvent.click(screen.getByRole('button', { name: '다시 추가' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText(/다시 추가했어요/)).not.toBeInTheDocument();
  });

  it('다시 추가 기능이 없는 연결이면 버튼을 보여 주지 않는다', () => {
    setup({ get: vi.fn(), approve: vi.fn(), dismiss: vi.fn(), conflicts: vi.fn() });
    expect(screen.queryByRole('button', { name: '다시 추가' })).not.toBeInTheDocument();
  });
});
