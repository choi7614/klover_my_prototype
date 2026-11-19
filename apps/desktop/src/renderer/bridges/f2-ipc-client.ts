// preload의 F2 통로를 F2 화면이 쓰는 F2Client로 바꾼다. 실패는 F2Problem으로 던져 화면의 안내를 그대로 쓴다.
import { F2Problem, type F2Client } from '../features/profile-draft';
import type { F2Bridge, F2Result } from '../../shared/f2-bridge';

async function unwrap<T>(pending: Promise<F2Result>): Promise<T> {
  let result: F2Result;
  try { result = await pending; }
  catch { throw new F2Problem('connection', '서버에 연결할 수 없어요. 서버 실행 상태를 확인한 뒤 다시 시도해 주세요.'); }
  if (!result || typeof result !== 'object') throw new F2Problem('invalid_response', '서버 응답을 확인할 수 없어요.');
  if (!result.ok) throw new F2Problem(result.error.code, result.error.message);
  return result.data as T;
}

export function createF2IPCClient(bridge: F2Bridge): F2Client {
  return {
    profile: () => unwrap(bridge.profile()),
    saveProfile: request => unwrap(bridge.saveProfile(request)),
    style: () => unwrap(bridge.style()),
    deleteStyle: () => unwrap(bridge.deleteStyle()),
    preview: request => unwrap(bridge.preview(request)),
    mail: mailId => unwrap(bridge.mail(mailId)),
    createDraft: request => unwrap(bridge.createDraft(request)),
    draft: draftId => unwrap(bridge.draft(draftId)),
    saveDraft: (draftId, request) => unwrap(bridge.saveDraft(draftId, request)),
    reviseDraft: (draftId, request) => unwrap(bridge.reviseDraft(draftId, request)),
  };
}
