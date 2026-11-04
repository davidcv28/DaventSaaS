<script setup>
import { computed, ref } from 'vue'
import { sizeById } from '../utils/flyer.js'
import { fillOf } from '../utils/flyerEditor.js'
import FlyerElement from './FlyerElement.vue'
import AppIcon from './AppIcon.vue'

// Lienzo del folleto libre: fondo + elementos absolutos en % con rotación.
// `container-type: inline-size` habilita cqw, así el mismo documento sirve
// para la vista previa, la imposición de impresión y el PNG exportado.
// Con `interactive` el propio lienzo gestiona selección, arrastre,
// redimensionado por esquinas y rotación (los objetos del doc se mutan en
// vivo; emite 'mutate' antes del gesto y 'commit' al soltar para el
// historial del editor).
const props = defineProps({
  doc: { type: Object, required: true },
  qr: { type: String, default: '' },
  logo: { type: String, default: '' },
  shopName: { type: String, default: '' },
  url: { type: String, default: '' },
  products: { type: Array, default: () => [] },
  selected: { type: String, default: '' },
  interactive: { type: Boolean, default: false }
})
const emit = defineEmits(['select', 'mutate', 'commit'])

const root = ref(null)
defineExpose({ el: root })

const aspectRatio = computed(() => {
  const s = sizeById(props.doc.size)
  return `${s.w} / ${s.h}`
})
const els = computed(() => (props.doc.elements || []).filter((e) => !e.hidden))
const sel = computed(() => els.value.find((e) => e.id === props.selected) || null)
const elStyle = (el) => ({
  left: `${el.x}%`, top: `${el.y}%`, width: `${el.w}%`, height: `${el.h}%`,
  transform: `rotate(${el.rot || 0}deg)`, opacity: el.opacity ?? 1
})

// Guías de alineación mientras se arrastra: centro del lienzo, bordes y
// bordes/centros de los demás elementos. El imán se apaga con Alt.
const guides = ref({ x: null, y: null })
const SNAP = 1.1

function snapAxis(value, size, others, axis) {
  const cross = axis === 'x' ? 'w' : 'h'
  const candidates = [
    { pos: 0, line: 0 },
    { pos: (100 - size) / 2, line: 50 },
    { pos: 100 - size, line: 100 }
  ]
  for (const o of others) {
    const start = o[axis]
    const end = start + o[cross]
    candidates.push(
      { pos: start, line: start },
      { pos: start + (o[cross] - size) / 2, line: start + o[cross] / 2 },
      { pos: end - size, line: end }
    )
  }
  let best = null
  for (const c of candidates) {
    const d = Math.abs(value - c.pos)
    if (d <= SNAP && (!best || d < best.d)) best = { ...c, d }
  }
  return best ? { value: best.pos, line: best.line } : { value, line: null }
}

const rad = (d) => (d * Math.PI) / 180
const rotVec = (x, y, deg) => {
  const a = rad(deg)
  return { x: x * Math.cos(a) - y * Math.sin(a), y: x * Math.sin(a) + y * Math.cos(a) }
}

function pick(el, ev) {
  emit('select', el.id)
  if (!props.interactive || el.locked) return
  ev.preventDefault()
  const rect = root.value.getBoundingClientRect()
  const start = { x: ev.clientX, y: ev.clientY }
  const orig = { x: el.x, y: el.y }
  let moved = false
  const move = (e) => {
    if (!moved) { moved = true; emit('mutate') }
    let nx = orig.x + ((e.clientX - start.x) / rect.width) * 100
    let ny = orig.y + ((e.clientY - start.y) / rect.height) * 100
    nx = Math.min(100 - 2, Math.max(2 - el.w, nx))
    ny = Math.min(100 - 2, Math.max(2 - el.h, ny))
    const others = els.value.filter((o) => o.id !== el.id)
    if (!e.altKey) {
      const sx = snapAxis(nx, el.w, others, 'x')
      const sy = snapAxis(ny, el.h, others, 'y')
      nx = sx.value
      ny = sy.value
      guides.value = { x: sx.line, y: sy.line }
    } else {
      guides.value = { x: null, y: null }
    }
    el.x = Math.round(nx * 10) / 10
    el.y = Math.round(ny * 10) / 10
  }
  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    guides.value = { x: null, y: null }
    if (moved) emit('commit')
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}

// Redimensionar desde una esquina: la esquina opuesta queda fija y el
// vector del puntero se des-rota al marco local del elemento.
function startResize(el, corner, ev) {
  ev.preventDefault()
  ev.stopPropagation()
  const rect = root.value.getBoundingClientRect()
  const cw = rect.width / 100
  const ch = rect.height / 100
  const sx = corner.includes('e') ? 1 : -1
  const sy = corner.includes('s') ? 1 : -1
  const fixedLocal = { x: -sx * (el.w / 2) * cw, y: -sy * (el.h / 2) * ch }
  const center = { x: (el.x + el.w / 2) * cw, y: (el.y + el.h / 2) * ch }
  const fixed = rotVec(fixedLocal.x, fixedLocal.y, el.rot || 0)
  fixed.x += center.x
  fixed.y += center.y
  emit('mutate')
  const move = (e) => {
    const v = { x: e.clientX - rect.left - fixed.x, y: e.clientY - rect.top - fixed.y }
    const l = rotVec(v.x, v.y, -(el.rot || 0))
    const w = Math.max(2, (l.x * sx) / cw)
    const h = Math.max(1, (l.y * sy) / ch)
    const nc = rotVec(l.x / 2, l.y / 2, el.rot || 0)
    el.w = Math.round(w * 10) / 10
    el.h = Math.round(h * 10) / 10
    el.x = Math.round(((fixed.x + nc.x) / cw - el.w / 2) * 10) / 10
    el.y = Math.round(((fixed.y + nc.y) / ch - el.h / 2) * 10) / 10
  }
  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    emit('commit')
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}

function startRotate(el, ev) {
  ev.preventDefault()
  ev.stopPropagation()
  const rect = root.value.getBoundingClientRect()
  const center = { x: rect.left + ((el.x + el.w / 2) / 100) * rect.width, y: rect.top + ((el.y + el.h / 2) / 100) * rect.height }
  emit('mutate')
  const move = (e) => {
    let deg = (Math.atan2(e.clientY - center.y, e.clientX - center.x) * 180) / Math.PI + 90
    if (e.shiftKey) deg = Math.round(deg / 15) * 15
    el.rot = Math.round(deg)
  }
  const up = () => {
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', up)
    emit('commit')
  }
  window.addEventListener('pointermove', move)
  window.addEventListener('pointerup', up)
}
</script>

<template>
  <div ref="root" class="fb" :class="{ 'fb-edit': interactive }" :style="{ aspectRatio, background: fillOf(doc.bg) }" @pointerdown.self="emit('select', null)">
    <div
      v-for="el in els" :key="el.id"
      class="fb-el" :class="{ sel: interactive && el.id === selected, locked: el.locked }"
      :style="elStyle(el)"
      @pointerdown="pick(el, $event)"
    >
      <FlyerElement :el="el" :qr="qr" :logo="logo" :shop-name="shopName" :url="url" :products="products" />
      <span v-if="interactive && el.locked" class="fb-lock"><AppIcon name="lock" :size="10" /></span>
    </div>

    <template v-if="interactive">
      <i v-if="guides.x !== null" class="fb-guide v" :style="{ left: `${guides.x}%` }" aria-hidden="true"></i>
      <i v-if="guides.y !== null" class="fb-guide h" :style="{ top: `${guides.y}%` }" aria-hidden="true"></i>
      <div v-if="sel" class="fb-sel" :style="elStyle(sel)" aria-hidden="true">
        <button v-for="c in ['nw', 'ne', 'sw', 'se']" :key="c" type="button" class="fb-h" :class="`fb-h-${c}`" @pointerdown="startResize(sel, c, $event)"></button>
        <button v-if="!sel.locked" type="button" class="fb-rot" @pointerdown="startRotate(sel, $event)"><AppIcon name="rotate-cw" :size="'1em'" /></button>
      </div>
    </template>
  </div>
</template>

<style>
.fb { container-type: inline-size; position: relative; width: 100%; overflow: hidden; color: #0f172a; font-family: var(--store-font, Inter, system-ui, sans-serif); -webkit-print-color-adjust: exact; print-color-adjust: exact; user-select: none; }
.fb-el { position: absolute; }
.fb-edit .fb-el { cursor: grab; touch-action: none; }
.fb-edit .fb-el:active { cursor: grabbing; }
.fb-edit .fb-el.locked { cursor: default; }
.fb-lock { position: absolute; top: 1cqw; right: 1cqw; width: 3.6cqw; height: 3.6cqw; min-width: 14px; min-height: 14px; display: grid; place-items: center; border-radius: 50%; background: rgba(15, 23, 42, .7); color: #fff; z-index: 3; }
.fb-guide { position: absolute; z-index: 4; background: var(--store-accent, #6366f1); pointer-events: none; }
.fb-guide.v { left: 50%; top: 0; bottom: 0; width: .35cqw; }
.fb-guide.h { top: 50%; left: 0; right: 0; height: .35cqw; }
.fb-sel { position: absolute; z-index: 5; outline: .35cqw solid var(--store-accent, #6366f1); pointer-events: none; }
.fb-h { position: absolute; width: 2.8cqw; height: 2.8cqw; min-width: 12px; min-height: 12px; max-width: 20px; max-height: 20px; border-radius: 50%; background: #fff; border: .45cqw solid var(--store-accent, #6366f1); pointer-events: auto; padding: 0; cursor: nwse-resize; }
.fb-h-nw { left: -1.4cqw; top: -1.4cqw; }
.fb-h-ne { right: -1.4cqw; top: -1.4cqw; cursor: nesw-resize; }
.fb-h-sw { left: -1.4cqw; bottom: -1.4cqw; cursor: nesw-resize; }
.fb-h-se { right: -1.4cqw; bottom: -1.4cqw; }
.fb-rot { position: absolute; left: 50%; top: -7cqw; transform: translateX(-50%); width: 4.6cqw; height: 4.6cqw; min-width: 24px; min-height: 24px; max-width: 34px; max-height: 34px; border-radius: 50%; display: grid; place-items: center; font-size: 2.4cqw; background: var(--store-accent, #6366f1); color: #fff; border: none; pointer-events: auto; cursor: grab; padding: 0; }
</style>
