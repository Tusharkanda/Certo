import assert from 'node:assert/strict';
import { test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createApp } from '../server.js';
import { Timeline, freeSlots } from '../ui.js';

async function withServer(fn) {
  const server = createApp().listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    await fn(base);
  } finally {
    server.close();
  }
}

test('free slots merge touching and overlapping bookings', () => {
  assert.deepEqual(freeSlots([]), [['08:00', '20:00']]);
  assert.deepEqual(
    freeSlots([
      { start: '10:00', end: '11:00' },
      { start: '09:00', end: '10:00' },
    ]),
    [['08:00', '09:00'], ['11:00', '20:00']],
  );
});

test('a booking, then an overlap', async () => {
  await withServer(async (base) => {
    const post = (body) =>
      fetch(`${base}/api/bookings`, { method: 'POST', body: JSON.stringify(body) });
    const one = { room: 'a', title: 'Standup', start: '09:00', end: '10:30', people: 3 };
    assert.equal((await post(one)).status, 201);
    assert.equal((await post({ ...one, start: '10:00', end: '11:00' })).status, 409);
    assert.equal((await post({ ...one, start: '10:30', end: '11:00' })).status, 201);
  });
});

test('the timeline shows one person and the free time', () => {
  const html = renderToStaticMarkup(
    React.createElement(Timeline, {
      rooms: [{ id: 'c', name: 'Cirrus', capacity: 2 }],
      bookings: [{ id: 1, room: 'c', title: 'Call', start: '08:00', end: '09:00', people: 1 }],
    }),
  );
  assert.match(html, /<li data-booking="1">08:00–09:00 Call \(1 person\)<\/li>/);
  assert.match(html, /<p class="free">Free: 09:00–20:00<\/p>/);
});
