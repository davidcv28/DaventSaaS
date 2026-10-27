<script setup>
import { ref, watch, nextTick, onBeforeUnmount } from 'vue'
import AppIcon from '../AppIcon.vue'

// Bottom sheet (talles, filtros, horarios): alto 60-85dvh, handle 36×4,
// cierre por swipe, Esc y backdrop, foco atrapado y scroll del fondo
// bloqueado (.sp-lock ya existe en el layout para el drawer).
const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
  tall: { type: Boolean, default: false } // 85dvh en vez de 60
})
const emit = defineEmits(['close'])
const sheet = ref(null)
const dragY = ref(0)
let startY = 0
let dragging = false
let lastFocus = null

function close() { emit('close') }
function onKey(e) {
  if (e.key === 'Escape') { close(); return }
  if (e.key !== 'Tab' || !sheet.value) return
  // Foco atrapado dentro del sheet.
  const els = [...sheet.value.querySelectorAll('button, a[href], input, textarea, select, [tabindex]:not([tabindex="-1"])')].filter((el) => !el.disabled && el.offsetParent !== null)
  if (!els.length) return
  const first = els[0]
  const last = els[els.length - 1]
  if (e.shiftKey && document.activeElement === first) { last.focus(); e.preventDefault() }
  else if (!e.shiftKey && document.activeElement === last) { first.focus(); e.preventDefault() }
}
function onTouchStart(e) { startY = e.touches[0].clientY; dragging = true; dragY.value = 0 }
function onTouchMove(e) {
  if (!dragging) return
  const dy = e.touches[0].clientY - startY
  dragY.value = Math.max(0, dy)
}
function onTouchEnd() {
  if (!dragging) return
  dragging = false
  if (dragY.value > 90) close()
  else dragY.value = 0
}

watch(() => props.open, async (open) => {
  document.documentElement.classList.toggle('sp-lock', open)
  if (open) {
    lastFocus = document.activeElement
    await nextTick()
    sheet.value?.querySelector('.bs-close')?.focus()
  } else if (lastFocus?.focus) {
    lastFocus.focus()
    lastFocus = null
  }
})
onBeforeUnmount(() => document.documentElement.classList.remove('sp-lock'))
</script>

<template>
  <Teleport to="body">
    <Transition name="bs">
      <div v-if="open" class="bs-root" @keydown="onKey">
        <div class="bs-backdrop" aria-hidden="true" @click="close"></div>
        <section
          ref="sheet"
          class="bs-sheet"
          :class="{ tall }"
          role="dialog"
          aria-modal="true"
          :aria-label="title || 'Panel'"
          :style="dragY ? { transform: `translateY(${dragY}px)`, transition: 'none' } : null"
        >
          <div class="bs-grip" @touchstart.passive="onTouchStart" @touchmove.passive="onTouchMove" @touchend="onTouchEnd">
            <span class="bs-handle" aria-hidden="true"></span>
          </div>
          <header v-if="title" class="bs-head">
            <h3>{{ title }}</h3>
            <button type="button" class="bs-close" aria-label="Cerrar" @click="close"><AppIcon name="x" :size="18" /></button>
          </header>
          <div class="bs-body"><slot /></div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.bs-root { position: fixed; inset: 0; z-index: 90; }
.bs-backdrop { position: absolute; inset: 0; background: rgba(8, 10, 14, .5); }
.bs-sheet { position: absolute; left: 0; right: 0; bottom: 0; max-height: 62dvh; display: flex; flex-direction: column; background: var(--sp-card, #fff); color: inherit; border-radius: 20px 20px 0 0; box-shadow: 0 -12px 40px -12px rgba(0, 0, 0, .35); overscroll-behavior: contain; padding-bottom: env(safe-area-inset-bottom, 0px); }
.bs-sheet.tall { max-height: 85dvh; }
.bs-grip { padding: 10px 0 6px; touch-action: none; cursor: grab; flex: none; }
.bs-handle { display: block; width: 36px; height: 4px; margin-inline: auto; border-radius: 99px; background: color-mix(in srgb, currentColor 24%, transparent); }
.bs-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 4px 20px 12px; border-bottom: 1px solid color-mix(in srgb, currentColor 10%, transparent); flex: none; }
.bs-head h3 { margin: 0; font-size: 17px; }
.bs-close { display: grid; place-items: center; width: 40px; height: 40px; border: 0; border-radius: 50%; background: transparent; color: inherit; cursor: pointer; }
.bs-body { overflow-y: auto; padding: 16px 20px 24px; }
.bs-enter-active, .bs-leave-active { transition: opacity .22s ease; }
.bs-enter-active .bs-sheet { transition: transform .3s cubic-bezier(.2, .8, .2, 1); }
.bs-leave-active .bs-sheet { transition: transform .2s ease-in; }
.bs-enter-from, .bs-leave-to { opacity: 0; }
.bs-enter-from .bs-sheet, .bs-leave-to .bs-sheet { transform: translateY(100%); }
@media (prefers-reduced-motion: reduce) {
  .bs-enter-active, .bs-leave-active, .bs-enter-active .bs-sheet, .bs-leave-active .bs-sheet { transition: none; }
}
@media (min-width: 768px) {
  .bs-sheet { left: 50%; right: auto; bottom: auto; top: 50%; width: min(520px, 92vw); transform: translate(-50%, -50%); border-radius: 20px; max-height: 80dvh; }
  .bs-grip { display: none; }
  .bs-enter-from .bs-sheet, .bs-leave-to .bs-sheet { transform: translate(-50%, -42%); }
}
</style>
