export function toggleTopic(current: string | null, tag: string): string | null {
  return current === tag ? null : tag;
}
