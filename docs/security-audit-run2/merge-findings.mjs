// Merges agents/verifier-*/result.json records into findings.json (flat array, dedup by fingerprint).
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = dirname(fileURLToPath(import.meta.url));
const byFp = new Map();
const decisions = new Map();

for (const name of readdirSync(join(DIR, 'agents'))) {
  if (!name.startsWith('verifier-')) continue;
  const p = join(DIR, 'agents', name, 'result.json');
  let r;
  try { r = JSON.parse(readFileSync(p, 'utf8')); } catch (e) { console.error('SKIP', name, e.message); continue; }
  const results = r.results || (Array.isArray(r) ? r : [r]);
  for (const v of results) {
    const fp = v.fingerprint || (v.record && v.record.fingerprint);
    const rec = v.record || v;
    if (!fp || !rec) { console.error('NOFP', name); continue; }
    if (byFp.has(fp)) console.error('DUP', fp, 'kept', decisions.get(fp), 'vs', name);
    else { byFp.set(fp, rec); decisions.set(fp, name); }
  }
}

const out = [...byFp.values()];
writeFileSync(join(DIR, 'findings.json'), JSON.stringify(out, null, 2) + '\n');
console.log('records:', out.length);
const tally = {};
for (const r of out) tally[r.verdict] = (tally[r.verdict] || 0) + 1;
console.log(tally);
