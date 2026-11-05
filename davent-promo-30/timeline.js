// timeline.js — single source of truth. Narration segments (Gemini TTS, real audio):
//   n0001 hook    0.00 – 3.77   "¿Todavía mostrás tu negocio solo por WhatsApp y redes?"
//   n0002 journey 3.77 – 20.34  "Con DAVENT creás la web... contactan directo por tus redes."
//   n0003 promo  20.34 – 35.23  "Y con el código PROMO... treinta días de Premium, gratis."
export const BPM = 92;
export const BEAT = 60 / BPM;
export const BAR = BEAT * 4;
export const b = n => n * BEAT;
export const revealOn = (hit, dur, reveal = 0) => hit - reveal * dur;

export const DUR = 36;

export const SEG = { s1: [0, 3.77], s2: [3.77, 20.34], s3: [20.34, 35.23] };

export const SHOTS = [
  { id: 'hook',      t0: 0,     t1: 3.77 },   // chat bubbles piling up
  { id: 'register',  t0: 3.77,  t1: 8.4 },    // phone: registro real
  { id: 'dashboard', t0: 8.4,   t1: 14.2 },   // phone: dashboard + feature chips
  { id: 'gym',       t0: 14.2,  t1: 20.34 },  // web gimnasio publicada, full bleed
  { id: 'promo',     t0: 20.34, t1: 24.5 },   // starburst PROMO
  { id: 'brand',     t0: 24.5,  t1: 31.5 },   // DAVENT + tagline
  { id: 'endcard',   t0: 31.5,  t1: DUR },    // cupón final, hold
];

export const BUBBLES = [0.55, 1.25, 1.95, 2.65]; // pop times, scene 1
export const CHIPS = [9.4, 10.4, 11.4, 12.4];    // feature chips, dashboard shot

export const CUES = [
  ...BUBBLES.map(t => ({ t, sfx: 'pop' })),
  { t: 3.77, sfx: 'whoosh' },
  { t: 8.4, sfx: 'whoosh' },
  ...CHIPS.map(t => ({ t, sfx: 'tick' })),
  { t: 14.2, sfx: 'whoosh' },
  { t: 20.34, sfx: 'impact' },
  { t: 21.1, sfx: 'chime' },
  { t: 24.5, sfx: 'whoosh' },
  { t: 31.5, sfx: 'shimmer' },
];

export const HOLDS = [[32, DUR]];
export const DROPS = [20.34];
