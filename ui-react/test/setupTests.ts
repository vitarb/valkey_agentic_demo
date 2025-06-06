import { afterEach } from 'vitest';
import '@testing-library/jest-dom';
import { Server } from 'mock-socket';

const servers: Server[] = [];

export function setupMockServer(path: string, messages: unknown[]) {
  const server = new Server(`ws://localhost:8000${path}`);
  let sock: WebSocket | null = null;
  server.on('connection', (socket) => {
    sock = socket as unknown as WebSocket;
    messages.forEach((m, i) =>
      setTimeout(() => socket.send(JSON.stringify(m)), i * 10)
    );
  });
  servers.push(server);
  return {
    send: (msg: string) => sock?.send(msg),
    stop: () => server.stop(),
  } as const;
}

afterEach(() => {
  servers.forEach((s) => s.stop());
  servers.length = 0;
});
