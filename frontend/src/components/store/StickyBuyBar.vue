<script setup>
import { ref, watch, onMounted, onBeforeUnmount, computed, inject } from 'vue'
import AppIcon from '../AppIcon.vue'

// Barra inferior fija en mobile (64px + safe-area): aparece cuando el CTA
// principal sale del viewport. Recibe el elemento a observar por prop
// `target` (ref/template ref del padre); sin target queda siempre visible.
//
// E-commerce: si el padre pasa `product` + orders_enabled efectivo, la
// barra suma un CTA "Agregar al carrito" propio (emite 'add' — la vista
// decide cómo mutar el carrito). Sin `product` queda igual que antes.
const props = defineProps({
  target: { type: Object, default: null },
  product: { type: Object, default: null },
  ordersEnabled: { type: Boolean, default: null }
})
const emit = defineEmits(['add'])

const storeCtx = inject('storePage', null)
const canBuy = computed(() => {
  if (props.ordersEnabled != null) return props.ordersEnabled
  const v = storeCtx?.ordersEnabled
  return Boolean(v?.value ?? v)
})
const showAdd = computed(() => Boolean(props.product?.id) && canBuy.value)
const adding = ref(false)
function onAdd() {
  if (adding.value) return
  adding.value = true
  emit('add', props.product)
  // El padre confirma el alta async — el flag se libera solo (el botón
  // no queda trabado si el emit es síncrono).
  setTimeout(() => { adding.value = false }, 900)
}

const visible = ref(!props.target)
let io = null
function bind(el) {
  io?.disconnect()
  io = null
  if (!el || !('IntersectionObserver' in window)) { visible.value = true; return }
  io = new IntersectionObserver(([e]) => { visible.value = !e.isIntersecting }, { threshold: 0 })
  io.observe(el)
}
watch(() => props.target, (t) => bind(t?.$el || t), { flush: 'post' })
onMounted(() => bind(props.target?.$el || props.target))
onBeforeUnmount(() => io?.disconnect())
</script>

<template>
  <div class="sbb" :class="{ on: visible }" role="region" aria-label="Compra rápida">
    <div class="sbb-in">
      <div class="sbb-info"><slot name="info" /></div>
      <div class="sbb-acts">
        <button v-if="showAdd" type="button" class="sbb-cart" :disabled="adding"
          :aria-label="`Agregar ${product.name} al carrito`" @click="onAdd">
          <AppIcon :name="adding ? 'check' : 'shopping-cart'" :size="17" aria-hidden="true" />
          <span>{{ adding ? 'Agregado' : 'Agregar' }}</span>
        </button>
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.sbb { position: fixed; left: 0; right: 0; bottom: 0; z-index: 60; transform: translateY(110%); transition: transform .28s cubic-bezier(.2, .8, .2, 1); background: color-mix(in srgb, var(--sp-card, #fff) 92%, transparent); backdrop-filter: blur(10px); border-top: 1px solid color-mix(in srgb, currentColor 14%, transparent); padding-bottom: env(safe-area-inset-bottom, 0px); }
.sbb.on { transform: translateY(0); }
.sbb-in { display: flex; align-items: center; gap: 12px; height: 64px; padding-inline: clamp(14px, 4vw, 24px); max-width: 1200px; margin-inline: auto; }
.sbb-info { min-width: 0; flex: none; }
.sbb-acts { display: flex; align-items: center; gap: 8px; flex: 1; justify-content: flex-end; min-width: 0; }
.sbb-cart { display: inline-flex; align-items: center; gap: 7px; flex: none; padding: 10px 15px; border: none; border-radius: 999px; background: var(--store-accent, #111); color: var(--store-accent-ink, #fff); font-size: 13.5px; font-weight: 700; cursor: pointer; }
.sbb-cart:disabled { opacity: .7; cursor: default; }
@media (prefers-reduced-motion: reduce) { .sbb { transition: none; } }
</style>
