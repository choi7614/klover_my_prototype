import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e-f4',
  fullyParallel: false,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5174',
    browserName: 'chromium',
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined },
    viewport: { width: 1440, height: 1000 },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'node scripts/review-weekly-report.mjs',
    url: 'http://127.0.0.1:5174/features/weekly-report/preview/',
    reuseExistingServer: false,
    timeout: 30000,
  },
});
