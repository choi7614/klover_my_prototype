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
});
