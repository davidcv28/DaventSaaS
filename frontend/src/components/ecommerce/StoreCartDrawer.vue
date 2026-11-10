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
const accountTo = computed(() => ({ path: storeHostSlug ? '/cuenta' : `/${props.slug}/cuenta` }))

const empty = computed(() => cart.status === 'ready' && !cart.hasItems)

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
  <Teleport to="body">
    <div v-if="cart.drawerOpen" class="ec-cart-backdrop" @click="onBackdrop">
      <aside class="ec-cart-panel" role="dialog" aria-label="Tu carrito" @keydown.esc="close">
        <header class="ec-cart-head">
          <h2 class="ec-cart-title"><AppIcon name="shopping-cart" :size="20" aria-hidden="true" /> Tu carrito</h2>
          <button type="button" class="ec-cart-close" aria-label="Cerrar carrito" @click="close">
            <AppIcon name="x" :size="18" />
          </button>
        </header>

        <div class="ec-cart-body">
          <p v-if="cart.status === 'loading'" class="ec-cart-empty">Cargando tu carrito…</p>
          <p v-else-if="cart.status === 'error'" class="ec-cart-empty">
            No pudimos cargar tu carrito.
            <button type="button" class="ec-cart-link" @click="cart.refresh()">Reintentar</button>
          </p>
          <div v-else-if="empty" class="ec-cart-empty">
            <AppIcon name="shopping-bag" :size="30" aria-hidden="true" />
            <p>Tu carrito está vacío.</p>
            <button type="button" class="ec-cart-ghost" @click="close">Seguir mirando</button>
          </div>

          <ul v-else class="ec-cart-items">
            <li v-for="item in cart.items" :key="item.id" class="ec-cart-item">
              <img v-if="item.image" :src="item.image" :alt="item.name" class="ec-cart-thumb" loading="lazy" />
              <div v-else class="ec-cart-thumb is-empty" aria-hidden="true"><AppIcon name="package" :size="18" /></div>
              <div class="ec-cart-info">
                <p class="ec-cart-name">{{ item.name }}</p>
                <p v-if="item.unavailable_reason || item.purchasable === false" class="ec-cart-warn">
                  {{ item.unavailable_reason || 'No disponible por ahora' }}
                </p>
                <div class="ec-cart-row">
                  <div class="ec-cart-qty">
                    <button type="button" :disabled="cart.busy || item.qty <= 1" aria-label="Quitar uno" @click="cart.setQty(item.id, item.qty - 1)">
                      <AppIcon name="minus" :size="13" />
                    </button>
                    <span>{{ item.qty }}</span>
                    <button type="button" :disabled="cart.busy" aria-label="Agregar uno" @click="cart.setQty(item.id, item.qty + 1)">
                      <AppIcon name="plus" :size="13" />
                    </button>
                  </div>
                  <span class="ec-cart-price">{{ money(item.line_total) }}</span>
                </div>
                <p v-if="item.list_price && item.unit_price !== item.list_price" class="ec-cart-was">
                  <s>{{ money(item.list_price) }}</s> c/u → {{ money(item.unit_price) }} c/u
                </p>
              </div>
              <button type="button" class="ec-cart-remove" aria-label="Quitar del carrito" :disabled="cart.busy" @click="cart.removeItem(item.id)">
                <AppIcon name="trash" :size="16" />
              </button>
            </li>
          </ul>
        </div>

        <footer v-if="cart.hasItems" class="ec-cart-foot">
          <div class="ec-cart-total">
            <span>Total</span>
            <strong>{{ money(cart.itemsTotal) }}</strong>
          </div>
          <p v-if="cart.memberDiscount" class="ec-cart-discount">
            Con tu membresía tenés {{ cart.memberDiscount }}% de descuento aplicado.
          </p>
          <button type="button" class="ec-cart-cta" @click="goCheckout">
            Ir a pagar <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
          </button>
          <button type="button" class="ec-cart-ghost" :disabled="cart.busy" @click="cart.clear()">Vaciar carrito</button>
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
.ec-cart-backdrop { position: fixed; inset: 0; z-index: 1150; background: color-mix(in srgb, #000 50%, transparent); backdrop-filter: blur(2px); }
.ec-cart-panel {
  position: absolute; top: 0; right: 0; bottom: 0; width: min(420px, 94vw);
  display: flex; flex-direction: column;
  background: var(--sp-card, var(--ds-bg, #fff)); color: var(--sp-ink, inherit);
  border-left: 1px solid var(--sp-line, rgba(0,0,0,.1));
  box-shadow: -18px 0 50px rgba(0,0,0,.2);
}
.ec-cart-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 18px; border-bottom: 1px solid var(--sp-line, rgba(0,0,0,.08)); }
.ec-cart-title { display: flex; align-items: center; gap: 10px; margin: 0; font-size: 18px; font-weight: 800; }
.ec-cart-close { display: grid; place-items: center; width: 34px; height: 34px; border: none; border-radius: calc(var(--sp-radius) * .65); background: transparent; color: inherit; cursor: pointer; }
.ec-cart-body { flex: 1; overflow-y: auto; padding: 14px 18px; }
.ec-cart-empty { display: grid; place-items: center; gap: 10px; padding: 48px 12px; text-align: center; color: var(--sp-muted, inherit); font-size: 14px; }
.ec-cart-items { list-style: none; margin: 0; padding: 0; display: grid; gap: 14px; }
.ec-cart-item { display: grid; grid-template-columns: 64px 1fr auto; gap: 12px; align-items: start; }
.ec-cart-thumb { width: 64px; height: 64px; object-fit: cover; border-radius: calc(var(--sp-radius) * .75); background: var(--sp-line, rgba(0,0,0,.06)); }
.ec-cart-thumb.is-empty { display: grid; place-items: center; color: var(--sp-muted, inherit); }
.ec-cart-info { min-width: 0; display: grid; gap: 6px; }
.ec-cart-name { margin: 0; font-size: 14px; font-weight: 700; line-height: 1.3; }
.ec-cart-warn { margin: 0; font-size: 12px; color: var(--sp-warning); }
.ec-cart-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.ec-cart-qty { display: inline-flex; align-items: center; gap: 4px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .65); }
.ec-cart-qty button { display: grid; place-items: center; width: 30px; height: 30px; border: none; background: transparent; color: inherit; cursor: pointer; }
.ec-cart-qty button:disabled { opacity: .4; cursor: default; }
.ec-cart-qty span { min-width: 22px; text-align: center; font-size: 13px; font-weight: 700; }
.ec-cart-price { font-size: 14px; font-weight: 800; font-variant-numeric: tabular-nums; }
.ec-cart-was { margin: 0; font-size: 11.5px; color: var(--sp-muted, inherit); }
.ec-cart-remove { border: none; background: transparent; color: var(--sp-muted, inherit); cursor: pointer; padding: 4px; }
.ec-cart-foot { display: grid; gap: 10px; padding: 16px 18px calc(16px + env(safe-area-inset-bottom)); border-top: 1px solid var(--sp-line, rgba(0,0,0,.08)); }
.ec-cart-total { display: flex; align-items: baseline; justify-content: space-between; font-size: 15px; }
.ec-cart-total strong { font-size: 20px; font-weight: 800; font-variant-numeric: tabular-nums; }
.ec-cart-discount { margin: 0; font-size: 12px; color: var(--sp-success); }
.ec-cart-cta { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 13px 16px; border: none; border-radius: calc(var(--sp-radius) * .75); background: var(--store-accent, #111); color: var(--store-accent-ink, #fff); font-size: 15px; font-weight: 800; cursor: pointer; text-decoration: none; }
.ec-cart-ghost { display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 11px 16px; border: 1px solid var(--sp-line, currentColor); border-radius: calc(var(--sp-radius) * .75); background: transparent; color: inherit; font-size: 14px; font-weight: 600; cursor: pointer; }
.ec-cart-ghost:disabled { opacity: .5; cursor: default; }
.ec-cart-hint { margin: 0; font-size: 13px; color: var(--sp-muted, inherit); text-align: center; }
.ec-cart-link { border: none; background: none; color: var(--store-accent, inherit); font-weight: 700; cursor: pointer; text-decoration: underline; }
</style>
