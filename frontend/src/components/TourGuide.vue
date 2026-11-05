<script setup>
// Tour de primera vez: 4 pasos con spotlight sobre el menú real. En móvil
// apunta a la tab bar; en desktop al sidebar. Se completa/salta una sola
// vez (localStorage) y se relanza desde "Repetir la guía" en el menú.
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import AppIcon from './AppIcon.vue'

const open = defineModel('open', { type: Boolean, default: false })

const STORAGE_KEY = 'davent:tour:done'

// Cada paso prueba primero el target del sidebar (desktop) y luego el de la
// tab bar (móvil); el que exista en pantalla es el que se ilumina.
const STEPS = [
  {
    sel: '[data-tour="nav-overview"], [data-tour="tab-overview"]',
    title: 'Tu Inicio',
    text: 'Acá está tu negocio hoy: qué hacer ahora, tus números y tu página en vivo.'
  },
  {
    sel: '[data-tour="nav-catalogs"], [data-tour="tab-catalogs"]',
    title: 'Vender',
    text: 'Tus productos, servicios y la venta en persona: todo lo que ofrecés se carga acá.'
  },
  {
    sel: '[data-tour="nav-store"], [data-tour="tab-store"]',
    title: 'Mi web',
    text: 'El diseño de tu página, sus secciones y el link para compartir con tus clientes.'
  },
  {
    sel: '.top-search',
    title: '¿No encontrás algo?',
    text: 'Tocá Buscar (o Ctrl K / “/”) y escribí lo que querés hacer: “logo”, “factura”, “QR”… te lleva directo.'
  }
]

const idx = ref(0)
const spot = ref(null) // {x,y,w,h}
const tipPos = ref({ x: 0, y: 0, below: true })
const step = computed(() => STEPS[idx.value])
const isLast = computed(() => idx.value === STEPS.length - 1)

function finish() {
  try { localStorage.setItem(STORAGE_KEY, '1') } catch {}
  open.value = false
}
function next() {
  if (isLast.value) { finish(); return }
  idx.value += 1
  place()
}
function prev() { idx.value = Math.max(0, idx.value - 1); place() }

function place() {
  nextTick(() => {
    const el = document.querySelector(step.value.sel)
    const pad = 8
    if (!el || !el.getBoundingClientRect().width) {
      // Sin target visible (p.ej. el item no existe en este plan): tooltip centrado.
      spot.value = null
      tipPos.value = { x: window.innerWidth / 2, y: window.innerHeight / 2, below: true, center: true }
      return
    }
    const r = el.getBoundingClientRect()
    spot.value = { x: r.left - pad, y: r.top - pad, w: r.width + pad * 2, h: r.height + pad * 2 }

    // Medir la card real: su alto depende del texto del paso.
    const card = document.querySelector('.tour-card')
    const cw = card?.offsetWidth || 300
    const ch = card?.offsetHeight || 190
    const vw = window.innerWidth
    const vh = window.innerHeight
    const M = 12 // margen mínimo al borde de la pantalla
    const clampX = (x) => Math.min(Math.max(M, x), Math.max(M, vw - cw - M))
    const clampY = (y) => Math.min(Math.max(M, y), Math.max(M, vh - ch - M))
    const fits = (x, y) => x >= M && y >= M && x + cw <= vw - M && y + ch <= vh - M

    let x, y
    if (vw <= 860) {
      // Móvil: probar abajo, arriba, derecha e izquierda del target; gana la
      // primera que entra completa en pantalla. Si ninguna entra (target
      // gigante), se usa la de abajo ya clampeada.
      const cx = r.left + r.width / 2 - cw / 2
      const candidates = [
        [cx, r.bottom + 12],
        [cx, r.top - ch - 12],
        [r.right + 12, r.top + r.height / 2 - ch / 2],
        [r.left - cw - 12, r.top + r.height / 2 - ch / 2]
      ]
      const hit = candidates.find(([px, py]) => fits(px, py))
      if (hit) { x = hit[0]; y = hit[1] }
      else { x = clampX(cx); y = clampY(r.bottom + 12) }
    } else {
      // Desktop: a la derecha del sidebar; si no entra, a la izquierda; si
      // tampoco, debajo del target centrado.
      const sideY = r.top - 8
      if (fits(r.right + 18, sideY)) { x = r.right + 18; y = sideY }
      else if (fits(r.left - cw - 18, sideY)) { x = r.left - cw - 18; y = sideY }
      else { x = clampX(vw / 2 - cw / 2); y = clampY(r.bottom + 12) }
    }
    tipPos.value = { x, y, below: false }
  })
}

function onKey(e) {
  if (!open.value) return
  if (e.key === 'Escape') finish()
  else if (e.key === 'ArrowRight' || e.key === 'Enter') next()
  else if (e.key === 'ArrowLeft') prev()
}
function onResize() { if (open.value) place() }

watch(open, (v) => {
  if (v) { idx.value = 0; nextTick(place); document.body.style.overflow = 'hidden' }
  else document.body.style.overflow = ''
})
onMounted(() => { window.addEventListener('keydown', onKey); window.addEventListener('resize', onResize, { passive: true }) })
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  window.removeEventListener('resize', onResize)
  document.body.style.overflow = ''
})
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="tour" role="dialog" aria-modal="true" :aria-label="`Guía del panel, paso ${idx + 1} de ${STEPS.length}`">
      <div
        class="tour-hole"
        :style="spot ? { left: spot.x + 'px', top: spot.y + 'px', width: spot.w + 'px', height: spot.h + 'px' } : { inset: 0 }"
        aria-hidden="true"
      ></div>
      <div
        class="tour-card"
        :class="{ center: tipPos.center }"
        :style="tipPos.center ? null : { left: tipPos.x + 'px', top: tipPos.y + 'px' }"
        role="document"
      >
        <span class="tour-step">{{ idx + 1 }} / {{ STEPS.length }}</span>
        <h3>{{ step.title }}</h3>
        <p>{{ step.text }}</p>
        <div class="tour-dots" aria-hidden="true">
          <i v-for="(s, i) in STEPS" :key="i" :class="{ on: i === idx }"></i>
        </div>
        <div class="tour-actions">
          <button type="button" class="tour-skip" @click="finish">Saltar</button>
          <span class="tour-spacer"></span>
          <button v-if="idx > 0" type="button" class="btn ghost btn-auto" @click="prev"><AppIcon name="chevron-left" :size="15" /> Atrás</button>
          <button type="button" class="btn btn-auto" autofocus @click="next">{{ isLast ? 'Entendido' : 'Siguiente' }} <AppIcon name="arrow-right" :size="15" /></button>
        </div>
      </div>
    </div>
  </Teleport>
</template>
