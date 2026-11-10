# Needs validation — run-1

Records that survived source review but whose decisive fact lives outside the repo (provider behavior or deployment config). They are prioritized leads, NOT confirmed vulnerabilities. Each lists a bounded local plan and/or an owner-observed deployment check. No live probing was performed.

## `storepayments:mp-refund-check-then-act-toctou` — Refund endpoint checks order status without locking before the irreversible MP refund call — concurrent requests can double-refund

MpRefundView → refund_payment reads order.status on an unlocked instance (get_order_for_store does a plain .first()), validates it is in {PAID,PACKING,SHIPPED}, then calls mp_client.refund_mp_payment (external POST /v1/payments/<id>/refunds) BEFORE mark_order_refunded acquires select_for_update. Two concurrent POST /api/store-payments/mp/refund/<order_id>/ requests can both pass the status check and both issue the MP refund call; only afterwards does mark_order_refunded serialize on the order row. Whether MP deduplicates or rejects a second total-refund POST for the same payment_id is provider behavior not visible in the repo. If MP honors both, the buyer is refunded twice while the order records a single REFUNDED. Verifier confirmed the TOCTOU is real in source; severity would be high if MP does not dedupe.

### Trace
- **entrypoint** `StoreApp/domains/storepayments/views/mp.py:162` — MpRefundView.post: Owner-authenticated POST; order fetched via get_order_for_store without row lock.
- **propagation** `StoreApp/domains/storepayments/services/orders_bridge.py:61` — get_order_for_store: Plain .filter(store_id, pk).first() — no select_for_update; stale status read possible under concurrency.
- **propagation** `StoreApp/domains/storepayments/services/refunds.py:65` — refund_payment: Status gate evaluated on the unlocked instance before any lock is taken.
- **sink** `StoreApp/domains/storepayments/services/mp_client.py:94` — refund_mp_payment: POST /v1/payments/<id>/refunds with the seller token — irreversible external money movement executed before local state serialization.

### Evidence
- `StoreApp/domains/storepayments/services/refunds.py:65` — if status not in {PAID,PACKING,SHIPPED}: raise — evaluated on the caller-supplied instance with no lock.
- `StoreApp/domains/storepayments/services/refunds.py:78` — orders_bridge.mark_refunded is called only AFTER mp_client.refund_mp_payment succeeds — the locking transition post-dates the external side effect.
- `StoreApp/domains/orders/services/payments.py:169` — mark_order_refunded does take select_for_update, but only after the MP refund already happened.

### Claimed root cause
refund_payment performs a check-then-act on order.status without select_for_update before an irreversible external side effect; the state transition that would serialize the operation (mark_order_refunded) happens only after the MP call.

### Blockers
- Whether Mercado Pago's POST /v1/payments/<id>/refunds is idempotent or rejects a second total refund for the same payment (provider behavior, not in repo).

### Local validation plan
In a Django shell/test, simulate two threads calling refund_payment on the same order with mp_client.refund_mp_payment mocked to record call count — confirm both pass the status gate before mark_refunded serializes (expected: 2 MP calls, 1 REFUNDED transition).

### Deployment-owner check
Owner-observed: with a test MP payment, fire two concurrent POST /api/store-payments/mp/refund/<order_id>/ and inspect the MP dashboard / GET /v1/payments/<id>/refunds for duplicate refund objects.

---

## `storepayments:webhook-approved-amount-none-failopen` — Approved webhook auto-credits the order when transaction_amount is present but unparseable — amount binding silently skipped

The amount-mismatch guard only fires when `amount is not None and order_total is not None and amount != order_total`. Verifier correction: a MISSING transaction_amount key defaults to '0' → Decimal('0') which normally mismatches (fail-closed); the fail-open requires the key PRESENT with an unparseable value (null/''/non-numeric) → _amount_or_none returns None → guard skipped → mark_paid executes with no amount verification. Whether MP's GET /v1/payments/<id> can return an approved payment with a present-but-unparseable transaction_amount is a provider fact not verifiable in the repo. No other amount guard exists downstream (mark_paid checks only status transition + stock).

### Trace
- **entrypoint** `StoreApp/domains/storepayments/views/webhook.py:176` — StoreMpWebhookView.post: Signed payment notification enters StoreMpWebhookQuery.
- **propagation** `StoreApp/domains/storepayments/services/webhook.py:64` — _amount_or_none: Returns None on present-but-unparseable transaction_amount; absent key defaults to '0'.
- **sink** `StoreApp/domains/storepayments/services/webhook.py:211` — StoreMpWebhookQuery: elif order_status != 'PAID' and old_status != APPROVED: mark_paid(...) executes whenever the mismatch condition's first conjunct fails — including amount=None.

### Evidence
- `StoreApp/domains/storepayments/services/webhook.py:202` — if amount is not None and order_total is not None and amount != order_total: — a None amount bypasses the guard entirely and reaches mark_paid.
- `StoreApp/domains/storepayments/services/orders_bridge.py:74` — mark_paid has no amount check — only PENDING_PAYMENT status transition plus stock effects.

### Claimed root cause
services/webhook.py treats amount=None as 'cannot compare, proceed' rather than 'cannot verify, do not credit' — the fail-open default contradicts the no-auto-credit-on-mismatch boundary.

### Blockers
- Whether Mercado Pago's payments API can return status='approved' with transaction_amount present but null/empty/non-numeric for any payment type or API version.

### Local validation plan
Unit-test StoreMpWebhookQuery with a mocked get_mp_payment returning status='approved' and transaction_amount=None/unparseable — confirm mark_paid is invoked (expected: yes, demonstrating the fail-open path).

### Deployment-owner check
Owner-observed: inspect real MP payment payloads (GET /v1/payments/<id>) across payment methods to confirm transaction_amount is always numeric for approved payments.

---
