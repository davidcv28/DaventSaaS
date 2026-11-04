// timeline.js — reloj compartido por imagen (index.html) y sonido (score.mjs).
// Voz: tiempos reales de Gemini TTS (audio/narration.json, voz Kore).
//   s1 "Vender solo por redes no alcanza…"            0.000 –  8.811
//   s2 "DAVENT te da tu web propia…"                  8.811 – 17.422
//   s3 "Y no es solo para tiendas…"                  17.422 – 25.873
//   s4 "Sin programar… davent.com.ar… código PROMO"   25.873 – 36.164
// Imagen: 8 tomas reales del sistema (capturas móviles) + placa final.

export const BPM = 96;
export const BEAT = 60 / BPM;
export const BAR = BEAT * 4;
export const b = n => n * BEAT;

export const DUR = 37.5;

export const NAR = {
  s1: [0.0, 8.811],
  s2: [8.811, 17.422],
  s3: [17.422, 25.873],
  s4: [25.873, 36.164],
};

export const END_T = 29.6;
export const LOGO_HIT = 30.1;

// pan: desplazamiento vertical en píxeles de la captura (1290 de ancho)
export const SHOTS = [
  { id: 'landing',   img: 'landing',       t0: 0.0,   t1: 2.9,   kicker: 'PLATAFORMA', pan: [0, 420] },
  { id: 'moda',      img: 'moda',          t0: 2.9,   t1: 8.811, kicker: 'TIENDA',     pan: [0, 1500] },
  { id: 'catalogo',  img: 'moda-catalogo', t0: 8.811, t1: 13.2,  kicker: 'CATÁLOGO',   pan: [260, 1150] },
  { id: 'tech',      img: 'tech',          t0: 13.2,  t1: 17.422,kicker: 'TECNOLOGÍA', pan: [0, 900] },
  { id: 'gym',       img: 'gym',           t0: 17.422,t1: 21.8,  kicker: 'GIMNASIOS',  pan: [0, 1100] },
  { id: 'servicios', img: 'servicios',     t0: 21.8,  t1: 25.873,kicker: 'SERVICIOS',  pan: [0, 760] },
  { id: 'impacto',   img: 'impacto',       t0: 25.873,t1: END_T, kicker: 'TU MARCA',   pan: [0, 1250] },
];

export const CAPTIONS = [
  { t0: 3.05,  t1: 8.811, text: ['Dejá de vender', 'por mensaje.'] },
  { t0: 8.95,  t1: 17.422, text: ['Tu web, con', 'diseño de nivel.'] },
  { t0: 17.56, t1: 25.873, text: ['Tiendas, servicios,', 'gimnasios y más.'] },
];

export const CUES = [
  { t: 0.2, sfx: 'pop' },
  { t: 2.9, sfx: 'whoosh' },
  { t: 8.811, sfx: 'whoosh' },
  { t: 13.2, sfx: 'whoosh' },
  { t: 17.422, sfx: 'whoosh' },
  { t: 21.8, sfx: 'whoosh' },
  { t: 25.873, sfx: 'whoosh' },
  { t: LOGO_HIT, sfx: 'impact' },
];

export const HOLDS = [[33.4, DUR]];
export const DROPS = [LOGO_HIT];
