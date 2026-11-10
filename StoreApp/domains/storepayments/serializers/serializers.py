"""
Serializers del dominio storepayments.

Ninguno expone secretos: los tokens MP y el webhook secret son write-only
en connect y JAMÁS vuelven en una respuesta (status/config solo devuelven
flags y metadata).
"""
import re

from django.conf import settings
from rest_framework import serializers

from AdminApp.domains.invoices.services.vault import encrypt_secret
from StoreApp.domains.stores.models import (
    StoreFiscalProfile,
    StoreOAuthConfig,
    StorePaymentConfig,
    StoreStorageConfig,
)
from StoreApp.domains.stores.services.commerce import cuit_is_valid


#=========================================
# MP CONNECT (credenciales pegadas por el dueño — MVP documentado)
#=========================================
class MpConnectSerializer(serializers.Serializer):
    """
    Alta de la cuenta MP del vendedor. `access_token` se valida contra
    GET /users/me ANTES de guardarse (encrypt en vault vía set_tokens).
    `webhook_secret` es opcional: el secret con el que MP firma las
    notificaciones de SU aplicación — sin él el webhook rechaza todo.
    """
    access_token         =   serializers.CharField(write_only = True, trim_whitespace = True)
    refresh_token        =   serializers.CharField(write_only = True, required = False, allow_blank = True, trim_whitespace = True)
    live_mode            =   serializers.BooleanField(required = False)
    webhook_secret       =   serializers.CharField(write_only = True, required = False, allow_blank = True, trim_whitespace = True, max_length = 200)
    def validate_access_token(self, value):
        #Acepta 'Bearer <token>' pegado completo: se normaliza al token.
        value   =   value.strip()
        if value.lower().startswith('bearer '):
            value   =   value[7:].strip()
        if not value:
            raise serializers.ValidationError('El access token no puede estar vacío')
        return value

#=========================================
# STORE PAYMENT CONFIG (métodos manuales del checkout)
#=========================================
_WHATSAPP_RE     =   re.compile(r'^\+?\d{8,15}$')


class StorePaymentConfigSerializer(serializers.ModelSerializer):
    whatsapp_number =   serializers.CharField(required = False, allow_blank = True, max_length = 20)
    class Meta:
        model       =   StorePaymentConfig
        fields      =   [
            'accept_transfer',
            'accept_whatsapp',
            'accept_cash',
            'mp_enabled',
            'transfer_alias',
            'transfer_holder',
            'transfer_instructions',
            'whatsapp_number',
            'require_payment_proof',
            'payment_deadline_hours',
        ]
    def validate_whatsapp_number(self, value):
        #Solo dígitos con '+' opcional: se limpian espacios/guiones/
        #paréntesis antes de validar (el vendedor copia el número como
        #viene de WhatsApp).
        cleaned =   re.sub(r'[\s\-()]', '', value or '')
        if cleaned == '':
            return ''
        if not _WHATSAPP_RE.match(cleaned):
            raise serializers.ValidationError('El WhatsApp solo admite dígitos (con + opcional), 8 a 15 números')
        return cleaned
    def validate_payment_deadline_hours(self, value):
        if value is not None and not (1 <= value <= 720):
            raise serializers.ValidationError('El plazo de pago debe ser entre 1 y 720 horas')
        return value
    def validate(self, attrs):
        #COHERENCIA DE MÉTODOS: no se puede apagar TODO — ni manuales ni
        #MP (con MP conectado y habilitado). Si accept_whatsapp está
        #activo exige whatsapp_number para que el comprador pueda pagar.
        store       =   self.context.get('store')
        instance    =   self.instance
        def _eff(field):
            if field in attrs:
                return attrs[field]
            if instance is not None:
                return getattr(instance, field)
            return StorePaymentConfig._meta.get_field(field).default
        accept_transfer    =   _eff('accept_transfer')
        accept_whatsapp    =   _eff('accept_whatsapp')
        accept_cash        =   _eff('accept_cash')
        mp_enabled         =   _eff('mp_enabled')
        whatsapp_number    =   attrs.get('whatsapp_number', getattr(instance, 'whatsapp_number', '') if instance else '')
        any_manual         =   bool(accept_transfer or accept_whatsapp or accept_cash)
        mp_connected       =   False
        if store is not None and mp_enabled:
            account =   getattr(store, 'mp_account', None)
            mp_connected    =   bool(account and account.is_connected)
        if not any_manual and not mp_connected:
            raise serializers.ValidationError({'detail': 'Activá al menos un método de cobro (transferencia, WhatsApp, efectivo o Mercado Pago conectado)'})
        if accept_whatsapp and not whatsapp_number:
            raise serializers.ValidationError({'whatsapp_number': 'Activaste el cobro por WhatsApp: cargá el número del vendedor'})
        return attrs

#=========================================
# FISCAL PROFILE (datos fiscales del vendedor — gate de orders_enabled)
#=========================================
class StoreFiscalProfileSerializer(serializers.ModelSerializer):
    """
    PUT = formulario completo: exige los campos que `orders_enabled`
    necesita para vender (legal_name + cuit válido + fiscal_address —
    espejo de StoreFiscalProfile.is_complete). tax_condition y
    point_of_sale son opcionales. El CUIT se normaliza a 11 dígitos y
    se valida con el dígito verificador (módulo 11) — un CUIT inválido
    jamás habilitaría ventas, así que se rechaza al guardar.
    """
    is_complete    =   serializers.ReadOnlyField()
    legal_name     =   serializers.CharField(required = True, allow_blank = False, max_length = 160, trim_whitespace = True)
    cuit           =   serializers.CharField(required = True, allow_blank = False, max_length = 32)
    fiscal_address =   serializers.CharField(required = True, allow_blank = False, max_length = 255, trim_whitespace = True)
    point_of_sale  =   serializers.CharField(required = False, allow_blank = True, max_length = 8, trim_whitespace = True)
    class Meta:
        model       =   StoreFiscalProfile
        fields      =   [
            'legal_name',
            'tax_condition',
            'cuit',
            'fiscal_address',
            'point_of_sale',
            'is_complete',
            'updated_at',
        ]
        read_only_fields    =   ['updated_at']
    def validate_cuit(self, value):
        #Acepta 'XX-XXXXXXXX-X', 'XX XXXXXXXX X' o los 11 dígitos →
        #se normaliza a dígitos (el modelo guarda max_length=11).
        digits  =   re.sub(r'\D', '', value or '')
        if not cuit_is_valid(digits):
            raise serializers.ValidationError('El CUIT no es válido (debe tener 11 dígitos y pasar el dígito verificador)')
        return digits

#=========================================
# OAUTH CONFIG (login social Google del checkout — BYO del dueño)
#=========================================
class StoreOAuthConfigSerializer(serializers.ModelSerializer):
    """
    `google_client_secret` es WRITE-ONLY: se cifra con el vault
    (purpose por tienda) y jamás vuelve — GET informa solo
    `has_client_secret`. `google_client_id` NO es secreto (viaja en el
    botón de Google) y sí se devuelve. PUT hace merge: un campo ausente
    conserva su valor; secret '' explícito lo limpia.
    """
    google_client_id        =   serializers.CharField(required = False, allow_blank = True, max_length = 200, trim_whitespace = True)
    google_client_secret    =   serializers.CharField(write_only = True, required = False, allow_blank = True, max_length = 200, trim_whitespace = True)
    has_client_secret       =   serializers.SerializerMethodField()
    has_own_client          =   serializers.ReadOnlyField()
    class Meta:
        model       =   StoreOAuthConfig
        fields      =   [
            'enabled',
            'google_client_id',
            'google_client_secret',
            'has_client_secret',
            'has_own_client',
            'updated_at',
        ]
        read_only_fields    =   ['updated_at']
    def get_has_client_secret(self, obj):
        return bool(obj.google_client_secret_enc)
    def validate_google_client_id(self, value):
        #Client ID de Google Cloud siempre termina en .apps.googleusercontent.com
        #— un typo acá dejaría el botón de login muerto sin error visible.
        value   =   (value or '').strip()
        if value and not value.endswith('.apps.googleusercontent.com'):
            raise serializers.ValidationError('El Client ID de Google debe terminar en .apps.googleusercontent.com')
        return value
    def update(self, instance, validated_data):
        #Secret write-only con merge: presente (incl. '') se aplica —
        #'' limpia; ausente conserva el cifrado actual.
        secret_provided =   'google_client_secret' in validated_data
        secret          =   validated_data.pop('google_client_secret', '')
        instance        =   super().update(instance, validated_data)
        if secret_provided:
            instance.set_client_secret(secret)
            instance.save(update_fields = ['google_client_secret_enc', 'updated_at'])
        return instance

#=========================================
# STORAGE CONFIG (bucket R2 propio del dueño — BYO storage)
#=========================================
_STORAGE_BUCKET_RE   =   re.compile(r'^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$')


def _clean_https_url(value, *, allow_http):
    """Normaliza una URL base (sin barra final). https siempre; http solo en DEBUG (MinIO local)."""
    value   =   (value or '').strip().rstrip('/')
    if not value:
        return ''
    lowered =   value.lower()
    if lowered.startswith('https://'):
        return value
    if allow_http and lowered.startswith('http://') and settings.DEBUG:
        return value
    raise serializers.ValidationError('La URL debe ser válida y empezar con https://')


class StoreStorageConfigSerializer(serializers.ModelSerializer):
    """
    BYO storage del dueño. `access_key`/`secret_key` son WRITE-ONLY y se
    cifran con el vault (purpose por tienda) — jamás vuelven; GET informa
    `has_credentials` + `is_configured`. `is_configured` (modelo) exige
    además public_base_url; el backend real lo usa `stores.services.
    storage._byo_backend` (sin public_base_url las URLs salen firmadas
    y vencen — la guía del panel lo advierte).

    PUT hace merge: credenciales ausentes se conservan, '' limpia ESE
    campo. `enabled` no exige config completa: incompleto = simplemente
    no activa el BYO (cae a DAVENT).
    """
    endpoint            =   serializers.CharField(required = False, allow_blank = True, max_length = 300)
    bucket              =   serializers.CharField(required = False, allow_blank = True, max_length = 120)
    region              =   serializers.CharField(required = False, allow_blank = True, max_length = 60)
    public_base_url     =   serializers.CharField(required = False, allow_blank = True, max_length = 500)
    access_key          =   serializers.CharField(write_only = True, required = False, allow_blank = True, max_length = 200, trim_whitespace = True)
    secret_key          =   serializers.CharField(write_only = True, required = False, allow_blank = True, max_length = 200, trim_whitespace = True)
    is_configured       =   serializers.ReadOnlyField()
    has_credentials     =   serializers.SerializerMethodField()
    url_mode            =   serializers.SerializerMethodField()
    class Meta:
        model       =   StoreStorageConfig
        fields      =   [
            'endpoint',
            'bucket',
            'region',
            'access_key',
            'secret_key',
            'public_base_url',
            'enabled',
            'is_configured',
            'has_credentials',
            'url_mode',
            'updated_at',
        ]
        read_only_fields    =   ['updated_at']
    def get_has_credentials(self, obj):
        return bool(obj.access_key_enc and obj.secret_key_enc)
    def get_url_mode(self, obj):
        if obj.public_base_url:
            return 'public'
        return 'presigned' if self.get_has_credentials(obj) else ''
    def validate_endpoint(self, value):
        return _clean_https_url(value, allow_http = True)
    def validate_public_base_url(self, value):
        return _clean_https_url(value, allow_http = True)
    def validate_bucket(self, value):
        value   =   (value or '').strip()
        if value and not _STORAGE_BUCKET_RE.match(value):
            raise serializers.ValidationError('Nombre de bucket inválido: minúsculas, números y guiones (3-63 caracteres, sin guiones al borde)')
        return value
    def validate_region(self, value):
        #R2 usa 'auto'; un '' no debe quedar persistido como región vacía.
        return (value or '').strip() or 'auto'
    def update(self, instance, validated_data):
        #Credenciales write-only con merge granular: presente (incl. '')
        #se cifra/limpia ESE campo; ausente conserva el blob actual.
        access_provided    =   'access_key' in validated_data
        secret_provided    =   'secret_key' in validated_data
        access_key         =   validated_data.pop('access_key', '')
        secret_key         =   validated_data.pop('secret_key', '')
        instance           =   super().update(instance, validated_data)
        enc_fields         =   []
        if access_provided:
            instance.access_key_enc   =   encrypt_secret(access_key.encode(), instance._purpose(instance.PURPOSE_ACCESS_KEY)) if access_key else ''
            enc_fields.append('access_key_enc')
        if secret_provided:
            instance.secret_key_enc   =   encrypt_secret(secret_key.encode(), instance._purpose(instance.PURPOSE_SECRET_KEY)) if secret_key else ''
            enc_fields.append('secret_key_enc')
        if enc_fields:
            instance.save(update_fields = enc_fields + ['updated_at'])
        return instance
