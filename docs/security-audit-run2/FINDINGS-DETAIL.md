# Findings detail — confirmed medium/high/critical records

## HIGH · Single customer account + single IP can saturate all gunicorn gthreads via replayable SSE tickets (full-API DoS)

Fingerprint: `customers-sse:worker-exhaustion`

### Source trace
- **entrypoint** `StoreApp/domains/customers/urls/urls.py:59` — urlpatterns: GET /api/customer/notifications/stream/ → CustomerNotificationStreamView.as_view() — public route proxied by nginx location /api/ (proxy_read_timeout 60s, no connection cap)
- **propagation** `StoreApp/domains/customers/views/notification_views.py:154` — CustomerNotificationStreamView: permission_classes=[AllowAny], authentication_classes=[], throttle_classes=[CustomerPublicReadThrottle] — no session auth runs, so request.customer is never set and the throttle falls back to client IP
- **propagation** `StoreApp/domains/customers/views/auth_views.py:175` — CustomerRateThrottle.get_cache_key: ident = f'c{customer.pk}' if request.customer else get_ident(request) → IP-keyed bucket; _pinned_ident (DaventProject/throttling.py:14-27) pins REMOTE_ADDR so XFF spoofing cannot multiply the quota; scope 'public_read' = '1000/hour' (DaventProject/settings.py:85); _ResilientThrottleMixin.allow_request fails OPEN on cache errors (throttling.py:73-79)
- **propagation** `StoreApp/domains/customers/views/notification_views.py:162` — CustomerNotificationStreamView.get: signing.loads(ticket, max_age=120) authorizes the stream; no jti/single-use — one ticket opens unlimited concurrent connections for 120s (mint cost: CustomerApiThrottle 'user'=1000/day per customer, auth_views.py:210-214)
- **propagation** `StoreApp/domains/customers/views/notification_views.py:178` — CustomerNotificationStreamView.get/_events: StreamingHttpResponse(self._events(...)) — gunicorn gthread iterates the generator synchronously; the worker thread is occupied until the monotonic deadline (STREAM_MAX_SECONDS=50, line 189/210) or client disconnect
- **sink** `docker/api/gunicorn.conf.py:14` — gunicorn gthread workers: workers=int(env GUNICORN_WORKERS,3) × threads=int(env GUNICORN_THREADS,4), worker_class='gthread', timeout=60 — 12 concurrent request handlers for the ENTIRE API; Render blueprint pins 2×4=8 (render.yaml:185-188), .env.example documents 3×4

### Evidence
- `StoreApp/domains/customers/views/notification_views.py:53` — STREAM_MAX_SECONDS=50 — every connection leases a gthread for up to 50s; PING_SECONDS=15 heartbeat is the only dead-client detector
- `StoreApp/domains/customers/views/notification_views.py:156` — throttle_classes=[CustomerPublicReadThrottle] is the ONLY rate control on the stream endpoint (overrides DEFAULT_THROTTLE_CLASSES)
- `StoreApp/domains/customers/views/notification_views.py:125` — Ticket minted as signing.dumps({'c':pk,'s':slug}) — replayable within TICKET_TTL=120s, no jti
- `StoreApp/domains/customers/views/auth_views.py:207` — class CustomerPublicReadThrottle(CustomerRateThrottle): scope='public_read'
- `DaventProject/settings.py:85` — 'public_read': '1000/hour' — ~1000 stream connection-opens per hour per IP; 864/hour suffices to hold 12 threads busy continuously
- `DaventProject/throttling.py:73` — _ResilientThrottleMixin.allow_request catches all exceptions → fail-open if the throttle cache (Redis/locmem) errors
- `docker/api/gunicorn.conf.py:14` — workers=3, threads=4, worker_class='gthread', timeout=60 — 12 handlers total; streams self-close at 50s so the 60s worker timeout never intervenes
- `docker-compose.yml:48` — GUNICORN_WORKERS default 3 / GUNICORN_THREADS default 4 via x-api-env; .env.example:50-51 documents the same; render.yaml:185-188 pins 2×4 for the Render deploy
- `docker/web/snippets/proxy_api.conf:10` — proxy_read_timeout 60s is the only proxy bound on /api/ — no limit_conn, no limit_req (the sole limit_req_zone covers = /api/token/ only, default.conf.template:10,112-115)
- `StoreApp/domains/customers/views/auth_views.py:246` — CustomerRegisterView.post → _session_response issues customer_access JWT at registration; email_verified is not required for token issuance (IsCustomer only needs is_active)

### Attacker / resource
- Principal: Attacker needs one customer account: POST /api/customer-auth/register/ is AllowAny self-service issuing an immediate JWT ('register' throttle 10/hour/IP is irrelevant — one account suffices). No platform (auth.User) account or email verification needed. 
- Resource: the affected boundary described above (per-record trace).

### Reproduction (target-native, bounded)
Attacker perspective: Unauthenticated internet user who self-registers one buyer account and runs a small script holding SSE sockets.

Payloads:
- `POST /api/customer-auth/register/ {"email":"a@b.c","password":"...","first_name":"x","last_name":"y"} → {access, customer}`
- `POST /api/customer/notifications/stream-ticket/ {"store":""} (Authorization: Bearer <access>) → {"ticket":"<T>","expires_in":120}`
- `GET /api/customer/notifications/stream/?ticket=<T>&store=  — repeated ×N concurrent; re-issue every ~45s while ticket age <120s; mint a new ticket via stream-ticket when it expires`

Instructions:
1. Register one customer account (open endpoint, JWT returned immediately).
2. Mint one stream ticket (replayable for 120s — unlimited concurrent GETs allowed with the same ticket).
3. Open ≥12 (or ≥8 on Render) concurrent GET /api/customer/notifications/stream/?ticket=<T> connections; each holds a gthread ~50s.
4. Cycle: re-open connections before each 'bye'/50s close using the same ticket until it nears 120s, then mint a new ticket (~every 2 minutes → ~720/day, under the 1000/day 'user' throttle).
5. Result: all gunicorn gthreads permanently occupied by streams → every other API request (all storefronts, auth, orders, admin) queues in the gunicorn backlog and times out at nginx (proxy_read_timeout 60s) for the duration of the attack.

Observed result: Source-traced end-to-end: throttle math (1000/hour/IP budget vs ~864-1000 needed holds/hour for 8-12 threads), thread-hold semantics of StreamingHttpResponse under gthread, replayable ticket removing per-connection credential cost, absence of any concurrency cap in view/nginx/Caddy/gunicorn config, and immediate-JWT open registration. No runtime test performed (source-only constraint).

### Security invariant
A long-lived connection endpoint must bound concurrent holds, not just request rate: a dedicated throttle scope sized for the feature plus a cache-backed in-flight counter (e.g. max 2-4 open streams per customer+IP), single-use or near-single-use tickets, and/or an nginx limit_conn on the stream route.

### Conditions & containment
- _authentication_level_: Attacker needs one customer account: POST /api/customer-auth/register/ is AllowAny self-service issuing an immediate JWT ('register' throttle 10/hour/IP is irrelevant — one account suffices). No platform (auth.User) account or email verification needed.
- _system_configuration_: Deployed concurrency = GUNICORN_WORKERS×GUNICORN_THREADS. Both documented configs fall below the single-IP saturation threshold (3×4=12 needs ~864 conn/hour; 2×4=8 needs ~576 — both < 1000/hour). A larger env override would raise the bar but the endpoint still lacks any dedicated concurrency bound.
- _network_routing_: All traffic from a single IP — the throttle ident pins REMOTE_ADDR|last-XFF so header spoofing cannot rotate the bucket; no per-IP connection cap exists at nginx or Caddy.
- _timing_dependency_: Sustained scripted hold: open N≥thread-count concurrent streams, re-GET before each ~50s server close while the ticket is <120s old, mint a fresh ticket ~every 120s (~720/day < 1000/day 'user' budget).

### Remediation
Bound concurrent holds, not just request rate: (1) dedicated throttle scope for the stream endpoint (e.g. 'customer_notifications_stream' ~120-240/hour per customer+IP) PLUS a cache-backed in-flight semaphore (max ~3 open streams per customer+IP, acquired on connect / released on generator close); (2) make tickets effectively single-use or few-use by embedding a jti consumed from cache at connect (the frontend already re-mints a ticket per connection, so single-use breaks nothing); (3) bind tickets to the session epoch (tokens_valid_after) and re-check customer.is_active inside _events; (4) optionally add nginx limit_conn on /api/customer/notifications/stream/ as a second layer.

`StoreApp/domains/customers/views/notification_views.py`:
```python
import secrets
from django.core.cache import cache

class CustomerNotificationStreamTicketView(APIView):
    throttle_classes = [CustomerApiThrottle]
    def post(self, request):
        slug = ((request.data or {}).get('store') or '').strip().lower()
        jti  = secrets.token_urlsafe(16)
        #jti de un solo uso + epoch de sesión: el ticket no sobrevive al
        #logout/reset (tokens_valid_after) ni puede abrir N streams a la vez.
        ticket = signing.dumps(
            {'c': request.customer.pk, 's': slug, 'j': jti,
             'tva': str(request.customer.tokens_valid_after or '')},
            salt = STREAM_SALT)
        cache.set(f'stream-ticket:{jti}', request.customer.pk, TICKET_TTL)
        return Response({'ticket': ticket, 'expires_in': TICKET_TTL}, status = status.HTTP_200_OK)

class CustomerNotificationStreamView(APIView):
    #... en get(), tras signing.loads:
    #   jti = data.get('j')
    #   if jti is None or cache.get(f'stream-ticket:{jti}') != data.get('c'):
    #       return 401                      # ticket ya usado / ajeno
    #   cache.delete(f'stream-ticket:{jti}') # un solo uso (front re-mintea)
    #   if data.get('tva') != str(customer.tokens_valid_after or ''): 401
    #   key = f'stream-open:c{customer.pk}'
    #   if not cache.add(key, 1, STREAM_MAX_SECONDS + 10): return 429  # tope concurrencia
    # y en _events(..., finally): cache.delete(key)
```

### Regression case
Add a test asserting the invariant above fails before the fix and passes after (per-repo test conventions: `manage.py test <app>`); cover the exploit path from `execution.payloads`.

## MEDIUM · Caddy edge image builds caddy-dns/cloudflare plugin at unpinned latest — mutable build input into the TLS terminator for all traffic

Fingerprint: `infra:caddy-xcaddy-unpinned`

### Source trace
- **entrypoint** `docker/caddy/Dockerfile:7` — xcaddy build: RUN xcaddy build --with github.com/caddy-dns/cloudflare --replace golang.org/x/net=...@v0.62.0 — plugin module has no @version; xcaddy resolves latest at build time
- **propagation** `docker/caddy/Dockerfile:4` — base images: FROM caddy:2-builder (line 4) and FROM caddy:2 (line 10) — mutable tags
- **propagation** `docker/caddy/Caddyfile:36` — wildcard platform site + on-demand custom domains: *.{env.PLATFORM_DOMAIN} uses tls { dns cloudflare {env.CF_API_TOKEN} } (lines 36-39) and the https:// catch-all uses on_demand tls with ask -> api (lines 19-21,48-52): the unpinned plugin/binary controls DNS-01 for the wildcard cert and terminates TLS for every verified customer domain
- **sink** `docker-compose.yml:118` — db/redis images: postgres:16-alpine (118) and redis:7.4-alpine (142) tag-mutable, re-pulled by `docker compose pull` each deploy (ci-cd.yml:513)

### Evidence
- `docker/caddy/Dockerfile:7` — xcaddy build --with github.com/caddy-dns/cloudflare — no version pin on the plugin
- `docker/caddy/Dockerfile:10` — FROM caddy:2 — mutable tag for the runtime image
- `docker/caddy/Caddyfile:38` — dns cloudflare {env.CF_API_TOKEN} — the unpinned plugin holds the Cloudflare Zone.DNS token
- `docker-compose.yml:351` — CF_API_TOKEN injected into the caddy container env
- `.github/workflows/ci-cd.yml:513` — docker compose pull re-pulls tag-mutable images on each deploy

### Attacker / resource
- Principal: A malicious or compromised commit lands in caddy-dns/cloudflare (or its transitive deps) before the next image build, or a mutable base-image tag is repointed; xcaddy generates a fresh go.mod without a committed go.sum so there is no lockfile review surface. 
- Resource: the affected boundary described above (per-record trace).

### Reproduction (target-native, bounded)
Attacker perspective: Not directly exploitable by a remote attacker; the exposure is a mutable build input into the highest-trust component. A compromised upstream module author or registry path would land code at the next image build.

Payloads:
- `docker/caddy/Dockerfile: xcaddy build --with github.com/caddy-dns/cloudflare (no version constraint)`

Instructions:
(Source review) Confirm the Dockerfile resolves the plugin without a version; confirm Caddyfile routes all platform + customer-domain TLS through the resulting binary

Observed result: Source-confirmed absence of version pin; xcaddy semantics resolve latest by default. Trivy/image scanning would not catch a malicious-but-clean Go module.

### Security invariant
Pin the plugin to a release tag/commit (@vX.Y.Z or pseudo-version), commit the resulting go.mod/go.sum or build via a locked module file, and digest-pin base images (or rely on Dependabot docker updates with review).

### Conditions & containment
- _third_party_dependency_: A malicious or compromised commit lands in caddy-dns/cloudflare (or its transitive deps) before the next image build, or a mutable base-image tag is repointed; xcaddy generates a fresh go.mod without a committed go.sum so there is no lockfile review surface.
- _environmental_dependency_: Requires an upstream supply-chain compromise — external trigger, very improbable, but the blast radius is maximal (edge MITM + CF DNS token).

### Remediation
Pin the plugin: `xcaddy build --with github.com/caddy-dns/cloudflare@v0.5.0` (or current release) and vendor/commit the resulting go.mod+go.sum; digest-pin caddy:2-builder/caddy:2 bases; optionally digest-pin postgres/redis images or accept the risk explicitly.

### Regression case
Add a test asserting the invariant above fails before the fix and passes after (per-repo test conventions: `manage.py test <app>`); cover the exploit path from `execution.payloads`.

## MEDIUM · DEBUG=True reachable in production via non-'True' env spellings — every deploy guard compares raw strings while decouple cast=bool accepts 'true'/'1'/'yes'/'on'

Fingerprint: `infra:debug-bypass-spellings`

### Source trace
- **entrypoint** `DaventProject/settings.py:29` — settings module top-level: DEBUG = config('DEBUG', default=False, cast=bool) — decouple _cast_boolean delegates to strtobool: 'true','t','yes','y','on','1' in any case parse True (verified in repo venv)
- **propagation** `docker/api/entrypoint.sh:20` — entrypoint gunicorn branch: if [ "$DEBUG" != "True" ] — only the exact string 'True' skips check --deploy; 'true'/'1'/'yes'/'TRUE'/'on' run a check that cannot fail
- **propagation** `DaventProject/checks.py:24` — check_production_transport_security: early-returns [] when settings.DEBUG; envguard computes prod = not settings.DEBUG (envguard.py:100) skipping prod rules, and users checks early-return at users/checks.py:18 and :38 — the whole custom check surface is vacuous under DEBUG
- **propagation** `DaventProject/urls.py:136` — DEBUG-gated urlpatterns: if settings.DEBUG: mounts api-auth/, api/schema/, swagger, redoc and static(MEDIA_URL) at line 145 — private/ chat attachments under MEDIA_ROOT become web-served where no nginx 404s them
- **sink** `.github/workflows/ci-cd.yml:480` — deploy preflight: grep -q '^DEBUG=True' .env is case-sensitive and misses every other truthy spelling; the Render deploy path has no equivalent gate at all

### Evidence
- `DaventProject/settings.py:29` — DEBUG = config('DEBUG', default = False, cast = bool)
- `docker/api/entrypoint.sh:20` — if [ "$DEBUG" != "True" ]; then python manage.py check --deploy --fail-level ERROR ...
- `.github/workflows/ci-cd.yml:480` — if grep -q '^DEBUG=True' .env; then echo "FATAL: DEBUG=True en el .env de producción"; exit 1; fi
- `DaventProject/checks.py:24` — if settings.DEBUG: return [] — project.E001-E005 skipped
- `AdminApp/domains/users/checks.py:18` — if settings.DEBUG: return [] — users.E001/E002/E003 skipped (same at line 38)
- `DaventProject/envguard.py:206` — E017 validates DEBUG spelling against ('0','1','true','false','yes','no','on','off') — proves the project knows these parse, yet nothing flags a truthy value in prod
- `DaventProject/urls.py:145` — urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) inside the DEBUG block
- `AdminApp/domains/chat/services/attachments.py:44` — default_storage.save('private/' + key, ...) — chat attachments live under MEDIA_ROOT/private when no object storage is configured
- `venv/Lib/site-packages/decouple.py:1` — Local decisive check: Config._cast_boolean -> strtobool; running `DEBUG=<v> python -c config('DEBUG', cast=bool)` printed True for 'true','TRUE','1','yes','on','t','y' and False for '0','no','off','false'

### Attacker / resource
- Principal: Operator/deploy sets DEBUG to a truthy spelling other than the exact string 'True' in the deploy env (.env on VPS, dashboard env on Render). Not attacker-controlled, but the guard chain exists precisely to catch this class of misconfiguration and all three layers fail on spelling. 
- Resource: the affected boundary described above (per-record trace).

### Reproduction (target-native, bounded)
Attacker perspective: Not directly attacker-controlled: an operator mistake or compromised deploy config sets DEBUG; afterwards any unauthenticated internet user can reach the exposed surfaces.

Payloads:
- `.env: DEBUG=true`
- `.env: DEBUG=1`
- `.env: DEBUG=yes`
- `.env: DEBUG=TRUE`
- `Render dashboard env: DEBUG=on`

Instructions:
Set DEBUG to a non-'True' truthy spelling in the deploy environment
Restart/redeploy the api service (entrypoint runs check --deploy which returns no errors)
As an anonymous client request /api/schema/, /api/docs/swagger/, /api-auth/ and a non-DRF route that raises to observe the technical debug page; on Render also request /media/private/<known-key>

Observed result: Source + local venv verification: decouple parses all listed spellings to True; entrypoint still runs check --deploy which passes vacuously (all custom checks early-return on settings.DEBUG; Django deploy findings are warnings below --fail-level ERROR); gunicorn boots with settings.DEBUG=True; urls.py DEBUG block mounts schema/docs/browsable API and static(MEDIA_URL).

### Security invariant
Any env spelling that Django parses as DEBUG=True must be treated identically by the entrypoint gate, the CI preflight, and a system check — production must refuse to boot (or at minimum run a check that can actually fail) whenever the effective DEBUG is true.

### Conditions & containment
- _environmental_dependency_: Operator/deploy sets DEBUG to a truthy spelling other than the exact string 'True' in the deploy env (.env on VPS, dashboard env on Render). Not attacker-controlled, but the guard chain exists precisely to catch this class of misconfiguration and all three layers fail on spelling.
- _system_configuration_: On the VPS compose path SECURE_SSL_REDIRECT/SESSION_COOKIE_SECURE/CSRF_COOKIE_SECURE/SECURE_HSTS_* are pinned by x-api-env defaults so the cookie/HSTS downgrade is mitigated there; on Render they are pinned in render.yaml. The schema/docs/api-auth/technical-error-page exposure and (on Render) MEDIA static exposure are unconditional once DEBUG parses True.

### Remediation
Normalize once and compare the parsed value everywhere: (1) entrypoint.sh and the CI preflight should test settings.DEBUG (e.g. `python -c "import django; django.setup(); from django.conf import settings; raise SystemExit(0 if settings.DEBUG else 1)"`) or grep case-insensitively for all truthy spellings; (2) add an envguard rule that errors when the raw DEBUG env parses truthy in a deploy context; (3) decouple the urls.py DEBUG block from DEBUG alone (require an explicit SCHEMA_ENABLED-style flag) so a DEBUG slip cannot expose schema/docs/media.

`docker/api/entrypoint.sh`:
```python
if ! python -c "import os,django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','DaventProject.settings'); django.setup(); from django.conf import settings; raise SystemExit(1 if settings.DEBUG else 0)"; then
    if [ "$DEPLOY_CHECK_STRICT" = "1" ]; then
        echo "DEBUG efectivo es True en produccion -> abortando arranque"
        exit 1
    fi
fi
if [ "$DEBUG" != "True" ]; then
    if ! python manage.py check --deploy --fail-level ERROR; then
        ...
    fi
fi
```

`.github/workflows/ci-cd.yml`:
```python
# Replace the case-sensitive grep with a parse-based check:
if grep -iqE '^DEBUG=(true|t|yes|y|on|1)\s*$' .env; then echo "FATAL: DEBUG truthy en el .env de producción"; exit 1; fi
```

### Regression case
Add a test asserting the invariant above fails before the fix and passes after (per-repo test conventions: `manage.py test <app>`); cover the exploit path from `execution.payloads`.

## MEDIUM · Authenticated users bypass the content_report throttle entirely — unbounded report emails to the legal mailbox

Fingerprint: `legal.content-report.throttle-anon-only-authenticated-bypass`

### Source trace
- **entrypoint** `AdminApp/domains/legal/views/viewset_base.py:25` — ContentReportBaseViewSet.throttle_classes: throttle_classes = [ContentReportRateThrottle] replaces DRF DEFAULT_THROTTLE_CLASSES entirely; this is the only throttle consulted for every action including create.
- **propagation** `AdminApp/domains/legal/views/viewset_base.py:14` — ContentReportRateThrottle: class ContentReportRateThrottle(AnonRateThrottle) with scope='content_report' (line 18). AnonRateThrottle.get_cache_key returns None for authenticated users (venv throttling.py:173-180); allow_request returns True on None key (throttling.py:119-121).
- **propagation** `AdminApp/domains/legal/views/viewset_config.py:25` — ContentReportConfigs['create'].permissions: create permissions = [AllowAny] — reachable with or without a session; JWTAuthentication (settings.py:64-66) still populates request.user for Bearer-authenticated callers before permission checks.
- **propagation** `AdminApp/domains/legal/services/services.py:23` — CreateContentReportQuery: Every valid create calls send_legal_report_email.delay(report.pk) after ContentReport.objects.create.
- **propagation** `AdminApp/domains/users/tasks.py:67` — send_legal_report_email: Celery task (autoretry x3) -> NotifyContentReportQuery -> send_mail to settings.LEGAL_REPORTS_EMAIL (legal/services/services.py:41-48).
- **sink** `DaventProject/settings.py:134` — DEFAULT_THROTTLE_RATES['content_report']: 'content_report': '5/hour' — the intended bound; unreachable for authenticated users because the anon-only throttle never keys them.

### Evidence
- `AdminApp/domains/legal/views/viewset_base.py:14` — ContentReportRateThrottle(AnonRateThrottle), scope 'content_report' — anonymous-only by DRF design.
- `AdminApp/domains/legal/views/viewset_base.py:25` — throttle_classes = [ContentReportRateThrottle] overrides DEFAULT_THROTTLE_CLASSES, so no user/anon fallback throttle applies on this viewset.
- `venv/Lib/site-packages/rest_framework/throttling.py:173` — AnonRateThrottle.get_cache_key: 'if request.user and request.user.is_authenticated: return None' — authenticated requests are never throttled.
- `venv/Lib/site-packages/rest_framework/throttling.py:119` — SimpleRateThrottle.allow_request: 'self.key = self.get_cache_key(...); if self.key is None: return True'.
- `AdminApp/domains/legal/views/viewset_config.py:25` — create permissions [AllowAny] — endpoint accepts authenticated and anonymous callers.
- `DaventProject/settings.py:75` — DEFAULT_THROTTLE_CLASSES (ResilientAnon + ResilientUser) only apply to views that do not override throttle_classes — this viewset does.
- `DaventProject/settings.py:134` — 'content_report': '5/hour' — documented anti-spam bound (comment lines 132-133: each valid POST emails LEGAL_REPORTS_EMAIL).
- `AdminApp/domains/legal/services/services.py:23` — send_legal_report_email.delay(report.pk) on every create.
- `AdminApp/domains/legal/services/services.py:46` — send_mail recipient_list=[settings.LEGAL_REPORTS_EMAIL] (default davidcv28@outlook.com, settings.py:407).
- `frontend/src/api/legal.api.js:1` — Report form uses the platform http client; http.js:116-124 attaches 'Authorization: Bearer' whenever a session token exists, so even UI submissions from logged-in users bypass the anon throttle.

### Attacker / resource
- Principal: Attacker holds any registered platform account (free registration; no subscription/plan required). A valid JWT access token sent as 'Authorization: Bearer <token>' makes request.user authenticated. 
- Resource: the affected boundary described above (per-record trace).

### Reproduction (target-native, bounded)
Attacker perspective: Registered platform user (free account) scripting POST /api/content-reports/ with their own Bearer access token in a loop.

Payloads:
- `POST /api/content-reports/ HTTP/1.1
Authorization: Bearer <access_token>
Content-Type: application/json

{"reporter_name":"Test User","reporter_email":"a@b.com","kind":"ILLEGAL","reported_url":"https://example.com/x","original_work":null,"description":"padding description at least twenty chars","good_faith":true}`

Instructions:
Register a free platform account and obtain an access token via POST /api/token/.
Loop POST /api/content-reports/ with the JSON body above and 'Authorization: Bearer <access_token>'.
Observe that requests beyond the first 5 within an hour still return 201 (each creating a ContentReport row and enqueueing an email) — no 429 is ever returned for the authenticated principal; only request throughput bounds the volume.
Repeat with additional accounts to multiply volume; anonymous callers from the same IP remain capped at 5/hour.

Observed result: Source-derived: for authenticated requests ContentReportRateThrottle.get_cache_key returns None -> allow_request True, and because throttle_classes replaces DEFAULT_THROTTLE_CLASSES no other throttle engages, so every request returns 201 with no rate limit at all (unbounded, worse than the ~1000/day fallback the hunter assumed). Anonymous callers are correctly capped at 5/hour per IP by the same class.

### Security invariant
The 5/hour 'content_report' limit should bound every caller of the public create endpoint — anonymous and authenticated alike — since every accepted POST produces an email to LEGAL_REPORTS_EMAIL plus a DB row and Celery/SMTP work.

### Conditions & containment
- _authentication_level_: Attacker holds any registered platform account (free registration; no subscription/plan required). A valid JWT access token sent as 'Authorization: Bearer <token>' makes request.user authenticated.
- _system_configuration_: Default DRF JWTAuthentication populates request.user on the AllowAny endpoint; Celery task delivery (eager in dev, worker in prod) sends one email per accepted report.
- _data_state_: Request body must pass ContentReportSerializer validation (valid kind, http(s) reported_url, description >= validators, good_faith=true; original_work required only for COPYRIGHT/TRADEMARK).

### Remediation
Make the content_report scope cover both principal classes. Either pair the anon throttle with an authenticated-user throttle on the same scope, or replace the class with a SimpleRateThrottle whose get_cache_key returns 'user_pk' when authenticated and pinned IP otherwise — and inherit DaventProject.throttling._ResilientThrottleMixin so a cache outage fails open consistently with the rest of the project. Keep throttle_classes containing BOTH classes (do not rely on DEFAULT_THROTTLE_CLASSES, which this viewset overrides).

`AdminApp/domains/legal/views/viewset_base.py`:
```python
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from DaventProject.throttling import _ResilientThrottleMixin

class ContentReportAnonThrottle(_ResilientThrottleMixin, AnonRateThrottle):
    scope = 'content_report'

class ContentReportUserThrottle(_ResilientThrottleMixin, UserRateThrottle):
    #Authenticated callers get the SAME 5/hour budget keyed by user pk —
    #AnonRateThrottle alone returns None for them and (because
    #throttle_classes overrides DEFAULT_THROTTLE_CLASSES) left the endpoint
    #completely unthrottled for any logged-in account.
    scope = 'content_report'

class ContentReportBaseViewSet(viewsets.GenericViewSet):
    viewset_config   = {}
    throttle_classes = [ContentReportAnonThrottle, ContentReportUserThrottle]
```

### Regression case
Add a test asserting the invariant above fails before the fix and passes after (per-repo test conventions: `manage.py test <app>`); cover the exploit path from `execution.payloads`.

## MEDIUM · Any paid plan price satisfies the payment amount check — pay the cheapest tier price, receive the most expensive plan for 30 days

Fingerprint: `payments.cross-plan-amount-acceptance`

### Source trace
- **entrypoint** `AdminApp/domains/payments/views/viewset.py:285` — PaymentViewSet.checkout: POST /api/payments/checkout/ -> _resolve_suscription -> CreateCheckoutPreferenceQuery(suscription): preference unit_price = pending_charge or (pending_plan or plan_suscription).price snapshot at creation time; external_reference = str(suscription.id). An earlier preference keeps its creation-time amount and stays payable.
- **propagation** `AdminApp/domains/payments/services/services.py:377` — CreateCheckoutPreferenceQuery: Lines 382-391 freeze unit_price + external_reference into the MP Checkout Pro preference — the charged amount is immutable once issued; MP preferences remain payable at the snapshot price.
- **propagation** `AdminApp/domains/suscriptions/serializers/serializers.py:68` — SuscriptionSerializer.update: PATCH /api/suscriptions/<id>/ {plan_suscription}: PENDING_PAYMENT branch (lines 74-83) rewrites plan_suscription directly to the expensive plan; ACTIVE branch (line 90) -> RequestPlanChangeQuery sets pending_plan_suscription=expensive + pending_charge=prorated.
- **propagation** `AdminApp/domains/suscriptions/services/services.py:133` — RequestPlanChangeQuery: Lines 132-135: upgrade sets pending_plan_suscription=target_plan and pending_charge=_upgrade_charge(...) (prorated); downgrade sets pending_plan only. Live-preapproval realignment is best-effort — exceptions swallowed at lines 136-141, so MP can keep debiting the old amount.
- **propagation** `AdminApp/domains/payments/views/viewset.py:140` — PaymentViewSet.webhook: MP notification for the stale cheap payment arrives at POST /api/payments/webhook/ (or via POST /api/payments/sync/ viewset.py:432 or POST /api/payments/ create) -> PaymentWebhookQuery -> CreatePaymentQuery with the attacker-owned suscription.
- **propagation** `AdminApp/domains/payments/services/services.py:124` — CreatePaymentQuery: `if amount not in accepted_amounts` — the cheap amount passes because accepted_amounts (lines 115-123) contains EVERY non-trial plan price; the pending/expensive entitlement is never bound to the paid amount.
- **sink** `AdminApp/domains/payments/services/services.py:287` — ApplyPendingPlanQuery: Lines 287-313: pending_plan applied to plan_suscription unconditionally on APPROVED; prorated gate (281-286) requires paid_amount == pending_charge exactly, so any other accepted amount -> prorated=False -> end_date = now+30d, status=ACTIVE, period_payment_id=payment. Expensive plan granted at cheap-tier price.

### Evidence
- `AdminApp/domains/payments/services/services.py:115` — accepted_amounts = {plan_price (pending_plan or plan), current plan price, *(ALL SuscriptionPlan.objects.filter(is_trial=False).values_list('price')), pending_charge} — union of every paid plan price, membership-only check at line 124.
- `AdminApp/domains/payments/services/services.py:281` — prorated = pending_plan AND pending_charge AND paid_amount == pending_charge — any other accepted amount takes the full-renewal branch (296-313): start=now, end=now+30d, status=ACTIVE.
- `AdminApp/domains/suscriptions/serializers/serializers.py:74` — PENDING_PAYMENT branch rewrites plan_suscription directly (lines 79-82) — no pending_plan indirection, so a stale cheap preference pays for whatever plan is currently set.
- `AdminApp/domains/suscriptions/services/services.py:136` — UpdatePreapprovalPlanQuery realignment is best-effort inside try/except — a failed MP update leaves the preapproval debiting the old cheap amount, recurring the mismatch monthly.
- `AdminApp/domains/payments/tests.py:1249` — test_debit_at_previous_plan_price_is_registered codifies symmetric acceptance: pending_plan=cheap(500), payment at current plan price(1000) -> APPROVED + pending_plan applied + pending cleared — deliberate design, the exploit primitive in mirror image.
- `AdminApp/domains/invoices/services/services.py:72` — IssueInvoiceQuery reads suscription.plan_suscription.name AFTER ApplyPendingPlanQuery (called at payments/services.py:146->149) -> plan_name=expensive plan while total=payment.amount=cheap (line 85): fiscally inconsistent receipt, CAE requested on the cheap total.
- `StoreApp/domains/storepayments/services/webhook.py:228` — Sibling comparison: seller-side MP webhook requires amount == order.total exactly; mismatch -> amount_mismatch flag + OrderEvent for manual review (fail-closed). The platform subscription path accepts any plan price (fail-open).
- `AdminApp/domains/suscriptions/management/commands/seeds.py:10` — Seeded plans differ in price — 25000/30000/40000/60000 ARS — giving a real spread for the cheapest-to-most-expensive arbitrage.

### Attacker / resource
- Principal: Attacker holds a platform account (store-owner principal) with billing fields complete — BillingMissingFieldsQuery (payments/views/viewset.py:275-280) only requires fiscal profile data, trivially supplied. 
- Resource: the affected boundary described above (per-record trace).

### Reproduction (target-native, bounded)
Attacker perspective: Registered DAVENT platform user with a complete billing profile and >=2 priced plans available (seeded default).

Payloads:
- `Variant A (pending_payment): 1) POST /api/payments/checkout/ {"plan_suscription": <cheap_pk>} -> creates pending_payment Suscription + MP preference P1 (unit_price=cheap.price, external_reference=<sub_id>) 2) PATCH /api/suscriptions/<sub_id>/ {"plan_suscription": <expensive_pk>} -> plan_suscription=expensive (PENDING_PAYMENT branch) 3) Pay P1 in MP Checkout ($cheap) -> payment approved, external_reference=<sub_id>, transaction_amount=cheap 4) POST /api/payments/sync/ {"payment_id": <mp_payment_id>} (or await webhook) -> Payment APPROVED, Suscription ACTIVE plan=expensive end_date=+30d`
- `Variant B (active upgrade): 1) On an ACTIVE cheap-plan subscription with auto_renew off: POST /api/payments/checkout/ {} -> preference P2 at cheap full price 2) PATCH /api/suscriptions/<sub_id>/ {"plan_suscription": <expensive_pk>} -> pending_plan=expensive, pending_charge=prorated 3) Pay stale P2 ($cheap) -> Payment APPROVED; paid_amount != pending_charge -> prorated=False -> pending expensive plan applied AND end_date=now+30d`
- `Recurring: repeat the downgrade-pending + stale-cheap-preference + upgrade-pending cycle each period, or keep a live preapproval whose UpdatePreapprovalPlanQuery realignment failed (best-effort, exceptions swallowed) so monthly debits keep arriving at the old cheap amount and each renews the expensive plan +30d.`

Instructions:
Ensure billing fields are complete (GET subscription -> billing_required fields if any).
Create the cheap-priced MP artifact first: POST /api/payments/checkout/ while the subscription targets the cheap plan (variant A: fresh pending_payment sub; variant B: active cheap-plan sub). Do NOT pay it yet.
Change the granted/target plan to the expensive one via PATCH /api/suscriptions/<id>/ {"plan_suscription": <expensive_pk>} (or POST /api/payments/checkout/ {"suscription": <id>, "plan_suscription": <expensive_pk>}, which also issues a new expensive preference while leaving the cheap one payable).
Pay the earlier cheap preference in the MP Checkout UI — it charges the snapshot cheap price with external_reference=<sub_id>.
Trigger registration: await the MP webhook, or POST /api/payments/sync/ {"payment_id": <id>}, or POST /api/payments/ {"suscription": <id>, "payment_id": <id>}.
Observe: Payment row amount=cheap_price status=approved; Suscription.plan_suscription=expensive, status='Suscripcion activa', end_date=now+30d; Invoice total=cheap_price plan_name=expensive; grants_access()=True -> full expensive-tier benefits for 30 days at cheap-tier price.

Observed result: Source-derived (read-only audit, MP not contacted): CreatePaymentQuery accepts amount=cheap because it is in accepted_amounts (all non-trial plan prices); Payment created APPROVED; ApplyPendingPlanQuery applies pending_plan (or the already-rewritten plan_suscription for pending_payment) and sets end_date=now+30d with status=ACTIVE; IssueInvoiceQuery emits invoice with plan_name=expensive plan and total=cheap amount. grants_access() returns True -> expensive-tier benefits at cheap-tier price, repeatable monthly.

### Security invariant
A payment should only credit the entitlement its amount pays for: pending_charge for prorated upgrades, or the price of the specific plan being applied (pending_plan if set else plan_suscription for pending_payment). Stale-amount MP charges should either map amount->plan (grant the plan that amount corresponds to) or be rejected/flagged for reconciliation — as the sibling StoreApp storepayments webhook does (exact order.total match required, mismatch -> manual review) — rather than silently upgrading entitlement.

### Conditions & containment
- _authentication_level_: Attacker holds a platform account (store-owner principal) with billing fields complete — BillingMissingFieldsQuery (payments/views/viewset.py:275-280) only requires fiscal profile data, trivially supplied.
- _data_state_: At least two non-trial SuscriptionPlans with different prices — the seeded default set (25000/30000/40000/60000 ARS) satisfies this out of the box.
- _third_party_dependency_: A payable stale-amount MP artifact bound to external_reference=<own suscription.id>: a Checkout Pro preference issued before the plan change keeps its creation-time unit_price (standard MP behavior the codebase explicitly relies on, services.py:107-112), or a preapproval debit generated before realignment.
- _user_interaction_: The attacker must complete the cheap-tier MP payment with real funds at the lower plan price — no provider misbehavior, race, or admin action is required; the sequence is fully deterministic.

### Remediation
Bind the accepted amount to the granted entitlement instead of unioning all plan prices. Compute expected = pending_charge if set else (pending_plan or plan_suscription).price for pending_payment contexts; accept only that amount for auto-apply. For genuinely stale MP artifacts (amount equals a DIFFERENT plan's price), resolve amount->plan and grant THAT plan — never the pending/pricier one — or reject and route to audit_orphan_payments/manual reconciliation like the storepayments sibling (exact amount match + amount_mismatch review). Also make UpdatePreapprovalPlanQuery realignment failure handling consistent so a stale-amount debit cannot recur monthly unnoticed (surface the failure instead of only logging).

`AdminApp/domains/payments/services/services.py`:
```python
    amount              =   Decimal(str(mp_payment.get('transaction_amount', '0')))
    pending_plan        =   suscription.pending_plan_suscription
    plan_price          =   (pending_plan or suscription.plan_suscription).price
    expected_amount     =   suscription.pending_charge if suscription.pending_charge is not None else plan_price
    #El monto solo puede acreditar el cargo/plan que se está aplicando.
    #Un monto de OTRO plan es un artefacto viejo de MP: se mapea monto->plan
    #y se otorga ESE plan (nunca uno más caro que el cobrado), o se rechaza
    #para reconciliación manual — copiar la regla de storepayments
    #(amount == expected exacto, mismatch -> revisión).
    accepted_amounts    =   {Decimal(str(expected_amount))}
    stale_plan          =   None
    if amount not in accepted_amounts:
        stale_plan  =   SuscriptionPlan.objects.filter(is_trial = False, price = amount).first()
        if stale_plan is None:
            raise serializers.ValidationError({
                'payment_id':   f'El monto del pago (${amount}) no coincide con el importe esperado (${expected_amount})'
            })
    #...tras crear el Payment APPROVED, pasar el plan resuelto por monto:
    #ApplyPendingPlanQuery(suscription, renew=True, paid_amount=new_payment.amount,
    #                      payment=new_payment, granted_plan=stale_plan or None)
    #y en ApplyPendingPlanQuery usar granted_plan (el plan cuyo precio se
    #pagó) en lugar de pending_plan cuando el monto no cubre el pendiente.
```

### Regression case
Add a test asserting the invariant above fails before the fix and passes after (per-repo test conventions: `manage.py test <app>`); cover the exploit path from `execution.payloads`.

## MEDIUM · Inventory denial and merchant spam via soft stock-reservation abuse across self-registered customer accounts

Fingerprint: `store-customer:stock-reservation-abuse-needs-validation`

### Source trace
- **entrypoint** `StoreApp/domains/customers/views/auth_views.py:220` — CustomerRegisterView.post: POST /api/customer-auth/register/ — AllowAny self-service registration; throttle_classes=[CustomerRegisterThrottle] (line 229) = scope 'register' 10/hour (settings.py:111) keyed by IP via CustomerRateThrottle.get_cache_key fallback to get_ident when request.customer is None (lines 175-178). No captcha anywhere in the view (post at 231-246).
- **propagation** `StoreApp/domains/orders/views/public.py:122` — PublicOrderCreateView.post: POST /api/stores/public/<slug>/orders/ — permission_classes=[IsCustomer] only; throttle_classes=[OrderCreateThrottle] (line 125) = ResilientUserRateThrottle scope 'store_order_create' rate '10/hour' (lines 63-67) keyed by request.user.pk = customer.pk via DRF UserRateThrottle.get_cache_key (venv rest_framework/throttling.py:193-202) — per ACCOUNT, not per IP. Captcha verified at line 136 (arithmetic, scriptable).
- **propagation** `StoreApp/domains/customers/authentication.py:76` — IsCustomer.has_permission: Requires only isinstance(request.customer, Customer) and customer.is_active — no email_verified, no membership, no per-store check anywhere in the order path.
- **propagation** `StoreApp/domains/orders/services/checkout.py:272` — claimed_quantities: Sums OrderItem.qty over Order.status=PENDING_PAYMENT AND order.expires_at__gt=now for the given product_ids across ALL customers (lines 286-294) — one global reservation pool; expiry is evaluated in the query, so release does not depend on the expire_orders cron.
- **propagation** `StoreApp/domains/orders/services/checkout.py:340` — _resolve_lines: available = product.stock - claimed.get(pid, 0); qty > available -> ValidationError — attacker's pending orders exhaust stock for every other buyer. Caps MAX_QTY=100/line, MAX_ITEMS=50 lines (lines 88-89); expires_at = now + payment_deadline_hours, default 48h, owner-set 1..720h (line 464).
- **sink** `StoreApp/domains/orders/services/notify.py:56` — dispatch_order_event: Every 'created' event: kind in OWNER_NOTIFY_KINDS -> synchronous in-app owner Notification (lines 35-38, 89-92) AND kind in OWNER_EVENT_KINDS -> transaction.on_commit Celery email -> mails.py:46-49,276-283 _owner_new_order_mail — fake orders spam the merchant inbox and panel.

### Evidence
- `DaventProject/settings.py:111` — 'register': '10/hour' — the only gate on self-service customer account minting; keyed by IP for anonymous requests.
- `StoreApp/domains/customers/views/auth_views.py:183` — CustomerRegisterThrottle scope='register'; get_cache_key (175-178) uses customer.pk if present else IP ident — anonymous registration buckets per IP at 10/h.
- `StoreApp/domains/orders/views/public.py:63` — OrderCreateThrottle: ResilientUserRateThrottle scope='store_order_create' rate='10/hour' — DRF UserRateThrottle keys authenticated requests by request.user.pk = customer.pk (per account, evadable by minting accounts).
- `StoreApp/domains/customers/models/models.py:64` — is_active default True, email_verified default False (line 62); is_authenticated property returns True (117-119) so the customer JWT always takes the pk-keyed throttle path.
- `StoreApp/domains/customers/services/customers.py:98` — RegisterCustomerQuery creates the Customer with model defaults and only enqueues a verification email post-commit — tokens are issued immediately (auth_views.py:246 _session_response); nothing requires email_verified to order.
- `StoreApp/domains/stores/services/contact.py:49` — _captcha_question generates deterministic arithmetic (add/sub/mul of small integers); verify_captcha (76-121) enforces only signature+TTL 300s+min 3s+5 attempts — trivially scriptable.
- `StoreApp/domains/orders/services/checkout.py:286` — claimed_quantities filter: product_id__in + order__status=PENDING_PAYMENT + order__expires_at__gt=now — NO customer/store-claimant partition; global soft reservation.
- `StoreApp/domains/orders/services/checkout.py:340` — available = product.stock - claimed; qty > available -> ValidationError 'Stock insuficiente' — cross-customer stock monopolization.
- `StoreApp/domains/orders/services/checkout.py:464` — expires_at = now + deadline_hours (default 48h via DEFAULT_DEADLINE_HOURS line 90; owner-configurable 1..720h per storepayments/serializers/serializers.py:80-83).
- `StoreApp/domains/orders/services/notify.py:35` — OWNER_NOTIFY_KINDS and OWNER_EVENT_KINDS both contain 'created' — every fake order creates an in-app owner notification plus a Celery-queued owner email (mails.py:276-283).

### Attacker / resource
- Principal: Target store is published with orders_enabled and has stock-controlled products (product.stock not null); low stock makes monopolization cheap — one order can claim up to 100 units of each of up to 50 SKUs. 
- Resource: the affected boundary described above (per-record trace).

### Reproduction (target-native, bounded)
Attacker perspective: Anonymous internet user running a script against a public DAVENT store with ecommerce orders enabled.

Payloads:
- `POST /api/customer-auth/register/ {"email":"atkN@mailinator.com","password":"Str0ng!Pass1","store_slug":"<slug>"} -> 200 {access, customer} (repeat <=10/h per IP)`
- `GET /api/stores/public/<slug>/orders/captcha/ -> {challenge_id, question} (arithmetic)`
- `POST /api/stores/public/<slug>/orders/ {"items":[{"product_id":<pid>,"qty":<stock>}],"shipping_method":"pickup","payment_method":"transfer","challenge_id":"<id>","captcha_answer":"<answer>"} -> 201 (repeat <=10/h per account, rotate accounts at 10/h per IP)`

Instructions:
Enumerate stock-controlled products and their stock via the public catalog endpoints.
Register customer accounts at 10/hour per IP (no captcha; unique disposable emails suffice; session tokens issued immediately).
For each account, fetch an order captcha, wait >=3s, solve the arithmetic question, and POST orders claiming qty=stock for target SKUs (up to 50 lines x 100 units per order).
Repeat continuously: claims last until expires_at (48h default, up to 720h owner-set) and auto-release via expires_at__gt=now — sustained ~10 orders/h/account keeps low-stock SKUs 'sold out' indefinitely.
Observe legitimate buyers receiving 'Stock insuficiente' ValidationErrors and the owner receiving an in-app notification + email per fake order.

Observed result: Source-derived (read-only audit, not executed): every link verified line-by-line — uncaptcha'd IP-throttled registration, per-customer.pk 10/h order throttle, global claimed_quantities across all customers' PENDING_PAYMENT orders, expires_at-based release independent of cron, and per-order owner notification+email dispatch.

### Security invariant
Stock claims should require a minimally verified principal (e.g., email_verified) and/or orders should be throttled per-IP in addition to per-account, with a cap on simultaneous PENDING_PAYMENT reservations per store/customer, so anonymous-scale account minting cannot monopolize inventory or flood the merchant.

### Conditions & containment
- _data_state_: Target store is published with orders_enabled and has stock-controlled products (product.stock not null); low stock makes monopolization cheap — one order can claim up to 100 units of each of up to 50 SKUs.
- _network_routing_: Register throttle is per-IP (10/h) and order throttle per-account (10/h): a single IP yields ~10 accounts/h -> ~100 orders/h; IP rotation scales linearly. _pinned_ident (throttling.py:14-27) pins REMOTE_ADDR into the bucket so XFF spoofing does not reset it.
- _system_configuration_: Throttles fail open on cache loss (deliberate, throttling.py:64-79) — but the configured 10/h rates already permit the abuse, so enforcement status does not gate exploitability; fail-open only increases attacker throughput.
- _third_party_dependency_: The owner-email sub-impact requires a running Celery worker + reachable SMTP; the inventory-denial impact is synchronous DB state inside create_order and needs neither.

### Remediation
Gate stock-claiming order creation on a verified principal and bound abuse per origin: (a) require customer.email_verified (or an equivalent verified-contact check) in PublicOrderCreateView/create_order before materializing claims; (b) add a per-IP order throttle alongside the per-account one so account minting does not multiply the budget; (c) cap simultaneous PENDING_PAYMENT reservations per store and/or per customer (e.g., reject create_order when the customer already holds >=N pending orders for the store, and/or when store-wide pending claims exceed a fraction of stock); (d) add captcha (or disposable-email checks) to customer registration; (e) optionally digest owner 'created' notifications/emails instead of one per order.

`StoreApp/domains/orders/views/public.py`:
```python
class OrderCreateIpThrottle(_ResilientThrottleMixin, SimpleRateThrottle):
    """Segunda bolsa por IP: el throttle por customer.pk se evade
    minteando cuentas — la IP acota el total de pedidos por origen."""
    scope = 'store_order_create'
    rate  = '30/hour'
    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {'scope': self.scope, 'ident': ident}

class PublicOrderCreateView(APIView):
    authentication_classes  =   [CustomerJWTAuthentication]
    permission_classes      =   [IsCustomer]
    throttle_classes        =   [OrderCreateThrottle, OrderCreateIpThrottle]
    def post(self, request, slug):
        store       =   _sellable_or_404(slug)
        customer    =   request.customer
        #Stock claims solo para principals verificados: un email sin
        #verificar no puede acaparar inventario ni spamear al dueño.
        if not customer.email_verified:
            return Response({'detail': 'Verificá tu correo para poder comprar.'}, status = status.HTTP_403_FORBIDDEN)
        # ... resto del flujo sin cambios
```

### Regression case
Add a test asserting the invariant above fails before the fix and passes after (per-repo test conventions: `manage.py test <app>`); cover the exploit path from `execution.payloads`.

## MEDIUM · Plan-gate bypass: store owner address leaks via pattern documents and /r/maps/ redirect on plans without has_location_map

Fingerprint: `store-public:location-address-plan-gate-bypass`

### Source trace
- **entrypoint** `StoreApp/domains/stores/views/viewset.py:689` — StoreViewSet.public_contact: Anonymous GET /api/stores/public/<slug>/r/<kind>/ (AllowAny via PUBLIC_ACTIONS). Gates only is_published+is_blocked (lines 694-697) and profile_has_benefit 'has_public_link' (698-699); kind='maps' flows into contact_redirect_url with no show_location/has_location_map check.
- **propagation** `StoreApp/domains/stores/views/viewset.py:818` — StoreViewSet.public_pattern_document: Anonymous GET /api/stores/public/<slug>/pattern/document/ (and /pattern at :797) via _pattern_store (788-795): same published+unblocked+has_public_link gate only; no plan check on location data.
- **propagation** `StoreApp/domains/design/services/pattern_render.py:1145` — build_store_context: address = _text(user.address,160) whenever customization.show_location is true — no profile_has_benefit(...,'has_location_map') check, unlike the serializer's triple gate.
- **propagation** `StoreApp/domains/design/services/pattern_render.py:236` — _page_flags: 'location' flag keyed only on show_location; flags_css ([data-flag] display:none, lines 1818-1821) hides location zones by owner toggle only — plan benefit never consulted.
- **propagation** `StoreApp/domains/design/services/pattern_render.py:1172` — build_store_context context dict: store_address (:1172) and store_maps_url = contact_redirect_path(store,'maps') (:1182) enter the render context; DesignPattern.render (design/models/models.py:358-380) substitutes {{store_address}} into the HTML served by /pattern and /pattern/document (escape() prevents markup injection, not disclosure).
- **sink** `StoreApp/domains/stores/services/contact.py:162` — contact_redirect_url: kind=='maps' builds https://maps.google.com/?q=<user.address>,<city>,<province> from raw UserProfile.address — zero gates: no has_location_map benefit and not even customization.show_location.

### Evidence
- `StoreApp/domains/stores/serializers/serializers.py:806` — get_location_address enforces the intended gate: returns None unless customization.show_location AND profile_has_benefit(store.user,'has_location_map') AND user.address (lines 800-817).
- `StoreApp/domains/stores/views/viewset.py:119` — LOCATION_FIELDS = ('show_location',); discarded from PATCH payload when the plan lacks has_location_map (lines 1398-1399) — basico owners cannot turn the toggle off.
- `StoreApp/domains/stores/models/models.py:243` — show_location = BooleanField(default=True); comment (238-242) states the intent that without the benefit 'la web pública no lo renderiza' — violated by the pattern/redirect paths.
- `AdminApp/domains/users/models/models.py:45` — UserProfile.address is an EncryptedCharField (AES-256-GCM at rest) — treated as protected PII whose plaintext is decrypted on attribute access.
- `SuscriptionApp/domains/benefits/management/commands/seeds.py:60` — Plan basico: has_public_link=True (:48), has_customization=True (:59), has_location_map=False (:60) — the exact affected plan combination.
- `StoreApp/domains/design/models/models.py:379` — DesignPattern.render returns escape(str(context[name])) for declared variables — store_address is declared via PATTERN_VARIABLES (pattern_render.py:47) and sources/*.html usage, so the plaintext address lands in served HTML.
- `StoreApp/domains/design/sources/esencial.html:1584` — {{store_address}} interpolated into served pattern HTML; esencial is tier 'base' (seed_data.json) and DEFAULT_PATTERN (design/seed.py:56) — resolvable by basico-plan stores via template 'raiz'/'esencial'.
- `StoreApp/domains/stores/services/services.py:70` — profile_has_benefit/plan_benefits_of derive benefits only from a subscription with grants_access(); expired plans yield {} so has_public_link fails and public routes 404 — scoping the bug to active low-tier plans.

### Attacker / resource
- Principal: None — both endpoints are AllowAny public actions (PUBLIC_ACTIONS, viewset.py:424,445-453). 
- Resource: the affected boundary described above (per-record trace).

### Reproduction (target-native, bounded)
Attacker perspective: Anonymous internet user who knows or discovers a published store slug (slugs are public via sitemap.xml, shared links, and the public catalog).

Payloads:
- `GET /api/stores/public/<slug>/pattern/document/`
- `GET /api/stores/public/<slug>/pattern/`
- `GET /api/stores/public/<slug>/r/maps/`

Instructions:
Enumerate published store slugs (sitemap.xml, public catalog, shared store links).
For each slug on a plan without has_location_map (Plan basico), request GET /api/stores/public/<slug>/pattern/document/ and search the returned HTML for the address block rendered from {{store_address}} (e.g. 'Dirección', 'Cómo llegar' rows); alternatively GET /api/stores/public/<slug>/pattern/ and inspect the 'html' field of the JSON.
Request GET /api/stores/public/<slug>/r/maps/ and read the 302 Location header — it contains https://maps.google.com/?q=<street address>,<city>,<province> even when the owner set show_location=False.

Observed result: Source-derived (no runtime execution): build_store_context populates store_address from user.address whenever customization.show_location is true with no plan check, so the pattern JSON/document HTML contains the plaintext business address; contact_redirect_url('maps') returns a Google Maps URL embedding the raw address with zero gates, so /r/maps/ 302s to it for any published+unblocked store with has_public_link — including Plan basico stores where StorePublicSerializer.location_address is null.

### Security invariant
Every public surface that exposes the owner street address or a maps deep-link must apply the same effective gate as the serializer: customization.show_location AND profile_has_benefit(store.user,'has_location_map') (and a non-empty address). The 'location' page flag and data-flag zones should hide on the same predicate.

### Conditions & containment
- _authentication_level_: None — both endpoints are AllowAny public actions (PUBLIC_ACTIONS, viewset.py:424,445-453).
- _data_state_: Store is_published=True, is_blocked=False; owner has an ACTIVE subscription granting has_public_link but NOT has_location_map (Plan basico per seeds.py:45-73); UserProfile.address non-empty; a StoreCustomization row exists (auto-created by get_or_create on GET /api/stores/customization/, viewset.py:1391) with show_location=True — the default, which basico owners cannot change because PATCH discards LOCATION_FIELDS.
- _data_state_: For the pattern-document path the resolved DesignPattern markup must reference {{store_address}} (true for the default 'esencial' and ~15 other sources); the /r/maps/ path needs only a non-empty address/city/province and leaks even when show_location=False.

### Remediation
Apply the serializer's effective gate everywhere the address/maps URL is derived: require customization.show_location AND profile_has_benefit(store.user,'has_location_map') in build_store_context for address/store_maps_url and in the 'location' page flag; gate contact_redirect_url kind=='maps' (or public_contact) on the same benefit plus show_location. Consider a data migration or read-time coercion setting show_location=False for stores whose plan lacks has_location_map, since basico owners cannot clear it via PATCH.

`StoreApp/domains/design/services/pattern_render.py`:
```python
    location = ', '.join(part for part in (city, province) if part)
    from StoreApp.domains.stores.services import (
        contact_redirect_path,
        profile_has_benefit,
    )
    #Mismo gate que StorePublicSerializer.get_location_address: la
    #dirección es beneficio 'has_location_map' — sin el flag no viaja al
    #documento ni al link de mapas.
    location_ok = bool(
        customization
        and customization.show_location
        and profile_has_benefit(store.user, 'has_location_map')
    )
    address = _text(getattr(user, 'address', ''), 160) if location_ok else ''
```

`StoreApp/domains/design/services/pattern_render.py`:
```python
    from StoreApp.domains.stores.services import profile_has_benefit
    ...
        'location':     on('show_location') and profile_has_benefit(store.user, 'has_location_map'),
```

`StoreApp/domains/stores/services/contact.py`:
```python
    if kind == 'maps':
        #Mismo gate que la API pública: la ubicación exige el beneficio
        #has_location_map y el toggle show_location del dueño.
        from StoreApp.domains.stores.services.services import profile_has_benefit
        user        =   getattr(store, 'user', None)
        if not getattr(customization, 'show_location', False):
            return ''
        if not profile_has_benefit(user, 'has_location_map'):
            return ''
        parts       =   [
            str(getattr(user, 'address', '') or '').strip(),
            str(getattr(getattr(user, 'city', None), 'name_city', '') or '').strip(),
            str(getattr(getattr(user, 'province', None), 'name_province', '') or '').strip(),
        ]
        query       =   ', '.join(part for part in parts if part)
        return f'https://maps.google.com/?q={quote(query)}' if query else ''
```

### Regression case
Add a test asserting the invariant above fails before the fix and passes after (per-repo test conventions: `manage.py test <app>`); cover the exploit path from `execution.payloads`.

## MEDIUM · Google social login auto-links by email without anti-pre-hijacking: pre-registered account stays accessible to attacker after victim's Google login

Fingerprint: `users-auth:google-autolink-prehijack`

### Source trace
- **entrypoint** `AdminApp/domains/users/views/auth_views.py:529` — GoogleAuthView.post: POST /api/auth/google/ {credential} → VerifyGoogleCredentialQuery + SocialLoginQuery → _social_session_response issues the DAVENT session
- **propagation** `AdminApp/domains/users/services/social.py:103` — SocialLoginQuery: user = User.objects.filter(email__iexact=email).first() — matches ANY account with that email, including one pre-registered by an attacker with unverified email and a usable password
- **propagation** `AdminApp/domains/users/services/social.py:136` — SocialLoginQuery: existing-account branch sets profile.email_verified=True and names only — no has_usable_password check, no set_unusable_password, no session revocation, no prior-verification gate
- **sink** `AdminApp/domains/users/views/auth_views.py:440` — _social_session_response: RefreshToken.for_user(user) mints refresh+access for the Google-verified caller while the pre-registrant's password still authenticates via POST /api/token/

### Evidence
- `AdminApp/domains/users/services/social.py:103` — Account resolution is email-only; no link between the Google identity (sub) and the account — pure auto-link by email
- `AdminApp/domains/users/services/social.py:134` — Existing-account branch (lines 134-147) only updates email_verified/names; zero hardening on credentials or sessions
- `AdminApp/domains/users/services/services.py:133` — RegisterUserQuery uses create_user(password=...) leaving a usable password and email_verified=False; verification mail is async and not required for account use
- `StoreApp/domains/customers/services/google.py:153` — Sibling anti-pre-hijacking block: 'Google probó la titularidad del EMAIL, no quién eligió la contraseña' → set_unusable_password() + tokens_valid_after seal (lines 160-165)
- `AdminApp/domains/users/models/models.py:48` — phone_hash unique=True — one account per phone limits the attack to targeted pre-registration
- `AdminApp/domains/users/tests.py:638` — test_google_links_existing_user_by_email codifies the unguarded auto-link (200 + email_verified=True, password untouched)
- `AdminApp/domains/users/services/services.py:58` — _revoke_sessions exists (bulk-blacklists all OutstandingToken) but SocialLoginQuery never calls it

### Attacker / resource
- Principal: Attacker needs only anonymous access: POST /api/register/ is open (IsAnonimous) and POST /api/token/ requires only the chosen password. 
- Resource: the affected boundary described above (per-record trace).

### Reproduction (target-native, bounded)
Attacker perspective: Unauthenticated internet user who knows or guesses a target's email address.

Payloads:
- `POST /api/register/ {username: 'attacker1', email: 'victim@example.com', password: 'Attacker!23', phone: '+5491100000001', accept_terms: true}`
- `POST /api/auth/google/ {credential: '<Google ID token for victim@example.com>'}  // performed by the VICTIM`
- `POST /api/token/ {username: 'attacker1', password: 'Attacker!23'}  // attacker retains access`

Instructions:
1. Attacker registers an account via POST /api/register/ using the victim's email, the attacker's own password, and a unique phone number (phone_hash uniqueness permits one account per phone — targeted attacks only).
2. The real mailbox owner later clicks 'Login with Google' on the platform; Google proves email ownership and SocialLoginQuery auto-links them into the attacker-created account, setting email_verified=True.
3. The attacker logs in with POST /api/token/ using their own username+password — the credential was never invalidated, so the attacker keeps a fully usable session alongside the victim's.

Observed result: Source-traced: SocialLoginQuery's existing-account branch (social.py:134-147) performs no password invalidation or session revocation; _social_session_response returns 200 with tokens to the Google caller; the password path via TokenObtainPairSerializer→authenticate() still returns 200 for the pre-registrant on the same User row. Both parties hold persistent sessions; profile.email_verified becomes True, also unblocking the store-claim gate.

### Security invariant
Mirror the customer-side contract (StoreApp/domains/customers/services/google.py:153-165): when Google proves ownership of an email that matches a pre-existing account, any usable password must be invalidated and prior sessions sealed, so only the mailbox owner (via Google or password-reset) retains access.

### Conditions & containment
- _authentication_level_: Attacker needs only anonymous access: POST /api/register/ is open (IsAnonimous) and POST /api/token/ requires only the chosen password.
- _data_state_: The victim's email must be unregistered when the attacker pre-registers it, and the victim must later authenticate with Google on that same email.
- _system_configuration_: GOOGLE_CLIENT_ID must be configured; otherwise GoogleAuthView returns 503 and the feature is off.
- _third_party_dependency_: The victim must control a Google account whose verified email equals the pre-registered address.

### Remediation
Port the customer-side anti-pre-hijacking hardening into SocialLoginQuery's existing-account branch: when the matched account has a usable password, call user.set_unusable_password() and revoke all outstanding sessions (_revoke_sessions), so only the mailbox owner retains access via Google or password reset. Optionally restrict auto-link to accounts whose email was already verified or that were social-created.

`AdminApp/domains/users/services/social.py`:
```python
    profile, _  =   UserProfile.objects.get_or_create(user = user)
    #Anti-pre-hijacking (paridad con StoreApp/domains/customers/services/google.py):
    #Google probó la titularidad del EMAIL, no quién eligió la contraseña que
    #ya tenía la cuenta — el alta no exige verificación y el link por email no
    #distingue al pre-registrante del dueño. Cualquier password usable se
    #inutiliza y las sesiones emitidas se revocan: el dueño entra por Google
    #o por reset de contraseña.
    if not is_new and user.has_usable_password():
        from AdminApp.domains.users.services.services import _revoke_sessions
        user.set_unusable_password()
        user.save(update_fields = ['password'])
        _revoke_sessions(user)
    update_fields   =   []
    if not profile.email_verified:
        profile.email_verified      =   True
        profile.email_verified_at   =   timezone.now()
        update_fields   +=  ['email_verified', 'email_verified_at']
```

### Regression case
Add a test asserting the invariant above fails before the fix and passes after (per-repo test conventions: `manage.py test <app>`); cover the exploit path from `execution.payloads`.
