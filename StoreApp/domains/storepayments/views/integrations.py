"""
Endpoints del panel "Cobros" del dueño — las tres configs que el CRUD
de métodos manuales (views/config.py) no cubre:

- GET|PUT /api/store-payments/fiscal-profile/  → StoreFiscalProfile
- GET|PUT /api/store-payments/oauth-config/    → StoreOAuthConfig (Google BYO)
- GET|PUT|DELETE /api/store-payments/storage-config/ → StoreStorageConfig (R2 BYO)
- GET  /api/store-payments/storage-config/guide/    → guía estática es-AR

Regla de secretos: el client_secret de Google y las llaves R2 son
write-only — se cifran con el vault (enc:v1:, purpose por campo y por
tienda) y JAMÁS vuelven en una respuesta (solo flags has_*).

OIDC/IDOR: todo cuelga de `request.user.profile.store` — no hay id de
tienda en la ruta y los serializers no aceptan `store`/`store_id`, así
que es imposible apuntar a la config de otro vendedor por body/query.
"""
import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from StoreApp.domains.storepayments.serializers import (
    StoreFiscalProfileSerializer,
    StoreOAuthConfigSerializer,
    StoreStorageConfigSerializer,
)
from StoreApp.domains.stores.models import (
    StoreFiscalProfile,
    StoreOAuthConfig,
    StoreStorageConfig,
)
from StoreApp.domains.stores.services.storage import invalidate_store_storage

from .mp import owner_store

logger  =   logging.getLogger(__name__)


#=========================================
# HELPERS
#=========================================
def _get_or_default(model, store):
    """
    Fila de config de la tienda o instancia NO persistida con los
    defaults del modelo — el GET informa sin escribir (mismo patrón que
    StorePaymentConfigView).
    """
    cfg =   model.objects.filter(store = store).first()
    return cfg if cfg is not None else model(store = store)


#=========================================
# FISCAL PROFILE (GET|PUT)
#=========================================
class FiscalProfileView(APIView):
    """
    Datos fiscales del vendedor (StoreFiscalProfile). PUT valida los
    campos que `orders_enabled` exige para vender — ver el serializer.
    """
    permission_classes    =   [IsAuthenticated]
    def get(self, request):
        store   =   owner_store(request)
        profile =   _get_or_default(StoreFiscalProfile, store)
        return Response(StoreFiscalProfileSerializer(profile).data, status = status.HTTP_200_OK)
    def put(self, request):
        store   =   owner_store(request)
        #Instancia transitoria si no hay fila: un PUT inválido NO debe
        #persistir una config vacía (mismo criterio que el GET).
        profile =   _get_or_default(StoreFiscalProfile, store)
        serializer  =   StoreFiscalProfileSerializer(profile, data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(serializer.data, status = status.HTTP_200_OK)


#=========================================
# OAUTH CONFIG — login social Google (GET|PUT)
#=========================================
class OAuthConfigView(APIView):
    """
    Login con Google del checkout de ESTA web. `google_client_secret`
    es write-only (vault); `google_client_id` sí se devuelve — es
    público por diseño. PUT merge: campos ausentes conservan valor.
    """
    permission_classes    =   [IsAuthenticated]
    def get(self, request):
        store   =   owner_store(request)
        cfg     =   _get_or_default(StoreOAuthConfig, store)
        return Response(StoreOAuthConfigSerializer(cfg).data, status = status.HTTP_200_OK)
    def put(self, request):
        store   =   owner_store(request)
        cfg     =   _get_or_default(StoreOAuthConfig, store)
        serializer  =   StoreOAuthConfigSerializer(cfg, data = request.data, partial = True)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(serializer.data, status = status.HTTP_200_OK)


#=========================================
# STORAGE CONFIG — bucket R2 propio (GET|PUT|DELETE) + guía
#=========================================
class StorageConfigView(APIView):
    """
    BYO storage del dueño. PUT merge (credenciales write-only cifradas
    con vault); DELETE = deshabilita Y limpia los secretos cifrados —
    la config no secreta (endpoint/bucket/URL pública) se conserva por
    si el dueño quiere reactivar sin reteclear todo. Jamás migra
    objetos: ver la guía.
    """
    permission_classes    =   [IsAuthenticated]
    def get(self, request):
        store   =   owner_store(request)
        cfg     =   _get_or_default(StoreStorageConfig, store)
        return Response(StoreStorageConfigSerializer(cfg).data, status = status.HTTP_200_OK)
    def put(self, request):
        store   =   owner_store(request)
        cfg     =   _get_or_default(StoreStorageConfig, store)
        serializer  =   StoreStorageConfigSerializer(cfg, data = request.data, partial = True)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        #El cache BYO de storage.py es corto (300s) pero la escritura
        #lo invalida ya — el próximo upload/URL usa la config nueva.
        invalidate_store_storage(store.id)
        return Response(serializer.data, status = status.HTTP_200_OK)
    def delete(self, request):
        store   =   owner_store(request)
        cfg     =   StoreStorageConfig.objects.filter(store = store).first()
        if cfg is not None:
            #Disable + clear secrets: revocación local inmediata. Las
            #keys cifradas se borran (set_credentials('','')) — si el
            #dueño reactiva tiene que volver a pegar sus llaves.
            cfg.enabled     =   False
            cfg.set_credentials('', '')
            cfg.save(update_fields = ['enabled', 'access_key_enc', 'secret_key_enc', 'updated_at'])
            invalidate_store_storage(store.id)
            logger.info('Storage BYO deshabilitado store=%s', store.slug)
        return Response(StoreStorageConfigSerializer(_get_or_default(StoreStorageConfig, store)).data, status = status.HTTP_200_OK)


STORAGE_GUIDE    =   {
    'title'     :   'Cómo conectar tu propio bucket de Cloudflare R2',
    'intro'     :   'R2 tiene capa gratuita generosa y DAVENT no toca tus archivos: con tu propio bucket las imágenes se sirven desde tu cuenta. Todo lo que subas se sigue midiendo en el cupo de tu plan.',
    'steps'     :   [
        '1. Creá una cuenta gratis en cloudflare.com y entrá a "R2 Object Storage" → "Create bucket". Nombre en minúsculas, números y guiones (ej. fotos-mi-tienda).',
        '2. En "Manage R2 API Tokens" → "Create API token" con permiso "Object Read & Write" limitado a ESE bucket. Copiá el Access Key ID y el Secret Access Key: el secret solo se muestra una vez.',
        '3. El endpoint S3 es https://<tu-account-id>.r2.cloudflarestorage.com (lo ves en el panel de R2, sección "Use compatible S3 API").',
        '4. Para que las imágenes se vean en tu web: en el bucket → Settings → "Public Development URL" te da una https://pub-<hash>.r2.dev (pegala en "URL pública base"), o configurá "Custom Domains" con un dominio tuyo (ej. img.tutienda.com).',
        '5. Regiones: dejá "auto". Pegá endpoint, bucket, Access Key, Secret Key y la URL pública, y activá "Usar storage propio".',
    ],
    'warnings'  :   [
        'Las llaves se guardan cifradas y nunca se vuelven a mostrar — guardá una copia del secret en tu gestor de contraseñas.',
        'Sin "URL pública base" las imágenes se sirven con links temporales firmados que VENCEN (unos 7 días): usá la URL r2.dev o un dominio propio para que no se rompan.',
        'DAVENT no migra objetos entre buckets: si desactivás el storage propio, las imágenes ya subidas a tu bucket dejan de servirse (y viceversa al activarlo con imágenes viejas en DAVENT). No lo apagues si ya tenés fotos cargadas.',
        'Si la subida a tu bucket falla (credenciales revocadas, bucket borrado), DAVENT la reintenta automáticamente en su propio storage — el upload nunca se rompe, pero esa imagen puntual puede quedar sirviéndose desde DAVENT.',
    ],
}


class StorageGuideView(APIView):
    """
    Guía estática es-AR para conectar el R2 propio (requisito del
    producto: texto instructivo, no integración automática). Pública
    para el dueño autenticado — no expone nada sensible.
    """
    permission_classes    =   [IsAuthenticated]
    def get(self, request):
        owner_store(request)      #mismo gate: solo dueños con tienda
        return Response(STORAGE_GUIDE, status = status.HTTP_200_OK)
