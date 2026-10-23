// Hidden tests: the HTTP API on a local port, and the components
// rendered with react-dom/server.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createApp } from '../server.js';
import { Timeline, freeSlots } from '../ui.js';

const ROOMS = [
  { id: 'a', name: 'Aurora', capacity: 4 },
  { id: 'b', name: 'Borealis', capacity: 8 },
  { id: 'c', name: 'Cirrus', capacity: 2 },
];

async function app(fn) {
  const server = createApp();
  server.listen(0, '127.0.0.1');
  await new Promise((resolve) => server.once('listening', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  const call = async (method, path, body) => {
    const res = await fetch(base + path, {
      method,
      body: body === undefined ? undefined : typeof body === 'string' ? body : JSON.stringify(body),
    });
    const text = await res.text();
    const type = res.headers.get('content-type') || '';
    let json;
    if (type.startsWith('application/json')) json = JSON.parse(text);
    if (res.status >= 400) {
      assert.ok(type.startsWith('application/json'), `${method} ${path}: error as ${type}`);
      assert.equal(typeof json.error, 'string', `${method} ${path}: ${text}`);
      assert.ok(json.error.length > 0);
      assert.deepEqual(Object.keys(json), ['error']);
    }
    return { status: res.status, json, text, type };
  };
  try {
    await fn(call);
  } finally {
    server.closeAllConnections?.();
    server.close();
  }
}

const book = (over = {}) => ({ room: 'a', title: 'Standup', start: '09:00', end: '10:30', people: 3, ...over });

test('hidden: rooms, and bookings with ids never reused', async () => {
  await app(async (call) => {
    const rooms = await call('GET', '/api/rooms');
    assert.equal(rooms.status, 200);
    assert.deepEqual(rooms.json, ROOMS);
    assert.deepEqual((await call('GET', '/api/bookings')).json, []);
    const one = await call('POST', '/api/bookings', book());
    assert.equal(one.status, 201);
    assert.deepEqual(one.json, { id: 1, ...book() });
    assert.equal((await call('POST', '/api/bookings', book({ start: '11:00', end: '12:00' }))).json.id, 2);
    const del = await call('DELETE', '/api/bookings/2');
    assert.equal(del.status, 204);
    assert.equal(del.text, '');
    assert.equal((await call('DELETE', '/api/bookings/2')).status, 404);
    assert.equal((await call('POST', '/api/bookings', book({ start: '11:00', end: '12:00' }))).json.id, 3);
  });
});

test('hidden: the list is sorted by room, then start', async () => {
  await app(async (call) => {
    await call('POST', '/api/bookings', book({ room: 'b', start: '13:00', end: '14:00' }));
    await call('POST', '/api/bookings', book({ room: 'a', start: '15:00', end: '16:00' }));
    await call('POST', '/api/bookings', book({ room: 'b', start: '08:00', end: '09:00' }));
    await call('POST', '/api/bookings', book({ room: 'a', start: '10:00', end: '11:00' }));
    const order = (await call('GET', '/api/bookings')).json.map((b) => `${b.room}${b.start}`);
    assert.deepEqual(order, ['a10:00', 'a15:00', 'b08:00', 'b13:00']);
  });
});

test('hidden: time rules', async () => {
  await app(async (call) => {
    const ok = [
      { start: '08:00', end: '09:00' },
      { start: '16:00', end: '20:00' }, // 4 hours, ends at closing
      { start: '12:15', end: '12:30' },
    ];
    for (const t of ok) assert.equal((await call('POST', '/api/bookings', book(t))).status, 201, JSON.stringify(t));
    const bad = [
      { start: '07:45', end: '08:30' },
      { start: '19:45', end: '20:15' },
      { start: '09:10', end: '10:00' },
      { start: '10:00', end: '10:00' },
      { start: '11:00', end: '10:00' },
      { start: '09:00', end: '13:15' }, // 4 h 15
      { start: '9:00', end: '10:00' },
      { start: '24:00', end: '24:15' },
      { start: '10:60', end: '11:00' },
    ];
    for (const t of bad) {
      assert.equal((await call('POST', '/api/bookings', book({ room: 'b', ...t }))).status, 400, JSON.stringify(t));
    }
  });
});

test('hidden: overlaps in the same room only', async () => {
  await app(async (call) => {
    assert.equal((await call('POST', '/api/bookings', book())).status, 201); // a 09:00-10:30
    for (const t of [
      { start: '10:00', end: '11:00' },
      { start: '08:00', end: '12:00' },
      { start: '09:30', end: '10:00' },
      { start: '08:30', end: '09:15' },
    ]) {
      assert.equal((await call('POST', '/api/bookings', book(t))).status, 409, JSON.stringify(t));
    }
    assert.equal((await call('POST', '/api/bookings', book({ start: '10:30', end: '11:00' }))).status, 201);
    assert.equal((await call('POST', '/api/bookings', book({ start: '08:00', end: '09:00' }))).status, 201);
    assert.equal((await call('POST', '/api/bookings', book({ room: 'b' }))).status, 201);
    await call('DELETE', '/api/bookings/1');
    assert.equal((await call('POST', '/api/bookings', book({ start: '09:00', end: '10:30' }))).status, 201);
  });
});

test('hidden: bad bodies, rooms and people', async () => {
  await app(async (call) => {
    const bodies = [
      'not json',
      '[]',
      'null',
      { room: 'a', title: 'x', start: '09:00', end: '10:00' },
      { ...book(), extra: true },
      book({ people: '3' }),
      book({ people: 2.5 }),
      book({ start: 900 }),
      book({ room: 'd' }),
      book({ title: '' }),
      book({ people: 0 }),
      book({ people: 5 }),
      book({ room: 'c', people: 3 }),
    ];
    for (const body of bodies) {
      assert.equal((await call('POST', '/api/bookings', body)).status, 400, JSON.stringify(body));
    }
    assert.equal((await call('POST', '/api/bookings', book({ room: 'b', people: 8 }))).status, 201);
    assert.equal((await call('POST', '/api/bookings', book({ room: 'c', people: 1 }))).status, 201);
    assert.equal((await call('GET', '/api/nothing')).status, 404);
    assert.equal((await call('DELETE', '/api/bookings/99')).status, 404);
  });
});

test('hidden: free slots', () => {
  const b = (start, end) => ({ start, end });
  assert.deepEqual(freeSlots([]), [['08:00', '20:00']]);
  assert.deepEqual(freeSlots([b('08:00', '12:00'), b('12:00', '16:00'), b('16:00', '20:00')]), []);
  assert.deepEqual(freeSlots([b('15:00', '16:00'), b('09:00', '10:00'), b('10:00', '11:30')]), [
    ['08:00', '09:00'],
    ['11:30', '15:00'],
    ['16:00', '20:00'],
  ]);
  assert.deepEqual(freeSlots([b('08:00', '08:15'), b('19:45', '20:00')]), [['08:15', '19:45']]);
});

const render = (props) => renderToStaticMarkup(React.createElement(Timeline, props));

test('hidden: the timeline', () => {
  const html = render({
    rooms: ROOMS,
    bookings: [
      { id: 7, room: 'a', title: 'Review', start: '13:00', end: '14:00', people: 4 },
      { id: 3, room: 'a', title: 'Standup', start: '09:00', end: '10:30', people: 1 },
      { id: 4, room: 'c', title: 'All day', start: '08:00', end: '12:00', people: 2 },
      { id: 5, room: 'c', title: 'Afternoon', start: '12:00', end: '16:00', people: 2 },
      { id: 6, room: 'c', title: 'Evening', start: '16:00', end: '20:00', people: 2 },
    ],
  });
  const sections = [...html.matchAll(/<section[^>]*data-room="(\w)"[^>]*>([\s\S]*?)<\/section>/g)];
  assert.deepEqual(sections.map((s) => s[1]), ['a', 'b', 'c']);
  const [a, b, c] = sections.map((s) => s[2]);
  assert.match(a, /<h2>Aurora \(4\)<\/h2>/);
  const items = [...a.matchAll(/<li[^>]*data-booking="(\d+)"[^>]*>([^<]*)<\/li>/g)].map((m) => [m[1], m[2]]);
  assert.deepEqual(items, [
    ['3', '09:00–10:30 Standup (1 person)'],
    ['7', '13:00–14:00 Review (4 people)'],
  ]);
  assert.match(a, /<ol[^>]*>/);
  assert.match(a, /<p class="free">Free: 08:00–09:00, 10:30–13:00, 14:00–20:00<\/p>/);
  assert.match(b, /<h2>Borealis \(8\)<\/h2>/);
  assert.doesNotMatch(b, /<ol|<li/);
  assert.match(b, /<p class="free">Free: 08:00–20:00<\/p>/);
  assert.match(c, /<p class="free">Fully booked<\/p>/);
});

test('hidden: rooms in the order given, titles as text', () => {
  const html = render({
    rooms: [ROOMS[2], ROOMS[0]],
    bookings: [{ id: 1, room: 'c', title: '<b>Q&A</b> "x"', start: '10:00', end: '11:00', people: 2 }],
  });
  assert.deepEqual([...html.matchAll(/data-room="(\w)"/g)].map((m) => m[1]), ['c', 'a']);
  assert.ok(!html.includes('<b>Q'), 'the title went in as HTML');
  assert.match(html, /&lt;b&gt;Q&amp;A&lt;\/b&gt;/);
});

test('hidden: the page shows the bookings', async () => {
  await app(async (call) => {
    await call('POST', '/api/bookings', book({ room: 'b', title: '<i>Plan</i>', start: '14:00', end: '15:00' }));
    const page = await call('GET', '/');
    assert.equal(page.status, 200);
    assert.ok(page.type.startsWith('text/html'), page.type);
    const root = /<div id="root">([\s\S]*)<\/div>/.exec(page.text);
    assert.ok(root, 'no <div id="root">');
    assert.deepEqual([...root[1].matchAll(/data-room="(\w)"/g)].map((m) => m[1]), ['a', 'b', 'c']);
    assert.match(root[1], /data-booking="1"/);
    assert.match(root[1], /&lt;i&gt;Plan&lt;\/i&gt;/);
  });
});
