<script setup>
// Panel "Estilo" del Studio: elegir el DesignStyle del catálogo.
// El estilo solo aporta look (colores, bordes, sombras, densidad, tipografía
// y botones): nunca estructura ni composición. El resultado se aplica al
// borrador del tema (para que la vista previa lo muestre en vivo) y a
// `form.site_theme` (para que el guardado lo persista).
import { computed, onMounted } from 'vue'
import AppIcon from '../../AppIcon.vue'
import PanelField from './PanelField.vue'
import { useDesignCatalog } from '../../../composables/useDesignCatalog.js'
import { allowedTemplatesFor, ensureStoreFont, STORE_ACCENTS } from '../../../api/stores.api.js'
import { resolveSiteTheme } from '../../../studio/contract.js'
import { nearestAccent, hexToRgb } from '../../../utils/colorTools.js'
import { styleChoice } from '../../../studio/designChoice.js'

const props = defineProps({
  form: { type: Object, required: true },
  theme: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) }
})
const emit = defineEmits(['navigate'])

const { styles, status, load } = useDesignCatalog()
onMounted(() => load(true))

const advanced = computed(() => Boolean(props.benefits?.has_design_advanced))
const allowed = computed(() => allowedTemplatesFor(props.benefits || {}))
const options = computed(() => styles.value.filter((s) => s.is_active !== false))
const current = computed(() => props.form.site_theme?.style?.id || '')
const same = (a, b) => JSON.stringify(a || {}) === JSON.stringify(b || {})

// El estilo es un tema completo: se vuelca entero al borrador para que lo que
// se ve en el lienzo sea exactamente lo que se guarda.
function applyTheme(tokens) {
  const resolved = resolveSiteTheme(tokens)
  for (const [section, content] of Object.entries(resolved)) {
    props.theme[section] = JSON.parse(JSON.stringify(content))
  }
}

function pick(style) {
  const choice = styleChoice(style, { allowed: allowed.value })
  if (!choice) return
  if (choice.locked) { emit('navigate', 'plans'); return }
  props.form.site_theme = choice.site_theme
  props.form.theme = choice.page_theme
  applyTheme(choice.site_theme)
  const typography = resolveSiteTheme(choice.site_theme).typography
  if (typography.heading) ensureStoreFont(typography.heading)
  if (typography.body) {
    props.form.name_font = typography.body
    ensureStoreFont(typography.body)
  }
  const accent = resolveSiteTheme(choice.site_theme).palette?.accent
  if (!accent) return
  if (advanced.value) {
    props.form.accent_custom = accent
    return
  }
  const slug = nearestAccent(hexToRgb(accent), STORE_ACCENTS)
  if (slug) {
    props.form.accent = slug
    props.form.accent_custom = ''
  }
}

const isCurrent = (style) => (
  current.value === style.slug
  || (!current.value && same(props.form.site_theme, style.tokens))
)
</script>

<template>
  <div class="stp-fields">
    <p class="stp-hint">
      El estilo define el look: paleta, bordes, sombras, aire y tipografía. La estructura la sigue
      mandando el diseño.
    </p>

    <div v-if="status === 'loading' && !options.length" class="stp-hint" role="status">Cargando estilos…</div>

    <div class="stp-picks" role="radiogroup" aria-label="Estilo de tu web">
      <button
        v-for="s in options" :key="s.slug" type="button" role="radio"
        class="stp-pick" :class="{ active: isCurrent(s), locked: !allowed.includes(s.template) }"
        :aria-checked="isCurrent(s)" :title="s.descripcion || s.nombre"
        @click="pick(s)"
      >
        <span class="stp-pick-art" aria-hidden="true"><AppIcon name="palette" :size="17" /></span>
        <span class="stp-pick-body">
          <span class="stp-pick-name">{{ s.nombre }}</span>
          <span class="stp-pick-meta">{{ s.categoria }}</span>
        </span>
        <AppIcon v-if="!allowed.includes(s.template)" name="lock" :size="14" class="stp-pick-lock" aria-hidden="true" />
        <AppIcon v-else-if="isCurrent(s)" name="circle-check" :size="16" aria-hidden="true" />
      </button>
    </div>

    <p class="stp-sec">Modo noche</p>
    <PanelField
      label="Tema de la página"
      tip="¿Qué es esto? El modo con el que abre tu web. Igual los visitantes pueden cambiarlo con el interruptor de la barra."
      focus="page" need="none" :benefits="benefits"
    >
      <div class="stp-seg" role="group" aria-label="Tema claro u oscuro">
        <button
          v-for="[id, lb, ic] in [['light', 'Claro', 'sun'], ['dark', 'Oscuro', 'moon']]" :key="id"
          type="button" class="stp-opt" :class="{ active: form.theme === id }"
          :aria-pressed="form.theme === id" @click="form.theme = id"
        ><AppIcon :name="ic" :size="14" /> {{ lb }}</button>
      </div>
    </PanelField>
    <label class="stp-check">
      <input v-model="form.theme_toggle" type="checkbox" />
      Mostrar el interruptor claro/oscuro a los visitantes
    </label>
  </div>
</template>
