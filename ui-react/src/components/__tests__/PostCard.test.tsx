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
