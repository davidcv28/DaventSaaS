<script setup>
// Cuenta del COMPRADOR: /<slug>/cuenta (+ sub-rutas /verificar y
// /restablecer que llegan por los mails de verificación y reset).
// Todo con sesión customer (NO la DAVENT del dueño). Sin sesión muestra
// un gate profesional que lleva al login/registro.
//
// Panel con sidebar en desktop (≥1024px) y header compacto + tabs con
// scroll en tablet/mobile. Tabs vía ?view=: pedidos | suscripciones |
// direcciones | soporte | perfil.
import { ref, computed, inject, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCustomerStore } from '../stores/customer.store.js'
import { useCartStore } from '../stores/cart.store.js'
import { customerApi } from '../api/customer.api.js'
import { customerOrdersApi } from '../api/storeorders.api.js'
import { membershipPlansApi } from '../api/membershipPlans.api.js'
import { extractApiError } from '../api/http.js'
import { storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import SupportPanel from '../components/ecommerce/SupportPanel.vue'
import AccountOrders from '../components/ecommerce/account/AccountOrders.vue'
import AccountSubscriptions from '../components/ecommerce/account/AccountSubscriptions.vue'
import AccountAddresses from '../components/ecommerce/account/AccountAddresses.vue'
import AccountProfile from '../components/ecommerce/account/AccountProfile.vue'
import '../assets/store-design-esencial-account.css'

const ctx = inject('storePage')
const slug = computed(() => ctx?.slug?.value || ctx?.slug || '')
const shopName = computed(() => ctx?.shopName?.value || ctx?.shopName || 'la tienda')

const route = useRoute()
const router = useRouter()
const customer = useCustomerStore()
const cart = useCartStore()

// Sub-vistas por path (los mails apuntan a /cuenta/verificar?token= y
// /cuenta/restablecer?uid=&token=).
const subView = computed(() => {
  const p = route.path.toLowerCase()
  if (p.endsWith('/verificar')) return 'verificar'
  if (p.endsWith('/restablecer')) return 'restablecer'
  return 'main'
})
const view = computed(() => {
  const v = String(route.query.view || 'pedidos')
  return ['pedidos', 'suscripciones', 'direcciones', 'soporte', 'perfil'].includes(v) ? v : 'pedidos'
})
const TABS = [
  { key: 'pedidos', label: 'Pedidos', icon: 'package' },
  { key: 'suscripciones', label: 'Suscripciones', icon: 'crown' },
  { key: 'direcciones', label: 'Direcciones', icon: 'map-pin' },
  { key: 'soporte', label: 'Soporte', icon: 'circle-help' },
  { key: 'perfil', label: 'Perfil', icon: 'user' },
]
function setView(v) { router.replace({ query: { ...route.query, view: v } }) }

const loginTo = computed(() => ({ path: storeHostSlug ? '/cuenta' : `/${slug.value}/cuenta` }))
const catalogoTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))

// Identidad para sidebar (desktop) y header compacto (mobile).
const displayFirst = computed(() => {
  const n = customer.displayName || ''
  if (n && !n.includes('@')) return n.split(/\s+/)[0]
  const email = customer.customer?.email || ''
  return email ? email.split('@')[0] : 'Cliente'
})
const initials = computed(() => {
  const src = (customer.displayName || customer.customer?.email || '').trim()
  if (!src) return '·'
  const clean = src.includes('@') ? src.split('@')[0] : src
  const parts = clean.split(/[\s._-]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return clean.slice(0, 2).toUpperCase()
})

// ---------- navegación: píldora deslizante ----------
// La píldora (.acc-tabs-ink) es un adorno de la piel "esencial": mide el tab
// activo y se desliza con transform. En el resto de los diseños está
// display:none, así que las medidas no afectan a nadie.
const navRef = ref(null)
const ink = ref({ x: 0, w: 0 })
let inkRo = null
function syncInk(scroll = false) {
  const nav = navRef.value
  if (!nav) return
  const on = nav.querySelector('.acc-tab.is-on')
  if (!on) return
  ink.value = { x: on.offsetLeft, w: on.offsetWidth }
  if (scroll) {
    const left = on.offsetLeft - (nav.clientWidth - on.offsetWidth) / 2
    if (Math.abs(nav.scrollLeft - left) > 2) {
      nav.scrollTo({ left: Math.max(0, left), behavior: 'smooth' })
    }
  }
}
const scheduleInk = (scroll = false) => nextTick(() => syncInk(scroll))

// ---------- telemetría real de la cabecera ----------
// Solo mostramos lo que ya está cargado: nunca inventamos métricas.
const statsChips = computed(() => {
  const out = []
  const n = orders.value.length
  if (n) out.push({ key: 'pedidos', icon: 'package', label: `${n} ${n === 1 ? 'pedido' : 'pedidos'}` })
  const sub = subData.value?.subscription
  if (sub?.is_vigente) out.push({ key: 'sub', icon: 'crown', label: sub.plan?.name || 'Suscripción activa' })
  const a = addresses.value.length
  if (a) out.push({ key: 'dir', icon: 'map-pin', label: `${a} ${a === 1 ? 'dirección' : 'direcciones'}` })
  return out
})

// ---------- auth gate ----------
const sessionChecked = ref(false)
async function ensureAuth() {
  const ok = await customer.ensureSession()
  sessionChecked.value = true
  if (!ok && subView.value === 'main') {
    // Gate visible con CTA — no auto-abrimos el modal para no
    // interrumpir la navegación del mail a /cuenta.
  }
  return ok
}
// La ruta 'store-auth' la crea el track de auth en paralelo: si ya
// existe navegamos a ella; si no, caemos al modal global (cart.store).
const hasAuthRoute = computed(() => router.hasRoute('store-auth'))
function openAuth() {
  if (hasAuthRoute.value) {
    // Tras el login volvemos a esta misma vista (query next).
    router.push({ name: 'store-auth', query: { mode: 'login', next: route.fullPath } })
    return
  }
  cart.openAuth('login', { route: { path: route.path, query: route.query } })
}

// ---------- VERIFICAR EMAIL ----------
const verifyState = ref('idle') // idle | busy | ok | error
const verifyMsg = ref('')
async function doVerify() {
  const token = String(route.query.token || '')
  if (!token) { verifyState.value = 'error'; verifyMsg.value = 'El enlace no trae el token de verificación.'; return }
  verifyState.value = 'busy'; verifyMsg.value = ''
  try {
    await customerApi.verifyEmail(token)
    verifyState.value = 'ok'
    verifyMsg.value = 'Tu correo quedó verificado. ¡Gracias!'
    customer.fetchMe().catch(() => {})
  } catch (err) {
    verifyState.value = 'error'
    verifyMsg.value = extractApiError(err).nonField || extractApiError(err).detail || 'El enlace es inválido o ya venció.'
  }
}
async function resendVerify() {
  try { await customerApi.resendVerification(); verifyMsg.value = 'Te reenviamos el correo de verificación.' }
  catch (err) { verifyMsg.value = extractApiError(err).nonField || 'No pudimos reenviar el correo.' }
}

// ---------- RESET PASSWORD ----------
const resetForm = ref({ password: '', confirm: '' })
const resetState = ref('idle') // idle | busy | ok | error
const resetMsg = ref('')
async function doReset() {
  const uid = String(route.query.uid || '')
  const token = String(route.query.token || '')
  if (!uid || !token) { resetState.value = 'error'; resetMsg.value = 'El enlace está incompleto.'; return }
  if (resetForm.value.password.length < 8) { resetState.value = 'error'; resetMsg.value = 'La contraseña necesita al menos 8 caracteres.'; return }
  if (resetForm.value.password !== resetForm.value.confirm) { resetState.value = 'error'; resetMsg.value = 'Las contraseñas no coinciden.'; return }
  resetState.value = 'busy'; resetMsg.value = ''
  try {
    await customerApi.confirmPasswordReset({ uid, token, new_password: resetForm.value.password, confirm_password: resetForm.value.confirm })
    resetState.value = 'ok'
    resetMsg.value = 'Tu contraseña se actualizó. Ya podés iniciar sesión con la clave nueva.'
  } catch (err) {
    resetState.value = 'error'
    resetMsg.value = extractApiError(err).nonField || extractApiError(err).detail || 'El enlace venció o la contraseña no es válida.'
  }
}

// ---------- PEDIDOS ----------
const orders = ref([])
const ordersLoading = ref(false)
const ordersError = ref('')
async function loadOrders() {
  ordersLoading.value = true; ordersError.value = ''
  try {
    const data = await customerOrdersApi.list({ store: slug.value })
    orders.value = data?.results || data || []
  } catch (err) {
    ordersError.value = extractApiError(err).nonField || 'No pudimos cargar tus pedidos.'
  } finally {
    ordersLoading.value = false
  }
}

// ---------- SUSCRIPCIONES ----------
const subData = ref(null)
const pubPayments = ref(null)   // config de cobro (viene del endpoint PÚBLICO de planes)
const subLoading = ref(false)
const subError = ref('')
const card = ref(null)
const cardOpen = ref(false)
const cardLoading = ref(false)
const cardError = ref('')

async function loadSubs() {
  subLoading.value = true; subError.value = ''
  try {
    const [mine, pub] = await Promise.all([
      membershipPlansApi.storePlans(slug.value),
      membershipPlansApi.publicPlans(slug.value).catch(() => null),
    ])
    subData.value = mine
    pubPayments.value = pub?.payments || null
    // Si la suscripción vigente tiene tarjeta digital, la pre-cargamos.
    if (subData.value?.subscription?.is_vigente && (subData.value.subscription.benefits || []).includes('digital_card')) {
      loadCard()
    }
  } catch (err) {
    subError.value = extractApiError(err).nonField || 'No pudimos cargar tus suscripciones.'
  } finally {
    subLoading.value = false
  }
}
function onSubscribed() { loadSubs() }
async function loadCard() {
  cardLoading.value = true; cardError.value = ''
  try {
    card.value = await membershipPlansApi.subscriptionCard(slug.value)
    cardOpen.value = true
  } catch (err) {
    cardError.value = extractApiError(err).nonField || 'Todavía no hay tarjeta disponible.'
  } finally {
    cardLoading.value = false
  }
}

// ---------- DIRECCIONES ----------
const addresses = ref([])
const addrLoading = ref(false)
const addrError = ref('')
async function loadAddresses() {
  addrLoading.value = true; addrError.value = ''
  try {
    const data = await customerApi.listAddresses()
    addresses.value = Array.isArray(data) ? data : (data?.results || [])
  } catch (err) {
    addrError.value = extractApiError(err).nonField || 'No pudimos cargar tus direcciones.'
  } finally {
    addrLoading.value = false
  }
}

// ---------- SOFE ----------
const supportRef = ref(null)
watch(() => route.query.order, (tok) => {
  if (view.value === 'soporte' && tok && supportRef.value) supportRef.value.prefill(String(tok))
}, { immediate: true })

async function logout() {
  await customer.logout()
  cart.onSessionExpired()
  cart.cart = null
  router.push(loginTo.value)
}

// ---------- orquestación ----------
watch([subView, view, sessionChecked], async ([sv, v, checked]) => {
  if (sv !== 'main' || !checked || !customer.isAuthenticated) return
  if (v === 'pedidos' && !orders.value.length && !ordersLoading.value) loadOrders()
  if (v === 'suscripciones' && !subData.value && !subLoading.value) loadSubs()
  if (v === 'direcciones' && !addresses.value.length && !addrLoading.value) loadAddresses()
  // perfil: AccountProfile se auto-carga al montar (v-if del tab).
})

onMounted(async () => {
  // verify-email es público (el token del mail ES la credencial) — no
  // hace falta sesión para confirmarlo.
  if (subView.value === 'verificar') { doVerify(); return }
  if (subView.value === 'restablecer') { sessionChecked.value = true; return }
  await ensureAuth()
  scheduleInk()
  if (typeof ResizeObserver !== 'undefined' && navRef.value) {
    inkRo = new ResizeObserver(() => syncInk())
    inkRo.observe(navRef.value)
  }
  // Las fuentes del diseño cambian el ancho de los tabs: re-medimos al cargar.
  document.fonts?.ready?.then(() => syncInk()).catch(() => {})
  // El watcher de [subView, view, sessionChecked] dispara la carga del
  // tab activo cuando sessionChecked pasa a true con sesión.
})
onBeforeUnmount(() => { inkRo?.disconnect(); inkRo = null })

// La píldora sigue al tab activo (y centra el tab en la tira scrolleable).
watch([view, subView, sessionChecked], () => scheduleInk(true))
</script>

<template>
  <div class="sp-page-root ec-account">
    <!-- ===== VERIFICAR EMAIL (link del mail) ===== -->
    <div v-if="subView === 'verificar'" class="acc-auth">
      <section class="acc-auth-card">
        <span class="acc-auth-ico" aria-hidden="true"><AppIcon name="mail" :size="26" /></span>
        <span class="acc-tele" aria-hidden="true">VERIFICACIÓN · {{ verifyState === 'ok' ? 'OK' : verifyState === 'error' ? 'ERROR' : 'EN CURSO' }}</span>
        <h1 class="acc-auth-title">Verificar tu correo</h1>
        <p v-if="verifyState === 'busy'" class="acc-auth-msg"><span class="acc-spin" aria-hidden="true"></span> Verificando tu correo…</p>
        <p v-else-if="verifyState === 'ok'" class="acc-auth-ok">{{ verifyMsg }}</p>
        <template v-else>
          <p class="acc-auth-msg">{{ verifyMsg || 'Estamos confirmando tu correo electrónico para activar tu cuenta.' }}</p>
          <div class="acc-auth-actions">
            <button v-if="customer.isAuthenticated" type="button" class="ec-btn-primary" @click="resendVerify">Reenviar correo</button>
            <RouterLink :to="loginTo" class="ec-btn-ghost">Ir a mi cuenta</RouterLink>
          </div>
        </template>
      </section>
    </div>

    <!-- ===== RESET PASSWORD (link del mail) ===== -->
    <div v-else-if="subView === 'restablecer'" class="acc-auth">
      <section class="acc-auth-card">
        <span class="acc-auth-ico" aria-hidden="true"><AppIcon name="lock" :size="26" /></span>
        <span class="acc-tele" aria-hidden="true">CLAVE · {{ resetState === 'ok' ? 'ACTUALIZADA' : 'RESTABLECER' }}</span>
        <h1 class="acc-auth-title">Restablecer contraseña</h1>
        <p v-if="resetState === 'ok'" class="acc-auth-ok">{{ resetMsg }}</p>
        <form v-else class="acc-auth-form" @submit.prevent="doReset">
          <label class="sp-field">
            <span class="sp-field-label">Nueva contraseña</span>
            <input v-model="resetForm.password" class="sp-input" type="password" autocomplete="new-password" minlength="8" required />
          </label>
          <label class="sp-field">
            <span class="sp-field-label">Repetí la contraseña</span>
            <input v-model="resetForm.confirm" class="sp-input" type="password" autocomplete="new-password" minlength="8" required />
          </label>
          <p v-if="resetState === 'error'" class="sp-form-error" role="alert">{{ resetMsg }}</p>
          <button type="submit" class="ec-btn-primary" :disabled="resetState === 'busy'">
            {{ resetState === 'busy' ? 'Guardando…' : 'Cambiar contraseña' }}
          </button>
        </form>
        <RouterLink :to="loginTo" class="acc-auth-link">Volver a ingresar</RouterLink>
      </section>
    </div>

    <!-- ===== CUENTA PRINCIPAL ===== -->
    <template v-else>
      <!-- Chequeo de sesión: skeleton del panel -->
      <div v-if="!sessionChecked" class="acc-skelpanel" aria-busy="true" aria-label="Cargando tu cuenta">
        <div class="acc-skel-id">
          <span class="acc-sk acc-sk-avatar"></span>
          <span class="acc-sk-lines"><span class="acc-sk acc-sk-l1"></span><span class="acc-sk acc-sk-l2"></span></span>
        </div>
        <span class="acc-sk acc-sk-tabs"></span>
        <span class="acc-sk acc-sk-panel"></span>
      </div>

      <!-- Gate de auth -->
      <section v-else-if="!customer.isAuthenticated" class="acc-gate">
        <div class="acc-gate-card">
          <span class="acc-kicker" aria-hidden="true">Tu cuenta · {{ shopName }}</span>
          <span class="acc-gate-ico" aria-hidden="true"><AppIcon name="user" :size="30" /></span>
          <div class="acc-gate-art" aria-hidden="true">
            <svg viewBox="0 0 240 150" role="presentation" focusable="false">
              <path class="a-line a-dash" d="M30 140h180" />
              <path class="a-line" d="M120 118c0-16-1-26-3-36" />
              <path class="a-leaf a-leaf--l" d="M117 84c-15-3-23-12-24-25 14 2 23 11 24 25Z" />
              <path class="a-leaf a-leaf--r" d="M123 78c13-3 20-12 20-24-12 2-19 11-20 24Z" />
              <path class="a-line" d="M106 118l3 20h22l3-20" />
              <path class="a-line" d="M102 118h36" />
              <circle class="a-dot" cx="120" cy="40" r="3" />
              <circle class="a-ring a-dash" cx="120" cy="40" r="11" />
            </svg>
          </div>
          <h1 class="acc-gate-title">Tu cuenta en {{ shopName }}</h1>
          <p class="acc-gate-sub">Ingresá o creá tu cuenta de comprador para tener todo en un solo lugar.</p>
          <ul class="acc-gate-list">
            <li><span class="acc-gate-num" aria-hidden="true">01</span><AppIcon name="package" :size="17" aria-hidden="true" /> Pedidos con seguimiento y comprobante</li>
            <li><span class="acc-gate-num" aria-hidden="true">02</span><AppIcon name="crown" :size="17" aria-hidden="true" /> Suscripciones y tarjeta de miembro</li>
            <li><span class="acc-gate-num" aria-hidden="true">03</span><AppIcon name="map-pin" :size="17" aria-hidden="true" /> Direcciones guardadas para el checkout</li>
            <li><span class="acc-gate-num" aria-hidden="true">04</span><AppIcon name="circle-help" :size="17" aria-hidden="true" /> Soporte directo con el comercio</li>
          </ul>
          <button type="button" class="ec-btn-primary acc-gate-cta" @click="openAuth">Ingresar o crear cuenta</button>
          <RouterLink :to="catalogoTo" class="acc-gate-link">Seguir mirando el catálogo</RouterLink>
        </div>
      </section>

      <!-- Panel con sesión -->
      <div v-else class="acc-shell">
        <!-- Sidebar (desktop ≥1024px) -->
        <aside class="acc-side">
          <div class="acc-id">
            <span class="acc-tele" aria-hidden="true">SESIÓN · ACTIVA</span>
            <span class="acc-avatar" aria-hidden="true">{{ initials }}</span>
            <div class="acc-id-meta">
              <strong class="acc-id-name">{{ customer.displayName || 'Mi cuenta' }}</strong>
              <small class="acc-id-email">{{ customer.customer?.email || '' }}</small>
            </div>
          </div>
          <nav class="acc-nav" aria-label="Secciones de tu cuenta">
            <button v-for="(t, i) in TABS" :key="t.key" type="button" class="acc-navitem" :class="{ 'is-on': view === t.key }" :aria-current="view === t.key ? 'page' : undefined" @click="setView(t.key)">
              <AppIcon :name="t.icon" :size="17" aria-hidden="true" />
              <span>{{ t.label }}</span>
              <span class="acc-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
            </button>
          </nav>
          <button type="button" class="acc-logout" @click="logout">
            <AppIcon name="logout" :size="16" aria-hidden="true" /> Cerrar sesión
          </button>
        </aside>

        <div class="acc-main">
          <!-- Header compacto (tablet/mobile) -->
          <header class="acc-mhead">
            <span class="acc-tele" aria-hidden="true">SESIÓN · ACTIVA</span>
            <span class="acc-avatar acc-avatar--sm" aria-hidden="true">{{ initials }}</span>
            <div class="acc-mhead-meta">
              <span class="acc-kicker" aria-hidden="true">Cuenta de comprador · {{ shopName }}</span>
              <h1 class="acc-greet">hola, <em>{{ displayFirst }}</em></h1>
              <strong>{{ displayFirst }}</strong>
              <small>{{ customer.customer?.email || '' }}</small>
              <ul v-if="statsChips.length" class="acc-stats">
                <li v-for="c in statsChips" :key="c.key" class="acc-stat">
                  <AppIcon :name="c.icon" :size="13" aria-hidden="true" />
                  <span>{{ c.label }}</span>
                </li>
              </ul>
            </div>
            <button type="button" class="acc-icon-btn" aria-label="Cerrar sesión" @click="logout">
              <AppIcon name="logout" :size="17" aria-hidden="true" />
              <span class="acc-icon-btn-txt" aria-hidden="true">Salir</span>
            </button>
          </header>

          <!-- Tabs horizontales con scroll (tablet/mobile) -->
          <nav ref="navRef" class="acc-tabs" role="tablist" aria-label="Secciones de tu cuenta">
            <span
              class="acc-tabs-ink"
              aria-hidden="true"
              :style="{ transform: `translateX(${ink.x}px)`, width: `${ink.w}px` }"
            ></span>
            <button v-for="(t, i) in TABS" :key="t.key" type="button" role="tab" :aria-selected="view === t.key" class="acc-tab" :class="{ 'is-on': view === t.key }" @click="setView(t.key)">
              <span class="acc-tab-ico" aria-hidden="true"><AppIcon :name="t.icon" :size="16" /></span>
              <span class="acc-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
              <span>{{ t.label }}</span>
            </button>
          </nav>

          <div :key="view" class="acc-body">
            <!-- PEDIDOS -->
            <AccountOrders
              v-if="view === 'pedidos'"
              :orders="orders"
              :loading="ordersLoading"
              :error="ordersError"
              :shop-name="shopName"
              @retry="loadOrders"
            />

            <!-- SUSCRIPCIONES -->
            <AccountSubscriptions
              v-else-if="view === 'suscripciones'"
              :slug="slug"
              :shop-name="shopName"
              :data="subData"
              :loading="subLoading"
              :error="subError"
              :payments="pubPayments"
              :card="card"
              :card-open="cardOpen"
              :card-loading="cardLoading"
              :card-error="cardError"
              @retry="loadSubs"
              @load-card="loadCard"
              @hide-card="cardOpen = false"
              @subscribed="onSubscribed"
            />

            <!-- DIRECCIONES -->
            <AccountAddresses
              v-else-if="view === 'direcciones'"
              :addresses="addresses"
              :loading="addrLoading"
              :error="addrError"
              @refresh="loadAddresses"
            />

            <!-- SOPORTE -->
            <section v-else-if="view === 'soporte'" class="acc-panel">
              <header class="acc-panel-head">
                <div class="acc-panel-headtxt">
                  <span class="acc-panel-kicker" aria-hidden="true">04 · Conversación</span>
                  <h2 class="acc-panel-title">Soporte</h2>
                  <p class="acc-panel-sub">Escribile a {{ shopName }} — podés relacionar el mensaje con un pedido.</p>
                </div>
              </header>
              <SupportPanel ref="supportRef" :slug="slug" />
            </section>

            <!-- PERFIL -->
            <AccountProfile v-else-if="view === 'perfil'" :email="customer.customer?.email || ''" />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.ec-account { display: grid; gap: 18px; min-width: 0; }

/* ---------- Nodos de la piel "esencial" ----------
   Quedan ocultos por defecto: sólo [data-design='esencial'] los enciende
   desde store-design-esencial-account.css. Otros diseños no los ven. */
.acc-kicker,
.acc-greet,
.acc-stats,
.acc-tab-ico,
.acc-tabs-ink,
.acc-icon-btn-txt,
.acc-gate-art,
.acc-gate-num,
.acc-panel-kicker { display: none; }
.acc-body { min-width: 0; }

/* ---------- Sub-vistas de mail (verificar / restablecer) ---------- */
.acc-auth { display: grid; place-items: center; padding: 20px 0 8px; }
.acc-auth-card { width: min(480px, 100%); display: grid; gap: 14px; justify-items: center; text-align: center; padding: 32px 26px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); box-shadow: var(--sp-shadow-md, none); }
.acc-auth-ico { display: grid; place-items: center; width: 60px; height: 60px; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 10%, transparent); color: var(--sp-accent-text, var(--store-accent, inherit)); }
.acc-auth-title { margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -.02em; }
.acc-auth-msg { display: flex; align-items: center; justify-content: center; gap: 10px; margin: 0; font-size: 14px; color: var(--sp-muted, inherit); }
.acc-auth-ok { margin: 0; font-size: 14.5px; font-weight: 700; color: var(--sp-success, #0E7A55); }
.acc-auth-form { width: 100%; display: grid; gap: 12px; text-align: left; }
.acc-auth-actions { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.acc-auth-link { font-size: 13px; font-weight: 700; color: var(--sp-accent-text, var(--store-accent, inherit)); }
.acc-spin { width: 16px; height: 16px; flex: none; border: 2px solid color-mix(in srgb, var(--sp-muted, #64748b) 30%, transparent); border-top-color: var(--sp-muted, #64748b); border-radius: 50%; animation: acc-rotate .8s linear infinite; }
@keyframes acc-rotate { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .acc-spin { animation-duration: 1.6s; } }

/* ---------- Skeleton de sesión ---------- */
.acc-skelpanel { display: grid; gap: 16px; padding: 20px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); }
.acc-skel-id { display: flex; align-items: center; gap: 12px; }
.acc-sk { display: block; border-radius: 8px; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.acc-sk-avatar { width: 52px; height: 52px; border-radius: 50%; flex: none; }
.acc-sk-lines { flex: 1; display: grid; gap: 8px; }
.acc-sk-l1 { width: 38%; height: 15px; }
.acc-sk-l2 { width: 62%; height: 11px; }
.acc-sk-tabs { height: 42px; border-radius: 999px; }
.acc-sk-panel { height: 220px; border-radius: calc(var(--sp-radius) * .75); }
@media (prefers-reduced-motion: no-preference) {
  .acc-skelpanel .acc-sk { animation: acc-panel-shimmer 1.4s ease-in-out infinite; }
  .acc-skelpanel .acc-sk-lines .acc-sk:nth-child(2) { animation-delay: .12s; }
  .acc-skelpanel .acc-sk-tabs { animation-delay: .2s; }
  .acc-skelpanel .acc-sk-panel { animation-delay: .28s; }
  @keyframes acc-panel-shimmer { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
}

/* ---------- Gate de auth ---------- */
.acc-gate { display: grid; place-items: center; padding: 26px 0; }
.acc-gate-card { width: min(560px, 100%); display: grid; justify-items: center; gap: 14px; text-align: center; padding: 36px 26px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); box-shadow: var(--sp-shadow-md, none); }
.acc-gate-ico { display: grid; place-items: center; width: 64px; height: 64px; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 10%, transparent); color: var(--sp-accent-text, var(--store-accent, inherit)); }
.acc-gate-title { margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -.02em; overflow-wrap: anywhere; }
.acc-gate-sub { margin: 0; max-width: 46ch; font-size: 14px; line-height: 1.55; color: var(--sp-muted, inherit); }
.acc-gate-list { list-style: none; margin: 4px 0 6px; padding: 14px 16px; width: 100%; max-width: 400px; display: grid; gap: 10px; text-align: left; border: 1px solid var(--sp-line, rgba(0,0,0,.08)); border-radius: calc(var(--sp-radius) * .75); background: var(--sp-surface, transparent); }
.acc-gate-list li { display: flex; align-items: center; gap: 10px; font-size: 13.5px; font-weight: 600; color: var(--sp-ink-2, inherit); }
.acc-gate-list svg { flex: none; color: var(--sp-accent-text, var(--store-accent, inherit)); }
.acc-gate-cta { min-width: 230px; }
.acc-gate-link { font-size: 13px; font-weight: 700; color: var(--sp-accent-text, var(--store-accent, inherit)); }

/* ---------- Panel (sidebar + contenido) ---------- */
.acc-shell { display: grid; gap: 18px; min-width: 0; }
.acc-side { display: none; }
.acc-main { display: grid; gap: 14px; min-width: 0; }

.acc-avatar { display: grid; place-items: center; width: 52px; height: 52px; flex: none; border-radius: 50%; background: linear-gradient(135deg, var(--store-accent, #111), var(--store-accent-ink, #111)); color: var(--sp-on-band, #fff); font-weight: 800; font-size: 17px; letter-spacing: .02em; }
.acc-avatar--sm { width: 42px; height: 42px; font-size: 14px; }

.acc-mhead { display: flex; align-items: center; gap: 12px; min-width: 0; }
.acc-mhead-meta { display: grid; gap: 1px; min-width: 0; flex: 1; }
.acc-mhead-meta strong { font-size: 15px; font-weight: 800; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.acc-mhead-meta small { font-size: 12px; color: var(--sp-muted, inherit); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.acc-icon-btn { display: grid; place-items: center; width: 40px; height: 40px; flex: none; border: 1px solid var(--sp-line, currentColor); border-radius: 10px; background: var(--sp-card, transparent); color: var(--sp-ink-2, inherit); cursor: pointer; }
.acc-icon-btn:hover { border-color: var(--store-accent, #111); color: var(--sp-accent-text, var(--store-accent, inherit)); }

.acc-tabs { display: flex; gap: 8px; overflow-x: auto; padding: 2px 2px 8px; scrollbar-width: none; -webkit-overflow-scrolling: touch; }
.acc-tabs::-webkit-scrollbar { display: none; }
.acc-tab { flex: none; display: inline-flex; align-items: center; gap: 7px; padding: 9px 15px; border: 1px solid var(--sp-line, currentColor); border-radius: 999px; background: var(--sp-card, transparent); color: var(--sp-ink-2, inherit); font: inherit; font-size: 13px; font-weight: 700; cursor: pointer; white-space: nowrap; }
.acc-tab:hover { border-color: var(--store-accent, #111); color: var(--sp-accent-text, var(--store-accent, inherit)); }
.acc-tab.is-on { background: color-mix(in srgb, var(--store-accent, #111) 12%, transparent); border-color: color-mix(in srgb, var(--store-accent, #111) 40%, transparent); color: var(--sp-accent-text, var(--store-accent, inherit)); }

@media (min-width: 1024px) {
  .acc-shell { grid-template-columns: 292px minmax(0, 1fr); gap: 22px; align-items: start; }
  .acc-side { display: grid; gap: 14px; align-content: start; position: sticky; top: 92px; padding: 18px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); box-shadow: var(--sp-shadow-sm, none); }
  .acc-mhead, .acc-tabs { display: none; }
  .acc-id { display: flex; align-items: center; gap: 12px; min-width: 0; padding-bottom: 14px; border-bottom: 1px solid var(--sp-line, rgba(0,0,0,.09)); }
  .acc-id-meta { display: grid; gap: 2px; min-width: 0; }
  .acc-id-name { font-size: 15px; font-weight: 800; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .acc-id-email { font-size: 12px; color: var(--sp-muted, inherit); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .acc-nav { display: grid; gap: 4px; }
  .acc-navitem { display: flex; align-items: center; gap: 11px; width: 100%; padding: 11px 13px; border: none; border-radius: 11px; background: transparent; color: var(--sp-ink-2, inherit); font: inherit; font-size: 14px; font-weight: 600; cursor: pointer; text-align: left; }
  .acc-navitem svg { flex: none; }
  .acc-navitem:hover { background: color-mix(in srgb, var(--sp-ink, #0f172a) 6%, transparent); color: var(--sp-ink, inherit); }
  .acc-navitem.is-on { background: color-mix(in srgb, var(--store-accent, #111) 12%, transparent); color: var(--sp-accent-text, var(--store-accent, inherit)); font-weight: 700; }
  .acc-logout { display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; padding: 11px; border: 1px solid var(--sp-line, currentColor); border-radius: 11px; background: transparent; color: var(--sp-muted, inherit); font: inherit; font-size: 13.5px; font-weight: 600; cursor: pointer; }
  .acc-logout:hover { color: var(--sp-danger, #dc2626); border-color: color-mix(in srgb, var(--sp-danger, #dc2626) 40%, transparent); background: color-mix(in srgb, var(--sp-danger, #dc2626) 7%, transparent); }
}

/* Panel compartido (soporte) */
.acc-panel { display: grid; gap: 16px; padding: 20px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); box-shadow: var(--sp-shadow-sm, none); }
.acc-panel-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.acc-panel-headtxt { display: grid; gap: 3px; min-width: 0; }
.acc-panel-title { margin: 0; font-size: 18px; font-weight: 800; letter-spacing: -.01em; }
.acc-panel-sub { margin: 0; font-size: 13px; color: var(--sp-muted, inherit); overflow-wrap: anywhere; }

.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 12px 18px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: var(--sp-on-band, #fff); font-size: 14px; font-weight: 700; cursor: pointer; text-decoration: none; }
.ec-btn-primary:hover { filter: brightness(1.06); }
.ec-btn-primary:disabled { opacity: .55; cursor: default; }
.ec-btn-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 10px 14px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .7); background: transparent; color: inherit; font-size: 13px; font-weight: 600; cursor: pointer; text-decoration: none; }

.acc-auth-card :focus-visible, .acc-gate-card :focus-visible, .acc-side :focus-visible, .acc-mhead :focus-visible, .acc-tabs :focus-visible, .acc-panel :focus-visible, .ec-btn-primary:focus-visible, .ec-btn-ghost:focus-visible, .acc-icon-btn:focus-visible {
  outline: 2px solid var(--store-accent, #111); outline-offset: 2px;
}
@media (max-width: 560px) {
  .acc-gate-card { padding: 28px 18px; }
  .acc-gate-title { font-size: 21px; }
  .acc-auth-card { padding: 26px 18px; }
}
</style>
