from django.contrib.auth.hashers import check_password as _check_password
from django.contrib.auth.hashers import make_password
from django.db import models

from AdminApp.domains.users.models.fields import EncryptedCharField, digest_for

"""

Compradores de las webs de tiendas (e-commerce DAVENT).

`Customer` es una cuenta GLOBAL del consumidor final: la misma cuenta
sirve para comprar en cualquier tienda de la plataforma — NO es un
`auth.User` ni un `UserProfile` (eso es la cuenta SaaS del DUEÑO). Vive
ajena a la suscripción DAVENT y no tiene plan, tienda ni permisos de
panel: solo identidad de compra + membresías por tienda.

PII (teléfono y documento) se guarda CIFRADA en reposo con
`EncryptedCharField` (AES-256-GCM del vault, un `purpose` por campo) y la
búsqueda/unicidad vive en las huellas HMAC `<campo>_hash` — mismo patrón
que `UserProfile`. El email NO se cifra: es la credencial de login y ya
es único normalizado a minúsculas.

Decisión de nombres: `first_name`/`last_name` van en claro — son datos
de contacto que el vendedor necesita para facturar/envíar el pedido y el
propio comprador los edita en su perfil; el riesgo de PII sensible lo
cubren teléfono y documento (identificadores), no el nombre.

Avatar: NO hay foto de perfil (requisito explícito) — la API expone
`avatar` como la inicial del nombre o del email.

"""
#=========================================
# CUSTOMER (cuenta global del comprador)
#=========================================
class Customer(models.Model):
    DOCUMENT_TYPE           =   [
        ('DNI' , 'Documento de identidad'),
        ('CUIT', 'CUIT/CUIL')
    ]
    #IDENTIDAD — email único case-insensitive (save/serializer normalizan a
    #minúsculas; la unicidad de Postgres es case-sensitive, por eso la
    #normalización es obligatoria en los dos caminos).
    email                   =   models.EmailField(unique = True, verbose_name = 'Correo electrónico')
    #Password hasheado con los hashers de Django (pbkdf2 por defecto) —
    #nunca el texto plano. `set_unusable_password()` para cuentas Google.
    password                =   models.CharField(max_length = 128, verbose_name = 'Contraseña (hash)')
    first_name              =   models.CharField(max_length = 150, blank = True, verbose_name = 'Nombre')
    last_name               =   models.CharField(max_length = 150, blank = True, verbose_name = 'Apellido')
    #PII cifrada — ver docstring del módulo. Las huellas HMAC se usan para
    #búsqueda por igualdad; NO son unique: la unicidad global convertía el
    #constraint en oráculo de existencia de PII ajeno (500 vs 200 en el
    #PATCH de perfil — ver security audit run-1).
    phone                   =   EncryptedCharField(aad = 'Customer.phone', max_length = 16, blank = True, verbose_name = 'Teléfono')
    phone_hash              =   models.CharField(max_length = 64, null = True, blank = True, editable = False, verbose_name = 'Huella del teléfono')
    document_type           =   models.CharField(max_length = 4, choices = DOCUMENT_TYPE, default = 'DNI', blank = True, verbose_name = 'Tipo de documento')
    #Opcional: solo lo pide el checkout del vendedor si lo necesita para
    #facturar — el alta no lo exige.
    document                =   EncryptedCharField(aad = 'Customer.document', max_length = 11, blank = True, verbose_name = 'Documento')
    document_hash           =   models.CharField(max_length = 64, null = True, blank = True, editable = False, verbose_name = 'Huella del documento')
    #EMAIL VERIFICATION — token firmado (django.core.signing) enviado por
    #correo; ver services/customers.py.
    email_verified          =   models.BooleanField(default = False, verbose_name = 'Correo verificado')
    email_verified_at       =   models.DateTimeField(null = True, blank = True, verbose_name = 'Fecha de verificación del correo')
    is_active               =   models.BooleanField(default = True, verbose_name = 'Cuenta activa')
    last_login_at           =   models.DateTimeField(null = True, blank = True, verbose_name = 'Último acceso')
    #Revocación de sesiones: al confirmar un reset de contraseña se sella
    #este timestamp y todo access/refresh con `iat` anterior se rechaza
    # CustomerRefreshToken/CustomerAccessToken no son blacklistables por
    #jti de a uno ( OutstandingToken.user es auth.User), así que el corte
    #global post-reset viaja acá. None = sin revocación.
    tokens_valid_after      =   models.DateTimeField(null = True, blank = True, verbose_name = 'Tokens emitidos antes de este momento quedan revocados')
    created_at              =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label           =   'customers'
        verbose_name        =   'Cliente'
        verbose_name_plural =   'Clientes'
        indexes             =   [
            #Búsquedas del panel del dueño por documento (type+hash) — el
            #compuesto indexa la igualdad (las huellas ya no son unique:
            #dos cuentas pueden compartir teléfono/documento).
            models.Index(fields = ['document_type', 'document_hash'], name = 'idx_customer_doctype_doc'),
        ]
    def __str__(self):
        return self.email
    #=====================================
    # PASSWORD (hashers de Django — nunca texto plano)
    #=====================================
    def set_password(self, raw_password):
        self.password   =   make_password(raw_password)
    def set_unusable_password(self):
        self.password   =   make_password(None)
    def check_password(self, raw_password):
        return _check_password(raw_password or '', self.password or '')
    #=====================================
    # SAVE — normalización + huellas PII
    #=====================================
    def save(self, *args, **kwargs):
        #Email siempre en minúsculas: la unique de Postgres distingue
        #mayúsculas y sin esto 'A@x.com'/'a@x.com' serían dos cuentas.
        if self.email:
            self.email  =   self.email.strip().lower()
        #Las huellas acompañan al campo cifrado: se recomputan siempre
        #y viajan en el UPDATE cuando el campo origen está en update_fields.
        self.document_hash  =   digest_for('customer.document', self.document) if self.document else None
        self.phone_hash     =   digest_for('customer.phone', self.phone) if self.phone else None
        update_fields       =   kwargs.get('update_fields')
        if update_fields is not None:
            if 'document' in update_fields and 'document_hash' not in update_fields:
                kwargs['update_fields'] = [*update_fields, 'document_hash']
                update_fields = kwargs['update_fields']
            if 'phone' in update_fields and 'phone_hash' not in update_fields:
                kwargs['update_fields'] = [*update_fields, 'phone_hash']
        super().save(*args, **kwargs)
    #=====================================
    # USER-LIKE (request.user = Customer en los endpoints de comprador)
    #=====================================
    @property
    def is_authenticated(self):
        return True
    @property
    def is_anonymous(self):
        return False
    #=====================================
    # AVATAR — solo la inicial (sin foto de perfil, requisito explícito)
    #=====================================
    @property
    def avatar(self):
        name    =   (self.first_name or self.email or '').strip()
        return name[0].upper() if name else '?'
#=========================================
# CUSTOMER ADDRESS (direcciones de envío del comprador)
#=========================================
class CustomerAddress(models.Model):
    """
    Dirección de envío del comprador. `province`/`city`/`country` son
    texto libre a propósito: el comprador puede comprar en cualquier
    país y la lista locations de DAVENT es del territorio argentino del
    dueño — acoplarla rompería compras internacionales.
    """
    customer                =   models.ForeignKey(Customer, on_delete = models.CASCADE, related_name = 'addresses')
    label                   =   models.CharField(max_length = 40, default = 'Casa', verbose_name = 'Etiqueta')
    line1                   =   models.CharField(max_length = 160, verbose_name = 'Domicilio')
    line2                   =   models.CharField(max_length = 160, blank = True, verbose_name = 'Departamento / piso / referencia')
    city                    =   models.CharField(max_length = 120, verbose_name = 'Ciudad')
    province                =   models.CharField(max_length = 120, verbose_name = 'Provincia / estado')
    postal_code             =   models.CharField(max_length = 20, blank = True, verbose_name = 'Código postal')
    country                 =   models.CharField(max_length = 2, default = 'AR', verbose_name = 'País (ISO)')
    is_default              =   models.BooleanField(default = False, verbose_name = 'Dirección principal')
    created_at              =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label           =   'customers'
        verbose_name        =   'Dirección de cliente'
        verbose_name_plural =   'Direcciones de clientes'
        ordering            =   ['-is_default', 'created_at']
    def __str__(self):
        return f'{self.label} — {self.customer_id}'
#=========================================
# CUSTOMER NOTIFICATION (avisos in-app del comprador en la web de tienda)
#=========================================
class CustomerNotification(models.Model):
    """
    Aviso in-app para un comprador registrado en la web de UNA tienda
    (campana del header + sección Notificaciones de /cuenta). No es un
    mail ni un mensaje de soporte: el click solo marca leído y navega a
    `target` (vista de /cuenta o el catálogo; '' = solo se lee).

    Kinds: 'order' (estado de seguimiento del pedido), 'offer' (ofertas
    y ofertas especiales del dueño), 'support' (respuesta del comercio
    en un hilo), 'membership' (ciclo de la suscripción a la tienda).
    Los avisos recurrentes usan `dedupe_key` para ser UNO solo que se
    actualiza y vuelve a no-leído (pedido, hilo, suscripción); el
    broadcast de ofertas deduplica por (descuento, comprador).
    """
    KIND_ORDER          =   'order'
    KIND_OFFER          =   'offer'
    KIND_SUPPORT        =   'support'
    KIND_MEMBERSHIP     =   'membership'
    KIND_CHOICES        =   [
        (KIND_ORDER,      'Estado del pedido'),
        (KIND_OFFER,      'Oferta'),
        (KIND_SUPPORT,    'Mensaje del comercio'),
        (KIND_MEMBERSHIP, 'Suscripción'),
    ]
    customer                =   models.ForeignKey(Customer, on_delete = models.CASCADE, related_name = 'notifications')
    store                   =   models.ForeignKey('stores.Store', on_delete = models.CASCADE, related_name = 'customer_notifications')
    kind                    =   models.CharField(max_length = 20, choices = KIND_CHOICES, db_index = True, verbose_name = 'Tipo')
    dedupe_key              =   models.CharField(max_length = 80, blank = True, default = '', verbose_name = 'Clave de deduplicación')
    title                   =   models.CharField(max_length = 200, verbose_name = 'Título')
    body                    =   models.CharField(max_length = 500, blank = True, default = '', verbose_name = 'Detalle')
    #Destino del click: vista de /cuenta ('pedidos', 'suscripciones',
    #'soporte') o 'catalogo'; '' = el click solo marca leído.
    target                  =   models.CharField(max_length = 40, blank = True, default = '', verbose_name = 'Destino')
    #null = sin leer; al actualizar un aviso deduplicado vuelve a null.
    read_at                 =   models.DateTimeField(null = True, blank = True, verbose_name = 'Leído')
    created_at              =   models.DateTimeField(auto_now_add = True)
    updated_at              =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label           =   'customers'
        verbose_name        =   'Notificación de cliente'
        verbose_name_plural =   'Notificaciones de clientes'
        ordering            =   ['-created_at', '-id']
        constraints         =   [
            models.UniqueConstraint(fields = ['customer', 'kind', 'dedupe_key'], name = 'uniq_cnotif_cust_kind_key'),
        ]
        indexes             =   [
            #La campana y /cuenta leen los avisos de ESTA tienda del
            #comprador (no leídos primero vía read_at IS NULL).
            models.Index(fields = ['customer', 'store', 'read_at'], name = 'idx_cnotif_cust_store_read'),
        ]
    def __str__(self):
        return f'{self.get_kind_display()} → {self.customer_id}@{self.store_id}'
#=========================================
# STORE MEMBERSHIP (customer × store — contrato con track D)
#=========================================
class StoreMembership(models.Model):
    """
    Vínculo del comprador con UNA tienda. Campos EXACTOS del contrato
    con el track de membresías (D): `status` ('active'/'suspended'),
    `tags` (JSON) y `joined_at`. Un comprador puede ser cliente de N
    tiendas; el unique (customer, store) evita filas duplicadas.
    """
    STATUS_ACTIVE           =   'active'
    STATUS_SUSPENDED        =   'suspended'
    STATUS_CHOICES          =   [
        (STATUS_ACTIVE,    'Activo'),
        (STATUS_SUSPENDED, 'Suspendido'),
    ]
    customer                =   models.ForeignKey(Customer, on_delete = models.CASCADE, related_name = 'memberships')
    store                   =   models.ForeignKey('stores.Store', on_delete = models.CASCADE, related_name = 'customer_memberships')
    status                  =   models.CharField(max_length = 10, choices = STATUS_CHOICES, default = STATUS_ACTIVE, verbose_name = 'Estado')
    tags                    =   models.JSONField(default = list, blank = True, verbose_name = 'Etiquetas')
    joined_at               =   models.DateTimeField(auto_now_add = True, verbose_name = 'Alta en la tienda')
    class Meta:
        app_label           =   'customers'
        verbose_name        =   'Membresía de tienda'
        verbose_name_plural =   'Membresías de tiendas'
        constraints         =   [
            models.UniqueConstraint(fields = ['customer', 'store'], name = 'uniq_customer_store_membership'),
        ]
        indexes             =   [
            #Panel del dueño: "mis clientes de ESTA tienda" filtra por
            #store + status — el unique (customer, store) indexa la otra
            #dirección.
            models.Index(fields = ['store', 'status'], name = 'idx_membership_store_status'),
        ]
    def __str__(self):
        return f'{self.customer_id}@{self.store_id}:{self.status}'
