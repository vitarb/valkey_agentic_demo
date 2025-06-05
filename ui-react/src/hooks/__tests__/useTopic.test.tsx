import { renderHook, waitFor } from '@testing-library/react';
import { setupMockServer } from '../../../test/setupTests';
import { useTopic } from '../useTopic';

test('useTopic receives messages', async () => {
  setupMockServer('/ws/topic/technology', [{ title: 'hello' }]);
  const { result } = renderHook(() => useTopic('technology'));
  await waitFor(() => {
    expect(result.current.messages).toHaveLength(1);
  });
  expect(result.current.messages[0].text).toBe('hello');
});
