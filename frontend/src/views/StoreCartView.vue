<script setup>
// Página completa del carrito: /<slug>/carrito (o /carrito en subdominio).
// Reusa cart.store — montos SIEMPRE server-side (el front no recalcula).
// Requiere sesión de comprador: sin sesión muestra el prompt de auth.
import { computed, inject, onMounted, watch } from 'vue'
import { useCartStore } from '../stores/cart.store.js'
import { useCustomerStore } from '../stores/customer.store.js'
import { formatARS } from '../api/billing.api.js'
import { storeHostSlug } from '../config/env.js'
import AppIcon from '../components/AppIcon.vue'

const ctx = inject('storePage')
const slug = computed(() => ctx?.slug?.value || ctx?.slug || '')
const ordersEnabled = computed(() => Boolean(ctx?.ordersEnabled?.value ?? ctx?.ordersEnabled))
const shopName = computed(() => ctx?.shopName?.value || ctx?.shopName || 'la tienda')

const cart = useCartStore()
const customer = useCustomerStore()

const money = (v) => (Number(v) > 0 ? formatARS(v, 2) : '$ 0,00')

const checkoutTo = computed(() => ({ path: storeHostSlug ? '/checkout' : `/${slug.value}/checkout` }))
const catalogoTo = computed(() => ({ path: storeHostSlug ? '/catalogo' : `/${slug.value}/catalogo` }))
const cuentaTo = computed(() => ({ path: storeHostSlug ? '/cuenta' : `/${slug.value}/cuenta` }))

const empty = computed(() => cart.status !== 'loading' && !cart.hasItems)
const itemNoun = computed(() => (cart.itemCount === 1 ? 'producto' : 'productos'))

// Tarifa de envío a domicilio del payload público (StoreShippingConfig):
// home_price null = "a coordinar"; número >= 0 = precio fijo del checkout.
const storeData = computed(() => ctx?.store?.value || ctx?.store || null)
const homePrice = computed(() => {
  const raw = storeData.value?.shipping?.home_price
  if (raw === null || raw === undefined || raw === '') return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})
// El envío se elige en el checkout: acá se anticipa la tarifa a domicilio
// y que el retiro en el local es sin cargo (el total lo cierra el server).
const shipNote = computed(() => {
  if (homePrice.value === null) return 'A coordinar en el checkout (domicilio o retiro sin cargo)'
  const home = homePrice.value > 0 ? `Domicilio ${money(homePrice.value)}` : 'Domicilio sin cargo'
  return `${home} · retiro sin cargo`
})

// Métodos de envío: home/pickup se eligen en el checkout (mismas dos
// opciones fijas que ofrece el formulario) — acá solo se anticipa el
// texto; el costo real lo fija el server al crear el pedido.
function maxQty(item) {
  const n = Number(item.stock)
  return Number.isFinite(n) && n > 0 ? n : null
}

function openAuth() {
  cart.openAuth('login', { route: { path: storeHostSlug ? '/carrito' : `/${slug.value}/carrito` } })
}

// Volver del login (pending.route = esta misma página no dispara
// remount): cuando la sesión aparece, recargar el carrito de una.
watch(() => customer.isAuthenticated, (authed) => {
  if (authed && ordersEnabled.value) cart.refresh()
})

onMounted(async () => {
  if (!ordersEnabled.value) return
  if (!(await cart.ensureCustomer())) return
  cart.refresh()
})
</script>

<template>
  <div class="sp-page-root ec-cartpg">
    <header class="ec-cp-head">
      <div class="ec-cp-headrow">
        <h1 class="ec-cp-title">Tu carrito</h1>
        <span v-if="customer.isAuthenticated && cart.itemCount" class="ec-cp-count" aria-label="Cantidad de productos">
          {{ cart.itemCount }} {{ itemNoun }}
        </span>
      </div>
      <p class="ec-cp-sub">{{ shopName }} · revisá los productos antes de pagar</p>
    </header>

    <div v-if="!ordersEnabled" class="ec-cp-card ec-cp-note">
      <span class="ec-cp-note-ico" aria-hidden="true"><AppIcon name="package" :size="22" /></span>
      <div>
        <h2 class="ec-cp-h2">Esta tienda todavía no vende online</h2>
        <p class="ec-cp-muted">Podés ver el catálogo y hacer tu pedido por los medios de contacto de la tienda.</p>
      </div>
      <RouterLink :to="catalogoTo" class="ec-btn-primary">Ver catálogo</RouterLink>
    </div>

    <div v-else-if="cart.status === 'loading'" class="ec-cp-card ec-cp-skel" aria-busy="true" aria-label="Cargando tu carrito">
      <span class="ec-sk-line ec-sk-title"></span>
      <div v-for="n in 3" :key="n" class="ec-sk-item">
        <span class="ec-sk-line ec-sk-thumb"></span>
        <span class="ec-sk-lines"><span class="ec-sk-line"></span><span class="ec-sk-line short"></span></span>
        <span class="ec-sk-line ec-sk-qty"></span>
      </div>
      <span class="ec-sk-line ec-sk-total"></span>
    </div>

    <div v-else-if="cart.status === 'error'" class="ec-cp-card ec-cp-note" role="alert">
      <span class="ec-cp-note-ico is-danger" aria-hidden="true"><AppIcon name="circle-alert" :size="22" /></span>
      <div>
        <h2 class="ec-cp-h2">No pudimos cargar tu carrito</h2>
        <p class="ec-cp-muted">Revisá tu conexión e intentá de nuevo.</p>
      </div>
      <button type="button" class="ec-btn-primary" @click="cart.refresh()">Reintentar</button>
    </div>

    <div v-else-if="!customer.isAuthenticated" class="ec-cp-card ec-cp-note">
      <span class="ec-cp-note-ico" aria-hidden="true"><AppIcon name="user" :size="22" /></span>
      <div>
        <h2 class="ec-cp-h2">Iniciá sesión para ver tu carrito</h2>
        <p class="ec-cp-muted">Tu carrito se guarda en tu cuenta de comprador: entrá o creá tu cuenta para retomarlo donde lo dejaste.</p>
      </div>
      <button type="button" class="ec-btn-primary" @click="openAuth">Ingresar o crear cuenta</button>
      <RouterLink :to="catalogoTo" class="ec-cp-link">Seguir mirando el catálogo</RouterLink>
    </div>

    <div v-else-if="empty" class="ec-cp-card ec-cp-empty">
      <span class="ec-cp-empty-ico" aria-hidden="true"><AppIcon name="shopping-bag" :size="30" /></span>
      <h2 class="ec-cp-h2">Tu carrito está vacío</h2>
      <p class="ec-cp-muted">Agregá productos del catálogo para empezar tu pedido.</p>
      <RouterLink :to="catalogoTo" class="ec-btn-primary">Ir al catálogo</RouterLink>
    </div>

    <div v-else class="ec-cp-grid">
      <section class="ec-cp-card ec-cp-items" aria-label="Productos del carrito">
        <ul class="ec-cp-list">
          <li v-for="item in cart.items" :key="item.id" class="ec-cp-item">
            <RouterLink v-if="item.product_id" :to="{ path: storeHostSlug ? `/producto/${item.product_id}` : `/${slug}/producto/${item.product_id}` }" class="ec-cp-thumblink" :aria-label="`Ver ${item.name}`">
              <img v-if="item.image" :src="item.image" :alt="item.name" class="ec-cp-thumb" loading="lazy" />
              <span v-else class="ec-cp-thumb is-empty" aria-hidden="true"><AppIcon name="package" :size="20" /></span>
            </RouterLink>
            <span v-else class="ec-cp-thumblink">
              <img v-if="item.image" :src="item.image" :alt="item.name" class="ec-cp-thumb" loading="lazy" />
              <span v-else class="ec-cp-thumb is-empty" aria-hidden="true"><AppIcon name="package" :size="20" /></span>
            </span>

            <div class="ec-cp-info">
              <p class="ec-cp-name">{{ item.name }}</p>
              <p class="ec-cp-unit">{{ money(item.unit_price) }} c/u<template v-if="item.list_price && item.unit_price !== item.list_price"> · antes <s>{{ money(item.list_price) }}</s></template></p>
              <p v-if="item.unavailable_reason || item.purchasable === false" class="ec-cp-warn" role="alert">
                <AppIcon name="circle-alert" :size="13" aria-hidden="true" />
                {{ item.unavailable_reason || 'No disponible por ahora' }}
              </p>
              <p v-else-if="maxQty(item) && item.qty >= maxQty(item)" class="ec-cp-stock">Stock máximo disponible</p>
            </div>

            <div class="ec-cp-controls">
              <div class="ec-cp-qty" role="group" :aria-label="`Cantidad de ${item.name}`">
                <button type="button" :disabled="cart.busy || item.qty <= 1" aria-label="Quitar uno" @click="cart.setQty(item.id, item.qty - 1)">
                  <AppIcon name="minus" :size="14" />
                </button>
                <span>{{ item.qty }}</span>
                <button type="button" :disabled="cart.busy || (maxQty(item) !== null && item.qty >= maxQty(item))" aria-label="Agregar uno" @click="cart.setQty(item.id, item.qty + 1)">
                  <AppIcon name="plus" :size="14" />
                </button>
              </div>
              <strong class="ec-cp-line">{{ money(item.line_total) }}</strong>
            </div>

            <button type="button" class="ec-cp-remove" aria-label="Quitar del carrito" :disabled="cart.busy" @click="cart.removeItem(item.id)">
              <AppIcon name="trash" :size="16" />
            </button>
          </li>
        </ul>
        <div class="ec-cp-items-foot">
          <button type="button" class="ec-cp-link" :disabled="cart.busy" @click="cart.clear()">Vaciar carrito</button>
          <RouterLink :to="catalogoTo" class="ec-cp-link">Seguir comprando</RouterLink>
        </div>
      </section>

      <aside class="ec-cp-side">
        <section class="ec-cp-card ec-cp-summary" aria-label="Resumen del pedido">
          <h2 class="ec-cp-h2">Resumen</h2>
          <p class="ec-cp-countline">{{ cart.itemCount }} {{ itemNoun }} en tu pedido</p>
          <dl class="ec-cp-totals">
            <div><dt>Subtotal</dt><dd>{{ money(cart.itemsTotal) }}</dd></div>
            <div v-if="cart.memberDiscount" class="ec-cp-discount">
              <dt><AppIcon name="badge-check" :size="14" aria-hidden="true" /> Descuento de miembro</dt>
              <dd>−{{ cart.memberDiscount }}% ya incluido</dd>
            </div>
            <div><dt>Envío</dt><dd class="ec-cp-ship-note">{{ shipNote }}</dd></div>
            <div class="ec-cp-grand"><dt>Total estimado</dt><dd>{{ money(cart.itemsTotal) }}</dd></div>
          </dl>
          <p class="ec-cp-muted">El total final lo confirma el servidor al crear el pedido.</p>
          <RouterLink :to="checkoutTo" class="ec-btn-primary ec-cp-cta">
            Finalizar compra <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
          </RouterLink>
          <RouterLink :to="cuentaTo" class="ec-cp-link">Ir a mi cuenta</RouterLink>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.ec-cartpg { display: grid; gap: 18px; }
.ec-cp-head { display: grid; gap: 4px; }
.ec-cp-headrow { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.ec-cp-title { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -.02em; }
.ec-cp-count { font-size: 12.5px; font-weight: 700; padding: 4px 11px; border-radius: 999px; background: color-mix(in srgb, var(--store-accent, #111) 12%, transparent); color: var(--store-accent, inherit); font-variant-numeric: tabular-nums; }
.ec-cp-sub { margin: 0; font-size: 14px; color: var(--sp-muted, inherit); }
.ec-cp-h2 { margin: 0; font-size: 16px; font-weight: 800; }
.ec-cp-card { display: grid; gap: 14px; padding: 18px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); }
.ec-cp-note { grid-template-columns: auto 1fr; align-items: center; }
.ec-cp-note > div { display: grid; gap: 4px; }
.ec-cp-note .ec-btn-primary, .ec-cp-note .ec-cp-link { grid-column: 1 / -1; justify-self: start; }
.ec-cp-note-ico { display: grid; place-items: center; width: 46px; height: 46px; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 10%, transparent); color: var(--store-accent, inherit); }
.ec-cp-note-ico.is-danger { background: color-mix(in srgb, var(--sp-danger, #dc2626) 12%, transparent); color: var(--sp-danger, #dc2626); }
.ec-cp-muted { margin: 0; font-size: 13px; line-height: 1.5; color: var(--sp-muted, inherit); }
.ec-cp-error { margin: 0; color: var(--sp-danger, #dc2626); }
.ec-cp-empty { justify-items: center; text-align: center; padding: 44px 18px; color: var(--sp-muted, inherit); }
.ec-cp-empty-ico { display: grid; place-items: center; width: 64px; height: 64px; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 9%, transparent); color: var(--store-accent, inherit); margin-bottom: 4px; }
.ec-cp-link { border: none; background: none; color: var(--store-accent, inherit); font-weight: 700; font-size: 14px; cursor: pointer; text-decoration: underline; text-underline-offset: 3px; padding: 4px 0; }
.ec-cp-link:disabled { opacity: .5; cursor: default; }
.ec-cp-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 18px; align-items: start; }
.ec-cp-items { padding: 10px 18px; }
.ec-cp-list { list-style: none; margin: 0; padding: 0; display: grid; }
.ec-cp-item { display: grid; grid-template-columns: 72px minmax(0,1fr) auto auto; gap: 14px; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--sp-line, rgba(0,0,0,.07)); }
.ec-cp-item:last-child { border-bottom: none; }
.ec-cp-thumblink { display: block; width: 72px; height: 72px; }
.ec-cp-thumb { display: block; width: 72px; height: 72px; object-fit: cover; border-radius: calc(var(--sp-radius) * .75); background: var(--sp-line, rgba(0,0,0,.06)); }
.ec-cp-thumb.is-empty { display: grid; place-items: center; color: var(--sp-muted, inherit); }
.ec-cp-info { min-width: 0; display: grid; gap: 3px; }
.ec-cp-name { margin: 0; font-size: 14.5px; font-weight: 700; line-height: 1.3; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: clamp; overflow: hidden; }
.ec-cp-unit { margin: 0; font-size: 12.5px; color: var(--sp-muted, inherit); }
.ec-cp-unit s { opacity: .8; }
.ec-cp-was { margin: 0; font-size: 11.5px; color: var(--sp-muted, inherit); }
.ec-cp-warn { display: flex; align-items: center; gap: 5px; margin: 0; font-size: 12px; color: var(--sp-warning, #B45309); }
.ec-cp-stock { margin: 0; font-size: 11.5px; color: var(--sp-muted, inherit); }
.ec-cp-controls { display: grid; justify-items: end; gap: 8px; }
.ec-cp-qty { display: inline-flex; align-items: center; gap: 2px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .65); }
.ec-cp-qty button { display: grid; place-items: center; width: 36px; height: 36px; border: none; background: transparent; color: inherit; cursor: pointer; border-radius: calc(var(--sp-radius) * .55); }
.ec-cp-qty button:hover:not(:disabled) { background: color-mix(in srgb, currentColor 8%, transparent); }
.ec-cp-qty button:disabled { opacity: .35; cursor: default; }
.ec-cp-qty span { min-width: 26px; text-align: center; font-size: 14px; font-weight: 700; font-variant-numeric: tabular-nums; }
.ec-cp-line { font-size: 15px; font-weight: 800; font-variant-numeric: tabular-nums; white-space: nowrap; }
.ec-cp-remove { border: none; background: transparent; color: var(--sp-muted, inherit); cursor: pointer; padding: 8px; border-radius: calc(var(--sp-radius) * .6); align-self: start; }
.ec-cp-remove:hover:not(:disabled) { color: var(--sp-danger, #dc2626); background: color-mix(in srgb, var(--sp-danger, #dc2626) 9%, transparent); }
.ec-cp-remove:disabled { opacity: .4; cursor: default; }
.ec-cp-items-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding-top: 12px; flex-wrap: wrap; }
.ec-cp-side { position: sticky; top: 90px; }
.ec-cp-summary { gap: 12px; }
.ec-cp-countline { margin: -8px 0 0; font-size: 12.5px; color: var(--sp-muted, inherit); }
.ec-cp-totals { display: grid; gap: 9px; margin: 0; font-size: 14px; }
.ec-cp-totals > div { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.ec-cp-totals dt { color: var(--sp-muted, inherit); display: inline-flex; align-items: center; gap: 5px; }
.ec-cp-totals dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; text-align: right; }
.ec-cp-discount dd { color: var(--sp-success, #0E7A55); font-weight: 700; }
.ec-cp-ship-note { font-size: 12px; font-weight: 500; max-width: 72%; line-height: 1.4; }
.ec-cp-grand { padding-top: 10px; border-top: 1px solid var(--sp-line, rgba(0,0,0,.09)); font-size: 16px; }
.ec-cp-grand dd { font-weight: 800; font-size: 18px; }
.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 13px 16px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: #fff; font-size: 15px; font-weight: 800; cursor: pointer; text-decoration: none; }
.ec-btn-primary:hover { filter: brightness(1.06); }
.ec-cp-cta { width: 100%; }

/* Skeletons discretos ( shimmer apagado, sin movimiento con reduced-motion) */
.ec-cp-skel { gap: 16px; }
.ec-sk-line { display: block; height: 12px; border-radius: 8px; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.ec-sk-title { width: 34%; height: 18px; }
.ec-sk-item { display: flex; gap: 14px; align-items: center; }
.ec-sk-thumb { width: 72px; height: 72px; border-radius: calc(var(--sp-radius) * .75); flex: none; }
.ec-sk-lines { flex: 1; display: grid; gap: 8px; }
.ec-sk-lines .short { width: 55%; }
.ec-sk-qty { width: 96px; height: 36px; border-radius: calc(var(--sp-radius) * .65); }
.ec-sk-total { width: 42%; height: 16px; margin-top: 4px; }
@media (prefers-reduced-motion: no-preference) {
  .ec-sk-line { animation: ec-cp-shimmer 1.4s ease-in-out infinite; }
  .ec-sk-item:nth-child(2) .ec-sk-line { animation-delay: .12s; }
  .ec-sk-item:nth-child(3) .ec-sk-line { animation-delay: .24s; }
  @keyframes ec-cp-shimmer { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
}

.ec-cp-item :focus-visible, .ec-cp-remove:focus-visible, .ec-cp-qty button:focus-visible,
.ec-cp-link:focus-visible, .ec-btn-primary:focus-visible, .ec-cp-thumblink:focus-visible {
  outline: 2px solid var(--store-accent, #111); outline-offset: 2px;
}

@media (max-width: 860px) {
  .ec-cp-grid { grid-template-columns: 1fr; }
  .ec-cp-side { position: static; }
}
@media (max-width: 560px) {
  .ec-cp-item { grid-template-columns: 56px minmax(0,1fr) auto; grid-template-areas: "img info remove" "img controls controls"; row-gap: 10px; }
  .ec-cp-thumblink { grid-area: img; width: 56px; height: 56px; }
  .ec-cp-thumblink .ec-cp-thumb, .ec-cp-thumblink .ec-cp-thumb.is-empty { width: 56px; height: 56px; }
  .ec-cp-info { grid-area: info; }
  .ec-cp-controls { grid-area: controls; grid-template-columns: 1fr auto; justify-items: start; align-items: center; }
  .ec-cp-line { justify-self: end; }
  .ec-cp-remove { grid-area: remove; justify-self: end; align-self: start; }
  .ec-cp-note { grid-template-columns: 1fr; justify-items: start; }
  .ec-cp-note .ec-btn-primary, .ec-cp-note .ec-cp-link { grid-column: auto; }
}
</style>
