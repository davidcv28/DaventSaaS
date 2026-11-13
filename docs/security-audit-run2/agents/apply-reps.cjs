const fs = require('fs');
const dir = __dirname;
const findingsPath = require('path').join(dir, '..', 'findings.json');
const a = JSON.parse(fs.readFileSync(findingsPath, 'utf8'));
for (const f of fs.readdirSync(dir).filter(x => x.startsWith('rep-') && x.endsWith('.json'))) {
  const rep = JSON.parse(fs.readFileSync(require('path').join(dir, f), 'utf8'));
  const i = a.findIndex(x => x.fingerprint === rep.fingerprint);
  if (i < 0) { console.log('MISSING', rep.fingerprint); continue; }
  a[i] = rep;
  console.log('applied', rep.fingerprint);
}
fs.writeFileSync(findingsPath, JSON.stringify(a, null, 2) + '\n');
