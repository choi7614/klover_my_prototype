import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    browserName: 'chromium',
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined,
    },
    viewport: { width: 1040, height: 644 },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'pnpm dev:renderer',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
  },
});
