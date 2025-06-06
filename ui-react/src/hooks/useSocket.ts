import { useEffect, useState } from 'react';

function socketBase(): string {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.hostname}:8000`;
}

export interface SocketState<T> {
  messages: T[];
  ready: boolean;
}

export function useSocket<T>(path: string, normalize: (raw: any) => T): SocketState<T> {
  const [messages, setMessages] = useState<T[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setMessages([]);
    let isMounted = true;
    let ws: WebSocket | null = null;
    let retry = 0;

    const connect = () => {
      ws = new WebSocket(`${socketBase()}${path}`);
      ws.onopen = () => {
        if (!isMounted) return;
        retry = 0;
        setReady(true);
      };
      ws.onmessage = (ev) => {
        if (!isMounted) return;
        setMessages((m) => [...m, normalize(JSON.parse(ev.data))]);
      };
      const handleClose = () => {
        if (!isMounted) return;
        setReady(false);
        retry += 1;
        const timeout = Math.min(1000 * 2 ** retry, 5000);
        setTimeout(() => {
          if (isMounted) connect();
        }, timeout);
      };
      ws.onclose = handleClose;
      ws.onerror = handleClose;
    };

    connect();

    return () => {
      isMounted = false;
      setReady(false);
      ws?.close();
    };
  }, [path]);

  return { messages, ready };
}
