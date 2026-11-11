"""
Serializers del dominio customers.

Reglas transversales aplicadas:
- Whitelist explícita de campos: `status`, `store`, `customer`, `is_active`,
  `email_verified`, `tags`, `password` (hash) JAMÁS son escribibles desde
  el cliente — los serializers de escritura declaran solo lo editable.
- Email se normaliza a minúsculas en validate (la unique de Postgres es
  case-sensitive y el save() del modelo lo repite como segunda capa).
- Password: validadores de Django (AUTH_PASSWORD_VALIDATORS — mínimo 8,
  no común, no numérica, no similar) — el comprador es consumidor final,
  no SaaS; la policy estricta de mayús/minús/especial queda en users.
- `store_slug` se valida como slug; la existencia/publicación de la
  tienda la resuelve el service (400 si no existe — nunca 500).
"""
import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from StoreApp.domains.customers.models import (
    Customer,
    CustomerAddress,
    StoreMembership,
)
from StoreApp.domains.customers.services.customers import (
    customer_reset_token,
    normalize_email,
)
from StoreApp.domains.stores.services.commerce import cuit_is_valid

#Teléfono del comprador: formato internacional laxo (+ opcional, 6-15
#dígitos tras limpiar separadores) — el vendedor lo usa para WhatsApp/
#llamadas, no es un identificador fiscal.
_PHONE_RE    =   re.compile(r'^\+?\d{6,15}$')


def normalize_phone(value):
    """Deja solo dígitos y un '+' inicial — la huella HMAC depende de esto."""
    value   =   (value or '').strip()
    if not value:
        return ''
    has_plus   =   value.startswith('+')
    digits     =   re.sub(r'\D', '', value)
    return ('+' if has_plus else '') + digits


def normalize_document(value):
    """Documento fiscal: solo dígitos (DNI 7-8, CUIT 11)."""
    return re.sub(r'\D', '', (value or '').strip())


#=====================================
# LECTURA DE PERFIL
#=====================================
class CustomerSerializer(serializers.ModelSerializer):
    """Perfil del comprador (lectura). `avatar` = inicial, nunca foto."""
    avatar  =   serializers.SerializerMethodField()
    class Meta:
        model       =   Customer
        fields      =   [
            'id', 'email', 'first_name', 'last_name',
            'phone', 'document_type', 'document',
            'email_verified', 'email_verified_at',
            'is_active', 'last_login_at', 'created_at', 'avatar',
        ]
        read_only_fields =   fields
    def get_avatar(self, obj):
        return obj.avatar


#=====================================
# EDICIÓN DE PERFIL (whitelist — PATCH)
#=====================================
class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    PATCH /api/customer/profile/ (y /api/customer-auth/me/): solo datos
    editables del comprador. Email NO se cambia por acá (requeriría
    re-verificación — flujo aparte); password va por password-reset.
    """
    #max_length holgado: validate_phone normaliza a dígitos+'+' antes de
    #persistir — el input crudo puede traer espacios/guiones/paréntesis.
    phone       =   serializers.CharField(required = False, allow_blank = True, max_length = 32)
    document    =   serializers.CharField(required = False, allow_blank = True, max_length = 11)
    class Meta:
        model       =   Customer
        fields      =   ['first_name', 'last_name', 'phone', 'document_type', 'document']
    def validate_phone(self, value):
        phone   =   normalize_phone(value)
        if phone and not _PHONE_RE.match(phone):
            raise serializers.ValidationError('Ingresá un teléfono válido (ej. +5493871551234).')
        return phone
    def validate_document(self, value):
        document    =   normalize_document(value)
        if not document:
            return ''
        doc_type    =   self.initial_data.get('document_type') or getattr(self.instance, 'document_type', 'DNI')
        if doc_type == 'CUIT':
            if not cuit_is_valid(document):
                raise serializers.ValidationError('El CUIT no es válido (dígito verificador).')
        elif not 7 <= len(document) <= 8:
            raise serializers.ValidationError('El DNI debe tener entre 7 y 8 dígitos.')
        return document


#=====================================
# AUTH — REGISTER / LOGIN
#=====================================
class CustomerRegisterSerializer(serializers.Serializer):
    email           =   serializers.EmailField(max_length = 254)
    password        =   serializers.CharField(write_only = True, min_length = 8, max_length = 128, trim_whitespace = False)
    first_name      =   serializers.CharField(required = False, allow_blank = True, max_length = 150)
    last_name       =   serializers.CharField(required = False, allow_blank = True, max_length = 150)
    store_slug      =   serializers.SlugField(required = False, allow_blank = True, max_length = 60)
    def validate_email(self, value):
        email   =   normalize_email(value)
        if Customer.objects.filter(email = email).exists():
            raise serializers.ValidationError('Ya existe una cuenta con ese correo.')
        return email
    def validate_password(self, value):
        #Policy de Django (AUTH_PASSWORD_VALIDATORS): mínimo 8, no común,
        #no puramente numérica. validate_password sin `user` saltea la
        #similitud (el comprador no tiene username que comparar).
        try:
            validate_password(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)
        return value
    def validate_store_slug(self, value):
        #Formato válido; existencia/publicación la chequea el service —
        #acá no se consulta DB para no duplicar la resolución.
        return (value or '').strip().lower()


class CustomerLoginSerializer(serializers.Serializer):
    email           =   serializers.EmailField()
    password        =   serializers.CharField(write_only = True, trim_whitespace = False)
    store_slug      =   serializers.SlugField(required = False, allow_blank = True, max_length = 60)
    def validate_store_slug(self, value):
        return (value or '').strip().lower()


#=====================================
# VERIFY EMAIL / PASSWORD RESET
#=====================================
class CustomerVerifyEmailSerializer(serializers.Serializer):
    token   =   serializers.CharField(max_length = 1024)


class CustomerPasswordResetRequestSerializer(serializers.Serializer):
    email           =   serializers.EmailField()
    #Contexto de tienda opcional: el link del mail cae en la web de ESA
    #tienda (/{slug}/cuenta/restablecer). Sin él se usa la membresía más
    #reciente del comprador o la página /cuenta de la plataforma.
    store_slug      =   serializers.SlugField(required = False, allow_blank = True, max_length = 60)
    def validate_store_slug(self, value):
        return (value or '').strip().lower()


class CustomerPasswordResetConfirmSerializer(serializers.Serializer):
    """Contrato {uid, token, new_password, confirm_password} — igual que users."""
    uid                 =   serializers.CharField()
    token               =   serializers.CharField()
    new_password        =   serializers.CharField(write_only = True, trim_whitespace = False)
    confirm_password    =   serializers.CharField(write_only = True, trim_whitespace = False)
    def validate(self, attrs):
        errors  =   {}
        try:
            uid         =   force_str(urlsafe_base64_decode(attrs['uid']))
            customer    =   Customer.objects.get(pk = uid)
        except (TypeError, ValueError, OverflowError, Customer.DoesNotExist):
            customer    =   None
        if customer is None or not customer_reset_token.check_token(customer, attrs['token']):
            errors['token'] =   'El enlace es inválido o ya venció. Pedí uno nuevo.'
        if attrs['new_password'] != attrs['confirm_password']:
            errors['confirm_password'] =   'Las contraseñas no coinciden'
        if customer is not None:
            try:
                validate_password(attrs['new_password'])
            except DjangoValidationError as exc:
                errors['new_password']  =   exc.messages
        if errors:
            raise serializers.ValidationError(errors)
        attrs['customer']   =   customer
        attrs.pop('confirm_password')
        attrs.pop('token')
        return attrs


#=====================================
# GOOGLE LOGIN
#=====================================
class GoogleLoginSerializer(serializers.Serializer):
    credential    =   serializers.CharField(max_length = 8192)
    store_slug    =   serializers.SlugField(max_length = 60)
    def validate_store_slug(self, value):
        return (value or '').strip().lower()


#=====================================
# ADDRESSES
#=====================================
class CustomerAddressSerializer(serializers.ModelSerializer):
    """
    Dirección de envío del comprador. `customer` jamás es campo del
    payload (IDOR/mass-assignment): lo fija la vista desde request.customer.
    `is_default` se valida como booleano; la unicidad del default la
    garantiza save_address_defaults en el service.
    """
    class Meta:
        model       =   CustomerAddress
        fields      =   [
            'id', 'label', 'line1', 'line2', 'city', 'province',
            'postal_code', 'country', 'is_default', 'created_at',
        ]
        read_only_fields =   ['id', 'created_at']
    def validate_country(self, value):
        value   =   (value or 'AR').strip().upper()
        if not re.fullmatch(r'[A-Z]{2}', value):
            raise serializers.ValidationError('Usá el código ISO de 2 letras del país (ej. AR).')
        return value


#=====================================
# MEMBERSHIPS (lectura — contrato track D)
#=====================================
class CustomerMembershipSerializer(serializers.ModelSerializer):
    """Membresía del comprador en una tienda (solo lectura para el front)."""
    store_slug      =   serializers.CharField(source = 'store.slug', read_only = True)
    store_name      =   serializers.SerializerMethodField()
    class Meta:
        model       =   StoreMembership
        fields      =   ['id', 'store_slug', 'store_name', 'status', 'tags', 'joined_at']
        read_only_fields =   fields
    def get_store_name(self, obj):
        profile =   getattr(getattr(obj.store, 'user', None), 'business_name', '') or ''
        return profile or obj.store.slug
