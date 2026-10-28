<script setup>
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  modelValue: { type: Object, default: () => ({ enabled: false, default: 'light' }) }
})
const emit = defineEmits(['update:modelValue'])

const enabled = computed(() => Boolean(props.modelValue?.enabled))
const start = computed(() => (props.modelValue?.default === 'dark' ? 'dark' : 'light'))

function setEnabled(value) {
  emit('update:modelValue', { enabled: value, default: value ? start.value : 'light' })
}
function setStart(value) {
  emit('update:modelValue', { enabled: true, default: value })
}
</script>

<template>
  <div class="aid-field">
    <div class="aidopt-grid two" role="group" aria-label="Modo noche">
      <button
        type="button"
        class="aidopt"
        :class="{ on: enabled }"
        :aria-pressed="enabled"
        @click="setEnabled(true)"
      >
        <span class="aidopt-icon"><AppIcon name="moon" :size="18" /></span>
        <span class="aidopt-text">
          <strong>Sí, con modo noche</strong>
          <small>Tus clientes pueden pasar de claro a oscuro cuando quieran.</small>
        </span>
        <span class="aidopt-mark" aria-hidden="true"><AppIcon v-if="enabled" name="check" :size="14" /></span>
      </button>

      <button
        type="button"
        class="aidopt"
        :class="{ on: !enabled }"
        :aria-pressed="!enabled"
        @click="setEnabled(false)"
      >
        <span class="aidopt-icon"><AppIcon name="sun" :size="18" /></span>
        <span class="aidopt-text">
          <strong>No, solo un estilo</strong>
          <small>La web se ve siempre igual, como la diseñamos.</small>
        </span>
        <span class="aidopt-mark" aria-hidden="true"><AppIcon v-if="!enabled" name="check" :size="14" /></span>
      </button>
    </div>

    <div v-if="enabled" class="aid-night-start">
      <span class="aid-night-label">¿Cómo arranca?</span>
      <div class="aidopt-grid two" role="group" aria-label="Cómo arranca la web">
        <button
          type="button"
          class="aidopt compact"
          :class="{ on: start === 'light' }"
          :aria-pressed="start === 'light'"
          @click="setStart('light')"
        >
          <span class="aidopt-icon"><AppIcon name="sun" :size="17" /></span>
          <span class="aidopt-text"><strong>Claro</strong></span>
          <span class="aidopt-mark" aria-hidden="true"><AppIcon v-if="start === 'light'" name="check" :size="14" /></span>
        </button>
        <button
          type="button"
          class="aidopt compact"
          :class="{ on: start === 'dark' }"
          :aria-pressed="start === 'dark'"
          @click="setStart('dark')"
        >
          <span class="aidopt-icon"><AppIcon name="moon" :size="17" /></span>
          <span class="aidopt-text"><strong>Oscuro</strong></span>
          <span class="aidopt-mark" aria-hidden="true"><AppIcon v-if="start === 'dark'" name="check" :size="14" /></span>
        </button>
      </div>
    </div>
  </div>
</template>
