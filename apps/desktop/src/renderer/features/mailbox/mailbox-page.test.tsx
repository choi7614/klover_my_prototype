import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { MailboxPage } from './mailbox-page';
import { MailboxRoute, SearchRoute, unavailableSearchClient } from './routes';
import { App } from '@/app';
import { mailFailure, validSyncResult, type MailDetail, type MailResult, type MailReadBridge, type MailSummary, type MailSyncResult } from '../../../shared/mail-read';

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

describe('새로고침: Gmail 새 메일 가져오기 → 목록 다시 읽기 (합성 응답)', () => {
  function syncing(result: MailResult<MailSyncResult> | Promise<MailResult<MailSyncResult>>) {
    return { ...api(), sync: vi.fn().mockImplementation(() => Promise.resolve(result)) };
  }
  it('가져오기 성공 후 목록을 처음부터 다시 읽고 가져온 건수를 알린다', async () => {
    const bridge = syncing({ ok: true, data: { saved: 2, skipped: 0, mode: 'history', token_refreshed: false } });
    render(<MailboxPage api={bridge} session={session} onDisconnected={vi.fn()} />);
    await screen.findByRole('button', { name: /합성 제목 mail-1/ });
    expect(screen.getByText(/새로고침하면 Gmail에서 새 메일을 가져옵니다/)).toBeInTheDocument();
    bridge.inbox.mockResolvedValueOnce({ ok: true, data: { items: [mail('mail-new'), mail()], next_cursor: null } });
    fireEvent.click(screen.getByRole('button', { name: '목록 새로고침' }));
    await screen.findByText('새 메일 2건을 가져왔습니다.');
    await screen.findByRole('button', { name: /합성 제목 mail-new/ });
    expect(bridge.sync).toHaveBeenCalledTimes(1);
    expect(bridge.inbox).toHaveBeenLastCalledWith({ limit: 20, cursor: null });
    expect(bridge.sync.mock.invocationCallOrder[0]).toBeLessThan(bridge.inbox.mock.invocationCallOrder[1]);
  });
  it('새 메일이 없으면 없다고 알린다', async () => {
    const bridge = syncing({ ok: true, data: { saved: 0, skipped: 3, mode: 'history', token_refreshed: true } });
    render(<MailboxPage api={bridge} session={session} onDisconnected={vi.fn()} />);
    await screen.findByRole('button', { name: /합성 제목 mail-1/ });
    fireEvent.click(screen.getByRole('button', { name: '목록 새로고침' }));
    await screen.findByText('새로 도착한 메일이 없습니다.');
  });
  it('가져오는 동안 진행 중을 표시하고 버튼을 잠가 중복 요청을 막는다', async () => {
    let finish: (value: MailResult<MailSyncResult>) => void = () => undefined;
    const bridge = syncing(new Promise(resolve => { finish = resolve; }));
    render(<MailboxPage api={bridge} session={session} onDisconnected={vi.fn()} />);
    await screen.findByRole('button', { name: /합성 제목 mail-1/ });
    const button = screen.getByRole('button', { name: '목록 새로고침' });
    fireEvent.click(button);
    expect(await screen.findByText('Gmail에서 새 메일 확인 중…')).toBeInTheDocument();
    expect(button).toBeDisabled();
    fireEvent.click(button);
    expect(bridge.sync).toHaveBeenCalledTimes(1);
    await act(async () => finish({ ok: true, data: { saved: 0, skipped: 0, mode: 'initial', token_refreshed: false } }));
    await waitFor(() => expect(button).not.toBeDisabled());
    expect(screen.queryByText('Gmail에서 새 메일 확인 중…')).not.toBeInTheDocument();
  });
  it('실패하면 기존 목록을 유지하고 오류와 다시 시도를 보여 준다', async () => {
    const bridge = syncing(mailFailure('gmail_unavailable'));
    render(<MailboxPage api={bridge} session={session} onDisconnected={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: /합성 제목 mail-1/ }));
    await screen.findByTestId('mail-text-body');
    fireEvent.click(screen.getByRole('button', { name: '목록 새로고침' }));
    expect(await screen.findByText(/Gmail에서 새 메일을 가져오지 못했습니다/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /합성 제목 mail-1/ })).toBeInTheDocument();
    expect(screen.getByTestId('mail-text-body')).toBeInTheDocument();
    expect(bridge.inbox).toHaveBeenCalledTimes(1);
    bridge.sync.mockResolvedValueOnce({ ok: true, data: { saved: 1, skipped: 0, mode: 'history', token_refreshed: false } });
    fireEvent.click(screen.getByRole('button', { name: '새 메일 다시 가져오기' }));
    await screen.findByText('새 메일 1건을 가져왔습니다.');
    expect(screen.queryByText(/Gmail에서 새 메일을 가져오지 못했습니다/)).not.toBeInTheDocument();
    expect(bridge.inbox).toHaveBeenCalledTimes(2);
  });
  it('이미 가져오는 중이면 그 안내를 보여 준다', async () => {
    const bridge = syncing(mailFailure('sync_in_progress'));
    render(<MailboxPage api={bridge} session={session} onDisconnected={vi.fn()} />);
    await screen.findByRole('button', { name: /합성 제목 mail-1/ });
    fireEvent.click(screen.getByRole('button', { name: '목록 새로고침' }));
    expect(await screen.findByText(/이미 새 메일을 가져오고 있습니다/)).toBeInTheDocument();
  });
  it('인증 실패는 연결 해제로 넘긴다', async () => {
    const bridge = syncing(mailFailure('unauthorized'));
    const disconnected = vi.fn();
    render(<MailboxPage api={bridge} session={session} onDisconnected={disconnected} />);
    await screen.findByRole('button', { name: /합성 제목 mail-1/ });
    fireEvent.click(screen.getByRole('button', { name: '목록 새로고침' }));
    await waitFor(() => expect(disconnected).toHaveBeenCalledWith(expect.objectContaining({ code: 'unauthorized' })));
  });
  it('가져오기 연결이 없으면 저장된 목록만 다시 읽고 그렇게 안내한다', async () => {
    const bridge = api();
    render(<MailboxPage api={bridge} session={session} onDisconnected={vi.fn()} />);
    expect(await screen.findByText(/Gmail 가져오기 연결 준비 중/)).toBeInTheDocument();
    await screen.findByRole('button', { name: /합성 제목 mail-1/ });
    fireEvent.click(screen.getByRole('button', { name: '목록 새로고침' }));
    await waitFor(() => expect(bridge.inbox).toHaveBeenCalledTimes(2));
  });
  it('서버 응답 형식 검사', () => {
    expect(validSyncResult({ saved: 1, skipped: 0, mode: 'history', token_refreshed: false })).toBe(true);
    expect(validSyncResult({ saved: -1, skipped: 0, mode: 'history', token_refreshed: false })).toBe(false);
    expect(validSyncResult({ saved: 1, skipped: 0, mode: 'other', token_refreshed: false })).toBe(false);
    expect(validSyncResult(null)).toBe(false);
  });
});

describe('F2·F3 화면 진입 (S03)', () => {
  it('사이드바 설정은 프로필 화면으로, 메일 읽기의 답장 초안 버튼은 해당 메일 초안 화면으로 간다', async () => {
    render(<MailboxPage api={api()} session={session} onDisconnected={vi.fn()} />);
    expect(screen.getByRole('link', { name: '설정' })).toHaveAttribute('href', '#/settings/profile');
    expect(screen.queryByRole('link', { name: /답장 초안 만들기/ })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: /합성 제목 mail-1/ }));
    expect(await screen.findByRole('link', { name: /답장 초안 만들기/ })).toHaveAttribute('href', '#/reply/mail-1');
  });
  it('상단 검색창은 Ctrl K로 포커스되고 Enter로 검색 화면에 질문을 넘긴다', async () => {
    render(<MailboxPage api={api()} session={session} onDisconnected={vi.fn()} />);
    const input = screen.getByRole('searchbox', { name: '자연어 검색' });
    fireEvent.keyDown(window, { key: 'k', ctrlKey: true });
    expect(input).toHaveFocus();
    fireEvent.submit(input.closest('form')!);
    expect(window.location.hash).toBe('');
    fireEvent.change(input, { target: { value: '  지난주 예산 메일 & 첨부  ' } });
    fireEvent.submit(input.closest('form')!);
    expect(window.location.hash).toBe(`#/search?q=${encodeURIComponent('지난주 예산 메일 & 첨부')}`);
  });
  it('메일 경로로 들어오면 그 메일을 선택해 연다', async () => {
    const bridge = api();
    render(<MemoryRouter initialEntries={['/mail/inbox/mail-9']}><Routes>
      <Route path="/mail/inbox/:mailId?" element={<MailboxRoute api={bridge} session={session} onDisconnected={vi.fn()} />} />
    </Routes></MemoryRouter>);
    expect((await screen.findByTestId('mail-text-body')).textContent).toContain('합성 본문 mail-9');
    expect(bridge.detail).toHaveBeenCalledWith('mail-9');
  });
  it('검색 경로는 질문을 이어받고, 연결 전에는 가짜 결과 대신 준비 중을 알린다', async () => {
    render(<MemoryRouter initialEntries={[`/search?q=${encodeURIComponent('예산 메일')}`]}><Routes>
      <Route path="/search" element={<SearchRoute client={unavailableSearchClient} session={session} />} />
      <Route path="/mail/inbox" element={<p>받은편지함 화면</p>} />
    </Routes></MemoryRouter>);
    expect(await screen.findByDisplayValue('예산 메일')).toBeInTheDocument();
    expect(await screen.findByText(/검색 서버 연결을 준비 중이에요/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '받은편지함으로' }));
    expect(await screen.findByText('받은편지함 화면')).toBeInTheDocument();
  });
});
