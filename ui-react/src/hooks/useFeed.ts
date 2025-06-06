import { useEffect, useState } from 'react';
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

export interface FeedState {
  messages: Message[];
  pending: Message[];
  ready: boolean;
  refresh: () => void;
}

export function useFeed(uid: string): FeedState {
  const { messages: socketMsgs, ready } = useSocket(`/ws/feed/${uid}`, normalize);
  const [messages, setMessages] = useState<Message[]>([]);
  const [pending, setPending] = useState<Message[]>([]);
  useEffect(() => {
    setMessages([]);
    setPending([]);
  }, [uid]);
  useEffect(() => {
    if (socketMsgs.length === 0) return;
    const start = messages.length + pending.length;
    const newItems = socketMsgs.slice(start);
    if (newItems.length) {
      setPending((p) => [...p, ...newItems]);
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
  return { messages, pending, ready, refresh };
}
