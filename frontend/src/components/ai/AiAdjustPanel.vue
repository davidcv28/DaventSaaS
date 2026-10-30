<script setup>
// Pantalla 3: ajustar la propuesta elegida SIN empezar de cero. La propuesta
// queda a la izquierda; acá solo los cuatro controles que el motor sabe
// tocar (tipografía, portada, aire, color). "Aplicar cambio" recalcula la
// misma propuesta con esos ajustes: no rehace la tanda ni pierde lo elegido.
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'
import AiSelect from './AiSelect.vue'

const props = defineProps({
  pairOptions: { type: Array, default: () => [] },
  hasLogo: { type: Boolean, default: false },
  busy: { type: Boolean, default: false },
  applied: { type: Array, default: () => [] },
  dirty: { type: Boolean, default: false }
})
const constraints = defineModel({ type: Object, default: () => ({}) })
const emit = defineEmits(['apply', 'reset'])

const COVERS = [
  { id: 'auto', label: 'Automática', icon: 'sparkles' },
  { id: 'foto', label: 'Foto', icon: 'image' },
  { id: 'logo', label: 'Logo', icon: 'store' }
]
const AIRS = [
  { id: 'compact', label: 'Compacta', icon: 'rows-3' },
  { id: 'comfortable', label: 'Cómoda', icon: 'layout-grid' },
  { id: 'spacious', label: 'Con aire', icon: 'maximize' }
]
const COLORS = ['#7c3aed', '#0f766e', '#c2410c', '#1d4ed8', '#be123c', '#111827']

function set(key, value) {
  constraints.value = { ...constraints.value, [key]: value }
}
const color = computed({
  get: () => String(constraints.value?.color || ''),
  set: (value) => set('color', value)
})
//"Aplicar cambio" solo cuando algo cambió respecto de lo que se ve.
const hasChanges = computed(() => props.dirty)
</script>

<template>
  <section class="aida" aria-labelledby="aida-title">
    <header class="aida-head">
      <div>
        <h3 id="aida-title">Ajustar esta propuesta</h3>
        <p>La IA cambia solo lo que marcás. El resto queda exactamente igual.</p>
      </div>
      <span v-if="applied.length" class="aida-applied">
        <AppIcon name="check" :size="12" /> {{ applied.join(' · ') }}
      </span>
    </header>

    <div class="aida-field">
      <p class="aida-label">Tipografía</p>
      <AiSelect
        :model-value="constraints.typography || ''"
        :options="pairOptions"
        label="Tipografía"
        placeholder="La que eligió la IA"
        @update:model-value="set('typography', $event)"
      />
    </div>

    <div class="aida-field">
      <p class="aida-label">Portada</p>
      <div class="aida-seg" role="group" aria-label="Portada">
        <button
          v-for="option in COVERS"
          :key="option.id"
          type="button"
          class="aida-seg-btn"
          :class="{ on: (constraints.cover || 'auto') === option.id }"
          :aria-pressed="(constraints.cover || 'auto') === option.id"
          :disabled="option.id === 'logo' && !hasLogo"
          @click="set('cover', option.id)"
        >
          <AppIcon :name="option.icon" :size="14" aria-hidden="true" />
          {{ option.label }}
        </button>
      </div>
      <p v-if="!hasLogo" class="aida-note">Sin logo cargado, la portada con logo queda deshabilitada.</p>
    </div>

    <div class="aida-field">
      <p class="aida-label">Aire</p>
      <div class="aida-seg" role="group" aria-label="Aire">
        <button
          v-for="option in AIRS"
          :key="option.id"
          type="button"
          class="aida-seg-btn"
          :class="{ on: constraints.air === option.id }"
          :aria-pressed="constraints.air === option.id"
          @click="set('air', constraints.air === option.id ? '' : option.id)"
        >
          <AppIcon :name="option.icon" :size="14" aria-hidden="true" />
          {{ option.label }}
        </button>
      </div>
    </div>

    <div class="aida-field">
      <p class="aida-label">Color de marca</p>
      <div class="aida-swatches" role="group" aria-label="Color de marca">
        <button
          v-for="swatch in COLORS"
          :key="swatch"
          type="button"
          class="aida-swatch"
          :class="{ on: color.toLowerCase() === swatch }"
          :style="{ '--swatch': swatch }"
          :aria-label="`Color ${swatch}`"
          :aria-pressed="color.toLowerCase() === swatch"
          @click="set('color', color.toLowerCase() === swatch ? '' : swatch)"
        ></button>
        <label class="aida-swatch aida-swatch-custom" :style="{ '--swatch': color || 'var(--aid-accent)' }">
          <AppIcon name="palette" :size="14" aria-hidden="true" />
          <input v-model="color" type="color" class="aida-color-input" aria-label="Elegir otro color" />
        </label>
      </div>
    </div>

    <footer class="aida-actions">
      <button class="btn btn-auto aid-primary" type="button" :disabled="busy || !hasChanges" @click="emit('apply')">
        <AppIcon name="sliders" :size="16" /> {{ busy ? 'Aplicando…' : 'Aplicar cambio' }}
      </button>
      <button class="btn ghost btn-auto" type="button" :disabled="busy" @click="emit('reset')">
        <AppIcon name="undo" :size="16" /> Volver a la versión anterior
      </button>
    </footer>
  </section>
</template>
