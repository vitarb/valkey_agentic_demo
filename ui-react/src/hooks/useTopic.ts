import { useEffect, useState } from 'react';

interface Message {
  text: string;
}

function useSocket(path: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost${path}`);
    ws.onmessage = (ev) => setMessages((m) => [...m, JSON.parse(ev.data)]);
    return () => ws.close();
  }, [path]);
  return messages;
}

export function useTopic(slug: string) {
  return useSocket(`/ws/topic/${slug}`);
}
