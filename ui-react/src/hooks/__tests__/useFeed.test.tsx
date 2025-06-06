import { renderHook, waitFor, act } from '@testing-library/react';
import { setupMockServer } from '../../../test/setupTests';
import { useFeed } from '../useFeed';

test('useFeed deferred refresh', async () => {
  setupMockServer('/ws/feed/0?backlog=100', [{ title: 'one' }, { title: 'two' }]);
  const { result } = renderHook(() => useFeed('0'));
  await waitFor(() => expect(result.current.messages).toHaveLength(1));
  expect(result.current.messages[0].title).toBe('one');
  expect(result.current.pending).toHaveLength(1);
  act(() => result.current.refresh());
  expect(result.current.pending).toHaveLength(0);
  expect(result.current.messages.map((m) => m.title)).toEqual(['two', 'one']);
});

test('useFeed re-subscribes when uid changes', async () => {
  setupMockServer('/ws/feed/0?backlog=100', [{ title: 'a0' }]);
  setupMockServer('/ws/feed/1?backlog=100', [{ title: 'b1' }]);
  const { result, rerender } = renderHook(({ uid }) => useFeed(uid), {
    initialProps: { uid: '0' },
  });
  await waitFor(() => expect(result.current.messages).toHaveLength(1));
  expect(result.current.messages[0].title).toBe('a0');
  rerender({ uid: '1' });
  await waitFor(() => expect(result.current.messages).toHaveLength(1));
  expect(result.current.messages[0].title).toBe('b1');
});

test('ready once socket opens even without backlog', async () => {
  const server = setupMockServer('/ws/feed/0?backlog=100', []);
  const { result } = renderHook(() => useFeed('0'));
  await waitFor(() => expect(result.current.ready).toBe(true));
  expect(result.current.messages).toHaveLength(0);
  await new Promise((r) => setTimeout(r, 20));
  server.send(JSON.stringify({ title: 'hi' }));
  await waitFor(() => expect(result.current.messages).toHaveLength(1));
});
