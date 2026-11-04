// score.mjs — Davent ad: warm upbeat pop under Spanish narration.
// Light groove (kick + shaker + mallets), lift into the logo hit at 6.9s,
// then a bright resolve bed for the end card. Narration ducking happens in mix.
import { DUR, BPM, CUES, NAR } from './timeline.js';
export { DUR };

export default function score(S) {
  S.tempo(BPM);
  const drums = S.bus('drums', { gain: 0.55 });
  const bass = S.bus('bass', { gain: 0.5, duck: 0.5 });
  const music = S.bus('music', { gain: 0.4, reverb: 0.3, duck: 0.55, highpass: 160 });
  const mallets = S.bus('mallets', { gain: 0.3, reverb: 0.35, duck: 0.55 });
  const sfx = S.bus('sfx', { gain: 0.8, reverb: 0.18 });

  const bars = Math.ceil(DUR / S.bar(1));
  const prog = [['C3', 'maj7'], ['G2', 'maj7'], ['A2', 'min7'], ['F2', 'maj7']];
  const motif = ['E5', 'G5', 'A5', 'C6'];

  for (let bar = 0; bar < bars; bar++) {
    const [root, q] = prog[bar % prog.length], t = S.bar(bar);
    if (t >= DUR) break;
    const outro = t >= 9.2;                        // end card: softer, warmer
    music.add(S.pad(S.chord(S.midi(root) + 12, q), Math.min(S.bar(1) * 0.98, DUR - t), { cutoff: outro ? 1400 : 2000 }), t);
    for (let k = 0; k < 4; k++) {
      const bt = t + S.beat(k);
      if (bt >= DUR) break;
      drums.add(S.kick({ decay: 0.28, drive: 0.25 }), bt, { gain: outro ? 0.4 : 0.55 });
      drums.add(S.shaker({ decay: 0.05 }), bt + S.beat(0.5), { gain: outro ? 0.15 : 0.3, pan: 0.25 });
      if (!outro && k % 2 === 1) drums.add(S.clap({ decay: 0.16 }), bt, { gain: 0.35 });
      bass.add(S.bass(root, S.beat(0.45), { cutoff: 480, sub: 0.35 }), bt + S.beat(0.5), { gain: outro ? 0.5 : 0.8 });
    }
    // mallet motif: one bright note per beat during features, sparse elsewhere
    const dense = t >= NAR.s2[0] && t < NAR.s3[0];
    for (let k = 0; k < (dense ? 4 : 2); k++) {
      const nt = t + S.beat(k * (dense ? 1 : 2));
      if (nt < DUR) mallets.add(S.mallet(motif[(bar + k) % 4], S.beat(0.9), { material: 'marimba' }), nt, { gain: dense ? 0.5 : 0.3, pan: Math.sin(nt * 3) * 0.3 });
    }
  }

  const hit = CUES.find(c => c.sfx === 'impact')?.t;
  if (hit) sfx.add(S.riser(S.bar(1)), hit - S.bar(1), { gain: 0.45 });

  for (const c of CUES) {
    if (c.sfx === 'pop') sfx.add(S.pop('C6'), c.t, { gain: 0.55 });
    if (c.sfx === 'tick') sfx.add(S.tick(), c.t, { gain: 0.3, pan: Math.sin(c.t * 7) * 0.5 });
    if (c.sfx === 'whoosh') sfx.add(S.whoosh(0.6), c.t - 0.42, { gain: 0.6 });
    if (c.sfx === 'impact') { sfx.add(S.impact(), c.t, { gain: 0.85 }); drums.add(S.crash(), c.t, { gain: 0.3 }); S.duck(c.t, 1); }
    if (c.sfx === 'shimmer') sfx.add(S.shimmer(1.6), c.t, { gain: 0.45 });
  }
}
