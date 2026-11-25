import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AISettingsPage } from './ai-settings-page';
import { AIChoiceControl } from './ai-choice';
import type { AIState } from '../../../shared/ai-bridge';

const state: AIState = { defaults: { draft: 'ollama', search: 'ollama', weekly_report: 'claude' }, external_consent: false, claude_key_set: false, local_configured: true, claude_model: 'synthetic-model' };
afterEach(() => { vi.unstubAllGlobals(); });
function bridge() {
  const ai = {
    get: vi.fn().mockResolvedValue({ ok: true, data: state }),
    save: vi.fn().mockImplementation(async (request) => ({ ok: true, data: { ...state, defaults: request.defaults, external_consent: request.external_consent, claude_key_set: true } })),
    check: vi.fn().mockResolvedValue({ ok: true, data: { status: 'reachable', provider: 'claude' } }),
  };
  vi.stubGlobal('klover', { ai });
  return ai;
}
describe('AI 설정', () => {
  it('기능별 기본값과 동의·키를 저장하고 화면에서 키를 지운다', async () => {
    const ai = bridge();
    render(<AISettingsPage />);
    await screen.findByLabelText('답장 초안·수정');
    fireEvent.change(screen.getByLabelText('답장 초안·수정'), { target: { value: 'claude' } });
    fireEvent.change(screen.getByLabelText('Claude API 키 등록·교체'), { target: { value: 'synthetic-private-key' } });
    expect(screen.getByLabelText('Claude API 키 등록·교체')).toHaveAttribute('type', 'password');
    fireEvent.click(screen.getByRole('checkbox', { name: /외부 전송과 비용/ }));
    fireEvent.click(screen.getByRole('button', { name: '설정 저장' }));
    await screen.findByText(/AI 설정을 저장했습니다/);
    expect(ai.save).toHaveBeenCalledWith({ mode: 'hybrid', defaults: { draft: 'claude', search: 'ollama', weekly_report: 'claude' }, external_consent: true, api_key: 'synthetic-private-key' });
    expect(screen.getByLabelText('Claude API 키 등록·교체')).toHaveValue('');
    expect(screen.queryByText('synthetic-private-key')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Claude 연결 검사' }));
    await screen.findByText('Claude 연결 확인 완료');
    expect(ai.check).toHaveBeenCalledWith('claude');
  });
  it('연결 검사 결과를 색과 문구로 버튼 아래에 보여 주고, 실패하면 원인을 알려 준다', async () => {
    const ai = bridge();
    render(<AISettingsPage />);
    await screen.findByLabelText('답장 초안·수정');
    expect(screen.getByText('아직 검사하지 않음', { selector: 'span' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Claude 연결 검사' }));
    const ok = await screen.findByText('Claude 연결 확인 완료');
    expect(ok.closest('[role="status"]')).not.toBeNull();
    expect(screen.getByText(/키와 모델\(synthetic-model\)로 응답을 받았어요/)).toBeInTheDocument();
    expect(screen.getByText(/^연결됨/)).toBeInTheDocument();
    ai.check.mockResolvedValueOnce({ ok: false, error: { code: 'claude_auth_failed', message: 'Claude API 키가 올바르지 않거나 사용 권한이 없어요. 키를 다시 입력해 저장하세요.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Claude 연결 검사' }));
    const failed = await screen.findByRole('alert');
    expect(failed).toHaveTextContent('Claude 연결에 실패했어요');
    expect(failed).toHaveTextContent('키가 올바르지 않거나');
    expect(screen.getByText('연결 실패')).toBeInTheDocument();
  });
  it('키를 입력하고 저장하지 않은 채 검사하면 먼저 저장한 뒤 검사한다', async () => {
    const ai = bridge();
    render(<AISettingsPage />);
    await screen.findByLabelText('답장 초안·수정');
    fireEvent.change(screen.getByLabelText('Claude API 키 등록·교체'), { target: { value: 'synthetic-private-key' } });
    fireEvent.click(screen.getByRole('button', { name: '저장하고 Claude 연결 검사' }));
    await screen.findByText('Claude 연결 확인 완료');
    expect(ai.save).toHaveBeenCalledTimes(1);
    expect(ai.save.mock.invocationCallOrder[0]).toBeLessThan(ai.check.mock.invocationCallOrder[0]);
    // 저장 결과도 따로 남고, 저장한 뒤에는 일반 검사 버튼으로 돌아온다.
    expect(screen.getByText(/AI 설정을 저장했습니다/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Claude 연결 검사' })).toBeInTheDocument();
    expect(screen.queryByText('synthetic-private-key')).not.toBeInTheDocument();
  });
  it('저장에 실패하면 검사하지 않고 실패 원인을 보여 준다', async () => {
    const ai = bridge();
    ai.save.mockResolvedValueOnce({ ok: false, error: { code: 'x', message: '서버에 저장하지 못했어요.' } });
    render(<AISettingsPage />);
    await screen.findByLabelText('답장 초안·수정');
    fireEvent.change(screen.getByLabelText('Claude API 키 등록·교체'), { target: { value: 'synthetic-private-key' } });
    fireEvent.click(screen.getByRole('button', { name: '저장하고 Claude 연결 검사' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('서버에 저장하지 못했어요.');
    expect(ai.check).not.toHaveBeenCalled();
  });
  it('키 입력을 비워 저장하면 기존 키를 변경하지 않는다', async () => {
    const ai = bridge(); render(<AISettingsPage />);
    await screen.findByLabelText('답장 초안·수정');
    fireEvent.click(screen.getByRole('button', { name: '설정 저장' }));
    await waitFor(() => expect(ai.save).toHaveBeenCalled());
    expect(ai.save.mock.calls[0][0]).not.toHaveProperty('api_key');
  });
  it('기본 제공자 표시와 이번 요청의 선택을 구분하고 외부 전송을 안내한다', async () => {
    const ai = bridge(); const change = vi.fn();
    const { rerender } = render(<AIChoiceControl purpose="weekly_report" value="default" onChange={change} />);
    await screen.findByRole('option', { name: '기본 설정 (Claude)' });
    expect(screen.getByText(/Anthropic으로 전송/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('이번 요청의 AI'), { target: { value: 'ollama' } });
    expect(change).toHaveBeenCalledWith('ollama');
    expect(ai.save).not.toHaveBeenCalled();
    rerender(<AIChoiceControl purpose="weekly_report" value="ollama" onChange={change} />);
    expect(screen.queryByText(/Anthropic으로 전송/)).not.toBeInTheDocument();
  });
  it('Claude 안내는 같은 줄의 짧은 표시라서 선택을 바꿔도 줄 수가 늘지 않고, 자세한 문장은 툴팁에 있다', async () => {
    bridge(); const { container, rerender } = render(<AIChoiceControl purpose="weekly_report" value="ollama" onChange={vi.fn()} />);
    await screen.findByRole('option', { name: /기본 설정/ });
    const row = container.firstElementChild as HTMLElement;
    expect(row.className).not.toContain('flex-wrap');
    const before = row.children.length;
    rerender(<AIChoiceControl purpose="weekly_report" value="claude" onChange={vi.fn()} />);
    const note = await screen.findByText('Anthropic으로 전송 · 요금 발생');
    expect(note.parentElement).toBe(row);
    expect(note.className).not.toContain('basis-full');
    expect(note).toHaveAttribute('title', '필요한 메일·프로필이 Anthropic으로 전송되며 API 요금이 발생합니다.');
    expect(row.children.length).toBeGreaterThan(before);
  });
});
