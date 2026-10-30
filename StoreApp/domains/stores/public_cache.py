from DaventProject.cache_utils import (
    cache_add,
    cache_delete,
    cache_get_many,
    cache_incr,
)

"""

Versionado del cache server-side de las webs públicas
(GET /api/stores/public/<slug>/ y .../catalog/).

Las keys llevan (época global, versión de la tienda): los post_save /
post_delete de los modelos que alimentan el payload las incrementan, así
una edición del dueño (tema, catálogo, servicios, imágenes, perfil o
suscripción) se ve al instante y las entradas viejas expiran solas por TTL.
Los senders se conectan en el models.py de cada app dueña del modelo —
misma convención que _bust_benefits_cache de suscriptions.

"""
_EPOCH_KEY      =   'stores:pub:epoch'
_VERSION_KEY    =   'stores:pub:ver:{store_id}'
#Las keys de versión no pueden ser eternas: cada tienda histórica dejaba su
#contador en Redis para siempre. 7 días alcanza de sobra (las entradas del
#payload viven minutos) y el bump re-crea la key si expiró.
_VERSION_TTL    =   60 * 60 * 24 * 7
#=========================================
# STAMP (una sola ida al backend: epoch + versión)
#=========================================
def public_cache_stamp(store_id):
    keys        =   [_EPOCH_KEY, _VERSION_KEY.format(store_id = store_id)]
    values      =   cache_get_many(keys)
    return (values.get(_EPOCH_KEY) or 0, values.get(keys[1]) or 0)
#=========================================
# BUMPERS (incr atómico en locmem y redis; la entrada vieja queda huérfana)
#=========================================
def _bump(key):
    try:
        if cache_incr(key) is None:
            #Backend caído: el payload viejo expira por TTL, no se rompe nada.
            return
    except ValueError:
        cache_add(key, 1, timeout = _VERSION_TTL)

def bump_public_store(store_id):
    #Post_save/post_delete de un modelo colgado de la tienda (customización,
    #imágenes, chatbot, servicios, catálogo). store_id viaja en la FK — no
    #hace falta fetch y sobrevive a los post_delete en cascada.
    if store_id:
        _bump(_VERSION_KEY.format(store_id = store_id))

def bump_public_owner(profile_id):
    #Cambio del lado del dueño (UserProfile, Suscription): la tienda cuelga
    #del perfil por OneToOne — se resuelve el id en el camino de escritura.
    from StoreApp.domains.stores.models.models import Store
    for store_id in Store.objects.filter(user_id = profile_id).values_list('pk', flat = True):
        bump_public_store(store_id)

def bump_public_epoch():
    #Cambio global que toca TODOS los payloads (p.ej. PlanBenefit: altera
    #los beneficios/allowed_templates de cada web con ese plan).
    _bump(_EPOCH_KEY)

def forget_public_store(store_id):
    #post_delete del Store: sin la tienda su key de versión queda huérfana
    #hasta el TTL — se borra explícitamente (bumpear no sirve, nadie la lee).
    if store_id:
        cache_delete(_VERSION_KEY.format(store_id = store_id))
