# Security Audit Report — run-2 (full repository)

- **Run**: run-2 · profile `standard` · repo `DaventSaaS`
- **Source ref**: `80f87a7a (HEAD, clean worktree)`
- **Scope**: whole repository: AdminApp, StoreApp, SuscriptionApp, McpApp, DaventProject, frontend/src, docker, .github/workflows
- **Budget**: none set
- **Execution**: No OS sandbox with no-network/read-only enforcement is available on this Windows host; hunters are source-only (method=source, artifact=null). Target-controlled execution was not performed; decisive runtime/deployment facts are recorded as needs_validation.
- **Prior run**: docs/security-audit-run1, SECURITY_AUDIT.md — used for coverage priors only; every retained record was re-verified against current source in this run.
- **Agents spent**: 13 hunters (10 wave-1 + 3 wave-2 gap-fill) + 1 coverage critic + 11 Phase-3 candidate verifiers + 23 Phase-5 record verifiers = 48 agent invocations.
- **Deferred / out-of-scope**: see Coverage summary. Wave-2 critic gaps were closed by hunters 11–13 before Phase-3; no coverage unit remains blocked.

## Security posture

The platform has a mature baseline: parameterized queries throughout, WebP image normalization on every upload path, signed Mercado Pago webhooks, sandboxed/CSP-locked design document rendering, owner-scoped querysets, and session-epoch sealing on customer JWTs. The residual risk concentrates in three places: (1) the anonymous-throttle abstraction silently disables itself for authenticated principals, which produced four independent confirmed bypasses (platform auth email side-effects, feed writes, content reports); (2) cost-bearing endpoints lack bounds proportional to their hold/amplification cost — the SSE stream endpoint allows a single self-registered customer to lease all gunicorn workers, and unbounded taxonomy/discount creation inflates public catalog cost; (3) billing amount→entitlement binding trusts a union of all plan prices, allowing cross-plan price acceptance. Deployment-coupled items (admin URL proxying, PUBLIC_DOMAIN, webhook throttle starvation under provider IP sharing) remain unproven and are listed under NEEDS VALIDATION.

## Confirmed findings

| Severity | Finding | Boundary | Observed result |
|---|---|---|---|
| **high** | Single customer account + single IP can saturate all gunicorn gthreads via replayable SSE tickets (full-API DoS) | `customers-sse:worker-exhaustion` | GET /api/customer/notifications/stream/ is AllowAny and authenticated solely by a replayable signed ticket, throttled only by CustomerPublicReadThrottle (sco… |
| **medium** | Caddy edge image builds caddy-dns/cloudflare plugin at unpinned latest — mutable build input into the TLS terminator for all traffic | `infra:caddy-xcaddy-unpinned` | docker/caddy/Dockerfile runs `xcaddy build --with github.com/caddy-dns/cloudflare --replace golang.org/x/net=golang.org/x/net@v0.62.0` |
| **medium** | DEBUG=True reachable in production via non-'True' env spellings — every deploy guard compares raw strings while decouple cast=bool accepts 'true'/'1'/'yes'/'on' | `infra:debug-bypass-spellings` | Three independent gates try to keep DEBUG off in production and all three compare the raw env string, not the parsed boolean: (1) docker/api/entrypoint.sh ru… |
| **medium** | Authenticated users bypass the content_report throttle entirely — unbounded report emails to the legal mailbox | `legal.content-report.throttle-anon-only-authenticated-bypass` | POST /api/content-reports/ is AllowAny and every valid create enqueues a Celery task that sends an email to LEGAL_REPORTS_EMAIL |
| **medium** | Any paid plan price satisfies the payment amount check — pay the cheapest tier price, receive the most expensive plan for 30 days | `payments.cross-plan-amount-acceptance` | CreatePaymentQuery validates an MP payment's transaction_amount against `accepted_amounts`, which is the UNION of every non-trial plan price plus pending_cha… |
| **medium** | Inventory denial and merchant spam via soft stock-reservation abuse across self-registered customer accounts | `store-customer:stock-reservation-abuse-needs-validation` | End-to-end source-verified abuse chain: (1) POST /api/customer-auth/register/ is AllowAny self-service registration guarded only by CustomerRegisterThrottle … |
| **medium** | Plan-gate bypass: store owner address leaks via pattern documents and /r/maps/ redirect on plans without has_location_map | `store-public:location-address-plan-gate-bypass` | StorePublicSerializer.get_location_address correctly requires customization.show_location AND profile_has_benefit(user,'has_location_map') AND user.address (… |
| **medium** | Google social login auto-links by email without anti-pre-hijacking: pre-registered account stays accessible to attacker after victim's Google login | `users-auth:google-autolink-prehijack` | SocialLoginQuery resolves the account purely by email__iexact and, for an existing user, issues a session and sets email_verified=True — but never invalidate… |
| **low** | No quota on categories, brands or discounts lets a store owner amplify public catalog request cost without bound | `catalog-owner:uncapped-taxonomy-discount-public-cost` | Category, Brand and Discount creation are gated only by plan flags — catalog_enabled (has_public_link, present on the cheapest paid plan) and has_discounts (… |
| **low** | Chat payload leaks full staff directory (ids, names/usernames, online presence) to every paying customer despite per-message anonymity | `chat.staff-roster-leaks-all-staff-identities` | The support chat deliberately anonymizes staff in messages — ChatMessageSerializer.get_sender_name returns the constant 'Soporte DAVENT' for from_staff messa… |
| **low** | Django 5.2 GZipMiddleware buffers the entire SSE stream — events and heartbeats only reach the client at ~50s stream close | `customers-sse:gzip-buffering` | GZipMiddleware is enabled (DaventProject/settings.py:241) and the pinned runtime is Django==5.2.18 (requirements.txt:17), installed verbatim into both deploy… |
| **low** | Stream ticket is a replayable, session-unbound bearer credential transmitted in the URL query (120s window) | `customers-sse:ticket-replay-no-epoch` | The SSE credential is signing.dumps({'c': customer_pk, 's': slug}, salt='customer-notifications-stream') verified with max_age=TICKET_TTL=120 |
| **low** | Feed customer writes (comment/like/vote) are completely unthrottled — FeedWriteThrottle is an AnonRateThrottle that skips authenticated customers | `feed-customer-writes-unthrottled-anon-throttle` | All three customer write endpoints of the store feed — POST /api/stores/public/<slug>/feed/<pk>/comments/, .../like/, .../vote/ — declare FeedWriteThrottle (… |
| **low** | Mercado Pago checkout redirect not host-validated in platform billing flows (LOW) | `frontend:mp-checkout-redirect-not-host-validated` | The codebase documents and implements a client-side revalidation control for Mercado Pago checkout redirects: PaymentInstructions.vue:36-47 defines isMpCheck… |
| **low** | RequestIdMiddleware logs raw request.path — percent-encoded control chars forge log lines | `infra:request-path-log-injection` | RequestIdMiddleware.__call__ ends every request with logger.info('request id=%s %s %s -> %s (%.0fms)', ..., request.method, request.path, ...) |
| **low** | StoreSitemap lists stores that fail the public-access gate (missing has_public_link / active-subscription check) | `infra:sitemap-benefit-gate` | /sitemap.xml is public and unauthenticated wherever Django serves it |
| **low** | Support-chat image attachments bypass all storage quota AND all rate limiting — unbounded R2 growth per paid user | `uploads:chat-attachments-no-storage-quota` | Every store-scoped image upload consumes the plan quota (Store.storage_used_bytes under select_for_update) or is a bounded staff/platform asset |
| **low** | AnonRateThrottle subclasses skip authenticated users -> authenticated attacker gets unbounded password-reset emails (mail bombing / SMTP+queue abuse) | `users-auth:anon-throttle-authenticated-bypass` | Every auth-endpoint throttle in AdminApp/domains/users/views/auth_views.py subclasses plain rest_framework AnonRateThrottle (LoginRateThrottle, RefreshRateTh… |
| **low** | Email-verification token is not bound to the email address: a stale link verifies a newly changed, never-proven email | `users-auth:email-verify-token-not-email-bound` | EmailVerificationTokenGenerator._make_hash_value signs only user.pk + user.password + timestamp + profile.email_verified — user.email is absent |
| **low** | No Origin/Referer check on platform session-issuing endpoints -> login CSRF (session donation) on /api/token/ and /api/auth/google/ | `users-auth:login-csrf-no-origin-check` | CustomTokenObtainPairView and GoogleAuthView plant the session cookies (davent_refresh httpOnly + davent_csrf) in the response with no validation of the requ… |

### HIGH — Single customer account + single IP can saturate all gunicorn gthreads via replayable SSE tickets (full-API DoS)

**Fingerprint**: `customers-sse:worker-exhaustion` · **Confidence**: high

**Location**: StoreApp/domains/customers/urls/urls.py, StoreApp/domains/customers/views/notification_views.py, StoreApp/domains/customers/views/auth_views.py, docker/api/gunicorn.conf.py

**Principal**: Attacker needs one customer account: POST /api/customer-auth/register/ is AllowAny self-service issuing an immediate JWT ('register' throttle 10/hour/IP is irrelevant — one account suffices). No platform (auth.User) account or email verification needed. 

**Description**: GET /api/customer/notifications/stream/ is AllowAny and authenticated solely by a replayable signed ticket, throttled only by CustomerPublicReadThrottle (scope 'public_read' = 1000/hour per IP). Each SSE connection consumes exactly one throttle token at check_throttles time and then occupies one gunicorn gthread for up to STREAM_MAX_SECONDS=50s (bounded below only by client disconnect, detected on the next ≤15s ping write). The whole API shares workers=3 × threads=4 = 12 concurrent request handlers (docker/api/gunicorn.conf.py:14-16; compose/.env.example 3×4, Render blueprint 2×4=8 — even easier). Sustained saturation needs ~N×3600/50 connection-opens/hour (864 for 12 threads, 576 for 8) — inside the 1000/hour per-IP budget with ~14-42% headroom, and a fresh burst of up to 1000 requests is allowed instantly by the sliding-window throttle. Because tickets carry no jti (customers-sse:ticket-replay-no-epoch), ONE ticket authorizes unlimited concurrent streams during its 120s TTL; ~720 ticket-mints/day per account covers continuous operation, under the 'user'=1000/day stream-ticket budget — so a single self-registered customer account (registration issues a working JWT immediately, email_verified not required) plus one source IP suffices for indefinite full-API denial of service for every tenant, storefront, auth endpoint and admin path.

**Root cause**: The SSE endpoint was given the generic public-read throttle (1000/hour/IP, sized for cheap request/response reads) instead of a bound proportional to connection-hold cost: a stream request is not a read, it is a 50-second worker-thread lease. No per-customer/per-IP concurrent-stream counter exists, and the ticket's replayability within its 120s TTL makes per-connection credential cost ~zero.

**Trace**:
- `entrypoint` `StoreApp/domains/customers/urls/urls.py:59` (urlpatterns) — GET /api/customer/notifications/stream/ → CustomerNotificationStreamView.as_view() — public route proxied by nginx location /api/ (proxy_read_timeout 60s, no connection cap)
- `propagation` `StoreApp/domains/customers/views/notification_views.py:154` (CustomerNotificationStreamView) — permission_classes=[AllowAny], authentication_classes=[], throttle_classes=[CustomerPublicReadThrottle] — no session auth runs, so request.customer is never set and the throttle falls back to client IP
- `propagation` `StoreApp/domains/customers/views/auth_views.py:175` (CustomerRateThrottle.get_cache_key) — ident = f'c{customer.pk}' if request.customer else get_ident(request) → IP-keyed bucket; _pinned_ident (DaventProject/throttling.py:14-27) pins REMOTE_ADDR so XFF spoofing cannot multiply the quota; scope 'public_read' = '1000/hour' (DaventProject/settings.py:85); _ResilientThrottleMixin.allow_request fails OPEN on cache errors (throttling.py:73-79)
- `propagation` `StoreApp/domains/customers/views/notification_views.py:162` (CustomerNotificationStreamView.get) — signing.loads(ticket, max_age=120) authorizes the stream; no jti/single-use — one ticket opens unlimited concurrent connections for 120s (mint cost: CustomerApiThrottle 'user'=1000/day per customer, auth_views.py:210-214)
- `propagation` `StoreApp/domains/customers/views/notification_views.py:178` (CustomerNotificationStreamView.get/_events) — StreamingHttpResponse(self._events(...)) — gunicorn gthread iterates the generator synchronously; the worker thread is occupied until the monotonic deadline (STREAM_MAX_SECONDS=50, line 189/210) or client disconnect
- `sink` `docker/api/gunicorn.conf.py:14` (gunicorn gthread workers) — workers=int(env GUNICORN_WORKERS,3) × threads=int(env GUNICORN_THREADS,4), worker_class='gthread', timeout=60 — 12 concurrent request handlers for the ENTIRE API; Render blueprint pins 2×4=8 (render.yaml:185-188), .env.example documents 3×4

**Conditions**:
- _authentication_level_ — Attacker needs one customer account: POST /api/customer-auth/register/ is AllowAny self-service issuing an immediate JWT ('register' throttle 10/hour/IP is irrelevant — one account suffices). No platform (auth.User) account or email verification needed.
- _system_configuration_ — Deployed concurrency = GUNICORN_WORKERS×GUNICORN_THREADS. Both documented configs fall below the single-IP saturation threshold (3×4=12 needs ~864 conn/hour; 2×4=8 needs ~576 — both < 1000/hour). A larger env override would raise the bar but the endpoint still lacks any dedicated concurrency bound.
- _network_routing_ — All traffic from a single IP — the throttle ident pins REMOTE_ADDR|last-XFF so header spoofing cannot rotate the bucket; no per-IP connection cap exists at nginx or Caddy.
- _timing_dependency_ — Sustained scripted hold: open N≥thread-count concurrent streams, re-GET before each ~50s server close while the ticket is <120s old, mint a fresh ticket ~every 120s (~720/day < 1000/day 'user' budget).

**Reproduction** (Unauthenticated internet user who self-registers one buyer account and runs a small script holding SSE sockets.):
- 1. Register one customer account (open endpoint, JWT returned immediately).
- 2. Mint one stream ticket (replayable for 120s — unlimited concurrent GETs allowed with the same ticket).
- 3. Open ≥12 (or ≥8 on Render) concurrent GET /api/customer/notifications/stream/?ticket=<T> connections; each holds a gthread ~50s.
- 4. Cycle: re-open connections before each 'bye'/50s close using the same ticket until it nears 120s, then mint a new ticket (~every 2 minutes → ~720/day, under the 1000/day 'user' throttle).
- 5. Result: all gunicorn gthreads permanently occupied by streams → every other API request (all storefronts, auth, orders, admin) queues in the gunicorn backlog and times out at nginx (proxy_read_timeout 60s) for the duration of the attack.
- **Observed**: Source-traced end-to-end: throttle math (1000/hour/IP budget vs ~864-1000 needed holds/hour for 8-12 threads), thread-hold semantics of StreamingHttpResponse under gthread, replayable ticket removing per-connection credential cost, absence of any concurrency cap in view/nginx/Caddy/gunicorn config, and immediate-JWT open registration. No runtime test performed (source-only constraint).

**Impact**: While sustained, all 8-12 gunicorn gthreads are leased by SSE generators, so EVERY API endpoint for ALL tenants (storefronts, catalog, orders, customer and platform auth, admin) stalls behind the gunicorn backlog until nginx/proxy timeouts fire — a full multi-tenant availability kill for the price of one account.

**Priority rationale**: likelihood=high, impact=high.

**Smallest fix**: Bound concurrent holds, not just request rate: (1) dedicated throttle scope for the stream endpoint (e.g. 'customer_notifications_stream' ~120-240/hour per customer+IP) PLUS a cache-backed in-flight semaphore (max ~3 open streams per customer+IP, acquired on connect / released on generator close); (2) make tickets effectively single-use or few-use by embedding a jti consumed from cache at connect (the frontend already re-mints a ticket per connection, so single-use breaks nothing); (3) bind tickets to the session epoch (tokens_valid_after) and re-check customer.is_active inside _events; (4) optionally add nginx limit_conn on /api/customer/notifications/stream/ as a second layer.

### MEDIUM — Caddy edge image builds caddy-dns/cloudflare plugin at unpinned latest — mutable build input into the TLS terminator for all traffic

**Fingerprint**: `infra:caddy-xcaddy-unpinned` · **Confidence**: high

**Location**: docker/caddy/Dockerfile, docker/caddy/Caddyfile, docker-compose.yml

**Principal**: A malicious or compromised commit lands in caddy-dns/cloudflare (or its transitive deps) before the next image build, or a mutable base-image tag is repointed; xcaddy generates a fresh go.mod without a committed go.sum so there is no lockfile review surface. 

**Description**: docker/caddy/Dockerfile runs `xcaddy build --with github.com/caddy-dns/cloudflare --replace golang.org/x/net=golang.org/x/net@v0.62.0`. The --replace pins x/net, but the cloudflare plugin module itself has no @version — xcaddy resolves the latest commit of the module repo at image-build time and produces the caddy binary that becomes the production edge: it terminates TLS for the platform wildcard AND on-demand TLS for every verified customer custom domain, holds CF_API_TOKEN (Zone.DNS), and proxies all HTTP. Any writer to that upstream repo (or a compromised module resolution path before sumdb pinning — xcaddy generates a fresh go.mod without a committed go.sum) can land code in the next scheduled/CI image build -> rebuild -> deploy to the edge with full MITM capability over every request including admin sessions and customer PII. Base images caddy:2-builder/caddy:2 are also tag-mutable. Same class, lower trust: compose `docker compose pull` (ci-cd.yml:513) re-pulls tag-mutable postgres:16-alpine and redis:7.4-alpine on every deploy.

**Root cause**: Build input (VCS module + base image tags) not bound to an immutable version/digest; no go.sum committed for the xcaddy module set.

**Trace**:
- `entrypoint` `docker/caddy/Dockerfile:7` (xcaddy build) — RUN xcaddy build --with github.com/caddy-dns/cloudflare --replace golang.org/x/net=...@v0.62.0 — plugin module has no @version; xcaddy resolves latest at build time
- `propagation` `docker/caddy/Dockerfile:4` (base images) — FROM caddy:2-builder (line 4) and FROM caddy:2 (line 10) — mutable tags
- `propagation` `docker/caddy/Caddyfile:36` (wildcard platform site + on-demand custom domains) — *.{env.PLATFORM_DOMAIN} uses tls { dns cloudflare {env.CF_API_TOKEN} } (lines 36-39) and the https:// catch-all uses on_demand tls with ask -> api (lines 19-21,48-52): the unpinned plugin/binary controls DNS-01 for the wildcard cert and terminates TLS for every verified customer domain
- `sink` `docker-compose.yml:118` (db/redis images) — postgres:16-alpine (118) and redis:7.4-alpine (142) tag-mutable, re-pulled by `docker compose pull` each deploy (ci-cd.yml:513)

**Conditions**:
- _third_party_dependency_ — A malicious or compromised commit lands in caddy-dns/cloudflare (or its transitive deps) before the next image build, or a mutable base-image tag is repointed; xcaddy generates a fresh go.mod without a committed go.sum so there is no lockfile review surface.
- _environmental_dependency_ — Requires an upstream supply-chain compromise — external trigger, very improbable, but the blast radius is maximal (edge MITM + CF DNS token).

**Reproduction** (Not directly exploitable by a remote attacker; the exposure is a mutable build input into the highest-trust component. A compromised upstream module author or registry path would land code at the next image build.):
- (Source review) Confirm the Dockerfile resolves the plugin without a version; confirm Caddyfile routes all platform + customer-domain TLS through the resulting binary
- **Observed**: Source-confirmed absence of version pin; xcaddy semantics resolve latest by default. Trivy/image scanning would not catch a malicious-but-clean Go module.

**Impact**: Code execution inside the TLS-terminating edge yields full MITM of every platform and verified customer-domain request (admin sessions, customer PII, payment flows) plus possession of CF_API_TOKEN with Zone.DNS scope.

**Priority rationale**: likelihood=low, impact=critical.

**Smallest fix**: Pin the plugin: `xcaddy build --with github.com/caddy-dns/cloudflare@v0.5.0` (or current release) and vendor/commit the resulting go.mod+go.sum; digest-pin caddy:2-builder/caddy:2 bases; optionally digest-pin postgres/redis images or accept the risk explicitly.

### MEDIUM — DEBUG=True reachable in production via non-'True' env spellings — every deploy guard compares raw strings while decouple cast=bool accepts 'true'/'1'/'yes'/'on'

**Fingerprint**: `infra:debug-bypass-spellings` · **Confidence**: high

**Location**: DaventProject/settings.py, docker/api/entrypoint.sh, DaventProject/checks.py, DaventProject/urls.py (+1)

**Principal**: Operator/deploy sets DEBUG to a truthy spelling other than the exact string 'True' in the deploy env (.env on VPS, dashboard env on Render). Not attacker-controlled, but the guard chain exists precisely to catch this class of misconfiguration and all three layers fail on spelling. 

**Description**: Three independent gates try to keep DEBUG off in production and all three compare the raw env string, not the parsed boolean: (1) docker/api/entrypoint.sh runs `check --deploy` only `if [ "$DEBUG" != "True" ]`; (2) the CI deploy preflight greps `^DEBUG=True` case-sensitively; (3) every custom security check (DaventProject/checks.py project.E001-E005, envguard E006-E018 prod rules, users.E001-E003) early-returns or is skipped when settings.DEBUG is true. But settings.py parses `DEBUG = config('DEBUG', default=False, cast=bool)` and python-decouple's bool cast uses strtobool semantics (verified by executing the repo venv: 'true','TRUE','1','yes','on','t','y' all -> True). So DEBUG=true/1/yes/TRUE/on in .env or the Render dashboard yields settings.DEBUG=True while the entrypoint still runs check --deploy — which passes vacuously because all project checks return [] under DEBUG and Django's own deploy findings are warnings below --fail-level ERROR — and the CI grep misses it entirely. urls.py then mounts /api/auth/ (api-auth/), /api/schema/, swagger, redoc, and static(MEDIA_URL): the last serves MEDIA_ROOT including private/ chat attachments on deployments without the nginx /media/private/ 404 (Render). Technical 500/404 pages also expose tracebacks. SECURE_* cookie/HSTS defaults flip to insecure under DEBUG, though both documented deploys pin them explicitly via compose/render.yaml env, mitigating that specific downgrade.

**Root cause**: Boolean security gates implemented as exact/case-sensitive shell string comparisons (`[ "$DEBUG" != "True" ]`, `grep '^DEBUG=True'`) instead of comparing the parsed settings.DEBUG, while the settings parser (python-decouple cast=bool -> strtobool) accepts a family of truthy spellings. No check anywhere asserts the effective settings.DEBUG is False in production.

**Trace**:
- `entrypoint` `DaventProject/settings.py:29` (settings module top-level) — DEBUG = config('DEBUG', default=False, cast=bool) — decouple _cast_boolean delegates to strtobool: 'true','t','yes','y','on','1' in any case parse True (verified in repo venv)
- `propagation` `docker/api/entrypoint.sh:20` (entrypoint gunicorn branch) — if [ "$DEBUG" != "True" ] — only the exact string 'True' skips check --deploy; 'true'/'1'/'yes'/'TRUE'/'on' run a check that cannot fail
- `propagation` `DaventProject/checks.py:24` (check_production_transport_security) — early-returns [] when settings.DEBUG; envguard computes prod = not settings.DEBUG (envguard.py:100) skipping prod rules, and users checks early-return at users/checks.py:18 and :38 — the whole custom check surface is vacuous under DEBUG
- `propagation` `DaventProject/urls.py:136` (DEBUG-gated urlpatterns) — if settings.DEBUG: mounts api-auth/, api/schema/, swagger, redoc and static(MEDIA_URL) at line 145 — private/ chat attachments under MEDIA_ROOT become web-served where no nginx 404s them
- `sink` `.github/workflows/ci-cd.yml:480` (deploy preflight) — grep -q '^DEBUG=True' .env is case-sensitive and misses every other truthy spelling; the Render deploy path has no equivalent gate at all

**Conditions**:
- _environmental_dependency_ — Operator/deploy sets DEBUG to a truthy spelling other than the exact string 'True' in the deploy env (.env on VPS, dashboard env on Render). Not attacker-controlled, but the guard chain exists precisely to catch this class of misconfiguration and all three layers fail on spelling.
- _system_configuration_ — On the VPS compose path SECURE_SSL_REDIRECT/SESSION_COOKIE_SECURE/CSRF_COOKIE_SECURE/SECURE_HSTS_* are pinned by x-api-env defaults so the cookie/HSTS downgrade is mitigated there; on Render they are pinned in render.yaml. The schema/docs/api-auth/technical-error-page exposure and (on Render) MEDIA static exposure are unconditional once DEBUG parses True.

**Reproduction** (Not directly attacker-controlled: an operator mistake or compromised deploy config sets DEBUG; afterwards any unauthenticated internet user can reach the exposed surfaces.):
- Set DEBUG to a non-'True' truthy spelling in the deploy environment
- Restart/redeploy the api service (entrypoint runs check --deploy which returns no errors)
- As an anonymous client request /api/schema/, /api/docs/swagger/, /api-auth/ and a non-DRF route that raises to observe the technical debug page; on Render also request /media/private/<known-key>
- **Observed**: Source + local venv verification: decouple parses all listed spellings to True; entrypoint still runs check --deploy which passes vacuously (all custom checks early-return on settings.DEBUG; Django deploy findings are warnings below --fail-level ERROR); gunicorn boots with settings.DEBUG=True; urls.py DEBUG block mounts schema/docs/browsable API and static(MEDIA_URL).

**Impact**: Effective DEBUG=True in production exposes the full OpenAPI schema, swagger/redoc, the DRF browsable-API login, technical 500/404 pages with tracebacks, and — on deployments without the nginx /media/private/ 404 (Render, or any no-storage env) — static(MEDIA_URL) serving private/ chat attachments; it also neutralizes every custom deploy check so other misconfigurations pass silently.

**Priority rationale**: likelihood=low, impact=high.

**Smallest fix**: Normalize once and compare the parsed value everywhere: (1) entrypoint.sh and the CI preflight should test settings.DEBUG (e.g. `python -c "import django; django.setup(); from django.conf import settings; raise SystemExit(0 if settings.DEBUG else 1)"`) or grep case-insensitively for all truthy spellings; (2) add an envguard rule that errors when the raw DEBUG env parses truthy in a deploy context; (3) decouple the urls.py DEBUG block from DEBUG alone (require an explicit SCHEMA_ENABLED-style flag) so a DEBUG slip cannot expose schema/docs/media.

### MEDIUM — Authenticated users bypass the content_report throttle entirely — unbounded report emails to the legal mailbox

**Fingerprint**: `legal.content-report.throttle-anon-only-authenticated-bypass` · **Confidence**: high

**Location**: AdminApp/domains/legal/views/viewset_base.py, AdminApp/domains/legal/views/viewset_config.py, AdminApp/domains/legal/services/services.py, AdminApp/domains/users/tasks.py (+1)

**Principal**: Attacker holds any registered platform account (free registration; no subscription/plan required). A valid JWT access token sent as 'Authorization: Bearer <token>' makes request.user authenticated. 

**Description**: POST /api/content-reports/ is AllowAny and every valid create enqueues a Celery task that sends an email to LEGAL_REPORTS_EMAIL. The dedicated anti-spam throttle (scope 'content_report', 5/hour per IP) is implemented as ContentReportRateThrottle(AnonRateThrottle) at AdminApp/domains/legal/views/viewset_base.py:14-18. DRF's AnonRateThrottle.get_cache_key() returns None whenever request.user.is_authenticated (venv/Lib/site-packages/rest_framework/throttling.py:173-180) and SimpleRateThrottle.allow_request returns True when the key is None (throttling.py:119-121). Worse than the hunter claimed: ContentReportBaseViewSet.throttle_classes = [ContentReportRateThrottle] (viewset_base.py:25) REPLACES DRF's DEFAULT_THROTTLE_CLASSES (settings.py:75-78: ResilientAnonRateThrottle + ResilientUserRateThrottle), so for an authenticated caller NO rate limit applies at all — not even the 'user' 1000/day fallback the hunter assumed. JWTAuthentication is the default auth class (settings.py:64-66) and DRF authenticates before permission checks, so a valid Bearer token on the AllowAny endpoint fully populates request.user. The frontend itself sends the platform Bearer on this endpoint (legal.api.js uses http.js whose interceptor attaches Authorization when a session token exists, http.js:116-124). Result: any registered account (free registration, no plan required) can submit an unlimited number of valid reports — each creating a ContentReport row, a Celery task, and an email to LEGAL_REPORTS_EMAIL — completely defeating the 5/hour bound that settings.py:132-134 documents as the anti-email-bombing control.

**Root cause**: ContentReportRateThrottle subclasses AnonRateThrottle (viewset_base.py:14-18), which is anonymous-only by design, and it is installed via throttle_classes which overrides the project's default throttle set. For authenticated requests get_cache_key() returns None so the throttle silently allows everything, and because the viewset replaces DEFAULT_THROTTLE_CLASSES no other throttle (anon 100/day, user 1000/day) covers the gap.

**Trace**:
- `entrypoint` `AdminApp/domains/legal/views/viewset_base.py:25` (ContentReportBaseViewSet.throttle_classes) — throttle_classes = [ContentReportRateThrottle] replaces DRF DEFAULT_THROTTLE_CLASSES entirely; this is the only throttle consulted for every action including create.
- `propagation` `AdminApp/domains/legal/views/viewset_base.py:14` (ContentReportRateThrottle) — class ContentReportRateThrottle(AnonRateThrottle) with scope='content_report' (line 18). AnonRateThrottle.get_cache_key returns None for authenticated users (venv throttling.py:173-180); allow_request returns True on None key (throttling.py:119-121).
- `propagation` `AdminApp/domains/legal/views/viewset_config.py:25` (ContentReportConfigs['create'].permissions) — create permissions = [AllowAny] — reachable with or without a session; JWTAuthentication (settings.py:64-66) still populates request.user for Bearer-authenticated callers before permission checks.
- `propagation` `AdminApp/domains/legal/services/services.py:23` (CreateContentReportQuery) — Every valid create calls send_legal_report_email.delay(report.pk) after ContentReport.objects.create.
- `propagation` `AdminApp/domains/users/tasks.py:67` (send_legal_report_email) — Celery task (autoretry x3) -> NotifyContentReportQuery -> send_mail to settings.LEGAL_REPORTS_EMAIL (legal/services/services.py:41-48).
- `sink` `DaventProject/settings.py:134` (DEFAULT_THROTTLE_RATES['content_report']) — 'content_report': '5/hour' — the intended bound; unreachable for authenticated users because the anon-only throttle never keys them.

**Conditions**:
- _authentication_level_ — Attacker holds any registered platform account (free registration; no subscription/plan required). A valid JWT access token sent as 'Authorization: Bearer <token>' makes request.user authenticated.
- _system_configuration_ — Default DRF JWTAuthentication populates request.user on the AllowAny endpoint; Celery task delivery (eager in dev, worker in prod) sends one email per accepted report.
- _data_state_ — Request body must pass ContentReportSerializer validation (valid kind, http(s) reported_url, description >= validators, good_faith=true; original_work required only for COPYRIGHT/TRADEMARK).

**Reproduction** (Registered platform user (free account) scripting POST /api/content-reports/ with their own Bearer access token in a loop.):
- Register a free platform account and obtain an access token via POST /api/token/.
- Loop POST /api/content-reports/ with the JSON body above and 'Authorization: Bearer <access_token>'.
- Observe that requests beyond the first 5 within an hour still return 201 (each creating a ContentReport row and enqueueing an email) — no 429 is ever returned for the authenticated principal; only request throughput bounds the volume.
- Repeat with additional accounts to multiply volume; anonymous callers from the same IP remain capped at 5/hour.
- **Observed**: Source-derived: for authenticated requests ContentReportRateThrottle.get_cache_key returns None -> allow_request True, and because throttle_classes replaces DEFAULT_THROTTLE_CLASSES no other throttle engages, so every request returns 201 with no rate limit at all (unbounded, worse than the ~1000/day fallback the hunter assumed). Anonymous callers are correctly capped at 5/hour per IP by the same class.

**Impact**: Each accepted POST yields a DB row, a Celery task and an email to the internal legal mailbox — unbounded per account (multi-account multiplies), enabling mailbox flooding and SMTP/Celery/DB resource exhaustion. No credential or tenant-data exposure; impact is operational, not confidentiality.

**Priority rationale**: likelihood=high, impact=medium.

**Smallest fix**: Make the content_report scope cover both principal classes. Either pair the anon throttle with an authenticated-user throttle on the same scope, or replace the class with a SimpleRateThrottle whose get_cache_key returns 'user_pk' when authenticated and pinned IP otherwise — and inherit DaventProject.throttling._ResilientThrottleMixin so a cache outage fails open consistently with the rest of the project. Keep throttle_classes containing BOTH classes (do not rely on DEFAULT_THROTTLE_CLASSES, which this viewset overrides).

### MEDIUM — Any paid plan price satisfies the payment amount check — pay the cheapest tier price, receive the most expensive plan for 30 days

**Fingerprint**: `payments.cross-plan-amount-acceptance` · **Confidence**: high

**Location**: AdminApp/domains/payments/views/viewset.py, AdminApp/domains/payments/services/services.py, AdminApp/domains/suscriptions/serializers/serializers.py, AdminApp/domains/suscriptions/services/services.py

**Principal**: Attacker holds a platform account (store-owner principal) with billing fields complete — BillingMissingFieldsQuery (payments/views/viewset.py:275-280) only requires fiscal profile data, trivially supplied. 

**Description**: CreatePaymentQuery validates an MP payment's transaction_amount against `accepted_amounts`, which is the UNION of every non-trial plan price plus pending_charge — not the amount corresponding to the entitlement actually being granted. A payment whose amount equals ANY plan's price is accepted and ApplyPendingPlanQuery then applies whatever pending_plan_suscription (or the already-rewritten plan_suscription of a pending_payment subscription) is set, granting the most expensive plan while collecting the cheapest plan's price. The broad acceptance was added deliberately to avoid orphaned MP charges when a preference/debit was issued before a plan change (services.py:107-112 comments), but it decouples amount from entitlement in both directions. Verified deterministic exploit: (a) pending_payment subscription — create checkout preference at cheap plan, PATCH plan_suscription to expensive (PENDING_PAYMENT branch rewrites plan_suscription directly), pay the stale cheap preference -> expensive plan ACTIVE 30d; (b) active subscription — create checkout preference at current cheap plan price, then request upgrade to expensive plan (pending_plan + prorated pending_charge via RequestPlanChangeQuery), pay the stale cheap preference -> paid_amount != pending_charge so prorated=False -> pending expensive plan applied AND end_date renewed +30d. Repeatable monthly via the stale-preference cycle or a failed best-effort UpdatePreapprovalPlanQuery realignment (RequestPlanChangeQuery swallows MP errors). IssueInvoiceQuery then emits a fiscally inconsistent invoice: plan_name snapshot = expensive plan, total = cheap payment.amount.

**Root cause**: AdminApp/domains/payments/services/services.py CreatePaymentQuery lines 115-124: `accepted_amounts` unions {pending_plan-or-current price, current plan price, ALL SuscriptionPlan prices where is_trial=False, pending_charge} and only checks set membership — the granted entitlement (pending_plan or pending_payment plan_suscription) is never bound to the amount paid. `expected_amount` (line 106) is computed but used only in the error message. ApplyPendingPlanQuery (lines 281-313) applies pending_plan whenever a payment is APPROVED with renew=True; the only amount-sensitive gate is `paid_amount == pending_charge` deciding prorated-vs-full-renewal, never amount-vs-plan-price.

**Trace**:
- `entrypoint` `AdminApp/domains/payments/views/viewset.py:285` (PaymentViewSet.checkout) — POST /api/payments/checkout/ -> _resolve_suscription -> CreateCheckoutPreferenceQuery(suscription): preference unit_price = pending_charge or (pending_plan or plan_suscription).price snapshot at creation time; external_reference = str(suscription.id). An earlier preference keeps its creation-time amount and stays payable.
- `propagation` `AdminApp/domains/payments/services/services.py:377` (CreateCheckoutPreferenceQuery) — Lines 382-391 freeze unit_price + external_reference into the MP Checkout Pro preference — the charged amount is immutable once issued; MP preferences remain payable at the snapshot price.
- `propagation` `AdminApp/domains/suscriptions/serializers/serializers.py:68` (SuscriptionSerializer.update) — PATCH /api/suscriptions/<id>/ {plan_suscription}: PENDING_PAYMENT branch (lines 74-83) rewrites plan_suscription directly to the expensive plan; ACTIVE branch (line 90) -> RequestPlanChangeQuery sets pending_plan_suscription=expensive + pending_charge=prorated.
- `propagation` `AdminApp/domains/suscriptions/services/services.py:133` (RequestPlanChangeQuery) — Lines 132-135: upgrade sets pending_plan_suscription=target_plan and pending_charge=_upgrade_charge(...) (prorated); downgrade sets pending_plan only. Live-preapproval realignment is best-effort — exceptions swallowed at lines 136-141, so MP can keep debiting the old amount.
- `propagation` `AdminApp/domains/payments/views/viewset.py:140` (PaymentViewSet.webhook) — MP notification for the stale cheap payment arrives at POST /api/payments/webhook/ (or via POST /api/payments/sync/ viewset.py:432 or POST /api/payments/ create) -> PaymentWebhookQuery -> CreatePaymentQuery with the attacker-owned suscription.
- `propagation` `AdminApp/domains/payments/services/services.py:124` (CreatePaymentQuery) — `if amount not in accepted_amounts` — the cheap amount passes because accepted_amounts (lines 115-123) contains EVERY non-trial plan price; the pending/expensive entitlement is never bound to the paid amount.
- `sink` `AdminApp/domains/payments/services/services.py:287` (ApplyPendingPlanQuery) — Lines 287-313: pending_plan applied to plan_suscription unconditionally on APPROVED; prorated gate (281-286) requires paid_amount == pending_charge exactly, so any other accepted amount -> prorated=False -> end_date = now+30d, status=ACTIVE, period_payment_id=payment. Expensive plan granted at cheap-tier price.

**Conditions**:
- _authentication_level_ — Attacker holds a platform account (store-owner principal) with billing fields complete — BillingMissingFieldsQuery (payments/views/viewset.py:275-280) only requires fiscal profile data, trivially supplied.
- _data_state_ — At least two non-trial SuscriptionPlans with different prices — the seeded default set (25000/30000/40000/60000 ARS) satisfies this out of the box.
- _third_party_dependency_ — A payable stale-amount MP artifact bound to external_reference=<own suscription.id>: a Checkout Pro preference issued before the plan change keeps its creation-time unit_price (standard MP behavior the codebase explicitly relies on, services.py:107-112), or a preapproval debit generated before realignment.
- _user_interaction_ — The attacker must complete the cheap-tier MP payment with real funds at the lower plan price — no provider misbehavior, race, or admin action is required; the sequence is fully deterministic.

**Reproduction** (Registered DAVENT platform user with a complete billing profile and >=2 priced plans available (seeded default).):
- Ensure billing fields are complete (GET subscription -> billing_required fields if any).
- Create the cheap-priced MP artifact first: POST /api/payments/checkout/ while the subscription targets the cheap plan (variant A: fresh pending_payment sub; variant B: active cheap-plan sub). Do NOT pay it yet.
- Change the granted/target plan to the expensive one via PATCH /api/suscriptions/<id>/ {"plan_suscription": <expensive_pk>} (or POST /api/payments/checkout/ {"suscription": <id>, "plan_suscription": <expensive_pk>}, which also issues a new expensive preference while leaving the cheap one payable).
- Pay the earlier cheap preference in the MP Checkout UI — it charges the snapshot cheap price with external_reference=<sub_id>.
- Trigger registration: await the MP webhook, or POST /api/payments/sync/ {"payment_id": <id>}, or POST /api/payments/ {"suscription": <id>, "payment_id": <id>}.
- Observe: Payment row amount=cheap_price status=approved; Suscription.plan_suscription=expensive, status='Suscripcion activa', end_date=now+30d; Invoice total=cheap_price plan_name=expensive; grants_access()=True -> full expensive-tier benefits for 30 days at cheap-tier price.
- **Observed**: Source-derived (read-only audit, MP not contacted): CreatePaymentQuery accepts amount=cheap because it is in accepted_amounts (all non-trial plan prices); Payment created APPROVED; ApplyPendingPlanQuery applies pending_plan (or the already-rewritten plan_suscription for pending_payment) and sets end_date=now+30d with status=ACTIVE; IssueInvoiceQuery emits invoice with plan_name=expensive plan and total=cheap amount. grants_access() returns True -> expensive-tier benefits at cheap-tier price, repeatable monthly.

**Impact**: Direct recurring revenue loss bounded by the plan price spread per billing period (e.g. 25000 vs 60000 ARS -> top tier at entry-tier price, repeatable). Also produces fiscally inconsistent invoices (expensive plan_name, cheap total, CAE requested) — a compliance/reconciliation problem. Does not grant admin access or cross-tenant data; impact is confined to plan-tier benefits and billing integrity.

**Priority rationale**: likelihood=medium, impact=medium.

**Smallest fix**: Bind the accepted amount to the granted entitlement instead of unioning all plan prices. Compute expected = pending_charge if set else (pending_plan or plan_suscription).price for pending_payment contexts; accept only that amount for auto-apply. For genuinely stale MP artifacts (amount equals a DIFFERENT plan's price), resolve amount->plan and grant THAT plan — never the pending/pricier one — or reject and route to audit_orphan_payments/manual reconciliation like the storepayments sibling (exact amount match + amount_mismatch review). Also make UpdatePreapprovalPlanQuery realignment failure handling consistent so a stale-amount debit cannot recur monthly unnoticed (surface the failure instead of only logging).

### MEDIUM — Inventory denial and merchant spam via soft stock-reservation abuse across self-registered customer accounts

**Fingerprint**: `store-customer:stock-reservation-abuse-needs-validation` · **Confidence**: high

**Location**: StoreApp/domains/customers/views/auth_views.py, StoreApp/domains/orders/views/public.py, StoreApp/domains/customers/authentication.py, StoreApp/domains/orders/services/checkout.py (+1)

**Principal**: Target store is published with orders_enabled and has stock-controlled products (product.stock not null); low stock makes monopolization cheap — one order can claim up to 100 units of each of up to 50 SKUs. 

**Description**: End-to-end source-verified abuse chain: (1) POST /api/customer-auth/register/ is AllowAny self-service registration guarded only by CustomerRegisterThrottle (scope 'register' = 10/hour keyed by client IP when no customer session exists) with NO captcha — CustomerRegisterView.post never calls verify_captcha, and CustomerRegisterSerializer only requires a unique well-formed email plus a Django-policy password. RegisterCustomerQuery creates the Customer with model defaults is_active=True / email_verified=False and _session_response issues a working customer_access JWT immediately; email verification is never required anywhere in the order path (IsCustomer checks only isinstance+is_active; mails.py:269-272 only skips CUSTOMER lifecycle emails for unverified addresses). (2) POST /api/stores/public/<slug>/orders/ requires only IsCustomer and is throttled by OrderCreateThrottle — a ResilientUserRateThrottle (scope 'store_order_create', rate '10/hour') whose DRF UserRateThrottle.get_cache_key keys on request.user.pk = customer.pk, i.e. PER ACCOUNT, not per IP. One IP minting ~10 accounts/hour therefore yields ~100 orders/hour. (3) The order captcha is deterministic arithmetic (add/sub/mul of small ints, single-use nonce, 5 attempts, >=3s min delay) — a scriptable speed bump, not a bot barrier. (4) Each created order claims SOFT STOCK globally: claimed_quantities sums OrderItem.qty over ALL customers' orders with status=PENDING_PAYMENT and expires_at > now (no customer filter), and _resolve_lines rejects any buyer whose qty exceeds product.stock - claimed. Caps are MAX_QTY=100 per product line and MAX_ITEMS=50 lines per order, so a single order can claim up to 100 units of up to 50 SKUs. expires_at = now + payment_deadline_hours (default 48h, owner-configurable 1..720h via StorePaymentConfig serializer); release is TIME-BASED inside the claimed_quantities query (expires_at__gt=now) — it does NOT depend on the expire_orders cron, refuting the hunter's cron blocker. Sustaining the DoS needs only continuous re-ordering at 10/h/account. (5) Every order fires append_event('created') -> dispatch_order_event: 'created' is in OWNER_NOTIFY_KINDS (synchronous in-app Notification to the store owner) and OWNER_EVENT_KINDS (transaction.on_commit -> Celery -> _owner_new_order_mail SMTP). ~100 fake orders/hour/IP = ~100 owner emails+notifications per hour. Impact: a single scripted IP can keep any stock-controlled low-stock SKU permanently 'sold out' to legitimate buyers (qty > available -> ValidationError 'Stock insuficiente') and spam the merchant's inbox/notifications, at zero cost (orders just expire unpaid).

**Root cause**: Stock reservations are claimed per-order GLOBALLY (claimed_quantities counts every customer's PENDING_PAYMENT orders regardless of owner) while order creation is gated only by a per-customer-pk throttle (10/hour), a scriptable arithmetic captcha, and self-service registration that is itself only IP-throttled at 10/hour with no captcha and no email_verified requirement — there is no per-IP order throttle, no per-store pending-reservation cap, and no verified-principal requirement before stock claims materialize.

**Trace**:
- `entrypoint` `StoreApp/domains/customers/views/auth_views.py:220` (CustomerRegisterView.post) — POST /api/customer-auth/register/ — AllowAny self-service registration; throttle_classes=[CustomerRegisterThrottle] (line 229) = scope 'register' 10/hour (settings.py:111) keyed by IP via CustomerRateThrottle.get_cache_key fallback to get_ident when request.customer is None (lines 175-178). No captcha anywhere in the view (post at 231-246).
- `propagation` `StoreApp/domains/orders/views/public.py:122` (PublicOrderCreateView.post) — POST /api/stores/public/<slug>/orders/ — permission_classes=[IsCustomer] only; throttle_classes=[OrderCreateThrottle] (line 125) = ResilientUserRateThrottle scope 'store_order_create' rate '10/hour' (lines 63-67) keyed by request.user.pk = customer.pk via DRF UserRateThrottle.get_cache_key (venv rest_framework/throttling.py:193-202) — per ACCOUNT, not per IP. Captcha verified at line 136 (arithmetic, scriptable).
- `propagation` `StoreApp/domains/customers/authentication.py:76` (IsCustomer.has_permission) — Requires only isinstance(request.customer, Customer) and customer.is_active — no email_verified, no membership, no per-store check anywhere in the order path.
- `propagation` `StoreApp/domains/orders/services/checkout.py:272` (claimed_quantities) — Sums OrderItem.qty over Order.status=PENDING_PAYMENT AND order.expires_at__gt=now for the given product_ids across ALL customers (lines 286-294) — one global reservation pool; expiry is evaluated in the query, so release does not depend on the expire_orders cron.
- `propagation` `StoreApp/domains/orders/services/checkout.py:340` (_resolve_lines) — available = product.stock - claimed.get(pid, 0); qty > available -> ValidationError — attacker's pending orders exhaust stock for every other buyer. Caps MAX_QTY=100/line, MAX_ITEMS=50 lines (lines 88-89); expires_at = now + payment_deadline_hours, default 48h, owner-set 1..720h (line 464).
- `sink` `StoreApp/domains/orders/services/notify.py:56` (dispatch_order_event) — Every 'created' event: kind in OWNER_NOTIFY_KINDS -> synchronous in-app owner Notification (lines 35-38, 89-92) AND kind in OWNER_EVENT_KINDS -> transaction.on_commit Celery email -> mails.py:46-49,276-283 _owner_new_order_mail — fake orders spam the merchant inbox and panel.

**Conditions**:
- _data_state_ — Target store is published with orders_enabled and has stock-controlled products (product.stock not null); low stock makes monopolization cheap — one order can claim up to 100 units of each of up to 50 SKUs.
- _network_routing_ — Register throttle is per-IP (10/h) and order throttle per-account (10/h): a single IP yields ~10 accounts/h -> ~100 orders/h; IP rotation scales linearly. _pinned_ident (throttling.py:14-27) pins REMOTE_ADDR into the bucket so XFF spoofing does not reset it.
- _system_configuration_ — Throttles fail open on cache loss (deliberate, throttling.py:64-79) — but the configured 10/h rates already permit the abuse, so enforcement status does not gate exploitability; fail-open only increases attacker throughput.
- _third_party_dependency_ — The owner-email sub-impact requires a running Celery worker + reachable SMTP; the inventory-denial impact is synchronous DB state inside create_order and needs neither.

**Reproduction** (Anonymous internet user running a script against a public DAVENT store with ecommerce orders enabled.):
- Enumerate stock-controlled products and their stock via the public catalog endpoints.
- Register customer accounts at 10/hour per IP (no captcha; unique disposable emails suffice; session tokens issued immediately).
- For each account, fetch an order captcha, wait >=3s, solve the arithmetic question, and POST orders claiming qty=stock for target SKUs (up to 50 lines x 100 units per order).
- Repeat continuously: claims last until expires_at (48h default, up to 720h owner-set) and auto-release via expires_at__gt=now — sustained ~10 orders/h/account keeps low-stock SKUs 'sold out' indefinitely.
- Observe legitimate buyers receiving 'Stock insuficiente' ValidationErrors and the owner receiving an in-app notification + email per fake order.
- **Observed**: Source-derived (read-only audit, not executed): every link verified line-by-line — uncaptcha'd IP-throttled registration, per-customer.pk 10/h order throttle, global claimed_quantities across all customers' PENDING_PAYMENT orders, expires_at-based release independent of cron, and per-order owner notification+email dispatch.

**Impact**: Blocks legitimate purchase of targeted SKUs for the attack duration (claims auto-release at expires_at <=720h, default 48h, but the attacker sustains with continuous orders) and floods the merchant with order notifications/emails (~100/h/IP). Bounded per store, reversible, no confidentiality/integrity breach or payment fraud.

**Priority rationale**: likelihood=medium, impact=medium.

**Smallest fix**: Gate stock-claiming order creation on a verified principal and bound abuse per origin: (a) require customer.email_verified (or an equivalent verified-contact check) in PublicOrderCreateView/create_order before materializing claims; (b) add a per-IP order throttle alongside the per-account one so account minting does not multiply the budget; (c) cap simultaneous PENDING_PAYMENT reservations per store and/or per customer (e.g., reject create_order when the customer already holds >=N pending orders for the store, and/or when store-wide pending claims exceed a fraction of stock); (d) add captcha (or disposable-email checks) to customer registration; (e) optionally digest owner 'created' notifications/emails instead of one per order.

### MEDIUM — Plan-gate bypass: store owner address leaks via pattern documents and /r/maps/ redirect on plans without has_location_map

**Fingerprint**: `store-public:location-address-plan-gate-bypass` · **Confidence**: high

**Location**: StoreApp/domains/stores/views/viewset.py, StoreApp/domains/design/services/pattern_render.py, StoreApp/domains/stores/services/contact.py

**Principal**: None — both endpoints are AllowAny public actions (PUBLIC_ACTIONS, viewset.py:424,445-453). 

**Description**: StorePublicSerializer.get_location_address correctly requires customization.show_location AND profile_has_benefit(user,'has_location_map') AND user.address (serializers.py:800-817), but two other anonymous public surfaces re-derive the same PII without the benefit check. (1) pattern_render.build_store_context sets address = user.address whenever customization.show_location is true (pattern_render.py:1145) — no has_location_map check — and exposes it as store_address (:1172) plus store_maps_url = contact_redirect_path(store,'maps') (:1172/:1182); _page_flags 'location' (:236) and the flags_css hiding (:1818-1821) key only on show_*, never on plan. DesignPattern.render (design/models/models.py:358-380) substitutes {{store_address}} into the HTML served by GET /api/stores/public/<slug>/pattern/document/ and /pattern/; ~16 sources/*.html templates interpolate it, including 'esencial' — the platform DEFAULT_PATTERN (seed.py:56) and a tier-'base' pattern allowed on Plan basico. (2) contact_redirect_url kind=='maps' (contact.py:162-173) builds https://maps.google.com/?q=<user.address>,<city>,<province> from raw UserProfile.address with zero gates — it does not even check show_location — and is reachable via public_contact (viewset.py:689-711) which only requires is_published+is_blocked+has_public_link. Compounding: show_location defaults True (models.py:243) and the customization PATCH discards LOCATION_FIELDS=('show_location',) for plans without has_location_map (viewset.py:119-121,1398-1399), so a Plan basico owner cannot disable the toggle at all. Plan basico is seeded with has_public_link=True, has_customization=True, has_location_map=False (SuscriptionApp seeds.py:45-73), so every published basico store leaks the owner's EncryptedCharField business domicilio to anonymous visitors. Correction to the hunter's framing: expired/lapsed subscriptions yield empty plan_benefits_of() so has_public_link fails and all public routes 404 — the affected population is stores on an ACTIVE plan lacking has_location_map (Plan basico). The leak additionally requires a StoreCustomization row (auto-created by get_or_create on the dashboard's GET /api/stores/customization/, viewset.py:1391) and a non-empty user.address.

**Root cause**: The has_location_map plan gate is enforced only in StorePublicSerializer.get_location_address; pattern_render.build_store_context and stores/services/contact.py contact_redirect_url independently derive the owner address / maps URL from raw UserProfile.address + customization.show_location without consulting profile_has_benefit('has_location_map'), and the /r/maps/ branch does not even honor the owner's show_location toggle.

**Trace**:
- `entrypoint` `StoreApp/domains/stores/views/viewset.py:689` (StoreViewSet.public_contact) — Anonymous GET /api/stores/public/<slug>/r/<kind>/ (AllowAny via PUBLIC_ACTIONS). Gates only is_published+is_blocked (lines 694-697) and profile_has_benefit 'has_public_link' (698-699); kind='maps' flows into contact_redirect_url with no show_location/has_location_map check.
- `propagation` `StoreApp/domains/stores/views/viewset.py:818` (StoreViewSet.public_pattern_document) — Anonymous GET /api/stores/public/<slug>/pattern/document/ (and /pattern at :797) via _pattern_store (788-795): same published+unblocked+has_public_link gate only; no plan check on location data.
- `propagation` `StoreApp/domains/design/services/pattern_render.py:1145` (build_store_context) — address = _text(user.address,160) whenever customization.show_location is true — no profile_has_benefit(...,'has_location_map') check, unlike the serializer's triple gate.
- `propagation` `StoreApp/domains/design/services/pattern_render.py:236` (_page_flags) — 'location' flag keyed only on show_location; flags_css ([data-flag] display:none, lines 1818-1821) hides location zones by owner toggle only — plan benefit never consulted.
- `propagation` `StoreApp/domains/design/services/pattern_render.py:1172` (build_store_context context dict) — store_address (:1172) and store_maps_url = contact_redirect_path(store,'maps') (:1182) enter the render context; DesignPattern.render (design/models/models.py:358-380) substitutes {{store_address}} into the HTML served by /pattern and /pattern/document (escape() prevents markup injection, not disclosure).
- `sink` `StoreApp/domains/stores/services/contact.py:162` (contact_redirect_url) — kind=='maps' builds https://maps.google.com/?q=<user.address>,<city>,<province> from raw UserProfile.address — zero gates: no has_location_map benefit and not even customization.show_location.

**Conditions**:
- _authentication_level_ — None — both endpoints are AllowAny public actions (PUBLIC_ACTIONS, viewset.py:424,445-453).
- _data_state_ — Store is_published=True, is_blocked=False; owner has an ACTIVE subscription granting has_public_link but NOT has_location_map (Plan basico per seeds.py:45-73); UserProfile.address non-empty; a StoreCustomization row exists (auto-created by get_or_create on GET /api/stores/customization/, viewset.py:1391) with show_location=True — the default, which basico owners cannot change because PATCH discards LOCATION_FIELDS.
- _data_state_ — For the pattern-document path the resolved DesignPattern markup must reference {{store_address}} (true for the default 'esencial' and ~15 other sources); the /r/maps/ path needs only a non-empty address/city/province and leaks even when show_location=False.

**Reproduction** (Anonymous internet user who knows or discovers a published store slug (slugs are public via sitemap.xml, shared links, and the public catalog).):
- Enumerate published store slugs (sitemap.xml, public catalog, shared store links).
- For each slug on a plan without has_location_map (Plan basico), request GET /api/stores/public/<slug>/pattern/document/ and search the returned HTML for the address block rendered from {{store_address}} (e.g. 'Dirección', 'Cómo llegar' rows); alternatively GET /api/stores/public/<slug>/pattern/ and inspect the 'html' field of the JSON.
- Request GET /api/stores/public/<slug>/r/maps/ and read the 302 Location header — it contains https://maps.google.com/?q=<street address>,<city>,<province> even when the owner set show_location=False.
- **Observed**: Source-derived (no runtime execution): build_store_context populates store_address from user.address whenever customization.show_location is true with no plan check, so the pattern JSON/document HTML contains the plaintext business address; contact_redirect_url('maps') returns a Google Maps URL embedding the raw address with zero gates, so /r/maps/ 302s to it for any published+unblocked store with has_public_link — including Plan basico stores where StorePublicSerializer.location_address is null.

**Impact**: Unauthenticated disclosure of the owner's EncryptedCharField business domicilio (treated as plan-gated PII) plus circumvention of a paid-plan monetization gate and of the owner's own visibility toggle; no credentials, payment data, or cross-tenant access.

**Priority rationale**: likelihood=high, impact=medium.

**Smallest fix**: Apply the serializer's effective gate everywhere the address/maps URL is derived: require customization.show_location AND profile_has_benefit(store.user,'has_location_map') in build_store_context for address/store_maps_url and in the 'location' page flag; gate contact_redirect_url kind=='maps' (or public_contact) on the same benefit plus show_location. Consider a data migration or read-time coercion setting show_location=False for stores whose plan lacks has_location_map, since basico owners cannot clear it via PATCH.

### MEDIUM — Google social login auto-links by email without anti-pre-hijacking: pre-registered account stays accessible to attacker after victim's Google login

**Fingerprint**: `users-auth:google-autolink-prehijack` · **Confidence**: high

**Location**: AdminApp/domains/users/views/auth_views.py, AdminApp/domains/users/services/social.py

**Principal**: Attacker needs only anonymous access: POST /api/register/ is open (IsAnonimous) and POST /api/token/ requires only the chosen password. 

**Description**: SocialLoginQuery resolves the account purely by email__iexact and, for an existing user, issues a session and sets email_verified=True — but never invalidates the password the account already had. Registration does not require email verification, so an attacker can pre-register a victim's email with their own password (and their own unique phone). When the real mailbox owner later uses 'Login with Google', Google proves email ownership and the backend logs them into the ATTACKER-CREATED account — while the attacker's password remains fully usable. Both parties hold persistent sessions for the same account: the attacker retains silent read/write access to everything the victim does (profile PII, store claim now unblocked because email_verified is set True, billing data). The sibling buyer-side implementation (google_customer_login) documents and fixes exactly this threat as 'Anti-pre-hijacking' by calling set_unusable_password() and sealing tokens_valid_after; the platform-users domain never received the port.

**Root cause**: SocialLoginQuery (services/social.py:103-147) performs find-or-create by verified provider email but, on the existing-account branch, only fills email_verified/names — it does not check whether the matched account's email was ever verified, does not invalidate a usable password, and does not revoke outstanding sessions. The credential proof covers the EMAIL, not the party who chose the existing password.

**Trace**:
- `entrypoint` `AdminApp/domains/users/views/auth_views.py:529` (GoogleAuthView.post) — POST /api/auth/google/ {credential} → VerifyGoogleCredentialQuery + SocialLoginQuery → _social_session_response issues the DAVENT session
- `propagation` `AdminApp/domains/users/services/social.py:103` (SocialLoginQuery) — user = User.objects.filter(email__iexact=email).first() — matches ANY account with that email, including one pre-registered by an attacker with unverified email and a usable password
- `propagation` `AdminApp/domains/users/services/social.py:136` (SocialLoginQuery) — existing-account branch sets profile.email_verified=True and names only — no has_usable_password check, no set_unusable_password, no session revocation, no prior-verification gate
- `sink` `AdminApp/domains/users/views/auth_views.py:440` (_social_session_response) — RefreshToken.for_user(user) mints refresh+access for the Google-verified caller while the pre-registrant's password still authenticates via POST /api/token/

**Conditions**:
- _authentication_level_ — Attacker needs only anonymous access: POST /api/register/ is open (IsAnonimous) and POST /api/token/ requires only the chosen password.
- _data_state_ — The victim's email must be unregistered when the attacker pre-registers it, and the victim must later authenticate with Google on that same email.
- _system_configuration_ — GOOGLE_CLIENT_ID must be configured; otherwise GoogleAuthView returns 503 and the feature is off.
- _third_party_dependency_ — The victim must control a Google account whose verified email equals the pre-registered address.

**Reproduction** (Unauthenticated internet user who knows or guesses a target's email address.):
- 1. Attacker registers an account via POST /api/register/ using the victim's email, the attacker's own password, and a unique phone number (phone_hash uniqueness permits one account per phone — targeted attacks only).
- 2. The real mailbox owner later clicks 'Login with Google' on the platform; Google proves email ownership and SocialLoginQuery auto-links them into the attacker-created account, setting email_verified=True.
- 3. The attacker logs in with POST /api/token/ using their own username+password — the credential was never invalidated, so the attacker keeps a fully usable session alongside the victim's.
- **Observed**: Source-traced: SocialLoginQuery's existing-account branch (social.py:134-147) performs no password invalidation or session revocation; _social_session_response returns 200 with tokens to the Google caller; the password path via TokenObtainPairSerializer→authenticate() still returns 200 for the pre-registrant on the same User row. Both parties hold persistent sessions; profile.email_verified becomes True, also unblocking the store-claim gate.

**Impact**: Yields durable, silent shared access to the victim's account — profile PII, store claim unblocked via email_verified=True, billing data — until the victim changes password or resets; the sibling code proves the threat model was known.

**Priority rationale**: likelihood=low, impact=high.

**Smallest fix**: Port the customer-side anti-pre-hijacking hardening into SocialLoginQuery's existing-account branch: when the matched account has a usable password, call user.set_unusable_password() and revoke all outstanding sessions (_revoke_sessions), so only the mailbox owner retains access via Google or password reset. Optionally restrict auto-link to accounts whose email was already verified or that were social-created.

### LOW — No quota on categories, brands or discounts lets a store owner amplify public catalog request cost without bound

**Fingerprint**: `catalog-owner:uncapped-taxonomy-discount-public-cost` · **Confidence**: high

**Location**: StoreApp/domains/catalog/views/viewset.py, StoreApp/domains/catalog/views/viewset_base.py, StoreApp/domains/catalog/serializers/mixins.py, StoreApp/domains/stores/views/viewset.py (+1)

**Principal**: Authenticated store owner (IsAuthenticated) with an active subscription: has_public_link suffices for categories/brands (all paid plans); has_discounts requires premium or ecommerce. 

**Description**: Category, Brand and Discount creation are gated only by plan flags — catalog_enabled (has_public_link, present on the cheapest paid plan) and has_discounts (premium/ecommerce) — with no count limit anywhere in the viewsets, serializers, models or benefit catalog. Every other owner-writable collection that feeds shared payloads IS capped (max_products rechecked under select_for_update, SERVICES_MAX=24 under lock, image caps). These unbounded collections feed the anonymous public catalog endpoint: running_discount_stamp(store) is evaluated on EVERY request — including cache hits — to build the cache key (one query plus a Python sorted() loop calling campaign.is_running() per in-window discount). On cache miss, _public_catalog_data runs effective_pricing_of per product x per running discount (O(PxD) via winning_discount_of->discount_covers), serializes ALL categories and brands including empty ones, and serializes all running discounts as promotions. Distinct query strings mint distinct cache keys (_params_fingerprint), so varied anonymous filters multiply the miss-path cost. Discount creation additionally fires _broadcast_offer -> notify_store_discount to all store members per create.

**Root cause**: Resource quotas were applied to products, services and images but never to catalog taxonomy (categories, brands) or discounts, even though all of them are serialized into the shared public catalog payload on every cache miss and discounts are scanned on every request via the cache-key stamp.

**Trace**:
- `entrypoint` `StoreApp/domains/catalog/views/viewset.py:88` (CategoryViewSet) — Owner POST /api/categories/ (BrandViewSet identical at :93): CatalogGateMixin gates create/update/destroy only on catalog_enabled = has_public_link; inherited CatalogBaseViewSet.create does serializer validation + save with no count check.
- `propagation` `StoreApp/domains/catalog/views/viewset.py:132` (DiscountViewSet) — Owner POST /api/discounts/: gated only by has_discounts flag (:134-143); create (:148-154) has no count check and triggers _broadcast_offer (:166-178) notifying all store members per create.
- `propagation` `StoreApp/domains/catalog/views/viewset_base.py:60` (CatalogBaseViewSet.create) — Generic create path: serializer.is_valid(raise_exception=True) then save(store=my_store()) — no quota hook exists for taxonomy/discount viewsets (contrast: ProductViewSet.create overrides with a locked can_add_product check).
- `propagation` `StoreApp/domains/catalog/serializers/mixins.py:19` (TaxonomyMixinValidator.validate_name) — Only per-(store,name) uniqueness is validated; DiscountMixinValidator.validate (:116-178) checks scope ownership/window/products cap (500) but no collection count. Serializers and models add no bound (Category/Brand UniqueConstraint(store,name) at models.py:32,55; Discount has no name constraint at all, models.py:243-245).
- `propagation` `StoreApp/domains/stores/views/viewset.py:1033` (StoreViewSet.public_catalog) — Every anonymous GET /api/stores/public/<slug>/catalog/ builds cache_key including running_discount_stamp(store) BEFORE cache_get — the O(active-discounts) stamp cost is paid on hits and misses alike.
- `propagation` `StoreApp/domains/catalog/services/services.py:67` (running_discount_stamp) — Runs a Discount query over all active in-window rows plus a Python sorted() loop calling campaign.is_running(moment) per row — O(D) per public request even on cache hits (:82-90); running_discounts_of (:40-66) repeats the same scan with prefetch on misses.
- `sink` `StoreApp/domains/stores/views/viewset.py:1144` (StoreViewSet._public_catalog_data) — On cache miss: effective_pricing_of(product, discounts) runs for EVERY active product and winning_discount_of iterates all running discounts per product -> O(PxD) (services.py:127-133); ALL categories/brands serialized unfiltered (:1199-1200, :1238-1239) and all running discounts serialized as promotions (:1236, :1240).

**Conditions**:
- _authentication_level_ — Authenticated store owner (IsAuthenticated) with an active subscription: has_public_link suffices for categories/brands (all paid plans); has_discounts requires premium or ecommerce.
- _data_state_ — Store must be published and publicly reachable: is_published, !is_blocked, has_public_link, show_catalog != False and 'catalog' in effective site_templates, with anonymous traffic (or attacker-generated requests) hitting the public catalog.
- _system_configuration_ — Plan benefits seeded per dict_plan_benefits; 'user' throttle = 1000/day caps create throughput, 'public_read' = 1000/hour/IP caps read amplification; Redis cache TTL 120s amortizes the miss path (throttles fail-open if Redis is down, worsening amplification).

**Reproduction** (A paying store owner (cheapest plan suffices for categories/brands; premium/ecommerce for discounts) seeking to inflate the per-request CPU/DB cost and payload size of their store's anonymous public catalog endpoint, degrading shared worker/cache capacity and their own visitors' experience.):
- Authenticate as the store owner and loop create requests with unique names; per-(store,name) uniqueness permits unlimited distinct rows and no count check exists on any path.
- For discounts keep is_active=true, starts_at<=now and ends_at=null so every row enters running_discount_stamp/running_discounts_of on every request.
- Let public traffic (or self-issued anonymous requests with distinct filter combinations, each producing a unique _params_fingerprint cache key) hit the catalog endpoint.
- Observe per-request Discount scans with campaign.is_running() per row, O(products x discounts) pricing on each miss, and response payload growth proportional to taxonomy/discount row counts.
- **Observed**: Source-verified: every catalog request executes running_discount_stamp (one Discount query + Python loop over all in-window discounts calling campaign.is_running per row) before cache lookup; every cache miss serializes ALL categories/brands including empty ones and ALL running discounts as promotions, and runs effective_pricing_of per product iterating every running discount (O(PxD)). No count validation exists in Category/Brand/Discount create paths, serializers, or models — unlike max_products/SERVICES_MAX/image caps enforced under select_for_update.

**Impact**: Amplifies shared-infrastructure cost (per-request Discount scan, O(PxD) pricing CPU on misses, unbounded payload size) for that store's public catalog and for shared workers/cache. Bounded by PUBLIC_CACHE_TTL=120s, 'public_read' 1000/hour/IP throttle, plan-capped products on lower tiers, and the owner-create throttle. No cross-tenant data exposure, integrity loss, or availability kill demonstrated from source.

**Priority rationale**: likelihood=medium, impact=low.

**Smallest fix**: Bound every owner-writable collection that feeds shared public payloads. Add count quotas for categories, brands and discounts — new plan benefits (e.g., max_categories/max_brands/max_discounts in dict_benefits + dict_plan_benefits) or fixed ceilings like SERVICES_MAX — enforced in create under select_for_update on the store row, mirroring can_add_product/can_add_service (e.g., a can_add_taxonomy/can_add_discount helper checked inside transaction.atomic in each viewset's create). Independently of quotas: exclude categories/brands with products_count=0 from the public payload (or cap the serialized lists), cap the promotions list length, and consider folding the discount stamp into a cached payload version instead of recomputing per request. Optionally dedupe/throttle notify_store_discount on mass discount creation.

### LOW — Chat payload leaks full staff directory (ids, names/usernames, online presence) to every paying customer despite per-message anonymity

**Fingerprint**: `chat.staff-roster-leaks-all-staff-identities` · **Confidence**: medium

**Location**: AdminApp/domains/chat/views/viewset.py, AdminApp/domains/chat/services/services.py, AdminApp/domains/chat/serializers/serializers.py

**Principal**: Attacker holds an authenticated platform account (JWT Bearer) with a paid non-trial subscription granting chat access; trial and no-plan accounts get 403 (list) or 204 (heartbeat). 

**Description**: The support chat deliberately anonymizes staff in messages — ChatMessageSerializer.get_sender_name returns the constant 'Soporte DAVENT' for from_staff messages (serializers.py:31-37) and the serializer module docstring promises 'nunca emails ni datos de cuenta'. However, SupportChatViewSet.list() and heartbeat() embed staff_roster() in every customer response (viewset.py:105 and viewset.py:198). staff_roster() (services.py:134-147) iterates User.objects.filter(is_staff=True, is_active=True) — i.e., ALL staff and superuser accounts, not just support agents — and returns {id (DB pk), name (get_full_name() or username — a login identifier), online} for each. Any authenticated user with a paid non-trial plan (chat_enabled: suscription.grants_access() and not plan.is_trial, services.py:29-39) can enumerate the complete staff account directory, real names or usernames, primary keys, and real-time per-person presence. The frontend does consume the roster (DashboardView.vue:3379/3426 -> chatStaff -> chatContacts rendered as named team members with online status at lines 6452-6464), so names/online are an intended UI feature — but the backend scope (every is_staff account incl. superusers, username fallback, numeric ids) exceeds what a support-team display needs and contradicts the per-message anonymity boundary.

**Root cause**: staff_roster() (services.py:140) scopes only by is_staff+is_active with no support-role filter, and both customer-facing responses (viewset.py:105 'staff': staff_roster(), viewset.py:198) include it unconditionally on every list/heartbeat poll.

**Trace**:
- `entrypoint` `AdminApp/domains/chat/views/viewset.py:105` (SupportChatViewSet.list (customer branch)) — Customer GET /api/chat/ response includes 'staff': staff_roster() alongside messages/unread/staff_online.
- `propagation` `AdminApp/domains/chat/views/viewset.py:198` (SupportChatViewSet.heartbeat (customer branch)) — Customer POST /api/chat/heartbeat/ response includes 'staff': staff_roster() on every ~45s presence poll.
- `propagation` `AdminApp/domains/chat/services/services.py:140` (staff_roster query) — User.objects.filter(is_staff=True, is_active=True) — all staff incl. superusers; presence set from ChatPresence (user__is_staff).
- `propagation` `AdminApp/domains/chat/services/services.py:141` (staff_roster payload fields) — Each entry returns {'id': u.id, 'name': u.get_full_name().strip() or u.username, 'online': u.id in online} — DB pk, full name or login username, live presence.
- `sink` `AdminApp/domains/chat/serializers/serializers.py:34` (ChatMessageSerializer.get_sender_name) — from_staff messages are hardcoded to 'Soporte DAVENT' — per-message anonymity enforced while the roster bypasses it.

**Conditions**:
- _authentication_level_ — Attacker holds an authenticated platform account (JWT Bearer) with a paid non-trial subscription granting chat access; trial and no-plan accounts get 403 (list) or 204 (heartbeat).
- _authorization_role_ — Non-staff customer principal — staff callers receive the staff bandeja branch instead and do not get this payload.
- _system_configuration_ — Read-only enumeration; no writes required. ChatPresence rows determine the 'online' flags.

**Reproduction** (Paying customer (any paid non-trial plan) calling the support-chat endpoints with their own Bearer token.):
- Obtain a paid non-trial plan on a platform account.
- GET /api/chat/ (or POST /api/chat/heartbeat/) with the Bearer token.
- Read response.staff: a list of {id, name, online} for every active is_staff user — names resolve to full name or login username, ids are DB primary keys, online reflects live ChatPresence.
- **Observed**: Source-derived: response.staff enumerates every active staff/superuser account with id, display name (full name or username) and real-time online flag; repeated heartbeat polls keep presence fresh. No email is exposed, but usernames (login identifiers) and the complete admin/staff directory are.

**Impact**: Discloses staff names/usernames/DB ids/online presence to customers — aids targeted phishing and credential attacks against admin accounts — but exposes no credentials, emails, or tenant data, and platform login is separately rate-limited.

**Priority rationale**: likelihood=medium, impact=low.

**Smallest fix**: Scope the roster to support-facing staff only (dedicated flag/group or is_staff AND a support permission), return a display-safe label instead of falling back to username, and drop the numeric id if the UI does not need it — the frontend uses id only as a local key, so a synthetic key or omission suffices. If showing the team is intended product behavior, document it and explicitly exclude superusers/non-support staff and presence granularity.

### LOW — Django 5.2 GZipMiddleware buffers the entire SSE stream — events and heartbeats only reach the client at ~50s stream close

**Fingerprint**: `customers-sse:gzip-buffering` · **Confidence**: medium

**Location**: DaventProject/settings.py, StoreApp/domains/customers/views/notification_views.py, requirements.txt

**Principal**: GZipMiddleware enabled (default in this repo) and client sends Accept-Encoding:gzip — true for every browser EventSource; non-gzip clients (e.g. curl without --compressed) bypass compression entirely and see correct streaming. 

**Description**: GZipMiddleware is enabled (DaventProject/settings.py:241) and the pinned runtime is Django==5.2.18 (requirements.txt:17), installed verbatim into both deploy images (docker/api/Dockerfile stages builder/runtime; render.yaml uses the same dockerfilePath). Verified against the Django stable/5.2.x release-branch source (the branch 5.2.18 is tagged from; the per-chunk flush fix, PR #20401 merged 2026-03-09, is absent from stable/5.2.x HEAD and therefore from every 5.2.x release): GZipMiddleware.process_response wraps response.streaming_content in compress_sequence whenever the request's Accept-Encoding contains 'gzip' and no Content-Encoding is set — with no content-type exemption, so text/event-stream is compressed. compress_sequence writes each SSE frame via zfile.write() but never calls zfile.flush(); zlib withholds output until its pending buffer reaches ~16-17KB (documented in the Django commit that removed the flush: 'the buffer is being flushed every 17k or so') or until the GzipFile context closes. The stream's frames are tens-to-hundreds of bytes (': conectado', ': ping' every 15s, small JSON events), so for any realistic notification volume NOTHING is emitted — not even response headers, since WSGI sends headers with the first body bytes — until either ~17KB accumulates or the generator ends at STREAM_MAX_SECONDS=50 and the gzip trailer flushes everything at once. Consequence: browsers (which always send Accept-Encoding: gzip on EventSource) receive the whole 50s of events/heartbeats in a single burst at reconnect time; the 'unread'/'notification' events effectively degrade to ~50s polling granularity and the 15s heartbeat cannot serve its liveness purpose. The view's X-Accel-Buffering:no only affects nginx proxy buffering and does not prevent Django-side gzip; nginx gzip_types excludes text/event-stream so nginx neither re-compresses nor helps; Caddy has no encode directive and passes the upstream Content-Encoding:gzip through.

**Root cause**: django.middleware.gzip.GZipMiddleware unconditionally gzip-compresses sync streaming responses via django.utils.text.compress_sequence, and in Django 5.2.x compress_sequence performs zfile.write() per chunk without zfile.flush(), so zlib buffers the stream until ~17KB pending or close — defeating the real-time delivery contract of text/event-stream.

**Trace**:
- `entrypoint` `DaventProject/settings.py:241` (MIDDLEWARE) — 'django.middleware.gzip.GZipMiddleware' enabled for all responses including the SSE stream
- `propagation` `StoreApp/domains/customers/views/notification_views.py:178` (CustomerNotificationStreamView.get) — StreamingHttpResponse(self._events(...), content_type='text/event-stream'); sets Cache-Control:no-cache and X-Accel-Buffering:no (nginx-only hint) but NO Content-Encoding — so GZipMiddleware will compress it for gzip-accepting clients
- `propagation` `requirements.txt:17` (GZipMiddleware.process_response (Django 5.2.x stable branch) [lib: django/middleware/gzip.py]) — for response.streaming (sync): response.streaming_content = compress_sequence(response.streaming_content, ...) whenever re_accepts_gzip matches HTTP_ACCEPT_ENCODING and no Content-Encoding header exists — no content-type check exempts text/event-stream
- `sink` `requirements.txt:17` (compress_sequence (Django 5.2.x stable branch) [lib: django/utils/text.py]) — for item in sequence: zfile.write(item); data = buf.read(); yield if data — NO zfile.flush() per chunk; zlib emits only at ~16-17KB pending or at GzipFile.__exit__ (stream close at ~50s) → entire SSE session buffered into one burst

**Conditions**:
- _system_configuration_ — GZipMiddleware enabled (default in this repo) and client sends Accept-Encoding:gzip — true for every browser EventSource; non-gzip clients (e.g. curl without --compressed) bypass compression entirely and see correct streaming.
- _data_state_ — Typical notification volume keeps each 50s stream well under ~17KB of SSE frames, so nothing flushes before close; a burst >~17KB (e.g. large catch-up payloads) could emit mid-stream but events still arrive late and batched.
- _timing_dependency_ — Buffered upstream silence lasts until ~50s stream end; nginx proxy_read_timeout is 60s so the response still completes — headroom is only ~10s.

**Reproduction** (Not attacker-driven — a deterministic defect affecting every legitimate SSE client.):
- 1. Open the stream as the SPA does (EventSource → ticket → GET stream).
- 2. Trigger or wait for a customer notification; observe that no 'notification'/'unread' event arrives in real time — all buffered frames plus the final 'bye' are delivered in one burst when the generator closes at ~50s.
- 3. Confirm response headers (Content-Encoding:gzip) arrive only with that first burst, since WSGI emits headers with the first non-empty body chunk.
- **Observed**: Source-traced: middleware chain, pinned-version library code on the release branch, and the absence of any Content-Encoding/content-type bypass prove the buffering path; the ~17KB zlib threshold is documented by Django developers in the fix commit. Not observed on a live instance (source-only review; no venv present in the workspace to byte-inspect the installed package — the stable/5.2.x branch source stands in for the 5.2.18 wheel).

**Impact**: Customer notifications degrade from push to ~50s batched delivery and heartbeats cannot serve liveness; a security-adjacent timeliness defect, not a trust-boundary crossing — data still arrives, just late, and the 50s<60s timeout margins keep streams alive.

**Priority rationale**: likelihood=high, impact=low.

**Smallest fix**: Exempt text/event-stream from gzip compression: replace 'django.middleware.gzip.GZipMiddleware' with a subclass that returns the response untouched when Content-Type starts with 'text/event-stream' (the Django ticket itself recommends this), or set an explicit no-op Content-Encoding the middleware respects. Alternatively/Additionally upgrade Django once the compress_sequence flush fix is backported to the deployed 5.2.x line (fix is on main; verify release notes). The heartbeat/liveness design then works as intended and events arrive per chunk.

### LOW — Stream ticket is a replayable, session-unbound bearer credential transmitted in the URL query (120s window)

**Fingerprint**: `customers-sse:ticket-replay-no-epoch` · **Confidence**: high

**Location**: StoreApp/domains/customers/urls/urls.py, StoreApp/domains/customers/views/notification_views.py, frontend/src/api/customerNotifications.api.js

**Principal**: Stream endpoint is AllowAny — whoever presents a valid unexpired ticket gets the stream; no DAVENT/customer session needed at connect time. 

**Description**: The SSE credential is signing.dumps({'c': customer_pk, 's': slug}, salt='customer-notifications-stream') verified with max_age=TICKET_TTL=120. Verified sub-claims: (1) REPLAYABLE — the payload carries no jti/nonce and nothing is consumed at verify time, so one ticket authorizes unlimited concurrent stream connections for its full 120s TTL (this is also the multiplier that makes customers-sse:worker-exhaustion cheap). (2) NO EPOCH BINDING — the signed material contains only customer pk and slug; the customer session-epoch mechanism that exists for JWTs (customer.tokens_valid_after vs token iat, authentication.py:28-41) is not consulted, so password-reset revocation does not kill outstanding tickets and deactivation is only checked once at connect. (3) is_active NOT RE-CHECKED — Customer.objects.filter(pk, is_active=True) runs once in get() (line 167); the _events loop (lines 187-215) iterates customer_id forever, so a deactivated/deleted customer keeps receiving their own notification stream until the 50s deadline. (4) QUERY-STRING CREDENTIAL — the frontend builds the EventSource URL as ?ticket=<signed>&store=<slug> (customerNotifications.api.js:32-35); the ticket therefore lands in nginx/gunicorn access logs (gunicorn accesslog='-', nginx default combined format) and any proxy/log pipeline. Correction to the hunter's framing: EventSource does not create browser-history entries, so exposure is via server/proxy access logs and any client that records request URLs — still a bearer credential in a URL (CWE-598). Impact is bounded: read-only access to that customer's own notifications for ≤120s per captured ticket, plus a ≤50s post-deactivation tail; the legitimate client already re-mints a ticket per connection (useCustomerNotifications.js:48), so single-use tickets would not break it.

**Root cause**: The stream ticket was designed as a minimal signed tuple {customer, slug}+TTL. It omits a single-use jti, omits binding to the session epoch (tokens_valid_after) used by the JWT path, performs the liveness check only at connect time, and is transported in the URL query string because EventSource cannot set Authorization headers.

**Trace**:
- `entrypoint` `StoreApp/domains/customers/urls/urls.py:58` (urlpatterns) — POST /api/customer/notifications/stream-ticket/ (CustomerJWTAuthentication + IsCustomer + CustomerApiThrottle 'user' 1000/day) mints the ticket
- `propagation` `StoreApp/domains/customers/views/notification_views.py:125` (CustomerNotificationStreamTicketView.post) — ticket = signing.dumps({'c': request.customer.pk, 's': slug}, salt=STREAM_SALT) — payload contains ONLY pk+slug: no jti, no iat floor, no tokens_valid_after, no session id
- `propagation` `StoreApp/domains/customers/views/notification_views.py:162` (CustomerNotificationStreamView.get) — signing.loads(ticket, salt, max_age=TICKET_TTL=120) — TimestampSigner age check only; successful loads are NOT consumed or recorded, so the same ticket re-authorizes unlimited connections until expiry
- `propagation` `StoreApp/domains/customers/views/notification_views.py:167` (CustomerNotificationStreamView.get) — Customer.objects.filter(pk=data['c'], is_active=True).first() — the ONLY liveness check; happens once per connection
- `propagation` `StoreApp/domains/customers/views/notification_views.py:187` (CustomerNotificationStreamView._events) — _events(customer_id, store_id, last_id) loops on the monotonic deadline with zero re-fetch of the Customer — is_active/deactivation and session revocation are never re-evaluated; stream survives up to STREAM_MAX_SECONDS=50s
- `sink` `frontend/src/api/customerNotifications.api.js:33` (notificationsStreamUrl) — new URLSearchParams({ticket}) → GET .../stream/?ticket=<signed blob>&store=<slug> — credential in the query string → captured by nginx/gunicorn access logs and any upstream proxy logs

**Conditions**:
- _authentication_level_ — Stream endpoint is AllowAny — whoever presents a valid unexpired ticket gets the stream; no DAVENT/customer session needed at connect time.
- _data_state_ — Ticket must be captured (access/proxy logs, tooling that records URLs, shared debugging context) or simply reused by its holder; customer must have been is_active at connect time.
- _timing_dependency_ — Replay/eavesdrop window ≤120s per ticket; deactivated-customer stream tail ≤50s (STREAM_MAX_SECONDS).
- _system_configuration_ — N/A beyond defaults — applies identically on compose/VPS and Render deploys.

**Reproduction** (Someone who obtains a stream ticket URL — e.g. from nginx/gunicorn access logs, log aggregation, or a client-side record of request URLs — needs no account at all; alternatively the ticket holder abuses replay for concurrency (see worker-exhaustion finding).):
- 1. Obtain a ticket+slug pair (e.g. from an access log line for /api/customer/notifications/stream/?ticket=...).
- 2. Issue the GET directly (curl/browser) — signing.loads accepts it until 120s elapse; the customer row is only required to be is_active at that moment.
- 3. For the epoch gap: after the customer resets their password (tokens_valid_after seals all JWTs), any ticket minted beforehand remains usable for the rest of its 120s TTL, and any customer deactivated mid-stream keeps receiving events until the 50s deadline.
- **Observed**: Source-traced: payload has no jti and verify consumes nothing (unlimited replays per ticket); no tokens_valid_after/session binding anywhere in mint or verify; is_active evaluated exactly once per connection and never inside _events; ticket confirmed in the URL query by both the view (request.query_params) and the frontend URL builder. No runtime test performed.

**Impact**: A captured ticket yields read-only access to that customer's own notification stream for ≤120s; deactivation leaves a ≤50s tail. No cross-customer or write access; notifications are low-sensitivity operational data (order/status updates) also delivered by email.

**Priority rationale**: likelihood=low, impact=low.

**Smallest fix**: Make the ticket single-use and epoch-bound, and re-validate liveness inside the stream: embed a random jti recorded in cache (cache.add/delete at connect — frontend already re-mints per connection so single-use is free), sign the customer's tokens_valid_after (or a session id) into the payload and compare at connect, re-check customer.is_active inside _events every ~15s alongside the ping, and consider shortening TICKET_TTL to ~30-60s. Optionally move the credential out of the query string (e.g. POST-minted one-time code → short-lived cookie) or ensure access logs for this route redact the query.

### LOW — Feed customer writes (comment/like/vote) are completely unthrottled — FeedWriteThrottle is an AnonRateThrottle that skips authenticated customers

**Fingerprint**: `feed-customer-writes-unthrottled-anon-throttle` · **Confidence**: high

**Location**: StoreApp/domains/feed/urls/urls.py, StoreApp/domains/feed/views/views.py, StoreApp/domains/customers/authentication.py, StoreApp/domains/customers/models/models.py (+1)

**Principal**: Attacker holds any customer_access JWT — free self-service registration at /api/customer-auth/register/ (10/hour per IP); is_active=True by default and the access token is issued immediately without email verification. 

**Description**: All three customer write endpoints of the store feed — POST /api/stores/public/<slug>/feed/<pk>/comments/, .../like/, .../vote/ — declare FeedWriteThrottle (scope 'store_review', configured 10/hour in settings, intended as antispam). FeedWriteThrottle extends ResilientAnonRateThrottle -> DRF AnonRateThrottle.get_cache_key returns None whenever request.user.is_authenticated is truthy (venv/Lib/site-packages/rest_framework/throttling.py:173-175). CustomerJWTAuthentication returns the Customer object as request.user (authentication.py:72-73) and Customer.is_authenticated is a property returning True (models.py:117-119), so for every request that can reach the handlers (all gated by IsCustomer) the throttle key is None and SimpleRateThrottle.allow_request returns True unconditionally (throttling.py:119-121). The throttle is dead code: one self-registered customer account (POST /api/customer-auth/register/, AllowAny, is_active=True default, access JWT issued immediately without email verification) can post unlimited 600-char comments on any published store feed, toggle likes, and cast poll votes. Sibling code proves intent: StoreReviewThrottle.get_cache_key explicitly buckets POSTs by 'review-customer-<pk>' (stores/views/viewset.py:391-401) and support uses _CustomerScopedThrottle keyed 'c<pk>' (support/views/customer.py:57-64); the customer-auth module's own comment states 'NO se usa AnonRateThrottle porque saltaría la cuota a un comprador autenticado' (customers/views/auth_views.py:164-168). Amplifier: PublicFeedCommentsView.get returns every non-hidden comment with no LIMIT/pagination (feed/views/views.py:214-215), so spamming a post inflates every subsequent public GET of that post. FeedComment has no unique constraint — unlimited comments per account per post; likes/votes are unique per (post, customer) but multi-account inflation is feasible since registration is self-service.

**Root cause**: FeedWriteThrottle subclasses ResilientAnonRateThrottle (DRF AnonRateThrottle) instead of a customer-scoped throttle; AnonRateThrottle.get_cache_key returns None for authenticated request.user, and CustomerJWTAuthentication sets request.user to a Customer whose is_authenticated property returns True — so the throttle can never deny any request that passes IsCustomer.

**Trace**:
- `entrypoint` `StoreApp/domains/feed/urls/urls.py:36` (feed URLconf) — PublicFeedCommentsView mounted at stores/public/<slug>/feed/<pk>/comments/ (POST gated to IsCustomer via get_permissions); like/vote routes at lines 38-39.
- `propagation` `StoreApp/domains/feed/views/views.py:55` (FeedWriteThrottle) — class FeedWriteThrottle(ResilientAnonRateThrottle) with scope='store_review' (line 58) — no get_cache_key override; inherits AnonRateThrottle behavior.
- `propagation` `StoreApp/domains/customers/authentication.py:73` (CustomerJWTAuthentication.authenticate) — Returns (customer, token) so DRF sets request.user = Customer; also sets request.customer used by IsCustomer.
- `propagation` `StoreApp/domains/customers/models/models.py:118` (Customer.is_authenticated) — Property returns True unconditionally (lines 117-119) — Customer counts as authenticated for DRF throttles.
- `propagation` `venv/Lib/site-packages/rest_framework/throttling.py:175` (AnonRateThrottle.get_cache_key / SimpleRateThrottle.allow_request) — if request.user and request.user.is_authenticated: return None (line 174-175); allow_request returns True when key is None (lines 119-121).
- `propagation` `StoreApp/domains/feed/views/views.py:220` (PublicFeedCommentsView.post) — FeedComment.objects.create(post=post, customer=request.customer, body=...) — no rate limit, no dedupe, no per-store quota; same unthrottled pattern in PublicFeedLikeView.post (line 241) and PublicFeedVoteView.post (line 259).
- `sink` `StoreApp/domains/feed/views/views.py:214` (PublicFeedCommentsView.get) — comments = post.comments.filter(is_hidden=False).select_related('customer') returned in full at line 215 — no [:N] cap, no pagination (contrast owner view line 166 which caps at 500).

**Conditions**:
- _authentication_level_ — Attacker holds any customer_access JWT — free self-service registration at /api/customer-auth/register/ (10/hour per IP); is_active=True by default and the access token is issued immediately without email verification.
- _data_state_ — Target store must have the feed benefit enabled (has_feed / feed_enabled) and a published feed post (is_published=True via _public_post).
- _system_configuration_ — Cache (Redis) healthy — irrelevant for the bug itself since the throttle never engages; relevant only to whether the intended 10/hour would have applied.

**Reproduction** (Any internet user who registers a free buyer account on a DAVENT store and wants to spam or skew a store's public feed (/novedades) — comment spam visible to all visitors, like/poll-vote inflation, or unbounded growth of the public comments payload.):
- Register a customer account and capture the access JWT from the response body.
- Pick any published store with feed enabled; GET /api/stores/public/<slug>/feed/ to enumerate post ids.
- POST comments in a loop — every request returns 201; no 429 ever occurs because FeedWriteThrottle.get_cache_key returns None for the authenticated Customer.
- Repeat like/vote across many posts and, for count inflation, across many freshly registered accounts (unique (post,customer) constraints do not help comments, which have no constraint at all).
- GET the comments endpoint repeatedly to observe the unbounded payload grow with each spammed comment.
- **Observed**: Source-derived (read-only audit): FeedWriteThrottle.get_cache_key resolves to AnonRateThrottle.get_cache_key -> request.user.is_authenticated is True (Customer property) -> returns None -> SimpleRateThrottle.allow_request returns True for 100% of requests that pass IsCustomer. The 10/hour 'store_review' scope is dead code on all three write endpoints; comment creation has no DB-level dedupe, so a single account can create unlimited FeedComment rows.

**Impact**: Abuse-class only: public comment spam (owner-moderatable one-by-one via is_hidden/delete), poll/like skew requiring multiple accounts, unbounded comment-list payloads amplifying read cost, and DB row growth. No confidentiality or authorization boundary crossed; comments/likes/votes trigger no emails or notifications.

**Priority rationale**: likelihood=high, impact=low.

**Smallest fix**: Replace FeedWriteThrottle with a customer-scoped throttle mirroring StoreReviewThrottle/_CustomerScopedThrottle: subclass SimpleRateThrottle (or reuse DaventProject.throttling._ResilientThrottleMixin) and key the cache by f'c{request.customer.pk}' (fallback IP for anonymous) with scope 'store_review'/'10/hour'. Bound PublicFeedCommentsView.get (e.g. comments.filter(is_hidden=False).select_related('customer')[:200] or paginate), consider a per-store inbound comment quota analogous to SUPPORT_STORE_MSGS_PER_HOUR, and consider requiring email_verified for customer_access issuance if abuse continues.

### LOW — Mercado Pago checkout redirect not host-validated in platform billing flows (LOW)

**Fingerprint**: `frontend:mp-checkout-redirect-not-host-validated` · **Confidence**: high

**Location**: frontend/src/api/payments.api.js, frontend/src/stores/payments.store.js, AdminApp/domains/payments/views/viewset.py, frontend/src/views/DashboardView.vue

**Principal**: The Mercado Pago API (or the payments backend viewset) must return a non-MP-host URL in checkout_url/init_point/sandbox_init_point — i.e., upstream compromise, provider bug, or backend compromise. Legitimate values are always MP-hosted, including sandbox_init_point under TEST- credentials. 

**Description**: The codebase documents and implements a client-side revalidation control for Mercado Pago checkout redirects: PaymentInstructions.vue:36-47 defines isMpCheckoutUrl() (https: + MP_HOST_RE over mercadopago/mercadolibre/mpago.la hosts) explicitly as 'defensa en profundidad ante un upstream comprometido', and applies it before window.location.assign(url) at line 56 for ORDER payments. The same control is absent from the platform billing (subscription/plan) flows: DashboardView.vue planAction() assigns renewUrl = data?.checkout_url || data?.init_point || data?.sandbox_init_point to checkoutTab.location.href at line 3816 (auto-renew downgrade path), assigns the URL returned by payments.checkout() to checkoutTab.location.href at line 3828 (plan purchase), and activateAutoRenew() does the same at line 3873. payments.store.js checkout() (line 82) returns the raw checkout_url||init_point||sandbox_init_point chain and subscribeAuto() (line 105) returns the raw response; payments.api.js createCheckout/createSubscription (lines 33-44) return API data unmodified; the axios response interceptor in http.js (lines 267-314) only handles 401 refresh/session logic and performs no URL sanitization; no router guard is involved because navigation happens via window.open('about:blank') + tab.location.href, and the native.js shim (lines 70-78) forwards the same unvalidated URL to Capacitor Browser.open. Backend verification (AdminApp/domains/payments/views/viewset.py:301-306 and :373-375) shows checkout_url/init_point/sandbox_init_point are passed verbatim from the Mercado Pago API preference/preapproval response with no host check, so the MP upstream is the sole trust boundary. Legitimate values are always MP-hosted (init_point/sandbox_init_point), so the allowlist would not break sandbox (TEST-) flows. Impact: if the MP API response (or the backend viewset) ever yields a non-MP URL — upstream compromise, provider bug, or backend compromise — the dashboard opens a new tab to an attacker-controlled page that can mimic the MP checkout and phish payment card details from authenticated store owners. Requires upstream/backend compromise; no direct user-input path exists.

**Root cause**: The MP-host allowlist validation (isMpCheckoutUrl) exists only inside the ecommerce PaymentInstructions component; the three platform billing redirect sites in DashboardView.vue assign checkout URLs to location.href without revalidation, and neither payments.api.js, payments.store.js, http.js interceptors, nor the backend viewset adds a compensating host check.

**Trace**:
- `entrypoint` `frontend/src/api/payments.api.js:34` (paymentsApi.createCheckout / createSubscription) — POST /payments/checkout/ and /payments/subscription/ return response data unmodified (lines 33-44); the API layer performs no URL validation.
- `propagation` `frontend/src/stores/payments.store.js:82` (usePaymentsStore.checkout / subscribeAuto) — checkout() returns data?.checkout_url || data?.init_point || data?.sandbox_init_point raw (line 82); subscribeAuto() returns the raw response object (line 105). No host validation.
- `propagation` `AdminApp/domains/payments/views/viewset.py:301` (PaymentViewSet.checkout / subscription) — Backend passes preference.get('init_point')/('sandbox_init_point') and preapproval.get(...) verbatim from the Mercado Pago API into checkout_url/init_point/sandbox_init_point (lines 301-306, 373-375) with no host check.
- `propagation` `frontend/src/views/DashboardView.vue:3816` (planAction() auto-renew downgrade path) — renewUrl = data?.checkout_url || data?.init_point || data?.sandbox_init_point (line 3810) assigned to checkoutTab.location.href at line 3816 without host validation.
- `propagation` `frontend/src/views/DashboardView.vue:3828` (planAction() plan purchase path) — url = await payments.checkout(...) (line 3822) assigned to checkoutTab.location.href at line 3828 without host validation.
- `sink` `frontend/src/views/DashboardView.vue:3873` (activateAutoRenew()) — url = data?.checkout_url || data?.init_point || data?.sandbox_init_point (line 3867) assigned to tab.location.href at line 3873 without host validation; native.js shim forwards it to Capacitor Browser.open.

**Conditions**:
- _third_party_dependency_ — The Mercado Pago API (or the payments backend viewset) must return a non-MP-host URL in checkout_url/init_point/sandbox_init_point — i.e., upstream compromise, provider bug, or backend compromise. Legitimate values are always MP-hosted, including sandbox_init_point under TEST- credentials.
- _authentication_level_ — Victim must be an authenticated store owner (platform JWT) who initiates a plan purchase or auto-renew activation from the dashboard billing section.
- _user_interaction_ — The owner must click the plan/auto-renew action that triggers the checkout redirect; the malicious page then loads in the opened tab.

**Reproduction** (An attacker who can influence the JSON returned by POST /api/payments/checkout/ or /api/payments/subscription/ — e.g., a compromised Mercado Pago API upstream, a MITM-free response injection at the backend, or a malicious/buggy backend deployment — supplies an arbitrary URL in place of the real init_point.):
- Source-only verification: trace paymentsApi.createCheckout/createSubscription -> payments.store checkout()/subscribeAuto() -> DashboardView planAction()/activateAutoRenew() and confirm no isMpCheckoutUrl()-equivalent check exists on any of the three location.href sinks.
- Confirm the contrast: PaymentInstructions.vue:39-56 applies the allowlist for order payments while the platform billing flows do not.
- Confirm no compensating layer: http.js interceptors (auth only), payments.api/store passthrough, native.js shim (no validation), backend viewset verbatim MP passthrough.
- Hypothetical runtime check (not executed, source-only constraint): stub paymentsApi.createCheckout to resolve {checkout_url:'https://attacker.example/x'} and invoke planAction — checkoutTab.location.href would navigate to the attacker origin.
- **Observed**: Source-derived: all three platform billing redirect sites assign the API-supplied URL to location.href with zero host validation; only the order-payment flow (PaymentInstructions.vue) enforces the MP allowlist. A non-MP URL in the response would navigate the owner's new tab to the attacker origin.

**Impact**: Successful exploitation redirects a paying user to an attacker page mimicking Mercado Pago checkout (credential/phishing exposure); bounded to platform billing flows that already trust the API response.

**Priority rationale**: likelihood=low, impact=low.

**Smallest fix**: Extract isMpCheckoutUrl()/MP_HOST_RE into a shared util (e.g., frontend/src/utils/mpCheckout.js) and apply it at all three DashboardView sinks before assigning location.href; on rejection, close the placeholder tab and surface payments.lastError (mirroring PaymentInstructions' 'Enlace de pago no válido.' behavior). Optionally add the same host check server-side in the payments viewset as a second layer.

### LOW — RequestIdMiddleware logs raw request.path — percent-encoded control chars forge log lines

**Fingerprint**: `infra:request-path-log-injection` · **Confidence**: medium

**Location**: DaventProject/middleware.py, DaventProject/logscrub.py

**Principal**: Any HTTP client can send percent-encoded CR/LF in the path; the WSGI server unquotes PATH_INFO and nginx proxy_pass passes the raw request URI, so the decoded control char reaches Django's request.path. 

**Description**: RequestIdMiddleware.__call__ ends every request with logger.info('request id=%s %s %s -> %s (%.0fms)', ..., request.method, request.path, ...). request.path is the URL-decoded PATH_INFO; a request like GET /%0AForged%20log%20entry HTTP/1.1 yields a newline inside the logged path, splitting one access-log record into attacker-shaped lines in stdout (json-file logs on the VPS, Render logs). The incoming X-Request-ID is charset-validated (middleware.py:120-123) but request.path is not, and the ScrubSecretsFilter redacts secret patterns only — it has no control-character stripping (logscrub.py:16-25). nginx proxy_pass forwards the raw request URI and gunicorn unquotes %XX into PATH_INFO per WSGI convention, so the encoded control char survives to Django.

**Root cause**: Untrusted, percent-decoded URL path interpolated into a single-line log record without sanitization/escaping.

**Trace**:
- `entrypoint` `DaventProject/middleware.py:125` (RequestIdMiddleware.__call__) — every request passes through; after the response it unconditionally emits the access log line
- `propagation` `DaventProject/middleware.py:142` (access log record) — logger.info('request id=%s %s %s -> %s (%.0fms)', request.request_id, request.method, request.path, ...) — decoded PATH_INFO interpolated unsanitized
- `sink` `DaventProject/logscrub.py:16` (ScrubSecretsFilter SECRET_PATTERNS) — patterns redact PEM/JWT/password/path/CUIT only; no control-character stripping, so a decoded %0A/%0D survives into the emitted line

**Conditions**:
- _network_routing_ — Any HTTP client can send percent-encoded CR/LF in the path; the WSGI server unquotes PATH_INFO and nginx proxy_pass passes the raw request URI, so the decoded control char reaches Django's request.path.

**Reproduction** (Unauthenticated remote HTTP client.):
- Send a request whose path contains percent-encoded control characters
- Observe the access log: the decoded newline splits the record and the attacker text appears as a separate log line
- **Observed**: Source-derived: decoded control characters reach logger.info -> multi-line/forged log records in stdout-collected logs (docker json-file, Render).

**Impact**: Log/audit integrity only — forged entries can confuse incident review or bury real attacks in noise; no code execution or data exposure.

**Priority rationale**: likelihood=medium, impact=low.

**Smallest fix**: Sanitize request.path (and method) in RequestIdMiddleware before logging — e.g. re.sub(r'[\x00-\x1f\x7f]', '?', path) — or log request.get_full_path() escaped; alternatively rely on gunicorn accesslog formatting which quotes fields.

### LOW — StoreSitemap lists stores that fail the public-access gate (missing has_public_link / active-subscription check)

**Fingerprint**: `infra:sitemap-benefit-gate` · **Confidence**: high

**Location**: DaventProject/urls.py, DaventProject/sitemaps.py, StoreApp/domains/stores/views/viewset.py, StoreApp/domains/stores/services/services.py

**Principal**: Any Store row with is_published=True, is_blocked=False whose owner lacks an active subscription granting has_public_link — the common case since registration no longer creates a subscription and Store.is_published defaults True. 

**Description**: /sitemap.xml is public and unauthenticated wherever Django serves it. StoreSitemap.items() filters Store.objects only by is_published=True, is_blocked=False, but the store-page endpoints that serve the public web — including public, public_catalog, pattern/document, contact, and reviews — require profile_has_benefit(store.user,has_public_link), resolved through plan_benefits_of -> suscription.grants_access() (active, in-vigencia subscription). The custom-domain resolver resolve_slug() itself checks only a verified StoreDomain plus is_published/is_blocked and omits that benefit gate, although the SPA then calls the gated publicStore endpoint and renders the store as unavailable. is_published defaults True and registration no longer creates a subscription, so any store whose owner never paid / let the plan lapse still appears in the sitemap with its slug and lastmod even though its public store data returns 404. The class docstring claims las mismas reglas del endpoint publico — it does not implement them. Caveat verified during validation: the VPS nginx vhost has no /sitemap.xml location (location / falls through to index.html), so on that tier the Django sitemap view is currently unreachable; the Render blueprint and any direct-Django serving expose the route.

**Root cause**: StoreSitemap.items() replicates only the two boolean flags and omits the subscription-benefit gate that the public viewset enforces per-request.

**Trace**:
- `entrypoint` `DaventProject/urls.py:73` (sitemap route registration) — path(sitemap.xml, sitemap, {sitemaps: {static: StaticSitemap(), stores: StoreSitemap()}}) — public Django view, no auth/throttle
- `propagation` `DaventProject/sitemaps.py:47` (StoreSitemap.items) — Store.objects.filter(is_published=True, is_blocked=False).only(slug,created_at) — no benefit/subscription filter
- `propagation` `StoreApp/domains/stores/views/viewset.py:638` (StoreViewSet.public) — The public store payload raises Http404 unless profile_has_benefit(store.user,has_public_link); public_catalog (:1012), _pattern_store (:793), _contact_store (:1257), and _review_store (:1306) apply the same gate
- `sink` `StoreApp/domains/stores/services/services.py:54` (plan_benefits_of) — benefits {} unless suscription.grants_access() — lapsed/no plan => has_public_link False => public store payload 404 while sitemap still lists slug/lastmod

**Conditions**:
- _data_state_ — Any Store row with is_published=True, is_blocked=False whose owner lacks an active subscription granting has_public_link — the common case since registration no longer creates a subscription and Store.is_published defaults True.
- _network_routing_ — Reachable wherever Django serves /sitemap.xml directly (Render blueprint, dev serverless). On the VPS nginx vhost it currently returns the SPA index.html instead, so exposure there depends on whether/when nginx gains a route for it.

**Reproduction** (Anonymous internet user or search-engine crawler.):
- On a deployment where Django serves /sitemap.xml (Render, or VPS if nginx routes it), fetch the sitemap
- Compare listed <loc> slugs against GET /api/stores/public/<slug>/ — lapsed/unpaid stores return 404 while remaining listed; the SPA route /<slug> still returns index.html and then renders its unavailable state after that API 404
- **Observed**: Source-derived: sitemap <url> entries expose slug and lastmod for stores whose public store payload endpoint returns 404; the SPA renders an unavailable page rather than a working store.

**Impact**: Unauthenticated enumeration of store slugs (business names) that are not publicly reachable, plus SEO indexing of dead stores; low-sensitivity identifiers only.

**Priority rationale**: likelihood=medium, impact=low.

**Smallest fix**: Filter StoreSitemap.items() through the same effective gate as the public store payload — restrict to stores whose owners suscription grants_access() and whose plan enables has_public_link (annotate/exists subquery or a shared queryset/helper used by both sitemap and public viewset). The related StoreDomain resolve_slug currently has the same omission (verified domain + published/not blocked only) and should be gated consistently if custom-domain resolution is meant to hide lapsed stores.

### LOW — Support-chat image attachments bypass all storage quota AND all rate limiting — unbounded R2 growth per paid user

**Fingerprint**: `uploads:chat-attachments-no-storage-quota` · **Confidence**: high

**Location**: AdminApp/domains/chat/views/viewset.py, venv/Lib/site-packages/rest_framework/throttling.py, AdminApp/domains/chat/services/attachments.py, StoreApp/domains/stores/services/storage.py (+2)

**Principal**: Attacker holds an authenticated platform User account (auth.User JWT) on any paid non-trial plan granting has_support_chat — the cheapest paid tier qualifies; staff bypass the gate but are trusted. 

**Description**: Every store-scoped image upload consumes the plan quota (Store.storage_used_bytes under select_for_update) or is a bounded staff/platform asset. Chat attachments are the sole exception: upload_chat_image validates (validate_image_file: ≤4MB, content-type allowlist, magic bytes), normalizes to WebP (imaging.normalize_image kind 'chat': ≤1600px, q78→floor 60), and PUTs to the DAVENT R2 bucket under key 'chat/<thread.id>/<uuid>.webp' — but never calls _check_quota/_consume_quota and ChatMessage stores only image_key, so no byte accounting exists anywhere. chat/ keys do not match _STORE_KEY_RE '^stores/(\d+)/' (storage.py:109) so they always land in the DAVENT bucket outside store.storage_used_bytes and outside BYO routing. Worse than the hunter claimed: the supposed 120/hour bound does not exist. ChatSendThrottle and ChatPollThrottle extend DRF ScopedRateThrottle, which reads the scope from view.throttle_scope (venv throttling.py:221) — and 'throttle_scope' appears nowhere in the repository, so self.scope becomes None and allow_request returns True unconditionally; the throttle classes' own scope attributes ('chat', 'chat_send') are shadowed and the settings rates (5000/h, 120/h) are never consulted. The view's throttle_classes=[ChatPollThrottle] also replaces DEFAULT_THROTTLE_CLASSES, so there is no fallback anon/user throttle either — /api/chat/send/ is effectively unthrottled. Remaining bounds: IsAuthenticated + chat_enabled gate (paid non-trial plan with has_support_chat, services.py:29-39), input normalization caps, and the annual purge_personal_data cron (default --days 365, only if scheduled — deployment fact). A user on the cheapest paid plan can therefore script unlimited ~350KB WebP objects into operator-owned R2, each also costing synchronous Pillow decode/encode CPU on gunicorn workers.

**Root cause**: upload_chat_image (AdminApp/domains/chat/services/attachments.py:27-45) performs validate_image_file + normalize_image + put_object with no quota check or accounting call; chat keys bypass _STORE_KEY_RE so they never touch store.storage_used_bytes; no per-user/per-thread attachment cap exists in send_message or the viewset; and the ScopedRateThrottle subclasses are dead code because no view defines throttle_scope.

**Trace**:
- `entrypoint` `AdminApp/domains/chat/views/viewset.py:127` (SupportChatViewSet.send) — POST /api/chat/send/ — IsAuthenticated + _gate(chat_enabled paid non-trial plan) + get_throttles appends ChatSendThrottle for action 'send' (lines 69-74). throttle_classes=[ChatPollThrottle] (line 67) replaces DEFAULT_THROTTLE_CLASSES.
- `propagation` `AdminApp/domains/chat/views/viewset.py:57` (ChatSendThrottle / ChatPollThrottle) — Both extend ScopedRateThrottle with class attrs scope='chat_send'/'chat' — but ScopedRateThrottle.allow_request sets self.scope=getattr(view,'throttle_scope',None) and returns True when falsy; no view in the repo defines throttle_scope (grep: zero matches), so both throttles always allow.
- `propagation` `venv/Lib/site-packages/rest_framework/throttling.py:221` (ScopedRateThrottle.allow_request) — self.scope = getattr(view, self.scope_attr, None); if not self.scope: return True — the throttle-class 'scope' attribute is ignored; scope must live on the view.
- `propagation` `AdminApp/domains/chat/services/attachments.py:27` (upload_chat_image) — validate_image_file -> imaging.normalize_image(upload,'chat') -> key=f'chat/{thread.id}/{uuid4().hex}.{ext}' -> storage.put_object(key, body, content_type) when storage_configured() else default_storage.save('private/'+key). Zero references to _check_quota/_consume_quota/storage_used_bytes.
- `propagation` `StoreApp/domains/stores/services/storage.py:289` (put_object / _byo_backend_for_key) — 'chat/...' does not match _STORE_KEY_RE '^stores/(\d+)/' (line 109) -> backend None -> unconditional DAVENT bucket PUT with CacheControl 'private, max-age=0' (lines 302-311); raises ValueError only on total failure.
- `propagation` `AdminApp/domains/chat/services/services.py:102` (send_message) — Persists ChatMessage.image_key (CharField, models.py:46) — object key only; no size/quota fields, no count cap, no FK-level storage accounting; message rows accumulate unbounded.
- `sink` `AdminApp/domains/users/management/commands/purge_personal_data.py:46` (purge_personal_data) — Only cleanup path: deletes ChatMessage rows + their attachments older than --days (default 365, line 37) — annual/batch cron, not a real-time bound; active threads' attachments persist for up to a year and scheduling is a deployment fact.

**Conditions**:
- _authentication_level_ — Attacker holds an authenticated platform User account (auth.User JWT) on any paid non-trial plan granting has_support_chat — the cheapest paid tier qualifies; staff bypass the gate but are trusted.
- _system_configuration_ — R2 (DAVENT bucket) configured via S3_API/R2_* env — the normal production path; without it objects go to MEDIA_ROOT/private (still unbounded disk growth, nginx-blocked).
- _environmental_dependency_ — purge_personal_data cron actually scheduled with some --days (default 365) — determines real retention bound; if unscheduled, attachments persist indefinitely. Unresolved deployment fact.
- _timing_dependency_ — Sustained automated uploads; with no effective rate limit the only practical bound is request throughput and per-file ~350KB-1MB output size.

**Reproduction** (A paying DAVENT customer (or anyone who buys the cheapest plan) wanting to inflate operator-owned R2 storage costs / bucket size, or to burn synchronous Pillow CPU on gunicorn workers, via the support-chat attachment path.):
- Purchase/activate any paid non-trial plan so chat_enabled(request.user) passes.
- Loop POST /api/chat/send/ with a valid image file (e.g., a 4MB PNG that normalizes to ~350KB-1MB WebP at 1600px).
- Observe 201 responses with no 429 — ChatSendThrottle is dead (no view.throttle_scope) and throttle_classes replaced the default user throttle.
- Each iteration creates one R2 object 'chat/<thread>/<uuid>.webp' plus one ChatMessage row; repeat indefinitely — nothing decrements or caps any counter.
- Confirm no quota surface exists: storage_payload/used_bytes belong to Store rows and are untouched by chat keys.
- **Observed**: Source-derived (read-only audit): each accepted upload produces a WebP object in the DAVENT R2 bucket with no increment/decrement of any quota counter and no rate-limit check (ScopedRateThrottle.allow_request returns True because no view defines throttle_scope). ChatMessage rows and R2 objects accumulate until the annual purge_personal_data run (if scheduled).

**Impact**: Operator-owned R2 storage spend and bucket growth plus synchronous Pillow CPU per request; per-file output ~350KB-1MB and input capped at 4MB/1600px. Slow-burn cost/resource issue with no cross-tenant data exposure; retention bounded to ~1 year if the purge cron runs.

**Priority rationale**: likelihood=medium, impact=low.

**Smallest fix**: Add a bounded budget for chat attachments: count attachment bytes in a per-user or per-plan quota (extend storage_used_bytes-style accounting or a dedicated usage table checked+consumed under lock in upload_chat_image), cap total attachments per thread/user, and shorten attachment retention. Separately fix the dead throttles: ScopedRateThrottle requires view.throttle_scope — either set throttle_scope='chat_send'/'chat' on the viewset actions or switch ChatPollThrottle/ChatSendThrottle to SimpleRateThrottle subclasses with get_cache_key keyed by user.pk (same fix pattern as feed/support). Audit NotificationPollThrottle (AdminApp/domains/notifications) for the identical bug.

### LOW — AnonRateThrottle subclasses skip authenticated users -> authenticated attacker gets unbounded password-reset emails (mail bombing / SMTP+queue abuse)

**Fingerprint**: `users-auth:anon-throttle-authenticated-bypass` · **Confidence**: high

**Location**: AdminApp/domains/users/views/auth_views.py, AdminApp/domains/users/services/services.py

**Principal**: Any registered platform user with a valid access token (open registration). 

**Description**: Every auth-endpoint throttle in AdminApp/domains/users/views/auth_views.py subclasses plain rest_framework AnonRateThrottle (LoginRateThrottle, RefreshRateThrottle, PasswordResetRateThrottle, PasswordResetConfirmRateThrottle, SocialAuthRateThrottle, PublicConfigRateThrottle). DRF's AnonRateThrottle.get_cache_key returns None when request.user.is_authenticated — and JWTAuthentication populates request.user on every request before check_throttles regardless of the view's AllowAny permission. Any registered user (open registration) therefore bypasses ALL these IP buckets entirely. The highest-impact instance is PasswordResetRequestView: each POST /api/password-reset/ for an existing email enqueues send_password_reset_email → a real SMTP send per request, with no per-user or per-email cap — unlimited mail-bombing of arbitrary victims through DAVENT's sender identity plus Celery/SMTP queue flooding that can delay transactional mail (invoices, verifications). The buyer-side code explicitly avoids AnonRateThrottle for exactly this reason ('NO se usa AnonRateThrottle porque saltaria la cuota a un comprador autenticado', customers auth_views.py:164-168) using a customer.pk-or-IP keyed throttle instead.

**Root cause**: Throttle classes chosen as AnonRateThrottle subclasses inherit the authenticated-skip semantics; no fallback per-user throttle exists on the AllowAny auth endpoints.

**Trace**:
- `entrypoint` `AdminApp/domains/users/views/auth_views.py:363` (PasswordResetRequestView) — AllowAny POST /api/password-reset/ with throttle_classes=[PasswordResetRateThrottle] — the only rate control on a side-effect endpoint
- `propagation` `AdminApp/domains/users/views/auth_views.py:126` (PasswordResetRateThrottle) — AnonRateThrottle subclass: DRF get_cache_key returns None for request.user.is_authenticated → allow_request always True for any valid-JWT caller (JWTAuthentication populates request.user before check_throttles)
- `sink` `AdminApp/domains/users/services/services.py:299` (RequestPasswordResetQuery) — existing email → send_password_reset_email.delay → SendPasswordResetEmailQuery sends one real SMTP message per accepted request, unbounded for authenticated callers

**Conditions**:
- _authentication_level_ — Any registered platform user with a valid access token (open registration).
- _data_state_ — Target email must belong to an existing account for the mail to be sent; the generic response lets the attacker spray arbitrary addresses blindly.
- _system_configuration_ — In production Celery is async: each accepted request enqueues a task that performs a real SMTP send; queue flooding can delay transactional mail (invoices, verifications).

**Reproduction** (Registered user (free signup) holding a Bearer access token.):
- 1. Register one account and obtain an access token via POST /api/token/.
- 2. Loop POST /api/password-reset/ with the victim's email and the Bearer token — no 429 regardless of volume because AnonRateThrottle.get_cache_key returns None for authenticated request.user.
- 3. Each request for an existing email enqueues send_password_reset_email → one real SMTP send to the victim; repeat unboundedly to mail-bomb the victim through DAVENT's sender identity and flood the Celery/SMTP queue.
- **Observed**: Source-traced: throttle key is None → allow_request returns True for every authenticated request; RequestPasswordResetQuery enqueues a mail task per existing-email request; no per-user or per-email cap exists anywhere in the chain.

**Impact**: Email abuse under DAVENT's sender identity (reputation/deliverability harm), victim mailbox flooding, and Celery/SMTP queue pressure that can delay transactional mail; no data exposure or account compromise.

**Priority rationale**: likelihood=high, impact=low.

**Smallest fix**: Replace the AnonRateThrottle subclasses on side-effect auth endpoints with a throttle keyed by user.pk when authenticated else IP (port the CustomerRateThrottle pattern); add a per-target-email cap for password-reset requests.

### LOW — Email-verification token is not bound to the email address: a stale link verifies a newly changed, never-proven email

**Fingerprint**: `users-auth:email-verify-token-not-email-bound` · **Confidence**: high

**Location**: AdminApp/domains/users/views/viewset_base.py, AdminApp/domains/users/services/services.py, AdminApp/domains/users/views/auth_views.py

**Principal**: Any registered user with a valid access token; registration is open and the email update is self-scoped. 

**Description**: EmailVerificationTokenGenerator._make_hash_value signs only user.pk + user.password + timestamp + profile.email_verified — user.email is absent. An authenticated user can PATCH /api/user/me/ to change user.email; UpdateUserQuery resets email_verified only when it was previously True, so a token issued while verified=False keeps identical hash inputs after the change. VerifyEmailQuery then sets email_verified=True for the new, never-proven address. StoreViewSet.create (viewset.py:463-469) treats that flag as the mailbox-control attestation for claiming a public store, while phone remains a separate requirement.

**Root cause**: _make_hash_value (services/services.py:202-209) omits user.email from the signed material, so the token proves only 'this user requested verification at time T', not 'this specific address was proven'.

**Trace**:
- `entrypoint` `AdminApp/domains/users/views/viewset_base.py:52` (UserBaseViewSet.update) — PATCH /api/user/me/ with UserUpdateSerializer {email} reaches the self-scoped update and calls UpdateUserQuery.
- `propagation` `AdminApp/domains/users/services/services.py:48` (UpdateUserQuery) — email change resets profile.email_verified only when it was True; when already False, no hash input changes.
- `propagation` `AdminApp/domains/users/services/services.py:202` (EmailVerificationTokenGenerator._make_hash_value) — signed material = f'{user.pk}{user.password}{timestamp}{verified}' — user.email absent.
- `propagation` `AdminApp/domains/users/views/auth_views.py:404` (VerifyEmailView.get) — GET /api/verify-email/?uid=&token= is AllowAny and calls VerifyEmailQuery.
- `sink` `AdminApp/domains/users/services/services.py:358` (VerifyEmailQuery) — after check_token succeeds, profile.email_verified=True is persisted for the account's current user.email.

**Conditions**:
- _authentication_level_ — Any registered user with a valid access token; registration is open and the email update is self-scoped.
- _data_state_ — Target email must be unregistered on auth.User (iexact uniqueness); profile.email_verified must be False when the token is generated and False after the email change — already False, or reset from True by UpdateUserQuery.
- _timing_dependency_ — Token use must occur within EmailVerificationTokenGenerator.timeout=86400 of token generation; receive the controlled-address verification mail before changing email because the queued sender uses the address current when it runs.

**Reproduction** (Authenticated platform user wanting to forge the verified-email attestation for an address they do not control.):
- 1. Register an account with an email the attacker controls; wait for the verification email at that controlled address and extract uid/token T while profile.email_verified=False. Do not change email before that mail is generated/sent: the Celery task reloads the user and sends to whatever user.email is current.
- 2. Log in and send PATCH /api/user/me/ {email:'victim@example.com'} with the Bearer access token; the serializer accepts any iexact-unused address and UpdateUserQuery leaves email_verified False.
- 3. GET /api/verify-email/?uid=<uid>&token=T — check_token recomputes the identical hash (pk, password, timestamp, verified all unchanged) and VerifyEmailQuery sets email_verified=True.
- 4. The account now carries victim@example.com with email_verified=True — an attestation the mailbox owner never made; store creation's email gate is satisfied (phone anchor still required).
- **Observed**: Source-traced: _make_hash_value omits user.email so the pre-change token validates post-change; VerifyEmailQuery sets the flag on check_token success; StoreViewSet.create then treats the unproven address as verified for the claim gate.

**Impact**: Forges the email_verified attestation for an unproven address — defeats the store-claim anti-abuse email gate (phone anchor still required) and points account mail at an address the owner never authorized; no direct data exposure or account takeover.

**Priority rationale**: likelihood=medium, impact=low.

**Smallest fix**: Bind the verification token to the address it was issued for: include user.email (or an HMAC of it) in EmailVerificationTokenGenerator._make_hash_value so any email change invalidates outstanding links; alternatively persist the address the mail was sent to and compare it at verification time.

### LOW — No Origin/Referer check on platform session-issuing endpoints -> login CSRF (session donation) on /api/token/ and /api/auth/google/

**Fingerprint**: `users-auth:login-csrf-no-origin-check` · **Confidence**: high

**Location**: DaventProject/urls.py, AdminApp/domains/users/views/auth_views.py

**Principal**: Victim must visit an attacker-controlled page that auto-submits a cross-site form POST, then use the SPA while unknowingly logged into the attacker's account. 

**Description**: CustomTokenObtainPairView and GoogleAuthView plant the session cookies (davent_refresh httpOnly + davent_csrf) in the response with no validation of the request Origin/Referer and no pre-session anti-CSRF token. DRF APIViews are csrf_exempt (rest_framework/views.py:149), the endpoints accept application/x-www-form-urlencoded bodies (a plain cross-site HTML form POST parses into request.data), and SameSite=Lax does not prevent a top-level navigation POST response from storing Set-Cookie. An attacker auto-submitting a form with THEIR credentials (password, or a Google credential minted with the public client_id from /api/config/) leaves the victim's browser holding the attacker's refresh+CSRF cookies; the SPA's silent refresh then logs the victim into the attacker's account, and everything the victim subsequently enters (billing PII, store content) is visible to the attacker. The buyer-side auth implements exactly this defense — _session_origin_allowed is invoked on register/login/google — but it was never ported to the platform auth views.

**Root cause**: Missing origin binding on cookie-session issuance: neither CustomTokenObtainPairView.post (auth_views.py:232) nor GoogleAuthView.post/_social_session_response (auth_views.py:435-460,529-538) checks Origin/Referer against the request host or trusted origins, unlike the sibling customer endpoints.

**Trace**:
- `entrypoint` `DaventProject/urls.py:110` (urlpatterns) — POST /api/token/ → CustomTokenObtainPairView; POST /api/auth/google/ → GoogleAuthView (:130) — both issue the cookie session
- `propagation` `AdminApp/domains/users/views/auth_views.py:232` (CustomTokenObtainPairView.post) — post() performs lockout+auth and sets cookies — no Origin/Referer validation anywhere in AdminApp auth (grep for Origin/Referer/Sec-Fetch across the domain returns only unrelated comments)
- `sink` `AdminApp/domains/users/views/auth_views.py:287` (CustomTokenObtainPairView.post / _set_refresh_cookie) — _set_refresh_cookie/_set_csrf_cookie (also auth_views.py:458-459 for Google) store the attacker's session in the victim's browser; SPA silent refresh (frontend/src/api/http.js:163-167) then authenticates as the attacker

**Conditions**:
- _user_interaction_ — Victim must visit an attacker-controlled page that auto-submits a cross-site form POST, then use the SPA while unknowingly logged into the attacker's account.
- _network_routing_ — API and SPA must be served on the same host (path-alias or same-origin deploy — both the compose/nginx and Render/whitenoise modes serve them same-origin) so davent_csrf is readable via document.cookie and the planted cookies are first-party.
- _authentication_level_ — Attacker needs a valid platform account (open registration) whose credentials are embedded in the auto-submitted form.

**Reproduction** (Authenticated platform user aiming to make victims unknowingly operate inside the attacker's account.):
- 1. Host a page with <form method='POST' action='https://<platform>/api/token/'> auto-submitting the attacker's username/password.
- 2. Victim visits the page; the top-level navigation POST returns 200 JSON and Set-Cookie stores davent_refresh (httpOnly, Path=/api/token/) + davent_csrf (Path=/) as first-party cookies — SameSite=Lax does not block setting.
- 3. Victim later opens the SPA; hasSessionCookie() sees davent_csrf and refreshCall posts /api/token/refresh/ with X-CSRFToken — the double-submit pair matches, rotation succeeds, and the SPA holds the attacker's access token.
- 4. Everything the victim enters (billing PII, store content) lands in the attacker's account.
- **Observed**: Source-traced: no Origin/Referer check exists on either session-issuing endpoint or in DaventProject/middleware.py; DRF APIView is csrf_exempt; FormParser accepts urlencoded bodies; cookies are set unconditionally on 200; the frontend's silent-refresh chain consumes exactly those cookies and the planted CSRF pair passes _require_csrf.

**Impact**: Victim unknowingly uses the attacker's account — data they enter (billing PII, store content) is exposed to the attacker; no takeover of the victim's own account and no direct credential theft.

**Priority rationale**: likelihood=medium, impact=low.

**Smallest fix**: Port the sibling _session_origin_allowed check into every session-issuing endpoint (CustomTokenObtainPairView.post and GoogleAuthView.post) before credentials are processed and cookies set; allow only request-host, CORS_ALLOWED_ORIGINS and CSRF_TRUSTED_ORIGINS origins, permitting absent Origin for non-browser clients.

## Needs validation (unproven leads — no severity assigned)

| Lead | Trace | Exact blocker |
|---|---|---|
| Django admin unreachable through the VPS web tier for any ADMIN_URL not under /admin/ or /api/ — obfuscation requirement and proxy coverage contradict each other | `docker/web/templates/default.conf.template, AdminApp/domains/users/checks.py, .env.example, DaventProject/urls.py (+1)` | The actual ADMIN_URL in the VPS .env is not source-visible; if it happens to be 'api/<something>/' the admin does work through the /api/ proxy (and 'api/admin/' would satisfy users.E001 while remaining guessable). / Whet |
| PUBLIC_DOMAIN is unsettable in every deploy path — canonical-host redirects and store-domain CNAME verification are hardcoded to 'davent.com.ar' | `DaventProject/settings.py, docker-compose.yml, DaventProject/middleware.py, StoreApp/domains/stores/services/domains.py (+1)` | Actual PLATFORM_DOMAIN, PUBLIC_DOMAIN, ALLOWED_HOSTS and FRONTEND_URL values in the VPS .env are not source-visible; PUBLIC_DOMAIN's absence from the allowlist means it cannot be set via compose regardless, but whether t |
| Store MP webhook and public order-pay inherit the default anonymous throttles — shared Mercado Pago egress IPs may starve legitimate payment notifications | `StoreApp/domains/storepayments/views/webhook.py, DaventProject/settings.py, venv/Lib/site-packages/rest_framework/throttling.py, DaventProject/throttling.py (+1)` | MP webhook egress IP count/distribution and aggregate daily notification volume across ALL DAVENT store webhooks plus the platform /api/payments/webhook/ consumer are provider/runtime facts not in source; starvation requ |

Full details in `NEEDS-VALIDATION.md`.

## Hardening notes (not findings)

- _hunter-01_: LogoutRateThrottle(UserRateThrottle) on AllowAny TokenLogoutView does NOT throttle anonymous requests (UserRateThrottle.get_cache_key returns None for anon) — the comment 'acotado por usuario o por IP si no hay auth' is inaccurate; impact is minor (blacklist needs a valid token) but the claim should be fixed or the scope changed to a SimpleRateThrottle keyed by IP.
- _hunter-01_: Platform auth throttles are plain AnonRateThrottle/UserRateThrottle — they lack the _pinned_ident REMOTE_ADDR pinning and _ResilientThrottleMixin fail-open used by DaventProject.throttling and the customer CustomerRateThrottle; a Redis outage turns login/reset endpoints into 500s instead of degrading gracefully.
- _hunter-01_: request.data.get('username') type-confusion: a JSON body with username as object/array/int reaches _login_fail_key's .strip() -> AttributeError -> 500 on POST /api/token/ (also via _register_login_failure on the 400 path). Robustness bug, no security bypass — coerce/validate type before use.
- _hunter-01_: VerifyGoogleCredentialQuery (platform) omits the iss+exp double-checks that the sibling verify_google_credential applies (customers/services/google.py:92-99); tokeninfo already enforces both server-side so this is defense-in-depth only.
- _hunter-01_: davent_remember cookie is unsigned client input: a caller can self-set it to extend refresh lifetime to 30d on each rotation — equivalent to the login-time remember flag, but worth noting since it also applies to any stolen refresh token replayed with the header/cookie pair.
- _hunter-01_: User.email has no DB-level uniqueness (Django default); iexact uniqueness is app-level only — a registration/update race could produce duplicate emails making password-reset's .first() lookup ambiguous. Consider a functional unique index on lower(email).
- _hunter-01_: SocialLoginQuery IntegrityError fallback re-queries by email only: a username-collision race (not email) re-raises -> 500. Availability nit.
- _hunter-01_: is_active is not re-checked per request by SimpleJWT JWTAuthentication nor on TokenRefresh — sessions issued before a deactivation stay valid until expiry/blacklist (library behavior; the Google-issuance bypass is reported separately).
- _hunter-02_: AdminApp/domains/payments/services/services.py:65 — _reject_test_payment accepts live_mode=None in production (only `is False` rejects); sibling StoreApp/domains/storepayments/services/webhook.py:59 fails closed requiring `is True`. Align to fail-closed.
- _hunter-02_: AdminApp/domains/payments/services/services.py:97 — `(mp_payment.get('currency_id') or 'ARS') != 'ARS'` defaults missing currency to ARS (fail-open); storepayments sibling requires =='ARS' (fail-closed).
- _hunter-02_: AdminApp/domains/payments/views/viewset.py:158 — `request.data.get('type')` runs before signature verification; a valid JSON array/scalar body makes request.data a non-dict -> AttributeError -> unauthenticated 500 on a public endpoint (storepayments webhook.py:135 hardened with isinstance check). Copy the isinstance guard.
- _hunter-02_: AdminApp/domains/payments/services/services.py:167 — `Suscription.objects.filter(pk=mp_payment.get('external_reference'))` raises ValueError->500->infinite MP retry for non-numeric external_reference; audit_orphan_payments.py:91 guards with isdigit(), the webhook path does not.
- _hunter-02_: Payment-mutating endpoints (checkout, subscription, sync?payment_id=, POST /payments/) each cost an MP API roundtrip but share only the generic 1000/day user throttle — a dedicated tighter scope would bound provider-side spend/latency.
- _hunter-02_: UpdatePreapprovalPlanQuery/SyncPreapprovalQuery/GetPreapproval perform MP HTTP inside select_for_update transactions (subscription action, RequestPlanChangeQuery, sync) — row lock held across network latency; same-suscription webhook/payment accreditation queues behind it (bounded by HTTP timeout; availability only).
- _hunter-02_: DailyRevenue/MonthlyRevenue.total_amount has no Greatest(0) floor (payments_count does); buckets are symmetric today, but any future paid_at drift could render a day/month total negative — dashboard-only impact.
- _hunter-02_: Webhook inherits anon throttle 100/day per IP; a misconfigured-secret deployment where every webhook 401s could see MP retries throttled to 429 — same net effect (not processed), but worth noting for ops alerting.
- _hunter-03_: DaventProject/sitemaps.py:47-50 — StoreSitemap.items() filters only is_published+is_blocked; no has_public_link check. Expired-plan stores appear in sitemap.xml but their public API 404s — leaks slug existence of stores whose public web is off. Low (cross-listed as infra:sitemap-benefit-gate).
- _hunter-03_: viewset.py:159 CATALOG_FEATURES_MAX = 4096 is dead code — _feature_filters (lines 209-232) runs json.loads on the full ?features= param (twice per cache miss). The CP-04 comment claims a byte cap that was never wired. Practical impact negligible (bounded by web-server URL/header limits ~8KB).
- _hunter-03_: MembershipCardPublicView (memberships/views/customer.py:323-364) intentionally ignores is_published/is_blocked (documented: unguessable public_token = credential). A blocked store's cards stay reachable; payload is minimal. Design decision — note only.
- _hunter-03_: Memberships _public_store_or_404 (memberships/views/customer.py:62-78) checks store_has_ecommerce but not has_public_link explicitly — ecommerce implies an active subscription so the link benefit is effectively implied. Consistent.
- _hunter-04_: bulk_prices: coerce/validate category, brand and product_ids to integers before use — non-numeric values currently reach store.categories.filter(pk='abc')/id__in and raise ValueError -> HTTP 500 (viewset.py:375-390; price_updates.py:84-88). Same class of issue for oversized product_ids lists (unbounded id__in).
- _hunter-04_: customization_publish and customization_restore copy layout_config/site_theme drafts/snapshots verbatim; even after adding a read-side layout_config filter, re-running clean_layout_config/clean_site_theme at publish/restore (like the template_draft whitelist check at viewset.py:1604/1694) would keep stored drafts honest and shrink the downgrade window.
- _hunter-04_: DiscountViewSet._broadcast_offer fires notify_store_discount to all store members on every create/activate (viewset.py:165-177); a mass-create loop spams the owner's own customers — consider dedupe/throttle on the notification path.
- _hunter-04_: Category/Brand/Discount list endpoints return the full unpaginated queryset (CatalogBaseViewSet.list has no pagination); harmless for the owner but compounds candidate 2 — cap or paginate once quotas exist.
- _hunter-04_: StoreSerializer.is_published is owner-writable; acceptable because public endpoints independently enforce has_public_link, but consider gating publish on an active subscription for defense in depth.
- _hunter-04_: export_prices iterates the entire product queryset per request (plan-capped, so bounded) — fine today; revisit if max_products becomes unlimited on the top tier.
- _hunter-05_: Proof-upload race (orders/views/public.py:216-279): status/payment_method/hasattr(order,'proof') checked before the Store->Order lock and never re-validated under it. An order transitioning to CANCELLED/EXPIRED between fast-path check and lock gets a PaymentProof created after release_proof already ran -> orphaned row + R2 object + consumed quota. Window sub-second; bounded by 10/h/IP and 4MB. Re-check locked_order.status/payment_method inside the atomic.
- _hunter-05_: CustomerRefreshView 500 on crafted JWT (auth_views.py:310-330): CustomerRefreshToken(refresh, verify=False) + unverified['jti']/['exp'] — a structurally valid JWT missing those claims raises KeyError, not caught by except (InvalidToken, TokenError) -> unhandled 500 on an unauthenticated endpoint (throttled 300/h). Wrap claim access.
- _hunter-05_: Throttle namespace collision: ResilientUserRateThrottle keys throttle_user_<pk>; request.user can be a Customer (pk space) or auth.User (same pk space) on different endpoints sharing the 'user' 1000/day scope (e.g., cart views have no throttle_classes -> defaults apply). Cross-principal quota interference — availability nuisance only.
- _hunter-05_: has_customer_auth porousness: resolve_store gates register/login/google/password-reset on has_customer_auth, but public_store/sellable_store/_public_store_or_404 (cart, orders, membership subscribe, exclusive products) require only has_ecommerce. A store without the customer-auth benefit still sells to any global customer and auto-creates StoreMembership rows. Plan-gate semantics gap — likely a product decision, flag for confirmation.
- _hunter-05_: MpPayment.order_id is a denormalized BigIntegerField, no FK (storepayments/models/models.py:50) — documented contract note; store scoping enforced via find_order_by_token + order.store_id double-check.
- _hunter-05_: Resilient throttles fail-open on cache loss — deliberate, logged; auth/state invariants unaffected.
- _hunter-05_: ReturnRequest PII not run through clean_free_text (legalpages/views/views.py:238-248) — stored plaintext; rendered escaped everywhere today. Defense-in-depth note only.
- _hunter-05_: ReturnRequestStatusView status change has no select_for_update — benign (idempotent transitions, owner-only).
- _hunter-05_: Subscription payment_method='mp' is selectable (memberships/views/customer.py:105-117) but no MP checkout exists for subscriptions (manual MVP) — cosmetic; owner verifies manually.
- _hunter-06_: Feed video upload is functionally broken (not security): upload_post_media video branch passes processed=None for kind='video' and storage._put_object then evaluates _IMAGE_CONTENT_TYPES[upload.content_type] -> KeyError on 'video/mp4' -> HTTP 500 on every video media upload (feed/services/feed.py:155-160 -> stores/services/storage.py:322-324).
- _hunter-06_: FeedPostWriteSerializer.validate requires caption (KIND_POLL) / embed_url (KIND_EMBED) even on partial PATCH, so unrelated edits like toggling is_published on a poll/embed post return 400 (feed/serializers/serializers.py:36-65).
- _hunter-06_: StoreFeedCommentsView.get filters comments by raw ?post= query param without int validation -> non-numeric value raises Django ValidationError/ValueError -> 500 (feed/views/views.py:163-165).
- _hunter-06_: PublicFeedCommentsView.get returns all non-hidden comments unpaginated — bound it regardless of the throttle fix (feed/views/views.py:211-215).
- _hunter-06_: StoreMpWebhookView relies on default throttles (anon 100/day + user 1000/day keyed by IP); MP webhook egress IPs are shared platform-wide — consider throttle_classes=[] or a dedicated scope so legitimate payment notifications cannot be 429'd at volume (storepayments/views/webhook.py:109-114).
- _hunter-06_: Order payment proofs use object_url(key, private=True) with the 7-day default presigned TTL while chat attachments use an explicit 1h TTL — consider passing expires=3600 for consistency on buyer PII receipts (orders/serializers/serializers.py:170, orders/views/public.py:279; orders domain, adjacent).
- _hunter-07_: AdminApp/domains/chat/views/viewset.py:249 — AssistantViewSet.send reads request.data.get('body') without a serializer: a JSON body of non-string type raises AttributeError on .strip() -> unhandled 500. Validate with a CharField serializer like ChatSendSerializer.
- _hunter-07_: AdminApp/domains/notifications/views/viewset.py:71-73 — read() passes request.data['id'] straight into qs.filter(pk=nid): a non-numeric id raises ValueError/TypeError -> 500. Coerce/validate to int first.
- _hunter-07_: AdminApp/domains/locations/views/viewset_config.py:18-21 — city_list_queryset passes raw ?province= into filter(province_id=...): non-numeric input raises ValueError -> 500 on a public anonymous endpoint. Wrap in try/except or validate digits.
- _hunter-07_: McpApp/domains/skills/views/viewset.py:91-106 — McpEndpointView assumes params is a dict; a JSON-RPC params array/string makes params.get raise AttributeError -> 500. isinstance-check params before dispatch.
- _hunter-07_: AdminApp/domains/legal/views/viewset_base.py:14 — ContentReportRateThrottle does not inherit DaventProject.throttling._ResilientThrottleMixin: a Redis/cache outage makes SimpleRateThrottle raise -> 500 on the public report endpoint, inconsistent with the project's deliberate fail-open throttle design.
- _hunter-07_: AdminApp/domains/chat/services/services.py:97-99 — messages_payload with after>0 returns qs.filter(id__gt=after) with no LIMIT; bounded in practice by chat_send rate and own-thread scoping, but an explicit cap would bound worst-case payload.
- _hunter-07_: AdminApp/domains/chat/services/services.py:52 — get_or_create_thread can race (two concurrent first-sends) -> IntegrityError -> 500; wrap in try/except IntegrityError and re-get.
- _hunter-07_: AdminApp/domains/chat/services/assistant.py:164-172 + McpApp/domains/skills/services/llm.py:122-148 — assistant send is synchronous across up to 4 providers (~30s timeout each, worst ~102s per request) on sync gunicorn workers; per-user chat_send 120/hour bounds spend but there is no global/daily LLM budget — consider a per-user daily cap or async task if abuse appears.
- _hunter-07_: AdminApp/domains/chat/services/services.py:140 — staff_roster() includes every is_staff user (incl. superusers); if the roster feature is kept, restrict to support agents (see candidate chat.staff-roster-leaks-all-staff-identities).
- _hunter-08_: SSE ?ticket= param isn't in the Sentry scrub list — EventSource isn't captured by default breadcrumbs and tracing is disabled, so no current exposure; add 'ticket' to the scrub patterns for completeness.
- _hunter-08_: Minor unrevoked blob on repeated AppProducts.vue:85 picks — hygiene only.
- _hunter-09_: .gitignore does not cover `.secrets/` — the deploy drops plaintext MP_WEBHOOK_SECRET/SECRET_MP_KEY into /opt/davent/.secrets/ (inside the git working tree) before shredding; a failed run leaves them on disk and `git add -A` on the VPS could commit them. Add `.secrets/` to .gitignore.
- _hunter-09_: First-party/sigstore GitHub actions are tag-pinned (actions/checkout@v7, setup-python@v7, setup-node@v4, docker/setup-buildx-action@v4, docker/login-action@v4, docker/metadata-action@v6, docker/build-push-action@v7, sigstore/cosign-installer@v3) while third-party actions are SHA-pinned — inconsistent; tags are mutable. Consider SHA-pinning all.
- _hunter-09_: cosign signs sha-<commit> images but the VPS deploy (`docker compose pull` + `up`) never verifies signatures — provenance is decorative until `cosign verify` (or registry-level policy) is added to the deploy script.
- _hunter-09_: build job keeps packages:write + id-token:write permissions on pull_request runs; PR-controlled Dockerfile RUN steps execute in that context. For same-repo PRs the token retains declared perms; consider gating elevated permissions to non-PR events.
- _hunter-09_: tblib is installed unpinned in the CI test job (`pip install ... tblib`); pin it like coverage==7.6.10.
- _hunter-09_: requirements.txt has == pins but no --require-hashes; pip-audit+trivy gates exist, so this is defense-in-depth only.
- _hunter-09_: Base images are tag-mutable throughout (python:3.11-slim-bookworm, node:22-alpine, nginxinc/nginx-unprivileged:1.30-alpine, postgres:16-alpine, redis:7.4-alpine, caddy:2*); Dependabot 'docker' entries point at '/' and '/docker' which may not match nested docker/api|web|caddy/Dockerfile — verify dependabot actually proposes base-image updates.
- _hunter-09_: logscrub SECRET_PATTERNS do not cover '*_SECRET'/'*_KEY' names — SECRET_KEY, MP_WEBHOOK_SECRET, SECRETS_MASTER_KEYS, R2_SECRET_ACCESS_KEY, non-PEM AFIP_KEY would pass through unredacted if ever logged. No current call site logs them (grep-verified), so this is a safety-net gap, not an active leak.
- _hunter-09_: envguard E010 false-positives on the legitimate Django CSRF wildcard 'https://*.domain' already present in .env.example — '://*' substring check can't distinguish CORS (no wildcard support) from CSRF (wildcard supported). A verbatim .env.example deploy fails check_env/check --deploy.
- _hunter-09_: envguard E018 exempts any origin containing 'localhost'/'127.0.0.1' — 'http://localhost.evil.com' would slip the prod http check; match host exactly instead of substring.
- _hunter-09_: envguard has no rule requiring DEBUG=False — combined with the spelling bypass (candidate), consider an explicit E-rule or a check that fails whenever settings.DEBUG under --deploy.
- _hunter-09_: ADMIN_URL validation (users.E001 + CI grep) only rejects exact 'admin'/'admin/' — 'Admin/', 'adminx/', ' admin/' pass; require minimum length/entropy or a charset check rather than a denylist of one value.
- _hunter-09_: gunicorn forwarded_allow_ips='*' + api/celery on edge_net: any compromised edge_net container can spoof X-Forwarded-For/Proto to api:8000, bypassing client_ip/throttle/lockout pinning (post-compromise lateral). Restrict forwarded_allow_ips to the nginx/caddy subnet if feasible.
- _hunter-09_: custom_hosts.is_verified_domain_host calls cache.get/cache.set outside the try — a Redis outage 500s all custom-domain/subdomain-foreign hosts (fail-closed but ungraceful); wrap cache ops in the resilient helpers.
- _hunter-09_: compose x-api-env omits PUBLIC_DOMAIN (see candidate), SENTRY_DSN (no error tracking on VPS), and all AI-provider keys (ANTHROPIC/GEMINI/GROQ/OPENROUTER + models) — AI design silently falls back to deterministic script on VPS; consider documenting or wiring intentionally.
- _hunter-09_: tls_ask endpoint is a public oracle revealing whether an arbitrary domain is a verified StoreDomain (customer enumeration, ~1000/h/IP via PublicReadThrottle) and doesn't check store is_published/is_blocked before Caddy issues certs — minor; consider a shared-secret header in the ask URL if Caddy supports it.
- _hunter-09_: render.yaml DEPLOY_CHECK_STRICT=0 means deploy-check violations (e.g. missing SECRETS_MASTER_KEYS -> PII encrypted under kid 'self' becoming unreadable later) only appear in logs; documented tradeoff, but consider alerting on the check output.
- _hunter-09_: vite ^5.4.8 resolves to 5.4.21 — Vite 5 is an EOL major line (devDep, build-time only, excluded from npm audit --omit=dev); plan upgrade to Vite 6/7.
- _hunter-09_: Dockerfile HEALTHCHECK and compose healthchecks hit /healthz/ which returns only {'status':'ok'} — verified no info disclosure; keep it that way.
- _hunter-09_: nginx :8081 vhost uses server_name _ accepting any Host — currently safe because only Caddy edge_net reaches it after tls-ask approval; if edge_net membership ever grows, re-review.
- _hunter-09_: SPA frame-ancestors/CSP allow https://*.${PLATFORM_DOMAIN} — any store subdomain can frame the platform SPA (intended for editor preview); store owners can't inject arbitrary iframes today, but keep an eye on design-pattern HTML capabilities.
- _hunter-10_: [object Object]
- _hunter-10_: [object Object]
- _hunter-10_: [object Object]
- _hunter-10_: [object Object]
- _hunter-10_: [object Object]
- _hunter-10_: [object Object]
- _hunter-10_: [object Object]
- _hunter-10_: [object Object]
- _hunter-10_: [object Object]
- _hunter-10_: [object Object]
- _hunter-10_: [object Object]
- _hunter-11_: Add a dedicated throttle scope for the stream endpoint sized for holds plus a per-customer concurrent-stream counter in cache (max 2-3 open streams).
- _hunter-11_: Make stream tickets single-use or near-single-use: embed a jti recorded in cache for the TTL, or shorten TICKET_TTL to ~30-60s.
- _hunter-11_: Bind the ticket to session state (tokens_valid_after/session iat floor) and re-check customer.is_active inside _events every ~15s.
- _hunter-11_: Validate the store slug at ticket mint via resolve_store and treat unknown slug as empty result instead of dropping the filter.
- _hunter-11_: Bypass GZipMiddleware for text/event-stream (set Content-Encoding identity) to preserve heartbeat delivery.
- _hunter-11_: Consider nginx limit_conn for the stream route as a second-layer cap.
- _hunter-11_: Do not log query strings for the stream route (ticket is a bearer credential for up to 120s).
- _hunter-11_: Bound Last-Event-ID replay.
- _hunter-12_: Gate design pattern retrieve/preview by plan entitlement or return markup-free serializer to non-entitled users.
- _hunter-12_: Add dedicated throttle scope and/or server-side cache for preview (key by pattern revision+theme+style, not accent).
- _hunter-12_: Validate preview params: accent must match HEX_COLOR_RE; style limited to is_active.
- _hunter-12_: Constrain public default/catalog serializers; consider is_default only for base-tier patterns.
- _hunter-12_: Add explicit public allowlist for benefit codes in PlanCatalogSerializer.get_benefits.
- _hunter-12_: Keep PublicReadThrottle's pinned-IP get_cache_key property if refactoring throttles.
- _hunter-13_: RegisterRateThrottle is plain AnonRateThrottle (not Resilient): 500s on cache outage, lacks _pinned_ident REMOTE_ADDR pinning.
- _hunter-13_: ai_design.apply_design_overlay trusts overlay verbatim — currently unreachable; re-run clean_* inside if a future path wires it.
- _hunter-13_: invoices retry-cae has no throttle — admin-only but synchronous ARCA round-trips; consider per-admin throttle.
- _hunter-13_: orders/services/carriers.py res.json() unguarded -> 500 on non-JSON 200; wrap in try/except.
- _hunter-13_: stores sync GET (line 1726) also lacks has_customization gate — read-only own-store, nil impact, consistency only.

## Positive patterns observed

- `sanitize_markup`/`sanitize_css` + sandboxed iframe (no `allow-same-origin`) + per-response nonce CSP on all design document/preview surfaces.
- `normalize_image` WebP recode enforced on every upload path reviewed (store images, chat attachments, order proofs, pattern imports).
- Mercado Pago webhook signature verification and store-scoped webhook routing.
- `_pinned_ident` REMOTE_ADDR pinning and `_ResilientThrottleMixin` fail-open on the customer throttle stack (the platform-side plain throttles lack both — see confirmed findings).
- Customer JWT session-epoch sealing via `tokens_valid_after` and SimpleJWT `CHECK_USER_IS_ACTIVE` enforcement.
- Server-side price recomputation on cart/orders; soft stock reservations filtered by `expires_at__gt=now` in the claim query itself.
- Owner-scoped `get_object_or_404`/queryset patterns with no cross-tenant IDOR found in reviewed units.
- Parameterized ORM usage throughout; no raw SQL injection sinks found.

## Coverage summary

- Units: 13 — candidate: 13
- Confirmed records: 20 · needs_validation: 3 · rejected candidates: 5
- Final critic result: wave-1 critic returned `gaps_found`; all three gaps (customer SSE stream, residual plumbing, public catalog/design surfaces) were closed by wave-2 hunters 11–13 and independently verified in Phase-3.
- Rejected candidates (not findings): `catalog-owner:layout-config-plan-gate-read-drift`, `public-catalog-and-design:auth-read-exposes-premium-pattern-markup`, `public-catalog-and-design:preview-render-no-dedicated-throttle-cache`, `residual-plumbing:sync-run-missing-plan-gate`, `users-auth:google-login-is-active-bypass`
