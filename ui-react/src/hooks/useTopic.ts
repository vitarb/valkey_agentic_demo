import { useSocket } from './useSocket';

export interface Message {
  id: string;
  title: string;
  summary?: string;
  body?: string;
  tags: string[];
  topic?: string;
}

const normalize = (raw: any): Message => ({
  id: raw.id ?? crypto.randomUUID(),
  title: raw.title ?? raw.text ?? '[no-title]',
  summary: raw.summary ?? raw.body ?? raw.text,
  body: raw.body,
  tags: raw.tags ?? (raw.topic ? [raw.topic] : []),
  topic: raw.topic,
});

export function useTopic(slug: string) {
  return useSocket(`/ws/topic/${slug}`, normalize);
}
