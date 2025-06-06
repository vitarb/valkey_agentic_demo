import { render, screen } from '@testing-library/react';
import { PostCard } from '../PostCard';

it('renders title, summary and tags', () => {
  render(
    <PostCard title="hello" summary="world" tags={['t1']} topic="tech" />
  );
  expect(screen.getByText('hello')).toBeInTheDocument();
  expect(screen.getByText('world')).toBeInTheDocument();
  // two chips: t1 and tech
  expect(screen.getByText('t1')).toBeInTheDocument();
  expect(screen.getByText('tech')).toBeInTheDocument();
});

import { fireEvent } from '@testing-library/react';
import { useState } from 'react';
import { toggleTopic } from '../../utils';

test('tag chip click toggles topic without opening details', () => {
  function Wrapper() {
    const [topic, setTopic] = useState<string | null>(null);
    return (
      <PostCard
        title="t"
        tags={['foo']}
        activeTopic={topic}
        onTagClick={(t) => setTopic((prev) => toggleTopic(prev, t))}
      />
    );
  }
  const { container } = render(<Wrapper />);
  const details = container.querySelector('details')!;
  const chip = screen.getByRole('button', { name: 'foo' });
  fireEvent.click(chip);
  expect(details.hasAttribute('open')).toBe(false);
  expect(screen.getByRole('button', { name: 'foo' }).className).toMatch('bg-blue-600');
  fireEvent.click(screen.getByRole('button', { name: 'foo' }));
  expect(screen.getByRole('button', { name: 'foo' }).className).not.toMatch('bg-blue-600');
});
