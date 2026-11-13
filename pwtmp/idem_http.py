import json, re, time, threading
import requests
from concurrent.futures import ThreadPoolExecutor

BASE = 'http://localhost:8000'
creds = json.load(open('pwtmp/idem_creds.json'))
CA = creds['customer_access']
H = {'Authorization': f'Bearer {CA}'}
OUT = {}

def par(fn, n=2):
    with ThreadPoolExecutor(n) as ex:
        return list(ex.map(lambda _: fn(), range(n)))

# ---------- CART ----------
def cart_get():
    return requests.get(f'{BASE}/api/cart/davent/', headers=H, timeout=15)

# clear first
requests.delete(f'{BASE}/api/cart/davent/items/', headers=H, timeout=15)

def add():
    return requests.post(f'{BASE}/api/cart/davent/items/', headers=H, json={'product_id': 817, 'qty': 2}, timeout=15)

r = par(add, 2)
OUT['cart_add_parallel'] = [(x.status_code) for x in r]
time.sleep(0.3)
body = cart_get().json()
OUT['cart_after_parallel_add'] = [(i['id'], i['product_id'], i['qty']) for i in body['items']]

# sequential retry same payload
requests.post(f'{BASE}/api/cart/davent/items/', headers=H, json={'product_id': 817, 'qty': 2}, timeout=15)
body = cart_get().json()
OUT['cart_after_retry_same_qty'] = [(i['id'], i['qty']) for i in body['items']]

# PATCH qty retry concurrent (target qty 5)
iid = body['items'][0]['id']
def patchq():
    return requests.patch(f'{BASE}/api/cart/davent/items/{iid}/', headers=H, json={'qty': 5}, timeout=15)
r = par(patchq, 2)
OUT['cart_patch_parallel'] = [x.status_code for x in r]
body = cart_get().json()
OUT['cart_after_patch'] = [(i['id'], i['qty']) for i in body['items']]

# DELETE sequential x2
d1 = requests.delete(f'{BASE}/api/cart/davent/items/{iid}/', headers=H, timeout=15)
d2 = requests.delete(f'{BASE}/api/cart/davent/items/{iid}/', headers=H, timeout=15)
OUT['cart_delete_seq'] = [d1.status_code, d2.status_code, d2.text[:200]]

# DELETE concurrent x2 (fresh item)
requests.post(f'{BASE}/api/cart/davent/items/', headers=H, json={'product_id': 817, 'qty': 1}, timeout=15)
iid2 = cart_get().json()['items'][0]['id']
r = par(lambda: requests.delete(f'{BASE}/api/cart/davent/items/{iid2}/', headers=H, timeout=15), 2)
OUT['cart_delete_parallel'] = [x.status_code for x in r]

# ---------- REVIEWS ----------
prod = 817
base_reviews = requests.get(f'{BASE}/api/stores/public/davent/products/{prod}/reviews/', timeout=15).json()
OUT['reviews_before'] = len(base_reviews)

def post_review(text):
    return requests.post(f'{BASE}/api/stores/public/davent/products/{prod}/reviews/',
        headers=H, json={'is_positive': True, 'text': text}, timeout=15)

# parallel double-submit same review
r = par(lambda: post_review('Muy bueno, idem-test'), 2)
OUT['review_parallel'] = [x.status_code for x in r]
time.sleep(0.5)
after = requests.get(f'{BASE}/api/stores/public/davent/products/{prod}/reviews/', timeout=15).json()
mine = [rv for rv in after if rv.get('text') == 'Muy bueno, idem-test']
OUT['reviews_mine_count'] = len(mine)

# sequential second attempt (dedupe path)
r2 = post_review('Otra distinta')
OUT['review_second_attempt'] = r2.status_code

# ---------- CONTACT ----------
def solve_cap():
    q = requests.get(f'{BASE}/api/stores/public/davent/contact/captcha/', timeout=15).json()
    m = re.search(r'(\d+)\s*[×x*]\s*(\d+)', q['question'])
    if m:
        ans = int(m.group(1)) * int(m.group(2))
    else:
        m = re.search(r'(\d+)\s*-\s*(\d+)', q['question'])
        ans = int(m.group(1)) - int(m.group(2))
    return q['challenge_id'], ans

cid, ans = solve_cap()
time.sleep(3.5)  # CAPTCHA_MIN_SECONDS
def send_contact():
    return requests.post(f'{BASE}/api/stores/public/davent/contact/', json={
        'name': 'Idem Test', 'email': 'idem@test.local', 'message': 'hola idempotencia',
        'challenge_id': cid, 'captcha_answer': str(ans), 'website': ''}, timeout=20)
r = par(send_contact, 2)
OUT['contact_parallel_same_challenge'] = [x.status_code for x in r]

# second distinct challenge, same content -> second mail?
cid2, ans2 = solve_cap()
time.sleep(3.5)
r2 = requests.post(f'{BASE}/api/stores/public/davent/contact/', json={
    'name': 'Idem Test', 'email': 'idem@test.local', 'message': 'hola idempotencia',
    'challenge_id': cid2, 'captcha_answer': str(ans2), 'website': ''}, timeout=20)
OUT['contact_new_challenge_same_content'] = r2.status_code

# ---------- REGISTER race ----------
import uuid
em = f'idem-{uuid.uuid4().hex[:8]}@test.local'
payload = {'username': em.split('@')[0], 'email': em, 'password': 'ClaveSegura123!',
           'confirm_password': 'ClaveSegura123!', 'phone': '1155555555', 'accept_terms': True}
def reg():
    return requests.post(f'{BASE}/api/register/', json=payload, timeout=30)
r = par(reg, 2)
OUT['register_parallel'] = [x.status_code for x in r]
OUT['register_email'] = em

# ---------- REFRESH replay ----------
rt = creds['refresh']
def refr():
    return requests.post(f'{BASE}/api/token/refresh/', json={'refresh': rt}, timeout=20)
r = par(refr, 2)
OUT['refresh_parallel'] = [x.status_code for x in r]
OUT['refresh_parallel_new_access'] = [bool(x.json().get('access')) for x in r]
# a third serial attempt with the same old refresh (should be blacklisted)
r3 = refr()
OUT['refresh_serial_replay'] = r3.status_code

json.dump(OUT, open('pwtmp/idem_http_out.json', 'w'), indent=2)
print(json.dumps(OUT, indent=2))
