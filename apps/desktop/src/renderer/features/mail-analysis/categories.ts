// 카테고리·상태 태그 정의. docs/design/tokens/categories.ts를 따른다. 색은 토큰 클래스만 쓴다.
import type { AnalysisCategory } from '../../../shared/f1-bridge';

export const CATEGORIES: Record<AnalysisCategory, { label: string; tag: string; dot: string }> = {
  work_request: { label: '업무 요청', tag: 'bg-cat-work-bg text-cat-work-fg', dot: 'bg-cat-work-dot' },
  meeting: { label: '회의·일정', tag: 'bg-cat-meeting-bg text-cat-meeting-fg', dot: 'bg-cat-meeting-dot' },
  approval: { label: '결재·승인', tag: 'bg-cat-approval-bg text-cat-approval-fg', dot: 'bg-cat-approval-dot' },
  report_share: { label: '보고·공유', tag: 'bg-cat-report-bg text-cat-report-fg', dot: 'bg-cat-report-dot' },
  notice: { label: '공지', tag: 'bg-cat-notice-bg text-cat-notice-fg', dot: 'bg-cat-notice-dot' },
  external: { label: '외부·고객', tag: 'bg-cat-external-bg text-cat-external-fg', dot: 'bg-cat-external-dot' },
  newsletter: { label: '뉴스레터·광고', tag: 'bg-cat-newsletter-bg text-cat-newsletter-fg', dot: 'bg-cat-newsletter-dot' },
};

export const STATUS_TAGS = {
  needs_reply: { label: '회신 필요', tag: 'bg-danger-subtle text-danger' },
  due: { label: (date: string) => `마감 ${date}`, tag: 'bg-warning-subtle text-warning' },
} as const;

export const TAG_BASE = 'inline-flex h-5 items-center whitespace-nowrap rounded-sm px-1.5 text-caption font-medium';

export const PRIORITY_LABELS = { high: '높음', normal: '보통', low: '낮음' } as const;
