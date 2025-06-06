import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './test/e2e',
  webServer: {
    command: 'npx serve -s dist -l 8500',
    port: 8500,
    reuseExistingServer: !process.env.CI
  }
});
