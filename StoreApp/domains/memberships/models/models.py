import secrets

from django.db import models

from StoreApp.domains.customers.models import StoreMembership
from StoreApp.domains.stores.models import Store

"""

Membresías de tienda (e-commerce DAVENT): planes de suscripción que cada
DUEÑO ofrece a SUS clientes (NO los planes DAVENT del dueño) y las
suscripciones resultantes.

Dos reglas de vigencia:

- `StoreSubscription.status='active'` + `vigente_hasta > now` = plan
  vigente. Los beneficios se evalúan AL LEER (services/benefits.py) — no
  hay cron destructivo: al vencer, el cliente pierde tarjeta digital,
  descuentos/envío gratis y acceso a exclusivos automáticamente.
- `cancelled` = el cliente/dueño dio de baja: como los helpers exigen
  status='active', CANCELAR CORTA LOS BENEFICIOS AL INSTANTE (no espera
  al fin del período pago — decisión documentada; si se quisiera "hasta
  el fin del período" habría que relajar el helper a
  status__in=('active','cancelled')). `expired` es el estado terminal
  cosmético que deja `expire_check()`/`POST .../expire/` para los
  listados del dueño.

El cobro es MANUAL como los pedidos (transferencia/whatsapp/efectivo:
el dueño acredita y activa) — la suscripción nace `pending` y el dueño
la pasa a `active` con POST .../activate/. El auto-billing por MP del
vendedor queda documentado como pendiente (reutilizará la infra de
storepayments/webhooks cuando exista).

`public_token` identifica la tarjeta digital pública
(/api/membership-cards/<slug>/<token>/): NO es credencial de auth —
solo hace la tarjeta innavegable (secrets.token_urlsafe) y minimiza lo
que expone (nombre + inicial, plan, vigencia, beneficios — jamás email,
teléfono ni documento del cliente).

"""
#=========================================
# STORE PLAN (lo crea el dueño de la tienda)
#=========================================
def _public_token():
    #Token de la tarjeta digital: 128 bits urlsafe (~22 chars) — unguessable
    #sin ser secreto de autenticación.
    return secrets.token_urlsafe(16)
class StorePlan(models.Model):
    """
    Plan de suscripción que el dueño vende a SUS clientes. Los beneficios
    son BOOLS explícitos (más claro que un JSON para el enforcement
    server-side de benefits.py): has_digital_card, has_free_shipping,
    has_exclusive_discounts (+ discount_percent) y has_exclusive_access
    (habilita ver/comprar Product.is_exclusive).
    """
    PERIOD_MONTHLY           =   'monthly'
    PERIOD_YEARLY            =   'yearly'
    PERIOD_CUSTOM            =   'custom'
    PERIOD_CHOICES           =   [
        (PERIOD_MONTHLY, 'Mensual'),
        (PERIOD_YEARLY,  'Anual'),
        (PERIOD_CUSTOM,  'Personalizado'),
    ]
    #Días canónicos por período: monthly/yearly los fija el servidor
    #siempre (el serializer pisa period_days — un valor suelto no puede
    #cambiar la duración de un plan mensual). Solo 'custom' usa el
    #period_days que carga el dueño.
    PERIOD_DAYS              =   {
        PERIOD_MONTHLY    :   30,
        PERIOD_YEARLY     :   365,
    }
    store                    =   models.ForeignKey(Store, on_delete = models.CASCADE, related_name = 'subscription_plans', db_index = False)
    name                     =   models.CharField(max_length = 80, verbose_name = 'Nombre')
    price                    =   models.DecimalField(max_digits = 12, decimal_places = 2, default = 0, verbose_name = 'Precio')
    period                   =   models.CharField(max_length = 10, choices = PERIOD_CHOICES, default = PERIOD_MONTHLY, verbose_name = 'Período')
    period_days              =   models.PositiveIntegerField(default = 30, verbose_name = 'Duración (días)')
    has_digital_card         =   models.BooleanField(default = False, verbose_name = 'Tarjeta digital')
    has_free_shipping        =   models.BooleanField(default = False, verbose_name = 'Envío gratis')
    has_exclusive_discounts  =   models.BooleanField(default = False, verbose_name = 'Descuentos exclusivos')
    discount_percent         =   models.DecimalField(max_digits = 5, decimal_places = 2, default = 0, verbose_name = 'Descuento de miembro (%)')
    has_exclusive_access     =   models.BooleanField(default = False, verbose_name = 'Acceso a productos exclusivos')
    is_active                =   models.BooleanField(default = True, verbose_name = 'Disponible')
    position                 =   models.PositiveIntegerField(default = 0, verbose_name = 'Orden')
    created_at               =   models.DateTimeField(auto_now_add = True)
    class Meta:
        app_label               =   'memberships'
        verbose_name            =   'Plan de suscripción'
        verbose_name_plural     =   'Planes de suscripción'
        ordering                =   ['position', 'name', 'id']
        indexes                 =   [
            #Listados del dueño: sus planes, activos primero por orden.
            models.Index(fields = ['store', 'is_active'], name = 'idx_storeplan_store_active'),
        ]
        constraints             =   [
            models.CheckConstraint(condition = models.Q(price__gte = 0), name = 'ck_storeplan_price_gte_0'),
            models.CheckConstraint(condition = models.Q(discount_percent__gte = 0, discount_percent__lte = 100), name = 'ck_storeplan_discount_range'),
        ]
    def __str__(self):
        return f'{self.name} ({self.store.slug})'
    def duration_days(self):
        """
        Días que otorga una suscripción vigente a este plan: 30/365 fijos
        para monthly/yearly; period_days solo manda en 'custom'.
        """
        return self.PERIOD_DAYS.get(self.period) or self.period_days
#=========================================
# STORE SUBSCRIPTION (customer × plan — historial por membresía)
#=========================================
class StoreSubscription(models.Model):
    """
    Suscripción de UN cliente (StoreMembership) a UN plan de ESA tienda.
    UN cliente puede acumular historial (renovaciones = filas nuevas);
    como mucho UNA pendiente a la vez (constraint parcial abajo).

    Estados: pending (creada, esperando que el dueño acredite el cobro
    manual) → active (grant_period fija started_at/vigente_hasta) →
    past_due/cancelled/expired. Los beneficios solo los da
    status='active' + vigente_hasta>now (ver services/benefits.py).
    """
    STATUS_PENDING          =   'pending'
    STATUS_ACTIVE           =   'active'
    STATUS_PAST_DUE         =   'past_due'
    STATUS_CANCELLED        =   'cancelled'
    STATUS_EXPIRED          =   'expired'
    STATUS_CHOICES          =   [
        (STATUS_PENDING,    'Pendiente de pago'),
        (STATUS_ACTIVE,     'Activa'),
        (STATUS_PAST_DUE,   'Pago vencido'),
        (STATUS_CANCELLED,  'Cancelada'),
        (STATUS_EXPIRED,    'Vencida'),
    ]
    #Estados desde los que el dueño puede pasar a 'active' (activate) o
    #'expired' (expire). 'cancelled'/'expired' son terminales.
    PAYMENT_TRANSFER        =   'transfer'
    PAYMENT_WHATSAPP        =   'whatsapp'
    PAYMENT_CASH            =   'cash'
    PAYMENT_MP              =   'mp'
    PAYMENT_MANUAL          =   'manual'
    PAYMENT_CHOICES         =   [
        (PAYMENT_TRANSFER,  'Transferencia'),
        (PAYMENT_WHATSAPP,  'WhatsApp'),
        (PAYMENT_CASH,      'Efectivo'),
        (PAYMENT_MP,        'Mercado Pago'),
        (PAYMENT_MANUAL,    'Manual'),
    ]
    membership              =   models.ForeignKey(StoreMembership, on_delete = models.CASCADE, related_name = 'subscriptions', db_index = False)
    plan                    =   models.ForeignKey(StorePlan, on_delete = models.PROTECT, related_name = 'subscriptions')
    status                  =   models.CharField(max_length = 10, choices = STATUS_CHOICES, default = STATUS_PENDING, verbose_name = 'Estado')
    started_at              =   models.DateTimeField(null = True, blank = True, verbose_name = 'Inicio')
    vigente_hasta           =   models.DateTimeField(null = True, blank = True, verbose_name = 'Vigente hasta')
    payment_method          =   models.CharField(max_length = 10, choices = PAYMENT_CHOICES, default = PAYMENT_MANUAL, verbose_name = 'Método de pago')
    payment_ref             =   models.CharField(max_length = 80, blank = True, verbose_name = 'Referencia de pago')
    public_token            =   models.CharField(max_length = 48, unique = True, editable = False, default = _public_token, verbose_name = 'Token público de la tarjeta')
    #Dedupe del aviso de vencimiento (comando membership_expiry_notices):
    #guarda el `vigente_hasta` por el que YA se avisó — si la suscripción
    #se renueva (vigente_hasta cambia) vuelve a notificar; correr el
    #comando dos veces el mismo día no duplica el mail.
    expiry_notified_until   =   models.DateTimeField(null = True, blank = True, verbose_name = 'Aviso de vencimiento enviado (vigente hasta)')
    created_at              =   models.DateTimeField(auto_now_add = True)
    updated_at              =   models.DateTimeField(auto_now = True)
    class Meta:
        app_label               =   'memberships'
        verbose_name            =   'Suscripción de tienda'
        verbose_name_plural     =   'Suscripciones de tienda'
        ordering                =   ['-created_at', '-id']
        indexes                 =   [
            #Lookup caliente del contrato: "¿tiene membresía vigente este
            #customer en esta tienda?" (membership, status, vigente_hasta)
            #cubre también el filtro por tienda vía join a membership.
            models.Index(fields = ['membership', 'status', 'vigente_hasta'], name = 'idx_subs_member_status_until'),
        ]
        constraints             =   [
            #Segunda capa de la idempotencia del subscribe: a lo sumo UNA
            #suscripción pendiente por membresía (el service chequea antes
            #bajo select_for_update; esto corta la carrera residual).
            models.UniqueConstraint(
                fields          =   ['membership'],
                condition       =   models.Q(status = 'pending'),
                name            =   'uniq_membership_pending_subscription',
            ),
        ]
    def __str__(self):
        return f'{self.membership_id} → plan {self.plan_id} [{self.status}]'
