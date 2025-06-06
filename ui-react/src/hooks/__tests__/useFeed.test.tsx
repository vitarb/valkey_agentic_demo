import { renderHook, waitFor } from '@testing-library/react';
import { setupMockServer } from '../../../test/setupTests';
import { useFeed } from '../useFeed';

test('useFeed receives messages', async () => {
  setupMockServer('/ws/feed/0', [{ title: 'one' }, { title: 'two' }]);
  const { result } = renderHook(() => useFeed('0'));
  await waitFor(() => {
    expect(result.current.messages).toHaveLength(2);
  });
  expect(result.current.messages[0].title).toBe('one');
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
