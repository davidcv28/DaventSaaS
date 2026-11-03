import csv
import io
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction

from StoreApp.domains.catalog.models import Product

"""

Actualización de precios del catálogo (del dueño autenticado):
- bulk_update_prices: aumento/baja masiva por porcentaje, monto fijo o
  precio nuevo, sobre todo el catálogo o un recorte (categoría, marca,
  productos elegidos), con redondeo opcional.
- parse_price_csv / import_prices: lista del proveedor en CSV — matchea
  por id o por nombre (insensible a mayúsculas) y actualiza price y/o
  offer_price. dry_run devuelve el reporte sin tocar la base.

"""
#=========================================
# CONSTANTES
#=========================================
BULK_MODES      =   ('percent', 'delta', 'set')
BULK_FIELDS     =   ('price', 'offer_price')
BULK_SCOPES     =   ('all', 'category', 'brand', 'products')
ROUNDINGS       =   ('none', 'unit', 'ten', 'hundred')
MAX_PRICE       =   Decimal('9999999999')
_MAX_ROWS       =   5000
#=========================================
# HELPERS PRIVADOS
#=========================================
def _quantize(value):
    return value.quantize(Decimal('0.01'), rounding = ROUND_HALF_UP)
def _round(value, rounding):
    if rounding == 'unit':
        return value.quantize(Decimal('1'), rounding = ROUND_HALF_UP)
    if rounding == 'ten':
        return (value / Decimal(10)).quantize(Decimal('1'), rounding = ROUND_HALF_UP) * Decimal(10)
    if rounding == 'hundred':
        return (value / Decimal(100)).quantize(Decimal('1'), rounding = ROUND_HALF_UP) * Decimal(100)
    return value
def _new_value(current, mode, value):
    if mode == 'percent':
        return current * (Decimal(100) + value) / Decimal(100)
    if mode == 'delta':
        return current + value
    return value
def parse_decimal(raw):
    """
    Número de una celda de la lista de precios: acepta "1234.56",
    "1.234,56" (AR) y "$ 1.234,56". None si no se puede leer.
    """
    text    =   str(raw or '').strip().replace('$', '').replace(' ', '')
    if not text:
        return None
    try:
        if '.' in text and ',' in text:
            text    =   text.replace('.', '').replace(',', '.')
        elif ',' in text:
            text    =   text.replace(',', '.')
        value   =   Decimal(text)
    except InvalidOperation:
        return None
    return value
def _norm(text):
    return ' '.join(str(text or '').split()).lower()
#=========================================
# BULK UPDATE (aumento/baja masiva)
#=========================================
def bulk_update_prices(store, *, mode, value, field, scope, category_id = None, brand_id = None, product_ids = None, rounding = 'none'):
    """
    Aplica el cambio a los productos del alcance y devuelve cuántos se
    tocaron. El resultado nunca baja de 0 ni pasa MAX_PRICE (clamp).
    `value` es Decimal ya validada por la vista.
    """
    qs          =   Product.objects.filter(store = store)
    if scope == 'category':
        qs      =   qs.filter(category_id = category_id)
    elif scope == 'brand':
        qs      =   qs.filter(brand_id = brand_id)
    elif scope == 'products':
        qs      =   qs.filter(id__in = product_ids or [])
    changed     =   []
    with transaction.atomic():
        for product in qs.select_for_update().iterator():
            current =   getattr(product, field) or Decimal('0')
            new     =   _quantize(_round(_new_value(current, mode, value), rounding))
            new     =   min(max(new, Decimal('0')), MAX_PRICE)
            if new == current:
                continue
            setattr(product, field, new)
            changed.append(product)
        if changed:
            Product.objects.bulk_update(changed, [field])
    return len(changed)
#=========================================
# CSV PARSING (lista del proveedor)
#=========================================
_COL_ID     =   {'id', 'codigo', 'código', 'sku', 'cod', 'code'}
_COL_NAME   =   {'nombre', 'name', 'producto', 'product', 'articulo', 'artículo', 'descripcion', 'descripción'}
_COL_PRICE  =   {'precio', 'price', 'precio_lista', 'lista', 'precio_nuevo'}
_COL_OFFER  =   {'oferta', 'offer', 'offer_price', 'precio_oferta', 'promo'}
def _column_indexes(header):
    indexes     =   {}
    for i, cell in enumerate(header):
        key     =   _norm(cell)
        if key in _COL_ID and 'id' not in indexes:
            indexes['id']       =   i
        elif key in _COL_NAME and 'name' not in indexes:
            indexes['name']     =   i
        elif key in _COL_PRICE and 'price' not in indexes:
            indexes['price']    =   i
        elif key in _COL_OFFER and 'offer' not in indexes:
            indexes['offer']    =   i
    return indexes
def parse_price_csv(upload):
    """
    (rows, fatal) del CSV subido. rows = [{line, key ('id:n' o 'name:x'),
    label, price, offer, error?}]. fatal = string cuando el archivo no se
    puede interpretar (sin header útil, vacío, etc.).
    """
    try:
        text    =   upload.read().decode('utf-8-sig')
    except (UnicodeDecodeError, AttributeError):
        return [], 'El archivo no es un CSV de texto (UTF-8).'
    sample      =   text[:4096]
    try:
        dialect =   csv.Sniffer().sniff(sample, delimiters = ',;\t')
    except csv.Error:
        dialect =   csv.excel
    reader      =   csv.reader(io.StringIO(text), dialect)
    rows        =   [row for row in reader if any(str(c).strip() for c in row)]
    if not rows:
        return [], 'El archivo está vacío.'
    indexes     =   _column_indexes(rows[0])
    if 'price' not in indexes or ('id' not in indexes and 'name' not in indexes):
        return [], 'El CSV necesita una columna de producto (id/nombre) y una de precio. Descargá la plantilla.'
    if len(rows) - 1 > _MAX_ROWS:
        return [], f'El archivo supera el máximo de {_MAX_ROWS} filas.'
    out         =   []
    for offset, row in enumerate(rows[1:], start = 2):
        ident   =   str(row[indexes['id']]).strip() if 'id' in indexes and indexes['id'] < len(row) else ''
        name    =   str(row[indexes['name']]).strip() if 'name' in indexes and indexes['name'] < len(row) else ''
        price   =   parse_decimal(row[indexes['price']]) if indexes['price'] < len(row) else None
        offer   =   parse_decimal(row[indexes['offer']]) if 'offer' in indexes and indexes['offer'] < len(row) else None
        item    =   {'line': offset, 'id': ident, 'name': name, 'price': price, 'offer': offer}
        if price is None and offer is None:
            item['error']   =   'precio ilegible'
        elif not ident and not name:
            item['error']   =   'sin producto'
        elif price is not None and not (Decimal('0') <= price <= MAX_PRICE):
            item['error']   =   'precio fuera de rango'
        elif offer is not None and not (Decimal('0') <= offer <= MAX_PRICE):
            item['error']   =   'oferta fuera de rango'
        out.append(item)
    return out, None
#=========================================
# IMPORT (aplicar la lista)
#=========================================
def import_prices(store, rows, dry_run = False):
    """
    Matchea cada fila por id (si vino) o por nombre normalizado y aplica
    los precios. Devuelve {updated, matched, skipped[], preview[]}; con
    dry_run no toca la base (preview = lo que cambiaría).
    """
    products    =   list(Product.objects.filter(store = store))
    by_id       =   {p.id: p for p in products}
    by_name     =   {}
    for p in products:
        by_name.setdefault(_norm(p.name), []).append(p)
    matched, skipped, preview, changed  =   [], [], [], []
    for row in rows:
        if row.get('error'):
            skipped.append({'line': row['line'], 'label': row.get('name') or row.get('id') or '', 'reason': row['error']})
            continue
        product     =   None
        if row.get('id'):
            try:
                product =   by_id.get(int(row['id']))
            except (TypeError, ValueError):
                product =   None
            if product is None:
                skipped.append({'line': row['line'], 'label': row['id'], 'reason': 'id no encontrado'})
                continue
        else:
            candidates  =   by_name.get(_norm(row.get('name')), [])
            if not candidates:
                skipped.append({'line': row['line'], 'label': row.get('name', ''), 'reason': 'no existe en tu catálogo'})
                continue
            if len(candidates) > 1:
                skipped.append({'line': row['line'], 'label': row.get('name', ''), 'reason': 'nombre repetido: usá la columna id'})
                continue
            product     =   candidates[0]
        new_price   =   _quantize(row['price']) if row['price'] is not None else product.price
        new_offer   =   _quantize(row['offer']) if row['offer'] is not None else product.offer_price
        if row['offer'] is None and new_offer is not None and new_offer >= new_price:
            #La oferta vieja dejaría de ser menor que el nuevo precio: se limpia.
            new_offer   =   None
        elif new_offer is not None and new_offer >= new_price:
            skipped.append({'line': row['line'], 'label': product.name, 'reason': 'la oferta tiene que ser menor que el precio'})
            continue
        if new_price == product.price and new_offer == product.offer_price:
            matched.append(product)
            continue
        preview.append({'id': product.id, 'name': product.name, 'old_price': str(product.price), 'new_price': str(new_price), 'old_offer': str(product.offer_price) if product.offer_price is not None else None, 'new_offer': str(new_offer) if new_offer is not None else None})
        product.price       =   new_price
        product.offer_price =   new_offer
        matched.append(product)
        changed.append(product)
    if changed and not dry_run:
        with transaction.atomic():
            Product.objects.bulk_update(changed, ['price', 'offer_price'])
    return {
        'updated'   :   len(changed),
        'matched'   :   len(matched),
        'skipped'   :   skipped,
        'preview'   :   preview,
    }
