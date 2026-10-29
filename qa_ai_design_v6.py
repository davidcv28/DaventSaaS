"""Escenario de aceptación §9.4 del motor "Diseñar con IA" v6.

Tres tiendas de rubros distintos (comercio, gastronomía, servicios) con la
MISMA entrevista. Para cada una:

  - genera 2+ propuestas y verifica plantillas y firmas de layout distintas;
  - `look.changed` con >= 3 cambios reales, `score.contrast == 100`;
  - `extras.offered[].block.id` dentro de los bloques aiOnly de TEMPLATE_BLOCKS;
  - aplica la propuesta ganadora y relee la web publicada: la piel, el estilo
    y los colores de texto viajaron al `site_theme` y la landing abre en hero
    y cierra en contact;
  - audita 5 pares de contraste × 2 modos sobre el tema emitido.

Uso: venv/Scripts/python.exe qa_ai_design_v6.py
Salida: resumen por tienda + exit code 1 si algo falla.
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DaventProject.settings')
import django

django.setup()

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient

from AdminApp.domains.locations.models import City, Province, ZipCode
from AdminApp.domains.suscriptions.models import Suscription, SuscriptionPlan
from AdminApp.domains.users.models import UserProfile
from StoreApp.domains.catalog.models import Product
from StoreApp.domains.stores.layout_blocks import TEMPLATE_BLOCKS
from StoreApp.domains.stores.models import Store, StoreCustomization, StoreGalleryImage
from StoreApp.domains.stores.services.ai_design import _contrast_ratio
from StoreApp.domains.stores.services import ai_design_recipes as R
from SuscriptionApp.domains.benefits.models import Benefit, PlanBenefit

AI_URL = '/api/stores/ai-design/'
APPLY_URL = '/api/stores/ai-design/apply/'
AI_ONLY = {block for block in R.AI_ELEMENT_ORDER}

CASES = [
    ('comercio', 'Almacén Don Pedro', 'vender_online'),
    ('gastronomia', 'Café La Esquina', 'mostrar_trabajos'),
    ('servicios_profesionales', 'Estudio Contable Sur', 'conseguir_consultas'),
]


def _grant(profile):
    plan = SuscriptionPlan.objects.create(name=f'QA v6 {profile.user.username} {int(time.time())}')
    for code, value in {
        'has_public_link': True, 'has_customization': True, 'has_design_plus': True,
        'has_design_advanced': True, 'has_ai_design': True, 'has_discounts': True,
        'max_gallery_images': 15, 'max_images': 40, 'max_storage_mb': 100,
    }.items():
        kind = Benefit.FLAG if isinstance(value, bool) else Benefit.LIMIT
        benefit = Benefit.objects.get_or_create(code=code, defaults={'label': code, 'kind': kind})[0]
        PlanBenefit.objects.create(
            plan=plan, benefit=benefit,
            enabled=value if kind == Benefit.FLAG else True,
            value=None if kind == Benefit.FLAG else value,
        )
    Suscription.objects.create(
        user=profile, plan_suscription=plan,
        end_date=timezone.now() + timedelta(days=30),
        status=Suscription.STATUS_ACTIVE,
    )


def _fixture(index, rubro, name, username):
    province, _ = Province.objects.get_or_create(name_province='Buenos Aires')
    zipcode, _ = ZipCode.objects.get_or_create(zipcode=f'19{index:02d}')
    city, _ = City.objects.get_or_create(name_city='La Plata', province=province, defaults={'zipcode': zipcode})
    user = User.objects.create_user(username=username, email=f'{username}@gmail.com', password='Xq7#mP2vL9bT')
    profile = UserProfile.objects.create(
        user=user, first_name='Ana', last_name='Perez', phone=f'11{index}2233445',
        document=f'30{index}44556', province=province, city=city, email_verified=True,
    )
    _grant(profile)
    store = Store.objects.create(user=profile, slug=f'qa-v6-{rubro.replace("_", "-")}', is_published=True)
    custom = StoreCustomization.objects.create(
        store=store, display_name=name,
        headline=f'{name}: {rubro.replace("_", " ")} con trato de barrio',
        description='Productos y atención de siempre.',
        about_text='Hacemos las cosas bien desde el primer día.', about_years=12,
        site_templates=['landing', 'catalog', 'services'], template='cobre',
        whatsapp='5492215551234',
        services=[{'icon': 'package', 'title': 'Envío', 'text': 'A domicilio en 24 h'},
                  {'icon': 'star', 'title': 'Calidad', 'text': 'Selección propia'},
                  {'icon': 'clock', 'title': 'Horarios', 'text': 'Lunes a sábado'},
                  {'icon': 'heart', 'title': 'Asesoría', 'text': 'Te ayudamos a elegir'}],
        stats=[{'value': '12', 'label': 'Años'}, {'value': '+2k', 'label': 'Clientes'},
               {'value': '4.9', 'label': 'Puntaje'}, {'value': '24 h', 'label': 'Entrega'}],
        testimonials=[{'name': 'Laura', 'detail': 'Vecina', 'text': 'Siempre impecable.'},
                      {'name': 'Martín', 'detail': 'Cliente', 'text': 'Atención de diez.'},
                      {'name': 'Sofía', 'detail': 'Cliente', 'text': 'Volvería a elegirlos.'}],
        faqs=[{'q': '¿Hacen envíos?', 'a': 'Sí, a toda la ciudad.'},
              {'q': '¿Aceptan tarjeta?', 'a': 'Sí, débito y crédito.'},
              {'q': '¿Tienen local?', 'a': 'Sí, en el centro.'},
              {'q': '¿Puedo encargar?', 'a': 'Sí, por WhatsApp.'}],
    )
    for n in range(6):
        Product.objects.create(
            store=store, name=f'{rubro.title()} producto {n + 1}', price=1000 + n * 250,
            description='Hecho con materia prima local.', image_key=f'qa/v6/{index}-{n}.webp', is_active=True,
        )
    for n in range(8):
        StoreGalleryImage.objects.create(
            store=store, image_key=f'qa/v6/g{index}-{n}.webp', position=n, image_size=1024,
        )
    return store, custom


def _pairs(theme):
    sets = theme.get('styleColors') or {}
    palette = theme.get('palette') or {}
    band = palette.get('secondary') or '#000000'
    pairs = []
    for mode in ('light', 'dark'):
        sc = sets.get(mode) or {}
        fonts = sc.get('fonts') or {}
        cont = sc.get('containers') or {}
        for fg, bg, label in (
            (fonts.get('heading'), cont.get('bg'), f'{mode} heading/bg'),
            (fonts.get('body'), cont.get('bg'), f'{mode} body/bg'),
            (fonts.get('muted'), cont.get('bg'), f'{mode} muted/bg'),
            (fonts.get('body'), cont.get('surface'), f'{mode} body/surface'),
            (fonts.get('muted'), cont.get('surface'), f'{mode} muted/surface'),
            ('#ffffff', band, f'{mode} blanco/banda'),
        ):
            if fg and bg:
                pairs.append((fg, bg, label))
    return pairs


def _blocks(layout_config):
    landing = (layout_config or {}).get('landing') or {}
    if isinstance(landing, dict):
        return landing.get('blocks') or []
    return landing or []


def _signature(proposal):
    landing = _blocks(proposal.get('layout_config'))
    ids = tuple(block.get('id') for block in landing)
    variants = tuple((block.get('id'), block.get('variant')) for block in landing)
    return proposal.get('template'), ids, variants


def run():
    failures = []
    cache.clear()
    for index, (rubro, name, goal) in enumerate(CASES, start=1):
        username = f'qa_v6_{rubro}'
        User.objects.filter(username=username).delete()
        store, _ = _fixture(index, rubro, name, username)
        client = APIClient()
        client.defaults['HTTP_HOST'] = 'localhost'
        client.force_authenticate(user=store.user.user)
        payload = {
            'rubro': rubro, 'tone': 'moderno', 'goals': [goal],
            'public': 'clientes', 'styles': ['editorial', 'minimal'],
            'night': 'auto', 'accept_extras': True,
        }
        response = client.post(AI_URL, payload, format='json')
        if response.status_code != 200:
            failures.append(f'{rubro}: generate {response.status_code} {response.content[:200]!r}')
            continue
        data = response.json()
        proposals = data.get('proposals') or []
        if data.get('engine') != 'ai-design/6':
            failures.append(f'{rubro}: engine {data.get("engine")!r}')
        if len(proposals) < 2:
            failures.append(f'{rubro}: {len(proposals)} propuestas')
        if len({p['template'] for p in proposals}) != len(proposals):
            failures.append(f'{rubro}: plantillas repetidas {[p["template"] for p in proposals]}')
        if len({_signature(p) for p in proposals}) != len(proposals):
            failures.append(f'{rubro}: firma de layout repetida')
        for proposal in proposals:
            changed = (proposal.get('look') or {}).get('changed') or []
            if len(changed) < 3:
                failures.append(f'{rubro}/{proposal["id"]}: look.changed {changed}')
            if (proposal.get('score') or {}).get('contrast') != 100:
                failures.append(f'{rubro}/{proposal["id"]}: score.contrast {(proposal.get("score") or {}).get("contrast")}')
            for extra in (proposal.get('extras') or {}).get('offered') or []:
                block_id = (extra.get('block') or {}).get('id')
                if block_id not in TEMPLATE_BLOCKS['landing'] or block_id not in AI_ONLY:
                    failures.append(f'{rubro}/{proposal["id"]}: extra fuera de catálogo {block_id!r}')
            for pair in _pairs(proposal.get('site_theme') or {}):
                if _contrast_ratio(pair[0], pair[1]) < 4.5:
                    failures.append(f'{rubro}/{proposal["id"]}: contraste {pair[2]} < 4.5')
        winner = proposals[0]
        applied = client.post(
            APPLY_URL,
            {'seed': data['seed'], 'proposal_id': winner['id']},
            format='json',
        )
        if applied.status_code != 200:
            failures.append(f'{rubro}: apply {applied.status_code} {applied.content[:200]!r}')
            continue
        custom = StoreCustomization.objects.get(store=store)
        theme = custom.site_theme or {}
        for key in ('skin', 'style', 'styleColors'):
            if not theme.get(key):
                failures.append(f'{rubro}: site_theme sin {key}')
        if not ((theme.get('typography') or {}).get('roles')):
            failures.append(f'{rubro}: site_theme sin typography.roles')
        if not custom.layout_config:
            failures.append(f'{rubro}: apply no publicó layout')
        landing = _blocks(custom.layout_config)
        ids = [block.get('id') for block in landing if block.get('enabled', True)]
        if ids and (ids[0] != 'hero' or ids[-1] != 'contact'):
            failures.append(f'{rubro}: landing {ids[0]}…{ids[-1]}')
        public = client.get(f'/api/stores/public/{store.slug}/')
        if public.status_code != 200:
            failures.append(f'{rubro}: público {public.status_code}')
        else:
            published = ((public.json().get('customization') or {}).get('site_theme') or {})
            if (published.get('skin') or {}).get('id') != (theme.get('skin') or {}).get('id'):
                failures.append(f'{rubro}: la web pública no trae la piel aplicada')
        for pair in _pairs(theme):
            if _contrast_ratio(pair[0], pair[1]) < 4.5:
                failures.append(f'{rubro}: tema aplicado, contraste {pair[2]} < 4.5')
        print(f'[{rubro}] {len(proposals)} propuestas, plantillas {[p["template"] for p in proposals]}, '
              f'piel aplicada {(theme.get("skin") or {}).get("id")}, extras '
              f'{(winner.get("extras") or {}).get("applied") or []}')
    if failures:
        print('\nFALLAS:')
        for item in failures:
            print(' -', item)
        return 1
    print('\nOK: 3 tiendas, propuestas distintas, extras válidos, tema publicado y contraste AA.')
    return 0


if __name__ == '__main__':
    sys.exit(run())
