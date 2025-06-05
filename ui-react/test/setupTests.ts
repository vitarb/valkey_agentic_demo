import { afterEach } from 'vitest';
import { Server } from 'mock-socket';

const servers: Server[] = [];

export function setupMockServer(path: string, messages: unknown[]) {
  const server = new Server(`ws://localhost:8000${path}`);
  server.on('connection', (socket) => {
    messages.forEach((m) => socket.send(JSON.stringify(m)));
  });
  servers.push(server);
  return server;
}

afterEach(() => {
  servers.forEach((s) => s.stop());
  servers.length = 0;
});
