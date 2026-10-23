export const ROOMS = [
  { id: 'a', name: 'Aurora', capacity: 4 },
  { id: 'b', name: 'Borealis', capacity: 8 },
  { id: 'c', name: 'Cirrus', capacity: 2 },
];

export const OPEN = '08:00';
export const CLOSE = '20:00';
export const MAX_MINUTES = 4 * 60;

/** Minutes since midnight for "HH:MM", or null if it isn't a time. */
export function minutes(text) {
  const match = typeof text === 'string' && /^(\d\d):(\d\d)$/.exec(text);
  if (!match) return null;
  const [h, m] = [Number(match[1]), Number(match[2])];
  return h < 24 && m < 60 ? h * 60 + m : null;
}
