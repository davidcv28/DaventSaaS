<script setup>
import { ref, computed, watch } from 'vue'
import AppIcon from '../AppIcon.vue'

// Color de marca: una decisión, tres estados visuales.
//  1) segmento "IA / yo elijo" (2 opciones, no 2 tarjetas enormes),
//  2) muestras circulares + "Otro" (sin nombres técnicos a la vista),
//  3) preview claro/oscuro con el color aplicado a botón y acentos.
// El código hex queda plegado: es un dato de quien ya lo sabe, no una
// pregunta para el dueño del negocio.
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
  <div class="aicf">
    <div class="aicf-seg" role="group" aria-label="Quién elige el color">
      <button
        type="button"
        class="aicf-seg-btn"
        :class="{ on: mode === 'ai' }"
        :aria-pressed="mode === 'ai'"
        @click="setMode('ai')"
      >
        <AppIcon name="sparkles" :size="16" aria-hidden="true" />
        Que lo elija la IA
      </button>
      <button
        type="button"
        class="aicf-seg-btn"
        :class="{ on: mode === 'user' }"
        :aria-pressed="mode === 'user'"
        @click="setMode('user')"
      >
        <AppIcon name="palette" :size="16" aria-hidden="true" />
        Elijo mi color
      </button>
    </div>

    <p class="aicf-note">
      <template v-if="mode === 'ai'">
        Buscamos el color que mejor le queda a tu rubro y lo usamos en botones, títulos y detalles.
      </template>
      <template v-else>
        El mismo color en botones, títulos y detalles de tu web.
      </template>
    </p>

    <div v-if="mode === 'user'" class="aicf-picker">
      <div class="aicf-swatches" role="group" aria-label="Colores sugeridos">
        <button
          v-for="p in PRESETS"
          :key="p.hex"
          type="button"
          class="aicf-swatch"
          :class="{ on: color === p.hex }"
          :style="{ '--swatch': p.hex }"
          :aria-pressed="color === p.hex"
          :aria-label="p.name"
          :title="p.name"
          @click="setColor(p.hex)"
        >
          <span class="aicf-swatch-dot" aria-hidden="true">
            <AppIcon v-if="color === p.hex" name="check" :size="14" :style="{ color: p.ink }" />
          </span>
          <span class="aicf-swatch-name">{{ p.name }}</span>
        </button>

        <label class="aicf-swatch aicf-swatch-custom" :style="{ '--swatch': color }">
          <span class="aicf-swatch-dot aicf-swatch-plus" aria-hidden="true">
            <AppIcon name="plus" :size="15" />
          </span>
          <span class="aicf-swatch-name">Otro</span>
          <span class="sr-only">Elegir otro color</span>
          <input class="aicf-color-input" type="color" :value="color" @input="setColor($event.target.value)" />
        </label>
      </div>

      <div class="aicf-preview" :style="{ '--swatch': color, '--swatch-ink': ink }">
        <span class="aicf-preview-label">Así se va a ver</span>
        <div class="aicf-preview-duo">
          <div class="aicf-mini is-light" aria-hidden="true">
            <span class="aicf-mini-bar"></span>
            <span class="aicf-mini-title"></span>
            <span class="aicf-mini-line"></span>
            <span class="aicf-mini-btn">Ver catálogo</span>
          </div>
          <div class="aicf-mini is-dark" aria-hidden="true">
            <span class="aicf-mini-bar"></span>
            <span class="aicf-mini-title"></span>
            <span class="aicf-mini-line"></span>
            <span class="aicf-mini-btn">Ver catálogo</span>
          </div>
        </div>
        <p class="aicf-preview-note">
          Sobre este color el texto va en {{ inkLabel }}. Ajustamos el contraste para que siempre se lea bien.
        </p>
      </div>

      <details class="aicf-more">
        <summary>Tengo el código exacto de mi marca</summary>
        <label class="aicf-hex-wrap">
          <span class="aicf-hex-label">Código (por ejemplo #1a7f5a)</span>
          <input
            class="aid-input aicf-hex"
            type="text"
            maxlength="7"
            spellcheck="false"
            :value="hexText"
            placeholder="#7c3aed"
            @input="onHexInput"
            @blur="onHexBlur"
          />
        </label>
      </details>
    </div>
  </div>
</template>
