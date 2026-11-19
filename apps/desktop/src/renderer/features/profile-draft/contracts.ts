import type { components } from './api-schema.generated';

type Schemas = components['schemas'];
export type Profile = Schemas['Profile'];
export type ProfileState = Omit<Schemas['ProfileState'], 'profile'> & { profile: Profile };
export type StyleState = Schemas['StyleState'];
export type Draft = Schemas['DraftState'];
export type Evidence = Schemas['Evidence'];
export type MailDetail = Schemas['MailDetail'];
export type Preview = Schemas['PreviewState'];
export type DraftAction = Schemas['DraftRevise']['action'];
export type Section = Profile['report_sections'][number];

/** F0의 제한된 IPC 어댑터가 구현할 포트. 토큰·임의 fetch·발송은 공개하지 않는다. */
export interface F2Client {
  profile(): Promise<ProfileState>;
  saveProfile(request: Schemas['ProfileUpdate']): Promise<ProfileState>;
  style(): Promise<StyleState>;
  deleteStyle(): Promise<ProfileState>;
  preview(request: Schemas['PreviewRequest']): Promise<Preview>;
  mail(mailId: string): Promise<MailDetail>;
  createDraft(request: Schemas['DraftCreate']): Promise<Draft>;
  draft(draftId: string): Promise<Draft>;
  saveDraft(draftId: string, request: Schemas['DraftSave']): Promise<Draft>;
  reviseDraft(draftId: string, request: Schemas['DraftRevise']): Promise<Draft>;
}

export const SECTION_LABELS: Record<Section, string> = {
  highlights: '금주 주요 업무', ongoing: '진행 중인 업무', issues: '이슈·요청사항', next_week: '차주 계획',
};

export function emptyProfile(): Profile {
  return {
    name: '', title: '', org: '', duties: '', frequent_contacts: [], formality: 70,
    reply_length: 'normal', greeting: '', closing: '', signature: '', style_learning_enabled: false,
    excluded_phrases: [], report_sections: ['highlights', 'ongoing', 'issues', 'next_week'],
    report_recipient: '', report_style: 'bullet',
  };
}

export const EMPTY_STYLE: StyleState = {
  enabled: false, status: 'disabled', analyzed_count: 0, phrases: [], traits: [],
};

export class F2Problem extends Error {
  constructor(public readonly code: string, message: string) { super(message); }
}

export function problemText(error: unknown): string {
  if (error instanceof F2Problem) return error.message;
  return '요청을 처리하지 못했어요. 입력한 내용은 보존됩니다. 다시 시도해 주세요.';
}

/** 연결 전 기본 포트. 합성 응답을 운영 결과로 사용하지 않는다. */
const unavailable = async (): Promise<never> => {
  throw new F2Problem('f2_unavailable', '프로필·초안 연결이 준비되지 않았어요. 앱 연결을 확인해 주세요.');
};
export const unavailableF2Client: F2Client = {
  profile: unavailable, saveProfile: unavailable, style: unavailable, deleteStyle: unavailable,
  preview: unavailable, mail: unavailable, createDraft: unavailable, draft: unavailable,
  saveDraft: unavailable, reviseDraft: unavailable,
};
