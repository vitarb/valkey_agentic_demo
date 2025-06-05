import { renderHook, waitFor } from '@testing-library/react';
import { setupMockServer } from '../../../test/setupTests';
import { useFeed } from '../useFeed';

test('useFeed receives messages', async () => {
  setupMockServer('/ws/feed/0', [{ text: 'one' }, { text: 'two' }]);
  const { result } = renderHook(() => useFeed('0'));
  await waitFor(() => {
    expect(result.current).toHaveLength(2);
  });
  expect(result.current[0].text).toBe('one');
});
