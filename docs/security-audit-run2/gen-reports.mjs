// Generates REPORT.md, FINDINGS-DETAIL.md, NEEDS-VALIDATION.md from final findings.json + ledger + run metadata.
import { readFileSync, writeFileSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = dirname(fileURLToPath(import.meta.url));
const findings = JSON.parse(readFileSync(join(DIR, 'findings.json'), 'utf8'));
const ledger = JSON.parse(readFileSync(join(DIR, 'coverage-ledger.json'), 'utf8'));
const meta = JSON.parse(readFileSync(join(DIR, 'run-metadata.json'), 'utf8'));

const SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3, informational: 4 };
const sev = (r) => (r.severity && r.severity.overall_severity) || 'low';
const confirmed = findings.filter((f) => f.verdict === 'confirmed').sort((a, b) => SEV_ORDER[sev(a)] - SEV_ORDER[sev(b)] || a.fingerprint.localeCompare(b.fingerprint));
const needsVal = findings.filter((f) => f.verdict === 'needs_validation');
const rejected = findings.filter((f) => f.verdict === 'rejected');

// hardening notes from all hunter result files
const hardening = [];
for (const name of readdirSync(join(DIR, 'agents'))) {
  if (!name.startsWith('hunter-')) continue;
  try {
    const h = JSON.parse(readFileSync(join(DIR, 'agents', name, 'result.json'), 'utf8'));
    for (const note of h.hardening || []) hardening.push({ hunter: name, note });
  } catch {}
}

const firstFile = (r) => (r.trace && r.trace.length ? r.trace[r.trace.length - 1].file : '');
const loc = (r) => {
  const files = [...new Set((r.trace || []).map((t) => t.file))];
  return files.slice(0, 4).join(', ') + (files.length > 4 ? ` (+${files.length - 4})` : '');
};
const oneLine = (r) => {
  const d = (r.description || '').split(/\n|\.\s/)[0];
  return d.length > 160 ? d.slice(0, 157) + '…' : d;
};

// ---------- REPORT.md ----------
const rep = [];
rep.push('# Security Audit Report — run-2 (full repository)');
rep.push('');
rep.push(`- **Run**: ${meta.run_id} · profile \`${meta.profile}\` · repo \`${meta.repo}\``);
rep.push(`- **Source ref**: \`${meta.source_ref}\``);
rep.push(`- **Scope**: ${meta.scope_paths.join('; ')}`);
rep.push(`- **Budget**: ${meta.budget === null ? 'none set' : meta.budget}`);
rep.push(`- **Execution**: ${meta.execution_note}`);
rep.push(`- **Prior run**: ${meta.prior_run_paths.join(', ')} — used for coverage priors only; every retained record was re-verified against current source in this run.`);
rep.push(`- **Agents spent**: 13 hunters (10 wave-1 + 3 wave-2 gap-fill) + 1 coverage critic + 11 Phase-3 candidate verifiers + 23 Phase-5 record verifiers = 48 agent invocations.`);
rep.push(`- **Deferred / out-of-scope**: see Coverage summary. Wave-2 critic gaps were closed by hunters 11–13 before Phase-3; no coverage unit remains blocked.`);
rep.push('');
rep.push('## Security posture');
rep.push('');
rep.push('The platform has a mature baseline: parameterized queries throughout, WebP image normalization on every upload path, signed Mercado Pago webhooks, sandboxed/CSP-locked design document rendering, owner-scoped querysets, and session-epoch sealing on customer JWTs. The residual risk concentrates in three places: (1) the anonymous-throttle abstraction silently disables itself for authenticated principals, which produced four independent confirmed bypasses (platform auth email side-effects, feed writes, content reports); (2) cost-bearing endpoints lack bounds proportional to their hold/amplification cost — the SSE stream endpoint allows a single self-registered customer to lease all gunicorn workers, and unbounded taxonomy/discount creation inflates public catalog cost; (3) billing amount→entitlement binding trusts a union of all plan prices, allowing cross-plan price acceptance. Deployment-coupled items (admin URL proxying, PUBLIC_DOMAIN, webhook throttle starvation under provider IP sharing) remain unproven and are listed under NEEDS VALIDATION.');
rep.push('');
rep.push('## Confirmed findings');
rep.push('');
rep.push('| Severity | Finding | Boundary | Observed result |');
rep.push('|---|---|---|---|');
for (const r of confirmed) {
  rep.push(`| **${sev(r)}** | ${r.title} | \`${r.fingerprint}\` | ${oneLine(r)} |`);
}
rep.push('');
for (const r of confirmed) {
  rep.push(`### ${sev(r).toUpperCase()} — ${r.title}`);
  rep.push('');
  rep.push(`**Fingerprint**: \`${r.fingerprint}\` · **Confidence**: ${r.confidence && r.confidence.score}`);
  rep.push('');
  rep.push(`**Location**: ${loc(r)}`);
  rep.push('');
  rep.push(`**Principal**: ${(r.conditions && r.conditions[0] && r.conditions[0].description) || 'see conditions'} `);
  rep.push('');
  rep.push('**Description**: ' + r.description);
  rep.push('');
  rep.push('**Root cause**: ' + r.root_cause);
  rep.push('');
  rep.push('**Trace**:');
  for (const t of r.trace || []) rep.push(`- \`${t.kind}\` \`${t.file}:${t.line}\` (${t.scope}) — ${t.description}`);
  rep.push('');
  rep.push('**Conditions**:');
  for (const c of r.conditions || []) rep.push(`- _${c.kind}_ — ${c.description}`);
  if (r.execution) {
    rep.push('');
    rep.push(`**Reproduction** (${r.execution.attacker_perspective}):`);
    for (const i of r.execution.instructions || []) rep.push(`- ${i}`);
    rep.push(`- **Observed**: ${r.execution.observed_result}`);
  }
  rep.push('');
  rep.push(`**Impact**: ${r.severity.impact.reason}`);
  rep.push('');
  rep.push(`**Priority rationale**: likelihood=${r.severity.likelihood.score}, impact=${r.severity.impact.score}.`);
  rep.push('');
  rep.push(`**Smallest fix**: ${typeof r.remediation === 'string' ? r.remediation : r.remediation.strategy}`);
  rep.push('');
}
rep.push('## Needs validation (unproven leads — no severity assigned)');
rep.push('');
rep.push('| Lead | Trace | Exact blocker |');
rep.push('|---|---|---|');
for (const r of needsVal) {
  rep.push(`| ${r.title} | \`${loc(r)}\` | ${(r.blockers || []).join(' / ').slice(0, 220)} |`);
}
rep.push('');
rep.push('Full details in `NEEDS-VALIDATION.md`.');
rep.push('');
rep.push('## Hardening notes (not findings)');
rep.push('');
for (const h of hardening) rep.push(`- _${h.hunter}_: ${h.note}`);
rep.push('');
rep.push('## Positive patterns observed');
rep.push('');
rep.push('- `sanitize_markup`/`sanitize_css` + sandboxed iframe (no `allow-same-origin`) + per-response nonce CSP on all design document/preview surfaces.');
rep.push('- `normalize_image` WebP recode enforced on every upload path reviewed (store images, chat attachments, order proofs, pattern imports).');
rep.push('- Mercado Pago webhook signature verification and store-scoped webhook routing.');
rep.push('- `_pinned_ident` REMOTE_ADDR pinning and `_ResilientThrottleMixin` fail-open on the customer throttle stack (the platform-side plain throttles lack both — see confirmed findings).');
rep.push('- Customer JWT session-epoch sealing via `tokens_valid_after` and SimpleJWT `CHECK_USER_IS_ACTIVE` enforcement.');
rep.push('- Server-side price recomputation on cart/orders; soft stock reservations filtered by `expires_at__gt=now` in the claim query itself.');
rep.push('- Owner-scoped `get_object_or_404`/queryset patterns with no cross-tenant IDOR found in reviewed units.');
rep.push('- Parameterized ORM usage throughout; no raw SQL injection sinks found.');
rep.push('');
rep.push('## Coverage summary');
rep.push('');
const tally = {};
for (const u of ledger) tally[u.status] = (tally[u.status] || 0) + 1;
rep.push(`- Units: ${ledger.length} — ${Object.entries(tally).map(([k, v]) => `${k}: ${v}`).join(', ')}`);
rep.push(`- Confirmed records: ${confirmed.length} · needs_validation: ${needsVal.length} · rejected candidates: ${rejected.length}`);
rep.push('- Final critic result: wave-1 critic returned `gaps_found`; all three gaps (customer SSE stream, residual plumbing, public catalog/design surfaces) were closed by wave-2 hunters 11–13 and independently verified in Phase-3.');
rep.push('- Rejected candidates (not findings): ' + rejected.map((r) => `\`${r.fingerprint}\``).join(', '));
rep.push('');
writeFileSync(join(DIR, 'REPORT.md'), rep.join('\n'));

// ---------- FINDINGS-DETAIL.md ----------
const det = [];
det.push('# Findings detail — confirmed medium/high/critical records');
det.push('');
const detail = confirmed.filter((r) => ['medium', 'high', 'critical'].includes(sev(r)));
if (!detail.length) det.push('No confirmed medium+ records.');
for (const r of detail) {
  det.push(`## ${sev(r).toUpperCase()} · ${r.title}`);
  det.push('');
  det.push(`Fingerprint: \`${r.fingerprint}\``);
  det.push('');
  det.push('### Source trace');
  for (const t of r.trace || []) det.push(`- **${t.kind}** \`${t.file}:${t.line}\` — ${t.scope}: ${t.description}`);
  det.push('');
  det.push('### Evidence');
  for (const e of r.evidence || []) det.push(`- \`${e.file}:${e.line}\` — ${e.description}`);
  det.push('');
  det.push('### Attacker / resource');
  det.push(`- Principal: ${(r.conditions || [])[0] ? r.conditions[0].description : 'unauthenticated remote client'} `);
  det.push('- Resource: the affected boundary described above (per-record trace).');
  det.push('');
  det.push('### Reproduction (target-native, bounded)');
  if (r.execution) {
    det.push(`Attacker perspective: ${r.execution.attacker_perspective}`);
    det.push('');
    det.push('Payloads:');
    for (const p of r.execution.payloads || []) det.push(`- \`${p}\``);
    det.push('');
    det.push('Instructions:');
    for (const i of r.execution.instructions || []) det.push(`${i}`);
    det.push('');
    det.push(`Observed result: ${r.execution.observed_result}`);
  } else {
    det.push('Source-only reproduction described in REPORT.md.');
  }
  det.push('');
  det.push('### Security invariant');
  det.push(r.intended_behavior);
  det.push('');
  det.push('### Conditions & containment');
  for (const c of r.conditions || []) det.push(`- _${c.kind}_: ${c.description}`);
  det.push('');
  det.push('### Remediation');
  det.push(typeof r.remediation === 'string' ? r.remediation : r.remediation.strategy);
  if (r.remediation && r.remediation.code_changes) {
    for (const cc of r.remediation.code_changes) {
      det.push('');
      det.push(`\`${cc.file_name}\`:`);
      det.push('```python\n' + cc.fixed_code + '\n```');
    }
  }
  det.push('');
  det.push('### Regression case');
  det.push('Add a test asserting the invariant above fails before the fix and passes after (per-repo test conventions: `manage.py test <app>`); cover the exploit path from `execution.payloads`.');
  det.push('');
}
writeFileSync(join(DIR, 'FINDINGS-DETAIL.md'), det.join('\n'));

// ---------- NEEDS-VALIDATION.md ----------
const nv = [];
nv.push('# Needs validation — unresolved leads (no severity assigned)');
nv.push('');
nv.push('These records are **not confirmed vulnerabilities**. Each lists the source trace, the exact blocker (a deployment/runtime fact not provable from source), and bounded next steps.');
nv.push('');
for (const r of needsVal) {
  nv.push(`## ${r.title}`);
  nv.push('');
  nv.push(`Fingerprint: \`${r.fingerprint}\``);
  nv.push('');
  nv.push(r.description);
  nv.push('');
  nv.push('Claimed root cause: ' + r.claimed_root_cause);
  nv.push('');
  nv.push('Trace:');
  for (const t of r.trace || []) nv.push(`- **${t.kind}** \`${t.file}:${t.line}\` — ${t.scope}: ${t.description}`);
  nv.push('');
  nv.push('Blockers:');
  for (const b of r.blockers || []) nv.push(`- ${b}`);
  nv.push('');
  if (r.validation_plan) {
    if (r.validation_plan.local) nv.push(`Local next step: ${r.validation_plan.local}`);
    if (r.validation_plan.deployment) nv.push(`Owner-observed deployment check: ${r.validation_plan.deployment}`);
  }
  nv.push('');
}
writeFileSync(join(DIR, 'NEEDS-VALIDATION.md'), nv.join('\n'));

console.log('REPORT.md', rep.length, 'lines-ish');
console.log('FINDINGS-DETAIL.md records:', detail.length);
console.log('NEEDS-VALIDATION.md records:', needsVal.length);
