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
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
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

// Foco: al abrir se guarda el elemento activo (el CTA que disparó el modal)
// para devolvérselo al cerrar; el primer campo lo enfoca StoreAuthForm
// (autofocus). Al cerrar con éxito también se restaura — si ese elemento
// ya no está en el DOM, focus() es un no-op seguro.
const cardRef = ref(null)
let lastFocus = null
function focusablesIn(card) {
  return [...card.querySelectorAll(
    'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )].filter((el) => el.offsetParent !== null || el === document.activeElement)
}
function onKey(e) {
  if (e.key === 'Escape') { close(); return }
  // Focus trap razonable: Tab/Shift+Tab ciclan dentro de la tarjeta.
  if (e.key !== 'Tab') return
  const card = cardRef.value
  if (!card) return
  const items = focusablesIn(card)
  if (!items.length) return
  const first = items[0]
  const last = items[items.length - 1]
  const active = document.activeElement
  if (e.shiftKey && (active === first || !card.contains(active))) {
    last.focus(); e.preventDefault()
  } else if (!e.shiftKey && (active === last || !card.contains(active))) {
    first.focus(); e.preventDefault()
  }
}

watch(() => cart.authMode, (m) => { if (m) mode.value = m })
watch(() => cart.authOpen, (open) => {
  if (open) {
    lastFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    mode.value = cart.authMode || 'login'
    // Escape a nivel window: el @keydown del backdrop solo recibe teclas si el
    // foco está dentro del diálogo; con el listener global cierra siempre.
    window.addEventListener('keydown', onKey)
    // Si el foco quedó fuera de la tarjeta (p.ej. el autofocus del form no
    // corrió), el trap lo reincorpora en el próximo Tab; además se enfoca la
    // tarjeta para lectores de pantalla hasta que el form tome el foco.
    nextTick(() => {
      const card = cardRef.value
      if (card && !card.contains(document.activeElement)) card.focus()
    })
  } else {
    window.removeEventListener('keydown', onKey)
    if (lastFocus?.isConnected) lastFocus.focus()
    lastFocus = null
  }
}, { immediate: true })
onUnmounted(() => window.removeEventListener('keydown', onKey))

function switchMode(m) { mode.value = m }
function close() { emit('close'); cart.closeAuth() }
function onBackdrop(e) { if (e.target === e.currentTarget) close() }
// Auth OK (login/register/google): cerrar el modal y correr la continuación
// pendiente del layout (acción o ruta). El watch de authOpen devuelve el
// foco al elemento que lo abrió.
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
    <div v-if="cart.authOpen" class="ec-auth-backdrop" @click="onBackdrop">
      <div
        ref="cardRef" class="ec-auth-card" role="dialog" aria-modal="true"
        aria-labelledby="ec-auth-modal-title" aria-describedby="ec-auth-modal-sub"
        tabindex="-1"
      >
        <button type="button" class="ec-auth-close" aria-label="Cerrar" @click="close">
          <AppIcon name="x" :size="18" />
        </button>

        <header class="ec-auth-head">
          <span class="ec-auth-badge" aria-hidden="true">
            <AppIcon :name="modeIcon" :size="18" />
          </span>
          <h2 id="ec-auth-modal-title" class="ec-auth-title">{{ title }}</h2>
          <p id="ec-auth-modal-sub" class="ec-auth-sub">{{ subtitle }}</p>
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
  background: color-mix(in srgb, #000 58%, transparent);
  backdrop-filter: blur(6px) saturate(1.05);
  -webkit-backdrop-filter: blur(6px) saturate(1.05);
}
.ec-auth-card {
  position: relative; width: min(440px, 100%); max-height: min(90vh, 760px);
  overflow-y: auto; overscroll-behavior: contain;
  padding: 30px 28px 26px;
  border-radius: calc(var(--sp-radius, 16px) * 1.2); border: 1px solid var(--sp-line, rgba(255, 255, 255, .12));
  /* Par bg+fg del MISMO scope de tokens: nunca card fija + color:inherit. */
  background: var(--sp-card-solid, var(--sp-card, #fff)); color: var(--sp-ink, #0f172a);
  box-shadow: 0 32px 80px -16px rgba(0, 0, 0, .45), 0 8px 24px -12px rgba(0, 0, 0, .25);
}
/* La tarjeta recibe foco programático (tabindex=-1) solo como fallback del
   focus trap: sin outline propio. */
.ec-auth-card:focus { outline: none; }
.ec-auth-card:focus-visible { outline: none; }
@keyframes ec-auth-card-in {
  from { opacity: 0; transform: translate3d(0, 10px, 0) scale(.985); }
  to   { opacity: 1; transform: none; }
}
.ec-auth-card { animation: ec-auth-card-in .22s ease-out both; }
.ec-auth-close {
  position: absolute; top: 12px; right: 12px; z-index: 2;
  display: grid; place-items: center; width: 34px; height: 34px;
  border: none; border-radius: 50%;
  background: var(--sp-soft, rgba(127, 127, 127, .12));
  color: var(--sp-muted, #5b6678); cursor: pointer;
  transition: color .15s, background-color .15s;
}
.ec-auth-close:hover { color: var(--sp-ink, #0f172a); background: color-mix(in srgb, var(--sp-soft, rgba(127, 127, 127, .12)) 70%, var(--sp-line, rgba(127,127,127,.2))); }
.ec-auth-close:focus-visible {
  outline: 2px solid var(--sp-accent-text, var(--store-accent-ink, #111));
  outline-offset: 2px;
}
.ec-auth-head { display: grid; gap: 8px; margin-bottom: 20px; padding-right: 32px; }
.ec-auth-badge {
  display: grid; place-items: center; width: 44px; height: 44px;
  border-radius: 14px; margin-bottom: 6px;
  border: 1px solid color-mix(in srgb, var(--store-accent, #4f46e5) 22%, transparent);
  background: color-mix(in srgb, var(--store-accent, #4f46e5) 13%, var(--sp-card-solid, #fff));
  color: var(--sp-accent-text, var(--store-accent-ink, #111));
}
.ec-auth-title { margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -.015em; line-height: 1.15; color: var(--sp-ink, #0f172a); }
.ec-auth-sub { margin: 0; font-size: 13.5px; line-height: 1.55; color: var(--sp-muted, #5b6678); }
@media (max-width: 480px) {
  .ec-auth-card { padding: 24px 20px 20px; border-radius: calc(var(--sp-radius, 16px) * 1.05); }
}
@media (prefers-reduced-motion: reduce) {
  .ec-auth-card { animation: none; }
}
</style>
