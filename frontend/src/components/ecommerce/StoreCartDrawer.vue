<script setup>
// Drawer del carrito del comprador (desktop: panel derecho; mobile: hoja).
// Lo abre el header (icono carrito con badge) o cart.store.openDrawer().
// Montos e items SIEMPRE del server (cartApi.get/add/update/remove) — el
// front no recalcula precios.
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useCartStore } from '../../stores/cart.store.js'
import { useCustomerStore } from '../../stores/customer.store.js'
import { storeHostSlug } from '../../config/env.js'
import { formatARS } from '../../api/billing.api.js'
import AppIcon from '../AppIcon.vue'

const props = defineProps({ slug: { type: String, required: true } })
const emit = defineEmits(['close'])

// formatARS devuelve 'Gratis' para 0 — en carrito/checkout el total $0
// se muestra como '$ 0,00' (un pedido puede quedar en 0 por descuento).
const money = (v) => (Number(v) > 0 ? formatARS(v, 2) : '$ 0,00')

const cart = useCartStore()
const customer = useCustomerStore()
const router = useRouter()

const checkoutTo = computed(() => ({ path: storeHostSlug ? '/checkout' : `/${props.slug}/checkout` }))
const cartPageTo = computed(() => ({ path: storeHostSlug ? '/carrito' : `/${props.slug}/carrito` }))
const accountTo = computed(() => ({ path: storeHostSlug ? '/cuenta' : `/${props.slug}/cuenta` }))

const empty = computed(() => cart.status === 'ready' && !cart.hasItems)
const loading = computed(() => cart.status === 'loading' || cart.status === 'idle')
const itemNoun = computed(() => (cart.itemCount === 1 ? 'artículo' : 'artículos'))

function goCheckout() {
  cart.drawerOpen = false
  router.push(checkoutTo.value)
}
function goAccount() {
  cart.drawerOpen = false
  router.push(accountTo.value)
}
function close() { cart.drawerOpen = false; emit('close') }
function onBackdrop(e) { if (e.target === e.currentTarget) close() }
</script>

<template>
  <!-- El teleport va a .store-page (raíz del layout), no a body: solo dentro
       de ese scope existen los tokens --sp-* y el data-store-theme activo.
       En body el panel quedaba blanco con tinta heredada — invisible en
       tiendas oscuras. position:fixed sigue siendo viewport: .store-page no
       declara transform/filter/contain. `defer` resuelve el target después
       del montaje: .store-page existe como el raíz del mismo ciclo. -->
  <Teleport defer to=".store-page">
    <div v-if="cart.drawerOpen" class="ec-cart-backdrop" @click="onBackdrop">
      <aside class="ec-cart-panel" role="dialog" aria-modal="true" aria-label="Tu carrito" @keydown.esc="close">
        <header class="ec-cart-head">
          <h2 class="ec-cart-title">
            <AppIcon name="shopping-cart" :size="20" aria-hidden="true" /> Tu carrito
            <span v-if="cart.itemCount" class="ec-cart-count">{{ cart.itemCount }}</span>
          </h2>
          <button type="button" class="ec-cart-close" aria-label="Cerrar carrito" @click="close">
            <AppIcon name="x" :size="18" />
          </button>
        </header>

        <div class="ec-cart-body">
          <div v-if="loading" class="ec-cart-skel" aria-busy="true" aria-label="Cargando tu carrito">
            <div v-for="n in 3" :key="n" class="ec-cart-sk-item">
              <span class="ec-sk-thumb"></span>
              <span class="ec-sk-lines"><span class="ec-sk-line"></span><span class="ec-sk-line short"></span></span>
            </div>
          </div>
          <p v-else-if="cart.status === 'error'" class="ec-cart-empty">
            <AppIcon name="circle-alert" :size="26" aria-hidden="true" />
            No pudimos cargar tu carrito.
            <button type="button" class="ec-cart-link" @click="cart.refresh()">Reintentar</button>
          </p>
          <div v-else-if="empty" class="ec-cart-empty">
            <span class="ec-cart-empty-ico" aria-hidden="true"><AppIcon name="shopping-bag" :size="28" /></span>
            <p><strong>Tu carrito está vacío</strong><br>Agregá productos del catálogo para empezar tu pedido.</p>
            <button type="button" class="ec-cart-ghost" @click="close">Seguir mirando</button>
          </div>

          <ul v-else class="ec-cart-items">
            <li v-for="item in cart.items" :key="item.id" class="ec-cart-item">
              <img v-if="item.image" :src="item.image" :alt="item.name" class="ec-cart-thumb" loading="lazy" />
              <div v-else class="ec-cart-thumb is-empty" aria-hidden="true"><AppIcon name="package" :size="18" /></div>
              <div class="ec-cart-info">
                <p class="ec-cart-name">{{ item.name }}</p>
                <p v-if="item.unavailable_reason || item.purchasable === false" class="ec-cart-warn">
                  <AppIcon name="circle-alert" :size="12" aria-hidden="true" />
                  {{ item.unavailable_reason || 'No disponible por ahora' }}
                </p>
                <div class="ec-cart-row">
                  <div class="ec-cart-qty" role="group" :aria-label="`Cantidad de ${item.name}`">
                    <button type="button" :disabled="cart.busy || item.qty <= 1" aria-label="Quitar uno" @click="cart.setQty(item.id, item.qty - 1)">
                      <AppIcon name="minus" :size="13" />
                    </button>
                    <span>{{ item.qty }}</span>
                    <button type="button" :disabled="cart.busy || (item.stock > 0 && item.qty >= item.stock)" aria-label="Agregar uno" @click="cart.setQty(item.id, item.qty + 1)">
                      <AppIcon name="plus" :size="13" />
                    </button>
                  </div>
                  <span class="ec-cart-price">{{ money(item.line_total) }}</span>
                </div>
                <p class="ec-cart-unit">{{ money(item.unit_price) }} c/u<template v-if="item.list_price && item.unit_price !== item.list_price"> · antes <s>{{ money(item.list_price) }}</s></template></p>
              </div>
              <button type="button" class="ec-cart-remove" aria-label="Quitar del carrito" :disabled="cart.busy" @click="cart.removeItem(item.id)">
                <AppIcon name="trash" :size="16" />
              </button>
            </li>
          </ul>
        </div>

        <footer v-if="cart.hasItems" class="ec-cart-foot">
          <div class="ec-cart-total">
            <span>Total · {{ cart.itemCount }} {{ itemNoun }}</span>
            <strong>{{ money(cart.itemsTotal) }}</strong>
          </div>
          <p v-if="cart.memberDiscount" class="ec-cart-discount">
            <AppIcon name="badge-check" :size="14" aria-hidden="true" />
            Con tu membresía tenés {{ cart.memberDiscount }}% de descuento aplicado.
          </p>
          <button type="button" class="ec-cart-cta" @click="goCheckout">
            Ir a pagar <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
          </button>
          <RouterLink :to="cartPageTo" class="ec-cart-ghost ec-cart-full" @click="close">Ver carrito completo</RouterLink>
          <div class="ec-cart-foot-row">
            <button type="button" class="ec-cart-ghost" :disabled="cart.busy" @click="cart.clear()">Vaciar carrito</button>
            <!-- En tiendas con diseño de patrón no hay header Vue: el drawer
                 es la única puerta a "Mi cuenta" (pedidos, suscripciones). -->
            <RouterLink :to="accountTo" class="ec-cart-link" @click="close">Mi cuenta</RouterLink>
          </div>
        </footer>

        <footer v-else-if="!customer.isAuthenticated" class="ec-cart-foot">
          <p class="ec-cart-hint">Iniciá sesión para guardar tu carrito y seguir tus pedidos.</p>
          <button type="button" class="ec-cart-cta" @click="cart.openAuth('login', { route: checkoutTo.value })">Ingresar</button>
          <button type="button" class="ec-cart-ghost" @click="goAccount">Crear cuenta</button>
        </footer>
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.ec-cart-backdrop { position: fixed; inset: 0; z-index: 1150; background: color-mix(in srgb, #000 50%, transparent); backdrop-filter: blur(2px); animation: ec-cart-fade .2s ease-out; }
.ec-cart-panel {
  position: absolute; top: 0; right: 0; bottom: 0; width: min(420px, 94vw);
  display: flex; flex-direction: column;
  /* Par bg+fg del MISMO scope de tokens: nunca card fija + color:inherit. */
  background: var(--sp-card, #fff); color: var(--sp-ink, #0f172a);
  border-left: 1px solid var(--sp-line, rgba(0,0,0,.1));
  box-shadow: -18px 0 50px rgba(0,0,0,.2);
  animation: ec-cart-slide .26s cubic-bezier(.2, .8, .2, 1);
}
@keyframes ec-cart-fade { from { opacity: 0; } }
@keyframes ec-cart-slide { from { transform: translateX(48px); opacity: .6; } }
.ec-cart-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 16px 18px; border-bottom: 1px solid var(--sp-line, rgba(0,0,0,.08)); }
.ec-cart-title { display: flex; align-items: center; gap: 10px; margin: 0; font-size: 18px; font-weight: 800; }
.ec-cart-count { display: grid; place-items: center; min-width: 26px; height: 26px; padding: 0 7px; border-radius: 999px; background: color-mix(in srgb, var(--store-accent, #111) 14%, transparent); color: var(--store-accent, inherit); font-size: 12.5px; font-weight: 800; font-variant-numeric: tabular-nums; }
.ec-cart-close { display: grid; place-items: center; width: 36px; height: 36px; border: none; border-radius: calc(var(--sp-radius) * .65); background: transparent; color: inherit; cursor: pointer; }
.ec-cart-close:hover { background: color-mix(in srgb, currentColor 8%, transparent); }
.ec-cart-body { flex: 1; overflow-y: auto; padding: 14px 18px; }
.ec-cart-empty { display: grid; place-items: center; gap: 10px; padding: 44px 12px; text-align: center; color: var(--sp-muted, #5b6678); font-size: 14px; line-height: 1.55; }
.ec-cart-empty p { margin: 0; }
.ec-cart-empty strong { color: var(--sp-ink, inherit); }
.ec-cart-empty-ico { display: grid; place-items: center; width: 60px; height: 60px; border-radius: 50%; background: color-mix(in srgb, var(--store-accent, #111) 10%, transparent); color: var(--store-accent, inherit); }
.ec-cart-items { list-style: none; margin: 0; padding: 0; display: grid; gap: 14px; }
.ec-cart-item { display: grid; grid-template-columns: 64px 1fr auto; gap: 12px; align-items: start; }
.ec-cart-thumb { width: 64px; height: 64px; object-fit: cover; border-radius: calc(var(--sp-radius) * .75); background: var(--sp-line, rgba(0,0,0,.06)); }
.ec-cart-thumb.is-empty { display: grid; place-items: center; color: var(--sp-muted, #5b6678); }
.ec-cart-info { min-width: 0; display: grid; gap: 6px; }
.ec-cart-name { margin: 0; font-size: 14px; font-weight: 700; line-height: 1.3; }
.ec-cart-warn { display: flex; align-items: center; gap: 5px; margin: 0; font-size: 12px; color: var(--sp-warning, #B45309); }
.ec-cart-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.ec-cart-qty { display: inline-flex; align-items: center; gap: 2px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .65); }
.ec-cart-qty button { display: grid; place-items: center; width: 30px; height: 30px; border: none; background: transparent; color: inherit; cursor: pointer; }
.ec-cart-qty button:disabled { opacity: .4; cursor: default; }
.ec-cart-qty span { min-width: 24px; text-align: center; font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; }
.ec-cart-price { font-size: 14px; font-weight: 800; font-variant-numeric: tabular-nums; }
.ec-cart-unit { margin: 0; font-size: 11.5px; color: var(--sp-muted, #5b6678); }
.ec-cart-unit s { opacity: .8; }
.ec-cart-remove { border: none; background: transparent; color: var(--sp-muted, #5b6678); cursor: pointer; padding: 6px; border-radius: calc(var(--sp-radius) * .6); align-self: start; }
.ec-cart-remove:hover:not(:disabled) { color: var(--sp-danger, #dc2626); background: color-mix(in srgb, var(--sp-danger, #dc2626) 9%, transparent); }
.ec-cart-remove:disabled { opacity: .4; cursor: default; }
.ec-cart-foot { display: grid; gap: 10px; padding: 16px 18px calc(16px + env(safe-area-inset-bottom)); border-top: 1px solid var(--sp-line, rgba(0,0,0,.08)); }
.ec-cart-total { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; font-size: 15px; }
.ec-cart-total span { color: var(--sp-muted, #5b6678); font-size: 13px; }
.ec-cart-total strong { font-size: 20px; font-weight: 800; font-variant-numeric: tabular-nums; }
.ec-cart-discount { display: flex; align-items: center; gap: 6px; margin: 0; font-size: 12px; color: var(--sp-success, #0E7A55); }
.ec-cart-cta { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 13px 16px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent-ink, #111); color: #fff; font-size: 15px; font-weight: 800; cursor: pointer; text-decoration: none; }
.ec-cart-cta:hover { filter: brightness(1.06); }
.ec-cart-foot-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.ec-cart-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 16px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .75); background: transparent; color: inherit; font-size: 14px; font-weight: 600; cursor: pointer; text-decoration: none; }
.ec-cart-ghost:hover { background: color-mix(in srgb, currentColor 6%, transparent); }
.ec-cart-ghost:disabled { opacity: .5; cursor: default; }
.ec-cart-hint { margin: 0; font-size: 13px; color: var(--sp-muted, #5b6678); text-align: center; line-height: 1.5; }
.ec-cart-full { justify-content: center; text-decoration: none; }
.ec-cart-link { border: none; background: none; color: var(--store-accent, #111); font-weight: 700; cursor: pointer; text-decoration: underline; text-underline-offset: 3px; }

/* Skeletons discretos */
.ec-cart-skel { display: grid; gap: 16px; padding: 4px 0; }
.ec-cart-sk-item { display: flex; gap: 12px; align-items: center; }
.ec-sk-thumb { width: 64px; height: 64px; border-radius: calc(var(--sp-radius) * .75); flex: none; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.ec-sk-lines { flex: 1; display: grid; gap: 8px; }
.ec-sk-line { display: block; height: 11px; border-radius: 7px; background: color-mix(in srgb, var(--sp-muted, #94a3b8) 16%, transparent); }
.ec-sk-lines .short { width: 55%; }
@media (prefers-reduced-motion: no-preference) {
  .ec-sk-thumb, .ec-sk-line { animation: ec-cart-shimmer 1.4s ease-in-out infinite; }
  .ec-cart-sk-item:nth-child(2) .ec-sk-thumb, .ec-cart-sk-item:nth-child(2) .ec-sk-line { animation-delay: .12s; }
  .ec-cart-sk-item:nth-child(3) .ec-sk-thumb, .ec-cart-sk-item:nth-child(3) .ec-sk-line { animation-delay: .24s; }
  @keyframes ec-cart-shimmer { 0%, 100% { opacity: 1; } 50% { opacity: .45; } }
}

.ec-cart-close:focus-visible, .ec-cart-remove:focus-visible, .ec-cart-qty button:focus-visible,
.ec-cart-ghost:focus-visible, .ec-cart-cta:focus-visible, .ec-cart-link:focus-visible {
  outline: 2px solid var(--store-accent, #111); outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .ec-cart-backdrop, .ec-cart-panel { animation: none; }
}
</style>
