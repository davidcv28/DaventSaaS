"""
Agregaciones del panel del dueño (storeadmin — Ola 2 e-commerce).

Reglas duras:

- TODO se agrega en DB (Sum/Count/Max/TruncDate, values+annotate y
  subqueries correlacionadas) — jamás se traen pedidos a Python para
  sumar. Los únicos loops Python son el relleno de días sin ventas de
  la serie diaria (acotado a MAX_RANGE_DAYS) y la escritura del CSV.
- La definición de "cobrado" vive ACÁ (`cobrado_q`) para que summary,
  daily, customers y el export compartan el mismo predicado:
  `paid_at IS NOT NULL` y status != REFUNDED. PAID es transitorio
  (mark_order_paid auto-avanza a PACKING), por eso el predicado es
  paid_at+status y no `status='PAID'`. Los reembolsados se reportan
  aparte (refunded_count/refunded_total) — la plata volvió.
- "Ganancias" = total vendido BRUTO: DAVENT no procesa los cobros del
  vendedor ni descuenta comisiones (Mercado Pago retiene las suyas
  aparte) — la respuesta del summary lo aclara en `note`.
- Fechas: `from`/`to` inclusivos en YYYY-MM-DD, interpretados en la TZ
  activa del settings (USE_TZ=True, TIME_ZONE='UTC'). El filtro va
  sobre `created_at` (fecha del pedido): `paid_at` no existe en los
  pendientes y no serviría de eje común del rango.
"""
import csv
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import (
    Count,
    DecimalField,
    F,
    Max,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import Coalesce, TruncDate
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from StoreApp.domains.customers.models import Customer, StoreMembership
from StoreApp.domains.memberships.models import StoreSubscription
from StoreApp.domains.orders.models import Order

#=========================================
# CONSTANTES
#=========================================
DEFAULT_RANGE_DAYS   =   30          #summary sin params: últimos 30 días
DAILY_DEFAULT_DAYS   =   90          #serie diaria sin params: últimos 90 días
MAX_RANGE_DAYS       =   366         #tope del rango (un año bisiesto)
EXPORT_MAX_ROWS      =   10_000      #techo del CSV — más que esto, 400
#Métodos de pago del enum del modelo — el filtro valida contra esto.
PAYMENT_METHODS      =   {choice for choice, _label in Order.PaymentMethod.choices}
ORDER_STATUSES       =   {choice for choice, _label in Order.Status.choices}
#=========================================
# PREDICADOS DE "COBRADO" (fuente única de verdad)
#=========================================
def cobrado_q(prefix = ''):
    """
    Q de "venta cobrada vigente" sobre Order — o sobre la relación
    `<prefix>` (p.ej. 'orders' desde Customer). Ver docstring del
    módulo: paid_at confirmado y no reembolsado.
    """
    p   =   f'{prefix}__' if prefix else ''
    return (
        Q(**{f'{p}paid_at__isnull': False})
        & ~Q(**{f'{p}status': Order.Status.REFUNDED})
    )
def pending_q(prefix = ''):
    """Q de pedido aún no pagado (PENDING_PAYMENT — incluye los que
    después vencerán/cancelarán; EXPIRED/CANCELLED no son 'pendientes')."""
    p   =   f'{prefix}__' if prefix else ''
    return Q(**{f'{p}status': Order.Status.PENDING_PAYMENT})
def _zero_money():
    return Value(Decimal('0.00'))
def _coalesce_money(expr):
    """
    Coalesce a 0.00 con output_field explícito: sin él, el Value
    mezclado puede ensanchar el DecimalField del agregado.
    """
    return Coalesce(expr, _zero_money(), output_field = DecimalField(max_digits = 14, decimal_places = 2))
def _money(value):
    """Decimal|None → string 'x.xx' para el JSON (el front formatea)."""
    if value is None:
        return '0.00'
    return str(Decimal(value).quantize(Decimal('0.01')))
#=========================================
# RANGOS DE FECHA (parse + validación)
#=========================================
def _parse_day(raw, field):
    """'YYYY-MM-DD' → date; cualquier otra cosa → ValidationError (400)."""
    try:
        return date.fromisoformat(str(raw).strip())
    except (TypeError, ValueError):
        raise ValidationError({field: 'Fecha inválida — usá el formato YYYY-MM-DD.'})
def _bounds(d_from, d_to):
    """(date, date) → (start_dt, end_dt_exclusive) aware en la TZ activa."""
    tz      =   timezone.get_current_timezone()
    start   =   datetime.combine(d_from, time.min, tzinfo = tz)
    end     =   datetime.combine(d_to + timedelta(days = 1), time.min, tzinfo = tz)
    return start, end
def resolve_date_range(params, *, default_days = DEFAULT_RANGE_DAYS, max_days = MAX_RANGE_DAYS):
    """
    `from`/`to` opcionales e inclusivos (YYYY-MM-DD). Sin params → los
    últimos `default_days` días hasta hoy. from>to o rango > max_days
    → 400. Devuelve (d_from, d_to, start_dt, end_dt_exclusive).
    """
    raw_from    =   params.get('from')
    raw_to      =   params.get('to')
    today       =   timezone.localdate()
    if raw_from or raw_to:
        if not (raw_from and raw_to):
            raise ValidationError({'detail': 'Los filtros "from" y "to" van juntos (YYYY-MM-DD).'})
        d_from  =   _parse_day(raw_from, 'from')
        d_to    =   _parse_day(raw_to, 'to')
        if d_from > d_to:
            raise ValidationError({'detail': '"from" no puede ser posterior a "to".'})
        if (d_to - d_from).days + 1 > max_days:
            raise ValidationError({'detail': f'El rango máximo es de {max_days} días — achicá el período o usá los filtros.'})
    else:
        d_to    =   today
        d_from  =   today - timedelta(days = default_days - 1)
    start, end  =   _bounds(d_from, d_to)
    return d_from, d_to, start, end
def resolve_daily_range(params):
    """
    Serie diaria: mismos `from`/`to` del summary o `days` (default 90,
    máx 366) cuando no hay fechas explícitas.
    """
    if params.get('from') or params.get('to'):
        return resolve_date_range(params)
    raw     =   params.get('days')
    try:
        days    =   int(str(raw if raw not in (None, '') else DAILY_DEFAULT_DAYS).strip())
    except (TypeError, ValueError):
        raise ValidationError({'days': 'Debe ser un entero (cantidad de días).'})
    if not (1 <= days <= MAX_RANGE_DAYS):
        raise ValidationError({'days': f'Entre 1 y {MAX_RANGE_DAYS} días.'})
    d_to    =   timezone.localdate()
    d_from  =   d_to - timedelta(days = days - 1)
    start, end  =   _bounds(d_from, d_to)
    return d_from, d_to, start, end
#=========================================
# FILTROS (payment_method / status)
#=========================================
def clean_payment_method(raw):
    value   =   (raw or '').strip().lower()
    if not value:
        return ''
    if value not in PAYMENT_METHODS:
        raise ValidationError({'payment_method': f'Inválido. Opciones: {", ".join(sorted(PAYMENT_METHODS))}.'})
    return value
def clean_status(raw):
    value   =   (raw or '').strip().upper()
    if not value:
        return ''
    if value not in ORDER_STATUSES:
        raise ValidationError({'status': f'Inválido. Opciones: {", ".join(sorted(ORDER_STATUSES))}.'})
    return value
def orders_in_range(store, start, end, payment_method = '', status = ''):
    """Queryset base de pedidos de LA tienda en el rango [start, end)."""
    qs  =   Order.objects.filter(store = store, created_at__gte = start, created_at__lt = end)
    if payment_method:
        qs  =   qs.filter(payment_method = payment_method)
    if status:
        qs  =   qs.filter(status = status)
    return qs
#=========================================
# VENTAS — RESUMEN
#=========================================
def build_sales_summary(store, d_from, d_to, start, end, payment_method = '', status = ''):
    """
    Agregados del rango: totales, ticket promedio, cortes por método de
    pago y por estado. Todo en DB (un aggregate + dos values+annotate).
    `note` aclara que los montos son brutos (sin comisiones de MP).
    """
    qs          =   orders_in_range(store, start, end, payment_method, status)
    paid_q      =   cobrado_q()
    pend_q      =   pending_q()
    agg         =   qs.aggregate(
        orders_count    =   Count('pk'),
        cobrado_count   =   Count('pk', filter = paid_q),
        gross_total     =   _coalesce_money(Sum('total', filter = paid_q)),
        pending_count   =   Count('pk', filter = pend_q),
        pending_total   =   _coalesce_money(Sum('total', filter = pend_q)),
        refunded_count  =   Count('pk', filter = Q(status = Order.Status.REFUNDED)),
        refunded_total  =   _coalesce_money(Sum('total', filter = Q(status = Order.Status.REFUNDED))),
    )
    cobrado_n    =   agg['cobrado_count'] or 0
    gross        =   agg['gross_total'] or Decimal('0')
    avg_ticket   =   (gross / cobrado_n).quantize(Decimal('0.01')) if cobrado_n else Decimal('0.00')
    #Cortes por método de pago — shape estable: las 4 opciones siempre.
    by_pm        =   {
        choice: {'orders_count': 0, 'total_cobrado': '0.00', 'total_pendiente': '0.00'}
        for choice, _label in Order.PaymentMethod.choices
    }
    for row in (qs.values('payment_method')
        .annotate(
            orders_count    =   Count('pk'),
            total_cobrado   =   _coalesce_money(Sum('total', filter = paid_q)),
            total_pendiente =   _coalesce_money(Sum('total', filter = pend_q)),
        )):
        by_pm[row['payment_method']] =   {
            'orders_count'      :   row['orders_count'],
            'total_cobrado'     :   _money(row['total_cobrado']),
            'total_pendiente'   :   _money(row['total_pendiente']),
        }
    #Cortes por estado — shape estable: los 8 estados siempre.
    by_status    =   {
        choice: {'orders_count': 0, 'total': '0.00'}
        for choice, _label in Order.Status.choices
    }
    for row in (qs.values('status')
        .annotate(
            orders_count    =   Count('pk'),
            total           =   _coalesce_money(Sum('total')),
        )):
        by_status[row['status']] =   {
            'orders_count'  :   row['orders_count'],
            'total'         :   _money(row['total']),
        }
    return {
        'from'              :   d_from.isoformat(),
        'to'                :   d_to.isoformat(),
        'orders_count'      :   agg['orders_count'] or 0,
        'cobrado_count'     :   cobrado_n,
        'gross_total'       :   _money(gross),
        'pending_count'     :   agg['pending_count'] or 0,
        'pending_total'     :   _money(agg['pending_total']),
        'refunded_count'    :   agg['refunded_count'] or 0,
        'refunded_total'    :   _money(agg['refunded_total']),
        'avg_ticket'        :   str(avg_ticket),
        'by_payment_method' :   by_pm,
        'by_status'         :   by_status,
        'note'              :   (
            'Montos en moneda de la tienda, brutos: DAVENT no procesa los cobros '
            'ni descuenta comisiones — si el cliente paga por Mercado Pago, MP '
            'retiene sus comisiones aparte del total vendido.'
        ),
    }
#=========================================
# VENTAS — SERIE DIARIA
#=========================================
def build_daily_series(store, d_from, d_to, start, end, payment_method = '', status = ''):
    """
    Un punto por día del rango (TruncDate en la TZ activa del settings):
    orders_count, total_cobrado y total_pendiente. Los días sin pedidos
    se rellenan con ceros — el front recibe una serie continua.
    """
    qs      =   orders_in_range(store, start, end, payment_method, status)
    rows    =   (qs
        .annotate(day = TruncDate('created_at'))
        .values('day')
        .annotate(
            orders_count    =   Count('pk'),
            total_cobrado   =   _coalesce_money(Sum('total', filter = cobrado_q())),
            total_pendiente =   _coalesce_money(Sum('total', filter = pending_q())),
        ))
    by_day  =   {row['day']: row for row in rows}
    series  =   []
    day     =   d_from
    while day <= d_to:
        row =   by_day.get(day)
        series.append({
            'date'              :   day.isoformat(),
            'orders_count'      :   row['orders_count'] if row else 0,
            'total_cobrado'     :   _money(row['total_cobrado']) if row else '0.00',
            'total_pendiente'   :   _money(row['total_pendiente']) if row else '0.00',
        })
        day +=  timedelta(days = 1)
    return series
#=========================================
# CLIENTES (LTV del dueño)
#=========================================
CUSTOMER_ORDERING   =   {
    'created_at'        :   ['created_at'],
    '-created_at'       :   ['-created_at'],
    'last_order_at'     :   [F('last_order_at').asc(nulls_last = True)],
    '-last_order_at'    :   [F('last_order_at').desc(nulls_last = True)],
    'total_spent'       :   ['total_spent'],
    '-total_spent'      :   ['-total_spent'],
    'orders_count'      :   ['orders_count'],
    '-orders_count'     :   ['-orders_count'],
    #`joined_at` ordena por la membresía en ESTA tienda (anotada como
    #store_joined_at) — el serializer expone el mismo dato como joined_at.
    'joined_at'         :   [F('store_joined_at').asc(nulls_last = True)],
    '-joined_at'        :   [F('store_joined_at').desc(nulls_last = True)],
    'email'             :   ['email'],
    '-email'            :   ['-email'],
}
CUSTOMER_ORDERING_DEFAULT =   [F('last_order_at').desc(nulls_last = True), '-created_at']
def clean_membership_filter(raw):
    """
    ?membership= → 'active' | 'suspended' | 'none' (sin membresía en la
    tienda — solo compró). Vacío = sin filtro. Inválido → 400.
    """
    value   =   (raw or '').strip().lower()
    if not value:
        return ''
    valid   =   {StoreMembership.STATUS_ACTIVE, StoreMembership.STATUS_SUSPENDED, 'none'}
    if value not in valid:
        raise ValidationError({'membership': f'Inválido. Opciones: {", ".join(sorted(valid))}.'})
    return value
def clean_ordering(raw):
    """
    ?ordering= con whitelist (nunca order_by crudo del usuario — inyección
    de campos). Acepta prefijo '-' para descendente. Default: actividad
    reciente primero (last_order_at desc, nulls al final, luego alta).
    """
    value   =   (raw or '').strip()
    if not value:
        return list(CUSTOMER_ORDERING_DEFAULT)
    if value not in CUSTOMER_ORDERING:
        raise ValidationError({'ordering': f'Inválido. Opciones: {", ".join(sorted(CUSTOMER_ORDERING))}.'})
    return CUSTOMER_ORDERING[value]
def build_customer_queryset(store, q = '', membership = ''):
    """
    Clientes DE la tienda = StoreMembership ∪ compradores con pedidos.

    Un pedido crea/usa un Customer pero NO crea membresía (la membresía
    nace del alta/login con store_slug — services.customers
    .ensure_membership), así que un comprador que solo pidió sin
    registrarse en la tienda existe como cliente sin membresía: la
    unión por `pk__in` (subqueries, sin JOINs) lo incluye igual.

    Los agregados (orders_count/total_spent/last_order_at) se anotan
    sobre la relación `orders` filtrada por ESTA tienda — una sola
    relación multivaluada joineada → sin fan-out, los Counts/Sums no se
    multiplican. `total_spent` usa cobrado_q: LTV bruto de ventas
    vigentes (sin pendientes, cancelados, expirados ni reembolsos).
    """
    member_ids  =   StoreMembership.objects.filter(store = store).values('customer_id')
    order_ids   =   Order.objects.filter(store = store).values('customer_id')
    qs          =   Customer.objects.filter(Q(pk__in = member_ids) | Q(pk__in = order_ids))
    if q:
        qs      =   qs.filter(
            Q(first_name__icontains = q)
            | Q(last_name__icontains = q)
            | Q(email__icontains = q)
        )
    if membership == 'none':
        qs      =   qs.exclude(pk__in = member_ids)
    elif membership in (StoreMembership.STATUS_ACTIVE, StoreMembership.STATUS_SUSPENDED):
        qs      =   qs.filter(
            pk__in =   StoreMembership.objects
                .filter(store = store, status = membership)
                .values('customer_id')
        )
    return (qs
        .annotate(
            orders_count    =   Count('orders', filter = Q(orders__store = store)),
            total_spent     =   _coalesce_money(Sum(
                'orders__total',
                filter =   Q(orders__store = store) & cobrado_q('orders'),
            )),
            last_order_at   =   Max('orders__created_at', filter = Q(orders__store = store)),
            #joined_at de la membresía en esta tienda (≤1 fila por el
            #unique customer×store) — subquery escalar, sin join extra.
            store_joined_at =   Subquery(
                StoreMembership.objects
                .filter(store = store, customer = OuterRef('pk'))
                .values('joined_at')
            ),
        ))
def memberships_prefetch(store):
    """
    Prefetch de la membresía del cliente EN esta tienda (to_attr
    'store_memberships' — lista de ≤1) con sus suscripciones
    (select_related plan, más nueva primero) precacheadas: la lista y
    el detalle serializan sin N+1.
    """
    subscriptions_qs    =   (StoreSubscription.objects
        .select_related('plan')
        .order_by('-created_at', '-id'))
    return Prefetch(
        'memberships',
        queryset =   (StoreMembership.objects
            .filter(store = store)
            .prefetch_related(Prefetch('subscriptions', queryset = subscriptions_qs))),
        to_attr    =   'store_memberships',
    )
#=========================================
# EXPORT CSV (ventas del rango)
#=========================================
CSV_HEADERS   =   [
    'Fecha', 'Pedido', 'Cliente', 'Email', 'Método de pago', 'Estado',
    'Subtotal', 'Descuento', 'Envío', 'Total', 'Nº de factura',
]
#Prefijos que Excel/Sheets interpretan como fórmula — se neutralizan
#con apóstrofo inicial (CSV injection, OWASP).
_CSV_DANGER   =   ('=', '+', '-', '@', '\t', '\r')
def _csv_safe(value):
    """Celda segura para Excel: si empieza (tras espacios) con un
    prefijo de fórmula se antepone `'` — el apóstrofo queda como
    marcador de texto y la celda se muestra literal."""
    s   =   '' if value is None else str(value)
    if s.lstrip()[:1] in _CSV_DANGER:
        return "'" + s
    return s
def _payment_label(value):
    return dict(Order.PaymentMethod.choices).get(value, value)
def _status_label(value):
    return dict(Order.Status.choices).get(value, value)
def build_sales_csv_response(store, d_from, d_to, start, end, payment_method = '', status = ''):
    """
    CSV de pedidos del rango (mismos filtros que el summary). UTF-8 con
    BOM para que Excel abra los acentos bien; escape de fórmulas por
    celda; tope EXPORT_MAX_ROWS → 400 sugiriendo achicar el rango.
    """
    qs  =   (orders_in_range(store, start, end, payment_method, status)
        .order_by('created_at', 'id')
        .values_list(
            'created_at', 'number',
            'customer_first_name', 'customer_last_name', 'customer_email',
            'payment_method', 'status',
            'subtotal', 'discount_total', 'shipping_cost', 'total',
            'invoice_ref',
        ))
    if qs.count() > EXPORT_MAX_ROWS:
        raise ValidationError({'detail': f'El rango supera las {EXPORT_MAX_ROWS:,} filas — achicá las fechas o agregá filtros (p.ej. payment_method).'})
    response    =   HttpResponse(content_type = 'text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="ventas-{store.slug}-{d_from.isoformat()}-{d_to.isoformat()}.csv"'
    )
    #BOM UTF-8: sin él Excel en es-AR lee los acentos como latin-1.
    response.write('\ufeff')
    writer  =   csv.writer(response)
    writer.writerow(CSV_HEADERS)
    for (created_at, number, first_name, last_name, email,
         pm, st, subtotal, discount, shipping, total, invoice_ref) in qs.iterator():
        name    =   f'{first_name or ""} {last_name or ""}'.strip()
        writer.writerow([
            _csv_safe(timezone.localtime(created_at).strftime('%d/%m/%Y %H:%M')),
            _csv_safe(f'PED-{number:04d}'),
            _csv_safe(name or '—'),
            _csv_safe(email),
            _csv_safe(_payment_label(pm)),
            _csv_safe(_status_label(st)),
            _csv_safe(subtotal),
            _csv_safe(discount),
            _csv_safe(shipping),
            _csv_safe(total),
            _csv_safe(invoice_ref),
        ])
    return response
