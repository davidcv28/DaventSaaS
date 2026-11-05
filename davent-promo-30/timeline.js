// timeline.js — single source of truth. Narration segments (Gemini TTS, real audio):
//   n0001 hook    0.00 – 3.77   "¿Todavía mostrás tu negocio solo por WhatsApp y redes?"
//   n0002 journey 3.77 – 20.34  "Con DAVENT creás la web... contactan directo por tus redes."
//   n0003 promo  20.34 – 35.23  "Y con el código PROMO... treinta días de Premium, gratis."
export const BPM = 92;
export const BEAT = 60 / BPM;
export const BAR = BEAT * 4;
export const b = n => n * BEAT;
export const revealOn = (hit, dur, reveal = 0) => hit - reveal * dur;

export const DUR = 45;

export const SEG = { s1: [0, 3.77], s2: [3.77, 20.34], s3: [20.34, 35.23] };

export const SHOTS = [
  { id: 'hook',      t0: 0,     t1: 3.77 },   // chat bubbles piling up
  { id: 'register',  t0: 3.77,  t1: 8.0 },    // phone: registro real
  { id: 'dashboard', t0: 8.0,   t1: 11.5 },   // phone: dashboard + feature chips
  { id: 'designs',   t0: 11.5,  t1: 20.34 },  // montaje de plantillas → gimnasio
  { id: 'promo',     t0: 20.34, t1: 26.0 },   // starburst PROMO
  { id: 'site',      t0: 26.0,  t1: 36.0 },   // davent.com.ar real
  { id: 'endcard',   t0: 36.0,  t1: DUR },    // cupón final, hold
];

export const BUBBLES = [0.55, 1.25, 1.95, 2.65]; // pop times, scene 1
export const CHIPS = [8.7, 9.5, 10.3, 11.1];     // feature chips, dashboard shot
export const DESIGNS = [                          // montaje de plantillas → cierra en gimnasio publicado
  { id: 'moda',      name: 'MODA',       t0: 11.5 },
  { id: 'impacto',   name: 'IMPACTO',    t0: 13.2 },
  { id: 'moderntec', name: 'MODERNTEC',  t0: 14.9 },
  { id: 'viajero',   name: 'VIAJERO',    t0: 16.6 },
  { id: 'gym',       name: 'GIMNASIO',   t0: 18.3 },
];

export const CUES = [
  ...BUBBLES.map(t => ({ t, sfx: 'pop' })),
  { t: 3.77, sfx: 'whoosh' },
  { t: 8.0, sfx: 'whoosh' },
  ...CHIPS.map(t => ({ t, sfx: 'tick' })),
  { t: 11.5, sfx: 'whoosh' },
  ...DESIGNS.slice(1).map(d => ({ t: d.t0, sfx: 'tick' })),
  { t: 20.34, sfx: 'impact' },
  { t: 21.1, sfx: 'chime' },
  { t: 26.0, sfx: 'whoosh' },
  { t: 36.0, sfx: 'shimmer' },
];

export const HOLDS = [[41.5, DUR]];
export const DROPS = [20.34];
