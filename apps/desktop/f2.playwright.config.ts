import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/f2-browser',
  fullyParallel: true,
  use: {
    baseURL: 'http://127.0.0.1:5175',
    browserName: 'chromium',
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'node_modules/.bin/vite --config f2.vite.config.ts',
    url: 'http://127.0.0.1:5175',
    reuseExistingServer: true,
  },
});
