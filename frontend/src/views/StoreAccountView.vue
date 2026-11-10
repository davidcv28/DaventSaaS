<script setup>
// Cuenta del COMPRADOR: /<slug>/cuenta (+ sub-rutas /verificar y
// /restablecer que llegan por los mails de verificación y reset).
// Todo con sesión customer (NO la DAVENT del dueño). Sin sesión muestra
// el prompt de auth — el modal global (cart.store) hace el login.
//
// Tabs vía ?view=: pedidos | suscripciones | direcciones | soporte | perfil.
import { ref, computed, inject, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useCustomerStore } from '../stores/customer.store.js'
import { useCartStore } from '../stores/cart.store.js'
import { customerApi } from '../api/customer.api.js'
import { customerOrdersApi } from '../api/storeorders.api.js'
import { membershipPlansApi } from '../api/membershipPlans.api.js'
import { formatARS } from '../api/billing.api.js'
import { extractApiError } from '../api/http.js'
import { storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'
import SupportPanel from '../components/ecommerce/SupportPanel.vue'
import PlanSubscribe from '../components/ecommerce/PlanSubscribe.vue'

const ctx = inject('storePage')
const slug = computed(() => ctx?.slug?.value || ctx?.slug || '')
const shopName = computed(() => ctx?.shopName?.value || ctx?.shopName || 'la tienda')

const route = useRoute()
const router = useRouter()
const customer = useCustomerStore()
const cart = useCartStore()

const money = (v) => (Number(v) > 0 ? formatARS(v, 2) : '$ 0,00')
const fmtDate = (iso) => iso ? new Date(iso).toLocaleDateString('es-AR', { day: 'numeric', month: 'long', year: 'numeric' }) : ''

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
  { key: 'pedidos', label: 'Mis pedidos' },
  { key: 'suscripciones', label: 'Suscripciones' },
  { key: 'direcciones', label: 'Direcciones' },
  { key: 'soporte', label: 'Soporte' },
  { key: 'perfil', label: 'Mi perfil' },
]
function setView(v) { router.replace({ query: { ...route.query, view: v } }) }

const seguimientoTo = (token) => ({
  path: storeHostSlug ? '/seguimiento' : `/${slug.value}/seguimiento`,
  query: { token }
})
const loginTo = computed(() => ({ path: storeHostSlug ? '/cuenta' : `/${slug.value}/cuenta` }))

// ---------- auth gate ----------
const sessionChecked = ref(false)
async function ensureAuth() {
  const ok = await customer.ensureSession()
  sessionChecked.value = true
  if (!ok && subView.value === 'main') {
    // Prompt visible + el modal se puede abrir con un toque (no auto-abrir
    // para no interrumpir la navegación del mail a /cuenta).
  }
  return ok
}
function openAuth() {
  // Tras el login volvemos a esta misma vista (ya con sesión).
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
const STATUS_LABELS = {
  PENDING_PAYMENT: 'Pendiente de pago', PAID: 'Pagado', PACKING: 'Preparando',
  SHIPPED: 'Enviado', DELIVERED: 'Entregado', EXPIRED: 'Vencido',
  CANCELLED: 'Cancelado', REFUNDED: 'Reembolsado',
}
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
const BENEFIT_LABELS = {
  digital_card: 'Tarjeta digital', free_shipping: 'Envío gratis',
  exclusive_discounts: 'Descuentos exclusivos', exclusive_access: 'Acceso exclusivo',
}
const benefitLabel = (c) => BENEFIT_LABELS[c] || c
const subStatusLabel = { pending: 'Pago pendiente', active: 'Activa', cancelled: 'Cancelada', expired: 'Vencida' }

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
const addrForm = ref(null)   // null = lista; objeto = editando/creando
const addrSaving = ref(false)
const emptyAddr = () => ({ id: null, label: '', line1: '', line2: '', city: '', province: '', postal_code: '', country: 'AR', is_default: false })
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
function editAddress(a) { addrForm.value = a ? { ...a } : emptyAddr() }
async function saveAddress() {
  if (addrSaving.value || !addrForm.value) return
  addrSaving.value = true; addrError.value = ''
  const f = addrForm.value
  try {
    if (f.id) await customerApi.updateAddress(f.id, f)
    else await customerApi.createAddress(f)
    addrForm.value = null
    await loadAddresses()
  } catch (err) {
    const parsed = extractApiError(err)
    addrError.value = parsed.nonField || parsed.line1 || parsed.city || parsed.province || 'Revisá los datos de la dirección.'
  } finally {
    addrSaving.value = false
  }
}
async function removeAddress(a) {
  try { await customerApi.deleteAddress(a.id); await loadAddresses() }
  catch (err) { addrError.value = extractApiError(err).nonField || 'No pudimos eliminar la dirección.' }
}

// ---------- PERFIL ----------
const profile = ref({ first_name: '', last_name: '', phone: '', document_type: '', document: '' })
const profileSaving = ref(false)
const profileMsg = ref('')
async function loadProfile() {
  try {
    const data = await customerApi.getProfile()
    const c = data?.customer || data || {}
    profile.value = {
      first_name: c.first_name || '', last_name: c.last_name || '',
      phone: c.phone || '', document_type: c.document_type || '', document: c.document || '',
    }
  } catch { /* perfil opcional */ }
}
async function saveProfile() {
  profileSaving.value = true; profileMsg.value = ''
  try {
    await customerApi.updateProfile({ ...profile.value })
    customer.fetchMe().catch(() => {})
    profileMsg.value = 'Perfil actualizado.'
  } catch (err) {
    profileMsg.value = extractApiError(err).nonField || 'No pudimos guardar los cambios.'
  } finally {
    profileSaving.value = false
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
  if (v === 'perfil') loadProfile()
})

onMounted(async () => {
  // verify-email es público (el token del mail ES la credencial) — no
  // hace falta sesión para confirmarlo.
  if (subView.value === 'verificar') { doVerify(); return }
  if (subView.value === 'restablecer') { sessionChecked.value = true; return }
  await ensureAuth()
  // El watcher de [subView, view, sessionChecked] dispara la carga del
  // tab activo cuando sessionChecked pasa a true con sesión.
})
</script>

<template>
  <div class="sp-page-root ec-account">
    <!-- ===== VERIFICAR EMAIL (link del mail) ===== -->
    <section v-if="subView === 'verificar'" class="ec-acc-card">
      <h1 class="ec-acc-title">Verificar tu correo</h1>
      <p v-if="verifyState === 'busy'" class="ec-acc-muted">Verificando…</p>
      <p v-else-if="verifyState === 'ok'" class="ec-acc-ok">{{ verifyMsg }}</p>
      <template v-else>
        <p class="ec-acc-muted">{{ verifyMsg || 'Estamos confirmando tu correo electrónico.' }}</p>
        <div class="ec-acc-actions">
          <button v-if="customer.isAuthenticated" type="button" class="ec-btn-primary" @click="resendVerify">Reenviar correo</button>
          <RouterLink :to="loginTo" class="ec-btn-ghost">Ir a mi cuenta</RouterLink>
        </div>
      </template>
    </section>

    <!-- ===== RESET PASSWORD (link del mail) ===== -->
    <section v-else-if="subView === 'restablecer'" class="ec-acc-card">
      <h1 class="ec-acc-title">Restablecer contraseña</h1>
      <p v-if="resetState === 'ok'" class="ec-acc-ok">{{ resetMsg }}</p>
      <form v-else class="ec-acc-form" @submit.prevent="doReset">
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
      <RouterLink :to="loginTo" class="ec-acc-link">Volver a ingresar</RouterLink>
    </section>

    <!-- ===== CUENTA PRINCIPAL ===== -->
    <template v-else>
      <header class="ec-acc-head">
        <div>
          <h1 class="ec-acc-title">Hola{{ customer.displayName ? `, ${customer.displayName.split(' ')[0]}` : '' }}</h1>
          <p class="ec-acc-sub">{{ customer.customer?.email || '' }} · tu cuenta en {{ shopName }}</p>
        </div>
        <button v-if="customer.isAuthenticated" type="button" class="ec-btn-ghost" @click="logout">
          <AppIcon name="logout" :size="15" aria-hidden="true" /> Salir
        </button>
      </header>

      <!-- Sin sesión -->
      <div v-if="!sessionChecked" class="ec-acc-card">Cargando tu cuenta…</div>
      <div v-else-if="!customer.isAuthenticated" class="ec-acc-card">
        <h2 class="ec-acc-h2">Ingresá para ver tu cuenta</h2>
        <p class="ec-acc-muted">Pedidos, suscripciones, direcciones y soporte de {{ shopName }} en un solo lugar.</p>
        <button type="button" class="ec-btn-primary" @click="openAuth">Ingresar o crear cuenta</button>
      </div>

      <template v-else>
        <nav class="ec-acc-tabs" role="tablist">
          <button v-for="t in TABS" :key="t.key" type="button" role="tab" :aria-selected="view === t.key" class="ec-acc-tab" :class="{ 'is-on': view === t.key }" @click="setView(t.key)">
            {{ t.label }}
          </button>
        </nav>

        <!-- PEDIDOS -->
        <section v-if="view === 'pedidos'" class="ec-acc-card">
          <h2 class="ec-acc-h2">Mis pedidos en {{ shopName }}</h2>
          <p v-if="ordersLoading" class="ec-acc-muted">Cargando…</p>
          <p v-else-if="ordersError" class="sp-form-error" role="alert">{{ ordersError }}</p>
          <div v-else-if="!orders.length" class="ec-acc-empty">
            <AppIcon name="package" :size="26" aria-hidden="true" />
            <p>Todavía no hiciste pedidos en esta tienda.</p>
          </div>
          <ul v-else class="ec-orders">
            <li v-for="o in orders" :key="o.tracking_token || o.id" class="ec-order">
              <div class="ec-order-main">
                <strong>{{ o.code || `#${o.id}` }}</strong>
                <small>{{ fmtDate(o.created_at) }} · {{ o.items_count ?? o.items?.length ?? '' }} {{ (o.items_count ?? o.items?.length ?? 0) === 1 ? 'producto' : 'productos' }}</small>
              </div>
              <span class="ec-order-status" :class="`is-${(o.status || '').toLowerCase()}`">{{ STATUS_LABELS[o.status] || o.status }}</span>
              <strong class="ec-order-total">{{ money(o.total) }}</strong>
              <RouterLink :to="seguimientoTo(o.tracking_token)" class="ec-order-link">Seguir</RouterLink>
            </li>
          </ul>
        </section>

        <!-- SUSCRIPCIONES -->
        <section v-if="view === 'suscripciones'" class="ec-acc-card">
          <h2 class="ec-acc-h2">Mis suscripciones</h2>
          <p v-if="subLoading" class="ec-acc-muted">Cargando…</p>
          <p v-else-if="subError" class="sp-form-error" role="alert">{{ subError }}</p>
          <template v-else-if="subData">
            <div v-if="subData.subscription" class="ec-sub-card">
              <div class="ec-sub-card-info">
                <strong>{{ subData.subscription.plan?.name || 'Plan de miembro' }}</strong>
                <small>{{ subData.store?.name || shopName }}</small>
                <span class="ec-order-status" :class="subData.subscription.is_vigente ? 'is-active' : 'is-pending'">
                  {{ subData.subscription.is_vigente ? 'Activa' : (subStatusLabel[subData.subscription.status] || subData.subscription.status) }}
                </span>
                <small v-if="subData.subscription.vigente_hasta">Vigente hasta el {{ fmtDate(subData.subscription.vigente_hasta) }}</small>
              </div>
              <button v-if="cardOpen && card" type="button" class="ec-btn-ghost" @click="cardOpen = false">Ocultar tarjeta</button>
              <button v-else type="button" class="ec-btn-primary" :disabled="cardLoading" @click="loadCard">
                {{ cardLoading ? 'Cargando…' : 'Ver mi tarjeta' }}
              </button>
            </div>
            <p v-if="cardError" class="sp-form-error" role="alert">{{ cardError }}</p>

            <!-- Tarjeta digital visual -->
            <div v-if="cardOpen && card" class="ec-member-card">
              <div class="ec-member-card-top">
                <span class="ec-member-card-store">{{ card.store_name || shopName }}</span>
                <span class="ec-member-card-plan">{{ card.plan_name }}</span>
              </div>
              <div class="ec-member-card-bottom">
                <div>
                  <small>Miembro</small>
                  <strong>{{ card.member_name }}</strong>
                </div>
                <div v-if="card.vigente_hasta">
                  <small>Vigente hasta</small>
                  <strong>{{ fmtDate(card.vigente_hasta) }}</strong>
                </div>
              </div>
              <ul v-if="card.benefits?.length" class="ec-member-benefits">
                <li v-for="b in card.benefits" :key="b">{{ benefitLabel(b) }}</li>
              </ul>
            </div>

            <div v-if="subData.plans?.length" class="ec-sub-plans">
              <h3 class="ec-acc-h3">Planes disponibles</h3>
              <ul class="ec-plans">
                <li v-for="p in subData.plans" :key="p.id" class="ec-plan">
                  <div class="ec-plan-info">
                    <strong>{{ p.name }}</strong>
                    <small>{{ money(p.price) }}<template v-if="p.period_days"> / {{ p.period_days }} días</template></small>
                    <ul v-if="p.benefits?.length" class="ec-plan-benefits">
                      <li v-for="b in p.benefits" :key="b">{{ benefitLabel(b) }}</li>
                      <li v-if="p.discount_percent">{{ p.discount_percent }}% de descuento</li>
                    </ul>
                  </div>
                  <PlanSubscribe :slug="slug" :plan="p" :payments="pubPayments" @subscribed="onSubscribed" />
                </li>
              </ul>
            </div>
            <p v-else class="ec-acc-muted">Esta tienda no tiene planes de suscripción activos.</p>
          </template>
        </section>

        <!-- DIRECCIONES -->
        <section v-if="view === 'direcciones'" class="ec-acc-card">
          <div class="ec-acc-row">
            <h2 class="ec-acc-h2">Mis direcciones</h2>
            <button v-if="!addrForm" type="button" class="ec-btn-ghost" @click="editAddress(null)">+ Nueva</button>
          </div>
          <p v-if="addrLoading" class="ec-acc-muted">Cargando…</p>
          <p v-else-if="addrError" class="sp-form-error" role="alert">{{ addrError }}</p>

          <form v-if="addrForm" class="ec-addrform" @submit.prevent="saveAddress">
            <div class="ec-co-grid2">
              <label class="sp-field"><span class="sp-field-label">Etiqueta</span><input v-model="addrForm.label" class="sp-input" type="text" maxlength="40" placeholder="Casa, Oficina…" /></label>
              <label class="sp-field"><span class="sp-field-label">País</span><input v-model="addrForm.country" class="sp-input" type="text" maxlength="2" /></label>
            </div>
            <label class="sp-field"><span class="sp-field-label">Calle y número *</span><input v-model="addrForm.line1" class="sp-input" type="text" maxlength="160" required /></label>
            <label class="sp-field"><span class="sp-field-label">Depto / piso / referencia</span><input v-model="addrForm.line2" class="sp-input" type="text" maxlength="160" /></label>
            <div class="ec-co-grid2">
              <label class="sp-field"><span class="sp-field-label">Ciudad *</span><input v-model="addrForm.city" class="sp-input" type="text" maxlength="120" required /></label>
              <label class="sp-field"><span class="sp-field-label">Provincia *</span><input v-model="addrForm.province" class="sp-input" type="text" maxlength="120" required /></label>
            </div>
            <label class="sp-field"><span class="sp-field-label">Código postal</span><input v-model="addrForm.postal_code" class="sp-input" type="text" maxlength="20" /></label>
            <label class="ec-acc-check"><input v-model="addrForm.is_default" type="checkbox" /> Usar como dirección principal</label>
            <div class="ec-acc-actions">
              <button type="submit" class="ec-btn-primary" :disabled="addrSaving">{{ addrSaving ? 'Guardando…' : 'Guardar' }}</button>
              <button type="button" class="ec-btn-ghost" @click="addrForm = null">Cancelar</button>
            </div>
          </form>

          <ul v-else-if="addresses.length" class="ec-addrs">
            <li v-for="a in addresses" :key="a.id" class="ec-addr">
              <div>
                <strong>{{ a.label || 'Dirección' }}{{ a.is_default ? ' · principal' : '' }}</strong>
                <small>{{ [a.line1, a.line2, a.city, a.province, a.postal_code].filter(Boolean).join(', ') }}</small>
              </div>
              <div class="ec-addr-actions">
                <button type="button" class="ec-addr-btn" @click="editAddress(a)">Editar</button>
                <button type="button" class="ec-addr-btn is-danger" @click="removeAddress(a)">Eliminar</button>
              </div>
            </li>
          </ul>
          <p v-else class="ec-acc-muted">No cargaste direcciones todavía.</p>
        </section>

        <!-- SOPORTE -->
        <section v-if="view === 'soporte'" class="ec-acc-card">
          <h2 class="ec-acc-h2">Soporte con {{ shopName }}</h2>
          <SupportPanel ref="supportRef" :slug="slug" />
        </section>

        <!-- PERFIL -->
        <section v-if="view === 'perfil'" class="ec-acc-card">
          <h2 class="ec-acc-h2">Mi perfil</h2>
          <form class="ec-acc-form" @submit.prevent="saveProfile">
            <div class="ec-co-grid2">
              <label class="sp-field"><span class="sp-field-label">Nombre</span><input v-model="profile.first_name" class="sp-input" type="text" maxlength="150" /></label>
              <label class="sp-field"><span class="sp-field-label">Apellido</span><input v-model="profile.last_name" class="sp-input" type="text" maxlength="150" /></label>
            </div>
            <label class="sp-field"><span class="sp-field-label">Email</span><input class="sp-input" type="email" :value="customer.customer?.email" disabled /><small class="ec-acc-hint">El email no se cambia desde acá — escribinos si necesitás actualizarlo.</small></label>
            <label class="sp-field"><span class="sp-field-label">Teléfono</span><input v-model="profile.phone" class="sp-input" type="tel" maxlength="24" /></label>
            <div class="ec-co-grid2">
              <label class="sp-field"><span class="sp-field-label">Tipo de documento</span>
                <select v-model="profile.document_type" class="sp-input">
                  <option value="">—</option><option value="DNI">DNI</option><option value="CUIT">CUIT / CUIL</option>
                </select>
              </label>
              <label class="sp-field"><span class="sp-field-label">Número</span><input v-model="profile.document" class="sp-input" type="text" maxlength="11" /></label>
            </div>
            <p v-if="profileMsg" class="ec-acc-muted">{{ profileMsg }}</p>
            <button type="submit" class="ec-btn-primary" :disabled="profileSaving">{{ profileSaving ? 'Guardando…' : 'Guardar cambios' }}</button>
          </form>
        </section>
      </template>
    </template>
  </div>
</template>

<style scoped>
.ec-account { display: grid; gap: 16px; }
.ec-acc-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.ec-acc-title { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -.02em; }
.ec-acc-sub { margin: 4px 0 0; font-size: 13.5px; color: var(--sp-muted, inherit); }
.ec-acc-h2 { margin: 0 0 12px; font-size: 16px; font-weight: 800; }
.ec-acc-h3 { margin: 18px 0 10px; font-size: 14px; font-weight: 800; }
.ec-acc-card { display: grid; gap: 12px; padding: 18px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: 16px; background: var(--sp-card, transparent); }
.ec-acc-muted { margin: 0; font-size: 13px; line-height: 1.5; color: var(--sp-muted, inherit); }
.ec-acc-ok { margin: 0; font-size: 14px; font-weight: 600; color: #16a34a; }
.ec-acc-hint { font-size: 11.5px; color: var(--sp-muted, inherit); }
.ec-acc-form { display: grid; gap: 12px; }
.ec-acc-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.ec-acc-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.ec-acc-check { display: flex; align-items: center; gap: 9px; font-size: 13.5px; }
.ec-acc-tabs { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 2px; }
.ec-acc-tab { flex: none; padding: 9px 14px; border: 1px solid var(--sp-line, rgba(0,0,0,.12)); border-radius: 999px; background: transparent; color: inherit; font-size: 13px; font-weight: 600; cursor: pointer; }
.ec-acc-tab.is-on { background: var(--store-accent, #111); border-color: var(--store-accent, #111); color: var(--store-accent-ink, #fff); }
.ec-acc-empty { display: grid; place-items: center; gap: 8px; padding: 26px 10px; text-align: center; color: var(--sp-muted, inherit); font-size: 13.5px; }
.ec-orders { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.ec-order { display: grid; grid-template-columns: 1fr auto auto auto; align-items: center; gap: 12px; padding: 12px 14px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: 12px; }
.ec-order-main { display: grid; gap: 2px; min-width: 0; }
.ec-order-main small { font-size: 12px; color: var(--sp-muted, inherit); }
.ec-order-status { font-size: 11.5px; font-weight: 700; padding: 4px 10px; border-radius: 999px; background: color-mix(in srgb, #6b7280 14%, transparent); white-space: nowrap; }
.ec-order-status.is-pending_payment, .ec-order-status.is-pending { background: color-mix(in srgb, #d97706 15%, transparent); color: #b45309; }
.ec-order-status.is-delivered, .ec-order-status.is-active { background: color-mix(in srgb, #16a34a 14%, transparent); color: #16a34a; }
.ec-order-status.is-cancelled, .ec-order-status.is-expired, .ec-order-status.is-refunded { background: color-mix(in srgb, #dc2626 12%, transparent); color: #b91c1c; }
.ec-order-total { font-size: 14px; font-variant-numeric: tabular-nums; }
.ec-order-link { font-size: 13px; font-weight: 700; color: var(--store-accent, inherit); text-decoration: none; }
.ec-sub-card { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px; border: 1px solid var(--sp-line, rgba(0,0,0,.12)); border-radius: 14px; flex-wrap: wrap; }
.ec-sub-card-info { display: grid; gap: 3px; }
.ec-sub-card-info small { color: var(--sp-muted, inherit); }
.ec-member-card { display: grid; gap: 14px; padding: 18px; border-radius: 16px; background: linear-gradient(135deg, var(--store-accent, #111), color-mix(in srgb, var(--store-accent, #111) 70%, #fff)); color: var(--store-accent-ink, #fff); }
.ec-member-card-top { display: flex; justify-content: space-between; gap: 10px; }
.ec-member-card-store { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; opacity: .8; }
.ec-member-card-plan { font-size: 15px; font-weight: 800; }
.ec-member-card-bottom { display: flex; justify-content: space-between; gap: 12px; }
.ec-member-card-bottom small { display: block; font-size: 10.5px; text-transform: uppercase; letter-spacing: .06em; opacity: .75; }
.ec-member-card-bottom strong { font-size: 15px; }
.ec-member-benefits { margin: 0; padding-left: 18px; display: grid; gap: 4px; font-size: 12.5px; opacity: .9; }
.ec-sub-plans { display: grid; gap: 10px; }
.ec-plans { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.ec-plan { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 13px 15px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: 13px; flex-wrap: wrap; }
.ec-plan-info { display: grid; gap: 4px; }
.ec-plan-benefits { margin: 2px 0 0; padding-left: 16px; font-size: 12px; color: var(--sp-muted, inherit); display: grid; gap: 2px; }
.ec-addrs { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.ec-addr { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 14px; border: 1px solid var(--sp-line, rgba(0,0,0,.1)); border-radius: 12px; }
.ec-addr small { display: block; font-size: 12px; color: var(--sp-muted, inherit); }
.ec-addr-actions { display: flex; gap: 6px; }
.ec-addr-btn { border: none; background: none; font-size: 12.5px; font-weight: 700; color: var(--store-accent, inherit); cursor: pointer; padding: 6px 8px; }
.ec-addr-btn.is-danger { color: #b91c1c; }
.ec-addrform { display: grid; gap: 12px; }
.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 16px; border: none; border-radius: 12px; background: var(--store-accent, #111); color: var(--store-accent-ink, #fff); font-size: 14px; font-weight: 700; cursor: pointer; text-decoration: none; }
.ec-btn-primary:disabled { opacity: .55; cursor: default; }
.ec-btn-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 16px; border: 1px solid var(--sp-line, currentColor); border-radius: 12px; background: transparent; color: inherit; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; }
.ec-acc-link { font-size: 13px; font-weight: 600; color: var(--store-accent, inherit); }
</style>
