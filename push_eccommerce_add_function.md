# PROMPT — Ecommerce fase 2b: pulido visual + plantillas de comprador (auth, cuenta, carrito/checkout, todos los diseños)

Sos el ORQUESTADOR de un grupo de subagentes trabajando sobre la rama `ECCOMMERCE-ADD` del repo `SaaS DAVENT` (raíz: `C:\Users\David\OneDrive\Escritorio\SaaS DAVENT`). Tu rol: dividir la tarea en tracks con ownership disjunto, lanzarlos en paralelo, revisar cada diff, correr seed/lint/build/tests en serie, commitear y pushear por track. NO codeás los tracks vos mismo salvo fixes de integración menores.

Pedido del usuario (literal): mejorar las nuevas plantillas y todo lo relacionado al ecommerce, trabajar en los distintos diseños, cuidar el responsive, crear un panel para el usuario más profesional, una plantilla de autenticación, mejorar sí o sí los diseños ya existentes — todo debe verse profesional a más no poder.

## Contexto que YA existe (no re-implementar)

- Ecommerce completo en `ECCOMMERCE-ADD`: `customers` (JWT `customer_access`/`customer_refresh`, Google login), `cart`, `orders` (tracking público por token, comprobante no fiscal), `storepayments`, `memberships`, `legalpages`, `support`. Stock con bloqueo pesimista ya mergeado (`select_for_update` en checkout y `mark_paid`).
- Storefront Vue 3 + Pinia: `StorePublicLayout` (shell + overlays teleportados a `.store-page`), `StoreAuthModal` (modal global de auth comprador), `StoreCartDrawer`, `StoreCheckoutView`, `StoreTrackingView`, `StoreReceiptView`, `StoreAccountView` (tabs `?view=` pedidos|suscripciones|direcciones|soporte|perfil), `PlanesView`, `StoreLegalView`, `StickyBuyBar`.
- Plantillas Vue en `frontend/src/views/store/{raiz,mercado,gimnasio,impacto,indumentaria,moderntec,movimiento,sastreria}` — las 7 pieles reusan sub-árboles Raíz bajo `.store-page[data-template='<piel>']` con su propia hoja `frontend/src/assets/store-<piel>.css`. CSS compartido en `frontend/src/assets/store-*.css` (`store-page.css`, `store-tpl-card.css`, `store-raiz-catalog.css`, etc.).
- Patrones HTML en `StoreApp/domains/design/sources/*.html` (23): se parten con `source_document.py`, se renderizan con `pattern_document.py` y los mejora `pattern_bridge.js` (inyecta `.dsx-buy` en `.ds-product`, `.dsx-account`, theme toggle, filtros, scroll, postMessage `davent:ds-*`). Documentos en iframe **sandbox sin `allow-same-origin`**: prohibido `fetch`/`sessionStorage` — toda API va por `postMessage` (`davent:ds-api`, `davent:ds-buy`, `davent:ds-account`, `davent:ds-cart`).
- Contrato `data-ds-*`: `data-ds-commerce="1"` (tienda con venta online), `data-ds-product`, `data-ds-buy`, `data-ds-account`, `data-ds-account-slot`, `data-ds-route`, `data-ds-surface`, `data-ds-pin`, `data-ds-theme-lock`, `data-ds-view-mode`. Seed: `manage.py seed_design_catalog` desde `seed_data.json`.
- QA visual: `frontend/scripts/visual-qa.mjs` + `visual-qa.config.json` (`npm run visual:qa`, flags `--only=<slug>`, `--surface`, `--viewport`, `--baseline`, `--update-baseline`, `--headed`). Audita overflow horizontal, errores de consola, overflow de texto y contraste AA en los viewports 390×844 / 768×1024 / 1360×900.
- Reglas: ver `AGENTS.md` — imágenes siempre WebP vía `normalize_image`, commits por track + push, respuestas cortas, no commitear `.env`/`venv`/`node_modules`/`dist`.

## Reglas de orquestación

1. Ownership de archivos DISJUNTO entre tracks paralelos. Si dos tracks necesitan el mismo archivo, el orquestador lo resuelve en integración.
2. Ningún subagente corre `migrate`/`makemigrations` de otra app ni `manage.py test` global (test DB Postgres compartida — la suite corre en serie al integrar). Escriben código + tests; vos corrés.
3. Cada track: subagente con prompt autocontenido (rutas exactas, contratos, qué NO tocar). Revisás el diff, corré lint/build del front + tests del dominio tocado, commiteás por track.
4. Frontend: componentes nuevos siguen las convenciones de `frontend/src/views/store/raiz/` y `frontend/src/components/store/` (tokens `--sp-*`/`--rz-*`/`--st-*`, `AppIcon`, `formatARS`, `storeContactLink`). HTML de patrones sigue el contrato `data-ds-*` y NO usa `fetch` directo.
5. Frontera legal intacta: DAVENT no vende, no cobra ni retiene fondos, no emite comprobantes fiscales de terceros — el contrato es comprador↔dueño. Nada de copy que sugiera lo contrario.
6. Todo debe verse profesional: jerarquía tipográfica, espaciado con tokens, empty/loading/error states, responsive mobile-first, contraste AA en claro Y oscuro, `prefers-reduced-motion` respetado, targets táctiles ≥44px.
7. Verificación final con browser-automation (DOM real): `/ingresar`, `/cuenta`, `/carrito`, `/checkout`, `/seguimiento`, comprobante, y 2-3 diseños representativos en claro y noche — 0 errores de consola ni requests fallidos.

---

## Tracks (ownership disjunto)

### AUTH — Plantilla de autenticación del comprador
**Archivos**: `frontend/src/views/StoreAuthView.vue` (nueva), `frontend/src/components/ecommerce/StoreAuthForm.vue` (nueva, compartida), `frontend/src/components/ecommerce/StoreAuthModal.vue`, `frontend/src/stores/cart.store.js`, `frontend/src/router/index.js`, `frontend/src/assets/store-*-auth*.css` (nuevas por piel si hace falta).

- Hoy el auth es solo un modal genérico. Crear página completa `/<slug>/ingresar` (nombre de ruta `store-auth`): login/registro/recuperación por `?mode=`, destino post-auth `?next=` sanitizado (anti open-redirect: solo paths internos `/`, rechazar `//` y `\`).
- `StoreAuthForm` = UN solo formulario usado por la página y por el modal global (que queda para pendientes de acción `{action}` que no pueden cruzar navegación).
- Soportar tema/piel de la tienda activa (tokens `--sp-*`/`--store-accent*`) y Google login si `google-config` lo habilita. Verificación de email y reseteo ya tienen sub-rutas `/cuenta/verificar` y `/cuenta/restablecer` — reutilizar.
- `cart.store`: helpers `authRoute(mode, next)` / `authNextPath(next)`; redirects alias `/tienda/:slug/{ingresar,carrito,pedido/:token/comprobante}` hacia las rutas hijas.
- El gate de `/cuenta` y `/checkout` navegan a `store-auth` con `?next=` si la ruta existe (`router.hasRoute`), fallback al modal.

### ACCOUNT — Panel de cuenta del comprador
**Archivos**: `frontend/src/views/StoreAccountView.vue`, `frontend/src/components/ecommerce/account/*.vue` (nuevos), CSS propio del panel.

- Rediseño profesional: sidebar en desktop (≥1024px: avatar con iniciales, nombre, nav con íconos, logout) y header compacto + tabs con scroll horizontal en mobile. Tabs `?view=`: pedidos | suscripciones | direcciones | soporte | perfil (se conservan los nombres de query).
- Extraer cada tab a su componente `account/Account{Orders,Subscriptions,Addresses,Profile}.vue`; soporte reusa `SupportPanel`. Pedidos con pills semánticos por estado + links a seguimiento/comprobante; suscripciones con tarjeta de miembro; direcciones CRUD; perfil autocontenido.
- Gate de invitado profesional (CTA a `store-auth` con `?next=`), no auto-abrir modal.

### CHECKOUT — Flujo de compra
**Archivos**: `frontend/src/views/Store{Cart,Checkout,Tracking,Receipt}View.vue`, `frontend/src/views/store/PlanesView.vue`, `frontend/src/components/ecommerce/{StoreCartDrawer,PlanSubscribe,CaptchaField,PaymentInstructions,SupportPanel}.vue`, `frontend/src/components/store/StickyBuyBar.vue`, `frontend/src/views/StorePublicLayout.vue`.

- Carrito página completa, drawer, checkout (stepper real Entrega→Pago→Confirmar, resumen colapsable mobile, métodos de pago con ícono+hint), tracking (stepper con conectores, chips de datos, upload de comprobante con preview), comprobante imprimible, planes/suscripciones, soporte.
- Empty/loading/error states con skeletons; `?next=`/`goAuth` hacia `store-auth` con fallback al modal; watcher de sesión que retoma la carga al volver del login.
- En `StorePublicLayout`: `ECOMMERCE_ROUTES` debe incluir TODAS las rutas decommerce (`store-checkout`, `store-tracking`, `store-cart`, `store-receipt`, `store-auth`, `store-plans`, `store-account*`, `store-legal*`) para que el iframe del patrón no las tape.

### VUE-CORE — Componentes storefront compartidos
**Archivos**: `frontend/src/components/store/TplProductCard.vue`, `frontend/src/views/store/raiz/{CatalogoView,ProductoView,ServiciosView}.vue`, componentes `store/blocks/*` que compartan los templates.

- Tarjetas de producto, catálogo, ficha y servicios de Raíz (base de las 7 pieles): pulido visual, responsive, qty stepper en PDP, lightbox de imagen, related con cat/brand, CTAs de compra coherentes con `ordersEnabled`.
- Los tokens de tarjeta `--tpc-name-*` (size/weight/transform) que las pieles ya declaran deben consumirse en `TplProductCard`/CSS — si un token existe y no se aplica, es bug.

### VUE-CSS — Hojas compartidas
**Archivos**: `frontend/src/assets/store-*.css` EXCEPTO `store-<piel>.css` de los tracks de skins (esos son SKINS-A/B). Permitido: `store-page.css`, `store-tpl-card.css`, `store-raiz-catalog.css`, `store-ecommerce*.css` y cualquier hoja compartida.

- Solo selectores existentes: pulido de contraste AA (nada de verdes hardcodeados tipo `#00a650`/`#16a34a` sin token — usar `var(--sp-success)` o `color-mix`), espaciados, focus-visible, reduced-motion. Reportar CSS muerto para limpieza futura, no borrarlo sin confirmar.
- `.sp-form` (orbe/rotación de Raíz) y `.tpc-flag`/`.sp-card` spotlight: documentar qué reglas base hay que neutralizar por piel.

### SKINS-A — mercado, impacto, indumentaria, sastreria
**Archivos**: `frontend/src/assets/store-{mercado,impacto,indumentaria,sastreria}.css` + sus carpetas `views/store/<piel>/` si tienen componentes propios.

### SKINS-B — gimnasio, moderntec, movimiento
**Archivos**: `frontend/src/assets/store-{gimnasio,moderntec,movimiento}.css` + `views/store/<piel>/`.

- Ecommerce nativo por piel: secciones de catálogo/ficha/servicios ya montan Raíz bajo la piel — el trabajo es que los componentes ecommerce (cards, forms, CTAs, badges, account/cart entries) hablen el idioma visual de cada diseño (gimnasio = placas lima + mono; moderntec = panel instrumento/telemetría; movimiento = fichas + animaciones con reduced-motion).
- Neutralizar por piel las reglas base que no aplican (`.sp-form::before/::after`, `.sp-form-badge` rotado, `.tpc-flag` verde absoluto, spotlight `.sp-card`) igual que hicieron sastrería/indumentaria/mercado/impacto.
- Cuidar el bug conocido de doble padding en sub-árboles Raíz dentro del wrapper de la piel.

### PATTERNS-1..4 — sources/*.html agrupados
**Archivos**: `StoreApp/domains/design/sources/*.html` — dividir los 23 en 4 grupos disjuntos (~6 c/u). Cada track SOLO sus archivos.

- Cada patrón con `data-ds-commerce="1"` debe tener: CTA "Agregar al carrito" visible y con la piel del diseño (el bridge lo inyecta en `.ds-product` y `[data-surface="product"]` — el patrón aporta el CSS de `.dsx-buy`, `.dsx-account`, `.dsx-cart`), entrada de cuenta/carrito en el header (slot `data-ds-account-slot` o fallback del bridge), secciones ecommerce propias (catálogo con filtros, ficha con CTA, membresías/suscripciones si el diseño las tiene) coherentes con su identidad.
- Contraste AA de los elementos inyectados en claro y noche (tokens `--ds-accent`/`--ds-accent-ink` ya pensados para AA — no inventar pares). `data-ds-theme-lock` para patrones de modo único. Sin `fetch`: todo por el bridge/postMessage.
- Responsive: nada de overflow horizontal a 390px; headers que colapsan (cuenta→solo ícono, burger); grillas que reflowan; `data-ds-view-mode="list"` si el patrón lo soporta.
- Después de editar fuentes: el orquestador corre `seed_design_catalog` al integrar.

### BRIDGE — pattern_bridge.js + PatternSurface.vue
**Archivos**: `StoreApp/domains/design/services/pattern_bridge.js`, `frontend/src/components/store/PatternSurface.vue`.

- Píldoras gemelas cuenta/carrito inyectadas (`.dsx-account`, `.dsx-cart` con badge `.dsx-cart-badge`), CSS base `.dsx-*` elevado (hover/focus-visible/active/reduced-motion, breakpoint móvil que compacta a solo-ícono).
- Host→iframe: `davent:ds-cart-state {count}` empuja `cartStore.itemCount` (el documento es origen opaco, no puede leer la sesión). Iframe→host: `davent:ds-cart` → `router.push` a `/carrito` de ESA tienda (`storeHostSlug ? '/carrito' : '/<slug>/carrito'`); `davent:ds-account` → emit account como hoy.
- Anclaje del botón de compra: `.dsx-buy-wrap` flex column con `margin-top:auto` (CTA al pie en filas de altura desigual); `.dsx-col` solo cuando la tarjeta no es flex/grid; en `[data-surface="product"]` el CTA va dentro del slot de CTAs del diseño (nunca `<button>` dentro de `<a>`).
- `node --check` del bridge + QA visual de 2-3 patrones antes de entregar.

---

## Integración (orquestador)

1. Revisar cada diff por track; resolver conflictos de archivos compartidos (`StorePublicLayout`, `cart.store`, `store-page.css`, `seed_data.json`) en una sola pasada.
2. `venv/Scripts/python.exe manage.py seed_design_catalog` si cambiaron fuentes/patrones.
3. `cd frontend && npx eslint <archivos tocados>` + `npm run build` + `npm run test`. En Windows/esbuild: si el build falla por lock de TEMP, usar `TEMP=$(pwd)/.tmp-build TMP=$(pwd)/.tmp-build npm run build` y borrar `.tmp-build` después.
4. `npm run visual:qa` acotado a patrones tocados (`--only`) + smoke browser de las rutas ecommerce.
5. Commits por track (conventional, inglés) + `git push` a `ECCOMMERCE-ADD`.
6. Actualizar `PLAN_ECOMMERCE.md` con el estado de la ola.
