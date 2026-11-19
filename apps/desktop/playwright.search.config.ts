import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/f3/e2e',
  use: {
    baseURL: 'http://127.0.0.1:5183',
    viewport: { width: 1280, height: 900 },
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'pnpm exec vite --config vite.search.config.ts',
    url: 'http://127.0.0.1:5183',
    reuseExistingServer: false,
  },
});
