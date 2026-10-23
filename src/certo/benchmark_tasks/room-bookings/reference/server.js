import http from 'node:http';
import { fileURLToPath } from 'node:url';
import React from 'react';
import { renderToString } from 'react-dom/server';
import { CLOSE, MAX_MINUTES, OPEN, ROOMS, minutes } from './rooms.js';
import { Timeline } from './ui.js';

const FIELDS = ['room', 'title', 'start', 'end', 'people'];

class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

/** The reason `input` isn't a valid booking, or null. */
function invalid(input) {
  if (typeof input !== 'object' || input === null || Array.isArray(input)) {
    return 'the body must be a JSON object';
  }
  const keys = Object.keys(input).sort();
  if (keys.join() !== [...FIELDS].sort().join()) return `the fields must be ${FIELDS.join(', ')}`;
  const { room, title, start, end, people } = input;
  if (![room, title, start, end].every((v) => typeof v === 'string')) {
    return 'room, title, start and end must be strings';
  }
  if (!Number.isInteger(people)) return 'people must be a whole number';
  const found = ROOMS.find((r) => r.id === room);
  if (!found) return `no room ${room}`;
  if (title === '') return 'the title must not be empty';
  const [s, e] = [minutes(start), minutes(end)];
  for (const t of [s, e]) {
    if (t === null || t % 15 !== 0 || t < minutes(OPEN) || t > minutes(CLOSE)) {
      return `times must be quarter hours from ${OPEN} to ${CLOSE}`;
    }
  }
  if (s >= e) return 'start must be before end';
  if (e - s > MAX_MINUTES) return 'a booking lasts at most 4 hours';
  if (people < 1 || people > found.capacity) return `people must be 1 to ${found.capacity}`;
  return null;
}

function sorted(bookings) {
  return [...bookings].sort(
    (x, y) => x.room.localeCompare(y.room) || minutes(x.start) - minutes(y.start),
  );
}

function page(bookings) {
  const body = renderToString(React.createElement(Timeline, { rooms: ROOMS, bookings }));
  return `<!doctype html><html><head><meta charset="utf-8"><title>Rooms</title></head><body><div id="root">${body}</div></body></html>`;
}

async function readJson(req) {
  let text = '';
  for await (const chunk of req) text += chunk;
  try {
    return JSON.parse(text);
  } catch {
    throw new HttpError(400, 'the body must be JSON');
  }
}

export function createApp() {
  const bookings = new Map();
  let nextId = 1;

  async function route(req) {
    const { pathname } = new URL(req.url, 'http://localhost');
    if (req.method === 'GET' && pathname === '/') return [200, page([...bookings.values()]), 'html'];
    if (req.method === 'GET' && pathname === '/api/rooms') return [200, ROOMS];
    if (req.method === 'GET' && pathname === '/api/bookings') {
      return [200, sorted([...bookings.values()])];
    }
    if (req.method === 'POST' && pathname === '/api/bookings') {
      const input = await readJson(req);
      const reason = invalid(input);
      if (reason) throw new HttpError(400, reason);
      const [s, e] = [minutes(input.start), minutes(input.end)];
      for (const other of bookings.values()) {
        if (other.room === input.room && s < minutes(other.end) && minutes(other.start) < e) {
          throw new HttpError(409, `room ${input.room} is booked from ${other.start} to ${other.end}`);
        }
      }
      const booking = { id: nextId++, ...input };
      bookings.set(booking.id, booking);
      return [201, booking];
    }
    const match = /^\/api\/bookings\/([^/]+)$/.exec(pathname);
    if (req.method === 'DELETE' && match) {
      const id = Number(match[1]);
      if (!bookings.delete(id)) throw new HttpError(404, `no booking ${match[1]}`);
      return [204, null];
    }
    throw new HttpError(404, 'not found');
  }

  return http.createServer(async (req, res) => {
    let status, body, kind;
    try {
      [status, body, kind] = await route(req);
    } catch (err) {
      [status, body] = err instanceof HttpError ? [err.status, { error: err.message }] : [500, { error: 'internal error' }];
    }
    if (status === 204) {
      res.writeHead(204).end();
    } else if (kind === 'html') {
      res.writeHead(status, { 'Content-Type': 'text/html; charset=utf-8' }).end(body);
    } else {
      res.writeHead(status, { 'Content-Type': 'application/json' }).end(JSON.stringify(body));
    }
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  createApp().listen(Number(process.env.PORT) || 3000);
}
