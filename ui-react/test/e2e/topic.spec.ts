import { test, expect } from '@playwright/test';
import { setupMockServer } from '../setupTests';

const PATH = '/ws/topic/news?backlog=50';

let server: { send: (m: string) => void; stop: () => void };

test.beforeEach(async ({ page }) => {
  server = setupMockServer(PATH, []);
  await page.exposeFunction('serverSend', (msg: string) => server.send(msg));
});

test.afterEach(() => {
  server.stop();
});

test('topic stream grows with live items', async ({ page }) => {
  server.on('connection', (socket) => {
    socket.send(JSON.stringify({ title: 'init' }));
  });
  await page.goto('http://localhost:8500/topic/news');
  await expect(page.locator('details')).toHaveCount(1);
  await page.evaluate(() => (window as any).serverSend(JSON.stringify({ title: 'more' })));
  await expect(page.locator('details')).toHaveCount(2);
});
