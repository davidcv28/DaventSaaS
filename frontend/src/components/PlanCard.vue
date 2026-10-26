<script setup>
import { computed } from 'vue'
import { formatARS } from '../api/billing.api.js'
import AppIcon from './AppIcon.vue'

const props = defineProps({
  plan: { type: Object, required: true },
  current: { type: Boolean, default: false },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])

const b = computed(() => props.plan.benefits || {})

// Medallón por nivel: la prueba regala, el avanzado corona, el medio despega.
const tierIcon = computed(() => {
  if (props.plan.is_trial) return 'gift'
  if (b.value.has_design_advanced) return 'crown'
  if (b.value.has_design_plus) return 'rocket'
  return 'zap'
})

// Ventajas clave en chips con ícono, las más vendedoras primero (máx. 5).
const perks = computed(() => {
  const v = b.value
  const list = []
  if ('max_products' in v) list.push({ icon: 'package', text: v.max_products == null ? 'Productos ilimitados' : `Hasta ${v.max_products} productos` })
  if (v.max_gallery_images) list.push({ icon: 'images', text: `${v.max_gallery_images} fotos` })
  if (v.has_design_advanced) list.push({ icon: 'palette', text: 'Diseños premium' })
  else if (v.has_design_plus) list.push({ icon: 'layout-grid', text: 'Diseños extra' })
  if (v.has_discounts) list.push({ icon: 'percent', text: 'Descuentos' })
  if (v.has_product_comments) list.push({ icon: 'star', text: 'Opiniones' })
  if (v.has_flyers) list.push({ icon: 'megaphone', text: 'Folletos y QR' })
  else if (v.has_qr) list.push({ icon: 'qr-code', text: 'Código QR' })
  if (v.has_chatbot) list.push({ icon: 'bot', text: 'Chatbot' })
  if (v.has_stats) list.push({ icon: 'trending-up', text: 'Estadísticas' })
  return list.slice(0, 5)
})
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
    <div v-if="perks.length" class="plan-perks">
      <span v-for="p in perks" :key="p.text" class="plan-perk"><AppIcon :name="p.icon" :size="12" /> {{ p.text }}</span>
    </div>
    <details v-if="plan.bullets?.length" class="plan-more">
      <summary>Todo lo que incluye <AppIcon name="chevron-down" :size="13" /></summary>
      <ul class="features">
        <li v-for="f in plan.bullets" :key="f"><AppIcon name="check" :size="15" :stroke="2.4" /> <span>{{ f }}</span></li>
      </ul>
    </details>
    <button class="btn" :class="current || plan.is_trial ? 'ghost' : ''" :disabled="current || busy || plan.is_trial" @click="emit('select', plan)">
      <span v-if="busy" class="spinner" aria-hidden="true"></span>
      {{ current ? 'Plan actual' : (plan.cta_label || 'Elegir plan') }}
      <AppIcon v-if="!current && !plan.is_trial && !busy" name="arrow-right" :size="15" />
    </button>
  </div>
</template>
