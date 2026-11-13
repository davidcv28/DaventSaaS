// One-shot generator for coverage-ledger.json (run-2). Not committed as tooling;
// kept next to the run artifacts for reproducibility.
import { writeFileSync } from 'node:fs';

const enc = (s) =>
  [...Buffer.from(s.normalize('NFC'), 'utf8')]
    .map((b) => {
      const c = String.fromCharCode(b);
      return /[A-Za-z0-9\-._~]/.test(c) ? c : '%' + b.toString(16).toUpperCase().padStart(2, '0');
    })
    .join('');

const U = (surface, boundary, subsystem, attack_class, extra = {}) => ({
  surface,
  boundary,
  subsystem,
  attack_class,
  ...extra,
});

const ORD = 'ATTACK-CLASSES.md';
const WEB = 'WEB-PROTOCOL-AND-AUTH.md';
const DATA = 'DATA-ISOLATION-AND-LIFECYCLE.md';
const CLIENT = 'CLIENT-SIDE.md';
const PROTO = 'PROTOCOLS-RPC-AND-MESSAGING.md';
const RES = 'RESOURCE-EXHAUSTION-AND-AVAILABILITY.md';
const CLOUD = 'CLOUD-AND-DEPLOYMENT.md';
const SUPPLY = 'SUPPLY-CHAIN-AND-RELEASE.md';
const AI = 'AI-AND-LLM.md';

const units = [
  U(
    'AdminApp/domains/users/urls/urls.py#token+password-reset+verify-email+google+profile',
    'AdminApp/domains/users/services#session issuance, JWT cookies, account recovery, social login',
    'AdminApp/domains/users',
    `${ORD}#Access control`,
    {
      starting_paths: [
        'AdminApp/domains/users',
        'DaventProject/urls.py',
        'DaventProject/middleware.py',
        'DaventProject/throttling.py',
      ],
      ordinary_attack_class_block: `${ORD}#Access control`,
      selected_companion_blocks: [
        `${WEB}#Core discipline`,
        `${WEB}#Browser-session attack classes`,
        `${WEB}#Federated-identity attack classes`,
        `${WEB}#Universal moves`,
        `${WEB}#Validation rules`,
        `${DATA}#Core discipline`,
        `${DATA}#Tenant and object-isolation attack classes`,
        `${DATA}#Universal moves`,
        `${DATA}#Validation rules`,
      ],
      excluded_blocks: [
        { block: `${WEB}#HTTP framing and cache attack classes`, reason: 'session/auth focus; framing covered by infra unit' },
        { block: `${WEB}#MFA, passkey, and account-transition attack classes`, reason: 'no MFA/passkeys in product' },
        { block: `${WEB}#API-key and mTLS attack classes`, reason: 'no API keys/mTLS' },
      ],
    }
  ),
  U(
    'AdminApp/domains/payments+suscriptions+invoices+SuscriptionApp/benefits#checkout,webhook,sync,coupons,plans,assign',
    'AdminApp/domains/payments/services#MP webhook HMAC, payment ownership, plan entitlement, rollups',
    'AdminApp/domains/payments',
    `${ORD}#Business logic`,
    {
      starting_paths: [
        'AdminApp/domains/payments',
        'AdminApp/domains/suscriptions',
        'AdminApp/domains/invoices',
        'SuscriptionApp/domains/benefits',
      ],
      ordinary_attack_class_block: `${ORD}#Business logic`,
      selected_companion_blocks: [
        `${PROTO}#Core discipline`,
        `${PROTO}#Replay, ordering, and transaction attack classes`,
        `${PROTO}#Universal moves`,
        `${PROTO}#Validation rules`,
        `${DATA}#Core discipline`,
        `${DATA}#Tenant and object-isolation attack classes`,
        `${DATA}#Universal moves`,
        `${DATA}#Validation rules`,
      ],
      excluded_blocks: [
        { block: `${PROTO}#Broker and queue isolation attack classes`, reason: 'no broker-facing surface; Celery tasks are internal' },
        { block: `${PROTO}#Framing, schema, and interpretation attack classes`, reason: 'JSON webhook body is not schema-parsed into privileged objects beyond signature check' },
      ],
    }
  ),
  U(
    'StoreApp/domains/stores/urls#public,public-catalog,contact,reviews,pattern-document,visit,stats',
    'StoreApp/domains/stores/views/viewset.py#published+unblocked+has_public_link gate, captcha, throttle, PII minimization',
    'StoreApp/domains/stores',
    `${ORD}#Feature abuse and data leakage`,
    {
      starting_paths: [
        'StoreApp/domains/stores',
        'StoreApp/domains/catalog/views',
        'StoreApp/domains/services',
      ],
      ordinary_attack_class_block: `${ORD}#Feature abuse and data leakage`,
      selected_companion_blocks: [
        `${WEB}#Core discipline`,
        `${WEB}#HTTP framing and cache attack classes`,
        `${WEB}#Universal moves`,
        `${WEB}#Validation rules`,
        `${RES}#Core discipline`,
        `${RES}#Quota and scheduling attack classes`,
        `${RES}#Universal moves`,
        `${RES}#Validation rules`,
        `${CLIENT}#Core discipline`,
        `${CLIENT}#Cross-origin messaging and network attack classes`,
        `${CLIENT}#Universal moves`,
        `${CLIENT}#Validation rules`,
      ],
      excluded_blocks: [
        { block: `${CLIENT}#DOM and object-state attack classes`, reason: 'frontend-only; assigned to frontend unit' },
        { block: `${RES}#Computational amplification attack classes`, reason: 'catalog queries are bounded by plan quotas; covered under quota class' },
      ],
    }
  ),
  U(
    'StoreApp/domains/catalog+services#owner CRUD, discounts, reviews moderation, services CRUD',
    'StoreApp/domains/*/views#my_store() owner scoping + plan/benefit gates',
    'StoreApp/domains/catalog',
    `${ORD}#Access control`,
    {
      starting_paths: [
        'StoreApp/domains/catalog',
        'StoreApp/domains/services',
      ],
      ordinary_attack_class_block: `${ORD}#Access control`,
      selected_companion_blocks: [
        `${DATA}#Core discipline`,
        `${DATA}#Tenant and object-isolation attack classes`,
        `${DATA}#Derived-data and disclosure attack classes`,
        `${DATA}#Universal moves`,
        `${DATA}#Validation rules`,
      ],
      excluded_blocks: [
        { block: `${DATA}#Export, backup, restore, and migration attack classes`, reason: 'no export/backup surface in these domains' },
        { block: `${DATA}#Deletion, revocation, and lifecycle attack classes`, reason: 'covered by derived-data class for soft-delete/visibility' },
      ],
    }
  ),
  U(
    'StoreApp/domains/customers+cart+orders+memberships+legalpages#buyer auth, cart, order lifecycle, plans, legal pages',
    'StoreApp/domains/customers/services#customer JWT, store tenancy, order state machine, proof uploads',
    'StoreApp/domains/customers',
    `${ORD}#Access control`,
    {
      starting_paths: [
        'StoreApp/domains/customers',
        'StoreApp/domains/cart',
        'StoreApp/domains/orders',
        'StoreApp/domains/memberships',
        'StoreApp/domains/legalpages',
      ],
      ordinary_attack_class_block: `${ORD}#Access control`,
      selected_companion_blocks: [
        `${WEB}#Core discipline`,
        `${WEB}#Browser-session attack classes`,
        `${WEB}#Universal moves`,
        `${WEB}#Validation rules`,
        `${DATA}#Core discipline`,
        `${DATA}#Tenant and object-isolation attack classes`,
        `${DATA}#Universal moves`,
        `${DATA}#Validation rules`,
        `${ORD}#Business logic`,
      ],
      excluded_blocks: [
        { block: `${DATA}#Export, backup, restore, and migration attack classes`, reason: 'no export surface' },
      ],
    }
  ),
  U(
    'StoreApp/domains/storepayments+storeadmin+support+feed#seller MP OAuth/config, storage BYO, store admin, support chat, feed',
    'StoreApp/domains/storepayments#merchant credential handling, webhook scoping, storage endpoint validation',
    'StoreApp/domains/storepayments',
    `${ORD}#Resource and file handling`,
    {
      starting_paths: [
        'StoreApp/domains/storepayments',
        'StoreApp/domains/storeadmin',
        'StoreApp/domains/support',
        'StoreApp/domains/feed',
      ],
      ordinary_attack_class_block: `${ORD}#Resource and file handling`,
      selected_companion_blocks: [
        `${DATA}#Core discipline`,
        `${DATA}#Tenant and object-isolation attack classes`,
        `${DATA}#Universal moves`,
        `${DATA}#Validation rules`,
        `${CLOUD}#Core discipline`,
        `${CLOUD}#Managed storage, events, and edge attack classes`,
        `${CLOUD}#Universal moves`,
        `${CLOUD}#Validation rules`,
      ],
      excluded_blocks: [
        { block: `${CLOUD}#Container and orchestration attack classes`, reason: 'deployment unit covers containers' },
        { block: `${CLOUD}#Workload identity and IAM attack classes`, reason: 'no cloud IAM in app code' },
      ],
    }
  ),
  U(
    'AdminApp/domains/chat+notifications+legal+locations + McpApp/domains/skills#support chat, notifications, reports, geo, LLM skills',
    'AdminApp/domains/chat/services#thread isolation, presence, attachment privacy; McpApp skills tool gating',
    'AdminApp/domains/chat',
    `${ORD}#Access control`,
    {
      starting_paths: [
        'AdminApp/domains/chat',
        'AdminApp/domains/notifications',
        'AdminApp/domains/legal',
        'AdminApp/domains/locations',
        'McpApp/domains/skills',
      ],
      ordinary_attack_class_block: `${ORD}#Access control`,
      selected_companion_blocks: [
        `${AI}#Core discipline`,
        `${AI}#Tool and action attack classes`,
        `${AI}#MCP and sub-agent trust classes`,
        `${AI}#Output and disclosure attack classes`,
        `${AI}#Universal moves`,
        `${AI}#Validation rules`,
        `${PROTO}#Core discipline`,
        `${PROTO}#Replay, ordering, and transaction attack classes`,
        `${PROTO}#Universal moves`,
        `${PROTO}#Validation rules`,
      ],
      excluded_blocks: [
        { block: `${AI}#Context, retrieval, and memory attack classes`, reason: 'skills service is thin; no retrieval/memory store' },
      ],
    }
  ),
  U(
    'frontend/src#SPA: stores, views, components, api clients, studio, pattern surfaces',
    'frontend/src#token storage, postMessage origins, v-html sinks, router guards, Sentry PII',
    'frontend',
    `${ORD}#Injection`,
    {
      starting_paths: ['frontend/src'],
      ordinary_attack_class_block: `${ORD}#Injection`,
      selected_companion_blocks: [
        `${CLIENT}#Core discipline`,
        `${CLIENT}#DOM and object-state attack classes`,
        `${CLIENT}#Cross-origin messaging and network attack classes`,
        `${CLIENT}#Service-worker and browser-storage attack classes`,
        `${CLIENT}#Cross-site information leak classes`,
        `${CLIENT}#UI-redress and navigation attack classes`,
        `${CLIENT}#Universal moves`,
        `${CLIENT}#Validation rules`,
      ],
      excluded_blocks: [],
    }
  ),
  U(
    'DaventProject/settings.py+middleware.py+throttling.py+checks.py+envguard.py + docker/ + .github/workflows + requirements.txt/package.json',
    'deployment config#DEBUG/SECRET/SECURE_* flags, CORS, CSP, admin URL, container hardening, CI gates, dependency pins',
    'DaventProject',
    `${ORD}#Cryptography and secrets`,
    {
      starting_paths: [
        'DaventProject',
        'docker',
        '.github/workflows',
        'requirements.txt',
        'frontend/package.json',
        'render.yaml',
        'docker-compose.yml',
      ],
      ordinary_attack_class_block: `${ORD}#Cryptography and secrets`,
      selected_companion_blocks: [
        `${CLOUD}#Core discipline`,
        `${CLOUD}#Ingress, network, and control-plane attack classes`,
        `${CLOUD}#Container and orchestration attack classes`,
        `${CLOUD}#Configuration and secret lifecycle attack classes`,
        `${CLOUD}#Universal moves`,
        `${CLOUD}#Validation rules`,
        `${SUPPLY}#Core discipline`,
        `${SUPPLY}#Dependency and build-input attack classes`,
        `${SUPPLY}#CI and automation attack classes`,
        `${SUPPLY}#Universal moves`,
        `${SUPPLY}#Validation rules`,
        `${RES}#Core discipline`,
        `${RES}#Failure and recovery attack classes`,
        `${RES}#Universal moves`,
        `${RES}#Validation rules`,
      ],
      excluded_blocks: [
        { block: `${SUPPLY}#Release and update attack classes`, reason: 'no self-update mechanism in repo' },
        { block: `${CLOUD}#Workload identity and IAM attack classes`, reason: 'no cloud IAM bindings in repo' },
        { block: `${CLOUD}#Managed storage, events, and edge attack classes`, reason: 'R2 usage covered by uploads unit' },
      ],
    }
  ),
  U(
    'StoreApp/domains/*/services/imaging.py+storage.py + chat attachments + order proofs + pattern sanitize_markup',
    'upload pipeline#magic-byte signature, WebP recode, size/pixel caps, R2 key control, signed URLs, markup sanitization',
    'StoreApp/domains/stores',
    `${ORD}#Resource and file handling`,
    {
      starting_paths: [
        'StoreApp/domains/stores/services',
        'StoreApp/domains/stores/views',
        'StoreApp/domains/design',
        'StoreApp/domains/chat',
        'StoreApp/domains/orders',
        'StoreApp/domains/customers',
      ],
      ordinary_attack_class_block: `${ORD}#Resource and file handling`,
      selected_companion_blocks: [
        `${DATA}#Core discipline`,
        `${DATA}#Deletion, revocation, and lifecycle attack classes`,
        `${DATA}#Universal moves`,
        `${DATA}#Validation rules`,
        `${RES}#Core discipline`,
        `${RES}#Computational amplification attack classes`,
        `${RES}#Universal moves`,
        `${RES}#Validation rules`,
      ],
      excluded_blocks: [
        { block: `${DATA}#Tenant and object-isolation attack classes`, reason: 'owner scoping covered by catalog/customers units' },
      ],
    }
  ),
];

const ledger = units.map((u, i) => {
  const refs = {
    surface: u.surface,
    boundary: u.boundary,
    subsystem: u.subsystem,
    attack_class: u.attack_class,
  };
  const coverage_id = [refs.surface, refs.boundary, refs.subsystem, refs.attack_class]
    .map(enc)
    .join('::');
  return {
    coverage_id,
    canonical_refs: refs,
    surface: u.surface.split('#')[0],
    boundary: u.boundary,
    subsystem: u.subsystem,
    attack_class: u.attack_class.split('#')[1],
    starting_paths: u.starting_paths,
    ordinary_attack_class_block: u.ordinary_attack_class_block,
    selected_companion_blocks: u.selected_companion_blocks,
    excluded_blocks: u.excluded_blocks,
    prior_status: 'prior_covered_same_source',
    attempts: [],
    wave: 1,
    status: 'planned',
    agent_id: null,
    reviewed_paths: [],
    local_checks: [],
    result_fingerprints: [],
    unresolved: [],
    hunter: `hunter-${String(i + 1).padStart(2, '0')}`,
  };
});

ledger.sort((a, b) => (a.coverage_id < b.coverage_id ? -1 : 1));
writeFileSync(new URL('./coverage-ledger.json', import.meta.url), JSON.stringify(ledger, null, 2));
console.log(`units: ${ledger.length}`);
ledger.forEach((u) => console.log(u.hunter, u.coverage_id.slice(0, 110)));
