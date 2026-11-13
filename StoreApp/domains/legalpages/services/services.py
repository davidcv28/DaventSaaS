import logging
import re

from django.conf import settings
from django.core.mail import send_mail
from django.http import Http404
from django.shortcuts import get_object_or_404

from StoreApp.domains.legalpages.models import ReturnRequest, StoreLegalPage
from StoreApp.domains.stores.models import Store
from StoreApp.domains.stores.services import contact_target, profile_has_benefit

"""
Servicios del dominio legalpages.

- interpolate_text: los textos legales guardan placeholders {{...}} que se
  resuelven AL SERVIR la página pública con los datos fiscales vigentes
  del StoreFiscalProfile — una corrección del dueño se refleja sola.
- public_store_or_404: misma regla que el resto de endpoints públicos de
  la web de la tienda (publicada + no bloqueada + beneficio has_public_link).
- notify_return_request: aviso in-app al dueño (KIND_SYSTEM) + email al
  contact_email del negocio (task Celery, nunca bloquea el request).
"""
logger                  =   logging.getLogger(__name__)
#=========================================
# INTERPOLACIÓN FISCAL (placeholders de los textos legales)
#=========================================
PLACEHOLDER_RE          =   re.compile(r'\{\{\s*([a-z_]+)\s*\}\}')

def _store_display_name(store):
    customization   =   getattr(store, 'customization', None)
    display         =   (getattr(customization, 'display_name', '') or '').strip()
    if display:
        return display
    business        =   (getattr(store.user, 'business_name', '') or '').strip()
    return business or store.slug

def fiscal_context(store):
    """
    Valores de los placeholders para ESTE store. Los datos fiscales que
    falten quedan como 'a completar' (los textos base ya lo contemplan);
    legal_name cae al nombre comercial y tax_condition a Consumidor Final.
    """
    profile         =   getattr(store, 'fiscal_profile', None)
    customization   =   getattr(store, 'customization', None)
    contact_email   =   ''
    if customization is not None:
        contact_email   =   (customization.contact_email or '').strip()
    if not contact_email:
        contact_email   =   (getattr(store.user.user, 'email', '') or '').strip()
    return {
        'store_name'        :   _store_display_name(store),
        'contact_email'     :   contact_email or 'a completar',
        'legal_name'        :   ((profile.legal_name if profile else '') or '').strip() or _store_display_name(store),
        'cuit'              :   ((profile.cuit if profile else '') or '').strip() or 'a completar',
        'fiscal_address'    :   ((profile.fiscal_address if profile else '') or '').strip() or 'a completar',
        'tax_condition'     :   (profile.get_tax_condition_display() if profile else '') or 'Consumidor Final',
    }

def interpolate_text(text, store):
    """
    Sustituye {{placeholder}} por el valor vigente. Placeholders
    desconocidos quedan literales (no se inventan datos).
    """
    if not text:
        return ''
    context     =   fiscal_context(store)
    return PLACEHOLDER_RE.sub(lambda match: context.get(match.group(1), match.group(0)), text)
#=========================================
# RESOLUCIÓN DE TIENDA PÚBLICA
#=========================================
def public_store_or_404(slug):
    """
    Misma regla que _contact_store/_review_store del viewset de stores:
    tienda publicada, no bloqueada y con el link público habilitado por el
    plan. Cualquier otra cosa es 404 (no se revela que la tienda existe).
    """
    store       =   get_object_or_404(
        Store.objects.select_related('user__user', 'customization', 'fiscal_profile'),
        slug = slug, is_published = True, is_blocked = False,
    )
    if not profile_has_benefit(store.user, 'has_public_link'):
        raise Http404
    return store
#=========================================
# SERIALIZACIÓN PÚBLICA / DUEÑO
#=========================================
def legal_page_payload(page, store):
    """
    Payload de una página. Título y cuerpo son SIEMPRE los textos base de
    la plataforma (DEFAULT_TITLES/DEFAULT_BODIES) interpolados con los
    datos fiscales vigentes — el dueño no puede modificarlos, solo
    publicar/ocultar. Devuelve el texto final que ve el comprador.
    """
    title   =   interpolate_text(StoreLegalPage.default_title(page.kind), store)
    body    =   interpolate_text(StoreLegalPage.default_body(page.kind, store), store)
    persisted   =   page.pk is not None
    return {
        'kind'          :   page.kind,
        'kind_label'    :   StoreLegalPage.KIND_LABELS.get(page.kind, page.kind),
        'title'         :   title,
        'body'          :   body,
        'is_published'  :   bool(page.is_published),
        'version'       :   page.version or 1,
        'updated_at'    :   page.updated_at.isoformat() if page.updated_at else None,
        'persisted'     :   persisted,
    }

def legal_detail_payload(page, store):
    """Detalle público de UNA página: cuerpo interpolado + datos fiscales."""
    profile     =   getattr(store, 'fiscal_profile', None)
    fiscal      =   {
        'legal_name'        :   (profile.legal_name if profile else '') or '',
        'cuit'              :   (profile.cuit if profile else '') or '',
        'tax_condition'     :   (profile.get_tax_condition_display() if profile else '') or '',
        'fiscal_address'    :   (profile.fiscal_address if profile else '') or '',
        'point_of_sale'     :   (profile.point_of_sale if profile else '') or '',
    }
    payload     =   legal_page_payload(page, store)
    payload.pop('is_published', None)
    payload.pop('persisted', None)
    payload['fiscal']           =   fiscal
    payload['fiscal_complete']  =   bool(profile and profile.is_complete)
    return payload
#=========================================
# GUARDADO (dueño — solo publicación)
#=========================================
def save_legal_page(store, kind, data):
    """
    Upsert de la página del dueño. `data` = validated_data del
    LegalPageWriteSerializer: solo `is_published` (el contenido es fijo
    de la plataforma). Devuelve (page, created).
    """
    page, created  =   StoreLegalPage.objects.get_or_create(
        store           =   store,
        kind            =   kind,
        defaults        =   {'is_published': bool(data.get('is_published', True))},
    )
    if not created and 'is_published' in data:
        page.is_published   =   bool(data['is_published'])
        page.save()
    return page, created
#=========================================
# ARREPENTIMIENTO (notificación + email al dueño)
#=========================================
#Sección del dashboard destino del aviso: tab 'legal' de "Vender online"
#("Páginas legales y devoluciones") — el target es el id del tab en
#tabGroups.selling del front.
RETURN_NOTIFICATION_TARGET   =   'legal'

def notify_return_request(store, req : ReturnRequest):
    """
    Aviso al dueño: Notification KIND_SYSTEM deduplicada por solicitud
    (cada pedido de devolución es un evento distinto) + email al
    contact_email del negocio o al email de la cuenta. Nada de esto puede
    romper el alta: la solicitud ya quedó persistida.
    """
    auth_user   =   getattr(store.user, 'user', None)
    if auth_user is not None:
        try:
            from AdminApp.domains.notifications.models import Notification
            from AdminApp.domains.notifications.services import upsert_notification
            reason_label    =   req.get_reason_display()
            order_bit       =   f' · pedido {req.order_ref}' if req.order_ref else ''
            upsert_notification(
                auth_user,
                Notification.KIND_SYSTEM,
                'Solicitud de devolución',
                body        =   f'{req.name} <{req.customer_email}> — {reason_label}{order_bit}'[:500],
                target      =   RETURN_NOTIFICATION_TARGET,
                dedupe_key  =   f'return_request:{req.pk}',
            )
        except Exception:
            logger.exception('No se pudo crear la notificación de devolución %s', req.pk)
    try:
        from StoreApp.domains.legalpages.tasks import send_return_request_email
        send_return_request_email.delay(req.pk)
    except Exception:
        #Sin broker el .delay() puede fallar: la solicitud ya está a salvo
        #y el email es un canal secundario (la notificación in-app quedó).
        logger.exception('No se pudo encolar el email de devolución %s', req.pk)

def deliver_return_request_email(req : ReturnRequest) -> bool:
    """
    Envío real del aviso (lo corre la task de Celery). Texto plano al
    contact_email de la tienda o al email del dueño. False sin destino o
    con SMTP caído — el caller (task) reintenta.
    """
    target      =   contact_target(req.store)
    if not target:
        return False
    shop        =   _store_display_name(req.store)
    order_bit   =   f'Pedido: {req.order_ref}\n' if req.order_ref else 'Pedido: (sin referencia)\n'
    body        =   (
        f'Recibiste una solicitud de devolución en tu web ({req.store.slug}).\n\n'
        f'{order_bit}'
        f'Nombre y apellido: {req.name}\n'
        f'Email: {req.customer_email}\n'
        f'Documento: {req.document or "-"}\n'
        f'Teléfono: {req.phone or "-"}\n'
        f'Domicilio: {req.address or "-"}\n'
        f'Motivo: {req.get_reason_display()}\n\n'
        f'Detalle:\n{req.details or "-"}\n\n'
        f'Podés gestionarla desde el panel → sección Mis productos → Solicitudes de devolución.'
    )
    try:
        send_mail(
            subject         =   f'[Web] Solicitud de devolución — {shop}',
            message         =   body,
            from_email      =   settings.DEFAULT_FROM_EMAIL,
            recipient_list  =   [target],
            fail_silently   =   False,
        )
    except Exception:
        logger.exception('No se pudo enviar el email de devolución %s', req.pk)
        return False
    return True
