"""
Serializers del dominio storepayments.

Ninguno expone secretos: los tokens MP y el webhook secret son write-only
en connect y JAMÁS vuelven en una respuesta (status/config solo devuelven
flags y metadata).
"""
import re

from rest_framework import serializers

from StoreApp.domains.stores.models import StorePaymentConfig


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
