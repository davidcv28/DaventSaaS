import copy

from django.utils import timezone

from StoreApp.domains.stores.models import StoreCustomization, StoreSyncEvent, StudioVersion
from StoreApp.domains.stores.services.services import allowed_templates_of

"""
Sección "Sincronización" del dashboard del dueño: bitácora de
operaciones que afectan la web pública (StoreSyncEvent) y la corrida
manual que procesa lo pendiente — hoy, el borrador de diseño del Studio
sin publicar. La publicación del borrador vive acá
(publish_design_draft) y la reusa el endpoint customization/publish:
una sola lógica, dos puertas de entrada.
"""
#=========================================
# DETECCIÓN DE BORRADOR SIN PUBLICAR
#=========================================
def design_draft_pending(store):
    """True si el Studio tiene cambios de diseño sin publicar (misma
    regla que has_unpublished del serializer)."""
    customization   =   StoreCustomization.objects.filter(store = store).first()
    if customization is None:
        return False
    return (
        (customization.layout_config_draft or {}) != (customization.layout_config or {})
        or (customization.site_theme_draft or {}) != (customization.site_theme or {})
        or customization.template_draft != customization.template
    )
#=========================================
# REGISTRO DE EVENTOS (un fallo de log nunca rompe el guardado)
#=========================================
def record_sync_event(store, op, detail = '', status = 'done'):
    try:
        StoreSyncEvent.objects.create(
            store           =   store,
            op              =   op,
            status          =   status,
            detail          =   str(detail or '')[:300],
            processed_at    =   timezone.now() if status == 'done' else None,
        )
    except Exception:
        #El evento es observabilidad del panel: no puede tirar el save.
        pass
#=========================================
# PUBLICAR BORRADOR (lógica única — endpoint publish y run_sync)
#=========================================
def publish_design_draft(store, note = ''):
    """El borrador del Studio pasa a ser lo publicado y queda el
    snapshot en el historial (últimas StudioVersion.MAX_PER_STORE por
    tienda). Devuelve la customization ya guardada."""
    customization, _    =   StoreCustomization.objects.get_or_create(store = store)
    customization.layout_config =   copy.deepcopy(customization.layout_config_draft) or {}
    customization.site_theme    =   copy.deepcopy(customization.site_theme_draft) or {}
    #La plantilla del borrador publica solo si sigue en la whitelist
    #del plan (una baja de plan no la re-habilita); si no aplica, el
    #borrador queda resuelto al publicado — has_unpublished limpio.
    if customization.template_draft in allowed_templates_of(store.user):
        customization.template    =   customization.template_draft
    customization.template_draft    =   customization.template
    customization.save(update_fields = ['layout_config', 'site_theme', 'template', 'template_draft', 'updated_at'])
    StudioVersion.objects.create(
        store       =   store,
        snapshot    =   {
            'template'      :   customization.template,
            'layout_config' :   customization.layout_config,
            'site_theme'    :   customization.site_theme,
        },
        note        =   note,
    )
    stale               =   list(StudioVersion.objects.filter(store = store).values_list('pk', flat = True)[StudioVersion.MAX_PER_STORE:])
    if stale:
        StudioVersion.objects.filter(pk__in = stale).delete()
    return customization
#=========================================
# ESTADO DE SINCRONIZACIÓN (GET /api/stores/sync/)
#=========================================
def sync_state(store):
    events          =   list(StoreSyncEvent.objects.filter(store = store)[:50])
    draft_pending   =   design_draft_pending(store)
    pending_count   =   sum(1 for event in events if event.status == 'pending') + (1 if draft_pending else 0)
    last            =   next((event for event in events if event.status == 'done'), None)
    operations      =   [
        {
            'id'         :  event.pk,
            'op'         :  event.op,
            'status'     :  event.status,
            'attempts'   :  event.attempts,
            'detail'     :  event.detail,
            'created_at' :  event.created_at,
        }
        for event in events
    ]
    if draft_pending:
        #Pseudo-operación al tope: el borrador sin publicar es lo
        #pendiente más visible del dueño.
        operations.insert(
            0,
            {
                'id'         :  None,
                'op'         :  'publish-diseno',
                'status'     :  'pending',
                'attempts'   :  0,
                'detail'     :  'Cambios de diseño sin publicar',
                'created_at' :  None,
            },
        )
    return {
        'pending_count' :   pending_count,
        'last_sync_at'  :   (last.processed_at or last.created_at) if last else None,
        'operations'    :   operations,
    }
#=========================================
# RUN SYNC (POST /api/stores/sync/run/)
#=========================================
def run_sync(store):
    """Procesa lo pendiente: publica el borrador de diseño si existe y
    marca los eventos 'pending' como resueltos."""
    if design_draft_pending(store):
        publish_design_draft(store, note = 'Sincronización manual')
        record_sync_event(store, 'publish-design', 'Publicación de cambios de diseño')
    now     =   timezone.now()
    StoreSyncEvent.objects.filter(store = store, status = 'pending').update(
        status          =   'done',
        processed_at    =   now,
    )
    return sync_state(store)
