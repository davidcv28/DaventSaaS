import re

from rest_framework import serializers

from StoreApp.domains.legalpages.models import ReturnRequest, StoreLegalPage


def _clean_text(value):
    #Postgres no admite \x00 en columnas de texto: se eliminan siempre.
    return (value or '').replace('\x00', '')

"""
Serializers del dominio legalpages.

- LegalPageWriteSerializer: PUT del dueño (title opcional, body requerido
  ≤20000, is_published). El body es texto plano — se sirve literal.
- ReturnRequestCreateSerializer: POST público del arrepentimiento —
  honeypot + challenge de captcha (mismo mecanismo del contacto).
- ReturnRequestSerializer / ReturnRequestStatusSerializer: bandeja del
  dueño y cambio de estado.
"""
#=========================================
# PÁGINAS LEGALES (escritura del dueño)
#=========================================
class LegalPageWriteSerializer(serializers.Serializer):
    title           =   serializers.CharField(max_length = 120, required = False, allow_blank = True)
    body            =   serializers.CharField(max_length = StoreLegalPage.BODY_MAX_LENGTH)
    is_published    =   serializers.BooleanField(required = False)
    def validate_title(self, value):
        #Título saneado: solo trim + largo (el modelo ya capa a 120).
        return _clean_text(value).strip()
    def validate_body(self, value):
        body    =   _clean_text(value).strip()
        if not body:
            raise serializers.ValidationError('El texto de la página no puede estar vacío.')
        return body
#=========================================
# SOLICITUDES DE DEVOLUCIÓN (público)
#=========================================
#order_ref = tracking_token del pedido (secrets.token_urlsafe del dominio
#orders): urlsafe base64 de ~43 chars. Se valida formato, nunca existencia.
ORDER_REF_RE     =   re.compile(r'^[A-Za-z0-9_-]{8,80}$')

class ReturnRequestCreateSerializer(serializers.Serializer):
    order_ref       =   serializers.CharField(max_length = ReturnRequest.ORDER_REF_MAX, required = False, allow_blank = True)
    name            =   serializers.CharField(max_length = 120)
    email           =   serializers.EmailField(max_length = 254)
    #Decreto 274/2019: documento/teléfono/domicilio son obligatorios en el
    #botón de arrepentimiento (blank=False → required por defecto).
    document        =   serializers.CharField(max_length = 20)
    phone           =   serializers.CharField(max_length = 40)
    address         =   serializers.CharField(max_length = 255)
    reason          =   serializers.ChoiceField(choices = ReturnRequest.REASON_CHOICES)
    details         =   serializers.CharField(max_length = 1000, required = False, allow_blank = True)
    #Honeypot + captcha firmado (mismo challenge del formulario de contacto).
    website         =   serializers.CharField(required = False, allow_blank = True, write_only = True)
    challenge_id    =   serializers.CharField(write_only = True)
    captcha_answer  =   serializers.CharField(max_length = 8, write_only = True)
    def validate_order_ref(self, value):
        ref =   _clean_text(value).strip()
        if ref and not ORDER_REF_RE.match(ref):
            raise serializers.ValidationError('La referencia del pedido no tiene un formato válido.')
        return ref
    def validate_name(self, value):
        name    =   _clean_text(value).strip()
        if not name:
            raise serializers.ValidationError('Indicá tu nombre.')
        return name
    def validate_details(self, value):
        return _clean_text(value).strip()
#=========================================
# BANDEJA DEL DUEÑO
#=========================================
class ReturnRequestSerializer(serializers.ModelSerializer):
    reason_display      =   serializers.SerializerMethodField()
    class Meta:
        model       =   ReturnRequest
        fields      =   ['id', 'order_ref', 'customer_email', 'name', 'document', 'phone', 'address', 'reason', 'reason_display', 'details', 'status', 'created_at', 'updated_at']
    def get_reason_display(self, req):
        return req.get_reason_display()

class ReturnRequestStatusSerializer(serializers.Serializer):
    status  =   serializers.ChoiceField(choices = ReturnRequest.STATUS_CHOICES)
