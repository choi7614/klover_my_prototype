import { Check } from 'lucide-react';
import { cn } from '@/lib/utils';

export const onboardingSteps = [
  'Gmail 계정 연결',
  '프로필 입력',
  '문체 학습 동의',
  '알림과 시작 프로그램',
  '완료',
] as const;

export type OnboardingStep = 1 | 2 | 3 | 4 | 5;

export function WizardSteps({ currentStep }: { currentStep: OnboardingStep }) {
  return (
    <nav aria-label="첫 실행 설정 단계">
      <ol className="space-y-1">
        {onboardingSteps.map((label, index) => {
          const step = index + 1;
          const complete = step < currentStep;
          const current = step === currentStep;

          return (
            <li key={label} aria-current={current ? 'step' : undefined} className="flex items-start gap-3 py-2.5">
              <span
                aria-hidden="true"
                className={cn(
                  'flex size-[26px] shrink-0 items-center justify-center rounded-full border-[1.5px] text-caption font-bold text-sidebar-muted',
                  complete && 'border-sidebar-primary bg-sidebar-primary text-sidebar-primary-foreground',
                  current && 'border-sidebar-primary text-sidebar-primary ring-4 ring-sidebar-accent',
                  !current && !complete && 'border-sidebar-muted',
                )}
              >
                {complete ? <Check className="size-4" /> : step}
              </span>
              <span className={cn('pt-0.5 text-body font-medium text-sidebar-muted', (complete || current) && 'font-semibold text-sidebar-primary')}>
                <span className="sr-only">{step}단계, {complete ? '완료, ' : current ? '현재 단계, ' : '대기, '}</span>
                {label}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
