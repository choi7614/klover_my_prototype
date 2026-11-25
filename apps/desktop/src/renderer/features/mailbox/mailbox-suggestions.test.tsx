import { fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MailboxPage } from './mailbox-page';
import { App } from '@/app';
import { syntheticBody, syntheticSuggestions } from '../suggestions/testing/synthetic-client';
import type { F5Client } from '../suggestions/types';
import type { MailReadBridge, MailSummary } from '../../../shared/mail-read';

const session = { email: 'demo@example.invalid', user_id: 'user-test', account_id: 'account-test', sync_started_at: '2026-11-19T00:00:00+09:00' };
const summary: MailSummary = { mail_id: 'synthetic-mail', subject: '합성 결산 회의', from_addr: 'sender@example.invalid', from_name: '합성 발신자', received_at: '2026-11-19T01:00:00+09:00', is_read: false, analysis_status: 'done', preview: '합성 미리보기' };
function api() {
  return {
    session: vi.fn().mockResolvedValue({ ok: true, data: session }),
    inbox: vi.fn().mockResolvedValue({ ok: true, data: { items: [summary], next_cursor: null } }),
    detail: vi.fn().mockResolvedValue({ ok: true, data: { ...summary, to: [], cc: [], body_text: syntheticBody } }),
  } satisfies MailReadBridge;
}
function f5(items = syntheticSuggestions()): F5Client {
  return {
    list: vi.fn(async () => ({ items, next_cursor: null })), get: vi.fn(), approve: vi.fn(), dismiss: vi.fn(), conflicts: vi.fn(),
    todos: vi.fn(async () => ({ items: [], next_cursor: null })), createTodo: vi.fn(), updateTodo: vi.fn(),
  } as unknown as F5Client;
}
afterEach(() => { Reflect.deleteProperty(window, 'klover'); window.location.hash = ''; });

describe('F5 메일 읽기·할 일 진입 (합성 응답)', () => {
  it('제안이 있는 메일은 메일 머리와 제안 패널을 함께 보여 주고 자동 실행하지 않는다', async () => {
    const client = f5();
    render(<MailboxPage api={api()} session={session} onDisconnected={vi.fn()} suggestions={client} />);
    fireEvent.click(await screen.findByRole('button', { name: /합성 결산 회의/ }));
    expect(await screen.findByRole('complementary', { name: 'AI 제안' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '합성 결산 회의' })).toBeInTheDocument();
    expect(client.list).toHaveBeenCalledWith({ mail_id: 'synthetic-mail', limit: 50 });
    expect(client.approve).not.toHaveBeenCalled();
    expect(client.dismiss).not.toHaveBeenCalled();
    expect(screen.getByRole('link', { name: '할 일' })).toHaveAttribute('href', '#/todos');
  });
  it('제안이 없으면 기존 S03 본문 모양을 유지한다', async () => {
    render(<MailboxPage api={api()} session={session} onDisconnected={vi.fn()} suggestions={f5([])} />);
    fireEvent.click(await screen.findByRole('button', { name: /합성 결산 회의/ }));
    expect(await screen.findByTestId('mail-text-body')).toBeInTheDocument();
    expect(screen.queryByRole('complementary', { name: 'AI 제안' })).not.toBeInTheDocument();
  });
  it('F5 통로가 없어도 할 일 경로는 준비 중 안내를 보여 준다', async () => {
    Object.defineProperty(window, 'klover', { configurable: true, value: { platform: 'test', mail: api() } });
    window.location.hash = '#/todos';
    render(<App />);
    expect(await screen.findByRole('heading', { name: '할 일' })).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toHaveTextContent('할 일 서버 연결을 준비 중이에요.');
  });
});
