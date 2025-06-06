import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { vi } from 'vitest';
import { setupMockServer } from '../../test/setupTests';
import App from '../App';

vi.mock('../hooks/useUser', () => ({
  useUser: () => ({ interests: ['tech', 'sports'] })
}));

it('filters feed when clicking interest chip', async () => {
  setupMockServer('/ws/feed/0?backlog=100', [
    { title: 't1', topic: 'tech' },
    { title: 's1', topic: 'sports' }
  ]);

  render(<App initialUid="0" />);
  await waitFor(() => expect(document.querySelectorAll('details')).toHaveLength(1));
  fireEvent.click(screen.getByText(/Refresh/));
  await waitFor(() => expect(document.querySelectorAll('details')).toHaveLength(2));

  const section = screen.getByRole('heading', { name: 'Interests' }).parentElement as HTMLElement;
  expect(within(section).getByText('tech')).toBeInTheDocument();
  expect(within(section).getByText('sports')).toBeInTheDocument();

  fireEvent.click(within(section).getByText('tech'));
  expect(document.querySelectorAll('details')).toHaveLength(1);
  expect(screen.getByText('t1')).toBeInTheDocument();
  expect(screen.queryByText('s1')).toBeNull();

  fireEvent.click(within(section).getByText('tech'));
  expect(document.querySelectorAll('details')).toHaveLength(2);
});

