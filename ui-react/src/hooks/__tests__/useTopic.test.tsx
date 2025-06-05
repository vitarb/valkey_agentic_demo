import { renderHook, waitFor } from '@testing-library/react';
import { setupMockServer } from '../../../test/setupTests';
import { useTopic } from '../useTopic';

test('useTopic receives messages', async () => {
  setupMockServer('/ws/topic/news', [{ text: 'hello' }]);
  const { result } = renderHook(() => useTopic('news'));
  await waitFor(() => {
    expect(result.current).toHaveLength(1);
  });
  expect(result.current[0].text).toBe('hello');
});
