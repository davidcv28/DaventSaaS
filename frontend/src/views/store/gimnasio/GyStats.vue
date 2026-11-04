<script setup>
// Cifras del club: banda de datos con contador animado (solo la primera vez
// que entra en pantalla), barra proporcional al valor real y etiqueta mono.
// Si el dueño no cargó `stats`, se derivan cifras verificables (años,
// disciplinas, membresías, fotos) en vez de inventar números.
import { computed, inject, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({
  block: { type: Object, default: null },
  sectionIndex: { type: Number, default: 0 }
})

const ctx = inject('storePage')
const { custom } = ctx

const reduceMotion = typeof window !== 'undefined'
  && window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches

const rows = computed(() => {
  const own = Array.isArray(custom.value.stats) ? custom.value.stats : []
  if (own.length) return own.filter((s) => String(s?.value ?? '').trim()).slice(0, 6)
  const derived = []
  if (custom.value.about_years) derived.push({ value: `+${custom.value.about_years}`, label: 'años entrenando' })
  if (custom.value.services?.length) derived.push({ value: String(custom.value.services.length), label: 'disciplinas' })
  if (custom.value.plans?.length) derived.push({ value: String(custom.value.plans.length), label: 'membresías' })
  if (custom.value.gallery?.length) derived.push({ value: String(custom.value.gallery.length), label: 'fotos de la sala' })
  return derived
})
const show = computed(() => custom.value.show_stats !== false && rows.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || '')

// Separa prefijo/sufijo del número para animar solo la parte numérica.
function parseStat(raw) {
  const text = String(raw ?? '')
  const m = text.match(/^(\D*)(\d+(?:[.,]\d+)?)(.*)$/)
  if (!m) return null
  const numeric = m[2].replace(',', '.')
  const decimals = numeric.includes('.') && numeric.split('.')[1].length > 2 ? 0 : (numeric.split('.')[1]?.length || 0)
  const target = Number(numeric)
  if (!Number.isFinite(target)) return null
  return { prefix: m[1], target, decimals, suffix: m[3] }
}

const parsed = computed(() => rows.value.map((s) => parseStat(s.value)))
const maxValue = computed(() => Math.max(1, ...parsed.value.filter(Boolean).map((p) => p.target)))
const display = ref(rows.value.map((s) => String(s.value ?? '')))

function settle() {
  display.value = rows.value.map((s) => String(s.value ?? ''))
}
function animate() {
  if (reduceMotion) { settle(); return }
  const now = performance.now()
  const frames = rows.value.map((s, i) => {
    const p = parsed.value[i]
    if (!p) return null
    return { p, start: now + i * 90, dur: 900 + i * 60, index: i }
  })
  const step = (t) => {
    let pending = false
    frames.forEach((f) => {
      if (!f) return
      const k = Math.min(1, Math.max(0, (t - f.start) / f.dur))
      if (k < 1) pending = true
      const eased = 1 - Math.pow(1 - k, 3)
      const value = f.p.target * eased
      display.value[f.index] = `${f.p.prefix}${value.toFixed(f.p.decimals)}${f.p.suffix}`
    })
    if (pending) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

const root = ref(null)
let observer = null
onMounted(() => {
  if (reduceMotion || !('IntersectionObserver' in window) || !root.value) { settle(); return }
  observer = new IntersectionObserver((entries) => {
    if (!entries.some((e) => e.isIntersecting)) return
    observer.disconnect()
    animate()
  }, { threshold: 0.35 })
  observer.observe(root.value)
})
watch(rows, settle)
onBeforeUnmount(() => observer?.disconnect())
</script>

<template>
  <section v-if="show" ref="root" class="gy-stats" aria-label="Cifras del club">
    <div class="gy-wrap gy-stats-inner">
      <header v-reveal class="gy-stats-head">
        <p class="gy-eyebrow"><span class="gy-eyebrow-idx">{{ String(sectionIndex || 1).padStart(2, '0') }}</span> En números</p>
        <h2 v-if="title" class="gy-stats-title">{{ title }}</h2>
      </header>
      <div class="gy-stats-grid">
        <div
          v-for="(s, i) in rows" :key="i" v-reveal="(i % 4) * 70"
          class="gy-stat" :class="{ 'is-wide': String(s.value).length > 7 }"
        >
          <span class="gy-stat-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <b class="gy-stat-value">{{ display[i] ?? s.value }}</b>
          <span class="gy-stat-label">{{ s.label }}</span>
          <span class="gy-stat-track" aria-hidden="true">
            <i :style="{ width: `${Math.max(14, Math.round(((parsed[i]?.target || 0) / maxValue) * 100))}%` }"></i>
          </span>
        </div>
      </div>
    </div>
  </section>
</template>
