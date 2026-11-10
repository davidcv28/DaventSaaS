<script setup>
// Página completa del carrito: /<slug>/carrito (o /carrito en subdominio).
// Reusa cart.store — montos SIEMPRE server-side (el front no recalcula).
// Requiere sesión de comprador: sin sesión muestra el prompt de auth.
import { computed, inject, onMounted } from 'vue'
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

onMounted(async () => {
  if (!ordersEnabled.value) return
  if (!(await cart.ensureCustomer())) return
  cart.refresh()
})
</script>

<template>
  <div class="sp-page-root ec-cartpg">
    <header class="ec-cp-head">
      <h1 class="ec-cp-title">Tu carrito</h1>
      <p class="ec-cp-sub">{{ shopName }} · revisá los productos antes de pagar</p>
    </header>

    <div v-if="!ordersEnabled" class="ec-cp-card">
      <p><AppIcon name="package" :size="22" aria-hidden="true" /> Esta tienda todavía no vende online.</p>
      <RouterLink :to="catalogoTo" class="ec-btn-primary">Ver catálogo</RouterLink>
    </div>

    <div v-else-if="cart.status === 'loading'" class="ec-cp-card">Cargando tu carrito…</div>
    <div v-else-if="cart.status === 'error'" class="ec-cp-card">
      <p class="ec-cp-error" role="alert">No pudimos cargar tu carrito.</p>
      <button type="button" class="ec-btn-primary" @click="cart.refresh()">Reintentar</button>
    </div>

    <div v-else-if="!customer.isAuthenticated" class="ec-cp-card">
      <h2 class="ec-cp-h2">Iniciá sesión para ver tu carrito</h2>
      <p class="ec-cp-muted">Tu carrito se guarda en tu cuenta de comprador.</p>
      <button type="button" class="ec-btn-primary" @click="openAuth">Ingresar o crear cuenta</button>
      <RouterLink :to="catalogoTo" class="ec-cp-link">Seguir mirando el catálogo</RouterLink>
    </div>

    <div v-else-if="empty" class="ec-cp-card ec-cp-empty">
      <AppIcon name="shopping-bag" :size="34" aria-hidden="true" />
      <h2 class="ec-cp-h2">Tu carrito está vacío</h2>
      <p class="ec-cp-muted">Agregá productos del catálogo para empezar tu pedido.</p>
      <RouterLink :to="catalogoTo" class="ec-btn-primary">Ir al catálogo</RouterLink>
    </div>

    <div v-else class="ec-cp-grid">
      <section class="ec-cp-card ec-cp-items" aria-label="Productos del carrito">
        <ul class="ec-cp-list">
          <li v-for="item in cart.items" :key="item.id" class="ec-cp-item">
            <img v-if="item.image" :src="item.image" :alt="item.name" class="ec-cp-thumb" loading="lazy" />
            <div v-else class="ec-cp-thumb is-empty" aria-hidden="true"><AppIcon name="package" :size="20" /></div>

            <div class="ec-cp-info">
              <p class="ec-cp-name">{{ item.name }}</p>
              <p class="ec-cp-unit">{{ money(item.unit_price) }} c/u</p>
              <p v-if="item.list_price && item.unit_price !== item.list_price" class="ec-cp-was">
                <s>{{ money(item.list_price) }}</s>
              </p>
              <p v-if="item.unavailable_reason || item.purchasable === false" class="ec-cp-warn" role="alert">
                <AppIcon name="circle-alert" :size="13" aria-hidden="true" />
                {{ item.unavailable_reason || 'No disponible por ahora' }}
              </p>
              <p v-else-if="maxQty(item) && item.qty >= maxQty(item)" class="ec-cp-stock">Stock máximo disponible</p>
            </div>

            <div class="ec-cp-qty">
              <button type="button" :disabled="cart.busy || item.qty <= 1" aria-label="Quitar uno" @click="cart.setQty(item.id, item.qty - 1)">
                <AppIcon name="minus" :size="14" />
              </button>
              <span>{{ item.qty }}</span>
              <button type="button" :disabled="cart.busy || (maxQty(item) !== null && item.qty >= maxQty(item))" aria-label="Agregar uno" @click="cart.setQty(item.id, item.qty + 1)">
                <AppIcon name="plus" :size="14" />
              </button>
            </div>

            <strong class="ec-cp-line">{{ money(item.line_total) }}</strong>

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
        <section class="ec-cp-card">
          <h2 class="ec-cp-h2">Resumen</h2>
          <dl class="ec-cp-totals">
            <div><dt>Subtotal</dt><dd>{{ money(cart.itemsTotal) }}</dd></div>
            <div v-if="cart.memberDiscount"><dt>Descuento de miembro</dt><dd>−{{ cart.memberDiscount }}%</dd></div>
            <div><dt>Envío</dt><dd>Se elige en el checkout (domicilio o retiro)</dd></div>
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
.ec-cp-title { margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -.02em; }
.ec-cp-sub { margin: 0; font-size: 14px; color: var(--sp-muted, inherit); }
.ec-cp-h2 { margin: 0; font-size: 16px; font-weight: 800; }
.ec-cp-card { display: grid; gap: 14px; padding: 18px; border: 1px solid var(--sp-line, rgba(0,0,0,.09)); border-radius: var(--sp-radius); background: var(--sp-card, transparent); }
.ec-cp-muted { margin: 0; font-size: 13px; line-height: 1.5; color: var(--sp-muted, inherit); }
.ec-cp-error { margin: 0; color: var(--sp-danger); }
.ec-cp-empty { justify-items: center; text-align: center; padding: 40px 18px; color: var(--sp-muted, inherit); }
.ec-cp-link { border: none; background: none; color: var(--store-accent, inherit); font-weight: 700; font-size: 14px; cursor: pointer; text-decoration: underline; padding: 0; }
.ec-cp-grid { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 18px; align-items: start; }
.ec-cp-items { padding: 10px 18px; }
.ec-cp-list { list-style: none; margin: 0; padding: 0; display: grid; }
.ec-cp-item { display: grid; grid-template-columns: 72px minmax(0,1fr) auto auto auto; gap: 14px; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--sp-line, rgba(0,0,0,.07)); }
.ec-cp-item:last-child { border-bottom: none; }
.ec-cp-thumb { width: 72px; height: 72px; object-fit: cover; border-radius: calc(var(--sp-radius) * .75); background: var(--sp-line, rgba(0,0,0,.06)); }
.ec-cp-thumb.is-empty { display: grid; place-items: center; color: var(--sp-muted, inherit); }
.ec-cp-info { min-width: 0; display: grid; gap: 3px; }
.ec-cp-name { margin: 0; font-size: 14.5px; font-weight: 700; line-height: 1.3; }
.ec-cp-unit { margin: 0; font-size: 12.5px; color: var(--sp-muted, inherit); }
.ec-cp-was { margin: 0; font-size: 11.5px; color: var(--sp-muted, inherit); }
.ec-cp-warn { display: flex; align-items: center; gap: 5px; margin: 0; font-size: 12px; color: var(--sp-warning); }
.ec-cp-stock { margin: 0; font-size: 11.5px; color: var(--sp-muted, inherit); }
.ec-cp-qty { display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .65); }
.ec-cp-qty button { display: grid; place-items: center; width: 34px; height: 34px; border: none; background: transparent; color: inherit; cursor: pointer; }
.ec-cp-qty button:disabled { opacity: .4; cursor: default; }
.ec-cp-qty span { min-width: 24px; text-align: center; font-size: 14px; font-weight: 700; }
.ec-cp-line { font-size: 15px; font-weight: 800; font-variant-numeric: tabular-nums; white-space: nowrap; }
.ec-cp-remove { border: none; background: transparent; color: var(--sp-muted, inherit); cursor: pointer; padding: 4px; }
.ec-cp-items-foot { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding-top: 12px; }
.ec-cp-side { position: sticky; top: 90px; }
.ec-cp-totals { display: grid; gap: 8px; margin: 0; font-size: 14px; }
.ec-cp-totals > div { display: flex; justify-content: space-between; gap: 10px; }
.ec-cp-totals dt { color: var(--sp-muted, inherit); }
.ec-cp-totals dd { margin: 0; font-weight: 600; font-variant-numeric: tabular-nums; }
.ec-cp-grand { padding-top: 10px; border-top: 1px solid var(--sp-line, rgba(0,0,0,.09)); font-size: 16px; }
.ec-cp-grand dd { font-weight: 800; }
.ec-btn-primary { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 13px 16px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: #fff; font-size: 15px; font-weight: 800; cursor: pointer; text-decoration: none; }
.ec-cp-cta { width: 100%; }

@media (max-width: 860px) {
  .ec-cp-grid { grid-template-columns: 1fr; }
  .ec-cp-side { position: static; }
}
@media (max-width: 560px) {
  .ec-cp-item { grid-template-columns: 56px minmax(0,1fr) auto; grid-template-areas: "img info info" "img qty total" "img remove remove"; }
  .ec-cp-thumb { grid-area: img; width: 56px; height: 56px; }
  .ec-cp-info { grid-area: info; }
  .ec-cp-qty { grid-area: qty; justify-self: start; }
  .ec-cp-line { grid-area: total; justify-self: end; }
  .ec-cp-remove { grid-area: remove; justify-self: end; }
}
</style>
