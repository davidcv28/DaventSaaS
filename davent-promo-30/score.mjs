// score.mjs — ambient profesional: pad suave, pulso discreto, plucks espaciados.
// La voz manda: música debajo, sin melodía protagonista hasta el cierre.
import { DUR, BPM, CUES, SHOTS } from './timeline.js';
export { DUR };

export default function score(S) {
  S.tempo(BPM);
  const drums = S.bus('drums', { gain: 0.5 });
  const bass  = S.bus('bass',  { gain: 0.55, duck: 0.6 });
  const music = S.bus('music', { gain: 0.4, reverb: 0.45, duck: 0.65, highpass: 160 });
  const sfx   = S.bus('sfx',   { gain: 0.7, reverb: 0.2 });

  const bars = Math.ceil(DUR / S.bar(1));
  // Dm ambient: cálido, serio, optimista en el cierre
  const prog = [['D2', 'min7'], ['A#1', 'maj7'], ['F2', 'maj7'], ['C2', 'maj7']];
  const promo = SHOTS.find(s => s.id === 'promo').t0;

  for (let bar = 0; bar < bars; bar++) {
    const [root, q] = prog[bar % prog.length], t = S.bar(bar);
    const isPromo = t >= promo;
    music.add(S.pad(S.chord(S.midi(root) + 12, q), S.bar(1) * 0.98, { cutoff: isPromo ? 2600 : 1600 }), t);
    bass.add(S.sub(S.midi(root), S.bar(1) * 0.9, { gain: isPromo ? 0.5 : 0.32 }), t);
    // pulso: hat suave en offbeats; kick entra solo con la oferta
    for (let k = 0; k < 4; k++) {
      const bt = t + S.beat(k);
      drums.add(S.hat({ decay: 0.03 }), bt + S.beat(0.5), { gain: isPromo ? 0.4 : 0.2, pan: 0.15 });
      if (isPromo) { drums.add(S.kick({ decay: 0.28 }), bt, { gain: 0.55 }); S.duck(bt); }
      if (isPromo && k % 2 === 1) bass.add(S.bass(root, S.beat(0.5), { cutoff: 480, sub: 0.25 }), bt);
    }
    // pluck espaciado, una nota por barra, arpegio del acorde
    const note = S.chord(S.midi(root) + 24, q)[bar % 3];
    music.add(S.pluck(note, { decay: 1.2 }), t + S.beat(bar % 2 ? 2 : 0), { gain: 0.3, pan: bar % 2 ? 0.35 : -0.35 });
  }

  const hit = promo;
  sfx.add(S.riser(S.bar(1) * 2), hit - S.bar(1) * 2, { gain: 0.45 });

  for (const c of CUES) {
    if (c.sfx === 'pop')     sfx.add(S.pop('D6'), c.t, { gain: 0.45 });
    if (c.sfx === 'tick')    sfx.add(S.tick(), c.t, { gain: 0.3, pan: Math.sin(c.t * 7) * 0.4 });
    if (c.sfx === 'whoosh')  sfx.add(S.whoosh(0.5), c.t - 0.35, { gain: 0.55 });
    if (c.sfx === 'chime')   sfx.add(S.bell('D6', { decay: 1.4 }), c.t, { gain: 0.5 });
    if (c.sfx === 'impact')  { sfx.add(S.impact(), c.t, { gain: 0.85 }); drums.add(S.crash(), c.t, { gain: 0.3 }); S.duck(c.t, 1); }
    if (c.sfx === 'shimmer') sfx.add(S.shimmer(1.8), c.t, { gain: 0.4 });
  }
}
