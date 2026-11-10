# Security Audit Report — DaventSaaS ecommerce (run-1)

- **Profile:** `standard` (full 6-phase workflow)
- **Scope:** `diff main...ECCOMMERCE-ADD (ecommerce module: customers, cart, orders, memberships, storepayments, legalpages, support, storeadmin + touched stores/catalog/design/notifications)`
- **Source ref:** `7f239dfbcfdbe401be3d03e1582e25c1769177e8` (`ECCOMMERCE-ADD`)
- **Execution:** sandboxed source-and-local-only — no deployed endpoints, no live identities, no real secrets, no shared infrastructure probed.
- **Budget:** none set (standard profile).
- **Prior runs:** none (`prior_run_paths` empty).
- **Companions:** WEB-PROTOCOL-AND-AUTH.md, DATA-ISOLATION-AND-LIFECYCLE.md, CLIENT-SIDE.md, PROTOCOLS-RPC-AND-MESSAGING.md

## Posture summary

El módulo e-commerce nuevo (8 dominios + frontend) se auditó completo: 9 vulnerabilidades confirmadas (todas corregidas en la misma rama), 1 lead que requiere un dato del proveedor/despliegue para cerrarse, y 5 candidatos refutados post-fix (la remediación ya estaba aplicada cuando el verificador final revisó el árbol). La postura general es sana: secretos de vendedor write-only, webhooks MP con HMAC + scoping por tienda, PII de compradores cifrada, aislamiento de tenants por store en todos los endpoints revisados. Los hallazgos concentrados fueron de ciclo de vida de sesión/PII del comprador y de superficies públicas anti-abuso.

## Confirmed findings

| Severity | Finding | Boundary | Observed result |
|---|---|---|---|
| HIGH | `customers:google-login-prehijack-unverified-account` — Google login links victim into attacker-pre-registered customer account, preserving the attacker-set password | StoreApp/domains/customers/views/auth_views.py (CustomerRegisterView.post) | Source-verified: register creates an unverified active account and returns a session, password auth ignores email_verified, Google link p... |
| HIGH | `storepayments:webhook-refund-requires-paid-status` — MP refund/chargeback webhook never marks the order REFUNDED — paid orders persist as PACKING | StoreApp/domains/storepayments/views/webhook.py (StoreMpWebhookView.post) | Source-verified and independently confirmed: mark_order_paid commits PACKING (test-asserted), the webhook refund gate requires the never-... |
| MEDIUM | `customers:session-establishing-endpoints-missing-origin-check` — Cross-site POST can bind the victim's browser to an attacker's customer session (login CSRF) | StoreApp/domains/customers/views/auth_views.py (CustomerLoginView.post) | Source-verified and independently confirmed: no origin/CSRF check on cookie issuance; DRF accepts form posts; CsrfViewMiddleware bypassed... |
| MEDIUM | `design:pattern-render-exclusive-products-leak` — Exclusive (member-only) products leak name, description, price, image and ID through the anonymous pattern document | StoreApp/domains/stores/views/viewset.py (StoreViewSet.public_pattern_document / public_pattern) | Source-verified and independently confirmed with a bounded local queryset check: the pattern queryset lacks the is_exclusive predicate wh... |
| MEDIUM | `frontend:customer-logout-no-epoch-invalidation` — Customer logout never invalidates the refresh epoch — an in-flight or failed logout can leave the buyer session recoverable | frontend/src/stores/customer.store.js (logout()) | Source-verified: refreshCall's guard cannot observe customer.store.logout() (sessionEnded never set, epoch never bumped), so customerToke... |
| MEDIUM | `stores:storage-byo-endpoint-blind-ssrf` — Owner-controlled R2 endpoint URL is fetched server-side by boto3 — blind SSRF into internal network | StoreApp/domains/storepayments/views/integrations.py (StorageConfigView.put) | Source-verified and independently confirmed: no host allowlist in validation or client construction; server-side PUT/DELETE to the arbitr... |
| MEDIUM | `support:per-message-owner-email-spam` — Any registered customer can email-bomb a store owner: one Celery email per support message, no per-store cap or opt-out | StoreApp/domains/support/views/customer.py (CustomerSupportMessageCreateView.post) | Source-verified by hunter and orchestrator: every accepted customer message deterministically produces one in-app notification upsert and... |
| LOW | `customers:logout-access-token-survives-12h` — Customer logout blacklists only the refresh token — Bearer access tokens remain valid up to 12h in other tabs/clients | StoreApp/domains/customers/views/auth_views.py (CustomerLogoutView.post) | Source-verified and independently confirmed: logout never touches tokens_valid_after; access JWTs remain valid for CUSTOMER_ACCESS_LIFETI... |
| LOW | `memberships:public-plans-payment-pii` — Anonymous membership-plans endpoint exposes raw merchant payment data that other public surfaces deliberately hide | StoreApp/domains/memberships/views/public.py (PublicStorePlansView.get) | Source-verified and independently confirmed: raw payment fields returned anonymously, contradicting the endpoint's own docstring and the ... |

### Detail

#### [HIGH] Google login links victim into attacker-pre-registered customer account, preserving the attacker-set password

`customers:google-login-prehijack-unverified-account`

**Root cause:** google_customer_login() treats a Google-verified email as proof of ownership of the existing account without checking who set the account's usable password or revoking sessions already issued; combined with register allowing unverified emails and password auth ignoring email_verified, the pre-registrant's credential and registration-time session survive the link.

**Intended behavior:** When a federated identity links to an existing local account, prior credentials and sessions must be re-proven or invalidated: either require the existing password, or — since Google just proved email ownership — invalidate any usable password (set_unusable_password), seal tokens_valid_after, and notify the account email so only the verified owner retains access.

**Trace:**

- `entrypoint` `StoreApp/domains/customers/views/auth_views.py:183` (CustomerRegisterView.post): AllowAny POST /api/customer-auth/register/ creates active Customer with caller-chosen password, email_verified=False; only a best-effort verification mail is queued.
- `propagation` `StoreApp/domains/customers/views/auth_views.py:443` (CustomerGoogleAuthView.post): AllowAny POST /api/customer-auth/google/ {credential, store_slug}; verifies Google token then calls google_customer_login and _session_response.
- `propagation` `StoreApp/domains/customers/services/google.py:126` (google_customer_login): Customer.objects.filter(email=email).first() finds the attacker-created account by email alone.
- `propagation` `StoreApp/domains/customers/services/google.py:145` (google_customer_login existing-customer branch): Updates only email_verified/email_verified_at/first_name/last_name; password untouched, tokens_valid_after untouched, no notification, no step-up.
- `sink` `StoreApp/domains/customers/services/customers.py:117` (authenticate_customer): Password login checks only check_password — email_verified never consulted; attacker retains a valid credential for the victim's account.

**Conditions:**
- *authentication_level*: Attacker needs only an anonymous register call with the victim's email before the victim's first DAVENT signup; victim must later choose 'Login with Google' on a store with Google login enabled.
- *data_state*: Attacker's pre-registered Customer must exist before the victim's first Google sign-in; customer accounts are global across stores.
- *system_configuration*: Target store must have StoreOAuthConfig enabled and resolve a Google client ID (its own google_client_id or the central GOOGLE_CLIENT_ID); register throttle is 10/hour/IP.

**Reproduction (target-neutral):** Anonymous internet user who knows the victim's email address

1. Attacker registers the victim's email with a password of their choice (store_slug optional) before the victim ever signs up; the register response already issues access/refresh credentials.
2. Victim signs in via Google on any store with Google login enabled; google_customer_login links the Google identity to the pre-existing account and issues the victim a session.
3. Attacker logs in with the still-valid password (or reuses the registration session) and receives a full customer session for the victim's account — orders, addresses, phone/document PII, memberships across all stores.

**Observed:** Source-verified: register creates an unverified active account and returns a session, password auth ignores email_verified, Google link preserves password and does not seal tokens_valid_after; after the victim's Google login both parties can hold valid sessions for the same Customer and the attacker retains durable silent access to orders, addresses and PII until a victim-initiated reset.

**Severity:** likelihood=medium (Requires only knowing a victim email, pre-registering before their first signup, and the victim later choosing Google sign-in — a common consumer flow; pre-registration is anonymous, throttled 10/hour per IP, and mass pre-hijacking is feasible with IP rotation.); impact=high (Durable unauthorized access to a buyer account: order history, addresses, phone/document PII, membership benefits across all stores; silent (no notification), and registration already issues the attacker refresh credentials.); overall=high.

**Confidence:** high — Complete source trace independently verified: register lacks verification and returns a session, password auth ignores email_verified, Google link preserves password and does not seal tokens_valid_after; only standard account-takeover preconditions are environmental.

**Remediation:** On federated link to an existing account, treat the provider-verified email as proof of mailbox ownership but not of the existing password: if is_password_usable(customer.password), call set_unusable_password(), seal tokens_valid_after at the current second boundary (JWT iat has one-second granularity) to revoke sessions already issued to the pre-registrant, persist, and send a security-notification email; alternatively require the existing password as step-up before linking. Independently, consider gating password login or checkout benefits on email_verified so unverified registrations carry less authority.

---

#### [HIGH] MP refund/chargeback webhook never marks the order REFUNDED — paid orders persist as PACKING

`storepayments:webhook-refund-requires-paid-status`

**Root cause:** services/webhook.py gates mark_refunded on order_status == 'PAID', a state that is never persisted because orders/services/payments.py mark_order_paid auto-advances PAID→PACKING within the same atomic block.

**Intended behavior:** An authenticated MP notification reporting status refunded/charged_back for a payment that credited an order should move that order to REFUNDED whenever Order.TRANSITIONS permits (PAID/PACKING/SHIPPED), mirroring the owner refund endpoint which already accepts those states.

**Trace:**

- `entrypoint` `StoreApp/domains/storepayments/views/webhook.py:175` (StoreMpWebhookView.post): Authenticated (per-store HMAC) MP notification with topic=='payment' dispatches StoreMpWebhookQuery(store, resource_id).
- `propagation` `StoreApp/domains/storepayments/services/webhook.py:198` (StoreMpWebhookQuery): order_status is read from the order instance; for any MP-paid order this is 'PACKING' (or SHIPPED/DELIVERED), never 'PAID'.
- `propagation` `StoreApp/domains/storepayments/services/webhook.py:222` (StoreMpWebhookQuery): elif mp_status in MP_STATUS_REFUNDED: mark_refunded is only invoked when order_status == 'PAID' — condition never true for real orders.
- `sink` `StoreApp/domains/orders/services/payments.py:156` (mark_order_paid): _apply_status(locked, Order.Status.PACKING) commits every paid order as PACKING in the same transaction that set PAID — PAID is transient and never observable.

**Conditions:**
- *data_state*: Order was paid via Mercado Pago (status ends at PACKING+) and MP later emits a payment notification with status 'refunded' or 'charged_back'.
- *third_party_dependency*: Genuine MP webhook delivery with valid per-store HMAC signature; no forgery needed — the defect triggers on legitimate refund/chargeback events.

**Reproduction (target-neutral):** Not an attacker action per se: any buyer-initiated MP refund, seller refund issued directly in the MP panel, or chargeback produces a legitimate signed webhook that the platform mishandles. A malicious buyer can also intentionally open a chargeback/dispute after receiving goods.

1. Create an order with payment_method='mp' and take it to PAID via the MP webhook (order commits as PACKING).
2. In MP (or via chargeback), refund/charge back that payment so MP emits a payment notification.
3. Deliver the signed webhook to /api/webhooks/store-mp/<slug>/?data.id=<payment_id>&type=payment.
4. Observe: MpPayment.status becomes 'refunded' but Order.status remains 'PACKING'/'SHIPPED' and no OrderEvent is created.

**Observed:** Source-verified and independently confirmed: mark_order_paid commits PACKING (test-asserted), the webhook refund gate requires the never-persisted 'PAID', mark_order_refunded has no hidden PAID-only gate, and no other path propagates MP refunds to Order.

**Severity:** likelihood=medium (Requires an MP-side refund or chargeback on an MP-paid order — a routine e-commerce event, but not present on every order.); impact=high (Systematic failure for 100% of MP-side refunds: seller can ship refunded goods, order panel shows no refund signal, and sales metrics count returned money as revenue.); overall=high.

**Confidence:** high — Complete source trace independently verified: PAID provably never a committed order state, the refund branch unreachable, the identical defect already acknowledged and fixed in refunds.py.

**Remediation:** Replace the literal 'PAID' check with the set of states Order.TRANSITIONS allows to reach REFUNDED (PAID/PACKING/SHIPPED), mirroring refunds.py. Consider re-fetching/locking the Order row inside the atomic block, and evaluate whether DELIVERED should also reach REFUNDED (requires a TRANSITIONS change). Fix the webhook test to use a realistic persisted state (PACKING).

---

#### [MEDIUM] Cross-site POST can bind the victim's browser to an attacker's customer session (login CSRF)

`customers:session-establishing-endpoints-missing-origin-check`

**Root cause:** Session-establishing endpoints mint ambient cookie credentials without any request-origin binding or pre-auth CSRF token; the double-submit check exists only on the refresh/logout consumers of those cookies, not on their issuers.

**Intended behavior:** State-changing endpoints that establish an ambient session should reject cross-site requests — e.g., validate Origin/Referer against an allowlist of storefront origins, or require a pre-login CSRF token issued by a GET endpoint, matching the protection already applied to cookie-authenticated mutations.

**Trace:**

- `entrypoint` `StoreApp/domains/customers/views/auth_views.py:209` (CustomerLoginView.post): AllowAny POST accepting email/password/store_slug; identical exposure on register (:183) and google (:432).
- `propagation` `StoreApp/domains/customers/serializers/serializers.py:138` (CustomerLoginSerializer): Plain Serializer fields — no origin/session binding; DRF default parsers accept form-encoded POST bodies.
- `propagation` `StoreApp/domains/customers/views/auth_views.py:250` (_require_csrf call sites): Double-submit enforced only inside refresh (from_cookie) and logout — never on the endpoints that issue the cookies.
- `sink` `StoreApp/domains/customers/views/auth_views.py:108` (_session_response): Sets customer_refresh (HttpOnly, Path=/api/, SameSite=Lax) and customer_csrf cookies on the response with no prior Origin/CSRF validation.

**Conditions:**
- *user_interaction*: Victim must load an attacker-controlled page (link, ad, embedded frame) while the storefront is reachable.
- *network_routing*: API and storefront share a site context where the API-domain cookies are sent on subsequent /api/ calls (path-alias apex mode amplifies to all stores; subdomain mode scopes per store host).

**Reproduction (target-neutral):** Remote web attacker who controls a page the victim visits

1. Host a page that auto-submits a cross-site form POST to the customer login endpoint with the attacker's own credentials.
2. Victim's browser receives 200 + Set-Cookie customer_refresh/customer_csrf for the attacker's account.
3. Victim uses the store normally; their refresh flow yields the attacker's session and their orders/PII accumulate in the attacker's account.

**Observed:** Source-verified and independently confirmed: no origin/CSRF check on cookie issuance; DRF accepts form posts; CsrfViewMiddleware bypassed by csrf_exempt; victim's browser holds an authenticated customer session belonging to the attacker.

**Severity:** likelihood=medium (Requires only a victim page-view; no credentials or tokens needed — the attacker uses their own account.); impact=medium (Silent account swap exposes the victim's order PII (addresses, phone, document) to the attacker and misattributes purchases; bounded to buyer accounts, no money movement by DAVENT.); overall=medium.

**Confidence:** high — Independently verified: no origin/CSRF check on cookie issuance, csrf_exempt confirmed in DRF source, form parsers accepted, no middleware mitigation; residual assumption is standard browser Set-Cookie behavior on cross-site POST.

**Remediation:** Bind session establishment to the request origin: reject register/login/google (and any future cookie-issuing endpoint, including the parallel DAVENT user auth) when the Origin/Referer header is present and not in an allowlist of configured storefront origins, or issue a pre-auth CSRF cookie via a same-site GET and require it on login. JSON-only enforcement is a weaker partial mitigation since fetch can still send simple requests.

---

#### [MEDIUM] Exclusive (member-only) products leak name, description, price, image and ID through the anonymous pattern document

`design:pattern-render-exclusive-products-leak`

**Root cause:** pattern_render.py builds public product fragments with Product.objects.filter(store=store, is_active=True) at three sites — _product_fragment default queryset (line 283), _related_fragment base queryset (line 856) and render_store_pattern products_total (line 1624) — none of which include is_exclusive=False, while every other anonymous read path in the codebase applies that predicate.

**Intended behavior:** is_exclusive products must be invisible to non-members on every public read path, including pattern documents — the public catalog comment states the rule explicitly: 'para el resto ni siquiera se sabe que existen' (viewset.py:905-909). The anonymous ?product= resolver already encodes the same intent (viewset.py:663-668).

**Trace:**

- `entrypoint` `StoreApp/domains/stores/views/viewset.py:710` (StoreViewSet.public_pattern_document / public_pattern): Anonymous GET /api/stores/public/<slug>/pattern/document/ and /pattern — PUBLIC_ACTIONS, AllowAny; gated only by _pattern_store (published, not blocked, has_public_link). No member authentication anywhere on this path.
- `propagation` `StoreApp/domains/design/services/pattern_render.py:1565` (render_store_pattern → build_store_context / _product_values): needed = VAR_RE.findall(pattern.html) selects which raw fragments to build; builders['products'] and product_raw['product_related'] are populated whenever the pattern markup declares {{products}}/{{product_related}} — 21 shipped sources do.
- `propagation` `StoreApp/domains/design/services/pattern_render.py:283` (_product_fragment default queryset → card markup): Product.objects.filter(store=store, is_active=True)[:FRAGMENT_LIMIT=24] — missing is_exclusive=False. Each card emits escaped name, 110-char description, effective price/offer, image URL, category, brand and data-ds-product=<pk> into anonymous HTML.
- `propagation` `StoreApp/domains/design/services/pattern_render.py:856` (_related_fragment base queryset): Related-product rail uses the same unfiltered base queryset (excludes only the current product pk), so up to 4 exclusive products render as 'related' cards on every public product page.
- `sink` `StoreApp/domains/design/services/pattern_render.py:1624` (render_store_pattern return payload 'products_total'): Product.objects.filter(store=store, is_active=True).count() includes exclusive products — discloses the total count via GET /pattern?meta=1.

**Conditions:**
- *data_state*: Store is_published=True, is_blocked=False, and the owner's plan includes the has_public_link benefit.
- *data_state*: Store's effective template resolves to a DesignPattern whose html declares {{products}} (landing/catalog) or {{product_related}} (product surface); 21 of the shipped pattern sources do.
- *data_state*: At least one Product with is_active=True and is_exclusive=True exists in that store.

**Reproduction (target-neutral):** Anonymous internet visitor with no account, no membership, and no special access — the same principal the public catalog already hides exclusive products from.

1. Issue the anonymous pattern document request for a store using a shipped HTML pattern.
2. The rendered HTML contains product cards for is_exclusive products (name, description, price, image, pk) that the public catalog JSON would never return.
3. GET /pattern?meta=1 additionally returns products_total including exclusive products.

**Observed:** Source-verified and independently confirmed with a bounded local queryset check: the pattern queryset lacks the is_exclusive predicate while the catalog queryset has it; anonymous entrypoints confirmed AllowAny; 21 shipped sources reference the vulnerable fragments.

**Severity:** likelihood=high (Anonymous, unauthenticated, default render path: any published design-pattern store with member-only products leaks them on every page view; no user interaction or special configuration beyond the store using a shipped pattern.); impact=medium (Confidentiality loss of member-only product catalog data (names, descriptions, prices/offers, images, categories, brands, product ids, total count) to the public — breaks the exclusivity access-control invariant. No integrity or availability impact; purchase remains blocked server-side.); overall=medium.

**Confidence:** high — Complete source trace from anonymous entrypoint to rendered sink, corroborated by a bounded local queryset check and explicit sibling-path filters documenting the intended invariant; independently verified.

**Remediation:** Apply the same is_exclusive=False predicate used by every other anonymous read path to all three pattern-render querysets, ideally via a single public-products helper so future fragments cannot drift; add a regression test asserting the anonymous pattern document/meta contains no exclusive product name, price or pk.

---

#### [MEDIUM] Customer logout never invalidates the refresh epoch — an in-flight or failed logout can leave the buyer session recoverable

`frontend:customer-logout-no-epoch-invalidation`

**Root cause:** customer.store.logout() bypasses the epoch/session-invalidation machinery: it does not call logoutCustomerSession() and performs no sessionEnded/sessionEpoch/clearSessionHints updates, so the refreshCall() staleness guard cannot detect that a logout occurred while a refresh was in flight or that the logout request failed before cookie cleanup.

**Intended behavior:** Explicit logout must invalidate the session epoch before/while the server logout is requested, unconditionally clear the readable session-hint cookies, and ensure no in-flight or subsequent refresh can re-arm the session — mirroring DAVENT's logoutSession() in frontend/src/api/http.js.

**Trace:**

- `entrypoint` `frontend/src/stores/customer.store.js:120` (logout()): awaits customerApi.logout() in try/catch, then clears accessToken.value, customerTokenStorage, customer/status/error refs; no epoch/sessionEnded/hint invalidation and no logoutCustomerSession() call.
- `propagation` `frontend/src/api/customer.http.js:143` (logoutCustomerSession()): sets sessionEnded=true, sessionEpoch++, awaits backend logout, then customerTokenStorage.clear() and clearSessionHints(); exported but has no callers in frontend/src.
- `propagation` `frontend/src/api/customer.http.js:95` (refreshCall()): stale-refresh guard only discards results when sessionEnded || epoch !== sessionEpoch; logout leaves both unchanged, so an in-flight refresh completes and calls customerTokenStorage.set(access).
- `sink` `frontend/src/stores/customer.store.js:45` (ensureSession() -> restoreCustomerSession()): store accessToken.value is null but customerTokenStorage.getAccess() is truthy, so restoreCustomerSession() returns true, accessToken.value is re-assigned, fetchMe() repopulates customer, and isAuthenticated becomes true again with a fresh 12h Bearer.

**Conditions:**
- *timing_dependency*: A refreshCall must be in flight when logout runs, or the logout request must fail before the backend clears cookies.
- *data_state*: A failed/non-2xx logout leaves the readable customer_csrf hint and, when the refresh credential remains valid, enables silent auto-restore on the next ensureSession().

**Reproduction (target-neutral):** Shared-device or session-hygiene scenario: a user clicks 'Salir' expecting the buyer session to end while an API 401-triggered refresh is in flight, or the logout request fails (network, CSRF, or stale Bearer). No external attacker input required.

1. Log in as a customer and let the access token expire or be revoked.
2. Trigger an authenticated action that produces a 401 so tryRefresh()/refreshCall() is in flight, then click Salir (StoreAccountView logout -> customer.logout) while the refresh POST is pending.
3. Alternatively, make the logout request fail before cookie cleanup and then trigger any ensureSession()-dependent action.
4. Observe whether the refresh response lands after logout/local clear and whether customer_csrf remains readable after a failed logout.

**Observed:** Source-verified: refreshCall's guard cannot observe customer.store.logout() (sessionEnded never set, epoch never bumped), so customerTokenStorage.set() can store the rotated access token and ensureSession()/restoreCustomerSession() re-adopts it, fetchMe() succeeds, and the UI returns to authenticated state; a late refresh Set-Cookie can also re-arm customer_refresh/customer_csrf. A logout request that fails before backend cookie cleanup leaves customer_csrf readable, so the next ensureSession() can silently restore via the still-valid refresh cookie.

**Severity:** likelihood=medium (Requires an in-flight refresh interleaving or a logout request failure (including stale-Bearer 401/CSRF/network) — plausible on flaky networks, expired sessions and shared devices, but not present on every logout.); impact=medium (Explicit logout can leave a recoverable buyer session: zombie 12h Bearer access token and/or re-armed 30-day refresh cookie, exposing order/address/profile data on shared devices. No remote attacker primitive.); overall=medium.

**Confidence:** high — Independently verified line-by-line: zero logoutCustomerSession call sites, missing epoch/sessionEnded/clearSessionHints invalidation in customer.store.logout(), the refreshCall stale-result guard, the ensureSession restore path, backend cookie re-arm on refresh, and the DAVENT logoutSession() contrast.

**Remediation:** Add logoutCustomerSession to the existing customer.http.js import in customer.store.js and make logout() await it instead of customerApi.logout(): the helper sets sessionEnded/sessionEpoch before the request, performs the backend logout without attaching the possibly-stale module Bearer, and clears token+hints even on failure. Then clear only the Pinia refs. Do not keep a second customerApi.logout() call and do not reference cartStore/localStorage cleanup inside the store (the caller already handles cart state).

---

#### [MEDIUM] Owner-controlled R2 endpoint URL is fetched server-side by boto3 — blind SSRF into internal network

`stores:storage-byo-endpoint-blind-ssrf`

**Root cause:** StoreStorageConfigSerializer.validate_endpoint accepts any https:// URL and storage._byo_backend/_client pass it verbatim as boto3 endpoint_url, making the server issue authenticated S3 requests to an arbitrary owner-chosen host with no egress restriction or host allowlist.

**Intended behavior:** Server-side outbound requests to owner-controlled endpoints should be restricted to known object-storage hosts (e.g., *.r2.cloudflarestorage.com, *.amazonaws.com, or an explicit owner-allowlist), or the feature should document and accept the SSRF trust assumption with egress controls at the network layer.

**Trace:**

- `entrypoint` `StoreApp/domains/storepayments/views/integrations.py:118` (StorageConfigView.put): Owner-authenticated PUT persists endpoint/bucket/credentials for their own store.
- `propagation` `StoreApp/domains/storepayments/serializers/serializers.py:256` (StoreStorageConfigSerializer.validate_endpoint): _clean_https_url only enforces https:// scheme (http only when settings.DEBUG) — no host allowlist.
- `propagation` `StoreApp/domains/stores/services/storage.py:153` (_byo_backend): Decrypts owner credentials and returns endpoint verbatim for any enabled+configured store.
- `sink` `StoreApp/domains/stores/services/storage.py:90` (_client): boto3.client('s3', endpoint_url=backend['endpoint'], ...) — server-side PUT/DELETE issued to the owner-controlled host on every store image operation.

**Conditions:**
- *authentication_level*: Authenticated store owner (DAVENT account with a store).
- *system_configuration*: BYO storage enabled with endpoint+bucket+credentials configured; production requires https endpoint.
- *environmental_dependency*: Impact depends on reachable internal HTTPS services that accept/act on SigV4-signed S3 PUT/DELETE requests — deployment-specific.

**Reproduction (target-neutral):** Authenticated store owner configuring their own BYO storage integration.

1. Configure StoreStorageConfig with an arbitrary https endpoint (e.g., an internal service address).
2. Trigger any image upload/delete for that store's keys.
3. The application server issues authenticated S3 PUT/DELETE requests to the chosen host; responses are discarded (blind).

**Observed:** Source-verified and independently confirmed: no host allowlist in validation or client construction; server-side PUT/DELETE to the arbitrary endpoint confirmed; blind because errors fall back silently and object_url uses local presigning.

**Severity:** likelihood=low (Requires an authenticated owner account plus internal network targets worth hitting; most deployments have limited internal HTTPS services accepting S3 verbs.); impact=medium (Blind request forgery with side effects (PUT/DELETE) against internal services and host probing; no data returned, no DAVENT secret disclosed (SigV4 uses owner's own creds).); overall=medium.

**Confidence:** high — Independently verified: owner-writable endpoint, no allowlist, verbatim boto3 endpoint_url, blind confirmed (local presigning, silent fallback). Upgraded from needs_validation — the missing control is source-certain.

**Remediation:** Allowlist the endpoint host: restrict to *.r2.cloudflarestorage.com, *.amazonaws.com, and known S3-compatible hosts (or an explicit env-configured allowlist), rejecting private/loopback/link-local addresses. Alternatively document the trust assumption and enforce egress rules at the network layer.

---

#### [MEDIUM] Any registered customer can email-bomb a store owner: one Celery email per support message, no per-store cap or opt-out

`support:per-message-owner-email-spam`

**Root cause:** post_message() treats every customer message as notification-worthy and enqueues a dedicated outbound email per message; the design assumed low-volume legitimate use and relied solely on a per-customer rate limit, with no store-side circuit breaker, per-store quota, membership precondition, or email batching/dedup.

**Intended behavior:** Support is a buyer<->owner channel: a store owner should receive a bounded, deduplicated stream of customer messages — e.g., per-store inbound rate limit, owner ability to disable support or block a sender, and/or digested/batched owner emails rather than one SMTP message per chat line.

**Trace:**

- `entrypoint` `StoreApp/domains/support/views/customer.py:164` (CustomerSupportMessageCreateView.post): Authenticated customer POSTs {body} to any own thread; throttle is only SupportMessageThrottle 60/hour keyed by customer.pk.
- `propagation` `StoreApp/domains/support/views/customer.py:117` (CustomerSupportThreadListCreateView.post): Creates thread against arbitrary published store slug (customer_visible_store checks only is_published/is_blocked — no membership, no support opt-out).
- `propagation` `StoreApp/domains/support/services/services.py:115` (post_message): On sender=CUSTOMER unconditionally calls notify_owner_message(thread, message) and enqueue_support_email(thread, message) for EVERY message.
- `propagation` `StoreApp/domains/support/services/services.py:190` (enqueue_support_email): Dispatches send_support_message_email.delay(message.pk) — one Celery task per message, no dedup key.
- `sink` `StoreApp/domains/support/services/services.py:215` (deliver_support_email): send_mail() to contact_target(store) — owner's contact_email or account email — body contains attacker-controlled subject/body text.

**Conditions:**
- *authentication_level*: Attacker holds any active customer JWT — free registration, email verification not required for API use.
- *data_state*: Target store is is_published=True and is_blocked=False (the normal state of every live merchant).
- *system_configuration*: Celery worker + SMTP configured (production posture); spam consumes platform mail quota/reputation.

**Reproduction (target-neutral):** Registered customer (optionally unverified email) targeting any merchant's public store slug.

1. Register a customer account via POST /api/customer-auth/register/ (no email verification needed to call the API).
2. Create one support thread against the victim store slug.
3. POST up to 60 messages/hour to that thread; each message enqueues a Celery task that emails the store owner's contact address.
4. Repeat across additional throwaway accounts (register is 10/hour/IP) or additional victim stores — there is no per-store aggregate cap and no owner-side block for non-members.

**Observed:** Source-verified by hunter and orchestrator: every accepted customer message deterministically produces one in-app notification upsert and one queued outbound email to the merchant; the only rate bound is per-customer (60/h) and fails open without cache. ~1,440 emails/day per account per store; unbounded thread/message rows.

**Severity:** likelihood=high (Trivial: one free registration + scripted POSTs; no CAPTCHA, no membership, no per-store cap; scales with disposable accounts.); impact=medium (Merchant inbox/email flooding at up to ~1,440 msgs/day/account, platform SMTP quota/reputation burn, unbounded DB row growth; owner has no recourse for non-member spammers.); overall=medium.

**Confidence:** high — Complete source lineage from endpoint to send_mail verified by hunter; orchestrator independently re-verified post_message→enqueue_support_email→deliver_support_email chain, throttle keying, missing membership/opt-out gates.

**Remediation:** Add store-side abuse controls: (1) per-store inbound message quota (e.g., N messages/hour across all customers, enforced in post_message under select_for_update or a cache counter keyed by store.pk); (2) batch/digest owner emails (e.g., one email per thread per X minutes, or notification-only with email on first message); (3) require StoreMembership (ensure_membership) or at least allow owners to suspend/block a customer independent of membership; (4) add a StoreCustomization show_support toggle checked in customer_visible_store/create_thread; (5) consider requiring verified email for support writes.

---

#### [LOW] Customer logout blacklists only the refresh token — Bearer access tokens remain valid up to 12h in other tabs/clients

`customers:logout-access-token-survives-12h`

**Root cause:** Logout performs refresh-token blacklisting only; the access-token revocation path (tokens_valid_after) is not invoked, and the 12h access lifetime makes the residual window large.

**Intended behavior:** Logout should invalidate the customer's session material comprehensively: either shorten access-token lifetime to match the owner pattern (minutes), blacklist outstanding access tokens, or bump tokens_valid_after accepting global sign-out semantics — documented as an accepted trade-off if intentional.

**Trace:**

- `entrypoint` `StoreApp/domains/customers/views/auth_views.py:294` (CustomerLogoutView.post): blacklists request.auth refresh token, deletes cookies, returns 200 — no tokens_valid_after update.
- `propagation` `StoreApp/domains/customers/authentication.py:70` (CustomerJWTAuthentication.authenticate): customer_session_valid() compares token iat vs tokens_valid_after; logout never moves the stamp so pre-logout access tokens still validate.
- `sink` `StoreApp/domains/customers/services/tokens.py:28` (CUSTOMER_ACCESS_LIFETIME): timedelta(hours=12) — revoked-by-logout sessions remain usable for up to 12h.

**Conditions:**
- *data_state*: Attacker must possess a pre-logout access token (XSS/malware capture, shared-device copy, or another open tab).
- *system_configuration*: Standard JWT deployment; CUSTOMER_ACCESS_LIFETIME not overridden.

**Reproduction (target-neutral):** Anyone holding a customer access JWT captured before logout (shared device, XSS, token leak).

1. Obtain a customer access token (e.g., from another tab or captured storage).
2. Victim logs out (refresh blacklisted, cookies cleared).
3. Use the still-valid access token for up to 12h against all customer endpoints.

**Observed:** Source-verified and independently confirmed: logout never touches tokens_valid_after; access JWTs remain valid for CUSTOMER_ACCESS_LIFETIME=12h post-logout.

**Severity:** likelihood=low (Requires prior access-token compromise; the token is not cookie-persisted and the revocable refresh credential IS killed at logout.); impact=low (Post-logout access to customer endpoints (orders, addresses, profile) for up to 12h — bounded session persistence gap, systemic JWT trade-off.); overall=low.

**Confidence:** high — Independently verified: logout blacklists refresh only, tokens_valid_after sole writer is password-reset, 12h lifetime confirmed, systemic parity with owner session noted.

**Remediation:** Options in increasing strength: (a) shorten CUSTOMER_ACCESS_LIFETIME to minutes (matching the owner pattern) so the residual window is negligible; (b) bump tokens_valid_after on logout accepting global sign-out (simplest, matches password-reset semantics); (c) blacklist access tokens via OutstandingToken jti. Document whichever trade-off is chosen.

---

#### [LOW] Anonymous membership-plans endpoint exposes raw merchant payment data that other public surfaces deliberately hide

`memberships:public-plans-payment-pii`

**Root cause:** _payment_instructions() was reused verbatim for the anonymous public plans payload instead of a flags-only variant; the privacy-by-redirect and post-order-gating precedents for the same fields were not carried over, and the endpoint's own docstring contradicts the implementation.

**Intended behavior:** The anonymous plans endpoint should return only method flags (accept_*, mp_enabled, mp_connected, deadline_hours) needed for the subscribe/checkout CTA decision; raw payment instructions (alias, holder, WhatsApp number, transfer_instructions) should be gated behind customer auth — the authenticated subscribe response already returns 'payment'.

**Trace:**

- `entrypoint` `StoreApp/domains/memberships/views/public.py:37` (PublicStorePlansView.get): permission_classes=[] / authentication_classes=[] (AllowAny-equivalent), PublicReadThrottle — fully anonymous.
- `propagation` `StoreApp/domains/memberships/views/customer.py:76` (_payment_instructions): Returns transfer_alias, transfer_holder, transfer_instructions, whatsapp_number, accept_* flags, mp_enabled, mp_connected, deadline_hours — raw values, not flags.
- `sink` `StoreApp/domains/memberships/views/public.py:47` (PublicStorePlansView.get): 'payments': _payment_instructions(store) included in the Response returned to any anonymous visitor.

**Conditions:**
- *authentication_level*: None — fully anonymous endpoint.
- *data_state*: Store has active membership plans and a populated StorePaymentConfig (raw fields empty otherwise, though flags still leak config defaults).

**Reproduction (target-neutral):** Anonymous scraper enumerating store slugs.

1. Request the public membership-plans endpoint for any store slug.
2. The 'payments' object contains whatsapp_number, transfer_alias, transfer_holder, transfer_instructions in cleartext.

**Observed:** Source-verified and independently confirmed: raw payment fields returned anonymously, contradicting the endpoint's own docstring and the /r/ anti-harvesting design; frontend needs only flags pre-auth. Additionally verified: StoreCheckoutView.vue consumes the same anonymous payments payload for order-checkout method selection (flags only), and PlanSubscribe.vue:58 prefers props.payments over result.payment — both facts constrain the remediation.

**Severity:** likelihood=medium (Trivially enumerable by any anonymous scraper across all store slugs, though actual sensitive values require the owner to have populated StorePaymentConfig.); impact=low (Exposes owner payment destination data (bank alias/CVU/CBU, account holder name, WhatsApp number) — non-credential, AR-commerce-normal, but bypasses the platform's deliberate anti-harvesting posture and the endpoint's own documented contract.); overall=low.

**Confidence:** high — Independently verified line-by-line: raw fields confirmed in payload, docstring contradiction confirmed verbatim, frontend flag-only pre-auth usage confirmed (PlanSubscribe + StoreCheckoutView), sibling /r/ redirect and post-order tracking_token gating contrasts confirmed, route registration confirmed. Original remediation whitelist corrected ('accept_mp' nonexistent; accept_cash/mp_enabled required by consumers; PlanSubscribe props.payments preference must be reordered).

**Remediation:** Restrict 'payments' in PublicStorePlansView to exactly the flag keys the storefront consumes — accept_transfer, accept_whatsapp, accept_cash, mp_enabled, mp_connected, deadline_hours (accept_cash and mp_connected are REQUIRED: PlanSubscribe.vue:40 and StoreCheckoutView.vue:80-81 read them to offer cash/MP; 'accept_mp' is not a real _payment_instructions key). This drops only transfer_alias, transfer_holder, transfer_instructions, whatsapp_number. Then fix PlanSubscribe.vue instructionsFor to prefer the authenticated subscribe response's payment over the now flags-only public payload, so post-subscribe instructions still render alias/holder. Update the module docstring/frontend contract comments accordingly.

---

## Needs validation

Leads source-grounded cuyo cierre depende de un hecho del proveedor MP o del despliegue. No son vulnerabilidades confirmadas; cada uno trae su plan acotado (ver `NEEDS-VALIDATION.md`).

| Lead | Boundary | Blocker |
|---|---|---|
| `storepayments:mp-refund-check-then-act-toctou` — MP refund endpoint locks the order row before the refund call (concurrent TOCTOU fixed), but an ambiguous MP outcome lets a retry issue a second refund POST — dedup is provider-side | StoreApp/domains/storepayments/views/mp.py (MpRefundView.post) | Whether Mercado Pago's POST /v1/payments/<id>/refunds is idempotent or rejects a second total refund for the same payment_id when the first attempt's outcome wa |

## Rejected candidates (post-fix verification)

- `customers:profile-pii-hash-unique-oracle` — Already remediated in current source: migration 0002 removes unique=True from Customer.phone_hash and Customer.document_hash, and the model declares both without uniqueness with an explicit comment citing this audit finding. Every other element verified accurate, but the sink — the DB unique constra
- `orders:mails-unverified-customer-email-recipient` — Claim was VALID against the audited source: deliver_order_event_email resolved the buyer recipient from the unverified Customer.email snapshot with no verification gate. Independent verification ran against the working tree AFTER the remediation phase and found the sink already closed: deliver_order
- `orders:public-receipt-buyer-pii` — Claim was VALID against the audited source, but Phase-5 verification against the current working tree found the sink already closed: build_receipt_payload's 'customer' block was stripped to first_name only — exactly the prescribed remediation, documented inline. The endpoint remains public but no lo
- `storepayments:webhook-approved-amount-none-failopen` — Fixed in current source. The claimed fail-open no longer exists: amount=None/order_total=None are explicit mismatch conditions that set amount_mismatch + OrderEvent and skip mark_paid; credit requires exact amount == order.total. The residual provider question is no longer security-relevant because 
- `stores:captcha-single-use-failopen-toctou` — Claim was VALID against the audited source: verify_captcha used the fail-open cache helpers and wrote the used-marker with cache_set only after a correct answer (TOCTOU window + replay collapse on cache outage). Independent verification ran against the working tree AFTER the remediation phase and fo

## Hardening notes

- `PublicOrderCreateView` acepta compradores con `email_verified=False` (hoy inofensivo porque todo lifecycle mail está gateado; considerar exigir verificación o magic-link en checkout como defensa en profundidad).
- Los throttles con cache fail-open (`_ResilientThrottleMixin`) están bien para UX pero conviene revisar scopes de auth/register en producción con Redis obligatorio (`check --deploy` ya lo exige para throttles?).
- `membership_expiry_notices` corre por cron — verificar que esté agendado en el VPS (no figura en MIGRATION_VPS.md).
- Considerar `tokens_valid_after` también en "cerrar otras sesiones" de perfil (hoy solo password-reset/google-link lo sellan).
- El access token de comprador ahora es 30 min; si en el futuro hay clientes API móviles de larga sesión, evaluar refresh token rotation por dispositivo.

## Positive source patterns

- Webhook MP: HMAC `compare_digest` + ventana de timestamp + `data.id` solo del query firmado + scope por tienda + idempotencia por `mp_payment_id` unique + `select_for_update`.
- Secretos de vendedor (MP/OAuth/R2) write-only, cifrados en vault con AAD por tienda, nunca devueltos por serializers.
- PII de `Customer` cifrada en reposo con huellas HMAC para igualdad (sin constraint unique que filtre existencia).
- Emisión de sesión customer con Origin/Referer check, CSRF double-submit, cookies httpOnly/SameSite y refresh rotativo con blacklist.
- Revocación por época `tokens_valid_after` aplicada en reset de password y auto-link de Google.
- Documentos de patrón en iframe sandboxed sin `allow-same-origin`, CSP por nonce, `sanitize_markup` obligatorio.
- `normalize_image` (WebP) en todos los uploads; storage BYO resuelve credenciales por store sin exponerlas.
- Anti-enumeración en login/register/trackings y respuestas uniformes en endpoints públicos.

## Coverage summary

- Units: 18 — covered=18, candidate=0, blocked=0, deferred=0, out_of_scope=0
- Hunters: 7 (h1-h7) en 2 waves + recon 4 agentes; verifiers Phase 3+5 por candidato/final record.
- Critics: coverage ledger validado (`validate-coverage-ledger` PASS); findings validado (`validate-findings` PASS: 15 records).
- Deferred/out-of-scope: ninguno dentro del scope `main...ECCOMMERCE-ADD`; FASE 4 del plan (envíos, facturación automática) quedó fuera por diseño post-MVP.

## Disposición de remediación

Los confirmados fueron corregidos en `7d53e880` y `5c249b52` (pusheados a `ECCOMMERCE-ADD`) con tests de regresión; suite backend relevante verde (customers 45, orders+support+memberships+design+captcha 191, storepayments+notify+expiry 133). Los rejected post-fix documentan claims que eran reales en el ref auditado pero cuyo sink ya fue remediado durante la fase de fixes — se conservan para que futuras corridas no repitan el claim sin evidencia nueva.