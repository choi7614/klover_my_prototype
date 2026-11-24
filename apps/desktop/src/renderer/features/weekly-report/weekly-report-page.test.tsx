import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import fixture from '../../../../../../fixtures/reports/F4-weekly-report.json';
import { createWeeklyReportClient, draftIsValid, WeeklyReportClientError } from './client';
import type { ExcludedMail, ReportSection, WeeklyReportDocument, WeeklyReportOptions } from './types';
import { WeeklyReportPage } from './weekly-report-page';

const document = fixture.document as WeeklyReportDocument;
const options = fixture.options as WeeklyReportOptions;
function client() {
  return {
    options: vi.fn(async () => structuredClone(options)),
    generate: vi.fn(async (request: import('./types').GenerateReportRequest) => { void request; return structuredClone(document); }),
    get: vi.fn(async () => structuredClone(document)),
    excluded: vi.fn(async () => structuredClone(fixture.excluded) as ExcludedMail[]),
    save: vi.fn(async (_id: string, revision: number, sections: ReportSection[]) => ({
      ...structuredClone(document), revision: revision + 1, sections,
    })),
  };
}
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
});
async function ready() { return screen.findByLabelText('항목 내용 1-1'); }

describe('S08 기능 화면', () => {
  it('프로필 기본값·근거·포함 범위·제외 목록을 표시한다', async () => {
    const api = client();
    render(<WeeklyReportPage client={api} />);
    await ready();
    expect(screen.getByLabelText('시작일')).toHaveValue('2026-10-05');
    expect(screen.getByLabelText('보고 대상')).toHaveValue('이수진 팀장');
    expect(screen.getByText('12건')).toBeInTheDocument();
    expect(screen.getByText('9건 (6개 업무)')).toBeInTheDocument();
    expect(screen.getByText(/검토용 테스트 대역/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '항목 1-1 근거 3개' }));
    const aside = screen.getByRole('complementary');
    fireEvent.click(within(aside).getByRole('button', { name: /^3분기 결산 자료 확인 요청/ }));
    expect(await screen.findByRole('dialog', { name: '근거 메일 원문' })).toHaveTextContent('3분기 결산 1차 마감을 위해');
    fireEvent.click(screen.getByRole('button', { name: '닫기' }));
    fireEvent.click(screen.getByRole('button', { name: '제외된 메일 보기 ›' }));
    expect(await screen.findByRole('dialog', { name: '제외된 메일' })).toHaveTextContent('주간 금융 브리프 구독 메일');
  });

  it('저장 전 편집 내용이 복사에 반영된다', async () => {
    const write = vi.fn(async () => {});
    render(<WeeklyReportPage client={client()} writeClipboard={write} />);
    fireEvent.change(await ready(), { target: { value: '사용자가 수정한 보고 문장' } });
    fireEvent.click(screen.getByRole('button', { name: '복사' }));
    await waitFor(() => expect(write).toHaveBeenCalledWith(expect.stringContaining('사용자가 수정한 보고 문장')));
    expect(screen.getByLabelText('항목 내용 1-1')).toHaveValue('사용자가 수정한 보고 문장');
  });

  it('편집을 저장하고 반환된 저장본을 표시한다', async () => {
    const api = client();
    render(<WeeklyReportPage client={api} />);
    fireEvent.change(await ready(), { target: { value: '수정한 업무' } });
    fireEvent.click(screen.getByRole('button', { name: '변경 내용 저장' }));
    await screen.findByText('편집한 내용을 저장했습니다.');
    expect(api.save).toHaveBeenCalledWith(document.report_id, 1, expect.any(Array));
    expect(screen.getByText('저장본 · 버전 2')).toBeInTheDocument();
  });

  it('저장 실패 시 입력을 보존한다', async () => {
    const api = client(); api.save.mockRejectedValue(new WeeklyReportClientError('report_conflict'));
    render(<WeeklyReportPage client={api} />);
    fireEvent.change(await ready(), { target: { value: '보존할 편집본' } });
    fireEvent.click(screen.getByRole('button', { name: '변경 내용 저장' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('저장본이 변경');
    expect(screen.getByLabelText('항목 내용 1-1')).toHaveValue('보존할 편집본');
  });

  it('수정 후 재생성은 확인하며 취소는 요청을 보내지 않는다', async () => {
    const api = client(); render(<WeeklyReportPage client={api} />);
    fireEvent.change(await ready(), { target: { value: '편집 유지' } });
    fireEvent.click(screen.getByRole('button', { name: '다시 만들기' }));
    expect(screen.getByRole('dialog', { name: '다시 만들기 전 확인' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '편집 계속하기' }));
    expect(api.generate).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('항목 내용 1-1')).toHaveValue('편집 유지');
  });

  it.each(['ai_failed', 'invalid_evidence', 'analysis_not_ready'])('재생성 %s 오류가 나도 편집본을 보존한다', async (code) => {
    const api = client(); api.generate.mockResolvedValueOnce(structuredClone(document)).mockRejectedValue(new WeeklyReportClientError(code));
    render(<WeeklyReportPage client={api} />);
    fireEvent.change(await ready(), { target: { value: '실패 시에도 남을 문장' } });
    fireEvent.click(screen.getByRole('button', { name: '다시 만들기' }));
    fireEvent.click(screen.getByRole('button', { name: '계속 진행' }));
    await screen.findByRole('alert');
    expect(screen.getByLabelText('항목 내용 1-1')).toHaveValue('실패 시에도 남을 문장');
    expect(api.generate).toHaveBeenLastCalledWith(expect.objectContaining({ regenerate: true, expected_revision: 1 }));
  });

  it('근거가 없는 새 항목은 저장하지 못한다', async () => {
    const api = client(); render(<WeeklyReportPage client={api} />); await ready();
    fireEvent.click(screen.getAllByRole('button', { name: '항목 추가' })[0]);
    const textbox = screen.getByLabelText('항목 내용 1-7');
    fireEvent.change(textbox, { target: { value: '새 항목' } });
    expect(screen.getByRole('button', { name: '변경 내용 저장' })).toBeDisabled();
    fireEvent.click(screen.getByText('근거 메일 변경'));
    fireEvent.click(screen.getAllByRole('checkbox')[0]);
    expect(screen.getByRole('button', { name: '변경 내용 저장' })).toBeEnabled();
    fireEvent.keyDown(textbox, { key: 'Enter' });
    await waitFor(() => expect(api.save).toHaveBeenCalled());
  });

  it('다른 기간을 여는 요청이 실패하면 원래 보고서와 편집본이 남는다', async () => {
    const api = client(); api.generate.mockResolvedValueOnce(structuredClone(document)).mockRejectedValue(new WeeklyReportClientError('ai_failed'));
    render(<WeeklyReportPage client={api} />);
    fireEvent.change(await ready(), { target: { value: '기간 변경 전 편집' } });
    fireEvent.change(screen.getByLabelText('시작일'), { target: { value: '2026-10-12' } });
    fireEvent.change(screen.getByLabelText('종료일'), { target: { value: '2026-10-16' } });
    fireEvent.click(screen.getByRole('button', { name: '보고서 열기' }));
    fireEvent.click(screen.getByRole('button', { name: '계속 진행' }));
    await screen.findByRole('alert');
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('10/05 – 10/09');
    expect(screen.getByLabelText('항목 내용 1-1')).toHaveValue('기간 변경 전 편집');
  });

  it('프로필이 없으면 기본 프로필을 꾸며내지 않는다', async () => {
    const api = client(); api.options.mockResolvedValue({ ...options, profile: null });
    render(<WeeklyReportPage client={api} />);
    await screen.findByText('주간 보고 프로필이 없습니다');
    expect(api.generate).not.toHaveBeenCalled();
  });

  it('F2에 보고 대상이 비어 있으면 입력받은 뒤 생성한다', async () => {
    const api = client();
    api.options.mockResolvedValue({ ...options, profile: { ...options.profile!, report_recipient: '' } });
    render(<WeeklyReportPage client={api} />);
    await screen.findByText('보고 대상을 입력해 주세요');
    expect(api.generate).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: '보고서 열기' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('보고 대상'), { target: { value: '직접 입력한 팀장' } });
    fireEvent.click(screen.getByRole('button', { name: '보고서 열기' }));
    await ready();
    expect(api.generate).toHaveBeenCalledWith(expect.objectContaining({ recipient: '직접 입력한 팀장' }));
  });

  it('기간 대기 표시로 첫 주 사용을 막지 않고 생성 버튼을 제공한다', async () => {
    const api = client(); api.options.mockResolvedValue({ ...options, remaining_days: 3 });
    render(<WeeklyReportPage client={api} autoGenerate={false} />);
    await screen.findByText('보고서를 만들 준비가 됐어요');
    expect(screen.queryByText(/사용 1주 후부터/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '보고서 열기' })).toBeEnabled();
  });

  it('빈 메일 상태에서도 포함 범위를 표시한다', async () => {
    const api = client(); api.generate.mockResolvedValue({ ...document, status: 'empty', generation: 'none', evidence_mails: [], sections: document.sections.map((section) => ({ ...section, items: [] })), scope: { total: 0, grouped: 0, excluded: 0, groups: 0 } });
    render(<WeeklyReportPage client={api} />);
    await screen.findByText('이 기간에 주고받은 업무 메일이 없어요');
    expect(screen.getByText('0건 (0개 업무)')).toBeInTheDocument();
  });

  it('클립보드 실패도 편집 내용을 보존한다', async () => {
    render(<WeeklyReportPage client={client()} writeClipboard={async () => { throw new Error(); }} />);
    fireEvent.change(await ready(), { target: { value: '클립보드 실패 전 편집' } });
    fireEvent.click(screen.getByRole('button', { name: '복사' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('클립보드 권한');
    expect(screen.getByLabelText('항목 내용 1-1')).toHaveValue('클립보드 실패 전 편집');
  });

  it('계정 전송 포트가 바뀌면 이전 요청의 늦은 결과를 표시하지 않는다', async () => {
    const previous = client();
    let finish: (value: WeeklyReportDocument) => void = () => {};
    previous.save.mockImplementationOnce(() => new Promise((resolve) => { finish = resolve; }));
    const view = render(<WeeklyReportPage client={previous} />);
    fireEvent.change(await ready(), { target: { value: '이전 계정의 편집본' } });
    fireEvent.click(screen.getByRole('button', { name: '변경 내용 저장' }));
    const next = client(); next.options.mockResolvedValue({ ...options, profile: null });
    view.rerender(<WeeklyReportPage client={next} />);
    await screen.findByText('주간 보고 프로필이 없습니다');
    finish({ ...document, title: '이전 계정 결과' });
    await waitFor(() => expect(screen.queryByText('이전 계정 결과')).not.toBeInTheDocument());
    expect(screen.queryByLabelText('항목 내용 1-1')).not.toBeInTheDocument();
  });
});

it('기능 전송 포트는 소유자를 보내지 않고 상대 경로만 사용한다', async () => {
  const transport = vi.fn(async () => ({ status: 200, body: document }));
  const api = createWeeklyReportClient(transport);
  await api.save('report-id', 1, document.sections);
  expect(transport).toHaveBeenCalledWith({ method: 'PATCH', path: '/reports/weekly/report-id', body: { expected_revision: 1, sections: document.sections } });
});

it('잘못된 근거와 비어 있는 본문은 클라이언트에서도 저장을 막는다', () => {
  const sections = structuredClone(document.sections);
  sections[0].items[0].evidence = ['other-user'];
  expect(draftIsValid(document, sections)).toBe(false);
  sections[0].items[0].evidence = ['f4-01']; sections[0].items[0].text = ' ';
  expect(draftIsValid(document, sections)).toBe(false);
});


it('첫 주 일부 기간 안내와 선택한 보고서 AI를 전달한다', async () => {
  const api = client();
  api.generate.mockResolvedValue({ ...structuredClone(document), partial_period: true });
  render(<WeeklyReportPage client={api} />);
  await ready();
  expect(screen.getByText(/일부 기간 자료 ·/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('이번 요청의 AI'), { target: { value: 'claude' } });
  fireEvent.click(screen.getByRole('button', { name: '보고서 열기' }));
  await waitFor(() => expect(api.generate).toHaveBeenCalledTimes(2));
  expect(api.generate.mock.calls[1][0]).toMatchObject({ ai_provider: 'claude' });
});


it('앱에서는 보고서 화면 진입만으로 외부 AI를 호출하지 않는다', async () => {
  const api = client();
  render(<WeeklyReportPage client={api} autoGenerate={false} />);
  await screen.findByText('보고서를 만들 준비가 됐어요');
  expect(api.generate).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('이번 요청의 AI'), { target: { value: 'claude' } });
  fireEvent.click(screen.getByRole('button', { name: '보고서 열기' }));
  await waitFor(() => expect(api.generate).toHaveBeenCalledWith(expect.objectContaining({ ai_provider: 'claude' })));
});

it('화면을 나갔다 돌아오면 같은 계정 편집본을 복원하고 다른 계정에는 노출하지 않는다', async () => {
  const api = client();
  const view = render(<WeeklyReportPage client={api} draftScope="user:account-a" />);
  fireEvent.change(await ready(), { target: { value: '이동 전 편집 내용' } });
  view.unmount();
  const other = render(<WeeklyReportPage client={api} draftScope="user:account-b" autoGenerate={false} />);
  await screen.findByText('보고서를 만들 준비가 됐어요');
  expect(screen.queryByDisplayValue('이동 전 편집 내용')).not.toBeInTheDocument();
  other.unmount();
  render(<WeeklyReportPage client={api} draftScope="user:account-a" autoGenerate={false} />);
  expect(await ready()).toHaveValue('이동 전 편집 내용');
  expect(api.generate).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: '변경 내용 저장' }));
  await screen.findByText('편집한 내용을 저장했습니다.');
});

it('보고서에서 프로필·AI 설정과 받은편지함으로 이동할 수 있다', async () => {
  render(<WeeklyReportPage client={client()} autoGenerate={false} />);
  await screen.findByText('보고서를 만들 준비가 됐어요');
  expect(screen.getByRole('link', { name: '프로필·보고 양식 설정' })).toHaveAttribute('href', '#/settings/profile');
  expect(within(screen.getByRole('navigation', { name: '주간 보고 이동' })).getByRole('link', { name: 'AI 설정' })).toHaveAttribute('href', '#/settings/ai');
  expect(screen.getByRole('link', { name: '받은편지함' })).toHaveAttribute('href', '#/mail/inbox');
});

it('복귀 시 옵션 조회 실패에도 근거 없는 편집 항목을 보존하고 저장을 막는다', async () => {
  const api = client();
  const view = render(<WeeklyReportPage client={api} draftScope="offline:account" />);
  await ready();
  fireEvent.click(screen.getAllByRole('button', { name: '항목 추가' })[0]);
  view.unmount();
  api.options.mockRejectedValue(new WeeklyReportClientError('unreachable'));
  render(<WeeklyReportPage client={api} draftScope="offline:account" autoGenerate={false} />);
  await screen.findByText(/화면 이동 전 편집본을 복원/);
  await waitFor(() => expect(screen.getByRole('button', { name: '변경 내용 저장' })).toBeDisabled());
  expect(screen.getAllByRole('textbox', { name: /^항목 내용/ })).toHaveLength(document.sections.flatMap(s => s.items).length + 1);
});

it('같은 화면에서 계정이 바뀌어도 이전 편집본을 새 계정 캐시에 저장하지 않는다', async () => {
  const api = client();
  const view = render(<WeeklyReportPage client={api} draftScope="switch:account-a" />);
  fireEvent.change(await ready(), { target: { value: '이전 계정 비공개 편집본' } });
  view.rerender(<WeeklyReportPage client={api} draftScope="switch:account-b" autoGenerate={false} />);
  await screen.findByText('보고서를 만들 준비가 됐어요');
  view.unmount();
  render(<WeeklyReportPage client={api} draftScope="switch:account-b" autoGenerate={false} />);
  await waitFor(() => expect(screen.queryByDisplayValue('이전 계정 비공개 편집본')).not.toBeInTheDocument());
});
