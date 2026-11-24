import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { PrivacyPage } from './privacy-page';
import { SyntheticF2Client } from '../../../../tests/f2-harness/synthetic-client';

async function setup() {
  const client = new SyntheticF2Client();
  client.state.profile.style_learning_enabled = true;
  client.state.profile.excluded_phrases = ['제외 합성 표현'];
  client.learned = { enabled: true, status: 'ready', analyzed_count: 10, phrases: ['합성 표현'], traits: ['결론 먼저'] };
  const onBack = vi.fn();
  render(<PrivacyPage client={client} onBack={onBack} />);
  await screen.findByText('저장된 학습 동의: 켬');
  return { client, onBack };
}
it('동의와 준비 중 상태를 구분하고 기존 기록·제외 표현·프로필을 보여 준다', async () => {
  const { onBack } = await setup();
  expect(screen.getByText(/실제 보낸 메일 수집·문체 학습: 준비 중/)).toBeInTheDocument();
  expect(screen.getByText('제외 표현: 제외 합성 표현')).toBeInTheDocument();
  expect(screen.getByText('홍길동')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '‹ 내 프로필·문체' }));
  expect(onBack).toHaveBeenCalledOnce();
});
it('삭제 취소는 서버를 변경하지 않고 확인 후 삭제·재조회·동의를 갱신한다', async () => {
  const { client } = await setup();
  const remove = vi.spyOn(client, 'deleteStyle');
  const read = vi.spyOn(client, 'profile');
  const profile = structuredClone(client.state.profile);
  fireEvent.click(screen.getByText('학습 기록·제외 표현 삭제'));
  expect(screen.getByRole('alertdialog')).toHaveTextContent('OAuth 토큰, Claude 키는 유지');
  fireEvent.click(screen.getByText('취소'));
  expect(remove).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('학습 기록·제외 표현 삭제'));
  fireEvent.click(screen.getByText('확인하고 삭제'));
  await screen.findByText('학습 기록·제외 표현을 삭제하고 동의를 껐어요.');
  expect(remove).toHaveBeenCalledOnce();
  expect(read).toHaveBeenCalledOnce();
  expect(client.state.profile).toEqual({ ...profile, style_learning_enabled: false, excluded_phrases: [] });
  expect(screen.getByText('저장된 학습 동의: 끔')).toBeInTheDocument();
  expect(screen.getByText('제외 표현: 없음')).toBeInTheDocument();
});
it('삭제 실패 후 성공을 알리지 않고 재조회 전 추가 변경을 막는다', async () => {
  const { client } = await setup();
  vi.spyOn(client, 'deleteStyle').mockRejectedValue(new Error('private raw error'));
  fireEvent.click(screen.getByText('학습 기록·제외 표현 삭제'));
  fireEvent.click(screen.getByText('확인하고 삭제'));
  await screen.findByRole('alert');
  expect(screen.queryByText(/private raw error/)).not.toBeInTheDocument();
  expect(screen.getByText('학습 기록·제외 표현 삭제')).toBeDisabled();
  fireEvent.click(screen.getByText('다시 불러오기'));
  await waitFor(() => expect(screen.getByText('학습 기록·제외 표현 삭제')).toBeEnabled());
});
it('동의 끄기는 기록을 보존하며 전체 프로필과 버전을 재사용한다', async () => {
  const { client } = await setup();
  const save = vi.spyOn(client, 'saveProfile');
  fireEvent.click(screen.getByText('학습 동의 끄기'));
  fireEvent.click(screen.getByText('확인하고 저장'));
  await screen.findByText('저장된 학습 동의: 끔');
  expect(save.mock.calls[0][0]).toMatchObject({ expected_version: 1, consent_given: false });
  expect(client.learned.analyzed_count).toBe(10);
  expect(client.state.profile.excluded_phrases).toEqual(['제외 합성 표현']);
});
it('동의 켜기는 명시적 확인 후 저장한다', async () => {
  const client = new SyntheticF2Client();
  const save = vi.spyOn(client, 'saveProfile');
  render(<PrivacyPage client={client} onBack={vi.fn()} />);
  await screen.findByText('저장된 학습 동의: 끔');
  fireEvent.click(screen.getByText('학습 동의 켜기'));
  fireEvent.click(screen.getByText('취소'));
  expect(save).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('학습 동의 켜기'));
  fireEvent.click(screen.getByText('확인하고 저장'));
  await screen.findByText('저장된 학습 동의: 켬');
  expect(save.mock.calls[0][0]).toMatchObject({ consent_given: true });
});
it('삭제 후 재조회 실패를 표시하고 재조회로 복구한다', async () => {
  const { client } = await setup();
  vi.spyOn(client, 'style').mockRejectedValueOnce(new Error('read failed'));
  fireEvent.click(screen.getByText('학습 기록·제외 표현 삭제'));
  fireEvent.click(screen.getByText('확인하고 삭제'));
  await screen.findByRole('alert');
  expect(screen.queryByText('학습 기록·제외 표현을 삭제하고 동의를 껐어요.')).not.toBeInTheDocument();
  expect(client.state.profile.style_learning_enabled).toBe(false);
  fireEvent.click(screen.getByText('다시 불러오기'));
  await screen.findByText('제외 표현: 없음');
});
it('프로필이 없으면 동의를 켤 수 없다', async () => {
  const client = new SyntheticF2Client();
  client.state.exists = false;
  render(<PrivacyPage client={client} onBack={vi.fn()} />);
  await screen.findByText(/저장된 프로필이 없어요/);
  expect(screen.getByText('학습 동의 켜기')).toBeDisabled();
});
