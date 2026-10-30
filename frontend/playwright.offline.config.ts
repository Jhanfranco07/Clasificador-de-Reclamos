import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e', workers: 1, fullyParallel: false, retries: 0,
  reporter: 'list', outputDir: './test-results/offline',
  use: { baseURL: 'http://127.0.0.1:5173', serviceWorkers: 'block', trace: 'off' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
