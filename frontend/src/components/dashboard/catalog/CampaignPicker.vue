<script setup>
import { computed, onMounted } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { useOffers } from '../../../composables/useOffers.js'

// Selector de campaña especial del descuento: "sin campaña" (default) o una
// del calendario. Fuera de su ventana anual el descuento no se aplica —
// se avisa antes de guardar.
const props = defineProps({
  modelValue: { type: [Number, String], default: '' }
})
const emit = defineEmits(['update:modelValue'])

const { campaigns, load } = useOffers()
onMounted(() => { load() })

const selected = computed(() => campaigns.value.find((c) => c.id === Number(props.modelValue)) || null)
const outOfWindow = computed(() => selected.value && !selected.value.is_running)

function pick(id) {
  emit('update:modelValue', id === props.modelValue ? '' : id)
}
function startsLabel(c) {
  const d = new Date(c.starts_at || '')
  if (Number.isNaN(d.getTime())) return ''
  return `Desde el ${d.toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })}`
}
</script>

<template>
  <div class="field camp-field">
    <label id="disc-campaign-label"><AppIcon name="tag" :size="14" class="label-icon" aria-hidden="true" />Etiqueta de campaña <small class="label-hint">(opcional)</small></label>
    <div class="camp-chips" role="radiogroup" aria-labelledby="disc-campaign-label">
      <button type="button" class="camp-chip" :class="{ on: modelValue === '' || modelValue === null }" role="radio" :aria-checked="modelValue === '' || modelValue === null" @click="emit('update:modelValue', '')">
        Sin campaña
      </button>
      <button
        v-for="c in campaigns" :key="c.id" type="button" class="camp-chip"
        :class="{ on: Number(modelValue) === c.id }" role="radio" :aria-checked="Number(modelValue) === c.id"
        :title="c.description || c.name" @click="pick(c.id)"
      >
        <img v-if="c.label_url" :src="c.label_url" :alt="c.label_alt || c.name" :width="c.label_width || undefined" :height="c.label_height || undefined" loading="lazy" class="camp-chip-img" />
        <span v-else class="camp-dot" :style="{ background: c.accent || '#888' }" aria-hidden="true"></span>
        <span class="camp-name">{{ c.name }}</span>
        <span class="camp-state" :class="c.is_running ? 'run' : 'next'">{{ c.is_running ? 'En curso' : startsLabel(c) }}</span>
      </button>
    </div>
    <p v-if="outOfWindow" class="hint camp-warn" role="status">
      <AppIcon name="clock" :size="13" aria-hidden="true" />
      «{{ selected.name }}» todavía no está en fecha: el descuento queda programado y recién se aplica cuando la campaña esté vigente.
    </p>
  </div>
</template>

<style scoped>
.camp-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.camp-chip {
  display: inline-flex; align-items: center; gap: 8px;
  min-height: 40px; padding: 4px 12px 4px 4px;
  border: 1px solid var(--line, #d9d9d9); border-radius: 999px;
  background: var(--surface, #fff); color: inherit; font: inherit; cursor: pointer;
}
.camp-chip:first-child { padding-left: 14px; }
.camp-chip.on { border-color: var(--brand, #6c4bd8); box-shadow: 0 0 0 1px var(--brand, #6c4bd8) inset; }
.camp-chip:focus-visible { outline: 2px solid var(--brand, #6c4bd8); outline-offset: 2px; }
.camp-chip-img { height: 28px; width: auto; object-fit: contain; display: block; }
.camp-dot { width: 14px; height: 14px; border-radius: 50%; margin-left: 8px; }
.camp-name { font-weight: 600; font-size: .86rem; }
.camp-state { font-size: .72rem; padding: 2px 8px; border-radius: 999px; }
.camp-state.run { background: #e7f6ec; color: #1f7a3d; }
.camp-state.next { background: var(--surface-2, #f1f1f1); color: var(--muted, #666); }
.camp-warn { display: flex; align-items: center; gap: 6px; margin-top: 8px; }
.label-hint { font-weight: 400; color: var(--muted, #666); }
</style>
