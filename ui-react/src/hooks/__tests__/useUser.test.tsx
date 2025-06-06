import { renderHook, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { useUser } from '../useUser';

it('builds URL from window.location and returns data', async () => {
  const originalLocation = window.location;
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: { protocol: 'https:', hostname: 'demo.local' } as Location,
  });
  const mockFetch = vi.fn(() =>
    Promise.resolve(new Response(JSON.stringify({ interests: ['x'] })))
  );
  vi.stubGlobal('fetch', mockFetch);

  const { result } = renderHook(() => useUser('5'));
  await waitFor(() => expect(result.current).not.toBeNull());

  expect(mockFetch).toHaveBeenCalledWith('https://demo.local:8000/user/5');
  expect(result.current).toEqual({ interests: ['x'] });

  vi.unstubAllGlobals();
  Object.defineProperty(window, 'location', { configurable: true, value: originalLocation });
});
