// score.mjs — Davent ad vertical: pop cálido y limpio bajo la narración en español.
// Pulso suave (kick + shaker + marimba), aire en la intro, empuje en el bloque de
// rubros y resolución luminosa en la placa final. La voz se mezcla y se hace duck en mix.
import { DUR, BPM, CUES, NAR } from './timeline.js';
export { DUR };

export default function score(S) {
  S.tempo(BPM);
  const drums = S.bus('drums', { gain: 0.42 });
  const bass = S.bus('bass', { gain: 0.42, duck: 0.5 });
  const music = S.bus('music', { gain: 0.34, reverb: 0.34, duck: 0.55, highpass: 180 });
  const mallets = S.bus('mallets', { gain: 0.26, reverb: 0.4, duck: 0.55 });
  const sfx = S.bus('sfx', { gain: 0.72, reverb: 0.2 });

  const bars = Math.ceil(DUR / S.bar(1));
  const prog = [['F3', 'maj9'], ['C3', 'maj7'], ['D3', 'min7'], ['A2', 'min7']];
  const motif = ['A5', 'C6', 'E6', 'G5'];

  for (let bar = 0; bar < bars; bar++) {
    const [root, q] = prog[bar % prog.length], t = S.bar(bar);
    if (t >= DUR) break;
    const intro = t < NAR.s1[1];
    const lift = t >= NAR.s3[0] && t < NAR.s4[0];
    const outro = t >= NAR.s4[0];

    music.add(S.pad(S.chord(S.midi(root) + 12, q), Math.min(S.bar(1) * 0.98, DUR - t),
      { cutoff: outro ? 1500 : lift ? 2600 : 2100 }), t);

    for (let k = 0; k < 4; k++) {
      const bt = t + S.beat(k);
      if (bt >= DUR) break;
      const strong = k === 0 || k === 2;
      if (!intro || strong) drums.add(S.kick({ decay: 0.3, drive: 0.2 }), bt, { gain: strong ? 0.5 : 0.32 });
      drums.add(S.shaker({ decay: 0.05 }), bt + S.beat(0.5), { gain: intro ? 0.14 : 0.26, pan: 0.28 });
      bass.add(S.bass(root, S.beat(0.42), { cutoff: 460, sub: 0.3 }), bt + S.beat(0.5),
        { gain: intro ? 0.45 : outro ? 0.5 : 0.72 });
    }

    // marimba: una nota por tiempo en los bloques con contenido, dos por compás al resto
    const dense = (t >= NAR.s2[0] && t < NAR.s2[1]) || lift;
    for (let k = 0; k < (dense ? 4 : 2); k++) {
      const nt = t + S.beat(k * (dense ? 1 : 2));
      if (nt < DUR) mallets.add(S.mallet(motif[(bar + k) % 4], S.beat(0.85), { material: 'marimba' }), nt,
        { gain: dense ? 0.42 : 0.24, pan: Math.sin(nt * 2.4) * 0.28 });
    }
  }

  const hit = CUES.find(c => c.sfx === 'impact')?.t;
  if (hit) sfx.add(S.riser(S.bar(0.5)), hit - S.bar(0.5), { gain: 0.34 });

  for (const c of CUES) {
    if (c.sfx === 'pop') sfx.add(S.pop('C6'), c.t, { gain: 0.42 });
    if (c.sfx === 'whoosh') sfx.add(S.whoosh(0.55), c.t - 0.4, { gain: 0.45 });
    if (c.sfx === 'impact') {
      sfx.add(S.impact(), c.t, { gain: 0.7 });
      drums.add(S.crash(), c.t, { gain: 0.24 });
      S.duck(c.t, 1);
    }
  }
}
