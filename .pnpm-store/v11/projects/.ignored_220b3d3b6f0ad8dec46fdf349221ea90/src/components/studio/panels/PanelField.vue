<script setup>
// Envoltura de campo compartida por los paneles del Studio: etiqueta +
// tooltip "¿Qué es esto?" (TipHint), badge de plan cuando el control está
// bloqueado e `inert` sobre el cuerpo para que ni mouse ni teclado lo editen.
// `need`: 'plus' = Estándar+ (containers.radius/density), 'advanced' = Premium.
import { computed } from 'vue'
import AppIcon from '../../AppIcon.vue'
import TipHint from '../../TipHint.vue'

const props = defineProps({
  label: { type: String, required: true },
  tip: { type: String, default: '' },
  hint: { type: String, default: '' },
  focus: { type: String, default: '' },
  need: { type: String, default: 'advanced' },
  benefits: { type: Object, default: () => ({}) }
})
const locked = computed(() => {
  if (props.need === 'none') return false
  return props.need === 'plus' ? !props.benefits?.has_design_plus : !props.benefits?.has_design_advanced
})
const planLabel = computed(() => props.need === 'plus' ? 'Estándar' : 'Premium')
</script>

<template>
  <div class="stp-field" :class="{ locked }" :data-focus="focus || null">
    <span class="stp-lb">
      <span class="stp-lb-txt">{{ label }}</span>
      <TipHint v-if="tip" :text="tip" />
      <span v-if="locked" class="lock-badge"><AppIcon name="lock" :size="11" aria-hidden="true" /> {{ planLabel }}</span>
    </span>
    <div class="stp-field-body" :inert="locked || null" :aria-disabled="locked">
      <slot />
    </div>
    <small v-if="hint" class="stp-fhint">{{ hint }}</small>
  </div>
</template>
