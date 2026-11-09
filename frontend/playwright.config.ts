import { defineConfig, devices } from '@playwright/test';
// Start both local servers first. Tests create isolated fictional households.
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop-chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile-chromium', use: { ...devices['Pixel 7'] } },
  ],
});
