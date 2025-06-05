import { useSocket } from './useSocket';

export interface Message {
  id: string;
  text: string;
}

const normalize = (raw: any): Message => ({
  id: raw.id ?? crypto.randomUUID(),
  text:
    raw.text ??
    raw.title ??
    raw.summary ??
    raw.body?.slice(0, 120) ??
    '[no-content]',
});

export function useTopic(slug: string) {
  return useSocket(`/ws/topic/${slug}`, normalize);
}
