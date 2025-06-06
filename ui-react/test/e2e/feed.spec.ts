import { test, expect } from '@playwright/test';
import { setupMockServer } from '../setupTests';

const FEED1_PATH = '/ws/feed/1?backlog=100';
const FEED2_PATH = '/ws/feed/2?backlog=100';

let server: { send: (m: string) => void; stop: () => void };
let server2: { send: (m: string) => void; stop: () => void } | null = null;

test.beforeEach(async ({ page }) => {
  server = setupMockServer(
    FEED1_PATH,
    Array.from({ length: 10 }, (_, i) => ({ title: `post ${i}`, topic: 'foo' }))
  );
  await page.exposeFunction('serverSend', (msg: string) => server.send(msg));
});

test.afterEach(() => {
  server.stop();
  server2?.stop();
  server2 = null;
});

test('initial backlog shown without refresh banner', async ({ page }) => {
  await page.goto('http://localhost:8500/user/1');
  await expect(page.locator('details')).toHaveCount(10);
  await expect(page.locator('text=Refresh')).toHaveCount(0);
});

test('filter resets when navigating between users', async ({ page }) => {
  server2 = setupMockServer(FEED2_PATH, [{ title: 'other', topic: 'bar' }]);
  await page.route('http://localhost:8000/user/1', async route => {
    await route.fulfill({ status: 200, body: JSON.stringify({ interests: ['foo'] }) });
  });
  await page.route('http://localhost:8000/user/2', async route => {
    await route.fulfill({ status: 200, body: JSON.stringify({ interests: ['bar'] }) });
  });

  await page.goto('http://localhost:8500/user/1');
  await expect(page.locator('details')).toHaveCount(10);
  await page.click('text=foo');

  await page.goto('http://localhost:8500/user/2');
  await expect(page.locator('details')).toHaveCount(1);
  await expect(page.locator('text=connecting…')).toHaveCount(0);

  await page.goto('http://localhost:8500/user/1');
  await expect(page.locator('details')).toHaveCount(10);
  await expect(page.locator('text=connecting…')).toHaveCount(0);
});
