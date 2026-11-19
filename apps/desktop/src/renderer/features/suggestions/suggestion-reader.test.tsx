import { useState } from 'react';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { SuggestionReader } from './suggestion-reader';
import { syntheticBody, syntheticSuggestions, SyntheticSuggestionsClient } from './testing/synthetic-client';
import type { ConflictResult, Suggestion } from './types';

function Harness({ client, initial = syntheticSuggestions(), ready = true, body = syntheticBody }: {
  client: SyntheticSuggestionsClient; initial?: Suggestion[]; ready?: boolean; body?: string;
}) {
  const [rows, setRows] = useState(initial);
  return <SuggestionReader mailId="synthetic-mail" body={body} suggestions={rows} client={client}
    calendarReady={ready} calendars={[{ id: 'synthetic-work', label: '업무 (합성 캘린더)' }]}
    onChange={row => setRows(current => current.map(item => item.suggestion_id === row.suggestion_id ? row : item))} />;
}

describe('S04 기능 전용 제안 화면', () => {
  it('버튼 전에는 실행하지 않고 수정한 제목·일시·장소를 승인에 전달한다', async () => {
    const client = new SyntheticSuggestionsClient();
    render(<Harness client={client} />);
    expect(client.calls).toEqual([]);
    const card = within(screen.getByTestId('suggestion-calendar'));
    fireEvent.change(card.getByLabelText('제목'), { target: { value: '수정한 합성 제목' } });
    fireEvent.change(card.getByLabelText('시작 (한국 시간)'), { target: { value: '2026-11-20T14:30' } });
    fireEvent.change(card.getByLabelText('장소'), { target: { value: '바꾼 합성 장소' } });
    fireEvent.click(card.getByRole('button', { name: '캘린더에 추가' }));
    await screen.findByText('테스트 실행을 확인했어요. 실제 캘린더에는 등록하지 않았어요.');
    expect(client.calls[0].payload).toMatchObject({ title: '수정한 합성 제목', start: '2026-11-20T14:30:00+09:00', location: '바꾼 합성 장소' });
    expect(screen.queryByText('✓ 캘린더에 추가했어요')).not.toBeInTheDocument();
  });

  it('연결되지 않은 캘린더·답장 초안 승인을 차단한다', () => {
    const client = new SyntheticSuggestionsClient();
    render(<Harness client={client} ready={false} />);
    expect(screen.getByRole('button', { name: '캘린더에 추가' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '◆ 회신 초안 만들기' })).toBeDisabled();
    expect(client.calls).toEqual([]);
  });

  it('실패를 표시하고 원문을 보존하며 재시도 후 테스트 결과만 표시한다', async () => {
    const client = new SyntheticSuggestionsClient();
    client.failApprovals = true;
    render(<Harness client={client} />);
    fireEvent.click(screen.getByRole('button', { name: '캘린더에 추가' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('처리하지 못했어요');
    expect(screen.getByTestId('mail-evidence')).toHaveTextContent('합성 메일입니다.');
    client.failApprovals = false;
    fireEvent.click(screen.getByRole('button', { name: '캘린더에 추가' }));
    await screen.findByText('테스트 실행을 확인했어요. 실제 캘린더에는 등록하지 않았어요.');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('무시는 해당 카드만 접고 새 승인을 실행하지 않는다', async () => {
    const client = new SyntheticSuggestionsClient();
    render(<Harness client={client} />);
    fireEvent.click(within(screen.getByTestId('suggestion-todo')).getByRole('button', { name: '무시' }));
    await screen.findByText('무시함');
    expect(client.calls).toEqual([{ action: 'dismiss', id: 'synthetic-todo' }]);
    expect(within(screen.getByTestId('suggestion-todo')).queryByRole('button')).not.toBeInTheDocument();
  });

  it('이모지를 포함한 코드 포인트 근거를 강조하고 키보드 포커스와 연결한다', () => {
    render(<Harness client={new SyntheticSuggestionsClient()} />);
    const quote = screen.getByText('📅 11월 20일 오후 2시에 테스트 회의를 합니다.');
    expect(quote.tagName).toBe('MARK');
    fireEvent.focus(within(screen.getByTestId('suggestion-calendar')).getByLabelText('제목'));
    expect(quote).toHaveAttribute('data-active', 'true');
    expect(screen.getByTestId('mail-evidence').querySelector('script')).toBeNull();
    expect(screen.getByTestId('mail-evidence')).toHaveTextContent('<script>실행하면 안 되는 합성 텍스트</script>');
  });

  it('잘못된 근거는 강조·승인하지 않고 빈 제안은 패널을 숨긴다', () => {
    const client = new SyntheticSuggestionsClient();
    const rows = syntheticSuggestions().slice(0, 1);
    rows[0].evidence_spans[0].start += 1;
    const view = render(<Harness client={client} initial={rows} />);
    expect(screen.getByRole('alert')).toHaveTextContent('근거를 확인하지 못했어요');
    expect(screen.getByRole('button', { name: '캘린더에 추가' })).toBeDisabled();
    expect(screen.getByTestId('mail-evidence').querySelector('mark')).toBeNull();
    view.unmount();
    render(<Harness client={client} initial={[]} />);
    expect(screen.queryByRole('complementary', { name: 'AI 제안' })).not.toBeInTheDocument();
  });

  it('겹침을 조회한 뒤 일시를 고치면 이전 경고를 지운다', async () => {
    const client = new SyntheticSuggestionsClient();
    render(<Harness client={client} />);
    fireEvent.click(screen.getByRole('button', { name: '겹치는 일정 확인' }));
    await screen.findByText('같은 시간에 1건의 일정이 있습니다.');
    fireEvent.change(screen.getByLabelText('시작 (한국 시간)'), { target: { value: '2026-11-20T14:30' } });
    expect(screen.queryByText('같은 시간에 1건의 일정이 있습니다.')).not.toBeInTheDocument();
    expect(client.calls.every(call => call.action === 'conflicts')).toBe(true);
  });

  it('수정 전의 늦은 겹침 응답은 화면에 반영하지 않는다', async () => {
    const client = new SyntheticSuggestionsClient();
    let resolve!: (value: ConflictResult) => void;
    vi.spyOn(client, 'conflicts').mockImplementation(() => new Promise(done => { resolve = done; }));
    render(<Harness client={client} />);
    fireEvent.click(screen.getByRole('button', { name: '겹치는 일정 확인' }));
    fireEvent.change(screen.getByLabelText('장소'), { target: { value: '바꾼 장소' } });
    await act(async () => resolve({ status: 'checked', request_hash: 'stale', mode: 'test', conflicts: [{ start: '2026-11-20T05:00Z', end: '2026-11-20T06:00Z' }] }));
    expect(screen.queryByText(/같은 시간에/)).not.toBeInTheDocument();
  });

  it('중복 클릭은 하나의 승인만 전송한다', async () => {
    const client = new SyntheticSuggestionsClient();
    let finish!: (row: Suggestion) => void;
    const approve = vi.spyOn(client, 'approve').mockImplementation(() => new Promise(resolve => { finish = resolve; }));
    render(<Harness client={client} />);
    const button = screen.getByRole('button', { name: '캘린더에 추가' });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(approve).toHaveBeenCalledTimes(1);
    await act(async () => finish(client.rows[0]));
    await waitFor(() => expect(button).not.toBeDisabled());
  });

  it('결과가 불명확하면 입력을 잠그고 같은 내용으로만 다시 확인한다', async () => {
    const client = new SyntheticSuggestionsClient();
    const rows = syntheticSuggestions();
    rows[0] = { ...rows[0], execution_status: 'uncertain', last_error: 'calendar_result_unknown' };
    client.rows = rows;
    render(<Harness client={client} initial={rows} />);
    const card = within(screen.getByTestId('suggestion-calendar'));
    expect(card.getByLabelText('제목')).toBeDisabled();
    expect(card.getByRole('button', { name: '무시' })).toBeDisabled();
    fireEvent.click(card.getByRole('button', { name: '등록 결과 다시 확인' }));
    await screen.findByText('테스트 실행을 확인했어요. 실제 캘린더에는 등록하지 않았어요.');
    expect(client.calls[0].payload).toEqual(rows[0].payload);
  });

  it('테스트 영수증에 approved가 잘못 붙어도 실제 등록 성공을 표시하지 않는다', () => {
    const client = new SyntheticSuggestionsClient();
    const rows = syntheticSuggestions();
    rows[0] = { ...rows[0], status: 'approved', execution_status: 'succeeded',
      execution_mode: 'test', result: { mode: 'test', external_id: 'synthetic-only' } };
    render(<Harness client={client} initial={rows} />);
    expect(screen.queryByText('✓ 캘린더에 추가했어요')).not.toBeInTheDocument();
    expect(client.calls).toEqual([]);
  });

  it('완료 영수증이 있는 내부 할 일만 추가 완료로 표시한다', () => {
    const client = new SyntheticSuggestionsClient();
    const rows = syntheticSuggestions();
    rows[1] = { ...rows[1], status: 'approved', execution_status: 'succeeded',
      execution_mode: 'internal', result: { mode: 'internal', todo_id: 'synthetic-todo-result' } };
    render(<Harness client={client} initial={rows} />);
    expect(screen.getByText('✓ 할 일에 추가했어요')).toBeVisible();
    expect(client.calls).toEqual([]);
  });
});
