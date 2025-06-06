import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { setupMockServer } from '../../test/setupTests';
import App from '../App';

vi.stubGlobal('fetch', vi.fn((url: string) => {
  if (url.endsWith('/user/0')) {
    return Promise.resolve(new Response(JSON.stringify({ interests: ['foo', 'bar'] })));
  }
  if (url.endsWith('/user/1')) {
    return Promise.resolve(new Response(JSON.stringify({ interests: ['baz'] })));
  }
  return Promise.resolve(new Response('null', { status: 404 }));
}));

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

test('topic filter resets when uid changes', async () => {
  setupMockServer('/ws/feed/0?backlog=100', [
    { title: 'p0', topic: 'foo' },
    { title: 'p1', topic: 'bar' }
  ]);
  setupMockServer('/ws/feed/1?backlog=100', [{ title: 'x', topic: 'baz' }]);

  const { rerender } = render(<App initialUid="0" />);
  await waitFor(() => expect(document.querySelectorAll('details')).toHaveLength(1));

  fireEvent.click(screen.getAllByText('foo')[0]);
  expect(document.querySelectorAll('details')).toHaveLength(1);

  rerender(<App initialUid="1" />);
  await waitFor(() => expect(document.querySelectorAll('details')).toHaveLength(1));
  expect(screen.queryByText('connecting…')).not.toBeInTheDocument();
});
