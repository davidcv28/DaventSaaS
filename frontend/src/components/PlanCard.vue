<script setup>
import { formatARS } from '../api/billing.api.js'
import AppIcon from './AppIcon.vue'

defineProps({
  plan: { type: Object, required: true },
  current: { type: Boolean, default: false },
  busy: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])
</script>

<template>
  <div class="price-card" :class="{ featured: plan.featured, current, trial: plan.is_trial }">
    <span v-if="plan.is_trial" class="flag trial">10 días gratis</span>
    <span v-else-if="plan.featured" class="flag">Recomendado</span>
    <h3>{{ plan.name }}</h3>
    <p class="tagline">{{ plan.tagline }}</p>
    <p class="price">{{ formatARS(plan.price) }}<small v-if="Number(plan.price) > 0">/mes</small></p>
    <ul class="features">
      <li v-for="f in plan.bullets" :key="f"><AppIcon name="check" :size="16" :stroke="2.4" /> <span>{{ f }}</span></li>
    </ul>
    <button class="btn" :class="current || plan.is_trial ? 'ghost' : ''" :disabled="current || busy || plan.is_trial" @click="emit('select', plan)">
      <span v-if="busy" class="spinner" aria-hidden="true"></span>
      {{ current ? 'Plan actual' : (plan.cta_label || 'Elegir plan') }}
    </button>
  </div>
</template>