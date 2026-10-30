<script setup>
// Panel "Diseño" del Studio (contrato nuevo): elegir el DesignPattern.
// El diseño manda la estructura (template + layout_config); su piel (tokens)
// solo se aplica si la tienda todavía no eligió estilo. El plan se valida acá
// con allowedTemplatesFor: un diseño de otro nivel abre "Ver planes".
import { computed, onMounted } from 'vue'
import AppIcon from '../../AppIcon.vue'
import PanelLock from './PanelLock.vue'
import { useDesignCatalog } from '../../../composables/useDesignCatalog.js'
import { allowedTemplatesFor, STORE_TEMPLATES } from '../../../api/stores.api.js'
import { normalizeLayoutConfig } from '../../../templates/index.js'
import { patternChoice } from '../../../studio/designChoice.js'

const props = defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['navigate', 'layout'])

// El catálogo público ya trae los patrones activos de la base (incluidos los
// importados con html/css/js): no hace falta pegarle al listado autenticado,
// que en una carga fría responde 403 mientras renueva el access.
const { patterns, status, load } = useDesignCatalog()
onMounted(() => load(true))

const options = computed(() => patterns.value)
const allowed = computed(() => allowedTemplatesFor(props.benefits || {}))
const tierOf = (template) => STORE_TEMPLATES[template]?.tier || 'base'
const tierLabel = (template) => {
  const tier = tierOf(template)
  return tier === 'plus' ? 'Desde Estándar' : tier === 'advanced' ? 'Premium' : 'Incluido'
}
const patternLayout = (p) => normalizeLayoutConfig(p.layout)
const sameJson = (a, b) => JSON.stringify(a || {}) === JSON.stringify(b || {})
const current = computed(() => (
  options.value.find((p) => (
    p.template === props.form.template && sameJson(patternLayout(p), props.form.layout_config)
  ))?.slug
  || options.value.find((p) => p.template === props.form.template)?.slug
  || ''
))
const hasStyle = computed(() => Boolean(props.form.site_theme?.style?.id))

function pick(p) {
  const choice = patternChoice(p, { allowed: allowed.value, hasStyle: hasStyle.value })
  if (!choice) return
  if (choice.locked) { emit('navigate', 'plans'); return }
  props.form.template = choice.template
  const layout = normalizeLayoutConfig(choice.layout_config)
  props.form.layout_config = layout
  emit('layout', layout)
  if (choice.site_theme) props.form.site_theme = { ...(props.form.site_theme || {}), ...choice.site_theme }
}
</script>

<template>
  <div class="stp-fields">
    <p class="stp-hint">
      El diseño decide cómo se organiza tu web: portada, catálogo y servicios propios de cada rubro.
      El estilo (bordes y colores) se elige en la herramienta Estilo.
    </p>

    <div v-if="status === 'loading' && !options.length" class="stp-hint" role="status">Cargando diseños…</div>

    <div class="stp-picks" role="radiogroup" aria-label="Diseño de tu web">
      <button
        v-for="p in options" :key="p.slug" type="button" role="radio"
        class="stp-pick" :class="{ active: current === p.slug, locked: !allowed.includes(p.template) }"
        :aria-checked="current === p.slug" :title="p.descripcion || p.nombre"
        @click="pick(p)"
      >
        <span class="stp-pick-art" aria-hidden="true"><AppIcon name="layers" :size="17" /></span>
        <span class="stp-pick-body">
          <span class="stp-pick-name">{{ p.nombre }}</span>
          <span class="stp-pick-meta">{{ p.categoria }} · {{ tierLabel(p.template) }}</span>
        </span>
        <AppIcon v-if="!allowed.includes(p.template)" name="lock" :size="14" class="stp-pick-lock" aria-hidden="true" />
        <AppIcon v-else-if="current === p.slug" name="circle-check" :size="16" aria-hidden="true" />
      </button>
    </div>

    <PanelLock
      v-if="options.length && options.every((p) => !allowed.includes(p.template))"
      text="Los diseños de este nivel vienen con un plan superior."
      @plans="emit('navigate', 'plans')"
    />
    <p v-if="hasStyle" class="stp-hint2">
      El diseño cambia la estructura; los colores y bordes siguen saliendo del estilo elegido.
    </p>
  </div>
</template>
