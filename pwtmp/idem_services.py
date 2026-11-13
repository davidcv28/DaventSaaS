"""
Service-level concurrency attacks (run inside manage.py shell context via
`manage.py shell < file` or exec(open(...).read())).
"""
import threading, time, json, uuid
from unittest.mock import patch

from django.db import connection, close_old_connections
from django.contrib.auth.models import User
from rest_framework import serializers

OUT = {}

# ---------- helpers ----------
def run_threads(fn, n=2):
    res = [None] * n
    b = threading.Barrier(n)
    def w(i):
        b.wait()
        try:
            res[i] = fn()
        except Exception as e:
            res[i] = f'EXC:{type(e).__name__}:{str(e)[:160]}'
        finally:
            close_old_connections()
    ts = [threading.Thread(target=w, args=(i,)) for i in range(n)]
    [t.start() for t in ts]; [t.join() for t in ts]
    return res

def mkprofile(tag):
    from AdminApp.domains.users.models import UserProfile
    u = User.objects.create(username=f'idem-{tag}-{uuid.uuid4().hex[:6]}', email=f'{tag}-{uuid.uuid4().hex[:6]}@t.local')
    return UserProfile.objects.create(user=u)

from AdminApp.domains.suscriptions.models import Coupon, CouponRedemption, SuscriptionPlan
from AdminApp.domains.suscriptions.services import RedeemCouponQuery
plan = SuscriptionPlan.objects.filter(is_trial=False).first()

# ---------- COUPON: same profile, 2 concurrent redeems ----------
code = 'IDEM' + uuid.uuid4().hex[:6].upper()
coupon = Coupon.objects.create(code=code, plan=plan, days=30, max_uses=100)
p = mkprofile('c1')
def redeem():
    try:
        RedeemCouponQuery(p, code)
        return 'OK'
    except serializers.ValidationError as e:
        return f'400:{e.detail}'
res = run_threads(redeem, 2)
OUT['coupon_same_profile'] = res
OUT['coupon_same_profile_redemptions'] = CouponRedemption.objects.filter(coupon=coupon).count()

# ---------- COUPON: max_uses=1, two profiles ----------
code2 = 'IDEM' + uuid.uuid4().hex[:6].upper()
coupon2 = Coupon.objects.create(code=code2, plan=plan, days=30, max_uses=1)
pa, pb = mkprofile('c2'), mkprofile('c3')
def ra():
    try:
        RedeemCouponQuery(pa, code2); return 'OK-a'
    except serializers.ValidationError as e:
        return f'400:{e.detail}'
def rb():
    try:
        RedeemCouponQuery(pb, code2); return 'OK-b'
    except serializers.ValidationError as e:
        return f'400:{e.detail}'
res = run_threads(lambda: None, 0)  # noop
b = threading.Barrier(2)
res2 = [None, None]
def w(i, f):
    b.wait()
    try: res2[i] = f()
    except Exception as e: res2[i] = f'EXC:{e}'
    finally: close_old_connections()
t1, t2 = threading.Thread(target=w, args=(0, ra)), threading.Thread(target=w, args=(1, rb))
t1.start(); t2.start(); t1.join(); t2.join()
OUT['coupon_maxuses1'] = res2
OUT['coupon_maxuses1_redemptions'] = CouponRedemption.objects.filter(coupon=coupon2).count()

# ---------- MP WEBHOOK redelivery ----------
from StoreApp.domains.stores.models import Store
from StoreApp.domains.orders.models import Order
from StoreApp.domains.storepayments.services import webhook as wh
from StoreApp.domains.storepayments.models import MpPayment

store = Store.objects.get(slug='davent')
order = Order.objects.filter(store=store, status='PENDING_PAYMENT', payment_method='mp').first()
if order is None:
    # make one manually: minimal fields
    order = Order.objects.filter(store=store, status='PENDING_PAYMENT').first()
    order.payment_method = 'mp'; order.save(update_fields=['payment_method'])
pay_id = '777001' + uuid.uuid4().hex[:6]
fake = {
    'id': int(''.join(filter(str.isdigit, pay_id)) or '1'),
    'status': 'approved', 'status_detail': 'accredited',
    'transaction_amount': float(order.total), 'currency_id': 'ARS',
    'external_reference': f'ord:{order.tracking_token}', 'live_mode': True,
}
with patch.object(wh.mp_client, 'get_mp_payment', return_value=fake):
    with patch.object(wh, '_reject_test_payment', return_value=None):
        r1 = wh.StoreMpWebhookQuery(store, str(fake['id']))
        # redelivery (serial)
        r2 = wh.StoreMpWebhookQuery(store, str(fake['id']))
OUT['webhook_records'] = MpPayment.objects.filter(mp_payment_id=str(fake['id'])).count()
from StoreApp.domains.orders.models import Order as O
o = O.objects.get(pk=order.pk)
OUT['webhook_order_status'] = o.status
from StoreApp.domains.orders.models import OrderEvent
OUT['webhook_events'] = list(OrderEvent.objects.filter(order=o).values_list('kind', flat=True))

# ---------- REVIEW model: unique constraint? ----------
from StoreApp.domains.catalog.models import ProductReview
OUT['review_constraints'] = [str(c) for c in ProductReview._meta.constraints]
OUT['review_unique_together'] = ProductReview._meta.unique_together

print('\n===RESULTS===')
print(json.dumps(OUT, indent=2, default=str))
