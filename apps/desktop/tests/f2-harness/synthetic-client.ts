/** 합성 화면·자동 검사 전용. 운영 진입점에서 import하지 않는다. */
import { emptyProfile, EMPTY_STYLE, F2Problem, type Draft, type F2Client, type MailDetail, type Preview, type Profile, type ProfileState, type StyleState } from '../../src/renderer/features/profile-draft/contracts';

function copy<T>(value: T): T { return structuredClone(value); }

export const SYNTHETIC_PROFILE: Profile = {
  ...emptyProfile(), name: '홍길동', title: '과장', org: '경영지원본부 재무팀',
  duties: '부서별 예산 편성·집행 관리, 월·분기 결산, 외부 감사 대응',
  frequent_contacts: ['영업기획팀', '전략기획팀', '한빛회계법인'],
  greeting: '안녕하세요 🌿, 재무팀 홍길동입니다.', closing: '감사합니다.\n홍길동 드림',
  signature: '홍길동 과장 | 경영지원본부 재무팀\n02-0000-0000 | synthetic@example.invalid', report_recipient: '이수진 팀장',
};

export const SYNTHETIC_MAIL: MailDetail = {
  mail_id: 'synthetic-mail', subject: '3분기 예산 집행 현황 자료 요청드립니다',
  from_addr: 'sender@example.invalid', from_name: '박지훈 과장 (합성)',
  body_text: '이 화면은 합성 응답으로 검사하고 있습니다.\n\n4분기 예산 검토를 위해 3분기 부서별 집행 현황 자료가 필요합니다.\n마케팅비와 출장비를 월별로 나눠 주시면 검토에 도움이 될 것 같습니다.',
  preview: '합성 검사 자료 요청', received_at: '2026-11-18T00:12:00Z', is_read: false,
  analysis_status: 'pending', to: [], cc: [],
};

export class SyntheticF2Client implements F2Client {
  state: ProfileState = { profile: copy(SYNTHETIC_PROFILE), exists: true, version: 1 };
  learned: StyleState = copy(EMPTY_STYLE);
  stored: Draft | null = null;
  failAI = false;
  failSave = false;
  delayAI = 0;
  includeReference = false;

  async profile() { return copy(this.state); }
  async style() { return copy(this.learned); }
  async saveProfile(request: Parameters<F2Client['saveProfile']>[0]) {
    if (this.failSave) throw new F2Problem('storage_unavailable', '합성 저장 실패');
    if (request.expected_version !== this.state.version) throw new F2Problem('version_conflict', '다른 변경이 저장됐어요. 다시 불러와 주세요.');
    this.state = { profile: copy(request.profile), exists: true, version: this.state.version + 1 };
    return copy(this.state);
  }
  async deleteStyle() {
    this.state = { ...this.state, profile: { ...this.state.profile, style_learning_enabled: false, excluded_phrases: [] }, version: this.state.version + 1 };
    this.learned = copy(EMPTY_STYLE);
    return copy(this.state);
  }
  async waitAI() {
    if (this.delayAI) await new Promise(resolve => window.setTimeout(resolve, this.delayAI));
    if (this.failAI) throw new F2Problem('ai_unavailable', 'AI 연결이 준비되지 않았어요. 직접 작성해 주세요.');
  }
  async preview(request: Parameters<F2Client['preview']>[0]): Promise<Preview> {
    await this.waitAI();
    const p = request.profile;
    return { body: [p.greeting, `합성 예시 · 격식 ${p.formality} · 길이 ${p.reply_length}`, p.closing, p.signature].filter(Boolean).join('\n'), evidence: [] };
  }
  async mail(mailId: string) {
    if (mailId !== SYNTHETIC_MAIL.mail_id) throw new F2Problem('not_found', '메일을 찾을 수 없습니다.');
    return copy(SYNTHETIC_MAIL);
  }
  private generated(direction = '기한 내 송부 약속', action?: string): Draft {
    const middle = action === 'shorter' ? '합성 검사: 자료를 확인하겠습니다.'
      : action === 'politer' ? '합성 검사: 요청하신 자료를 확인하여 정중히 회신드리겠습니다.'
        : direction === '기한 조정 요청' ? '합성 검사: 자료 확인에 필요한 기한을 조정할 수 있을까요?'
          : '합성 검사: 요청하신 자료를 확인하고 회신드리겠습니다. 마케팅비와 출장비는 월별로 구분하겠습니다.';
    let body = '';
    const evidence: Draft['evidence'] = [];
    const add = (value: string, source?: string) => {
      if (!value) return;
      if (body) body += '\n\n';
      const start = Array.from(body).length;
      body += value;
      if (source) evidence.push({ span: [start, Array.from(body).length], source });
    };
    add(this.state.profile.greeting, 'profile.greeting'); add(middle, this.includeReference ? `mail:${SYNTHETIC_MAIL.mail_id}` : undefined);
    add(this.state.profile.closing, 'profile.closing'); add(this.state.profile.signature, 'profile.signature');
    return {
      draft_id: 'synthetic-draft', mail_id: SYNTHETIC_MAIL.mail_id,
      directions: ['기한 내 송부 약속', '기한 조정 요청', '추가 정보 문의'], selected_direction: direction,
      body, evidence, references: this.includeReference ? [{ mail_id: SYNTHETIC_MAIL.mail_id, subject: '합성 참고 자료 메일', received_at: SYNTHETIC_MAIL.received_at }] : [], version: (this.stored?.version ?? 0) + 1,
      profile_version: this.state.version, context_status: { related: 'unavailable', analysis: 'unavailable' },
    };
  }
  async createDraft(request: Parameters<F2Client['createDraft']>[0]) {
    await this.waitAI(); await this.mail(request.mail_id);
    this.stored = this.generated(request.direction ?? undefined);
    return copy(this.stored);
  }
  async draft(draftId: string) {
    if (!this.stored || draftId !== this.stored.draft_id) throw new F2Problem('not_found', '초안을 찾을 수 없습니다.');
    return copy(this.stored);
  }
  async saveDraft(draftId: string, request: Parameters<F2Client['saveDraft']>[1]) {
    if (this.failSave) throw new F2Problem('storage_unavailable', '합성 저장 실패');
    const previous = await this.draft(draftId);
    if (request.expected_version !== previous.version) throw new F2Problem('version_conflict', '다른 변경이 저장됐어요.');
    this.stored = { ...previous, body: request.body, evidence: request.body === previous.body ? previous.evidence : [], version: previous.version + 1 };
    return copy(this.stored);
  }
  async reviseDraft(draftId: string, request: Parameters<F2Client['reviseDraft']>[1]) {
    await this.waitAI();
    const previous = await this.draft(draftId);
    if (request.expected_version !== previous.version) throw new F2Problem('version_conflict', '다른 변경이 저장됐어요.');
    this.stored = this.generated(request.direction ?? previous.selected_direction, request.action);
    return copy(this.stored);
  }
}
