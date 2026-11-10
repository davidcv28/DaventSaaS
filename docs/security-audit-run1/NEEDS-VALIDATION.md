# Needs validation — run-1

Records that survived source review but whose decisive fact lives outside the repo (provider behavior or deployment config). They are prioritized leads, NOT confirmed vulnerabilities. Each lists a bounded local plan and/or an owner-observed deployment check. No live probing was performed.

## `storepayments:mp-refund-check-then-act-toctou` — MP refund endpoint locks the order row before the refund call (concurrent TOCTOU fixed), but an ambiguous MP outcome lets a retry issue a second refund POST — dedup is provider-side

CURRENT SOURCE (post-remediation): MpRefundView → refund_payment re-reads the Order row with select_for_update() inside transaction.atomic() and evaluates the {PAID,PACKING,SHIPPED} status gate on the LOCKED row before calling mp_client.refund_mp_payment and orders_bridge.mark_refunded in the same transaction. Two concurrent refund requests serialize on the row lock: the second sees status=REFUNDED (terminal) and is rejected before reaching MP — the original check-then-act double-refund race is CLOSED. RESIDUAL (provider-dependent): the irreversible MP refund executes inside the atomic block, so if MP processes the refund but the outcome is ambiguous locally — response lost/timeout raising MpApiError, or mark_refunded failing — the transaction rolls back leaving the order refundable and MpPayment APPROVED; a retry issues a second POST /v1/payments/<id>/refunds for the same payment_id. Whether MP deduplicates or rejects a second total refund is provider behavior not visible in the repo; if MP honors both, the buyer is refunded twice while the order records a single REFUNDED.

### Trace
- **entrypoint** `StoreApp/domains/storepayments/views/mp.py:162` — MpRefundView.post: Owner-authenticated POST /api/store-payments/mp/refund/<order_id>/; order fetched via get_order_for_store then passed to refund_payment.
- **propagation** `StoreApp/domains/storepayments/services/orders_bridge.py:61` — get_order_for_store: Plain .filter(store_id, pk).first() — no lock here, but refund_payment re-locks the row itself.
- **propagation** `StoreApp/domains/storepayments/services/refunds.py:70` — refund_payment: transaction.atomic() + Order.objects.select_for_update().filter(pk, store_id).first(); status gate evaluated on the LOCKED row — concurrent requests serialize (local TOCTOU closed).
- **propagation** `StoreApp/domains/storepayments/services/refunds.py:88` — refund_payment: mp_client.refund_mp_payment called while holding the row lock inside the atomic block; MpApiError → RefundError → full rollback leaves order refundable if MP may have processed the refund.
- **sink** `StoreApp/domains/storepayments/services/mp_client.py:94` — refund_mp_payment: POST /v1/payments/<id>/refunds with the seller token — irreversible external money movement; a retry after ambiguous outcome issues a second refund POST for the same payment_id.

### Evidence
- `StoreApp/domains/storepayments/services/refunds.py:75` — locked = Order.objects.select_for_update().filter(pk=order.pk, store_id=...).first() or order — row lock acquired inside transaction.atomic() BEFORE the status check.
- `StoreApp/domains/storepayments/services/refunds.py:82` — if locked.status not in {PAID,PACKING,SHIPPED}: raise — gate on the locked row; concurrent loser sees REFUNDED and never reaches MP.
- `StoreApp/domains/storepayments/services/refunds.py:89` — mp_client.refund_mp_payment executes inside the atomic block; MpApiError → RefundError rolls back local state while MP-side outcome may be ambiguous.
- `StoreApp/domains/storepayments/services/refunds.py:95` — orders_bridge.mark_refunded(locked) + MpPayment.status=REFUNDED commit in the same transaction as the MP call — post-MP failure rolls everything back.
- `StoreApp/domains/orders/services/payments.py:169` — mark_order_refunded re-locks via select_for_update and validates Order.TRANSITIONS; REFUNDED is terminal so a committed refund permanently blocks retries.
- `StoreApp/domains/storepayments/services/mp_client.py:22` — MP_TIMEOUT=15 bounds how long the order row lock is held across the external HTTP call.

### Claimed root cause
refund_payment performs the irreversible MP refund inside transaction.atomic() while holding the order row lock; any failure after MP may have moved money (lost response → MpApiError, or mark_refunded error) rolls back local state, so a retry re-issues POST /v1/payments/<id>/refunds — protection against double-refund depends entirely on MP-side idempotency, not verifiable in the repo. (The original unlocked check-then-act root cause is remediated: the status gate now runs on a select_for_update-locked row.)

### Blockers
- Whether Mercado Pago's POST /v1/payments/<id>/refunds is idempotent or rejects a second total refund for the same payment_id when the first attempt's outcome was ambiguous (provider behavior, not in repo) — the ONLY remaining path to a double refund now that concurrent requests serialize on the order row lock.
- Whether MP can return/process a refund whose HTTP response is lost in transit (timeout after server-side success) — determines if the rollback-then-retry path is reachable in practice.

### Local validation plan
Unit test refund_payment with mp_client.refund_mp_payment mocked to raise MpApiError AFTER simulating MP-side success (or mark_refunded mocked to raise): assert the order stays refundable and a second refund_payment call issues a second MP refund POST. Concurrency regression: two threads calling refund_payment on the same order → exactly one MP call thanks to select_for_update.

### Deployment-owner check
Owner-observed: with a test MP payment, force an ambiguous refund outcome (client-side timeout after MP processed the refund) then retry; inspect the MP dashboard / GET /v1/payments/<id>/refunds for duplicate refund objects.

---
