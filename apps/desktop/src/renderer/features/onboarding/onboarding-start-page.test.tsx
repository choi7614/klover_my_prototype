import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { App } from '@/app';
import { OnboardingStartPage } from './onboarding-start-page';

describe('첫 실행 시작 화면', () => {
  it('서버 연결 전에는 계정 연결·다음 진행을 막고 이유를 알린다', () => {
    render(<OnboardingStartPage />);

    expect(screen.getByRole('button', { name: 'Google 계정으로 연결' })).toBeDisabled();
    const next = screen.getByRole('button', { name: '다음' });
    expect(next).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('현재 계정 연결을 사용할 수 없습니다.');

    fireEvent.click(next);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Gmail 계정 연결');
    expect(screen.queryByText('연결됨')).not.toBeInTheDocument();
    expect(screen.queryByText('준비가 끝났어요')).not.toBeInTheDocument();
  });

  it('직접 완료 단계 주소를 열어도 연결 확인 없이 단계를 건너뛰지 못한다', async () => {
    window.location.hash = '/onboarding/5';
    render(<App />);

    expect(await screen.findByRole('heading', { name: 'Gmail 계정 연결' })).toBeInTheDocument();
    expect(window.location.hash).toBe('#/onboarding/1');
  });
});
