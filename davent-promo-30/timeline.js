// timeline.js — single source of truth. Versión 25s (estado WhatsApp):
// voz = gancho (n0001) + cierre con cupón (n0003); el segmento medio se omitió.
//   n0001 hook    audio 0.00 – 3.77    → video 0 – 3.77
//   n0003 promo   audio 9.00 – 23.89   → video 9.0 – 23.89 (silencio 3.77–9.0 de música)
export const BPM = 92;
export const BEAT = 60 / BPM;
export const BAR = BEAT * 4;
export const b = n => n * BEAT;
export const revealOn = (hit, dur, reveal = 0) => hit - reveal * dur;

export const DUR = 25;

export const SEG = { s1: [0, 3.77], s3: [9.0, 23.89] };

export const SHOTS = [
  { id: 'hook',      t0: 0,    t1: 3.77 },
  { id: 'register',  t0: 3.77, t1: 5.9 },
  { id: 'dashboard', t0: 5.9,  t1: 7.7 },
  { id: 'gym',       t0: 7.7,  t1: 9.0 },
  { id: 'promo',     t0: 9.0,  t1: 12.6 },
  { id: 'site',      t0: 12.6, t1: 17.0 },
  { id: 'endcard',   t0: 17.0, t1: DUR },
];

export const BUBBLES = [0.55, 1.25, 1.95, 2.65];
export const CHIPS = [6.2, 6.55, 6.9, 7.25];

export const CUES = [
  ...BUBBLES.map(t => ({ t, sfx: 'pop' })),
  { t: 3.77, sfx: 'whoosh' },
  { t: 5.9, sfx: 'whoosh' },
  { t: 7.7, sfx: 'whoosh' },
  ...CHIPS.map(t => ({ t, sfx: 'tick' })),
  { t: 9.0, sfx: 'impact' },
  { t: 9.7, sfx: 'chime' },
  { t: 12.6, sfx: 'whoosh' },
  { t: 17.0, sfx: 'shimmer' },
];

export const HOLDS = [[21.5, DUR]];
export const DROPS = [9.0];
