# Room bookings: an API and its React page

Build a one-day meeting-room booking app in Node: an HTTP API and a page
rendered with React. `package.json` and `package-lock.json` are here,
with `react` and `react-dom` 19.0.0: install them with `npm ci` and add
no other packages. Use ES modules (`"type": "module"` is set). Write
components with `React.createElement`, not JSX: nothing compiles the
code. Keep `npm test` (`node --test`) passing, and add tests of your own.

The rooms are fixed:

| id | name | capacity |
|---|---|---|
| `a` | Aurora | 4 |
| `b` | Borealis | 8 |
| `c` | Cirrus | 2 |

Times are `"HH:MM"` strings on the same day.

## `server.js`

Export `createApp()`, which returns a Node `http.Server` that isn't
listening yet; each call starts with no bookings. `node server.js`
listens on the port in `PORT`, or 3000. Every JSON answer has
`Content-Type: application/json`; every error is `{"error": "a message"}`.

- `GET /api/rooms`: `200`, the three rooms as
  `[{"id": "a", "name": "Aurora", "capacity": 4}, ...]` in id order.
- `GET /api/bookings`: `200`, every booking, sorted by room id, then by
  start time.
- `POST /api/bookings` with
  `{"room": "a", "title": "...", "start": "09:00", "end": "10:30", "people": 3}`:
  `201` and the booking with an `"id"` added (1, 2, 3, ... never
  reused). A booking must follow all of these rules, or the answer is a
  `400`:
  - the body is a JSON object with exactly these five fields; `room`,
    `title`, `start` and `end` are strings, `people` a whole number;
  - `room` is one of the rooms; `title` isn't empty;
  - `start` and `end` are valid times on a quarter hour (`:00`, `:15`,
    `:30`, `:45`), from 08:00 to 20:00 included; `start` is before
    `end`, and the booking lasts at most 4 hours;
  - `people` is from 1 to the room's capacity.

  A booking that overlaps another one in the same room is a `409`. One
  that starts exactly when another ends doesn't overlap.
- `DELETE /api/bookings/{id}`: `204` with no body, or `404` if there is
  no such booking.
- `GET /`: `200`, `Content-Type: text/html`, a page whose
  `<div id="root">` holds the `Timeline` below, rendered on the server
  with the current rooms and bookings.
- Any other path is a `404`, with a JSON error.

## `ui.js`

Export:

- `freeSlots(bookings)`: for the bookings of one room (in any order),
  the free periods between 08:00 and 20:00, as `[["08:00", "09:00"],
  ["10:30", "20:00"]]`, in time order. Bookings that touch leave no free
  period between them; a room with no bookings is free
  `[["08:00", "20:00"]]`, and a fully booked one `[]`.
- `Timeline({ rooms, bookings })`: a React component. For each room, in
  the order given, a `<section data-room="ID">` holding:
  - `<h2>NAME (CAPACITY)</h2>`, for example `<h2>Aurora (4)</h2>`;
  - when the room has bookings, an `<ol>` with one
    `<li data-booking="ID">START–END TITLE (N people)</li>` per booking,
    by start time, for example `09:00–10:30 Standup (3 people)`, with an
    en dash (`–`) between the times, and `(1 person)` for one;
  - `<p class="free">Free: 08:00–09:00, 10:30–20:00</p>`, listing
    `freeSlots` the same way, or `<p class="free">Fully booked</p>`.

Titles are shown as text, never as HTML.
