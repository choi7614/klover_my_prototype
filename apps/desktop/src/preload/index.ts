import { contextBridge, ipcRenderer } from 'electron';
import type { MailReadBridge } from '../shared/mail-read';
import type { F2Bridge } from '../shared/f2-bridge';
import type { F4Bridge } from '../shared/f4-bridge';
import type { F5Bridge } from '../shared/f5-bridge';
import type { SearchBridge, SearchMessage } from '../shared/search-bridge';

// 화면에는 필요한 정보와 정해진 통로만 공개한다. Node·파일·임의 IPC 접근은 공개하지 않는다.
// 샌드박스 preload는 런타임 로컬 모듈을 require하지 않도록 채널을 리터럴로 제한한다.
const mail = Object.freeze<MailReadBridge>({
  session: () => ipcRenderer.invoke('klover:mail:session'),
  inbox: query => ipcRenderer.invoke('klover:mail:inbox', query),
  detail: mailId => ipcRenderer.invoke('klover:mail:detail', mailId),
  sync: () => ipcRenderer.invoke('klover:mail:sync'),
});

// F2 프로필·답장 초안. 인수는 main에서 다시 검사한다. 발송 통로는 없다.
const f2 = Object.freeze<F2Bridge>({
  profile: (...args) => ipcRenderer.invoke('klover:f2:profile', ...args),
  saveProfile: (...args) => ipcRenderer.invoke('klover:f2:saveProfile', ...args),
  style: (...args) => ipcRenderer.invoke('klover:f2:style', ...args),
  deleteStyle: (...args) => ipcRenderer.invoke('klover:f2:deleteStyle', ...args),
  preview: (...args) => ipcRenderer.invoke('klover:f2:preview', ...args),
  mail: (...args) => ipcRenderer.invoke('klover:f2:mail', ...args),
  createDraft: (...args) => ipcRenderer.invoke('klover:f2:createDraft', ...args),
  draft: (...args) => ipcRenderer.invoke('klover:f2:draft', ...args),
  saveDraft: (...args) => ipcRenderer.invoke('klover:f2:saveDraft', ...args),
  reviseDraft: (...args) => ipcRenderer.invoke('klover:f2:reviseDraft', ...args),
});

// F3 검색. 단계 메시지는 main이 이 창으로만 보낸다.
const search = Object.freeze<SearchBridge>({
  start: (requestId, request) => ipcRenderer.invoke('klover:search:start', requestId, request),
  cancel: requestId => ipcRenderer.invoke('klover:search:cancel', requestId),
  recent: () => ipcRenderer.invoke('klover:search:recent'),
  onMessage: listener => {
    const handler = (_event: unknown, requestId: unknown, message: unknown) => {
      if (typeof requestId === 'string' && message && typeof message === 'object') listener(requestId, message as SearchMessage);
    };
    ipcRenderer.on('klover:search:message', handler);
    return () => { ipcRenderer.removeListener('klover:search:message', handler); };
  },
});

const weeklyReport = Object.freeze<F4Bridge>({
  options: () => ipcRenderer.invoke('klover:weekly-report:options'),
  generate: request => ipcRenderer.invoke('klover:weekly-report:generate', request),
  get: id => ipcRenderer.invoke('klover:weekly-report:get', id),
  excluded: id => ipcRenderer.invoke('klover:weekly-report:excluded', id),
  save: (id, revision, sections) => ipcRenderer.invoke('klover:weekly-report:save', id, revision, sections),
});
// F5 AI 제안·할 일. 인수는 main에서 다시 검사한다. 알림 outbox·캘린더 직접 호출 통로는 없다.
const suggestions = Object.freeze<F5Bridge>({
  list: query => ipcRenderer.invoke('klover:suggestions:list', query),
  get: suggestionId => ipcRenderer.invoke('klover:suggestions:get', suggestionId),
  approve: (suggestionId, request) => ipcRenderer.invoke('klover:suggestions:approve', suggestionId, request),
  dismiss: (suggestionId, request) => ipcRenderer.invoke('klover:suggestions:dismiss', suggestionId, request),
  conflicts: (suggestionId, payload) => ipcRenderer.invoke('klover:suggestions:conflicts', suggestionId, payload),
  todos: query => ipcRenderer.invoke('klover:suggestions:todos', query),
  createTodo: request => ipcRenderer.invoke('klover:suggestions:createTodo', request),
  updateTodo: (todoId, request) => ipcRenderer.invoke('klover:suggestions:updateTodo', todoId, request),
});
contextBridge.exposeInMainWorld('klover', Object.freeze({ platform: process.platform, mail, f2, search, weeklyReport, suggestions }));
