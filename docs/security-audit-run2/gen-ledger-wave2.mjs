// Adds wave-2 coverage units (critic gaps) to coverage-ledger.json, then consolidates.
import { readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = dirname(fileURLToPath(import.meta.url));
const ledger = JSON.parse(readFileSync(join(DIR, 'coverage-ledger.json'), 'utf8'));

const enc = (s) =>
  [...Buffer.from(s.normalize('NFC'), 'utf8')]
    .map((b) => {
      const c = String.fromCharCode(b);
      return /[A-Za-z0-9\-._~]/.test(c) ? c : '%' + b.toString(16).toUpperCase().padStart(2, '0');
    })
    .join('');

const RES = 'RESOURCE-EXHAUSTION-AND-AVAILABILITY.md';
const WEB = 'WEB-PROTOCOL-AND-AUTH.md';
const DATA = 'DATA-ISOLATION-AND-LIFECYCLE.md';
const ORD = 'ATTACK-CLASSES.md';
const CLIENT = 'CLIENT-SIDE.md';

const mk = (surface, boundary, subsystem, attack_class, extra) => {
  const refs = { surface, boundary, subsystem, attack_class };
  return {
    coverage_id: [refs.surface, refs.boundary, refs.subsystem, refs.attack_class].map(enc).join('::'),
    canonical_refs: refs,
    surface: surface.split('#')[0],
    boundary,
    subsystem,
    attack_class: attack_class.split('#')[1],
    starting_paths: extra.starting_paths,
    ordinary_attack_class_block: extra.ordinary_attack_class_block,
    selected_companion_blocks: extra.selected_companion_blocks,
    excluded_blocks: extra.excluded_blocks || [],
    prior_status: 'none',
    attempts: [],
    wave: 2,
    status: 'in_progress',
    agent_id: extra.hunter,
    reviewed_paths: [],
    local_checks: [],
    result_fingerprints: [],
    unresolved: [],
    hunter: extra.hunter,
  };
};

const units = [
  mk(
    'StoreApp/domains/customers/views/notification_views.py#SSE stream + stream-ticket',
    'StoreApp/domains/customers#ticket auth binding, session epoch, per-connection worker occupancy',
    'StoreApp/domains/customers',
    `${RES}#Resource exhaustion`,
    {
      hunter: 'hunter-11',
      starting_paths: [
        'StoreApp/domains/customers/views/notification_views.py',
        'StoreApp/domains/customers/services/tokens.py',
        'StoreApp/domains/customers/views/auth_views.py',
        'StoreApp/domains/customers/authentication.py',
        'StoreApp/domains/customers/models/models.py',
        'DaventProject/throttling.py',
        'docker/api/gunicorn.conf.py',
      ],
      ordinary_attack_class_block: `${RES}#Resource exhaustion`,
      selected_companion_blocks: [
        `${WEB}#Core discipline`,
        `${WEB}#Browser-session attack classes`,
        `${WEB}#Universal moves`,
        `${WEB}#Validation rules`,
        `${DATA}#Core discipline`,
        `${DATA}#Tenant and object-isolation attack classes`,
        `${DATA}#Universal moves`,
        `${DATA}#Validation rules`,
      ],
      excluded_blocks: [
        { block: `${RES}#Quota and scheduling attack classes`, reason: 'stream holds workers, not quota accounting' },
      ],
    }
  ),
  mk(
    'SuscriptionApp/domains/benefits + StoreApp/domains/design/views#public plan catalog + design catalog CRUD/preview',
    'SuscriptionApp/domains/benefits#public serializer field exposure; StoreApp/domains/design#read/preview entitlement gating',
    'SuscriptionApp/domains/benefits',
    `${DATA}#Derived-data and disclosure`,
    {
      hunter: 'hunter-12',
      starting_paths: [
        'SuscriptionApp/domains/benefits',
        'StoreApp/domains/design/views',
        'StoreApp/domains/design/serializers',
        'StoreApp/domains/design/services/pattern_preview.py',
        'DaventProject/urls.py',
      ],
      ordinary_attack_class_block: `${DATA}#Derived-data and disclosure`,
      selected_companion_blocks: [
        `${ORD}#Access control`,
        `${RES}#Core discipline`,
        `${RES}#Computational amplification attack classes`,
        `${RES}#Universal moves`,
        `${RES}#Validation rules`,
        `${CLIENT}#Core discipline`,
        `${CLIENT}#Universal moves`,
        `${CLIENT}#Validation rules`,
      ],
      excluded_blocks: [],
    }
  ),
  mk(
    'residual unreviewed plumbing#register throttle, sync publish path, AI-design submodules, invoices, customer services, MCP transport, aux serializers',
    'cross-domain#serializer field exposure, email/content injection, missing plan gates, deployment exposure',
    'multi',
    `${ORD}#Feature abuse and data leakage`,
    {
      hunter: 'hunter-13',
      starting_paths: [
        'AdminApp/domains/users/views/viewset.py',
        'StoreApp/domains/stores/services/sync.py',
        'StoreApp/domains/stores/services/ai_design_copy.py',
        'AdminApp/domains/invoices',
        'StoreApp/domains/customers/services',
        'McpApp/fastmcp_server.py',
        'DaventProject/pagination.py',
      ],
      ordinary_attack_class_block: `${ORD}#Feature abuse and data leakage`,
      selected_companion_blocks: [
        `${DATA}#Core discipline`,
        `${DATA}#Tenant and object-isolation attack classes`,
        `${DATA}#Derived-data and disclosure attack classes`,
        `${DATA}#Universal moves`,
        `${DATA}#Validation rules`,
        `${RES}#Core discipline`,
        `${RES}#Universal moves`,
        `${RES}#Validation rules`,
      ],
      excluded_blocks: [],
    }
  ),
];

for (const u of units) {
  if (ledger.some((e) => e.coverage_id === u.coverage_id)) {
    console.error('dup', u.coverage_id.slice(0, 80));
    continue;
  }
  ledger.push(u);
}
ledger.sort((a, b) => (a.coverage_id < b.coverage_id ? -1 : 1));
writeFileSync(join(DIR, 'coverage-ledger.json'), JSON.stringify(ledger, null, 2) + '\n');
console.log('units now:', ledger.length);
