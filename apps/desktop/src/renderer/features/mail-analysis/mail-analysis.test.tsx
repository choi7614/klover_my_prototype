import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MailboxPage } from '../mailbox/mailbox-page';
import { AnalysisClientError, createAnalysisIPCClient, type MailAnalysisClient } from './client';
import { AiSummaryBox, dayDate, firstSentence, shortDate } from './analysis-view';
import { POLL_MS } from './use-mail-analysis';
import {
  analysisFailure, parseAnalysisBatch, parseRetryResult, validBatchIds,
  type AutoAnalysisState, type MailAnalysisView,
} from '../../../shared/f1-bridge';
import type { MailDetail, MailReadBridge, MailSummary } from '../../../shared/mail-read';

const session = { email: 'demo@example.invalid', user_id: 'user-test', account_id: 'account-test', sync_started_at: '2026-11-19T00:00:00+09:00' };
function mail(id: string): MailSummary {
  return { mail_id: id, subject: `합성 제목 ${id}`, from_addr: 'sender@example.invalid', from_name: '합성 발신자', received_at: '2026-11-19T01:00:00+09:00', is_read: false, analysis_status: 'pending', preview: `합성 미리보기 ${id}` };
}
function api(ids = ['mail-1', 'mail-2']) {
  return {
    session: vi.fn().mockResolvedValue({ ok: true, data: session }),
    inbox: vi.fn().mockResolvedValue({ ok: true, data: { items: ids.map(mail), next_cursor: null } }),
    detail: vi.fn().mockImplementation((id: string) => Promise.resolve({ ok: true, data: { ...mail(id), to: [], cc: [], body_text: `합성 본문 ${id}` } satisfies MailDetail })),
  } satisfies MailReadBridge;
}
function done(id: string, overrides: Partial<MailAnalysisView> = {}): MailAnalysisView {
  return {
    mail_id: id, analysis_status: 'done', category: 'work_request',
    summary: '영업기획팀이 예산 집행 현황 자료를 요청했습니다. 금요일까지 회신이 필요합니다.',
    needs_reply: true, action_items: [{ text: '집행 현황 자료 송부', due: '2026-10-16' }],
    priority: 'high', priority_reason: '팀장 참조', failure_code: null, ...overrides,
  };
}
function waiting(id: string, status: 'pending' | 'failed' = 'pending'): MailAnalysisView {
  return { mail_id: id, analysis_status: status, category: null, summary: null, needs_reply: null, action_items: [], priority: null, priority_reason: null, failure_code: status === 'failed' ? 'invalid_response' : null };
}
function client(items: MailAnalysisView[], auto: AutoAnalysisState = 'ready') {
  return {
    batch: vi.fn().mockImplementation((ids: string[]) => Promise.resolve({ items: items.filter(item => ids.includes(item.mail_id)), auto_analysis: auto })),
    retry: vi.fn().mockImplementation((id: string) => Promise.resolve({ mail_id: id, analysis_status: 'pending' as const })),
  } satisfies MailAnalysisClient;
}
const row = (id: string) => screen.findByRole('button', { name: new RegExp(`합성 제목 ${id}`) });

afterEach(() => { vi.useRealTimers(); });

describe('F1 받은편지함 분류·요약 표시 (합성 응답)', () => {
  it.each([
    ['invalid_response', 'AI 응답의 형식 또는 근거 위치를 검증하지 못했어요.'],
    ['provider_error', '로컬 AI 호출에 실패했어요. 연결 또는 응답 시간을 확인해 주세요.'],
    ['embedding_error', '검색용 데이터 생성에 실패했어요. 로컬 임베딩 모델 설정을 확인해 주세요.'],
    ['input_too_large', '메일이 자동 분석 길이 제한을 초과했어요. 원문은 그대로 읽을 수 있어요.'],
    ['private-provider-response', '분석 실패 원인을 확인하지 못했어요. 원문은 그대로 읽을 수 있어요.'],
    ['__proto__', '분석 실패 원인을 확인하지 못했어요. 원문은 그대로 읽을 수 있어요.'],
    [null, '분석 실패 원인을 확인하지 못했어요. 원문은 그대로 읽을 수 있어요.'],
  ])('실패 사유 %s는 고정 안내로 표시하고 임의 응답은 노출하지 않는다', (code, text) => {
    render(<AiSummaryBox view={{ ...waiting('mail-1', 'failed'), failure_code: code }} state="ready" onRetry={vi.fn()} retryNotice={null} />);
    expect(screen.getByTestId('ai-summary-failed')).toHaveTextContent(text!);
    expect(screen.queryByText('private-provider-response')).not.toBeInTheDocument();
    expect(screen.queryByText('__proto__')).not.toBeInTheDocument();
  });

  it('목록에 ◆ 요약 첫 문장과 분류·회신 필요·마감 태그를, 읽기 영역에 AI 요약 박스를 보여 준다', async () => {
    const analysis = client([done('mail-1'), done('mail-2', { category: 'newsletter', needs_reply: false, action_items: [] })]);
    render(<MailboxPage api={api()} session={session} onDisconnected={vi.fn()} analysis={analysis} />);
    const first = await row('mail-1');
    await within(first).findByText('영업기획팀이 예산 집행 현황 자료를 요청했습니다.');
    expect(within(first).getByText('업무 요청').className).toContain('bg-cat-work-bg');
    expect(within(first).getByText('회신 필요').className).toContain('bg-danger-subtle');
    expect(within(first).getByText('마감 10/16').className).toContain('bg-warning-subtle');
    expect(within(first).queryByText('합성 미리보기 mail-1')).not.toBeInTheDocument();
    const second = await row('mail-2');
    expect(within(second).getByText('뉴스레터·광고').className).toContain('bg-cat-newsletter-bg');
    expect(within(second).queryByText('회신 필요')).not.toBeInTheDocument();
    expect(analysis.batch).toHaveBeenCalledWith(['mail-1', 'mail-2']);

    fireEvent.click(first);
    const box = await screen.findByTestId('ai-summary-box');
    expect(box).toHaveTextContent('◆ AI 요약');
    expect(box).toHaveTextContent('금요일까지 회신이 필요합니다.');
    expect(box).toHaveTextContent('내가 할 일 집행 현황 자료 송부');
    expect(box).toHaveTextContent('마감 10/16(금)');
    expect(box).toHaveTextContent('우선순위 높음 · 팀장 참조');
    expect(screen.getByText('분류').parentElement ?? screen.getByText('분류')).toBeInTheDocument();
    expect(await screen.findByTestId('mail-text-body')).toHaveTextContent('합성 본문 mail-1');
  });

  it('분석 중이면 대기 문구와 태그 자리를 보이고, 완료되면 다시 확인해 채운다', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const analysis = client([waiting('mail-1'), waiting('mail-2')]);
    render(<MailboxPage api={api()} session={session} onDisconnected={vi.fn()} analysis={analysis} />);
    const first = await row('mail-1');
    await within(first).findByText('AI가 분석하고 있어요…');
    expect(within(first).getByText('합성 미리보기 mail-1')).toBeInTheDocument();
    fireEvent.click(first);
    expect(await screen.findByTestId('ai-summary-loading')).toBeInTheDocument();

    analysis.batch.mockImplementation((ids: string[]) => Promise.resolve({ items: ids.map(id => done(id)), auto_analysis: 'ready' }));
    await act(async () => { await vi.advanceTimersByTimeAsync(POLL_MS + 10); });
    await within(first).findByText('영업기획팀이 예산 집행 현황 자료를 요청했습니다.');
    expect(await screen.findByTestId('ai-summary-box')).toBeInTheDocument();
    const calls = analysis.batch.mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(POLL_MS * 3); });
    expect(analysis.batch.mock.calls.length).toBe(calls); // 모두 끝나면 더 묻지 않는다
  });

  it('AI 미설정·외부 AI면 가짜 요약 없이 대기 이유를 알리고 다시 묻지 않는다', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    for (const [auto, text] of [
      ['not_configured', 'AI 연결 전이라 분석을 기다리고 있어요'],
      ['external_blocked', '외부 AI 설정이라 실제 메일은 분석하지 않아요'],
    ] as const) {
      const analysis = client([waiting('mail-1')], auto);
      const view = render(<MailboxPage api={api(['mail-1'])} session={session} onDisconnected={vi.fn()} analysis={analysis} />);
      const first = await row('mail-1');
      await within(first).findByText(text);
      fireEvent.click(first);
      expect(await screen.findByTestId('ai-summary-waiting')).toHaveTextContent('원문은 아래에 그대로 있어요');
      await act(async () => { await vi.advanceTimersByTimeAsync(POLL_MS * 2); });
      expect(analysis.batch.mock.calls.every(([ids]) => ids.includes('mail-1'))).toBe(true);
      expect(analysis.batch).toHaveBeenCalledTimes(1); // 목록에 있는 메일 선택은 다시 묻지 않고, 반복 확인도 없다
      view.unmount();
    }
  });

  it('실패하면 "요약을 만들지 못했어요 · 다시 시도"를 보이고 다시 시도하면 분석 대기로 바뀐다', async () => {
    const analysis = client([waiting('mail-1', 'failed')]);
    render(<MailboxPage api={api(['mail-1'])} session={session} onDisconnected={vi.fn()} analysis={analysis} />);
    const first = await row('mail-1');
    await within(first).findByText('요약을 만들지 못했어요');
    fireEvent.click(first);
    const failed = await screen.findByTestId('ai-summary-failed');
    expect(await screen.findByTestId('mail-text-body')).toHaveTextContent('합성 본문 mail-1');
    analysis.batch.mockImplementation((ids: string[]) => Promise.resolve({ items: ids.map(id => waiting(id)), auto_analysis: 'ready' }));
    fireEvent.click(within(failed).getByRole('button', { name: '다시 시도' }));
    await waitFor(() => expect(analysis.retry).toHaveBeenCalledWith('mail-1'));
    expect(await screen.findByTestId('ai-summary-loading')).toBeInTheDocument();
  });

  it('다시 시도가 거절되면 이유를 보여 주고, AI 미연결이면 버튼을 잠근다', async () => {
    const analysis = client([waiting('mail-1', 'failed')]);
    analysis.retry.mockRejectedValueOnce(new AnalysisClientError('analysis_unavailable', 'AI가 연결되지 않아 지금은 다시 분석할 수 없습니다.'));
    const view = render(<MailboxPage api={api(['mail-1'])} session={session} onDisconnected={vi.fn()} analysis={analysis} />);
    fireEvent.click(await row('mail-1'));
    fireEvent.click(within(await screen.findByTestId('ai-summary-failed')).getByRole('button', { name: '다시 시도' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('AI가 연결되지 않아');
    view.unmount();

    render(<MailboxPage api={api(['mail-1'])} session={session} onDisconnected={vi.fn()} analysis={client([waiting('mail-1', 'failed')], 'not_configured')} />);
    fireEvent.click(await row('mail-1'));
    expect(within(await screen.findByTestId('ai-summary-failed')).getByRole('button', { name: '다시 시도' })).toBeDisabled();
  });

  it('다른 메일의 결과는 붙이지 않고, 조회 실패 때는 미리보기를 그대로 둔다', async () => {
    const analysis = client([done('other-mail')]);
    render(<MailboxPage api={api(['mail-1'])} session={session} onDisconnected={vi.fn()} analysis={analysis} />);
    const first = await row('mail-1');
    await waitFor(() => expect(analysis.batch).toHaveBeenCalled());
    expect(within(first).getByText('합성 미리보기 mail-1')).toBeInTheDocument();
    expect(within(first).queryByText('업무 요청')).not.toBeInTheDocument();

    const broken = client([]);
    broken.batch.mockRejectedValue(new AnalysisClientError('connection', 'x'));
    render(<MailboxPage api={api(['mail-9'])} session={session} onDisconnected={vi.fn()} analysis={broken} />);
    expect(within(await row('mail-9')).getByText('합성 미리보기 mail-9')).toBeInTheDocument();
  });

  it('통로가 없으면 기존 목록 모양 그대로다', async () => {
    render(<MailboxPage api={api(['mail-1'])} session={session} onDisconnected={vi.fn()} />);
    expect(within(await row('mail-1')).getByText('합성 미리보기 mail-1')).toBeInTheDocument();
    expect(screen.queryByText(/AI가 분석하고 있어요/)).not.toBeInTheDocument();
  });
});

describe('F1 통로 계약', () => {
  it('묶음 응답은 요청한 메일만 받고 예상 밖 필드를 버린다', () => {
    const parsed = parseAnalysisBatch({ items: [{ ...done('mail-1'), body_text: '원문', llm_model: 'x' }], auto_analysis: 'ready' }, ['mail-1']);
    expect(parsed.items[0]).toEqual(done('mail-1'));
    expect(() => parseAnalysisBatch({ items: [done('mail-2')], auto_analysis: 'ready' }, ['mail-1'])).toThrow();
    expect(() => parseAnalysisBatch({ items: [], auto_analysis: 'on' }, ['mail-1'])).toThrow();
    expect(() => parseAnalysisBatch({ items: [{ ...done('mail-1'), category: '스팸' }], auto_analysis: 'ready' }, ['mail-1'])).toThrow();
    expect(() => parseAnalysisBatch({ items: [done('mail-1', { action_items: [{ text: 'x', due: '10/16' }] })], auto_analysis: 'ready' }, ['mail-1'])).toThrow();
    expect(parseRetryResult({ mail_id: 'mail-1', analysis_status: 'pending' }, 'mail-1')).toEqual({ mail_id: 'mail-1', analysis_status: 'pending' });
    expect(() => parseRetryResult({ mail_id: 'mail-2', analysis_status: 'pending' }, 'mail-1')).toThrow();
    expect(validBatchIds(['mail-1'])).toBe(true);
    expect(validBatchIds([])).toBe(false);
    expect(validBatchIds(['../x'])).toBe(false);
    expect(validBatchIds(Array.from({ length: 101 }, (_, index) => `m${index}`))).toBe(false);
  });

  it('IPC 결과를 화면 오류로 바꾼다', async () => {
    const ipc = createAnalysisIPCClient({
      batch: vi.fn().mockResolvedValue(analysisFailure('connection')),
      retry: vi.fn().mockRejectedValue(new Error('boom')),
    });
    await expect(ipc.batch(['mail-1'])).rejects.toMatchObject({ code: 'connection' });
    await expect(ipc.retry('mail-1')).rejects.toMatchObject({ code: 'connection' });
  });

  it('날짜·요약 표시 형식', () => {
    expect(shortDate('2026-10-16')).toBe('10/16');
    expect(dayDate('2026-10-16')).toBe('10/16(금)');
    expect(firstSentence('첫 문장입니다. 둘째 문장.')).toBe('첫 문장입니다.');
    expect(firstSentence('마침표 없는 요약')).toBe('마침표 없는 요약');
  });
});
