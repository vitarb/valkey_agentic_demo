import { toggleTopic } from '../utils';

test('toggleTopic sets and clears topic', () => {
  expect(toggleTopic(null, 'a')).toBe('a');
  expect(toggleTopic('a', 'a')).toBeNull();
  expect(toggleTopic('a', 'b')).toBe('b');
});
