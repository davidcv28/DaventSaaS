import json
from PIL import ImageFont

FONTS = {
    'black': r'C:\Windows\Fonts\seguibl.ttf',
    'bold': r'C:\Windows\Fonts\segoeuib.ttf',
    'regular': r'C:\Windows\Fonts\segoeui.ttf',
}

PT2MM = 25.4 / 72.0

# (key, text, font, size_pt, letter_spacing_em)
ITEMS = [
    ('hook1', 'TU NEGOCIO', 'black', 25, 0),
    ('hook2', 'EN INTERNET.', 'black', 25, 0),
    ('brand', 'DAVENT', 'black', 12, 0.2),
    ('brand_back', 'DAVENT', 'black', 9.6, 0.18),
    ('eyebrow', 'LO QUE PODÉS HACER CON DAVENT', 'bold', 5.6, 0.15),
    ('perk1', 'Tu web con catálogo', 'bold', 7.3, 0),
    ('perk2', 'Pedidos por WhatsApp', 'bold', 7.3, 0),
    ('perk3', 'QR y folletos', 'bold', 7.3, 0),
    ('perk4', 'Estadísticas de visitas', 'bold', 7.3, 0),
    ('p1a', 'Productos, fotos y precios', 'regular', 6.1, 0),
    ('p1b', 'en un link propio.', 'regular', 6.1, 0),
    ('p2a', 'El cliente consulta y pide', 'regular', 6.1, 0),
    ('p2b', 'sin salir de tu web.', 'regular', 6.1, 0),
    ('p3a', 'Para tu local, tu vidriera', 'regular', 6.1, 0),
    ('p3b', 'y tus redes.', 'regular', 6.1, 0),
    ('p4a', 'Cuánta gente ve tu web', 'regular', 6.1, 0),
    ('p4b', 'cada día.', 'regular', 6.1, 0),
    ('s3a', 'Compartí el link y', 'regular', 5.9, 0),
    ('s3b', 'empezá a vender.', 'regular', 5.9, 0),
    ('promo1', '30 DÍAS DE PREMIUM DE REGALO', 'black', 9.4, -0.01),
    ('promo2a', 'Registrate y canjeá el código ', 'regular', 6.5, 0),
    ('promo2b', 'PROMO', 'black', 7, 0.04),
    ('promo2c', '. Sin tarjeta ni débito.', 'regular', 6.5, 0),
    ('fsub1', 'Creá tu web con catálogo, QR y pedidos por WhatsApp.', 'regular', 8, 0),
    ('fsub2', 'La armás en minutos y sin saber de tecnología.', 'regular', 8, 0),
    ('cta_label', 'CREÁ TU WEB GRATIS', 'bold', 5.7, 0.15),
    ('cta_url', 'www.davent.com.ar', 'black', 9.4, 0),
    ('cta_hint', 'Apuntá la cámara al QR y empezá hoy.', 'regular', 6.1, 0),
    ('wpp', '387 518-1791', 'bold', 7, 0),
    ('plan_basico', 'Básico', 'black', 9, 0),
    ('plan_estandar', 'Estándar', 'black', 9, 0),
    ('plan_premium', 'Premium', 'black', 9, 0),
    ('tag', 'MÁS ELEGIDO', 'bold', 4.9, 0.08),
    ('plan_desc1', 'Web con catálogo · hasta 100 productos · estadísticas', 'regular', 6.2, 0),
    ('plan_desc2', '+ QR, folletos, mapa y página de servicios', 'regular', 6.2, 0),
    ('plan_desc3', '+ asistencia en vivo, IA de diseño y sin límites', 'regular', 6.2, 0),
    ('b_title1', 'Elegí tu plan.', 'black', 15, -0.03),
    ('b_title2', 'Sin contratos.', 'black', 15, -0.03),
    ('b_sub', 'Pago mensual en pesos. Cambiás de plan o das de baja cuando quieras.', 'regular', 6.7, 0),
    ('trial_b', '¿Primera vez? Probá sin pagar', 'bold', 7, 0),
    ('trial_s', 'Al registrarte arrancás con un plan de prueba, sin tarjeta.', 'regular', 6.1, 0),
    ('steps_title', 'EMPEZÁ HOY EN 3 PASOS', 'bold', 5.6, 0.15),
    ('step1_b', 'Escaneá el QR', 'bold', 6.5, 0),
    ('step1_s', 'Entrás a la web de DAVENT.', 'regular', 5.9, 0),
    ('step2_b', 'Registrate', 'bold', 6.5, 0),
    ('step2_s', 'Con tu email y tu celular.', 'regular', 5.9, 0),
    ('step3_b', 'Publicá tu web', 'bold', 6.5, 0),
    ('step3_s', 'Compartí el link y empezá a vender.', 'regular', 5.9, 0),
    ('header_pill', 'PLANES Y PRECIOS', 'bold', 5.4, 0.14),
    ('b_foot_url', 'www.davent.com.ar', 'black', 8, 0),
    ('b_foot_tel', 'WhatsApp 387 518-1791', 'bold', 6.6, 0),
    ('fine', 'Precios en ARS por mes · renovación mensual · baja cuando quieras.', 'regular', 4.6, 0),
]

cache = {}
out = {}
for key, text, fk, size, ls in ITEMS:
    f = cache.get(fk, {})
    if size not in f:
        f[size] = ImageFont.truetype(FONTS[fk], size)
        cache[fk] = f
    font = f[size]
    base = font.getlength(text)
    width_mm = (base + ls * size * max(len(text) - 1, 0)) * PT2MM
    out[key] = round(width_mm, 3)

print(json.dumps(out, ensure_ascii=False, indent=1))
with open('metrics.json', 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
