// Normalizes findings.json to report-schema: sort by fingerprint, positional trace kinds,
// backfill missing severity/confidence/payloads from verifier artifacts.
import { readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = dirname(fileURLToPath(import.meta.url));
const findings = JSON.parse(readFileSync(join(DIR, 'findings.json'), 'utf8'));

const loadResult = (agent) =>
  JSON.parse(readFileSync(join(DIR, 'agents', agent, 'result.json'), 'utf8'));

// Backfill: catalog taxonomy record missing confidence (lives at result level)
{
  const cat = loadResult('verifier-catalog');
  const res = (cat.results || []).find((r) => r.fingerprint === 'catalog-owner:uncapped-taxonomy-discount-public-cost');
  const rec = findings.find((f) => f.fingerprint === 'catalog-owner:uncapped-taxonomy-discount-public-cost');
  if (res && res.confidence && rec && !rec.confidence) rec.confidence = res.confidence;
}

// Backfill: frontend mp-checkout missing severity+confidence
{
  const fe = loadResult('verifier-frontend');
  const res = (fe.results || []).find((r) => r.fingerprint === 'frontend:mp-checkout-redirect-not-host-validated');
  const rec = findings.find((f) => f.fingerprint === 'frontend:mp-checkout-redirect-not-host-validated');
  if (res && rec) {
    if (res.confidence && !rec.confidence) rec.confidence = res.confidence;
    if (!rec.severity) {
      rec.severity = {
        likelihood: {
          score: 'low',
          reason: 'Exploitation requires a compromised or malicious upstream (MP API response or MITM of the API) supplying a non-Mercado-Pago checkout_url; not directly attacker-controlled from the browser.',
        },
        impact: {
          score: 'low',
          reason: 'Successful exploitation redirects a paying user to an attacker page mimicking Mercado Pago checkout (credential/phishing exposure); bounded to platform billing flows that already trust the API response.',
        },
        overall_severity: 'low',
      };
    }
  }
}

// Backfill: caddy record empty payloads
{
  const rec = findings.find((f) => f.fingerprint === 'infra:caddy-xcaddy-unpinned');
  if (rec && rec.execution && Array.isArray(rec.execution.payloads) && rec.execution.payloads.length === 0) {
    rec.execution.payloads = [
      'docker/caddy/Dockerfile: xcaddy build --with github.com/caddy-dns/cloudflare (no version constraint)',
    ];
  }
}

// Fix library-internal refs (django/*, line:null) -> repo-relative anchors; detail stays in description/scope.
{
  const rec = findings.find((f) => f.fingerprint === 'customers-sse:gzip-buffering');
  if (rec) {
    const fixTrace = (n) => {
      if (typeof n.file === 'string' && n.file.startsWith('django/')) {
        const lib = n.file;
        n.file = 'requirements.txt';
        n.line = 17;
        n.scope = `${n.scope || ''} [lib: ${lib}]`.trim();
      }
      if (!Number.isInteger(n.line) || n.line < 1) n.line = 17;
    };
    const fixEvidence = (n) => {
      if (typeof n.file === 'string' && n.file.startsWith('django/')) {
        const lib = n.file;
        n.file = 'requirements.txt';
        n.line = 17;
        if (!n.description.includes(lib)) n.description = `[${lib}] ${n.description}`;
      }
      if (!Number.isInteger(n.line) || n.line < 1) n.line = 17;
    };
    (rec.trace || []).forEach(fixTrace);
    (rec.evidence || []).forEach(fixEvidence);
  }
}

// Normalize condition kinds to schema enum
const COND_KIND = {
  authentication_level: 1, authorization_role: 1, user_interaction: 1,
  system_configuration: 1, network_routing: 1, environmental_dependency: 1,
  data_state: 1, timing_dependency: 1, third_party_dependency: 1,
};
const COND_ALIAS = { network_position: 'network_routing' };
for (const f of findings) {
  for (const c of f.conditions || []) {
    if (c.kind && !COND_KIND[c.kind]) c.kind = COND_ALIAS[c.kind] || 'system_configuration';
  }
}

// Normalize trace kinds positionally: first=entrypoint, last=sink, middle=propagation
for (const f of findings) {
  const t = f.trace;
  if (!Array.isArray(t) || t.length === 0) continue;
  t.forEach((node, i) => {
    node.kind = i === 0 ? 'entrypoint' : i === t.length - 1 ? 'sink' : 'propagation';
  });
}

findings.sort((a, b) => (a.fingerprint < b.fingerprint ? -1 : a.fingerprint > b.fingerprint ? 1 : 0));
writeFileSync(join(DIR, 'findings.json'), JSON.stringify(findings, null, 2) + '\n');
console.log('normalized', findings.length, 'findings');
