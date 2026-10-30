<script setup>
import { computed } from 'vue'
import { passwordChecks, passwordScore } from '../validators/auth.validators.js'
import AppIcon from './AppIcon.vue'

const props = defineProps({ value: { type: String, default: '' } })
const checks = computed(() => passwordChecks(props.value || ''))
const score = computed(() => passwordScore(props.value || ''))
const label = computed(() => {
  if (!props.value) return 'Escribe tu contraseña'
  if (score.value <= 2) return 'Débil'
  if (score.value === 3) return 'Aceptable'
  if (score.value === 4) return 'Fuerte'
  return 'Excelente'
})
</script>

<template>
  <div>
    <div class="strength" aria-live="polite">
      <i v-for="n in 5" :key="n" :class="n <= score ? `on-${score}` : ''"></i>
      <small>{{ label }} ({{ score }}/5)</small>
    </div>
    <ul class="checks">
      <li v-for="c in checks" :key="c.label" :class="{ ok: c.ok }">
        <AppIcon :name="c.ok ? 'check' : 'dot'" :size="c.ok ? 14 : 10" :stroke="2.4" /> {{ c.label }}
      </li>
    </ul>
  </div>
</template>
