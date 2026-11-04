// timeline.js — reloj compartido por imagen (index.html) y sonido (score.mjs).
// Voz: Gemini TTS (audio/narration.json, voz Charon — masculina).
//   s1 0.000–9.211   landing
//   s2 9.211–16.742  moda + impacto
//   s3 16.742–22.913 tecnología + gimnasio
//   s4 22.913–30.564 servicios + bazar
//   s5 30.564–36.055 placa final (dominio)
//   s6 36.055–39.826 placa final (PROMO)
// Imagen: grabación real de navegación (assets/tour.webm). Cada toma mapea su
// ventana de voz a un tramo del video, así el scroll dura lo que dura la frase.

export const BPM = 96;
export const BEAT = 60 / BPM;
export const BAR = BEAT * 4;

export const DUR = 42;
export const END_T = 30.564;

export const NAR = {
  s1: [0.0, 9.211],
  s2: [9.211, 16.742],
  s3: [16.742, 22.913],
  s4: [22.913, 30.564],
  s5: [30.564, 36.055],
  s6: [36.055, 39.826],
};

// v0/v1: tramo del video (segundos) que corresponde a la toma
export const SHOTS = [
  { id: 'landing',   t0: 0.0,    t1: 9.211,  v0: 1.606,  v1: 14.273, path: 'davent.com.ar',                  kicker: 'LA LANDING' },
  { id: 'moda',      t0: 9.211,  t1: 12.977, v0: 16.135, v1: 21.213, path: 'davent.com.ar/tienda/moda-qa',    kicker: 'MODA' },
  { id: 'impacto',   t0: 12.977, t1: 16.742, v0: 23.195, v1: 28.198, path: 'davent.com.ar/tienda/mi-qa',      kicker: 'INDUMENTARIA' },
  { id: 'tech',      t0: 16.742, t1: 19.828, v0: 30.849, v1: 36.628, path: 'davent.com.ar/tienda/mt-qa',      kicker: 'TECNOLOGÍA' },
  { id: 'gym',       t0: 19.828, t1: 22.913, v0: 38.540, v1: 43.101, path: 'davent.com.ar/tienda/gym-qa',     kicker: 'GIMNASIO' },
  { id: 'servicios', t0: 22.913, t1: 26.739, v0: 44.636, v1: 49.704, path: 'davent.com.ar/tienda/demo',       kicker: 'SERVICIOS' },
  { id: 'mercado',   t0: 26.739, t1: 30.564, v0: 51.537, v1: 56.948, path: 'davent.com.ar/tienda/bench-store', kicker: 'BAZAR' },
];

export const CAPTIONS = [
  { t0: 0.9,  t1: 9.0,  text: ['Tu web con', 'link propio.'] },
  { t0: 9.6,  t1: 16.6, text: ['Un diseño', 'para cada rubro.'] },
  { t0: 17.1, t1: 22.8, text: ['Tiendas, marcas', 'y gimnasios.'] },
  { t0: 23.3, t1: 30.4, text: ['Servicios que', 'se muestran solos.'] },
];

export const CUES = [
  { t: 9.211,  sfx: 'whoosh' },
  { t: 12.977, sfx: 'whoosh' },
  { t: 16.742, sfx: 'whoosh' },
  { t: 19.828, sfx: 'whoosh' },
  { t: 22.913, sfx: 'whoosh' },
  { t: 26.739, sfx: 'whoosh' },
  { t: 30.564, sfx: 'impact' },
];

export const HOLDS = [[37.0, DUR]];
export const DROPS = [30.564];
