/// <reference types="vite/client" />

interface Window {
  readonly klover?: Readonly<{
    platform: string;
    ai?: import('../shared/ai-bridge').AIBridge;
    mail: import('../shared/mail-read').MailReadBridge;
    /** main/preload 연결 전 빌드에서는 없을 수 있다. */
    f2?: import('../shared/f2-bridge').F2Bridge;
    weeklyReport?: import('../shared/f4-bridge').F4Bridge;
    search?: import('../shared/search-bridge').SearchBridge;
    suggestions?: import('../shared/f5-bridge').F5Bridge;
    analysis?: import('../shared/f1-bridge').F1Bridge;
  }>;
}
