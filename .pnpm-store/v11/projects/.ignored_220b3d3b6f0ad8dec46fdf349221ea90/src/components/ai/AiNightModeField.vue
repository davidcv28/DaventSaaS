<script setup>
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'

// Modo noche: un interruptor (sí/no) y, solo si se activa, dos miniaturas
// de la web en claro y en oscuro para elegir con qué arranca. Antes eran
// cuatro tarjetas de texto: la decisión real es una sola y se ve mejor
// con la web dibujada que con adjetivos.
const props = defineProps({
  modelValue: { type: Object, default: () => ({ enabled: false, default: 'light' }) },
  accent: { type: String, default: '#7c3aed' }
})
const emit = defineEmits(['update:modelValue'])

const enabled = computed(() => Boolean(props.modelValue?.enabled))
const start = computed(() => (props.modelValue?.default === 'dark' ? 'dark' : 'light'))
const tint = computed(() => (/^#[0-9a-f]{6}$/i.test(props.accent) ? props.accent : '#7c3aed'))

function setEnabled(value) {
  emit('update:modelValue', { enabled: value, default: value ? start.value : 'light' })
}
function setStart(value) {
  emit('update:modelValue', { enabled: true, default: value })
}
</script>

<template>
  <div class="ainm" :style="{ '--ainm-accent': tint }">
    <label class="aid-switch">
      <input type="checkbox" :checked="enabled" @change="setEnabled($event.target.checked)" />
      <span class="aid-switch-text">
        <strong>Modo noche en tu web</strong>
        <small>Tus clientes pueden pasar de claro a oscuro cuando quieran.</small>
      </span>
    </label>

    <div v-if="enabled" class="ainm-start">
      <p class="ainm-start-q">¿Cómo arranca cuando alguien entra?</p>
      <div class="ainm-start-opts" role="group" aria-label="Cómo arranca la web">
        <button
          type="button"
          class="ainm-thumb"
          :class="{ on: start === 'light' }"
          :aria-pressed="start === 'light'"
          @click="setStart('light')"
        >
          <span class="ainm-frame is-light" aria-hidden="true">
            <span class="ainm-frame-bar"></span>
            <span class="ainm-frame-title"></span>
            <span class="ainm-frame-line"></span>
            <span class="ainm-frame-btn"></span>
          </span>
          <span class="ainm-thumb-label">
            <AppIcon name="sun" :size="15" aria-hidden="true" /> Claro
            <span class="ainm-mark" aria-hidden="true"><AppIcon v-if="start === 'light'" name="check" :size="12" /></span>
          </span>
        </button>

        <button
          type="button"
          class="ainm-thumb"
          :class="{ on: start === 'dark' }"
          :aria-pressed="start === 'dark'"
          @click="setStart('dark')"
        >
          <span class="ainm-frame is-dark" aria-hidden="true">
            <span class="ainm-frame-bar"></span>
            <span class="ainm-frame-title"></span>
            <span class="ainm-frame-line"></span>
            <span class="ainm-frame-btn"></span>
          </span>
          <span class="ainm-thumb-label">
            <AppIcon name="moon" :size="15" aria-hidden="true" /> Oscuro
            <span class="ainm-mark" aria-hidden="true"><AppIcon v-if="start === 'dark'" name="check" :size="12" /></span>
          </span>
        </button>
      </div>
      <p class="ainm-note">La web arranca así y el interruptor queda a la vista del visitante.</p>
    </div>
  </div>
</template>
