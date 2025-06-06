import { test, expect } from '@playwright/test';
import { Server } from 'mock-socket';

const FEED_PATH = '/ws/feed/0';

let server: Server;

test.beforeEach(async ({ page }) => {
  server = new Server(`ws://localhost:8000${FEED_PATH}`);
  server.on('connection', (socket) => {
    socket.send(JSON.stringify({ title: 'hello', topic: 'news' }));
  });
  await page.exposeFunction('serverSend', (msg: string) => server.send(msg));
});

test.afterEach(() => {
  server.stop();
});

test('tag filter with pending refresh', async ({ page }) => {
  await page.goto('http://localhost:8500');
  await page.getByLabel('User ID').fill('0');
  await expect(page.getByText('hello')).toBeVisible();
  await page.getByText('news').click();
  await expect(page.getByText('hello')).toBeVisible();
  const countBefore = await page.locator('details').count();
  await page.evaluate(() => (window as any).serverSend(JSON.stringify({ title: 'new', topic: 'news' })));
  await expect(page.locator('text=Refresh')).toBeVisible();
  await page.getByText('Refresh').click();
  await expect(page.locator('details')).toHaveCount(countBefore + 1);
});
