// timeline.js — shared clock for picture (index.html) and sound (score.mjs).
// Narration: TTS real segment times from audio/narration.json (Gemini, voice Kore).
//   s1 "Tu tienda, tu panel, tu control."            0.000 – 2.851
//   s2 "Productos, diseño y ventas en un solo lugar." 2.851 – 6.582
//   s3 "Davent. Publicá hoy."                        6.582 – 8.913
// Picture: dashboard builds under s1, three feature beats under s2,
// logo lands with s3, end card holds to 15s.

export const BPM = 120;
export const BEAT = 60 / BPM;
export const BAR = BEAT * 4;
export const b = n => n * BEAT;
export const revealOn = (hit, dur, reveal = 0) => hit - reveal * dur;

export const DUR = 15;

export const NAR = { s1: [0.0, 2.851], s2: [2.851, 6.582], s3: [6.582, 8.913] };
export const LOGO_HIT = 6.9;      // wordmark lands as "Davent" is heard
export const CARD_IN = 9.2;       // end card settles

export const SHOTS = [
  { id: 'build', t0: 0, t1: 2.851 },        // dashboard springs together
  { id: 'features', t0: 2.851, t1: 6.582 }, // productos / diseño / ventas beats
  { id: 'logo', t0: 6.582, t1: 9.2 },       // dashboard recedes, wordmark lands
  { id: 'card', t0: 9.2, t1: DUR },         // end card hold + CTA
];

export const CUES = [
  { t: 0.15, sfx: 'pop' },                       // rail lands
  { t: 0.5, sfx: 'tick' }, { t: 0.8, sfx: 'tick' }, { t: 1.1, sfx: 'tick' }, { t: 1.4, sfx: 'tick' }, // cards
  { t: 2.851, sfx: 'whoosh' },                   // into features
  { t: 3.1, sfx: 'tick' }, { t: 4.35, sfx: 'tick' }, { t: 5.55, sfx: 'tick' },  // productos/diseño/ventas
  { t: 6.582, sfx: 'whoosh' },                   // dashboard recedes
  { t: LOGO_HIT, sfx: 'impact' },                // "Davent" lands
  { t: CARD_IN, sfx: 'shimmer' },                // end card
];

export const HOLDS = [[10.5, DUR]];              // end card breathing room
export const DROPS = [LOGO_HIT];                 // breath before the logo hit
