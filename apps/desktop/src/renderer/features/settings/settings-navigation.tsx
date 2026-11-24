import type { ReactNode } from 'react';

export const SETTINGS = [
  { id: 'profile', path: '/settings/profile', label: '내 프로필·문체', description: '이름, 인사말, 서명과 보고 양식' },
  { id: 'ai', path: '/settings/ai', label: 'AI 설정', description: '기능별 AI 선택, Claude 키와 로컬 전용 모드' },
  { id: 'calendar', path: '/settings/calendar', label: '캘린더 연결', description: 'Google Calendar 추가 동의와 연결 관리' },
  { id: 'history', path: '/settings/mail-history', label: '과거 메일 가져오기', description: '선택한 기간의 받은편지함 메일 가져오기' },
  { id: 'privacy', path: '/settings/privacy', label: '개인정보·학습 데이터', description: '저장된 프로필과 학습 동의·기록 관리' },
] as const;
export type SettingsTarget = typeof SETTINGS[number]['id'];

export function SettingsNavigation({ current }: { current?: SettingsTarget }) {
  return <nav aria-label="설정 메뉴" className="flex flex-wrap gap-2 border-b bg-muted p-3 text-caption">
    <a href="#/mail/inbox" className="rounded-md px-3 py-2 hover:bg-accent focus-visible:outline-ring">‹ 받은편지함</a>
    <a href="#/settings" className="rounded-md px-3 py-2 hover:bg-accent focus-visible:outline-ring">설정 전체</a>
    {SETTINGS.map(item => <a key={item.id} href={`#${item.path}`} aria-current={current === item.id ? 'page' : undefined} className={`rounded-md px-3 py-2 focus-visible:outline-ring ${current === item.id ? 'bg-selected font-semibold text-selected-foreground' : 'hover:bg-accent'}`}>{item.label}</a>)}
  </nav>;
}
export function SettingsFrame({ current, children }: { current: SettingsTarget; children: ReactNode }) {
  return <div className="flex h-full min-h-0 flex-col bg-background"><SettingsNavigation current={current} /><div className="min-h-0 flex-1 overflow-auto">{children}</div></div>;
}
export function SettingsHome() {
  return <div className="h-full overflow-auto bg-background text-foreground"><SettingsNavigation />
    <main className="mx-auto max-w-5xl space-y-6 p-6 sm:p-8">
      <header><h1 className="text-heading font-bold">설정</h1><p className="mt-2 text-body text-muted-foreground">사용할 기능을 선택해 설정하세요.</p></header>
      <div className="grid gap-3 sm:grid-cols-2">{SETTINGS.map(item => <a key={item.id} href={`#${item.path}`} className="rounded-lg border bg-card p-5 hover:border-primary focus-visible:outline-ring"><h2 className="text-title font-semibold">{item.label} →</h2><p className="mt-2 text-body text-muted-foreground">{item.description}</p></a>)}</div>
      <a href="#/report/weekly" className="inline-block rounded-md border px-4 py-2 text-body hover:bg-accent focus-visible:outline-ring">주간 보고 열기 →</a>
      <section className="rounded-lg border bg-muted p-4 text-body text-muted-foreground"><h2 className="font-semibold">준비 중인 기능</h2><p className="mt-2">앱 안 메일 계정 연결·변경, 알림·시작 프로그램, 보낸 메일 자동 문체 학습은 아직 제공하지 않습니다.</p><p className="mt-1">현재 Gmail 연결은 유지됩니다. 학습 동의와 저장 기록은 개인정보·학습 데이터에서 관리할 수 있습니다.</p></section>
    </main>
  </div>;
}
