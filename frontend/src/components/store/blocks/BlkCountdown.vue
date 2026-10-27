<script setup>
// Bloque 'countdown': cuenta regresiva automática hacia el fin del
// descuento vigente más próximo (product.discount.ends_at del catálogo).
// Sin ofertas con vencimiento se auto-oculta. Se apaga con
// show_countdown. Respeta reduced-motion: solo cuenta, sin animaciones.
import { ref, computed, inject, onMounted, onBeforeUnmount } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { productDiscount } from '../../../api/catalog.api.js'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, showCatalog } = ctx
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
// El descuento vigente que vence primero conduce la cuenta.
const next = computed(() => {
  let best = null
  for (const p of shopCatalog.value.products) {
    const d = productDiscount(p)
    const t = Date.parse(d?.ends_at || '')
    if (!d || !Number.isFinite(t) || t <= Date.now()) continue
    if (!best || t < best.time) best = { name: d.name, percent: d.percent, time: t }
  }
  return best
})
const show = computed(() => custom.value.show_countdown !== false && Boolean(next.value))

const now = ref(Date.now())
let clock = null
const left = computed(() => {
  const ms = Math.max(0, (next.value?.time || 0) - now.value)
  const s = Math.floor(ms / 1000)
  return {
    d: Math.floor(s / 86400),
    h: Math.floor((s % 86400) / 3600),
    m: Math.floor((s % 3600) / 60),
    s: s % 60
  }
})
const pad = (n) => String(n).padStart(2, '0')

onMounted(() => { clock = setInterval(() => { now.value = Date.now() }, 1000) })
onBeforeUnmount(() => clearInterval(clock))
</script>

<template>
  <section v-if="showCatalog && show" class="sp-countdown" aria-labelledby="sp-countdown-title">
    <div class="sp-container">
      <div v-reveal class="sp-cd-inner">
        <div class="sp-cd-copy">
          <p class="sp-cd-eyebrow"><AppIcon name="zap" :size="14" /> Oferta por tiempo limitado</p>
          <h2 id="sp-countdown-title" class="sp-cd-title">{{ next.name }}<template v-if="next.percent"> · -{{ next.percent }}%</template></h2>
        </div>
        <div class="sp-cd-clock" role="timer" aria-label="Tiempo restante de la oferta">
          <div v-if="left.d" class="sp-cd-unit"><strong>{{ pad(left.d) }}</strong><span>días</span></div>
          <div class="sp-cd-unit"><strong>{{ pad(left.h) }}</strong><span>horas</span></div>
          <div class="sp-cd-unit"><strong>{{ pad(left.m) }}</strong><span>min</span></div>
          <div class="sp-cd-unit"><strong>{{ pad(left.s) }}</strong><span>seg</span></div>
        </div>
        <RouterLink class="sp-btn sp-cd-btn" :to="catalogTo">Aprovechar ahora <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
      </div>
    </div>
  </section>
</template>
