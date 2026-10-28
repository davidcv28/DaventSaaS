<script setup>
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  modelValue: { type: String, default: 'auto' },
  hasLogo: { type: Boolean, default: false }
})
const emit = defineEmits(['update:modelValue'])

const OPTIONS = [
  { id: 'foto', label: 'Una foto mía', icon: 'camera', desc: 'La foto la cargás en “Cómo se ve”.' },
  { id: 'logo', label: 'Mi logo', icon: 'image', desc: 'La portada muestra tu logo o tus iniciales.' },
  { id: 'auto', label: 'Que decida la IA', icon: 'sparkles', desc: 'Elegimos lo que mejor le queda a tu negocio.' }
]
const current = () => (OPTIONS.some((o) => o.id === props.modelValue) ? props.modelValue : 'auto')
function desc(o) {
  if (o.id === 'logo' && !props.hasLogo) return 'Todavía no cargaste un logo: podés subirlo en “Cómo se ve”.'
  return o.desc
}
</script>

<template>
  <div class="aicv">
    <div class="aicv-grid" role="group" aria-label="Portada de tu web">
      <button
        v-for="o in OPTIONS"
        :key="o.id"
        type="button"
        class="aicv-card"
        :class="{ on: current() === o.id }"
        :aria-pressed="current() === o.id"
        @click="emit('update:modelValue', o.id)"
      >
        <span class="aicv-card-icon"><AppIcon :name="o.icon" :size="18" /></span>
        <span class="aicv-card-text">
          <strong>{{ o.label }}</strong>
          <small>{{ desc(o) }}</small>
        </span>
        <span class="aicv-mark" aria-hidden="true"><AppIcon v-if="current() === o.id" name="check" :size="14" /></span>
      </button>
    </div>
  </div>
</template>
