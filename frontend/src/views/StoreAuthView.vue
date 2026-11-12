<script setup>
// Página completa de auth del COMPRADOR: /<slug>/ingresar (+ /ingresar en
// host propio de tienda). Modos login | register | forgot por ?mode=
// (default login). ?next= es el destino post-auth — solo paths internos
// (anti open-redirect). Con sesión ya activa redirige a next o a la cuenta.
//
// El formulario es StoreAuthForm (el mismo del modal global): una sola
// lógica de campos/errores/Google BYO, dos envoltorios — esta página con
// la piel del diseño activo y el modal para acciones pendientes.
import { ref, computed, inject, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCustomerStore } from '../stores/customer.store.js'
import { storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import StoreAuthForm from '../components/ecommerce/StoreAuthForm.vue'
import '../assets/store-design-esencial-auth.css'

const ctx = inject('storePage')
const slug = computed(() => ctx?.slug?.value || ctx?.slug || '')
const pageTemplate = computed(() => ctx?.pageTemplate?.value || ctx?.pageTemplate || '')
const shopName = computed(() => ctx?.shopName?.value || ctx?.shopName || 'la tienda')
const custom = computed(() => ctx?.custom?.value || ctx?.custom || {})
const hasDesignAdvanced = computed(() => Boolean(ctx?.hasDesignAdvanced?.value ?? ctx?.hasDesignAdvanced))
// Ícono del sello circular por diseño: ModernTec usa rayo (técnico), el
// resto conserva la hoja editorial del diseño esencial.
const sealIcon = computed(() => (pageTemplate.value === 'moderntec' ? 'zap' : 'leaf'))
const ordersEnabled = computed(() => Boolean(ctx?.ordersEnabled?.value ?? ctx?.ordersEnabled))

const route = useRoute()
const router = useRouter()
const customer = useCustomerStore()

const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${slug.value}` }))
const accountTo = computed(() => (storeHostSlug ? '/cuenta' : `/${slug.value}/cuenta`))
const initial = computed(() => shopName.value.slice(0, 1).toUpperCase())
const logoUrl = computed(() => (typeof custom.value.logo === 'string' ? custom.value.logo : custom.value.logo?.url) || '')
// La portada es contenido premium (mismo gate que el hero): sin
// has_design_advanced el panel de marca va con la gradiente sola.
const coverUrl = computed(() => (hasDesignAdvanced.value ? ((typeof custom.value.cover === 'string' ? custom.value.cover : custom.value.cover?.url) || '') : ''))
const brandStyle = computed(() => (coverUrl.value ? { '--ec-cover': `url("${coverUrl.value}")` } : {}))

// ---------- modo (login | register | forgot) ----------
// ?mode= define el modo INICIAL (deep-linking desde authRoute y mails);
// el cambio interno NO escribe la query: el layout monta las vistas con
// :key="route.fullPath" y cada replace remontaría la página entera —
// se perdería lo tipeado y ensureSession pegaría a la API de nuevo.
const MODES = ['login', 'register', 'forgot']
const modeFromQuery = (m) => (MODES.includes(String(m)) ? String(m) : 'login')
const mode = ref(modeFromQuery(route.query.mode))
function setMode(m) { mode.value = modeFromQuery(m) }
// Cambios externos de la query (atrás/adelante, link con otro modo)
// sí se reflejan — son navegación real, no un simple switch de tabs.
watch(() => route.query.mode, (m) => { mode.value = modeFromQuery(m) })

const TITLES = { login: 'Ingresá a tu cuenta', register: 'Creá tu cuenta', forgot: 'Recuperá tu contraseña' }
const title = computed(() => TITLES[mode.value])
const MODE_TAGS = { login: 'Acceso', register: 'Registro', forgot: 'Recuperación' }
const modeTag = computed(() => MODE_TAGS[mode.value])
const subtitle = computed(() => {
  if (mode.value === 'register') return `Un solo registro en ${shopName.value} para comprar, suscribirte y seguir tus pedidos.`
  if (mode.value === 'forgot') return 'Te enviamos un enlace a tu correo para crear una contraseña nueva.'
  return `Pedidos, suscripciones y soporte de ${shopName.value} en un solo lugar.`
})

// ---------- ?next= (destino post-auth) ----------
// Solo paths internos: empiezan con '/', nunca '//' (open-redirect), sin
// backslashes ni tramo de autoridad. Además nunca puede apuntar a la
// propia página de auth (evita el loop /ingresar → /ingresar).
const nextPath = computed(() => {
  const q = route.query.next
  const raw = String(Array.isArray(q) ? q[0] : q || '')
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.includes('\\')) return ''
  if (raw.split(/[?#]/)[0].endsWith('/ingresar')) return ''
  return raw
})
function goNext() {
  router.replace(nextPath.value || accountTo.value)
}

// ---------- session gate ----------
// 'checking' mientras ensureSession resuelve la cookie de refresh; si ya
// hay sesión no tiene sentido mostrar el formulario — se redirige.
const sessionState = ref('checking') // checking | guest | auth
onMounted(async () => {
  try {
    const ok = await customer.ensureSession()
    if (ok && customer.isAuthenticated) {
      sessionState.value = 'auth'
      goNext()
      return
    }
  } catch { /* sin sesión recuperable: se muestra el formulario igual */ }
  sessionState.value = 'guest'
})
function onAuthed() { goNext() }

// ---------- panel de marca ----------
const BRAND_TITLES = {
  login: 'Qué bueno verte de nuevo',
  register: 'Sumate y comprá más fácil',
  forgot: 'Tranquilo, lo resolvemos',
}
const brandTitle = computed(() => BRAND_TITLES[mode.value])
const brandText = computed(() => (
  custom.value.headline || custom.value.description
    || `Comprá en ${shopName.value}, seguí tus pedidos y accedé a tus beneficios y suscripciones.`
))
const perks = computed(() => {
  const list = []
  if (ordersEnabled.value) list.push({ icon: 'shopping-cart', text: 'Carrito guardado y checkout más rápido' })
  list.push({ icon: 'package', text: 'Seguimiento de pedidos en tiempo real' })
  list.push({ icon: 'crown', text: 'Suscripciones y beneficios de miembro' })
  list.push({ icon: 'map-pin', text: 'Direcciones y soporte en un solo lugar' })
  return list
})

// ---------- ornamento editorial (solo piel esencial) ----------
// Índice del modo activo (01/02/03) y sello circular giratorio. El markup
// nace oculto (ver <style scoped>) y la piel esencial lo muestra: para el
// resto de los diseños no existe.
const MODE_INDEX = [
  { key: 'login', n: '01', label: 'Ingresar' },
  { key: 'register', n: '02', label: 'Crear cuenta' },
  { key: 'forgot', n: '03', label: 'Recuperar' },
]
const sealText = computed(() => {
  const name = shopName.value.length > 22 ? `${shopName.value.slice(0, 21)}…` : shopName.value
  return `${name} · cuenta de comprador ·`.toUpperCase()
})
</script>

<template>
  <!-- El layout público no renderiza <main>: cada página hija lo pone, así
       que el landmark de contenido principal nace acá. -->
  <main class="sp-page-root ec-auth">
    <!-- Fondo ambiental (esencial): dos deriva de gradientes + grano. Solo
         transform/opacity, nunca background-position. -->
    <div class="ec-auth-ambient" aria-hidden="true">
      <span class="ec-auth-glow ec-auth-glow-a"></span>
      <span class="ec-auth-glow ec-auth-glow-b"></span>
      <span class="ec-auth-grain"></span>
    </div>

    <div class="ec-auth-shell">
      <!-- ===== Panel de marca (piel del diseño activo) ===== -->
      <aside class="ec-auth-brand" :style="brandStyle" aria-label="Tu cuenta en la tienda">
        <span class="ec-auth-hatch" aria-hidden="true"></span>
        <div class="ec-auth-brand-inner">
          <RouterLink :to="homeTo" class="ec-auth-brand-top">
            <span class="ec-auth-logo">
              <img v-if="logoUrl" :src="logoUrl" :alt="`Logo de ${shopName}`" />
              <template v-else>{{ initial }}</template>
            </span>
            <span class="ec-auth-brand-name">{{ shopName }}</span>
          </RouterLink>

          <div class="ec-auth-brand-copy">
            <span class="ec-auth-rail" aria-hidden="true">01</span>
            <p class="ec-auth-brand-kicker">Cuenta de comprador</p>
            <h1 class="ec-auth-brand-title">{{ brandTitle }}</h1>
            <p class="ec-auth-brand-text">{{ brandText }}</p>
            <ol class="ec-auth-index" aria-hidden="true">
              <li v-for="it in MODE_INDEX" :key="it.key" :class="{ 'is-on': it.key === mode }">
                <span class="ec-auth-index-n">{{ it.n }}</span>
                <span class="ec-auth-index-l">{{ it.label }}</span>
              </li>
            </ol>
            <ul class="ec-auth-perks">
              <li v-for="p in perks" :key="p.text">
                <AppIcon :name="p.icon" :size="15" aria-hidden="true" />
                <span>{{ p.text }}</span>
              </li>
            </ul>
          </div>

          <p class="ec-auth-brand-foot">Sesión segura · Acceso directo a tu cuenta</p>
        </div>

        <!-- Sello circular giratorio (ornamento, no información). -->
        <span class="ec-auth-seal" aria-hidden="true">
          <svg class="ec-auth-seal-ring" viewBox="0 0 100 100" focusable="false">
            <defs>
              <path id="ec-auth-seal-path" d="M50,50 m-38,0 a38,38 0 1,1 76,0 a38,38 0 1,1 -76,0" />
            </defs>
            <text>
              <textPath href="#ec-auth-seal-path" startOffset="0" textLength="238" lengthAdjust="spacing">{{ sealText }}</textPath>
            </text>
          </svg>
          <AppIcon :name="sealIcon" :size="17" />
        </span>
      </aside>

      <!-- ===== Panel del formulario ===== -->
      <!-- <section> nombrada por el h2 del modo activo: el header/footer del
           formulario dejan de exponerse como banner/contentinfo (dentro de
           sectioning content no lo son) y el formulario queda como region. -->
      <section
        class="ec-auth-panel"
        :aria-labelledby="sessionState === 'guest' ? `ec-auth-title-${mode}` : undefined"
        :aria-describedby="sessionState === 'guest' ? `ec-auth-sub-${mode}` : undefined"
      >
        <div class="ec-auth-panel-inner">
          <RouterLink :to="homeTo" class="ec-auth-back">
            <AppIcon name="arrow-left" :size="15" aria-hidden="true" /> Volver a la tienda
          </RouterLink>

          <div v-if="sessionState === 'checking'" class="ec-auth-loading" role="status">
            <AppIcon name="loader" :size="24" class="ec-auth-spin" aria-hidden="true" />
            <p>Verificando tu sesión…</p>
          </div>

          <div v-else-if="sessionState === 'auth'" class="ec-auth-loading" role="status">
            <AppIcon name="loader" :size="24" class="ec-auth-spin" aria-hidden="true" />
            <p>Ya tenés sesión — te llevamos a tu destino…</p>
          </div>

          <template v-else>
            <header class="ec-auth-head">
              <span class="ec-auth-badge" aria-hidden="true">
                <AppIcon :name="mode === 'forgot' ? 'lock' : 'user'" :size="18" />
              </span>
              <span class="ec-auth-tag">{{ modeTag }}</span>
              <h2 :id="`ec-auth-title-${mode}`" class="ec-auth-title">{{ title }}</h2>
              <p :id="`ec-auth-sub-${mode}`" class="ec-auth-sub">{{ subtitle }}</p>
            </header>
            <StoreAuthForm :slug="slug" :mode="mode" @done="onAuthed" @mode="setMode" />
            <p class="ec-auth-trust">
              <AppIcon name="lock" :size="12" aria-hidden="true" />
              Conexión segura · no compartimos tus datos
            </p>
          </template>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
/* Ornamento editorial (ambiente, trama, sello, índice, línea de confianza):
   nace OCULTO para el resto de los diseños — la piel esencial lo enciende
   con más especificidad desde store-design-esencial-auth.css. */
.ec-auth-ambient,
.ec-auth-hatch,
.ec-auth-seal,
.ec-auth-index,
.ec-auth-trust { display: none; }

/* Envoltorio neutro: display:contents lo hace invisible para el layout de
   cualquier diseño (los hijos siguen siendo ítems directos del panel). */
.ec-auth-panel-inner { display: contents; }

/* ===== Base minimalista =====
   Tarjeta única centrada: una columna, una sola superficie, un solo CTA
   (el submit del formulario). Las hojas store-design-*-auth.css y
   store-design-*.css redefinen columnas/colores con más especificidad —
   esta base es el fallback profesional y el contrato de espaciado. */
.ec-auth-shell {
  flex: 1; width: min(470px, 100%);
  margin: clamp(16px, 4vw, 48px) auto clamp(48px, 7vw, 96px);
  display: grid; grid-template-columns: minmax(0, 1fr);
  border-radius: calc(var(--sp-radius, 16px) * 1.2);
  overflow: hidden;
  border: 1px solid var(--sp-line, rgba(127, 127, 127, .22));
  background: var(--sp-card-solid, var(--sp-card, #fff));
  color: var(--sp-ink, #0f172a);
  box-shadow: var(--sp-shadow-md, 0 18px 50px -18px rgba(15, 23, 42, .35));
}

/* ===== Cabecera de marca compacta =====
   En la base minimalista el panel de marca se reduce a una banda superior
   con logo + nombre de la tienda (identidad mínima, como el auth de un
   competidor). El copy editorial (.ec-auth-brand-copy: kicker/título/
   texto/índice/perks) y el pie (.ec-auth-brand-foot) nacen OCULTOS: las
   pieles que los usan los re-muestran declarando `display` con más
   especificidad (esencial, calzado, moda, etc.). */
.ec-auth-brand {
  position: relative; overflow: hidden;
  display: flex; flex-direction: column;
  padding: clamp(20px, 3vw, 36px);
  color: var(--sp-on-band, #fff);
  background:
    radial-gradient(120% 90% at 85% -10%, color-mix(in srgb, var(--store-accent, #4f46e5) 55%, transparent), transparent 60%),
    linear-gradient(155deg, color-mix(in srgb, var(--store-accent-ink, #111) 78%, #000) 0%, var(--store-accent-ink, #111) 100%);
}
/* Portada de la tienda (premium) bajo el velo de tinta: la imagen nunca
   baja el contraste del texto — el scrim ::after garantiza AA. */
.ec-auth-brand::before {
  content: ''; position: absolute; inset: 0; z-index: 0;
  background: var(--ec-cover, none) center / cover no-repeat;
}
.ec-auth-brand::after {
  content: ''; position: absolute; inset: 0; z-index: 0;
  background: linear-gradient(165deg, color-mix(in srgb, var(--store-accent-ink, #111) 30%, transparent), color-mix(in srgb, #000 62%, transparent));
}
.ec-auth-brand-inner {
  position: relative; z-index: 1;
  flex: 1; display: flex; flex-direction: column; justify-content: space-between;
  gap: clamp(22px, 3.5vw, 40px); min-height: 100%;
}
.ec-auth-brand-top {
  display: inline-flex; align-items: center; gap: 12px;
  width: fit-content; text-decoration: none; color: inherit;
}
.ec-auth-logo {
  display: grid; place-items: center; width: 44px; height: 44px;
  border-radius: 12px; overflow: hidden; flex: none;
  background: color-mix(in srgb, var(--sp-on-band, #fff) 16%, transparent);
  border: 1px solid color-mix(in srgb, var(--sp-on-band, #fff) 26%, transparent);
  font-weight: 800; font-size: 19px; letter-spacing: -.02em;
}
.ec-auth-logo img { width: 100%; height: 100%; object-fit: cover; }
.ec-auth-brand-name {
  font-family: var(--store-font, inherit);
  font-size: clamp(17px, 1.6vw, 21px); font-weight: 800; letter-spacing: -.01em;
  color: var(--sp-on-band, #fff);
}
.ec-auth-brand-copy { display: grid; gap: 14px; max-width: 46ch; }
.ec-auth-rail, .ec-auth-tag { display: none; }
.ec-auth-brand-kicker {
  margin: 0; font-size: 11.5px; font-weight: 700; letter-spacing: .1em;
  text-transform: uppercase; color: var(--sp-on-band-muted, color-mix(in srgb, var(--sp-on-band, #fff) 78%, transparent));
}
.ec-auth-brand-title {
  margin: 0; font-family: var(--store-font, inherit);
  font-size: clamp(26px, 3.2vw, 38px); font-weight: 800; line-height: 1.08; letter-spacing: -.02em;
  color: var(--sp-on-band, #fff);
}
.ec-auth-brand-text {
  margin: 0; font-size: clamp(13.5px, 1.15vw, 15px); line-height: 1.55;
  color: var(--sp-on-band-2, color-mix(in srgb, var(--sp-on-band, #fff) 88%, transparent));
}
.ec-auth-perks { list-style: none; margin: 4px 0 0; padding: 0; display: grid; gap: 10px; }
.ec-auth-perks li {
  display: flex; align-items: center; gap: 10px;
  font-size: 13px; font-weight: 600; line-height: 1.35;
  color: var(--sp-on-band, #fff);
}
.ec-auth-perks svg { flex: none; color: var(--sp-on-band-muted, color-mix(in srgb, var(--sp-on-band, #fff) 80%, transparent)); }
.ec-auth-brand-foot {
  margin: 0; font-size: 11.5px; letter-spacing: .04em;
  color: var(--sp-on-band-muted, color-mix(in srgb, var(--sp-on-band, #fff) 78%, transparent));
}
/* Copy editorial y pie de marca: OCULTOS en la base minimalista — la banda
   de marca se reduce a logo + nombre. Las pieles que los usan los
   re-muestran declarando `display` con más especificidad (esencial,
   calzado, moda, etc.). Los estilos de arriba quedan intactos para esas
   pieles y para cualquier hoja que encienda el copy sin redecorarlo. */
.ec-auth-brand-copy,
.ec-auth-brand-foot { display: none; }
.ec-auth-rail, .ec-auth-tag { display: none; }

/* ===== Panel del formulario ===== */
.ec-auth-panel {
  display: flex; flex-direction: column; min-width: 0;
  padding: clamp(22px, 5vw, 32px) clamp(20px, 5vw, 32px) clamp(24px, 5vw, 32px);
  background: var(--sp-card-solid, var(--sp-card, #fff));
  color: var(--sp-ink, #0f172a);
}
.ec-auth-back {
  display: inline-flex; align-items: center; gap: 7px; width: fit-content;
  margin-bottom: clamp(16px, 3vw, 24px);
  font-size: 12.5px; font-weight: 600; text-decoration: none;
  color: var(--sp-muted, #5b6678);
}
.ec-auth-back:hover { color: var(--sp-accent-text, var(--store-accent-ink, #111)); }
.ec-auth-back:focus-visible {
  outline: 2px solid var(--sp-accent-text, var(--store-accent-ink, #111));
  outline-offset: 3px; border-radius: 4px;
}
.ec-auth-head { display: grid; gap: 8px; margin-bottom: 20px; }
.ec-auth-badge {
  display: grid; place-items: center; width: 42px; height: 42px;
  border-radius: 12px; margin-bottom: 4px;
  background: color-mix(in srgb, var(--store-accent, #4f46e5) 13%, var(--sp-card-solid, #fff));
  color: var(--sp-accent-text, var(--store-accent-ink, #111));
}
.ec-auth-title {
  margin: 0; font-family: var(--store-font, inherit);
  font-size: clamp(21px, 2.4vw, 25px); font-weight: 800; letter-spacing: -.02em;
  color: var(--sp-ink, #0f172a);
}
.ec-auth-sub { margin: 0; font-size: 13.5px; line-height: 1.55; color: var(--sp-muted, #5b6678); }
.ec-auth-loading {
  flex: 1; display: grid; place-items: center; align-content: center; gap: 12px;
  min-height: 320px; color: var(--sp-muted, #5b6678); font-size: 14px;
}
.ec-auth-spin { animation: ec-auth-rotate 1s linear infinite; color: var(--sp-accent-text, var(--store-accent-ink, #111)); }
@keyframes ec-auth-rotate { to { transform: rotate(360deg); } }

/* ===== Breakpoints =====
   La base ya es una sola columna: los cortes solo ajustan aire y el
   encabezado de marca. Las hojas de diseño conservan sus propios
   breakpoints con más especificidad. */
@media (max-width: 720px) {
  .ec-auth-shell { margin-top: 8px; border-radius: calc(var(--sp-radius, 16px) * 1.1); }
  .ec-auth-brand { padding: 14px 18px; }
  .ec-auth-brand-name { font-size: 16px; }
  .ec-auth-logo { width: 38px; height: 38px; border-radius: 11px; font-size: 16px; }
  .ec-auth-panel { padding: 18px 16px 24px; }
  .ec-auth-head { margin-bottom: 16px; }
}
@media (max-width: 480px) {
  .ec-auth-shell { width: 100%; border-radius: 0; border-inline: 0; }
  .ec-auth-brand { border-bottom-width: 1px; }
}
@media (prefers-reduced-motion: reduce) {
  .ec-auth-spin { animation: none; }
}
</style>
