from django.db.models.signals import post_delete, post_save

from StoreApp.domains.design.models import DesignIconStyle, DesignPattern, DesignStyle

"""
El catálogo de diseño alimenta la web pública de TODAS las tiendas: un
patrón o estilo editado cambia el documento servido por
`/public/<slug>/pattern/` aunque la tienda no se haya tocado. Se bumpea la
época global del cache público para que el cambio se vea al instante.
"""
def _bump_public_catalog(sender, **kwargs):
    from StoreApp.domains.stores.public_cache import bump_public_epoch
    try:
        bump_public_epoch()
    except Exception:
        #Backend de cache caído: el payload viejo expira por TTL.
        pass


for _model in (DesignPattern, DesignStyle, DesignIconStyle):
    post_save.connect(
        _bump_public_catalog, sender = _model,
        dispatch_uid = f'design:{_model.__name__}:save',
    )
    post_delete.connect(
        _bump_public_catalog, sender = _model,
        dispatch_uid = f'design:{_model.__name__}:delete',
    )
