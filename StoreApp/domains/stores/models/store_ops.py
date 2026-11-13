import json

from django.db import models
from django.utils import timezone

from AdminApp.domains.invoices.services.vault import decrypt_secret, encrypt_secret
from StoreApp.domains.stores.models.models import Store

"""
Configuración comercial de la tienda (e-commerce DAVENT): una fila por
Store con los datos fiscales del vendedor, sus métodos de cobro, la
cuenta de Mercado Pago propia, el login social Google y el storage R2
del dueño.

Regla fiscal DAVENT: la plataforma NO cobra ni factura las ventas —
estos modelos solo describen cómo cobra el vendedor (su MP, su
transferencia) y qué datos fiscales exhibe. Los secretos (tokens MP,
client secret de Google, llaves R2) viajan SIEMPRE como blob `enc:v1:`
del vault de invoices (AES-256-GCM, un purpose por campo y por tienda);
los services los descifran únicamente al llamar al proveedor y jamás
salen en una respuesta API.
"""
#=========================================
# STORE FISCAL PROFILE (datos fiscales del vendedor — Fase 0 legal)
#=========================================
class StoreFiscalProfile(models.Model):
    """
    Datos fiscales que la ley argentina exige mostrar en la web del
    comercio y que habilitan el modo ventas (services.commerce.
    orders_enabled). El CUIT se valida con dígito verificador en
    services.commerce.cuit_is_valid — acá solo se enforcea el formato.
    """
    TAX_CONDITION               =   [
        ('CF', 'Consumidor Final'),
        ('MO', 'Monotributista'),
        ('RI', 'Responsable Inscripto'),
        ('EX', 'Exento'),
    ]
    store                       =   models.OneToOneField(Store, on_delete = models.CASCADE, related_name = 'fiscal_profile')
    legal_name                  =   models.CharField(max_length = 160, blank = True, verbose_name = 'Razón social / nombre fiscal')
    tax_condition               =   models.CharField(max_length = 2, choices = TAX_CONDITION, default = 'CF', verbose_name = 'Condición frente a IVA')
    cuit                        =   models.CharField(max_length = 11, blank = True, verbose_name = 'CUIT')
    fiscal_address              =   models.CharField(max_length = 255, blank = True, verbose_name = 'Domicilio fiscal')
    point_of_sale               =   models.CharField(max_length = 8, blank = True, verbose_name = 'Punto de venta')
    updated_at                  =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Perfil fiscal de tienda'
        verbose_name_plural     =   'Perfiles fiscales de tiendas'
    def __str__(self):
        return f'fiscal:{self.store.slug}'
    @property
    def is_complete(self):
        """True si están los datos mínimos para vender (Fase 0 legal)."""
        from StoreApp.domains.stores.services.commerce import cuit_is_valid
        return bool(
            self.legal_name
            and self.cuit
            and self.fiscal_address
            and cuit_is_valid(self.cuit)
        )
#=========================================
# STORE PAYMENT CONFIG (métodos de cobro del checkout)
#=========================================
class StorePaymentConfig(models.Model):
    """
    Métodos de cobro que el dueño ofrece en su checkout. La plata va
    directo al vendedor: DAVENT nunca la toca (prohibido application_fee
    ni split de MP). `mp_enabled` solo decide si la opción Mercado Pago
    se muestra cuando hay StoreMpAccount conectado — no es la conexión
    en sí.
    """
    store                       =   models.OneToOneField(Store, on_delete = models.CASCADE, related_name = 'payment_config')
    accept_transfer             =   models.BooleanField(default = True, verbose_name = 'Transferencia / depósito')
    accept_whatsapp             =   models.BooleanField(default = False, verbose_name = 'Coordinar por WhatsApp')
    accept_cash                 =   models.BooleanField(default = False, verbose_name = 'Efectivo / pago en persona')
    mp_enabled                  =   models.BooleanField(default = True, verbose_name = 'Mostrar Mercado Pago')
    transfer_alias              =   models.CharField(max_length = 120, blank = True, verbose_name = 'Alias / CVU / CBU')
    transfer_holder             =   models.CharField(max_length = 160, blank = True, verbose_name = 'Titular de la cuenta')
    transfer_instructions       =   models.TextField(max_length = 600, blank = True, verbose_name = 'Instrucciones de pago')
    whatsapp_number             =   models.CharField(max_length = 20, blank = True, verbose_name = 'WhatsApp para coordinar el pago')
    require_payment_proof       =   models.BooleanField(default = False, verbose_name = 'Exigir comprobante de pago')
    payment_deadline_hours      =   models.PositiveIntegerField(default = 48, verbose_name = 'Horas para acreditar el pago')
    updated_at                  =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Configuración de cobros'
        verbose_name_plural     =   'Configuraciones de cobros'
    def __str__(self):
        return f'payments:{self.store.slug}'
#=========================================
# STORE MP ACCOUNT (Mercado Pago del vendedor — credenciales propias)
#=========================================
class StoreMpAccount(models.Model):
    """
    Cuenta de Mercado Pago DEL VENDEDOR (Checkout Pro con sus
    credenciales — la plata cae en su cuenta, MP le deposita a su
    banco). Los tokens se guardan cifrados con el vault (enc:v1:, un
    purpose por campo y por tienda): get_access_token() es el único
    camino de lectura y solo lo usan los services de cobro.
    """
    PURPOSE_ACCESS              =   'StoreMpAccount.access_token'
    PURPOSE_REFRESH             =   'StoreMpAccount.refresh_token'
    store                       =   models.OneToOneField(Store, on_delete = models.CASCADE, related_name = 'mp_account')
    mp_user_id                  =   models.CharField(max_length = 64, blank = True, verbose_name = 'ID de usuario MP')
    access_token_enc            =   models.TextField(blank = True, verbose_name = 'Access token (cifrado)')
    refresh_token_enc           =   models.TextField(blank = True, verbose_name = 'Refresh token (cifrado)')
    live_mode                   =   models.BooleanField(default = False, verbose_name = 'Modo productivo')
    scope                       =   models.CharField(max_length = 200, blank = True, verbose_name = 'Scopes otorgados')
    connected_at                =   models.DateTimeField(null = True, blank = True, verbose_name = 'Conectado el')
    updated_at                  =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Cuenta MP de tienda'
        verbose_name_plural     =   'Cuentas MP de tiendas'
    def __str__(self):
        return f'mp:{self.store.slug}'
    @property
    def is_connected(self):
        return bool(self.access_token_enc)
    def _purpose(self, base):
        #El purpose lleva el store_id: un blob cifrado para la tienda A
        #no puede reutilizarse en la cuenta de la tienda B (AAD del GCM).
        return f'{base}:{self.store_id}'
    def set_tokens(self, access_token, refresh_token = '', *, live_mode = False, mp_user_id = '', scope = ''):
        self.access_token_enc  =   encrypt_secret(access_token.encode(), self._purpose(self.PURPOSE_ACCESS))
        self.refresh_token_enc =   encrypt_secret(refresh_token.encode(), self._purpose(self.PURPOSE_REFRESH)) if refresh_token else ''
        self.live_mode          =   live_mode
        self.mp_user_id         =   mp_user_id
        self.scope              =   scope
        self.connected_at       =   timezone.now()
    def get_access_token(self):
        if not self.access_token_enc:
            return ''
        return decrypt_secret(self.access_token_enc, self._purpose(self.PURPOSE_ACCESS)).decode()
    def get_refresh_token(self):
        if not self.refresh_token_enc:
            return ''
        return decrypt_secret(self.refresh_token_enc, self._purpose(self.PURPOSE_REFRESH)).decode()
    def clear_tokens(self):
        self.access_token_enc   =   ''
        self.refresh_token_enc  =   ''
        self.mp_user_id         =   ''
        self.scope              =   ''
        self.connected_at       =   None
#=========================================
# STORE OAUTH CONFIG (login social Google de los compradores)
#=========================================
class StoreOAuthConfig(models.Model):
    """
    Login con Google en el checkout/registro de ESTA web. Si el dueño
    carga su propio client de Google (BYO) se usa ese; si `enabled`
    está activo sin credenciales propias, se usa el client central
    DAVENT. Solo el secret va cifrado — el client_id es público por
    diseño (viaja en el botón de Google).
    """
    PURPOSE_SECRET               =   'StoreOAuthConfig.google_client_secret'
    store                       =   models.OneToOneField(Store, on_delete = models.CASCADE, related_name = 'oauth_config')
    enabled                     =   models.BooleanField(default = False, verbose_name = 'Login con Google activo')
    google_client_id            =   models.CharField(max_length = 200, blank = True, verbose_name = 'Google Client ID propio')
    google_client_secret_enc    =   models.TextField(blank = True, verbose_name = 'Google Client Secret (cifrado)')
    updated_at                  =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Login social de tienda'
        verbose_name_plural     =   'Logins sociales de tiendas'
    def __str__(self):
        return f'oauth:{self.store.slug}'
    @property
    def has_own_client(self):
        return bool(self.google_client_id)
    def set_client_secret(self, secret):
        self.google_client_secret_enc =   encrypt_secret(secret.encode(), f'{self.PURPOSE_SECRET}:{self.store_id}') if secret else ''
    def get_client_secret(self):
        if not self.google_client_secret_enc:
            return ''
        return decrypt_secret(self.google_client_secret_enc, f'{self.PURPOSE_SECRET}:{self.store_id}').decode()
#=========================================
# STORE STORAGE CONFIG (bucket R2 propio del dueño — BYO storage)
#=========================================
class StoreStorageConfig(models.Model):
    """
    Bucket Cloudflare R2 propio del dueño. Si está `enabled` y completo
    (is_configured), las subidas nuevas de ESA tienda van a su bucket;
    si falta algo o la subida falla, cae al R2 de DAVENT — nunca se
    rompe un upload por una config incompleta. Las llaves van cifradas
    con el vault y jamás salen en la API.
    """
    PURPOSE_ACCESS_KEY          =   'StoreStorageConfig.access_key'
    PURPOSE_SECRET_KEY          =   'StoreStorageConfig.secret_key'
    store                       =   models.OneToOneField(Store, on_delete = models.CASCADE, related_name = 'storage_config')
    endpoint                    =   models.CharField(max_length = 300, blank = True, verbose_name = 'Endpoint S3 (https://<cuenta>.r2.cloudflarestorage.com)')
    bucket                      =   models.CharField(max_length = 120, blank = True, verbose_name = 'Bucket')
    region                      =   models.CharField(max_length = 60, default = 'auto', verbose_name = 'Región')
    access_key_enc              =   models.TextField(blank = True, verbose_name = 'Access Key (cifrada)')
    secret_key_enc              =   models.TextField(blank = True, verbose_name = 'Secret Key (cifrada)')
    public_base_url             =   models.CharField(max_length = 500, blank = True, verbose_name = 'URL pública base (pub-*.r2.dev o dominio propio)')
    enabled                     =   models.BooleanField(default = False, verbose_name = 'Usar storage propio')
    updated_at                  =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Storage propio de tienda'
        verbose_name_plural     =   'Storages propios de tiendas'
    def __str__(self):
        return f'storage:{self.store.slug}'
    @property
    def is_configured(self):
        return bool(
            self.endpoint
            and self.bucket
            and self.access_key_enc
            and self.secret_key_enc
            and self.public_base_url
        )
    def _purpose(self, base):
        return f'{base}:{self.store_id}'
    def set_credentials(self, access_key, secret_key):
        self.access_key_enc =   encrypt_secret(access_key.encode(), self._purpose(self.PURPOSE_ACCESS_KEY)) if access_key else ''
        self.secret_key_enc =   encrypt_secret(secret_key.encode(), self._purpose(self.PURPOSE_SECRET_KEY)) if secret_key else ''
    def get_access_key(self):
        if not self.access_key_enc:
            return ''
        return decrypt_secret(self.access_key_enc, self._purpose(self.PURPOSE_ACCESS_KEY)).decode()
    def get_secret_key(self):
        if not self.secret_key_enc:
            return ''
        return decrypt_secret(self.secret_key_enc, self._purpose(self.PURPOSE_SECRET_KEY)).decode()
#=========================================
# STORE SHIPPING CONFIG (envío a domicilio del checkout)
#=========================================
class StoreShippingConfig(models.Model):
    """
    Tarifa de envío a domicilio que el dueño fija para su checkout.
    `home_price` NULL = "a coordinar" (el comprador coordina el envío
    con la tienda como en el MVP — shipping_cost queda 0 y el pedido
    NO se marca priced); un valor >= 0 se cobra en create_order y se
    suma al total (0 explícito = envío gratis). El retiro en el local
    siempre es sin cargo.
    """
    store                       =   models.OneToOneField(Store, on_delete = models.CASCADE, related_name = 'shipping_config')
    home_price                  =   models.DecimalField(max_digits = 12, decimal_places = 2, null = True, blank = True, default = None, verbose_name = 'Precio de envío a domicilio')
    #Correo integrado: el dueño carga las credenciales de SU cuenta
    #andreani/oca (el contrato y el costo del envío los paga él) y el
    #panel genera el código de seguimiento al marcar el pedido enviado.
    carrier                     =   models.CharField(max_length = 20, blank = True, default = '', choices = [('', 'Ninguno'), ('andreani', 'Andreani'), ('oca', 'OCA')], verbose_name = 'Correo integrado')
    carrier_creds_enc           =   models.TextField(blank = True, default = '', verbose_name = 'Credenciales del correo (cifradas)')
    updated_at                  =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'stores'
        verbose_name            =   'Configuración de envíos'
        verbose_name_plural     =   'Configuraciones de envíos'
    def __str__(self):
        return f'shipping:{self.store.slug}'
    def set_carrier_credentials(self, creds):
        payload =   json.dumps(creds or {}, separators = (',', ':')).encode()
        self.carrier_creds_enc  =   encrypt_secret(payload, f'StoreShippingConfig.carrier:{self.store_id}')
    def get_carrier_credentials(self):
        if not self.carrier_creds_enc:
            return {}
        try:
            return json.loads(decrypt_secret(self.carrier_creds_enc, f'StoreShippingConfig.carrier:{self.store_id}').decode())
        except Exception:
            return {}
#=========================================
# PUBLIC CACHE BUST (la tarifa de envío viaja en el payload público —
# una edición del dueño se ve al instante, igual que el resto de la
# config de tienda; ver public_cache.py y el bloque de signals de
# models/models.py para los modelos de esa app)
#=========================================
from django.db.models.signals import post_delete, post_save


def _bust_public_shipping(sender, instance, **kwargs):
    from StoreApp.domains.stores.public_cache import bump_public_store
    bump_public_store(instance.store_id)
post_save.connect(_bust_public_shipping, sender = StoreShippingConfig)
post_delete.connect(_bust_public_shipping, sender = StoreShippingConfig)
