# Architecture — DaventSaaS (run-2)

## Product and principals

DAVENT is a multi-tenant SaaS (Django 5.2 + DRF + SimpleJWT backend, Vue 3 SPA
frontend, PostgreSQL, Redis cache/broker, Celery, R2 object storage, Mercado
Pago payments). Principals, lowest to highest trust:

1. **Anonymous internet user** — public store pages, catalog, contact forms,
   reviews, pattern documents, healthz, robots/sitemap.
2. **Customer (buyer)** — `StoreApp/domains/customers`: per-store buyer account
   with its own JWT (`customer_access`), cart, orders, memberships, support.
3. **Store owner** — platform `User` with an active `Suscription`; manages own
   store, catalog, design, discounts, orders, payouts.
4. **Staff/admin** — `is_staff`/`is_superuser`: moderation, plan assign,
   payment approval, chat support side, Django admin at `ADMIN_URL`.

Protected resources: user PII (encrypted `document`/`phone`/names/address via
`SECRETS_MASTER_KEYS` keyring + `SECRETS_HASH_KEY` HMAC hashes), merchant MP
credentials (`StoreMpAccount`, write-only), customer PII, payment records,
invoice numbering, R2 objects (private vs public URL), design-pattern markup
served to iframes, LLM skill invocations (McpApp).

## Stack and deployment paths

- Backend: `manage.py` (Django), apps `AdminApp/domains/{users,suscriptions,
  locations,payments,invoices,legal,chat,notifications}`,
  `StoreApp/domains/{stores,catalog,services,design,customers,cart,orders,
  memberships,storepayments,legalpages,support,storeadmin,feed}`,
  `SuscriptionApp/domains/benefits`, `McpApp/domains/skills`. URLconf root:
  `DaventProject/urls.py` mounts every domain under `/api/` plus JWT token
  endpoints, password reset, email verify, Google social login, public config,
  and a SPA catch-all (`spa()` with CSP/COOP headers).
- Frontend: `frontend/src` Vue 3 SPA (Vite), Pinia stores, vue-router,
  customer vs platform auth clients.
- Deploys: Docker compose on a VPS (nginx-unprivileged + gunicorn api +
  celery + redis + postgres service optional), Render blueprint
  (`render.yaml`), GitHub Actions `ci-cd.yml` (lint→test→security→build→deploy),
  `security-schedule.yml`, Dependabot. Neon Postgres in production.
- Offline verification: `venv/Scripts/python.exe manage.py test`, `check
  --deploy`, `ruff`, `bandit`, `pip-audit`, `npm audit`, `vite build`. Local
  runserver on :8000 + Vite :5173. No OS-level sandbox with no-network +
  read-only mounts is available in this environment → hunters are
  source-only; decisive runtime/deployment facts become `needs_validation`.

## Entry surfaces and key flows

- **Auth**: `POST /api/token/` (login + per-account lockout), cookie refresh
  `/api/token/refresh/` (httpOnly, CSRF double-submit, rotation+blacklist),
  logout, password reset/confirm, email verify/resend, `POST
  /api/auth/google/` (Google ID token → platform session), `POST
  /api/customer-auth/*` (buyer register/login/google/refresh/logout/phone).
- **Public store**: `GET /api/stores/public/<slug>/`, `public-catalog`,
  `contact` (captcha+honeypot+throttle), product reviews (registered buyers
  only on ecommerce stores), `pattern/document` (sandboxed iframe, per-response
  CSP nonce, opaque origin, `postMessage` bridge `davent:ds-api` whitelisted to
  `PUBLIC_API_RE`), visit counter (IP+date dedupe).
- **Billing**: checkout/subscription → MP preference; webhook
  `/api/payments/webhook/` (HMAC manifest + 10-min freshness + `x-request-id`
  dedup + `MP_WEBHOOK_ALLOW_UNSIGNED` opt-in only with DEBUG); `/sync/`;
  coupons; plan assign (staff); invoices auto-issued on approved payment.
- **Ecommerce**: buyer orders (`transfer`/`mp`), proof uploads, tracking
  token, memberships, seller MP OAuth + BYO storage config, support threads.
- **Platform**: chat (premium-gated, staff↔customer), notifications, legal
  content reports, locations geo, McpApp skills (LLM tool endpoints).
- **Uploads**: all images through `normalize_image` (magic bytes, ≤4 MB read,
  `MAX_IMAGE_PIXELS=40M`, WebP recode q86, EXIF strip, R2 key server-generated);
  chat attachments private + 1h signed URLs; order proofs; pattern markup via
  `sanitize_markup`.

## Trust boundaries and strongest controls

- anon→store data: `is_published` + `!is_blocked` + `has_public_link` +
  `grants_access()` else 404; public serializers minimize PII.
- owner→tenant data: `my_store()` queryset scoping (404 cross-tenant), plan
  benefit gates (`catalog_enabled`, `has_*` flags), `select_for_update` on
  quota checks.
- buyer→store: customer JWT + `IsCustomer`, store-scoped querysets,
  `tracking_token` for public order status.
- webhook→billing: HMAC-SHA256 manifest, freshness window, dedup, MP API
  re-fetch of truth, `external_reference` ownership, amount==plan price.
- pattern markup→DOM: `sanitize_markup` + sandboxed iframe without
  `allow-same-origin` + per-response nonce CSP + `PUBLIC_API_RE` bridge
  whitelist.
- secrets: env-only, `check_env`/`check --deploy` fail-closed, keyring for PII,
  write-only merchant secrets.

## Prior coverage

- `SECURITY_AUDIT.md` (repo root): 8+ manual audit rounds (Oct 30 → Nov 10),
  ~40 findings remediated; residuals are deployment-side (env vars, DAST,
  secret rotation) — not source-verifiable.
- `docs/security-audit-run1/`: formal 6-phase run scoped to the ecommerce
  branch; 9 confirmed (fixed), 1 needs_validation (MP refund idempotency —
  provider-side, still open).
- This run-2 covers the **whole current tree** (post-ecommerce merge). Prior
  confirmed records are treated as `prior_covered_same_source` units:
  re-hunted with fresh eyes but known-fixed root causes are excluded only
  where source confirms the fix is present.

## Companion selection

Selected per unit in `coverage-ledger.json`: WEB-PROTOCOL-AND-AUTH (sessions,
federated login, HTTP framing), DATA-ISOLATION-AND-LIFECYCLE (tenant
isolation, PII lifecycle), CLIENT-SIDE (SPA XSS, postMessage, storage),
PROTOCOLS-RPC-AND-MESSAGING (webhook replay/ordering, chat), RESOURCE-
EXHAUSTION-AND-AVAILABILITY (throttles, uploads, quotas), CLOUD-AND-DEPLOYMENT
+ SUPPLY-CHAIN-AND-RELEASE (docker, CI, deps), AI-AND-LLM (McpApp skills).
Excluded blocks are recorded per unit with source facts.
