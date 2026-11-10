# Prompt — Piel moderntec para auth y cuenta del comprador

Orquestá subagentes (`subagent_general`, background, ownership disjunto) para darle identidad `moderntec` a la autenticación y a la cuenta del COMPRADOR. Hoy se ven genéricas.

Lenguaje moderntec: "instrumento de laboratorio". Grafito `#06080c`, grilla fina, reglas de 1px, telemetría JetBrains Mono, display Outfit, acento cyan→violeta. Tokens `--mt-*` en `frontend/src/assets/store-moderntec.css` (leer solo el bloque de tokens, ~120 líneas).

## Wiring (hacer antes de lanzar los agentes)
1. Crear vacíos en `frontend/src/assets/`: `store-moderntec-auth.css`, `store-moderntec-account.css`, `store-moderntec-account-sections.css`.
2. En `frontend/src/views/StorePublicLayout.vue`, `TEMPLATE_CSS.moderntec` → `Promise.all` con `import()` de `store-moderntec.css` y las tres hojas.

## Subagentes
| Agente | Archivos propios (únicos que puede tocar) |
|---|---|
| Auth | `views/StoreAuthView.vue`, `components/ecommerce/StoreAuthForm.vue`, `components/ecommerce/StoreAuthModal.vue`, `assets/store-moderntec-auth.css` |
| Shell cuenta | `views/StoreAccountView.vue`, `components/ecommerce/account/AccountProfile.vue`, `assets/store-moderntec-account.css` |
| Secciones | `components/ecommerce/account/AccountOrders.vue`, `AccountAddresses.vue`, `AccountSubscriptions.vue`, `assets/store-moderntec-account-sections.css` |

## Reglas para todos
- Todo override scopeado con `.store-page[data-template='moderntec']`. Los `<style scoped>` de los componentes ganan por especificidad: usar `:is()`/`[data-store-template]` y `!important` solo si hace falta.
- Se puede agregar marcado (índices mono 01–05, chips de estado con datos reales, rail `01`) sin tocar lógica, props ni emits. Nada de telemetría inventada.
- Estados (pedido/suscripción) distinguibles sin depender solo del color (glifo + texto).
- Evitar clichés genéricos de IA (tarjeta centrada con gradiente, glow excesivo).
- Un `*/` dentro de un comentario CSS descarta el bloque entero.
- AA, `:focus-visible`, `prefers-reduced-motion`, 360px sin scroll horizontal.
- QA: `http://localhost:5173/mt-qa/ingresar` (`?mode=register|forgot`) y `/mt-qa/cuenta`. Verificar con screenshot (skill `browser-automation`).
- Sin `git commit` en los subagentes; el orquestador commitea solo los archivos de la tarea (el repo suele tener cambios ajenos sin commitear) y hace push a `main`.

## Pendiente conocido
- Estilar `PlanSubscribe` (hijo de Suscripciones).
- Timeline de pedidos (no existe en el marcado).
- Revisión visual de contraste, 360px y especificidad contra los `<style scoped>`.
- `npm run build` falló una vez por "Acceso denegado" en un temp de esbuild; reintentar.

---

# Prompt — Fix navbar + responsive del patrón `moderntec`

Orquestá subagentes (`subagent_general`, background, ownership disjunto) para corregir el navbar y el responsive del diseño `moderntec`. Síntomas reportados: "iconos que se tapan con el fondo" y "responsive roto".

## Contexto clave (verificado en sesión)
- Las tiendas con `DesignPattern` NO montan el skin Vue: `StorePublicLayout` sirve `StoreApp/domains/design/sources/<slug>.html` en iframe sandbox vía `/api/stores/public/<slug>/pattern/document/`. El fix va en el **source HTML**, NO en `frontend/src/assets/store-moderntec*.css` ni en vistas Vue.
- El chrome que inyecta el puente (`pattern_bridge.js` + `pattern_document.py`): píldoras `.dsx-account`/`.dsx-cart`, badge `.dsx-cart-badge`, filtro activo `.cat-filters .ds-cat[aria-pressed="true"]`, CTAs `.dsx-buy`, chat `.ds-chat-*`. Todos leen tokens `--ds-*` con **fallbacks claros `#111`/`#fff`** → invisibles sobre pieles oscuras si el source no los define.
- `m-lock` en `<html>` → el puente postea `davent:ds-lock` y bloquea el scroll del host. `davent:ds-frame` postea `{top, vh}` de la ventana visible (el iframe va estirado al alto del documento: `vh`/`bottom` miden la página entera). `data-ds-no-pin` excluye al elemento del pin de barras del puente. `data-ds-offset="64"` en el header hace exacto el scroll de anchors bajo el chrome fijo.
- Breakpoint commerce: con `html[data-ds-commerce="1"]` el cluster suma cuenta+carrito → el nav debe ceder antes (~920px) para no desbordar.

## División sugerida
| Agente | Archivo propio |
|---|---|
| Documento de patrón | `StoreApp/domains/design/sources/moderntec.html` (único) |
| Skin Vue (descartada tras verificar que no se sirve) | `frontend/src/assets/store-moderntec*.css`, `views/store/moderntec/*`, `components/store/blocks/moderntec/*` |

## Reglas duras
- Solo `sources/moderntec.html`. Prohibido tocar otros `sources/*.html`, `pattern_bridge.js`, `pattern_document.py`, `seed_data.json` ni frontend.
- Mantener hooks `data-ds-*` (`data-ds-pin`, `data-ds-route`, `data-ds-surface`, `data-ds-theme-lock`, `data-ds-offset`, `data-ds-no-pin`, `data-flag`, `data-off`), `{{...}}` de `render()` (nada de interpolación dentro de CSS `content`), sin `fetch` en el JS del patrón (datos por postMessage `davent:ds-api`/`davent:ds-frame`). `<script>` nuevo va antes de `</body>`: `split_document` lo manda al campo `js` y se sirve con nonce.
- Fallbacks `--ds-*` en `html` (especificidad 0-0-1 < `:root` del tema 0-1-0) para no pisar variantes de estilo ni el acento de la tienda.
- Menú móvil: el panel se posiciona con `davent:ds-frame` + `data-ds-no-pin`; cerrar con Escape, al navegar (`data-ds-route`/`data-ds-anchor`/`data-m-close`), al cambiar `data-ds-surface` (MutationObserver) y si el burger desaparece (resize). Foco al primer enlace y restauración.
- Sin `git commit` en subagentes; el orquestador commitea solo los archivos de la tarea y pushea (el repo suele tener cambios ajenos sin commitear).

## Verificación
- `split_document` balanceado (llaves HTML/CSS/JS), `sanitize_markup`+`pattern_document` limpio.
- `venv/Scripts/python.exe manage.py test StoreApp.domains.design.tests` (26 tests).
- Doc servido en vivo: `http://localhost:8000/api/stores/public/mt-qa/pattern/document/` (slug QA `mt-qa`, template/patrón moderntec, commerce activo). Tiendas locales con el patrón: `davent`, `nodo`, `qatienda`.
- QA visual con Playwright/`browser-automation`: viewports 1440 / 920 / 768 / 560 / 420 / 360px, overflow horizontal = 0, contraste AA = 0 fallos, menú móvil abre/cierra.

## Resultado aplicado (commit `d065a42e`, rama `ECCOMMERCE-ADD`)
- `--ds-*` fallbacks en `html` (acento cyan `#3dd6ff`, tinta `#04121a`, surface/muted/radius del diseño).
- `.dsx-account`/`.dsx-cart` → píldoras hermanas de `.top-wa` (mono uppercase, filete acento, `margin-inline-start:0` para anular el auto-margin del puente); `.dsx-cart-badge` con pareja acento/tinta + anillo `--bg`.
- `.m-burger` + `.m-menu`/`#mmenu`: el nav ya no queda inalcanzable ≤760px (y ≤920px con commerce); compactación ≤560/≤420px (`brand-name` fuera, WA mínimo).
- `.cat-filters .ds-cat[aria-pressed="true"]` píldora de acento (mata el subrayado genérico del host); `.ds-contact-row` a 1 columna en móvil.
- DB local sincronizada (`DesignPattern('moderntec').html/css/js` desde `split_document`); **producción requiere re-importar el source** — actualizar solo `html/css/js` para no pisar `layout`/`style`/`tags` (el comando `import_design_pattern` pisa `layout` con `style.layout` vacío).
