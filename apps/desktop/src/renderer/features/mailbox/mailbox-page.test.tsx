import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MailboxPage } from './mailbox-page';
import { App } from '@/app';
import { mailFailure, type MailDetail, type MailResult, type MailReadBridge, type MailSummary } from '../../../shared/mail-read';

const session = { email: 'demo@example.invalid', user_id: 'user-test', account_id: 'account-test', sync_started_at: '2026-11-19T00:00:00+09:00' };
function mail(id = 'mail-1'): MailSummary {
  return { mail_id: id, subject: `합성 제목 ${id}`, from_addr: 'sender@example.invalid', from_name: '합성 발신자', received_at: '2026-11-19T01:00:00+09:00', is_read: false, analysis_status: 'pending', preview: '합성 미리보기' };
}
function body(id = 'mail-1'): MailDetail { return { ...mail(id), to: [], cc: [], body_text: `합성 본문 ${id}\n<img src="https://outside.invalid/x"><script>bad()</script>` }; }
function api() {
  return {
    session: vi.fn().mockResolvedValue({ ok: true, data: session }),
    inbox: vi.fn().mockResolvedValue({ ok: true, data: { items: [mail()], next_cursor: null } }),
    detail: vi.fn().mockImplementation((id: string) => Promise.resolve({ ok: true, data: body(id) })),
  } satisfies MailReadBridge;
}
afterEach(() => {
  Reflect.deleteProperty(window, 'klover');
  window.location.hash = '';
});
describe('받은편지함 화면 (합성 API 응답)', () => {
  it('계정·목록·본문을 표시하고 HTML은 텍스트로만 보여 준다', async () => {
    const bridge = api();
    render(<MailboxPage api={bridge} session={session} onDisconnected={vi.fn()} />);
    expect(screen.getByText(session.email)).toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: /합성 제목 mail-1/ }));
    const text = await screen.findByTestId('mail-text-body');
    expect(text.textContent).toBe(body().body_text);
    expect(text.querySelector('img,script,iframe')).toBeNull();
    expect(screen.queryByText('바로 사용')).not.toBeInTheDocument();
    expect(screen.getByText(/프로필·알림 설정과 AI 기능은 아직 준비 중/)).toBeInTheDocument();
    expect(bridge.detail).toHaveBeenCalledWith('mail-1');
  });
  it('커서로 다음 페이지를 읽고 중복을 제거하며 새로고침 후 빈 목록을 표시한다', async () => {
    const bridge = api();
    bridge.inbox.mockResolvedValueOnce({ ok: true, data: { items: [mail()], next_cursor: 'next-page' } })
      .mockResolvedValueOnce({ ok: true, data: { items: [mail(), mail('mail-2')], next_cursor: null } })
      .mockResolvedValueOnce({ ok: true, data: { items: [], next_cursor: null } });
    render(<MailboxPage api={bridge} session={session} onDisconnected={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: '다음 페이지' }));
    await screen.findByRole('button', { name: /합성 제목 mail-2/ });
    expect(bridge.inbox).toHaveBeenNthCalledWith(2, { limit: 20, cursor: 'next-page' });
    expect(screen.getAllByRole('button', { name: /합성 제목 mail-1/ })).toHaveLength(1);
    expect(screen.queryByRole('button', { name: '다음 페이지' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '목록 새로고침' }));
    await screen.findByText('받은편지함이 비어 있습니다');
    expect(bridge.inbox).toHaveBeenLastCalledWith({ limit: 20, cursor: null });
    expect(screen.queryByText(/합성 제목 mail-/)).not.toBeInTheDocument();
  });
  it('목록 오류와 본문 404를 구분하고 다시 시도한다', async () => {
    const bridge = api();
    bridge.inbox.mockResolvedValueOnce(mailFailure('connection'));
    bridge.detail.mockResolvedValueOnce(mailFailure('not_found'));
    render(<MailboxPage api={bridge} session={session} onDisconnected={vi.fn()} />);
    await screen.findByRole('alert');
    expect(screen.queryByText('받은편지함이 비어 있습니다')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '목록 다시 시도' }));
    fireEvent.click(await screen.findByRole('button', { name: /합성 제목 mail-1/ }));
    await screen.findByText(/메일을 찾을 수 없습니다/);
    fireEvent.click(screen.getByRole('button', { name: '본문 다시 시도' }));
    await screen.findByTestId('mail-text-body');
  });
  it('느린 이전 메일 응답이 새로 선택한 본문을 덮어쓰지 않는다', async () => {
    const bridge = api();
    let oldResponse!: (value: MailResult<MailDetail>) => void;
    bridge.inbox.mockResolvedValue({ ok: true, data: { items: [mail(), mail('mail-2')], next_cursor: null } });
    bridge.detail.mockImplementationOnce(() => new Promise(resolve => { oldResponse = resolve; }));
    render(<MailboxPage api={bridge} session={session} onDisconnected={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: /합성 제목 mail-1/ }));
    fireEvent.click(screen.getByRole('button', { name: /합성 제목 mail-2/ }));
    await screen.findByTestId('mail-text-body');
    await act(async () => oldResponse({ ok: true, data: body() }));
    expect(screen.getByTestId('mail-text-body').textContent).toBe(body('mail-2').body_text);
  });
  it('인증 실패 시 이전 메일을 숨기고 기존 첫 실행 화면에서 재확인한다', async () => {
    const bridge = api();
    Object.defineProperty(window, 'klover', { configurable: true, value: { platform: 'test', mail: bridge } });
    window.location.hash = '/mail/inbox';
    render(<App />);
    await screen.findByRole('button', { name: /합성 제목 mail-1/ });
    bridge.inbox.mockResolvedValueOnce(mailFailure('unauthorized'));
    fireEvent.click(screen.getByRole('button', { name: '목록 새로고침' }));
    await screen.findByRole('heading', { name: 'Gmail 계정 연결' });
    expect(screen.queryByText(session.email)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '다음' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: '메일함 연결 다시 확인' }));
    await waitFor(() => expect(screen.getByText(session.email)).toBeInTheDocument());
  });
});
