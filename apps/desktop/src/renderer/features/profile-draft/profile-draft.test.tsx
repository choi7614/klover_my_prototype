import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { StrictMode } from 'react';
import { SyntheticF2Client, SYNTHETIC_MAIL } from '../../../../tests/f2-harness/synthetic-client';
import { ProfilePage } from './profile-page';
import { ReplyDraftPage } from './reply-draft-page';
import { EvidenceBody, preserveEvidence } from './evidence';
import type { Draft, Preview } from './contracts';

afterEach(() => vi.useRealTimers());

async function profilePage(client = new SyntheticF2Client(), confirm = vi.fn(() => true)) {
  const onExit = vi.fn();
  const view = render(<ProfilePage client={client} confirm={confirm} onExit={onExit} />);
  await screen.findByDisplayValue('홍길동');
  return { client, confirm, onExit, ...view };
}

async function replyPage(client = new SyntheticF2Client(), confirm = vi.fn(() => true)) {
  const onExit = vi.fn();
  const view = render(<ReplyDraftPage client={client} mailId={SYNTHETIC_MAIL.mail_id} confirm={confirm} onExit={onExit} />);
  await waitFor(() => expect((screen.getByLabelText('답장 본문') as HTMLTextAreaElement).value).toContain('합성 검사'));
  return { client, confirm, onExit, ...view };
}

describe('S09 프로필', () => {
  it('저장 전 취소는 서버를 수정하지 않는다', async () => {
    const { client } = await profilePage();
    const save = vi.spyOn(client, 'saveProfile');
    fireEvent.change(screen.getByLabelText('소속'), { target: { value: '저장 전 변경' } });
    fireEvent.click(screen.getByRole('button', { name: '취소' }));
    expect(screen.getByLabelText('소속')).toHaveValue('경영지원본부 재무팀');
    expect(save).not.toHaveBeenCalled();
  });

  it('입력·보고 순서를 저장하고 재조회한다', async () => {
    const { client, unmount } = await profilePage();
    const save = vi.spyOn(client, 'saveProfile');
    fireEvent.change(screen.getByLabelText('이름'), { target: { value: '변경 이름' } });
    fireEvent.change(screen.getByLabelText('격식 수준'), { target: { value: '90' } });
    fireEvent.click(screen.getByRole('radio', { name: '자세히' }));
    fireEvent.click(screen.getByRole('radio', { name: '서술형' }));
    fireEvent.click(screen.getByLabelText('이슈·요청사항 위로'));
    fireEvent.click(screen.getByRole('button', { name: '저장' }));
    await screen.findByText('저장했어요. 다음 초안부터 반영돼요.');
    expect(save.mock.calls[0][0]).toMatchObject({ expected_version: 1, profile: { name: '변경 이름', formality: 90, reply_length: 'long', report_style: 'prose', report_sections: ['highlights', 'issues', 'ongoing', 'next_week'] } });
    unmount();
    render(<ProfilePage client={client} onExit={vi.fn()} />);
    expect(await screen.findByDisplayValue('변경 이름')).toBeInTheDocument();
  });

  it('저장 전 나가기와 학습 동의를 명시적으로 확인한다', async () => {
    const { confirm, onExit } = await profilePage();
    confirm.mockReturnValue(false);
    fireEvent.change(screen.getByLabelText('이름'), { target: { value: '미저장' } });
    fireEvent.click(screen.getByRole('button', { name: '‹ 받은편지함' }));
    await waitFor(() => expect(confirm).toHaveBeenCalled());
    expect(onExit).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('switch', { name: '문체 학습 동의' }));
    expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'false');
    confirm.mockReturnValue(true);
    fireEvent.click(screen.getByRole('switch'));
    await waitFor(() => expect(screen.getByRole('switch')).toHaveAttribute('aria-checked', 'true'));
    expect(screen.getByText(/학습 연결 준비 중/)).toBeInTheDocument();
  });

  it('학습 삭제 후에도 저장하지 않은 기본 정보는 보존한다', async () => {
    const { client } = await profilePage();
    fireEvent.change(screen.getByLabelText('소속'), { target: { value: '편집 중 소속' } });
    fireEvent.click(screen.getByRole('button', { name: '학습 기록 삭제' }));
    await screen.findByText('학습 기록을 삭제하고 학습을 껐어요.');
    expect(screen.getByLabelText('소속')).toHaveValue('편집 중 소속');
    expect(client.state.profile.org).toBe('경영지원본부 재무팀');
  });

  it('저장 실패 때 편집값을 유지한다', async () => {
    const { client } = await profilePage();
    client.failSave = true;
    fireEvent.change(screen.getByLabelText('소속'), { target: { value: '보존할 소속' } });
    fireEvent.click(screen.getByRole('button', { name: '저장' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('합성 저장 실패');
    expect(screen.getByLabelText('소속')).toHaveValue('보존할 소속');
  });

  it('미리보기의 늦은 응답으로 새 설정을 덮어쓰지 않는다', async () => {
    const { client } = await profilePage();
    vi.useFakeTimers();
    let first: (v: Preview) => void = () => {};
    vi.spyOn(client, 'preview').mockImplementationOnce(() => new Promise(resolve => { first = resolve; }))
      .mockResolvedValueOnce({ body: '새 설정 미리보기', evidence: [] });
    fireEvent.change(screen.getByLabelText('첫 인사'), { target: { value: '첫 응답 대기' } });
    await act(async () => { vi.advanceTimersByTime(1000); });
    fireEvent.change(screen.getByLabelText('첫 인사'), { target: { value: '새 인사' } });
    await act(async () => { vi.advanceTimersByTime(1000); });
    expect(screen.getByText('새 설정 미리보기')).toBeInTheDocument();
    await act(async () => { first({ body: '오래된 미리보기', evidence: [] }); });
    expect(screen.queryByText('오래된 미리보기')).not.toBeInTheDocument();
  });
});

describe('S06 초안', () => {
  it('앱의 StrictMode에서도 최초 초안은 한 번만 생성한다', async () => {
    const client = new SyntheticF2Client();
    const create = vi.spyOn(client, 'createDraft');
    render(<StrictMode><ReplyDraftPage client={client} mailId={SYNTHETIC_MAIL.mail_id} onExit={vi.fn()} /></StrictMode>);
    await waitFor(() => expect((screen.getByLabelText('답장 본문') as HTMLTextAreaElement).value).toContain('합성 검사'));
    expect(create).toHaveBeenCalledTimes(1);
  });
  it('원문·방향·프로필 근거를 표시하고 발송을 비활성으로 둔다', async () => {
    const { container } = await replyPage();
    expect(screen.getByText(SYNTHETIC_MAIL.subject)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { pressed: false }).length).toBe(2);
    expect(container.querySelector('[data-source="profile.greeting"]')).toHaveTextContent('안녕하세요 🌿');
    expect(screen.queryByText(/참고한 메일:/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '보내기' })).toBeDisabled();
  });

  it('수정한 근거만 지우고 이모지 뒤 서명 밑줄은 유지한다', async () => {
    const { container } = await replyPage();
    const editor = screen.getByLabelText('답장 본문') as HTMLTextAreaElement;
    fireEvent.change(editor, { target: { value: editor.value.replace('안녕하세요', '반갑습니다') } });
    expect(container.querySelector('[data-source="profile.greeting"]')).not.toBeInTheDocument();
    expect(container.querySelector('[data-source="profile.signature"]')).toHaveTextContent('홍길동 과장');
  });

  it('편집 후 방향 변경을 취소하면 생성하지 않는다', async () => {
    const { client, confirm } = await replyPage();
    const revise = vi.spyOn(client, 'reviseDraft');
    fireEvent.change(screen.getByLabelText('답장 본문'), { target: { value: '사용자 편집 내용' } });
    confirm.mockReturnValue(false);
    fireEvent.click(screen.getByRole('button', { name: '기한 조정 요청' }));
    await waitFor(() => expect(confirm).toHaveBeenCalled());
    expect(revise).not.toHaveBeenCalled();
    expect(screen.getByLabelText('답장 본문')).toHaveValue('사용자 편집 내용');
  });

  it.each([['더 짧게', 'shorter'], ['더 정중하게', 'politer'], ['다시 쓰기', 'rewrite']] as const)('%s는 현재 편집 본문을 사용한다', async (label, action) => {
    const { client } = await replyPage();
    const revise = vi.spyOn(client, 'reviseDraft');
    fireEvent.change(screen.getByLabelText('답장 본문'), { target: { value: '반영할 편집 내용' } });
    fireEvent.click(screen.getByRole('button', { name: label }));
    await waitFor(() => expect(revise).toHaveBeenCalled());
    expect(revise.mock.calls[0][1]).toMatchObject({ body: '반영할 편집 내용', action, expected_version: 1 });
  });

  it('생성 실패 시 편집한 본문과 근거를 보존한다', async () => {
    const { client } = await replyPage();
    client.failAI = true;
    fireEvent.change(screen.getByLabelText('답장 본문'), { target: { value: '실패해도 남길 내용' } });
    fireEvent.click(screen.getByRole('button', { name: '다시 쓰기' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('AI 연결이 준비되지 않았어요');
    expect(screen.getByLabelText('답장 본문')).toHaveValue('실패해도 남길 내용');
  });

  it('생성 중에 입력한 편집을 늦은 생성 결과로 덮어쓰지 않는다', async () => {
    const { client } = await replyPage();
    let complete: (value: Draft) => void = () => {};
    const result = structuredClone(client.stored!);
    vi.spyOn(client, 'reviseDraft').mockImplementation(() => new Promise(resolve => { complete = resolve; }));
    fireEvent.click(screen.getByRole('button', { name: '다시 쓰기' }));
    fireEvent.change(screen.getByLabelText('답장 본문'), { target: { value: '대기 중 새로 입력한 내용' } });
    await act(async () => { complete({ ...result, body: '늦게 생성된 결과', version: 2 }); });
    expect(screen.getByLabelText('답장 본문')).toHaveValue('대기 중 새로 입력한 내용');
    expect(screen.getByRole('status')).toHaveTextContent('수정한 내용을 보존했어요');
  });

  it('나갈 때 임시 저장하며 저장 실패 시 화면을 유지한다', async () => {
    const { client, onExit } = await replyPage();
    client.failSave = true;
    fireEvent.change(screen.getByLabelText('답장 본문'), { target: { value: '임시 저장할 내용' } });
    fireEvent.click(screen.getByRole('button', { name: '‹ 받은편지함' }));
    await screen.findByText('합성 저장 실패');
    expect(onExit).not.toHaveBeenCalled();
    client.failSave = false;
    fireEvent.click(screen.getByRole('button', { name: '‹ 받은편지함' }));
    await waitFor(() => expect(onExit).toHaveBeenCalled());
    expect(client.stored?.body).toBe('임시 저장할 내용');
  });

  it('AI 미연결 시 가짜 성공 본문 대신 준비 부족과 직접 쓰기를 제공한다', async () => {
    const client = new SyntheticF2Client(); client.failAI = true;
    render(<ReplyDraftPage client={client} mailId={SYNTHETIC_MAIL.mail_id} onExit={vi.fn()} />);
    await screen.findByRole('alert');
    expect(screen.getByLabelText('답장 본문')).toHaveValue('');
    expect(screen.queryByText(/이 초안에 반영된 것/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '직접 쓰기' })).toBeEnabled();
  });

  it('임시 저장 ID가 있으면 새로 생성하지 않고 편집 본문을 다시 연다', async () => {
    const client = new SyntheticF2Client();
    const initial = await client.createDraft({ mail_id: SYNTHETIC_MAIL.mail_id });
    await client.saveDraft(initial.draft_id, { body: '임시 저장한 사용자 편집', expected_version: 1 });
    const create = vi.spyOn(client, 'createDraft');
    render(<ReplyDraftPage client={client} mailId={SYNTHETIC_MAIL.mail_id} draftId={initial.draft_id} onExit={vi.fn()} />);
    await waitFor(() => expect(screen.getByLabelText('답장 본문')).toHaveValue('임시 저장한 사용자 편집'));
    expect(create).not.toHaveBeenCalled();
  });

  it('참고한 메일의 제목·날짜와 일반 텍스트 미리보기를 제공한다', async () => {
    const client = new SyntheticF2Client();
    const initial = await client.createDraft({ mail_id: SYNTHETIC_MAIL.mail_id });
    initial.evidence = [{ span: [0, 5], source: `mail:${SYNTHETIC_MAIL.mail_id}` }];
    initial.references = [{ mail_id: SYNTHETIC_MAIL.mail_id, subject: '합성 참고 메일', received_at: SYNTHETIC_MAIL.received_at }];
    client.stored = initial;
    render(<ReplyDraftPage client={client} mailId={SYNTHETIC_MAIL.mail_id} draftId={initial.draft_id} onExit={vi.fn()} />);
    fireEvent.click(await screen.findByRole('button', { name: '합성 참고 메일' }));
    const dialog = await screen.findByRole('dialog', { name: '참고 메일 미리보기' });
    await within(dialog).findByText(SYNTHETIC_MAIL.subject);
    expect(within(dialog).getByText(/합성 응답으로 검사/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole('button', { name: '닫기' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});

it('근거의 Unicode 범위·HTML 문자 처리를 서버와 맞춘다', () => {
  const evidence = [{ source: 'profile.signature', span: [2, 4] as [number, number] }];
  expect(preserveEvidence('🌿 서명', '🌿 새 서명', evidence)[0].span).toEqual([4, 6]);
  render(<EvidenceBody body="<script>가짜</script>" evidence={[]} />);
  expect(screen.getByText('<script>가짜</script>')).toBeInTheDocument();
  expect(document.querySelector('script')).toBeNull();
  expect(within(document.body).queryByRole('alert')).not.toBeInTheDocument();
});
