/// <reference types="vite/client" />

interface Window {
  readonly klover?: Readonly<{ platform: string; mail: import('../shared/mail-read').MailReadBridge }>;
}
