import { test, expect } from '@playwright/test';
import { setupMockServer } from '../setupTests';

const FEED_PATH = '/ws/feed/1?backlog=100';

let server: { send: (m: string) => void; stop: () => void };

test.beforeEach(async ({ page }) => {
  server = setupMockServer(
    FEED_PATH,
    Array.from({ length: 10 }, (_, i) => ({ title: `post ${i}` }))
  );
  await page.exposeFunction('serverSend', (msg: string) => server.send(msg));
});

test.afterEach(() => {
  server.stop();
});

test('initial backlog shown without refresh banner', async ({ page }) => {
  await page.goto('http://localhost:8500/user/1');
  await expect(page.locator('details')).toHaveCount(10);
  await expect(page.locator('text=Refresh')).toHaveCount(0);
});
