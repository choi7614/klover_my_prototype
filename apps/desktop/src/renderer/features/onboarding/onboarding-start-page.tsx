import { Calendar, Mail, ShieldCheck } from 'lucide-react';
import type { ReactNode } from 'react';
import logo from '@brand/klover-logo.svg';
import mark from '@brand/klover-mark.svg';
import { Button } from '@/components/ui/button';
import { WizardSteps } from '@/components/wizard-steps';

export function OnboardingStartPage({ connectionNotice }: { connectionNotice?: ReactNode }) {
  return (
    <main className="flex min-h-screen bg-background">
      <aside className="flex w-[280px] shrink-0 flex-col border-r bg-muted px-6 py-7">
        <img src={logo} alt="Klover" className="mb-6 h-7 self-start" />
        <WizardSteps currentStep={1} />
      </aside>

      <section aria-labelledby="onboarding-title" className="flex min-w-0 flex-1 flex-col px-10 py-8">
        <header>
          <p className="text-caption font-semibold text-primary">1 / 5단계</p>
          <h1 id="onboarding-title" className="mt-1 text-heading font-bold">Gmail 계정 연결</h1>
          <p className="mt-1.5 text-body text-muted-foreground">Klover에서 사용할 Google 계정을 연결해 주세요.</p>
        </header>

        <div className="flex flex-1 flex-col justify-center py-6">
          <img src={mark} alt="" className="mb-6 size-16" />
          <h2 className="text-title font-semibold">메일을 한곳에서 확인하세요</h2>
          <p className="mt-2 max-w-[480px] text-body text-muted-foreground">
            지금부터 도착하는 메일을 Klover에서 확인하고, 작성하고, 보낼 수 있습니다.
            이전 메일은 가져오지 않습니다.
          </p>

          <ul className="mt-6 space-y-3 text-body text-secondary-foreground">
            <li className="flex items-center gap-3"><Mail aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />Gmail 메일 읽기·보내기·보관·삭제</li>
            <li className="flex items-center gap-3"><Calendar aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />Google Calendar 연결 권한 안내</li>
            <li className="flex items-center gap-3"><ShieldCheck aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />연결할 계정과 권한은 Google 로그인에서 확인합니다</li>
          </ul>

          <div className="mt-7">
            {/* 실제 OAuth 연결부가 준비되기 전에는 계정 연결이나 완료를 흉내 내지 않는다. */}
            <Button variant="secondary" size="lg" disabled aria-describedby="account-connection-status">
              Google 계정으로 연결
            </Button>
            <p id="account-connection-status" role="status" className="mt-3 text-caption text-muted-foreground">
              현재 계정 연결을 사용할 수 없습니다.
            </p>
            {connectionNotice}
          </div>
        </div>

        <footer className="flex items-center gap-6 border-t pt-4">
          <p className="text-caption text-muted-foreground">계정을 연결하면 다음 단계로 이동할 수 있습니다.</p>
          <Button className="ml-auto min-w-24" disabled>다음</Button>
        </footer>
      </section>
    </main>
  );
}
