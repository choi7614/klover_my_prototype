import { contextBridge } from 'electron';

// 화면에는 필요한 읽기 전용 정보만 공개한다. Node·파일·임의 IPC 접근은 공개하지 않는다.
contextBridge.exposeInMainWorld('klover', Object.freeze({ platform: process.platform }));
