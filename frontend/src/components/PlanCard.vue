<script setup>
import { computed } from 'vue'
import { formatARS } from '../api/billing.api.js'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  plan: { type: Object, required: true },
  prev: { type: Object, default: null },
  current: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  paymentsOff: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])

const b = computed(() => props.plan.benefits || {})
const bPrev = computed(() => props.prev?.benefits || null)

// Ventaja sobre el plan anterior: flag que el anterior no tiene, o tope más
// alto (None = ilimitado, siempre mejora salvo que el anterior también lo sea).
function improves(key, val) {
  if (!bPrev.value) return false
  const pv = bPrev.value[key]
  if (val === true) return pv !== true
  if (val == null) return pv !== null && key in bPrev.value
  if (typeof val === 'number') return pv == null ? false : val > pv
  return false
}

// Medallón por nivel: la prueba regala, el avanzado corona, el medio despega.
const tierIcon = computed(() => {
  if (props.plan.is_trial) return 'gift'
  if (b.value.has_design_advanced) return 'crown'
  if (b.value.has_design_plus) return 'rocket'
  return 'zap'
})

// Ventajas clave en chips con ícono, las más vendedoras primero (máx. 5).
// `up` marca las que mejoran respecto del plan anterior (`prev`).
const perks = computed(() => {
  const v = b.value
  const list = []
  const add = (key, icon, text) => list.push({ icon, text, up: improves(key, v[key]) })
  if ('max_products' in v) add('max_products', 'package', v.max_products == null ? 'Productos ilimitados' : `Hasta ${v.max_products} productos`)
  if (v.max_gallery_images) add('max_gallery_images', 'images', `${v.max_gallery_images} fotos`)
  if (v.max_videos) add('max_videos', 'play', `${v.max_videos} videos`)
  if (v.has_design_advanced) add('has_design_advanced', 'palette', 'Diseños premium')
  else if (v.has_design_plus) add('has_design_plus', 'layout-grid', 'Diseños extra')
  if (v.has_discounts) add('has_discounts', 'percent', 'Descuentos')
  if (v.has_product_comments) add('has_product_comments', 'star', 'Opiniones')
  if (v.has_flyer_editor) add('has_flyer_editor', 'pen-tool', 'Editor de folletos')
  else if (v.has_flyers) add('has_flyers', 'megaphone', 'Folletos y QR')
  else if (v.has_qr) add('has_qr', 'qr-code', 'Código QR')
  if (v.has_chatbot) add('has_chatbot', 'bot', 'Chatbot')
  if (v.has_stats) add('has_stats', 'trending-up', 'Estadísticas')
  return list.slice(0, 5)
})
const upsCount = computed(() => perks.value.filter((p) => p.up).length)
</script>

<template>
  <div class="price-card" :class="{ featured: plan.featured, current, trial: plan.is_trial }">
    <span v-if="plan.is_trial" class="flag trial">1 día gratis</span>
    <span v-else-if="plan.featured" class="flag">Recomendado</span>
    <div class="plan-head">
      <span class="plan-medal" aria-hidden="true"><AppIcon :name="tierIcon" :size="18" /></span>
      <div class="plan-title">
        <h3>{{ plan.name }}</h3>
        <p class="tagline">{{ plan.tagline }}</p>
      </div>
      <p class="price">{{ formatARS(plan.price) }}<small v-if="Number(plan.price) > 0">/mes</small></p>
    </div>
    <p v-if="prev && upsCount" class="plan-vs"><AppIcon name="plus" :size="11" /> Ventajas sobre {{ prev.name }}</p>
    <div v-if="perks.length" class="plan-perks">
      <span v-for="p in perks" :key="p.text" class="plan-perk" :class="{ up: p.up }"><AppIcon :name="p.icon" :size="12" /> {{ p.text }}</span>
    </div>
    <details v-if="plan.bullets?.length" class="plan-more">
      <summary>Todo lo que incluye <AppIcon name="chevron-down" :size="13" /></summary>
      <ul class="features">
        <li v-for="f in plan.bullets" :key="f"><AppIcon name="check" :size="15" :stroke="2.4" /> <span>{{ f }}</span></li>
      </ul>
    </details>
    <button class="btn" :class="current || plan.is_trial ? 'ghost' : ''" :disabled="current || busy || plan.is_trial || paymentsOff" @click="emit('select', plan)">
      <span v-if="busy" class="spinner" aria-hidden="true"></span>
      {{ current ? 'Plan actual' : (paymentsOff && !plan.is_trial ? 'Próximamente' : (plan.cta_label || 'Elegir plan')) }}
      <AppIcon v-if="!current && !plan.is_trial && !busy && !paymentsOff" name="arrow-right" :size="15" />
    </button>
  </div>
</template>
