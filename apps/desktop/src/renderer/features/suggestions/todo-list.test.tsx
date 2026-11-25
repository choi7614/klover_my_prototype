import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { dueLabel, TodoListPage } from './todo-list';
import type { F5Client, Todo } from './types';

const todo = (id: string, extra: Partial<Todo> = {}): Todo => ({
  todo_id: id, mail_id: 'synthetic-mail', suggestion_id: null, title: `합성 할 일 ${id}`, due: '2026-11-20',
  status: 'open', version: 1, created_at: '2026-11-19T00:00:00Z', ...extra,
} as Todo);

function client(overrides: Partial<F5Client> = {}): F5Client {
  return {
    list: vi.fn(), get: vi.fn(), approve: vi.fn(), dismiss: vi.fn(), conflicts: vi.fn(),
    todos: vi.fn(async query => ({ items: query.status === 'completed' ? [todo('c1', { status: 'completed' })] : [todo('t1'), todo('t2', { due: null, mail_id: null })], next_cursor: null })),
    createTodo: vi.fn(async request => todo('new', { title: request.title, due: request.due ?? null, mail_id: null })),
    updateTodo: vi.fn(async (id, request) => todo(id, { status: request.status, version: 2 })),
    ...overrides,
  } as F5Client;
}

describe('할 일 목록', () => {
  it('마감 날짜를 요일과 함께 보여 준다', () => {
    expect(dueLabel('2026-11-20')).toBe('마감 11/20(금)');
    expect(dueLabel(null)).toBe('마감 없음');
  });
  it('진행 중 목록을 보여 주고 완료 표시는 version과 함께 보낸다', async () => {
    const value = client();
    render(<TodoListPage client={value} />);
    expect(await screen.findByText('합성 할 일 t1')).toBeInTheDocument();
    expect(value.todos).toHaveBeenCalledWith({ status: 'open', limit: 50 });
    expect(screen.getByText('마감 11/20(금)')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: '근거 메일' })[0]).toHaveAttribute('href', '#/mail/inbox/synthetic-mail');
    fireEvent.click(screen.getByRole('checkbox', { name: '합성 할 일 t1 완료로 표시' }));
    expect(await screen.findByRole('status')).toHaveTextContent('삭제된 것이 아니라');
    // 삭제처럼 사라지지 않고 그 자리에 줄긋기로 남는다.
    expect(screen.getByText('합성 할 일 t1')).toHaveClass('line-through');
    expect(screen.getByRole('checkbox', { name: '합성 할 일 t1 진행 중으로 되돌리기' })).toBeChecked();
    expect(value.updateTodo).toHaveBeenCalledWith('t1', { version: 1, status: 'completed' });
  });
  it('완료한 할 일은 체크를 다시 눌러 진행 중으로 되돌릴 수 있다', async () => {
    const value = client();
    render(<TodoListPage client={value} />);
    await screen.findByText('합성 할 일 t1');
    fireEvent.click(screen.getByRole('checkbox', { name: '합성 할 일 t1 완료로 표시' }));
    fireEvent.click(await screen.findByRole('checkbox', { name: '합성 할 일 t1 진행 중으로 되돌리기' }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('진행 중으로 되돌렸어요'));
    expect(screen.getByText('합성 할 일 t1')).not.toHaveClass('line-through');
  });
  it('완료 탭을 따로 불러오고, 직접 추가는 버튼을 눌렀을 때만 요청한다', async () => {
    const value = client();
    render(<TodoListPage client={value} />);
    await screen.findByText('합성 할 일 t1');
    expect(value.createTodo).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText('제목'), { target: { value: '  새 합성 할 일 ' } });
    fireEvent.click(screen.getByRole('button', { name: '+ 할 일 추가' }));
    expect(await screen.findByText('새 합성 할 일')).toBeInTheDocument();
    expect(value.createTodo).toHaveBeenCalledWith(expect.objectContaining({ title: '새 합성 할 일', due: null, request_id: expect.stringMatching(/^[A-Za-z0-9_-]+$/) }));
    fireEvent.click(screen.getByRole('tab', { name: '완료' }));
    expect(await screen.findByText('합성 할 일 c1')).toBeInTheDocument();
    expect(value.todos).toHaveBeenLastCalledWith({ status: 'completed', limit: 50 });
  });
  it('통로가 없거나 실패하면 안내한다', async () => {
    render(<TodoListPage client={client({ todos: vi.fn(async () => { throw new Error('suggestions_unavailable'); }) })} />);
    expect(await screen.findByRole('alert')).toHaveTextContent('할 일 서버 연결을 준비 중이에요.');
  });
});
