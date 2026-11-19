import { contextBridge, ipcRenderer } from 'electron';
import type { MailReadBridge } from '../shared/mail-read';

// 화면에는 필요한 읽기 전용 정보만 공개한다. Node·파일·임의 IPC 접근은 공개하지 않는다.
// 샌드박스 preload는 런타임 로컬 모듈을 require하지 않도록 채널을 리터럴로 제한한다.
const mail = Object.freeze<MailReadBridge>({
  session: () => ipcRenderer.invoke('klover:mail:session'),
  inbox: query => ipcRenderer.invoke('klover:mail:inbox', query),
  detail: mailId => ipcRenderer.invoke('klover:mail:detail', mailId),
  sync: () => ipcRenderer.invoke('klover:mail:sync'),
});
contextBridge.exposeInMainWorld('klover', Object.freeze({ platform: process.platform, mail }));
