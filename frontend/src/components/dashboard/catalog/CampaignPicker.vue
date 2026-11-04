<script setup>
import { computed, onMounted } from 'vue'
import AppIcon from '../../AppIcon.vue'
import DesignSelect from '../../design/DesignSelect.vue'
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

const options = computed(() => [
  { value: '', label: 'Sin campaña' },
  ...campaigns.value.map((c) => ({
    value: c.id,
    label: c.name,
    img: c.label_url || '',
    imgW: c.label_width || undefined,
    imgH: c.label_height || undefined,
    imgAlt: c.label_alt || c.name,
    swatch: c.accent || '#888',
    badge: c.is_running ? 'En curso' : startsLabel(c),
    badgeTone: c.is_running ? 'green' : 'amber'
  }))
])

function startsLabel(c) {
  const d = new Date(c.starts_at || '')
  if (Number.isNaN(d.getTime())) return ''
  return `Desde el ${d.toLocaleDateString('es-AR', { day: 'numeric', month: 'short' })}`
}
</script>

<template>
  <div class="field camp-field">
    <label id="disc-campaign-label"><AppIcon name="tag" :size="14" class="label-icon" aria-hidden="true" />Elegí la campaña</label>
    <DesignSelect
      :model-value="modelValue" :options="options" icon="tag"
      placeholder="Sin campaña" aria-label="Elegí la campaña"
      @update:model-value="emit('update:modelValue', $event)"
    />
    <p v-if="outOfWindow" class="hint camp-warn" role="status">
      <AppIcon name="clock" :size="13" aria-hidden="true" />
      «{{ selected.name }}» todavía no está en fecha: el descuento queda programado y recién se aplica cuando la campaña esté vigente.
    </p>
  </div>
</template>

<style scoped>
.camp-warn { display: flex; align-items: center; gap: 6px; margin-top: 8px; }
</style>
