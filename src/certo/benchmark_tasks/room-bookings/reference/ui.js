import React from 'react';
import { CLOSE, OPEN, minutes } from './rooms.js';

const h = React.createElement;

/** The free periods of one room between OPEN and CLOSE, in time order. */
export function freeSlots(bookings) {
  const sorted = [...bookings].sort((x, y) => minutes(x.start) - minutes(y.start));
  const free = [];
  let from = OPEN;
  for (const booking of sorted) {
    if (minutes(booking.start) > minutes(from)) free.push([from, booking.start]);
    if (minutes(booking.end) > minutes(from)) from = booking.end;
  }
  if (minutes(from) < minutes(CLOSE)) free.push([from, CLOSE]);
  return free;
}

function people(n) {
  return n === 1 ? '1 person' : `${n} people`;
}

function Room({ room, bookings }) {
  const mine = bookings
    .filter((b) => b.room === room.id)
    .sort((x, y) => minutes(x.start) - minutes(y.start));
  const free = freeSlots(mine);
  return h(
    'section',
    { 'data-room': room.id },
    h('h2', null, `${room.name} (${room.capacity})`),
    mine.length > 0 &&
      h(
        'ol',
        null,
        mine.map((b) =>
          h(
            'li',
            { key: b.id, 'data-booking': String(b.id) },
            `${b.start}–${b.end} ${b.title} (${people(b.people)})`,
          ),
        ),
      ),
    h(
      'p',
      { className: 'free' },
      free.length ? `Free: ${free.map(([a, b]) => `${a}–${b}`).join(', ')}` : 'Fully booked',
    ),
  );
}

export function Timeline({ rooms, bookings }) {
  return h(
    'main',
    null,
    rooms.map((room) => h(Room, { key: room.id, room, bookings })),
  );
}
