// Consolidates agents/hunter-NN/result.json into coverage-ledger.json.
// reviewed_paths aggregate must equal the union of local_checks[].reviewed_paths.
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = dirname(fileURLToPath(import.meta.url));
const ledger = JSON.parse(readFileSync(join(DIR, 'coverage-ledger.json'), 'utf8'));

const results = new Map();
for (const name of readdirSync(join(DIR, 'agents'))) {
  try {
    const r = JSON.parse(readFileSync(join(DIR, 'agents', name, 'result.json'), 'utf8'));
    results.set(r.agent, r);
  } catch (e) { console.error('skip', name, e.message); }
}

const PATH_BAD = /[\u0000-\u001f\u007f-\u009f\u2028\u2029]/;
const bad = [];
const isSafePath = (p) => {
  if (typeof p !== 'string' || !p || p.trim() !== p || p.includes('\\') || p.includes(':') || PATH_BAD.test(p)) return false;
  if (p.startsWith('/') || p.startsWith('~')) return false;
  return p.split('/').every((s) => s && s !== '.' && s !== '..' && !/[ .]$/.test(s));
};

for (const unit of ledger) {
  const res = results.get(unit.hunter || unit.agent_id);
  if (!res) { console.error('NO RESULT for', unit.hunter); continue; }
  const checks = res.checks || [];
  const paths = new Set();
  for (const c of checks) for (const p of c.reviewed_paths || []) paths.add(p);
  const fingerprints = res.candidate_fingerprints || [];
  const unresolved = res.unresolved || [];

  for (const p of paths) if (!isSafePath(p)) bad.push([unit.hunter, p]);
  for (const c of checks) {
    if (!c.agent_id || !/^[a-z0-9][a-z0-9_-]{0,63}$/.test(c.agent_id)) bad.push([unit.hunter, 'bad agent_id ' + c.agent_id]);
    if (c.method !== 'source' && c.method !== 'local') bad.push([unit.hunter, 'bad method ' + c.method]);
    if (c.method === 'source' && c.artifact !== null) bad.push([unit.hunter, 'source check with artifact']);
    if (typeof c.result !== 'string' || !c.result || c.result.length > 4096) bad.push([unit.hunter, 'result len ' + (c.result || '').length]);
    if (typeof c.invariant !== 'string' || !c.invariant || c.invariant.length > 4096) bad.push([unit.hunter, 'invariant len']);
  }
  for (const u of unresolved) if (typeof u !== 'string' || !u || u.length > 4096) bad.push([unit.hunter, 'unresolved len']);

  unit.status = fingerprints.length ? 'candidate' : (unresolved.length ? 'blocked' : 'covered');
  unit.reviewed_paths = [...paths].sort();
  unit.local_checks = checks;
  unit.result_fingerprints = fingerprints;
  unit.unresolved = unresolved;
}

writeFileSync(join(DIR, 'coverage-ledger.json'), JSON.stringify(ledger, null, 2) + '\n');
console.log('units:', ledger.length, 'statuses:', ledger.map(u => u.status).join(','));
console.log('bad entries:', bad.length);
for (const b of bad.slice(0, 50)) console.log('  ', b[0], '->', JSON.stringify(b[1]).slice(0, 120));
