import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { MailSuggestions } from './mail-suggestions';
import { syntheticBody, SyntheticSuggestionsClient } from './testing/synthetic-client';
import type { F5Client } from './types';

function client(list: F5Client['list']): F5Client & { calls: unknown[] } {
  const base = new SyntheticSuggestionsClient();
  return Object.assign(base, {
    list, todos: vi.fn(), createTodo: vi.fn(), updateTodo: vi.fn(),
  }) as unknown as F5Client & { calls: unknown[] };
}

describe('S04 메일 읽기 제안 진입', () => {
  it('해당 메일의 제안만 조회해 패널로 보여 주고, 버튼 전에는 실행하지 않는다', async () => {
    const rows = new SyntheticSuggestionsClient().rows;
    const list = vi.fn(async () => ({ items: [...rows, { ...rows[0], suggestion_id: 'other', mail_id: 'other-mail' }], next_cursor: null }));
    const value = client(list);
    render(<MailSuggestions mailId="synthetic-mail" body={syntheticBody} client={value}
      header={<h2>합성 제목</h2>} fallback={<p>기본 본문</p>} />);
    expect(await screen.findByRole('heading', { name: 'AI 제안 3건' })).toBeInTheDocument();
    expect(list).toHaveBeenCalledWith({ mail_id: 'synthetic-mail', limit: 50 });
    expect(screen.getByRole('heading', { name: '합성 제목' })).toBeInTheDocument();
    expect(screen.queryByText('기본 본문')).not.toBeInTheDocument();
    // 캘린더·답장 초안은 연결 전이라 승인 버튼이 꺼져 있다.
    expect(screen.getByRole('button', { name: '캘린더에 추가' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '회신 초안 만들기' })).toBeDisabled();
    expect(value.calls).toEqual([]);
  });
  it('제안이 없으면 기존 S03 모양을 유지한다', async () => {
    const list = vi.fn(async () => ({ items: [], next_cursor: null }));
    render(<MailSuggestions mailId="synthetic-mail" body={syntheticBody} client={client(list)} fallback={<p>기본 본문</p>} />);
    await waitFor(() => expect(list).toHaveBeenCalled());
    expect(screen.getByText('기본 본문')).toBeInTheDocument();
    expect(screen.queryByRole('complementary', { name: 'AI 제안' })).not.toBeInTheDocument();
  });
  it('조회 실패 때도 본문은 보이고 안내만 한다', async () => {
    const list = vi.fn(async () => { throw new Error('connection'); });
    render(<MailSuggestions mailId="synthetic-mail" body={syntheticBody} client={client(list)} fallback={<p>기본 본문</p>} />);
    expect(await screen.findByText('AI 제안을 불러오지 못했어요. 메일 본문은 그대로 볼 수 있어요.')).toBeInTheDocument();
    expect(screen.getByText('기본 본문')).toBeInTheDocument();
  });
});
