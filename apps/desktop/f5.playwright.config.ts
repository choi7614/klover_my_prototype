import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/f5-e2e',
  fullyParallel: true,
  use: {
    baseURL: 'http://127.0.0.1:5175/f5-preview/',
    browserName: 'chromium',
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined },
    viewport: { width: 1440, height: 1000 },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'corepack pnpm exec vite --config f5-preview/vite.config.ts',
    url: 'http://127.0.0.1:5175/f5-preview/',
    reuseExistingServer: false,
  },
});
