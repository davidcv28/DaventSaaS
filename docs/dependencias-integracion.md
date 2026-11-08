# Dependencias de integración — ola 2 (track F)

> Lo que los tracks A-E dejaron pendiente y que **solo** puede resolver la integración.
> Cada ítem trae el archivo exacto y el criterio. Nada de esto lo tocó A-E por scope.

## 1. Cablear `quality` en la respuesta del upload (track D)

`media_quality.quality()` está implementada y testeada, pero la respuesta HTTP no la incluye.

- `StoreApp/domains/stores/views/viewset.py` — acción `customization_logo` (~línea 1539) y
  `customization_cover` (~línea 1571): agregar `'quality': media_quality.quality(upload, 'logo' | 'cover')`
  al dict del `Response`. El `upload` ya fue `seek(0)`-eado por `normalize_image` y
  `_open_size` re-busca al inicio, así que es seguro llamarlo después de `upload_logo`/`upload_cover`
  dentro del mismo `try`. Importar `media_quality` junto a los demás services.
- `frontend/src/stores/store.store.js` — `uploadLogo`/`uploadCover` devuelven `bool`; si se quiere
  consumir `quality` desde el front, propagar `data.quality` (opcional: el hint ya funciona por
  inspección client-side en `MediaQualityHint.vue`).

Criterio: nunca rechazar el upload por calidad; `quality` es informativo.

## 2. Workaround de build en este entorno (esbuild + OneDrive)

`npm run build` falla con `[vite:esbuild-transpile] remove %TEMP%\esbuild-<hash>: Acceso denegado`
por huérfanos de esbuild dentro de OneDrive. **No es un defecto del código.** Correr con:

```powershell
cd frontend
$env:TMP = "C:\Users\David\OneDrive\Escritorio\SaaS DAVENT\.tmp_build"
$env:TEMP = $env:TMP
npm run build
```

Verificado: 933 módulos, build OK en 12s. Anotar esto en `AGENTS.md` como nota de entorno.

## 3. Estado de los gates al cerrar la ola 1

| Gate | Estado |
|------|--------|
| `npm run lint` | verde (0 errores) tras el cierre de B |
| `npm run verify:studio` | verde (reportado por E) |
| `npm run build` | verde con el workaround de §2 |
| `manage.py test StoreApp.domains.stores.tests_quality` | 7 tests OK |
| `manage.py test StoreApp.domains.stores.tests_media_quality` | 12 tests OK |
| `npm run visual:qa` | **hay FAIL reales** — ver §4 |

## 4. Fallos visuales reales encontrados por B (NO arreglar en F)

Son de severidad media/alta de `docs/audit-design-slop.md` y corresponden a la **ola 3**
(tracks G1-G4), no a la integración. F solo debe verificar que el gate los reporta y dejar constancia:

- `moda/moda` (documento): contraste `figcaption.hero-fig` ratio **1.23**, `p.form-title` **3.41**,
  `span.ds-contact-q` **4.33**.
- `neon` (documento, 4 estilos): `s.ds-product-old` (precio tachado) **3.38-3.91**.
- `aurum` (documento): text-overflow `span.foot-word` "ATELIER NUEVE" en footer móvil + contraste
  **4.43-4.47** (justo bajo 4.5).
- `impacto` (SPA, móvil): `sp-name` **1-1.05**, `tpc-stock` **3.13**, glifos `✳` del ribbon **1-2.69**.

## 5. Fixes de severidad alta de la auditoría que SÍ corresponden a F

De `docs/audit-design-slop.md` (top 5 de menor riesgo). Aplicar **solo** estos, en commits separados,
y verificar cada uno con `npm run visual:qa -- --only=<slug>`:

1. `StoreApp/domains/design/sources/showroom.html:31` — `--muted` → ≥ `#767676` (3.45 → AA).
2. `StoreApp/domains/design/sources/expediente.html:45` — `--muted` → ≥ `#6B6250` (3.55 → AA).
3. `StoreApp/domains/design/sources/atelier-noir.html:34` — `--muted` → ≥ `#7A6E5C` (3.43 → AA).
4. `StoreApp/domains/design/sources/viajero.html:50-52` — CTA con `--accent-deep` o tinta oscura
   (3.88 → ≥ 4.5).
5. `StoreApp/domains/design/sources/moderntec.html:7-8` — `<link>` de Google Fonts muerto por CSP
   → `@font-face` con gstatic (patrón ya usado en otros docs; ver `DESIGN_SYSTEM.md`).

Criterio: contraste calculado ≥ 4.5 en texto normal y ≥ 3.0 en grande, sin cambiar el look de día.
Si un fix rompe el render, revertir y reportarlo.

## 6. Reglas duras para F

- Contrato de tema retrocompatible: un tema sin la clave nueva se ve exactamente igual.
- Nada de `allow-same-origin`, `unsafe-inline` en CSP, ni `fetch` nuevo dentro de un patrón.
- Todo upload de imagen sigue pasando por `normalize_image` (WebP, EXIF corregido).
- Patrones sin requests externos (CSP `default-src 'none'`).
- `frontend/visual-qa/` es runtime gitignored: no commitear `current/`, `baseline/`, `.tmp/`,
  `.jobs/`, `report.json`. Los baselines pixel a pixel son opt-in (`--baseline`) y locales.
- No tocar los commits del usuario `7a49ab4` (portico plus/night) ni `0021106` (olivium).
- No hacer git: dejar el árbol listo y reportar qué se commitea por área.
