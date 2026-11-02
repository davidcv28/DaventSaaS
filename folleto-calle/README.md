# Folleto DAVENT para repartir en la calle

Diseño **A6 vertical (105 × 148 mm), a color, doble faz**, hecho a partir del sistema
DAVENT (misma marca, beneficios reales de los planes y el QR a `/login`).

## Archivos

| Archivo | Para qué sirve |
|---|---|
| `DAVENT-folleto-A6.pdf` | **Archivo de impresión principal.** 2 páginas A6 exactas (frente + dorso), 300 dpi. |
| `DAVENT-folleto-A6-con-sangrado.pdf` | Igual pero con **3 mm de sangrado** a cada lado (111 × 154 mm) para imprenta que corta a sangre. |
| `DAVENT-hoja-A4-4x-frentes.pdf` | Pliego A4 con **4 copias por hoja** (2×2) + marcas de corte. Pág. 1 frentes, pág. 2 dorsos. |
| `frente.png` / `dorso.png` | Vistas 300 dpi (1240 × 1748 px) para mandar por WhatsApp o revisar. |
| `frente.svg` / `dorso.svg` | Fuente vectorial (editable con Illustrator / Inkscape / Figma). |
| `build-folleto.cjs` | Genera los SVG y PNG. Config editable arriba de todo (`CFG`). |
| `measure.py` + `metrics.json` | Miden los textos para que nada se desborde al regenerar. |
| `compose.py` | Arma los PDF (A6, con sangrado y pliego A4). |
| `preview-hoja-A4.png` | Vista previa del pliego. |

## Cómo imprimir barato

- **Fotocopiadora / imprenta chica:** llevá `DAVENT-hoja-A4-4x-frentes.pdf`, pedí **doble faz
  "voltear por el borde largo"** y corte en 4. Salen 4 folletos por hoja A4.
- **Gráfica:** llevá `DAVENT-folleto-A6-con-sangrado.pdf` (papel obra 150 g mate, 4/4 colores).
- **En casa:** usá `DAVENT-folleto-A6.pdf` con "ajustar al área imprimible" (queda un borde
  blanco fino porque las impresoras hogareñas no imprimen al ras del papel).
- Cantidad sugerida para una salida a la calle: 250–500 unidades.

## Qué dice el folleto

- **Frente:** gancho ("Tu negocio en internet."), 4 beneficios (web con catálogo, pedidos por
  WhatsApp, QR/folletos, estadísticas), promo de 30 días de Premium con código `PROMO`, QR a
  `www.davent.com.ar/login` y WhatsApp de ventas.
- **Dorso:** los 3 planes con precio real del sistema (Básico $25.000 · Estándar $30.000 ·
  Premium $40.000), plan de prueba sin tarjeta, 3 pasos para arrancar y datos de contacto.

## Antes de mandar a imprimir

1. **Código `PROMO`:** el frente promete 30 días de Premium. Creá el cupón en el backend o no
   va a poder canjearse:
   ```bash
   venv/Scripts/python.exe manage.py create_coupon --code PROMO --plan "Plan premium" --days 30
   ```
   (o cambialo en `CFG.promoCode` / `CFG.promoDays` y volvé a generar).
2. **Precios:** están en `CFG.plans` con los valores del seed (`suscriptions.py`). Si cambian
   los precios, actualizá `CFG.plans` y regenerá.
3. **Teléfono / URL / QR:** todo sale de `CFG` (`phone`, `url`, `loginUrl`).

## Regenerar

```bash
node folleto-calle/build-folleto.cjs
python folleto-calle/compose.py
# si cambiás textos: python folleto-calle/measure.py  (antes del build)
```

Requiere `sharp` y `qrcode` (ya están en `frontend/node_modules`) y Pillow para los PDF.
