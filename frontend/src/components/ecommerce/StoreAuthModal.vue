<script setup>
// Modal de auth del COMPRADOR de tienda (sesión customer — distinta de la
// sesión DAVENT del dueño). La monta StorePublicLayout una sola vez y el
// cart.store la abre desde cualquier "Agregar al carrito" / "Ir a pagar" /
// "Suscribirme". Modos: login | register | forgot (recuperar contraseña).
//
// El formulario es StoreAuthForm — el mismo de la página /ingresar
// (StoreAuthView): un solo comportamiento, dos envoltorios. El modal queda
// para pendientes de ACCIÓN ({action}) que no pueden cruzar una
// navegación; los {route} ya pueden usar authRoute → /ingresar.
import { ref, computed, watch } from 'vue'
import { useCartStore } from '../../stores/cart.store.js'
import StoreAuthForm from './StoreAuthForm.vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  slug: { type: String, required: true },
  // Título contextual: 'checkout' | 'cart' | 'subscribe' | '' (genérico).
  purpose: { type: String, default: '' }
})
const emit = defineEmits(['done', 'close'])

const cart = useCartStore()

const mode = ref('login')

const titles = { login: 'Ingresá a tu cuenta', register: 'Creá tu cuenta', forgot: 'Recuperá tu contraseña' }
const title = computed(() => titles[mode.value] || 'Tu cuenta')
const subtitle = computed(() => {
  if (props.purpose === 'checkout') return 'Para finalizar tu compra necesitás ingresar o crear tu cuenta.'
  if (props.purpose === 'subscribe') return 'Para suscribirte necesitás ingresar o crear tu cuenta.'
  return 'Seguimiento de pedidos, suscripciones y soporte en un solo lugar.'
})
const modeIcon = computed(() => (mode.value === 'forgot' ? 'lock' : 'user'))

watch(() => cart.authMode, (m) => { if (m) mode.value = m })
watch(() => cart.authOpen, (open) => { if (open) mode.value = cart.authMode || 'login' })

function switchMode(m) { mode.value = m }
function close() { emit('close'); cart.closeAuth() }
function onBackdrop(e) { if (e.target === e.currentTarget) close() }
function onKey(e) { if (e.key === 'Escape') close() }
// Auth OK (login/register/google): cerrar el modal y correr la continuación
// pendiente del layout (acción o ruta).
function onDone() { cart.closeAuth(); emit('done') }
</script>

<template>
  <!-- El teleport va a .store-page (raíz del layout), no a body: solo dentro
       de ese scope existen los tokens --sp-* y el data-store-theme activo.
       En body la tarjeta quedaba blanca con tinta heredada — invisible en
       tiendas oscuras. position:fixed sigue siendo viewport: .store-page no
       declara transform/filter/contain. `defer` resuelve el target después
       del montaje: .store-page existe como el raíz del mismo ciclo. -->
  <Teleport defer to=".store-page">
    <div v-if="cart.authOpen" class="ec-auth-backdrop" @click="onBackdrop" @keydown="onKey">
      <div class="ec-auth-card" role="dialog" aria-modal="true" :aria-label="title">
        <button type="button" class="ec-auth-close" aria-label="Cerrar" @click="close">
          <AppIcon name="x" :size="18" />
        </button>

        <header class="ec-auth-head">
          <span class="ec-auth-badge" aria-hidden="true">
            <AppIcon :name="modeIcon" :size="18" />
          </span>
          <h2 class="ec-auth-title">{{ title }}</h2>
          <p class="ec-auth-sub">{{ subtitle }}</p>
        </header>

        <StoreAuthForm :slug="slug" :mode="mode" @done="onDone" @mode="switchMode" />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.ec-auth-backdrop {
  position: fixed; inset: 0; z-index: 1200;
  display: grid; place-items: center; padding: 20px;
  background: color-mix(in srgb, #000 55%, transparent);
  backdrop-filter: blur(3px);
}
.ec-auth-card {
  position: relative; width: min(440px, 100%); max-height: min(90vh, 760px);
  overflow-y: auto; padding: 28px 26px 24px;
  border-radius: calc(var(--sp-radius, 16px) * 1.2); border: 1px solid var(--sp-line, rgba(255, 255, 255, .12));
  /* Par bg+fg del MISMO scope de tokens: nunca card fija + color:inherit. */
  background: var(--sp-card-solid, var(--sp-card, #fff)); color: var(--sp-ink, #0f172a);
  box-shadow: 0 24px 60px rgba(0, 0, 0, .3);
}
.ec-auth-close {
  position: absolute; top: 12px; right: 12px; z-index: 2;
  display: grid; place-items: center; width: 34px; height: 34px;
  border: none; border-radius: calc(var(--sp-radius, 16px) * .65); background: transparent; color: inherit; cursor: pointer;
}
.ec-auth-close:hover { background: var(--sp-soft, rgba(127, 127, 127, .12)); }
.ec-auth-head { display: grid; gap: 8px; margin-bottom: 18px; padding-right: 30px; }
.ec-auth-badge {
  display: grid; place-items: center; width: 42px; height: 42px;
  border-radius: 12px; margin-bottom: 4px;
  background: color-mix(in srgb, var(--store-accent, #4f46e5) 13%, var(--sp-card-solid, #fff));
  color: var(--sp-accent-text, var(--store-accent-ink, #111));
}
.ec-auth-title { margin: 0; font-size: 21px; font-weight: 800; letter-spacing: -.01em; color: var(--sp-ink, #0f172a); }
.ec-auth-sub { margin: 0; font-size: 13px; line-height: 1.5; color: var(--sp-muted, #5b6678); }
@media (max-width: 480px) {
  .ec-auth-card { padding: 24px 20px 20px; border-radius: calc(var(--sp-radius, 16px) * 1.05); }
}
</style>
