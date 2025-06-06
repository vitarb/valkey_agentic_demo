import { renderHook, waitFor, act } from '@testing-library/react';
import { setupMockServer } from '../../../test/setupTests';
import { useFeed } from '../useFeed';

test('useFeed deferred refresh', async () => {
  setupMockServer('/ws/feed/0', [{ title: 'one' }, { title: 'two' }]);
  const { result } = renderHook(() => useFeed('0'));
  await waitFor(() => expect(result.current.messages).toHaveLength(1));
  expect(result.current.messages[0].title).toBe('one');
  expect(result.current.pending).toHaveLength(1);
  act(() => result.current.refresh());
  expect(result.current.pending).toHaveLength(0);
  expect(result.current.messages.map((m) => m.title)).toEqual(['two', 'one']);
});

test('useFeed re-subscribes when uid changes', async () => {
  setupMockServer('/ws/feed/0', [{ title: 'a0' }]);
  setupMockServer('/ws/feed/1', [{ title: 'b1' }]);
  const { result, rerender } = renderHook(({ uid }) => useFeed(uid), {
    initialProps: { uid: '0' },
  });
  await waitFor(() => expect(result.current.messages).toHaveLength(1));
  expect(result.current.messages[0].title).toBe('a0');
  rerender({ uid: '1' });
  await waitFor(() => expect(result.current.messages).toHaveLength(1));
  expect(result.current.messages[0].title).toBe('b1');
});
