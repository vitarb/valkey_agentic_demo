import { useEffect, useState } from 'react';
import { useSocket } from './useSocket';
import { Message } from './useFeed';

export interface TopicState {
  messages: Message[];
  pending: Message[];
  ready: boolean;
  loading: boolean;
  refresh: () => void;
}

const normalize = (raw: any): Message => ({
  id: raw.id ?? crypto.randomUUID(),
  title: raw.title ?? raw.text ?? '[no-title]',
  summary: raw.summary ?? raw.body ?? raw.text,
  body: raw.body,
  tags: raw.tags ?? (raw.topic ? [raw.topic] : []),
  topic: raw.topic,
});

export function useTopic(slug: string): TopicState {
  const { messages: socketMsgs, ready } = useSocket(
    `/ws/topic/${slug}?backlog=50`,
    normalize
  );
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    setMessages([]);
    setPending([]);
    setLoading(true);
  }, [slug]);
  useEffect(() => {
    if (socketMsgs.length === 0) return;
    const start = messages.length + pending.length;
    const newItems = socketMsgs.slice(start);
    if (newItems.length) {
      if (loading) {
        setMessages(newItems);
        setLoading(false);
      } else {
        setPending((p) => [...p, ...newItems]);
      }
    }
  }, [socketMsgs]);
  useEffect(() => {
    if (messages.length === 0 && pending.length > 0) {
      setMessages(pending);
      setPending([]);
    }
  }, [pending]);
  const refresh = () => {
    if (pending.length) {
      setMessages((m) => [...pending, ...m]);
      setPending([]);
    }
  };
  return { messages, pending, ready, loading, refresh };
}
