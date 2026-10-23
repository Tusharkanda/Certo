import http from 'node:http';

// The booking API: see the task. Returns a server that isn't listening yet.
export function createApp() {
  return http.createServer((req, res) => {
    res.writeHead(501, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'not implemented' }));
  });
}
