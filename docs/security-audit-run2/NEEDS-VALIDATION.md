# Needs validation — unresolved leads (no severity assigned)

These records are **not confirmed vulnerabilities**. Each lists the source trace, the exact blocker (a deployment/runtime fact not provable from source), and bounded next steps.

## Django admin unreachable through the VPS web tier for any ADMIN_URL not under /admin/ or /api/ — obfuscation requirement and proxy coverage contradict each other

Fingerprint: `infra:admin-url-nginx-gap`

The compose/VPS deploy requires ADMIN_URL to be non-predictable: users.E001 fails check --deploy for 'admin/', the CI preflight greps it out (ci-cd.yml:483-487), and DEPLOY_CHECK_STRICT=1 aborts boot. But the nginx vhost (docker/web/templates/default.conf.template) only proxies /api/ (line 107), = /api/token/ (line 112), and literal /admin/ (line 118) to gunicorn; every other path falls to `location / { try_files $uri $uri/ /index.html; }` (lines 158-160) -> SPA. The web container's env only receives PLATFORM_DOMAIN (docker-compose.yml:298-299), so envsubst cannot inject the admin prefix. With the documented pattern ADMIN_URL=gestion-xxx/ (.env.example:28), requests to /gestion-xxx/login/ are answered with index.html — the Django admin is unreachable from the public web entirely (staff would need an SSH tunnel to api:8000, or an ADMIN_URL placed under 'api/' which passes E001 since strip('/')!='admin' but remains guessable). Either the admin is broken-by-deployment — an ops failure that pressures admins to weaken controls — or operators discovered the 'api/' prefix workaround. On Render there is no nginx so admin works at whatever ADMIN_URL is set.

Claimed root cause: nginx location coverage was written for a literal /admin/ path while the security model requires ADMIN_URL to be a non-obvious env path; no nginx location or envsubst variable maps the configured admin prefix to the API upstream, and the web container is never given ADMIN_URL to do so.

Trace:
- **entrypoint** `docker/web/templates/default.conf.template:107` — platform vhost locations: only /api/ (107), =/api/token/ (112) and literal /admin/ (118) proxy to gunicorn; line 158-160 location / -> try_files /index.html (SPA)
- **propagation** `AdminApp/domains/users/checks.py:20` — check_admin_url (users.E001): settings.ADMIN_URL.strip('/') in ('','admin') -> deploy error; 'admin/' forbidden
- **propagation** `.env.example:28` — documented ADMIN_URL: ADMIN_URL=gestion-cambiar-por-un-path-aleatorio/ — such a path matches NO nginx location
- **propagation** `DaventProject/urls.py:78` — admin mount: path(settings.ADMIN_URL, admin.site.urls) — Django side is correct; only the proxy layer lacks the route
- **sink** `docker-compose.yml:298` — web service environment: web receives only PLATFORM_DOMAIN — the nginx template cannot know ADMIN_URL

Blockers:
- The actual ADMIN_URL in the VPS .env is not source-visible; if it happens to be 'api/<something>/' the admin does work through the /api/ proxy (and 'api/admin/' would satisfy users.E001 while remaining guessable).
- Whether staff actually reach the admin via an SSH tunnel or a different mechanism is an ops fact not in the repo.
- Whether the VPS or the Render deployment is the live production for staff is not source-visible (Render has no nginx, so admin works there at any ADMIN_URL).

Local next step: Render the nginx template through envsubst with a test PLATFORM_DOMAIN and probe /gestion-x/login/ (expect SPA index.html); alternatively `docker compose config` to confirm web env lacks ADMIN_URL.
Owner-observed deployment check: On the VPS: grep '^ADMIN_URL' /opt/davent/.env; curl -sk https://<platform-domain>/<ADMIN_URL>login/ -o /dev/null -w '%{http_code} %{content_type}' — a 200 text/html SPA response instead of the Django admin login confirms the gap; also test an 'api/'-prefixed ADMIN_URL hypothesis if the env shows one.

## PUBLIC_DOMAIN is unsettable in every deploy path — canonical-host redirects and store-domain CNAME verification are hardcoded to 'davent.com.ar'

Fingerprint: `infra:public-domain-unset`

settings.PUBLIC_DOMAIN = config('PUBLIC_DOMAIN', default='davent.com.ar') feeds two mechanisms: (a) CanonicalHostMiddleware builds www.<PUBLIC_DOMAIN> -> <PUBLIC_DOMAIN> 301s (middleware.py:252-263); (b) StoreDomain verification (services/domains.py public_domain()/check_domain/serialize_domain) tells owners to CNAME their custom domain to PUBLIC_DOMAIN and accepts CNAME targets equal to or ending in '.<PUBLIC_DOMAIN>'. PUBLIC_DOMAIN appears nowhere in docker-compose.yml x-api-env (explicit allowlist, lines 22-106), .env.example, or render.yaml envVars — verified by repo-wide grep: only settings.py:36, domains.py:23, middleware.py consume it. So it is ALWAYS 'davent.com.ar' on both deploys regardless of the real platform domain (the repo's own docs disagree: .env.example PLATFORM_DOMAIN=davent.com vs render.yaml davent.com.ar). Depending on the deployed PLATFORM_DOMAIN this produces either: owners following the UI's CNAME instructions pointing traffic at the wrong backend (verified domains that 400 DisallowedHost or serve the other deployment's DB), or — if PLATFORM_DOMAIN=davent.com.ar — an apex->www nginx 301 (default.conf.template:59) fighting Django's www->apex middleware 301 in an infinite loop.

Claimed root cause: PUBLIC_DOMAIN is missing from the compose environment allowlist (x-api-env), .env.example, and render.yaml, so the documented 'env-configurable canonical domain' is unreachable; the hardcoded default 'davent.com.ar' silently wins everywhere — even setting it in .env would not reach the container because compose only injects allowlisted vars.

Trace:
- **entrypoint** `DaventProject/settings.py:36` — settings module: PUBLIC_DOMAIN = config('PUBLIC_DOMAIN', default = 'davent.com.ar')
- **propagation** `docker-compose.yml:22` — x-api-env allowlist: allowlist contains PLATFORM_DOMAIN (line 45) but NOT PUBLIC_DOMAIN -> container always sees the default; also absent from .env.example and render.yaml envVars
- **propagation** `DaventProject/middleware.py:252` — CanonicalHostMiddleware.__init__: canonical/alias derived from PUBLIC_DOMAIN -> www.<PUBLIC_DOMAIN> 301s to apex (lines 260-263)
- **propagation** `StoreApp/domains/stores/services/domains.py:21` — public_domain/check_domain/serialize_domain: public_domain() -> settings.PUBLIC_DOMAIN -> CNAME verification target (line 74), UI instructions and tls-ask trust chain (line 124 cname_target)
- **sink** `docker/web/templates/default.conf.template:59` — apex vhost: nginx apex server 301s to www.${PLATFORM_DOMAIN} — opposite canonical direction to Django's www->apex when PUBLIC_DOMAIN coincides with PLATFORM_DOMAIN

Blockers:
- Actual PLATFORM_DOMAIN, PUBLIC_DOMAIN, ALLOWED_HOSTS and FRONTEND_URL values in the VPS .env are not source-visible; PUBLIC_DOMAIN's absence from the allowlist means it cannot be set via compose regardless, but whether the resulting hardcoded 'davent.com.ar' coincides with the live domain determines the impact.
- Which deployment(s) actually serve production traffic for davent.com vs davent.com.ar is not source-visible (both compose/VPS and Render blueprint exist).
- Whether Render permits dashboard-only env vars not declared in render.yaml (which could still set PUBLIC_DOMAIN there) is a platform behavior, not source-verifiable.

Local next step: Run `docker compose config` with a test .env to confirm PUBLIC_DOMAIN is absent from the rendered api environment; run `python -c` with DJANGO_SETTINGS_MODULE to print settings.PUBLIC_DOMAIN with the env unset -> 'davent.com.ar'.
Owner-observed deployment check: On the VPS: grep '^PLATFORM_DOMAIN\|^PUBLIC_DOMAIN\|^ALLOWED_HOSTS\|^FRONTEND_URL' /opt/davent/.env; curl -sI https://<apex>/ and https://www.<apex>/ observing 301 targets for a loop (apex->www by nginx vs www->apex by Django); in a store-owner session check the 'cname_target' value returned by GET /api/stores/domain/ and whether it matches the platform's real domain. On Render: check the service's environment for a dashboard-set PUBLIC_DOMAIN.

## Store MP webhook and public order-pay inherit the default anonymous throttles — shared Mercado Pago egress IPs may starve legitimate payment notifications

Fingerprint: `storepayments:webhook-default-throttle-starvation`

StoreMpWebhookView (POST /api/webhooks/store-mp/<slug>/) declares permission_classes=[AllowAny] and authentication_classes=[] but no throttle_classes, so DRF uses DEFAULT_THROTTLE_CLASSES = ResilientAnonRateThrottle + ResilientUserRateThrottle (settings.py:75-78). With no authentication, request.user is AnonymousUser: AnonRateThrottle keys throttle_anon_<ident> at 100/day and UserRateThrottle also applies to anonymous requests under throttle_user_<ident> at 1000/day (venv throttling.py:173-202). DaventProject.throttling pins REMOTE_ADDR into the ident (throttling.py:14-27,87-88), but neither default key has a per-view component, so every default-throttled anonymous endpoint shares the same cache key per cache backend/process. The platform MP webhook /api/payments/webhook/ is another AllowAny/default-throttled MP consumer (AdminApp/domains/payments/views/viewset_config.py:66-70), so store and subscription webhook traffic from the same provider egress IPs can share the anon bucket. If MP egress IPs are few and aggregate webhook volume from one IP exceeds the applicable anon cap, later legitimate signed notifications receive HTTP 429 in APIView.initial before HMAC verification, dedup, or StoreMpWebhookQuery run. PublicOrderPayView has the same default-throttle exposure for buyer IPs. Whether starvation occurs depends on MP egress IP distribution/volume, MP retry-on-429 behavior, the active deployment/cache topology, and cache health; none are fully source-visible.

Claimed root cause: StoreMpWebhookView and PublicOrderPayView omit throttle_classes, so they inherit DRF DEFAULT_THROTTLE_CLASSES; for anonymous requests the anon scope enforces 100/day per pinned client IP in a cache key shared by every default-throttled endpoint (with a separate user scope adding a 1000/day IP-keyed bucket), and MP webhook egress IPs may be shared provider infrastructure — aggregate webhook volume from one egress IP can exceed the anon cap and 429 legitimate payment notifications before signature verification.

Trace:
- **entrypoint** `StoreApp/domains/storepayments/views/webhook.py:114` — StoreMpWebhookView.post: POST /api/webhooks/store-mp/<slug>/ — permission_classes=[AllowAny] (line 110), authentication_classes=[] (line 113), and no throttle_classes on the class, so APIView.throttle_classes falls back to DEFAULT_THROTTLE_CLASSES.
- **propagation** `DaventProject/settings.py:75` — REST_FRAMEWORK DEFAULT_THROTTLE_CLASSES/RATES: DEFAULT_THROTTLE_CLASSES = [ResilientAnonRateThrottle, ResilientUserRateThrottle]; DEFAULT_THROTTLE_RATES sets anon=100/day (line 80) and user=1000/day (line 81).
- **propagation** `venv/Lib/site-packages/rest_framework/throttling.py:173` — AnonRateThrottle.get_cache_key / UserRateThrottle.get_cache_key: AnonRateThrottle returns None only for authenticated users and otherwise keys throttle_anon_<ident> (177-180); UserRateThrottle does not skip anonymous requests — it keys throttle_user_<ident> by IP for unauthenticated callers (193-202).
- **propagation** `DaventProject/throttling.py:87` — _ResilientThrottleMixin.get_ident/allow_request: Resilient wrappers keep DRF get_cache_key but pin REMOTE_ADDR into the ident via _pinned_ident (14-27); allow_request/wait fail open on cache exceptions (73-85). The resulting keys still have no view/action component.
- **propagation** `DaventProject/settings.py:409` — REDIS_URL/CACHES: REDIS_URL selects shared RedisCache for throttling; without it Django locmem is per process. render.yaml declares no REDIS_URL and sets GUNICORN_WORKERS=2, while docker-compose derives REDIS_URL with 3 workers — so whether the anon key is one platform-wide bucket or one bucket per worker is deployment-dependent.
- **sink** `venv/Lib/site-packages/rest_framework/views.py:421` — APIView.initial: perform_authentication -> check_permissions -> check_throttles run before dispatch to the handler; a failed throttle raises 429 before StoreMpWebhookView.post body-size/store lookup/HMAC/dedup logic (webhook.py:114-183).

Blockers:
- MP webhook egress IP count/distribution and aggregate daily notification volume across ALL DAVENT store webhooks plus the platform /api/payments/webhook/ consumer are provider/runtime facts not in source; starvation requires the anon cap (100 per rolling day per pinned ident per cache backend/process) to be exceeded by deliveries from one egress IP, including any other anonymous traffic sharing that IP.
- MP's retry behavior on HTTP 429 (retry count, backoff schedule, maximum retry age) is provider-side and not documented in the repo — it determines whether throttling merely delays confirmations or permanently drops them after retry exhaustion.
- The active deployment is not fully source-visible: docker-compose uses shared Redis and nginx (only /api/token/ has limit_req), while render.yaml declares no REDIS_URL (locmem) and GUNICORN_WORKERS=2; locmem makes the anon cap per worker rather than platform-wide, and any edge/WAF rate limiting in the live path cannot be confirmed from source.
- Resilient throttles fail open on cache exceptions — whether the anon/user buckets are enforced depends on cache backend health/availability (locmem always 'works' but is per-process).

Local next step: In a test deployment with a working cache, clear the cache and send 101 POSTs to /api/webhooks/store-mp/<slug>/ from one REMOTE_ADDR/XFF pair (invalid body is fine; the throttle precedes HMAC) and confirm the 101st returns 429; then alternate requests across the store webhook, /api/payments/webhook/, and PublicOrderPayView from the same ident to prove they share throttle_anon_<ident>, and inspect cache keys to confirm the separate throttle_user_<ident> 1000/day bucket also increments. Repeat with cache.get/set raising to confirm fail-open. For locmem multi-worker behavior, run two processes and show each has an independent 100/day bucket.
Owner-observed deployment check: Identify the live deployment (compose Redis vs Render locmem) and inspect owner-side production access logs and the MP developer panel for webhook delivery counts per day and source IPs for both /api/webhooks/store-mp/*/ and /api/payments/webhook/; determine whether any single egress IP exceeds the applicable anon cap (100/day under a shared cache, or ~100/day per worker under locmem) and check MP documentation/support for retry-on-429 semantics and horizon. Do not send audit traffic to production; use owner-observed logs/panel data.
