/// <reference types="vite/client" />

interface Window {
  readonly klover?: Readonly<{
    platform: string;
    mail: import('../shared/mail-read').MailReadBridge;
    /** main/preload 연결 전 빌드에서는 없을 수 있다. */
    f2?: import('../shared/f2-bridge').F2Bridge;
    search?: import('../shared/search-bridge').SearchBridge;
  }>;
}
