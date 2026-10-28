<script setup>
import { ref, computed, watch } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  modelValue: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue'])

const DEFAULT = '#7c3aed'
const HEX_RE = /^#?[0-9a-f]{6}$/i

function inkFor(hex) {
  const raw = String(hex || '').replace('#', '')
  const rgb = [0, 2, 4].map((i) => {
    const c = parseInt(raw.slice(i, i + 2), 16) / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  const lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
  return lum > 0.45 ? '#111827' : '#ffffff'
}

const PRESETS = [
  { hex: '#7c3aed', name: 'Violeta' },
  { hex: '#f43f5e', name: 'Coral' },
  { hex: '#16a34a', name: 'Verde' },
  { hex: '#2563eb', name: 'Azul' },
  { hex: '#ca8a04', name: 'Mostaza' },
  { hex: '#db2777', name: 'Rosa' },
  { hex: '#0d9488', name: 'Turquesa' },
  { hex: '#111827', name: 'Negro' }
].map((p) => ({ ...p, ink: inkFor(p.hex) }))

const mode = ref(props.modelValue ? 'user' : 'ai')
const color = computed(() => props.modelValue || DEFAULT)
const hexText = ref(color.value)

watch(() => props.modelValue, (v) => {
  if (!v && mode.value === 'user') mode.value = 'ai'
  hexText.value = v || DEFAULT
})

function setMode(next) {
  mode.value = next
  if (next === 'ai') emit('update:modelValue', '')
  else if (!props.modelValue) emit('update:modelValue', DEFAULT)
}

function normalize(value) {
  const raw = String(value || '').trim()
  return HEX_RE.test(raw) ? `#${raw.replace('#', '').toLowerCase()}` : ''
}
function setColor(value) {
  const hex = normalize(value)
  if (hex) emit('update:modelValue', hex)
}
function onHexInput(e) {
  hexText.value = e.target.value
  setColor(e.target.value)
}
function onHexBlur() {
  hexText.value = color.value
}

const ink = computed(() => inkFor(color.value))
const inkLabel = computed(() => (ink.value === '#ffffff' ? 'blanco' : 'negro'))
</script>

<template>
  <div class="aidc-field">
    <div class="aidopt-grid two" role="group" aria-label="Color de tu marca">
      <button
        type="button"
        class="aidopt"
        :class="{ on: mode === 'ai' }"
        :aria-pressed="mode === 'ai'"
        @click="setMode('ai')"
      >
        <span class="aidopt-icon"><AppIcon name="sparkles" :size="18" /></span>
        <span class="aidopt-text">
          <strong>Que lo elija la IA</strong>
          <small>Buscamos el color que mejor le queda a tu negocio.</small>
        </span>
        <span class="aidopt-mark" aria-hidden="true"><AppIcon v-if="mode === 'ai'" name="check" :size="14" /></span>
      </button>

      <button
        type="button"
        class="aidopt"
        :class="{ on: mode === 'user' }"
        :aria-pressed="mode === 'user'"
        @click="setMode('user')"
      >
        <span class="aidopt-icon"><AppIcon name="palette" :size="18" /></span>
        <span class="aidopt-text">
          <strong>Elijo mi color</strong>
          <small>Lo usamos en botones y detalles de tu web.</small>
        </span>
        <span class="aidopt-mark" aria-hidden="true"><AppIcon v-if="mode === 'user'" name="check" :size="14" /></span>
      </button>
    </div>

    <div v-if="mode === 'user'" class="aidc-picker">
      <div class="aidc-swatches" role="group" aria-label="Colores sugeridos">
        <button
          v-for="p in PRESETS"
          :key="p.hex"
          type="button"
          class="aidc-swatch"
          :class="{ on: color === p.hex }"
          :style="{ '--sw': p.hex, color: p.ink }"
          :aria-pressed="color === p.hex"
          :aria-label="p.name"
          @click="setColor(p.hex)"
        >
          <span class="aidc-swatch-name">{{ p.name }}</span>
        </button>
      </div>

      <div class="aidc-custom">
        <label class="aidc-color-wrap" :style="{ '--sw': color }">
          <span class="sr-only">Elegir otro color</span>
          <input class="aidc-color" type="color" :value="color" @input="setColor($event.target.value)" />
          <span class="aidc-color-face" aria-hidden="true"></span>
        </label>
        <label class="aidc-hex-wrap">
          <span>Código del color</span>
          <input
            class="aidc-hex"
            type="text"
            maxlength="7"
            spellcheck="false"
            :value="hexText"
            placeholder="#7c3aed"
            @input="onHexInput"
            @blur="onHexBlur"
          />
        </label>
      </div>

      <div class="aidc-preview" :style="{ '--sw': color, '--sw-ink': ink }">
        <span class="aidc-preview-label">Así se va a ver</span>
        <div class="aidc-preview-row">
          <span class="aidc-preview-card">
            <strong>Tu negocio</strong>
            <small>Tu rubro, en una línea</small>
          </span>
          <span class="aidc-preview-btn">Ver catálogo</span>
        </div>
        <span class="aidc-preview-contrast">Sobre este color conviene el texto {{ inkLabel }}.</span>
      </div>
    </div>
  </div>
</template>
