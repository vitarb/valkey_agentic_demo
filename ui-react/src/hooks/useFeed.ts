import { useEffect, useState } from 'react';

interface Message {
  text: string;
}

function socketBase(): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.hostname}:8000`;
}

function useSocket(path: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  useEffect(() => {
    const ws = new WebSocket(`${socketBase()}${path}`);
    ws.onmessage = (ev) => setMessages((m) => [...m, JSON.parse(ev.data)]);
    return () => ws.close();
  }, [path]);
  return messages;
}

export function useFeed(uid: string) {
  return useSocket(`/ws/feed/${uid}`);
}
