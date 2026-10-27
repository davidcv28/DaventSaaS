from django.core.cache import cache
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
#=========================================
# STAMP (una sola ida al backend: epoch + versión)
#=========================================
def public_cache_stamp(store_id):
    keys        =   [_EPOCH_KEY, _VERSION_KEY.format(store_id = store_id)]
    values      =   cache.get_many(keys)
    return (values.get(_EPOCH_KEY) or 0, values.get(keys[1]) or 0)
#=========================================
# BUMPERS (incr atómico en locmem y redis; la entrada vieja queda huérfana)
#=========================================
def _bump(key):
    try:
        cache.incr(key)
    except ValueError:
        cache.add(key, 1, timeout = None)

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
