# Ola "auth + cuenta por diseño" — brief compartido

## Objetivo
Cada diseño del catálogo tiene su propia identidad visual en la autenticación del
comprador (`/ingresar`) y en su cuenta (`/cuenta` + secciones). Hoy todas
comparten la misma composición genérica (split 50/50, panel de color, tarjeta
blanca). Hay que darle a cada diseño una composición propia, arreglar el
responsive y garantizar que ninguna barra, fondo, hover o `select` tape texto ni
iconos.

## Archivos
- Creás **un archivo por diseño**: `frontend/src/assets/store-design-<slug>.css`.
- **No edites** archivos Vue/JS/CSS existentes. Si necesitás marcado nuevo,
  reportalo al orquestador; el marcado actual ya trae hooks decorativos.
- El archivo se carga solo en tiendas con ese diseño
  (`.store-page[data-design='<slug>']`), en todas sus páginas.

## Contrato técnico
- Todo selector arranca con `.store-page[data-design='<slug>']` y se limita al
  subárbol `.ec-auth*` / `.ec-account*` (no toques catálogo, ficha ni portada).
- Definí tokens propios en el scope (`--xx-paper`, `--xx-ink`, `--xx-accent`,
  `--xx-display`, `--xx-mono`, radios, líneas) y usalos en todo el archivo.
- Tipografías: las del diseño suelen viajar ya en `site_theme.typography` y se
  cargan en la página. Verificá en QA con
  `document.fonts.check('12px "Anton"')`. Siempre con fallback (`Georgia`,
  `system-ui`, `monospace`). Si falta la familia, podés cargarla con
  `@import url('https://fonts.googleapis.com/css2?family=...')` (la CSP permite
  `fonts.googleapis.com` y `fonts.gstatic.com`), pero preferí la que ya está.
- Modo oscuro: `.store-page[data-design='<slug>'][data-store-theme='dark'] ...`
  (los diseños con variante `-noche` usan esa misma marca).
- Especificidad: los `<style scoped>` de los componentes pesan (0,2,0). Tu
  selector `.store-page[data-design] .clase` es 0,3,0 y gana. `!important` solo
  cuando haga falta de verdad.
- Si animás algo: `@media (prefers-reduced-motion: reduce)` obligatorio.
- AA: texto ≥ 4.5:1, controles ≥ 3:1. `:focus-visible` visible en todo control.
- 360px sin scroll horizontal; 768 y 1280 sin solapamientos.

## Reglas de composición (lo importante)
- **Cada diseño usa una estrategia distinta.** Prohibido repetir: split 50/50
  con panel de color + tarjeta blanca, tarjeta centrada con sombra difusa,
  pestañas tipo pill.
- Variá de verdad: lado del panel de marca, proporción de columnas, tipo de
  contenedor (hoja, ticket con muescas, ficha, índice, consola, placa, dossier),
  tipografía (display vs mono), densidad, filetes, numeración, sellos, cintas,
  texturas de fondo.
- Auth: la marca puede ser banda superior, columna lateral, portada a sangre,
  sello, ticket con talón, cabecera de revista, credencial.
- Cuenta: el sidebar puede ser índice numerado, lomo de ticket, placa, rail
  vertical, ficha técnica; las secciones pueden ser ledger, dossier, fichas,
  pliego, consola.
- Hooks existentes que podés estilizar:
  `.ec-auth` `.ec-auth-shell` `.ec-auth-brand` `.ec-auth-brand-inner`
  `.ec-auth-brand-top` `.ec-auth-logo` `.ec-auth-brand-name` `.ec-auth-brand-copy`
  `.ec-auth-rail` (01) `.ec-auth-brand-kicker` `.ec-auth-brand-title`
  `.ec-auth-brand-text` `.ec-auth-perks` `.ec-auth-brand-foot` `.ec-auth-panel`
  `.ec-auth-back` `.ec-auth-head` `.ec-auth-badge` `.ec-auth-tag`
  `.ec-auth-title` `.ec-auth-sub` `.ec-auth-loading` `.ecaf*` (form)
  `.ec-account` `.acc-tele` `.acc-idx` `.acc-avatar` `.acc-id` `.acc-nav`
  `.acc-navitem` `.acc-tabs` `.acc-tab` `.acc-mhead` `.acc-side` `.acc-main`
  `.acc-panel*` `.acc-auth-card` `.acc-gate-card` `.acc-skelpanel`
  `.acc-logout` `.acc-icon-btn` `.ec-btn-primary` `.ec-btn-ghost`
- No inventes datos ni estados. Etiquetas decorativas cortas (Nº, índices,
  rótulos del propio diseño) sí.

## Prohibido
- Glow excesivo, gradientes genéricos, glassmorphism porque sí, sombras difusas
  grandes, emojis.
- Fondos u hovers opacos encima de iconos/texto: `select`, `option`, tabs, navs
  y botones tienen que quedar legibles en reposo, hover, focus y abierto.
- Tocar layout de otras páginas o cambiar lógica/props/emits.

## QA obligatorio (con capturas)
1. Desde la raíz del repo:
   ```
   STORE=<store> DESIGN=<slug> node "C:\Users\David\.claude\skills\browser-automation\browser.mjs" \
     http://localhost:5173/<store>/ingresar --script frontend/scripts/qa-ec-screens.mjs
   ```
   Carga la tienda una sola vez y cambia modos/secciones dentro de la página
   (el endpoint público tiene rate-limit). Si aparece 429, esperá el
   `Retry-After` y reintentá.
2. Leé las capturas de `frontend/visual-qa/<slug>/`: auth login/register/forgot
   1280, login 768 y 360, cuenta en sus 5 secciones a 1280, perfil 768 y 360.
3. En el reporte: `overflow.*.wide` vacío y `covered.*` vacío a 360/768.
4. Revisá a ojo hover/focus (tabs, navs, botones, links) y el `select` abierto
   del perfil.
5. Credenciales QA: `qa.visual@davent.test` / `QaVisual2026!`.

## Entrega
- Archivos creados + capturas revisadas + problemas que no pudiste resolver.
- Sin `git commit`: el orquestador integra y commitea.
