<script setup>
// Cuenta regresiva (§6.5-10): placa de tinta con números tabulares gigantes,
// solo si hay un descuento vigente con vencimiento. Respeta reduced-motion:
// solo cuenta, sin animaciones.
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { productDiscount } from '../../../../api/catalog.api.js'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'
import { useRhLinks } from './rhLinks.js'

defineProps({ block: { type: Object, default: null } })

const { ctx, catalogTo } = useRhLinks()
const { custom, showCatalog } = ctx
const { featured } = useFeaturedCatalog()

// El descuento vigente que vence primero conduce la cuenta.
const next = computed(() => {
  let best = null
  for (const p of featured.value.products) {
    const d = productDiscount(p)
    const time = Date.parse(d?.ends_at || '')
    if (!d || !Number.isFinite(time) || time <= Date.now()) continue
    if (!best || time < best.time) best = { name: d.name, percent: d.percent, time }
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
  <section v-if="showCatalog && show" class="rz-section rh-numbered rh-countdown" aria-labelledby="rh-countdown-title">
    <div class="rh-wrap">
      <div v-reveal class="rh-cd rz-band">
        <div class="rh-cd-copy">
          <p class="rz-eyebrow rh-cd-eyebrow">
            <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
            Oferta por tiempo limitado
          </p>
          <h2 id="rh-countdown-title" class="rh-cd-title">
            {{ next.name }}<template v-if="next.percent"> <span class="rh-cd-pct">-{{ next.percent }}%</span></template>
          </h2>
          <RouterLink class="rz-btn rh-cd-btn" :to="catalogTo">
            Aprovechar ahora <AppIcon name="arrow-right" :size="16" />
          </RouterLink>
        </div>
        <div class="rh-cd-clock" role="timer" aria-label="Tiempo restante de la oferta">
          <div v-if="left.d" class="rh-cd-unit"><strong>{{ pad(left.d) }}</strong><span>días</span></div>
          <div class="rh-cd-unit"><strong>{{ pad(left.h) }}</strong><span>horas</span></div>
          <div class="rh-cd-unit"><strong>{{ pad(left.m) }}</strong><span>min</span></div>
          <div class="rh-cd-unit"><strong>{{ pad(left.s) }}</strong><span>seg</span></div>
        </div>
      </div>
    </div>
  </section>
</template>
