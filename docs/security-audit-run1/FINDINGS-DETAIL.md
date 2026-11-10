# Findings detail — run-1 (confirmed medium+)

## [HIGH] Google login links victim into attacker-pre-registered customer account, preserving the attacker-set password

Fingerprint: `customers:google-login-prehijack-unverified-account`

Customer accounts are global and registration does not require email verification: POST /api/customer-auth/register/ creates an active Customer with any email plus a caller-chosen password (and returns a session), and password login (authenticate_customer) never checks email_verified. When the real owner later signs in with Google, google_customer_login() finds the existing Customer by the Google-verified email and issues a session — but the existing-customer branch only flips email_verified when needed and backfills names; it never invalidates the password that was set by whoever registered first, seals tokens_valid_after, or sends a security notification. An attacker who pre-registers the victim's email (before the victim's first DAVENT signup) therefore retains durable password/session access to the account the victim now uses: orders, shipping addresses, phone and document PII, and memberships are all readable, across every store. Preconditions: attacker registers before victim's first signup (email unique) and victim later uses Google login on a store whose StoreOAuthConfig resolves a Google client ID. Verifier correction: the hunter's 'force-reset to lock victim out' sub-claim is NOT supported — there is no authenticated change-password endpoint and a victim-initiated reset would actually revoke attacker sessions via tokens_valid_after; the attacker retains silent parallel access until/unless the victim resets. Registration does send a verification email to the victim (weak detection signal, not a mitigation).

### Trace
- **entrypoint** `StoreApp/domains/customers/views/auth_views.py:183` — CustomerRegisterView.post: AllowAny POST /api/customer-auth/register/ creates active Customer with caller-chosen password, email_verified=False; only a best-effort verification mail is queued.
- **propagation** `StoreApp/domains/customers/views/auth_views.py:443` — CustomerGoogleAuthView.post: AllowAny POST /api/customer-auth/google/ {credential, store_slug}; verifies Google token then calls google_customer_login and _session_response.
- **propagation** `StoreApp/domains/customers/services/google.py:126` — google_customer_login: Customer.objects.filter(email=email).first() finds the attacker-created account by email alone.
- **propagation** `StoreApp/domains/customers/services/google.py:145` — google_customer_login existing-customer branch: Updates only email_verified/email_verified_at/first_name/last_name; password untouched, tokens_valid_after untouched, no notification, no step-up.
- **sink** `StoreApp/domains/customers/services/customers.py:117` — authenticate_customer: Password login checks only check_password — email_verified never consulted; attacker retains a valid credential for the victim's account.

### Evidence
- `StoreApp/domains/customers/services/google.py:148` — Existing-customer link sets email_verified=True and fills names but never touches customer.password, customer.tokens_valid_after, or notifies the address.
- `StoreApp/domains/customers/services/customers.py:129` — authenticate_customer checks only password — email_verified is irrelevant to password login.
- `StoreApp/domains/customers/serializers/serializers.py:120` — Register rejects only duplicate emails; no verification gate before account activation.
- `StoreApp/domains/customers/authentication.py:67` — CustomerJWTAuthentication requires is_active and customer_session_valid (tokens_valid_after); email_verified is never consulted in any session path.
- `StoreApp/domains/customers/services/customers.py:284` — ConfirmCustomerPasswordResetQuery is the only path that would evict the attacker, and it requires the victim to notice and act.
- `StoreApp/domains/customers/views/auth_views.py:196` — Register returns _session_response, so the pre-registrant obtains customer access/refresh credentials immediately.

### Reproduction (target-neutral, local)
Attacker principal: Anonymous internet user who knows the victim's email address

- Payload/input: `POST /api/customer-auth/register/ {"email":"victim@example.com","password":"AttackerChosen!1"}`
- Payload/input: `(victim, later) POST /api/customer-auth/google/ {"credential":"<victim Google id_token>","store_slug":"tienda-x"}`
- Payload/input: `POST /api/customer-auth/login/ {"email":"victim@example.com","password":"AttackerChosen!1"}`

1. Attacker registers the victim's email with a password of their choice (store_slug optional) before the victim ever signs up; the register response already issues access/refresh credentials.
2. Victim signs in via Google on any store with Google login enabled; google_customer_login links the Google identity to the pre-existing account and issues the victim a session.
3. Attacker logs in with the still-valid password (or reuses the registration session) and receives a full customer session for the victim's account — orders, addresses, phone/document PII, memberships across all stores.

Observed: Source-verified: register creates an unverified active account and returns a session, password auth ignores email_verified, Google link preserves password and does not seal tokens_valid_after; after the victim's Google login both parties can hold valid sessions for the same Customer and the attacker retains durable silent access to orders, addresses and PII until a victim-initiated reset.

### Conditions
- authentication_level: Attacker needs only an anonymous register call with the victim's email before the victim's first DAVENT signup; victim must later choose 'Login with Google' on a store with Google login enabled.
- data_state: Attacker's pre-registered Customer must exist before the victim's first Google sign-in; customer accounts are global across stores.
- system_configuration: Target store must have StoreOAuthConfig enabled and resolve a Google client ID (its own google_client_id or the central GOOGLE_CLIENT_ID); register throttle is 10/hour/IP.

### Remediation
On federated link to an existing account, treat the provider-verified email as proof of mailbox ownership but not of the existing password: if is_password_usable(customer.password), call set_unusable_password(), seal tokens_valid_after at the current second boundary (JWT iat has one-second granularity) to revoke sessions already issued to the pre-registrant, persist, and send a security-notification email; alternatively require the existing password as step-up before linking. Independently, consider gating password login or checkout benefits on email_verified so unverified registrations carry less authority.
- {"file_name": "StoreApp/domains/customers/services/google.py", "fixed_code": "    else:\n        ensure_membership(customer, store)\n        update_fields   =   []\n        # Google proved mailbox ownership, not who chose the password\n        # already on the account. Kill any usable password and seal\n        # tokens_valid_after so sessions issued to the pre-registrant die.\n        # JWT iat has one-second granularity: seal at the current second\n        # boundary or the session minted after this returns is rejected.\n        # Customer has no has_usable_password(); ask Django's hasher.\n        from django.contrib.auth.hashers import is_password_usable\n        if is_password_usable(customer.password):\n            customer.set_unusable_password()\n            customer.tokens_valid_after   =   timezone.now().replace(microsecond = 0)\n            update_fields   +=  ['password', 'tokens_valid_after']\n        if not customer.email_verified:\n            customer.email_verified      =   True\n            customer.email_verified_at   =   timezone.now()\n            update_fields   +=  ['email_verified', 'email_verified_at']\n        if not customer.first_name and info.get('first_name'):\n            customer.first_name  =   info['first_name']\n            update_fields.append('first_name')\n        if not customer.last_name and info.get('last_name'):\n            customer.last_name   =   info['last_name']\n            update_fields.append('last_name')\n        if update_fields:\n            customer.save(update_fields = update_fields)"}

### Regression case
_Cubierto por tests agregados en el fix (ver commits 7d53e880 / 5c249b52)._

---

## [HIGH] MP refund/chargeback webhook never marks the order REFUNDED — paid orders persist as PACKING

Fingerprint: `storepayments:webhook-refund-requires-paid-status`

When Mercado Pago reports a payment as 'refunded' or 'charged_back', StoreMpWebhookQuery only calls orders_bridge.mark_refunded if the order's current status equals 'PAID'. However mark_order_paid always transitions PENDING_PAYMENT→PAID→PACKING inside a single transaction, so no order ever commits in status PAID — every MP-paid order sits in PACKING (or later SHIPPED/DELIVERED). The refund branch is therefore dead code: the MpPayment row is updated to REFUNDED but the Order keeps its active status, paid_at stays set, no OrderEvent is emitted, and sales metrics (cobrado_q excludes only status=REFUNDED) keep counting the returned money as revenue. The seller receives no in-panel signal and can ship goods whose payment was already returned. The identical bug was already fixed for the owner-facing refund_payment (refunds.py accepts PAID/PACKING/SHIPPED with an explicit comment) but the webhook path was missed. Verified independently: webhook test test_refunded_marks_order_refunded uses _fake_order(status='PAID') — a state that never persists — so the suite passes while production is dead code. Residual gap: TRANSITIONS has no DELIVERED→REFUNDED, so chargebacks after delivery cannot propagate even with the gate fixed.

### Trace
- **entrypoint** `StoreApp/domains/storepayments/views/webhook.py:175` — StoreMpWebhookView.post: Authenticated (per-store HMAC) MP notification with topic=='payment' dispatches StoreMpWebhookQuery(store, resource_id).
- **propagation** `StoreApp/domains/storepayments/services/webhook.py:198` — StoreMpWebhookQuery: order_status is read from the order instance; for any MP-paid order this is 'PACKING' (or SHIPPED/DELIVERED), never 'PAID'.
- **propagation** `StoreApp/domains/storepayments/services/webhook.py:222` — StoreMpWebhookQuery: elif mp_status in MP_STATUS_REFUNDED: mark_refunded is only invoked when order_status == 'PAID' — condition never true for real orders.
- **sink** `StoreApp/domains/orders/services/payments.py:156` — mark_order_paid: _apply_status(locked, Order.Status.PACKING) commits every paid order as PACKING in the same transaction that set PAID — PAID is transient and never observable.

### Evidence
- `StoreApp/domains/orders/services/payments.py:156` — mark_order_paid sets status=PAID then immediately _apply_status(locked, PACKING) — committed state is always PACKING+.
- `StoreApp/domains/orders/tests.py:260` — Test asserts order.status == PACKING after mark_order_paid — PAID never persists.
- `StoreApp/domains/storepayments/services/webhook.py:222` — if order_status == 'PAID': orders_bridge.mark_refunded(...) — the only MP-side refund propagation path.
- `StoreApp/domains/storepayments/services/refunds.py:65` — Owner refund endpoint already fixed the same defect: accepts {'PAID','PACKING','SHIPPED'} with comment that requiring PAID made refunds unreachable.
- `StoreApp/domains/storeadmin/services/metrics.py:62` — cobrado_q excludes only status=REFUNDED — an order stuck in PACKING after an MP refund still counts as collected revenue.
- `StoreApp/domains/storepayments/tests.py:314` — Webhook refund test uses _fake_order(status='PAID') — unreachable state, so the dead gate passed CI.

### Reproduction (target-neutral, local)
Attacker principal: Not an attacker action per se: any buyer-initiated MP refund, seller refund issued directly in the MP panel, or chargeback produces a legitimate signed webhook that the platform mishandles. A malicious buyer can also intentionally open a chargeback/dispute after receiving goods.

- Payload/input: `POST /api/webhooks/store-mp/<slug>/?data.id=<mp_payment_id>&type=payment (validly signed by MP for the store's webhook_secret; payment object returns status='refunded' or 'charged_back')`

1. Create an order with payment_method='mp' and take it to PAID via the MP webhook (order commits as PACKING).
2. In MP (or via chargeback), refund/charge back that payment so MP emits a payment notification.
3. Deliver the signed webhook to /api/webhooks/store-mp/<slug>/?data.id=<payment_id>&type=payment.
4. Observe: MpPayment.status becomes 'refunded' but Order.status remains 'PACKING'/'SHIPPED' and no OrderEvent is created.

Observed: Source-verified and independently confirmed: mark_order_paid commits PACKING (test-asserted), the webhook refund gate requires the never-persisted 'PAID', mark_order_refunded has no hidden PAID-only gate, and no other path propagates MP refunds to Order.

### Conditions
- data_state: Order was paid via Mercado Pago (status ends at PACKING+) and MP later emits a payment notification with status 'refunded' or 'charged_back'.
- third_party_dependency: Genuine MP webhook delivery with valid per-store HMAC signature; no forgery needed — the defect triggers on legitimate refund/chargeback events.

### Remediation
Replace the literal 'PAID' check with the set of states Order.TRANSITIONS allows to reach REFUNDED (PAID/PACKING/SHIPPED), mirroring refunds.py. Consider re-fetching/locking the Order row inside the atomic block, and evaluate whether DELIVERED should also reach REFUNDED (requires a TRANSITIONS change). Fix the webhook test to use a realistic persisted state (PACKING).
- {"file_name": "StoreApp/domains/storepayments/services/webhook.py", "fixed_code": "        elif mp_status in MP_STATUS_REFUNDED:\n            # mark_order_paid auto-avanza a PACKING en la misma transacción,\n            # así que PAID nunca es el estado persistido: aceptar todos los\n            # estados desde los que Order.TRANSITIONS permite llegar a REFUNDED.\n            if order_status in {'PAID', 'PACKING', 'SHIPPED'}:\n                orders_bridge.mark_refunded(order, actor = None)\n                order_status    =   'REFUNDED'"}

### Regression case
_Cubierto por tests agregados en el fix (ver commits 7d53e880 / 5c249b52)._

---

## [MEDIUM] Cross-site POST can bind the victim's browser to an attacker's customer session (login CSRF)

Fingerprint: `customers:session-establishing-endpoints-missing-origin-check`

CustomerRegisterView, CustomerLoginView and CustomerGoogleAuthView are AllowAny POST endpoints that set the ambient credentials customer_refresh (HttpOnly) and customer_csrf cookies via _session_response, but none validates Origin/Referer or requires a pre-session anti-CSRF token. DRF APIView is csrf_exempt (CsrfViewMiddleware never fires), default parsers accept application/x-www-form-urlencoded, and no custom middleware enforces Origin — so a plain auto-submitting cross-site form reaches these views. Browsers apply Set-Cookie from cross-site POST responses regardless of SameSite (SameSite governs sending, not setting), and CORS does not block 'simple' form posts. An attacker page can therefore log the victim's browser into the attacker's customer account — silently overwriting any existing customer session — so the victim's subsequent orders, addresses and PII are recorded under the attacker's account. Host-only cookies scope this per store host in subdomain mode; in path-alias mode (canonical store URLs on the www apex) one forced POST covers all stores. The identical gap exists in the parallel DAVENT user auth (systemic pattern, separate fingerprint-worthy but out of ecommerce scope).

### Trace
- **entrypoint** `StoreApp/domains/customers/views/auth_views.py:209` — CustomerLoginView.post: AllowAny POST accepting email/password/store_slug; identical exposure on register (:183) and google (:432).
- **propagation** `StoreApp/domains/customers/serializers/serializers.py:138` — CustomerLoginSerializer: Plain Serializer fields — no origin/session binding; DRF default parsers accept form-encoded POST bodies.
- **propagation** `StoreApp/domains/customers/views/auth_views.py:250` — _require_csrf call sites: Double-submit enforced only inside refresh (from_cookie) and logout — never on the endpoints that issue the cookies.
- **sink** `StoreApp/domains/customers/views/auth_views.py:108` — _session_response: Sets customer_refresh (HttpOnly, Path=/api/, SameSite=Lax) and customer_csrf cookies on the response with no prior Origin/CSRF validation.

### Evidence
- `StoreApp/domains/customers/views/auth_views.py:100` — _require_csrf is defined but invoked only at lines 250 and 297 (refresh/logout), never in register/login/google.
- `StoreApp/domains/customers/views/auth_views.py:80` — _set_refresh_cookie issues the ambient credential; SameSite=Lax does not prevent a cross-site POST response from setting it.
- `DaventProject/settings.py:245` — CsrfViewMiddleware present but DRF APIView.as_view() wraps views in csrf_exempt — middleware never fires on these endpoints.
- `DaventProject/middleware.py:61` — All five custom middlewares contain no Origin/Referer/CSRF enforcement.
- `frontend/src/api/customer.http.js:36` — Frontend sends X-CSRFToken only on refresh/logout; the victim's own SPA performs the double-submit legitimately after login-CSRF, so the planted session works normally.

### Reproduction (target-neutral, local)
Attacker principal: Remote web attacker who controls a page the victim visits

- Payload/input: `<form method=POST action=https://<api-host>/api/customer-auth/login/><input name=email value=attacker@x><input name=password value=Attacker!1></form><script>document.forms[0].submit()</script>`

1. Host a page that auto-submits a cross-site form POST to the customer login endpoint with the attacker's own credentials.
2. Victim's browser receives 200 + Set-Cookie customer_refresh/customer_csrf for the attacker's account.
3. Victim uses the store normally; their refresh flow yields the attacker's session and their orders/PII accumulate in the attacker's account.

Observed: Source-verified and independently confirmed: no origin/CSRF check on cookie issuance; DRF accepts form posts; CsrfViewMiddleware bypassed by csrf_exempt; victim's browser holds an authenticated customer session belonging to the attacker.

### Conditions
- user_interaction: Victim must load an attacker-controlled page (link, ad, embedded frame) while the storefront is reachable.
- network_routing: API and storefront share a site context where the API-domain cookies are sent on subsequent /api/ calls (path-alias apex mode amplifies to all stores; subdomain mode scopes per store host).

### Remediation
Bind session establishment to the request origin: reject register/login/google (and any future cookie-issuing endpoint, including the parallel DAVENT user auth) when the Origin/Referer header is present and not in an allowlist of configured storefront origins, or issue a pre-auth CSRF cookie via a same-site GET and require it on login. JSON-only enforcement is a weaker partial mitigation since fetch can still send simple requests.
- {"file_name": "StoreApp/domains/customers/views/auth_views.py", "fixed_code": "ALLOWED_ORIGINS = {o.rstrip('/') for o in getattr(settings, 'CUSTOMER_ALLOWED_ORIGINS', [])}\n\ndef _require_same_origin(request):\n    origin  =   request.headers.get('Origin') or request.headers.get('Referer') or ''\n    if origin and origin.rstrip('/') not in ALLOWED_ORIGINS:\n        raise PermissionDenied('Origen no permitido.')\n\n# en CustomerLoginView/CustomerRegisterView/CustomerGoogleAuthView.post, antes de emitir sesión:\n#   _require_same_origin(request)"}

### Regression case
_Cubierto por tests agregados en el fix (ver commits 7d53e880 / 5c249b52)._

---

## [MEDIUM] Exclusive (member-only) products leak name, description, price, image and ID through the anonymous pattern document

Fingerprint: `design:pattern-render-exclusive-products-leak`

The server-rendered design-pattern document — served anonymously at GET /api/stores/public/<slug>/pattern/document/ and /pattern — builds its product cards and related-product rail from querysets that filter only store+is_active and omit is_exclusive=False. Every sibling public path (catalog JSON, ?product= resolver, reviews, facet counts, member endpoint) filters exclusive products precisely so non-members cannot learn they exist; the pattern fragments violate that invariant. An anonymous visitor of any published store whose chosen DesignPattern declares {{products}} or {{product_related}} (21 of the shipped pattern sources do) receives up to 24 full product cards — name, 110-char description, price/offer price, image URL, category, brand and the product's numeric pk in data-ds-product — plus up to 4 related-product cards on product pages and the all-products count via ?meta=1. Purchase remains blocked server-side (cart/checkout reject exclusive products for non-members), so the impact is confidentiality of member-only catalog data, not unauthorized buying. Verifier corrections: {{product_related}} leak requires ?product=<non-exclusive id> (surfaces exclusive products as related cards, cannot render the exclusive product itself as PDP); products_total is NOT flag-gated and counts exclusive products even when the catalog page flag is off.

### Trace
- **entrypoint** `StoreApp/domains/stores/views/viewset.py:710` — StoreViewSet.public_pattern_document / public_pattern: Anonymous GET /api/stores/public/<slug>/pattern/document/ and /pattern — PUBLIC_ACTIONS, AllowAny; gated only by _pattern_store (published, not blocked, has_public_link). No member authentication anywhere on this path.
- **propagation** `StoreApp/domains/design/services/pattern_render.py:1565` — render_store_pattern → build_store_context / _product_values: needed = VAR_RE.findall(pattern.html) selects which raw fragments to build; builders['products'] and product_raw['product_related'] are populated whenever the pattern markup declares {{products}}/{{product_related}} — 21 shipped sources do.
- **propagation** `StoreApp/domains/design/services/pattern_render.py:283` — _product_fragment default queryset → card markup: Product.objects.filter(store=store, is_active=True)[:FRAGMENT_LIMIT=24] — missing is_exclusive=False. Each card emits escaped name, 110-char description, effective price/offer, image URL, category, brand and data-ds-product=<pk> into anonymous HTML.
- **propagation** `StoreApp/domains/design/services/pattern_render.py:856` — _related_fragment base queryset: Related-product rail uses the same unfiltered base queryset (excludes only the current product pk), so up to 4 exclusive products render as 'related' cards on every public product page.
- **sink** `StoreApp/domains/design/services/pattern_render.py:1624` — render_store_pattern return payload 'products_total': Product.objects.filter(store=store, is_active=True).count() includes exclusive products — discloses the total count via GET /pattern?meta=1.

### Evidence
- `StoreApp/domains/design/services/pattern_render.py:283` — _product_fragment: Product.objects.filter(store=store, is_active=True) — no is_exclusive predicate; renders up to 24 cards with name/description/price/image/category/brand/data-ds-product pk.
- `StoreApp/domains/design/services/pattern_render.py:856` — _related_fragment: base = Product.objects.filter(store=store, is_active=True).exclude(pk=product.pk) — same omission.
- `StoreApp/domains/design/services/pattern_render.py:1624` — 'products_total' counts exclusive products; exposed via /pattern?meta=1 and not gated by the catalog page flag.
- `StoreApp/domains/stores/views/viewset.py:666` — Contrast proving intent: the anonymous ?product= resolver filters pk+store+is_active+is_exclusive=False with comment 'is_exclusive queda fuera del documento público'.
- `StoreApp/domains/stores/views/viewset.py:910` — Public catalog filters is_active+is_exclusive=False with explicit invariant comment; facet counts apply the same filter.
- `StoreApp/domains/memberships/views/customer.py:287` — Exclusive products are only served by /api/customer/stores/<slug>/exclusive-products/ behind CustomerJWT + has_exclusive_access.
- `StoreApp/domains/cart/services/cart.py:113` — Purchase blocked server-side for is_exclusive without membership access — impact is confidentiality only.

### Reproduction (target-neutral, local)
Attacker principal: Anonymous internet visitor with no account, no membership, and no special access — the same principal the public catalog already hides exclusive products from.

- Payload/input: `GET /api/stores/public/<slug>/pattern/document/?surface=catalog`
- Payload/input: `GET /api/stores/public/<slug>/pattern?meta=1`
- Payload/input: `GET /api/stores/public/<slug>/pattern/document/?surface=product&product=<public_product_id>`

1. Issue the anonymous pattern document request for a store using a shipped HTML pattern.
2. The rendered HTML contains product cards for is_exclusive products (name, description, price, image, pk) that the public catalog JSON would never return.
3. GET /pattern?meta=1 additionally returns products_total including exclusive products.

Observed: Source-verified and independently confirmed with a bounded local queryset check: the pattern queryset lacks the is_exclusive predicate while the catalog queryset has it; anonymous entrypoints confirmed AllowAny; 21 shipped sources reference the vulnerable fragments.

### Conditions
- data_state: Store is_published=True, is_blocked=False, and the owner's plan includes the has_public_link benefit.
- data_state: Store's effective template resolves to a DesignPattern whose html declares {{products}} (landing/catalog) or {{product_related}} (product surface); 21 of the shipped pattern sources do.
- data_state: At least one Product with is_active=True and is_exclusive=True exists in that store.

### Remediation
Apply the same is_exclusive=False predicate used by every other anonymous read path to all three pattern-render querysets, ideally via a single public-products helper so future fragments cannot drift; add a regression test asserting the anonymous pattern document/meta contains no exclusive product name, price or pk.
- {"file_name": "StoreApp/domains/design/services/pattern_render.py", "fixed_code": "# line 283 (_product_fragment default queryset)\nproducts = (\n    Product.objects.filter(store = store, is_active = True, is_exclusive = False)\n    .select_related('category', 'brand')\n    .order_by('-created_at')[:FRAGMENT_LIMIT]\n)\n\n# line 856 (_related_fragment base queryset)\nbase = Product.objects.filter(store = store, is_active = True, is_exclusive = False).exclude(pk = product.pk).select_related('category', 'brand')\n\n# line 1624 (products_total)\n'products_total': Product.objects.filter(store = store, is_active = True, is_exclusive = False).count(),"}

### Regression case
_Cubierto por tests agregados en el fix (ver commits 7d53e880 / 5c249b52)._

---

## [MEDIUM] Customer logout never invalidates the refresh epoch — an in-flight or failed logout can leave the buyer session recoverable

Fingerprint: `frontend:customer-logout-no-epoch-invalidation`

customer.store.logout() awaits customerApi.logout() inside try/catch and then clears only the Pinia refs and the module access token via customerTokenStorage.clear(); it never sets sessionEnded, never increments sessionEpoch, never calls clearSessionHints(), and never calls the exported logoutCustomerSession() helper, which has zero call sites in frontend/src. A refreshCall() already in flight when logout runs therefore still passes the stale-result guard (sessionEnded===false && epoch unchanged), writes the rotated access token back via customerTokenStorage.set(), and can leave a zombie access token if it lands after the logout/local clear; its Set-Cookie can also re-arm customer_refresh/customer_csrf after CustomerRefreshView deletes them. If the logout request fails before the backend clears cookies (network error, CSRF failure, or a stale Bearer rejected during authentication), customer_csrf remains readable, hasCustomerSessionCookie() stays true, and the next ensureSession()/restoreCustomerSession() silently refreshes and restores the session. The DAVENT owner twin implements the intended pattern: http.js logoutSession() sets sessionEnded=true, sessionEpoch++ and clearSessionHints() unconditionally.

### Trace
- **entrypoint** `frontend/src/stores/customer.store.js:120` — logout(): awaits customerApi.logout() in try/catch, then clears accessToken.value, customerTokenStorage, customer/status/error refs; no epoch/sessionEnded/hint invalidation and no logoutCustomerSession() call.
- **propagation** `frontend/src/api/customer.http.js:143` — logoutCustomerSession(): sets sessionEnded=true, sessionEpoch++, awaits backend logout, then customerTokenStorage.clear() and clearSessionHints(); exported but has no callers in frontend/src.
- **propagation** `frontend/src/api/customer.http.js:95` — refreshCall(): stale-refresh guard only discards results when sessionEnded || epoch !== sessionEpoch; logout leaves both unchanged, so an in-flight refresh completes and calls customerTokenStorage.set(access).
- **sink** `frontend/src/stores/customer.store.js:45` — ensureSession() -> restoreCustomerSession(): store accessToken.value is null but customerTokenStorage.getAccess() is truthy, so restoreCustomerSession() returns true, accessToken.value is re-assigned, fetchMe() repopulates customer, and isAuthenticated becomes true again with a fresh 12h Bearer.

### Evidence
- `frontend/src/stores/customer.store.js:120` — logout() body contains no sessionEnded/sessionEpoch/clearSessionHints/logoutCustomerSession reference; cleanup runs after the swallowed try/catch regardless of request success.
- `frontend/src/api/customer.http.js:143` — logoutCustomerSession is defined/exported; grep over frontend/src shows only this definition and no invocation — dead code.
- `frontend/src/api/customer.http.js:95` — epoch guard followed by customerTokenStorage.set(access) — the resurrection write.
- `frontend/src/api/http.js:206` — DAVENT logoutSession() sets sessionEnded=true, sessionEpoch++ and clearSessionHints() unconditionally — the intended contrast.
- `frontend/src/api/customer.http.js:53` — hasCustomerSessionCookie() returns false only when sessionEnded or the readable customer_csrf hint is absent; a failed logout leaves the hint intact.
- `frontend/src/api/customer.http.js:76` — customerHttp attaches the module Bearer to API-origin requests, including /customer-auth/logout/, so a stale/expired access token can make the logout request fail before cookie cleanup.
- `StoreApp/domains/customers/authentication.py:63` — CustomerJWTAuthentication raises AuthenticationFailed for an invalid/expired Bearer before the AllowAny logout view can blacklist the refresh or delete cookies.
- `StoreApp/domains/customers/views/auth_views.py:276` — CustomerRefreshView cookie-flow branch (lines 276-278) calls _set_refresh_cookie(response, new_refresh) and _set_csrf_cookie(response), so a late-landing refresh re-arms the hints deleted by logout.

### Reproduction (target-neutral, local)
Attacker principal: Shared-device or session-hygiene scenario: a user clicks 'Salir' expecting the buyer session to end while an API 401-triggered refresh is in flight, or the logout request fails (network, CSRF, or stale Bearer). No external attacker input required.

- Payload/input: `n/a — timing interleaving / request failure, not input-driven`

1. Log in as a customer and let the access token expire or be revoked.
2. Trigger an authenticated action that produces a 401 so tryRefresh()/refreshCall() is in flight, then click Salir (StoreAccountView logout -> customer.logout) while the refresh POST is pending.
3. Alternatively, make the logout request fail before cookie cleanup and then trigger any ensureSession()-dependent action.
4. Observe whether the refresh response lands after logout/local clear and whether customer_csrf remains readable after a failed logout.

Observed: Source-verified: refreshCall's guard cannot observe customer.store.logout() (sessionEnded never set, epoch never bumped), so customerTokenStorage.set() can store the rotated access token and ensureSession()/restoreCustomerSession() re-adopts it, fetchMe() succeeds, and the UI returns to authenticated state; a late refresh Set-Cookie can also re-arm customer_refresh/customer_csrf. A logout request that fails before backend cookie cleanup leaves customer_csrf readable, so the next ensureSession() can silently restore via the still-valid refresh cookie.

### Conditions
- timing_dependency: A refreshCall must be in flight when logout runs, or the logout request must fail before the backend clears cookies.
- data_state: A failed/non-2xx logout leaves the readable customer_csrf hint and, when the refresh credential remains valid, enables silent auto-restore on the next ensureSession().

### Remediation
Add logoutCustomerSession to the existing customer.http.js import in customer.store.js and make logout() await it instead of customerApi.logout(): the helper sets sessionEnded/sessionEpoch before the request, performs the backend logout without attaching the possibly-stale module Bearer, and clears token+hints even on failure. Then clear only the Pinia refs. Do not keep a second customerApi.logout() call and do not reference cartStore/localStorage cleanup inside the store (the caller already handles cart state).
- {"file_name": "frontend/src/stores/customer.store.js", "fixed_code": "import {\n  customerTokenStorage,\n  hasCustomerSessionCookie,\n  restoreCustomerSession,\n  logoutCustomerSession,\n} from '../api/customer.http.js'\n\n// ...existing store body...\n\n  async function logout() {\n    // Invalida la época antes del request: un refresh en vuelo se descarta\n    // y los hints se limpian aunque el logout falle (patrón http.js).\n    await logoutCustomerSession()\n    accessToken.value = null\n    customer.value = null\n    status.value = 'idle'\n    lastError.value = ''\n    fieldErrors.value = {}\n  }"}

### Regression case
_Cubierto por tests agregados en el fix (ver commits 7d53e880 / 5c249b52)._

---

## [MEDIUM] Public order receipt endpoint leaks buyer email, national document and last name to any tracking-token holder

Fingerprint: `orders:public-receipt-buyer-pii`

GET /api/stores/public/<slug>/orders/<tracking_token>/receipt/ is AllowAny (no authentication, only PublicReadThrottle) and returns build_receipt_payload(order), whose 'customer' block includes customer_email, customer_document_type, customer_document (EncryptedCharField decrypts transparently → plaintext national ID) and customer_last_name. The sibling tracking endpoint order_tracking_payload deliberately withholds exactly these fields — its docstring states email/teléfono/documento 'NUNCA salen' — and the customer-authenticated detail endpoint reuses that same scrubbed payload. The receipt endpoint is therefore the only non-owner path that exposes the buyer's government ID and email. Verifier confirmed the frontend NEVER renders receipt.customer (StoreTrackingView uses only seller/order/items/totals) — the PII block is dead weight, making scrubbing trivial. shipping_address is already disclosed by tracking by design, so the incremental exposure is last_name+email+document_type+document.

### Trace
- **entrypoint** `StoreApp/domains/orders/views/public.py:238` — PublicOrderReceiptView.get: AllowAny + authentication_classes=[] endpoint; resolves store (published/unblocked, orders_enabled NOT required) and order by tracking_token, then returns build_receipt_payload(order) with only PublicReadThrottle.
- **propagation** `StoreApp/domains/orders/services/checkout.py:482` — build_receipt_payload: Builds the receipt dict including the 'customer' block with first_name, last_name, email, document_type and document.
- **sink** `StoreApp/domains/orders/services/checkout.py:514` — build_receipt_payload → customer.document: order.customer_document is an EncryptedCharField whose from_db_value/to_python decrypt AES-256-GCM transparently, so the JSON response contains the buyer's plaintext national document number alongside email and last name.

### Evidence
- `StoreApp/domains/orders/services/checkout.py:511` — 'customer' block returns first_name, last_name, email, document_type, document — the last three are PII the tracking payload explicitly forbids.
- `StoreApp/domains/orders/services/checkout.py:463` — order_tracking_payload docstring: 'PII mínima: solo el nombre del comprador y su dirección de envío … email/teléfono/documento NUNCA salen' — the stated policy the receipt violates.
- `StoreApp/domains/orders/views/public.py:239` — PublicOrderReceiptView: permission_classes=[AllowAny], authentication_classes=[] — anonymous access gated solely by the unguessable tracking_token.
- `StoreApp/domains/orders/models/models.py:122` — customer_document = EncryptedCharField(aad='Order.customer_document') — decrypts transparently on attribute access.
- `StoreApp/domains/orders/views/customer.py:95` — Even the authenticated customer's own detail endpoint uses order_tracking_payload (scrubbed) — the receipt endpoint is the ONLY non-owner path exposing document/email.
- `frontend/src/views/StoreTrackingView.vue:307` — Receipt render uses only receipt.seller/order/items/totals/legend — never references receipt.customer; the PII block is unused by the frontend.

### Reproduction (target-neutral, local)
Attacker principal: Anonymous internet user who obtains a store order tracking link (e.g., a forwarded 'Tu pedido fue enviado' email, a WhatsApp message, or a leaked access-log entry containing /api/stores/public/<slug>/orders/<token>/).

- Payload/input: `GET /api/stores/public/<slug>/orders/<tracking_token>/receipt/`

1. Obtain any valid tracking_token for a store order (intercept/forward the public tracking link).
2. Issue GET /api/stores/public/<slug>/orders/<token>/receipt/ with no authentication.
3. Read the JSON 'customer' object: email, document_type and document (plaintext national ID) plus last_name are returned.

Observed: Source-verified and independently confirmed: build_receipt_payload returns order.customer_email, customer_document_type, customer_document (decrypted) and customer_last_name in the anonymous response — fields that order_tracking_payload explicitly documents as never leaving the public API, and that the frontend never consumes.

### Conditions
- authentication_level: None — endpoint is AllowAny; the only credential is knowledge of the order's tracking_token (secrets.token_urlsafe(24), ~192 bits, unguessable by brute force).
- data_state: Attacker must possess or intercept the tracking link — realistic via forwarded status emails/WhatsApp messages, shared devices, browser history, or HTTP access logs since the token travels in the URL path.
- system_configuration: Store must be published and not blocked (require_orders_enabled=False, so even stores that disabled online sales still expose receipts for existing orders).

### Remediation
Remove buyer-identifying fields that the tracking policy forbids from the public receipt payload: drop email, document_type, document and last_name from build_receipt_payload's 'customer' block (keep first_name, which tracking already exposes). The frontend never renders these fields, so removal is zero-risk. If fiscal receipt data is ever needed, gate it behind CustomerJWTAuthentication + ownership check instead of the anonymous token path.
- {"file_name": "StoreApp/domains/orders/services/checkout.py", "fixed_code": "        'customer'          :   {\n            'first_name'        :   order.customer_first_name,\n            # PII policy (order_tracking_payload): email/phone/document\n            # NUNCA salen por la API pública — el token es la credencial\n            # de seguimiento, no de identidad.\n        },"}

### Regression case
_Cubierto por tests agregados en el fix (ver commits 7d53e880 / 5c249b52)._

---

## [MEDIUM] Owner-controlled R2 endpoint URL is fetched server-side by boto3 — blind SSRF into internal network

Fingerprint: `stores:storage-byo-endpoint-blind-ssrf`

StoreStorageConfig.endpoint is owner-writable via PUT /api/store-payments/storage-config/ and validated only as an https:// URL (http allowed only under DEBUG for MinIO). When enabled with credentials, every image upload/delete for that store's keys constructs boto3.client('s3', endpoint_url=<owner URL>) and issues real authenticated PUT/DELETE requests to that host from the application server. There is no allowlist restricting the endpoint to Cloudflare R2 (*.r2.cloudflarestorage.com) or any public S3 host, so an authenticated owner can point it at internal HTTPS services. Impact is blind: responses are not returned to the owner (errors trigger silent fallback to the DAVENT bucket; object_url uses locally-generated presigned URLs, not a server-side GET), and the SigV4 Authorization header is signed with the owner's own chosen credentials, so no DAVENT secret is disclosed. The residual risk is request forgery with side effects (PUT/DELETE against internal S3-compatible or HTTP-accepting services) and internal host probing via timing/error behavior. Upgraded from needs_validation: the missing endpoint allowlist/egress control is a source-certain defect; deployment topology only modulates impact.

### Trace
- **entrypoint** `StoreApp/domains/storepayments/views/integrations.py:118` — StorageConfigView.put: Owner-authenticated PUT persists endpoint/bucket/credentials for their own store.
- **propagation** `StoreApp/domains/storepayments/serializers/serializers.py:256` — StoreStorageConfigSerializer.validate_endpoint: _clean_https_url only enforces https:// scheme (http only when settings.DEBUG) — no host allowlist.
- **propagation** `StoreApp/domains/stores/services/storage.py:153` — _byo_backend: Decrypts owner credentials and returns endpoint verbatim for any enabled+configured store.
- **sink** `StoreApp/domains/stores/services/storage.py:90` — _client: boto3.client('s3', endpoint_url=backend['endpoint'], ...) — server-side PUT/DELETE issued to the owner-controlled host on every store image operation.

### Evidence
- `StoreApp/domains/storepayments/serializers/serializers.py:199` — _clean_https_url: accepts any https:// value; http only under DEBUG — no domain restriction.
- `StoreApp/domains/stores/services/storage.py:292` — put_object issues _client(backend).put_object to backend['endpoint'] — a real server-side request to the arbitrary URL.
- `StoreApp/domains/stores/services/storage.py:243` — object_url catches all exceptions and returns None / uses local presigned generation — responses/errors are not exposed, making the SSRF blind.

### Reproduction (target-neutral, local)
Attacker principal: Authenticated store owner configuring their own BYO storage integration.

- Payload/input: `PUT /api/store-payments/storage-config/ {"enabled":true,"endpoint":"https://<internal-host>/","bucket":"x","access_key":"...","secret_key":"..."}`

1. Configure StoreStorageConfig with an arbitrary https endpoint (e.g., an internal service address).
2. Trigger any image upload/delete for that store's keys.
3. The application server issues authenticated S3 PUT/DELETE requests to the chosen host; responses are discarded (blind).

Observed: Source-verified and independently confirmed: no host allowlist in validation or client construction; server-side PUT/DELETE to the arbitrary endpoint confirmed; blind because errors fall back silently and object_url uses local presigning.

### Conditions
- authentication_level: Authenticated store owner (DAVENT account with a store).
- system_configuration: BYO storage enabled with endpoint+bucket+credentials configured; production requires https endpoint.
- environmental_dependency: Impact depends on reachable internal HTTPS services that accept/act on SigV4-signed S3 PUT/DELETE requests — deployment-specific.

### Remediation
Allowlist the endpoint host: restrict to *.r2.cloudflarestorage.com, *.amazonaws.com, and known S3-compatible hosts (or an explicit env-configured allowlist), rejecting private/loopback/link-local addresses. Alternatively document the trust assumption and enforce egress rules at the network layer.
- {"file_name": "StoreApp/domains/storepayments/serializers/serializers.py", "fixed_code": "ALLOWED_STORAGE_HOSTS = ('r2.cloudflarestorage.com', 'amazonaws.com')\n\ndef _clean_https_url(value):\n    ...\n    host = urlparse(value).hostname or ''\n    if not any(host == h or host.endswith('.' + h) for h in ALLOWED_STORAGE_HOSTS):\n        raise serializers.ValidationError('Endpoint no permitido.')\n    return value"}

### Regression case
_Cubierto por tests agregados en el fix (ver commits 7d53e880 / 5c249b52)._

---

## [MEDIUM] Any registered customer can email-bomb a store owner: one Celery email per support message, no per-store cap or opt-out

Fingerprint: `support:per-message-owner-email-spam`

POST /api/support/threads/ and /api/support/threads/<id>/messages/ let ANY active customer account (email verification NOT required — Customer.is_active defaults True and IsCustomer never checks email_verified) open threads and post messages against ANY published, non-blocked store slug. Every customer-authored message calls post_message(), which unconditionally calls notify_owner_message() AND enqueue_support_email(); the latter dispatches one Celery task per message that SMTP-sends the raw message body to contact_target(store) — the owner's chosen contact_email or account email. The only bound is a per-customer throttle (60 messages/hour, 10 threads/hour), which still permits ~1,440 owner emails/day from a single free account, multiplies linearly with throwaway accounts (register is 10/hour/IP), is keyed per customer so it cannot be raised by the victim, and fails open if the cache backend errors. There is no per-store inbound quota, no StoreCustomization toggle to disable support, no membership requirement (create_thread never calls ensure_membership, so the spamming customer may have no StoreMembership row and therefore cannot be suspended), and no email dedup/batching. Result: cross-tenant spam/notification flood and operator-owned mail spend; also unbounded SupportThread/SupportMessage row growth. Orchestrator-verified directly against source (verifier agent timed out; disposition confirmed by parent review of services.py:100-130,170-230, views/customer.py:51-80,117-145, services.py:55-69).

### Trace
- **entrypoint** `StoreApp/domains/support/views/customer.py:164` — CustomerSupportMessageCreateView.post: Authenticated customer POSTs {body} to any own thread; throttle is only SupportMessageThrottle 60/hour keyed by customer.pk.
- **propagation** `StoreApp/domains/support/views/customer.py:117` — CustomerSupportThreadListCreateView.post: Creates thread against arbitrary published store slug (customer_visible_store checks only is_published/is_blocked — no membership, no support opt-out).
- **propagation** `StoreApp/domains/support/services/services.py:115` — post_message: On sender=CUSTOMER unconditionally calls notify_owner_message(thread, message) and enqueue_support_email(thread, message) for EVERY message.
- **propagation** `StoreApp/domains/support/services/services.py:190` — enqueue_support_email: Dispatches send_support_message_email.delay(message.pk) — one Celery task per message, no dedup key.
- **sink** `StoreApp/domains/support/services/services.py:215` — deliver_support_email: send_mail() to contact_target(store) — owner's contact_email or account email — body contains attacker-controlled subject/body text.

### Evidence
- `StoreApp/domains/support/views/customer.py:75` — SupportMessageThrottle scope support_message rate 60/hour — the ONLY inbound bound; keyed per customer (c<pk>), not per store.
- `StoreApp/domains/support/services/services.py:55` — customer_visible_store requires only is_published+is_blocked; membership never checked.
- `StoreApp/domains/support/services/services.py:182` — enqueue_support_email fires per message with no dedupe_key (contrast: notify_owner_message dedupes in-app via dedupe_key=support:<thread.pk>).
- `StoreApp/domains/customers/models/models.py:62` — Customer.is_active defaults True; email_verified never consulted by IsCustomer/authentication — unverified throwaway accounts can post immediately.
- `StoreApp/domains/stores/models/models.py:204` — StoreCustomization exposes show_contact/show_catalog/etc. toggles but NO support/inbox disable flag — owner cannot turn the channel off.
- `DaventProject/throttling.py:35` — _ResilientThrottleMixin.allow_request fails OPEN on cache errors — the per-customer bound disappears during a cache outage.

### Reproduction (target-neutral, local)
Attacker principal: Registered customer (optionally unverified email) targeting any merchant's public store slug.

- Payload/input: `POST /api/support/threads/ {"store":"<victim-slug>","subject":"x","body":"x"}`
- Payload/input: `POST /api/support/threads/<id>/messages/ {"body":"<repeat 60x/hour>"}`

1. Register a customer account via POST /api/customer-auth/register/ (no email verification needed to call the API).
2. Create one support thread against the victim store slug.
3. POST up to 60 messages/hour to that thread; each message enqueues a Celery task that emails the store owner's contact address.
4. Repeat across additional throwaway accounts (register is 10/hour/IP) or additional victim stores — there is no per-store aggregate cap and no owner-side block for non-members.

Observed: Source-verified by hunter and orchestrator: every accepted customer message deterministically produces one in-app notification upsert and one queued outbound email to the merchant; the only rate bound is per-customer (60/h) and fails open without cache. ~1,440 emails/day per account per store; unbounded thread/message rows.

### Conditions
- authentication_level: Attacker holds any active customer JWT — free registration, email verification not required for API use.
- data_state: Target store is is_published=True and is_blocked=False (the normal state of every live merchant).
- system_configuration: Celery worker + SMTP configured (production posture); spam consumes platform mail quota/reputation.

### Remediation
Add store-side abuse controls: (1) per-store inbound message quota (e.g., N messages/hour across all customers, enforced in post_message under select_for_update or a cache counter keyed by store.pk); (2) batch/digest owner emails (e.g., one email per thread per X minutes, or notification-only with email on first message); (3) require StoreMembership (ensure_membership) or at least allow owners to suspend/block a customer independent of membership; (4) add a StoreCustomization show_support toggle checked in customer_visible_store/create_thread; (5) consider requiring verified email for support writes.
- {"file_name": "StoreApp/domains/support/services/services.py", "fixed_code": "def post_message(thread, *, sender, body):\n    # Per-store inbound quota: max STORE_MSG_PER_HOUR customer messages/hour.\n    if sender == SupportMessage.Sender.CUSTOMER:\n        key = f'support:store:{thread.store_id}:msgs'\n        if not cache_add(key, 0, 3600):\n            pass\n        count = cache_incr(key) or 0\n        if count > STORE_MSG_PER_HOUR:\n            from rest_framework.exceptions import Throttled\n            raise Throttled(detail='La tienda recibió demasiados mensajes. Probá más tarde.')\n    message = SupportMessage.objects.create(thread=thread, sender=sender, body=body.strip())\n    thread.last_message_at = message.created_at\n    thread.last_message_by = sender\n    thread.save(update_fields=['last_message_at','last_message_by','updated_at'])\n    if sender == SupportMessage.Sender.CUSTOMER:\n        notify_owner_message(thread, message)\n        enqueue_support_email(thread, message)   # ideally: digest/batch, not per-message\n    return message"}

### Regression case
_Cubierto por tests agregados en el fix (ver commits 7d53e880 / 5c249b52)._

---
