<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from './AppIcon.vue'

// Burbuja flotante de mensajería estilo Messenger (chat-head): punto de
// presencia, badge de no-leídos y, al tocarla, despliega el contenido del
// slot (panel de contactos/bandeja o la ventana de conversación) anclado
// sobre ella. Se arrastra con el dedo o el mouse y al soltarla pega a la
// arista horizontal más cercana — la posición queda guardada.
const props = defineProps({
  // 'panel' (lista de contactos/conversaciones) | 'win' (conversación) | null
  content: { type: String, default: null },
  online: { type: Boolean, default: false },
  unread: { type: Number, default: 0 },
  minimized: { type: Boolean, default: false },
  label: { type: String, default: 'Mensajes de soporte' }
})
const emit = defineEmits(['toggle'])

const SIZE = 56 // alto/ancho de la burbuja en px (coincide con .dock-fab)
const EDGE = 18

const vw = ref(window.innerWidth)
const vh = ref(window.innerHeight)
const pos = ref(null) // {x, y} top-left en px; null = esquina por CSS (aún no medido)
const dragging = ref(false)

const clampPos = (p) => ({
  x: Math.min(Math.max(8, p.x), vw.value - SIZE - 8),
  y: Math.min(Math.max(64, p.y), vh.value - SIZE - 8)
})
const defaultPos = () => ({ x: vw.value - SIZE - EDGE, y: vh.value - SIZE - EDGE })
const cur = () => pos.value || defaultPos()

function onResize() {
  vw.value = window.innerWidth
  vh.value = window.innerHeight
  if (pos.value) pos.value = clampPos(pos.value)
}

onMounted(() => {
  let saved = null
  try { saved = JSON.parse(localStorage.getItem('davent:chat-dock') || 'null') } catch { /* storage bloqueado */ }
  pos.value = clampPos(saved && Number.isFinite(saved.x) && Number.isFinite(saved.y) ? saved : defaultPos())
  window.addEventListener('resize', onResize, { passive: true })
})
onBeforeUnmount(() => window.removeEventListener('resize', onResize))

// Lado donde quedó anclada: el contenido se alinea a esa misma arista.
const side = computed(() => (cur().x + SIZE / 2 > vw.value / 2 ? 'right' : 'left'))

// Caja anclada sobre la burbuja (o debajo si no hay lugar arriba). 'win'
// lleva alto fijo (la ventana crece hasta él); 'panel' es auto con tope.
const boxStyle = computed(() => {
  const gap = 12
  const p = cur()
  const above = p.y - gap - 8
  const below = vh.value - (p.y + SIZE + gap) - 8
  const useAbove = above >= 260 || above >= below
  const avail = Math.max(160, useAbove ? above : below)
  const s = { width: Math.min(390, vw.value - 36) + 'px' }
  if (side.value === 'right') s.right = EDGE + 'px'
  else s.left = EDGE + 'px'
  if (useAbove) s.bottom = `${vh.value - p.y + gap}px`
  else s.top = `${p.y + SIZE + gap}px`
  if (props.content === 'win') s.height = props.minimized ? 'auto' : `${Math.min(560, avail)}px`
  else s.maxHeight = `${Math.min(430, avail)}px`
  return s
})

const fabStyle = computed(() => {
  const p = cur()
  return pos.value ? { left: `${p.x}px`, top: `${p.y}px` } : {}
})

// --- Arrastre (Pointer Events: mouse + touch). >6px se considera drag, no
// tap; al soltar, la burbuja pega a la arista horizontal más cercana. ---
let drag = null
let eatClick = false

function onDown(e) {
  if (e.button !== undefined && e.button !== 0) return
  drag = { px: e.clientX, py: e.clientY, moved: false }
  e.currentTarget.setPointerCapture?.(e.pointerId)
}

function onMove(e) {
  if (!drag) return
  const dx = e.clientX - drag.px
  const dy = e.clientY - drag.py
  if (!drag.moved && Math.hypot(dx, dy) <= 6) return
  if (!drag.moved) { drag.moved = true; dragging.value = true }
  drag.px = e.clientX
  drag.py = e.clientY
  pos.value = clampPos({ x: pos.value.x + dx, y: pos.value.y + dy })
}

function endDrag() {
  if (!drag) return
  if (drag.moved) {
    eatClick = true
    const p = pos.value
    pos.value = clampPos({ x: p.x + SIZE / 2 > vw.value / 2 ? vw.value - SIZE - EDGE : EDGE, y: p.y })
    try { localStorage.setItem('davent:chat-dock', JSON.stringify(pos.value)) } catch { /* storage bloqueado */ }
  }
  drag = null
  dragging.value = false
}

// El tap llega como click (teclado incluido); tras un drag se descarta.
function onClick() {
  if (eatClick) { eatClick = false; return }
  emit('toggle')
}
</script>

<template>
  <div class="chat-dock" :class="{ left: side === 'left', dragging }">
    <div v-if="content" class="chat-dock-box" :class="[content, { min: minimized }]" :style="boxStyle">
      <slot />
    </div>
    <button
      type="button"
      class="dock-fab"
      :class="{ on: online, dragging }"
      :style="fabStyle"
      :aria-label="label"
      :aria-expanded="!!content"
      @pointerdown="onDown"
      @pointermove="onMove"
      @pointerup="endDrag"
      @pointercancel="endDrag"
      @click="onClick"
    >
      <AppIcon name="message-circle" :size="24" />
      <span class="dock-status" :class="{ on: online }" aria-hidden="true"></span>
      <span v-if="unread" class="chat-badge dock-badge">{{ unread > 99 ? '99+' : unread }}</span>
    </button>
  </div>
</template>
