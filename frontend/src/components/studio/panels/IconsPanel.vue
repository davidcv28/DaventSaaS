<script setup>
// Panel "Iconos" del Studio: set de iconos del menú y los controles.
// El diseño trae un set por defecto; el usuario puede cambiarlo sin tocar el
// diseño. Vacío = hereda el del diseño (la web pública resuelve la caída).
import { computed, onMounted } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { useDesignCatalog } from '../../../composables/useDesignCatalog.js'
import { iconChoice } from '../../../studio/designChoice.js'

const props = defineProps({
  form: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) }
})

const { iconStyles, defaultIconStyle, defaultPattern, status, load } = useDesignCatalog()
onMounted(() => load(true))

const options = computed(() => iconStyles.value.filter((s) => s.is_active !== false))
const slugs = computed(() => options.value.map((s) => s.slug))
const current = computed(() => props.form.icon_style || '')
// Set que hereda: el del diseño elegido y, si no declara uno, el del catálogo.
const inherited = computed(() => {
  const own = defaultPattern.value?.icon_style
  const found = options.value.find((s) => s.slug === own) || defaultIconStyle.value
  return found?.nombre || 'el del diseño'
})

const PREVIEW_KEYS = ['home', 'catalog', 'services', 'search', 'theme', 'cart']
function previewPaths(set) {
  return PREVIEW_KEYS
    .map((key) => set.icons?.[key])
    .filter((entry) => entry?.path)
    .slice(0, 5)
}

function pick(slug) {
  props.form.icon_style = iconChoice(slug, { options: slugs.value }).icon_style
}
</script>

<template>
  <div class="stp-fields">
    <p class="stp-hint">
      Los iconos del menú, el buscador y el carrito. Cambiarlos no toca el diseño: solo el dibujo
      de los controles.
    </p>

    <div v-if="status === 'loading' && !options.length" class="stp-hint" role="status">Cargando iconos…</div>

    <div class="stp-picks" role="radiogroup" aria-label="Set de iconos de los controles">
      <button
        type="button" role="radio" class="stp-pick" :class="{ active: current === '' }"
        :aria-checked="current === ''" @click="pick('')"
      >
        <span class="stp-pick-art" aria-hidden="true"><AppIcon name="grid" :size="17" /></span>
        <span class="stp-pick-body">
          <span class="stp-pick-name">Heredar del diseño</span>
          <span class="stp-pick-meta">Usa {{ inherited }}</span>
        </span>
        <AppIcon v-if="current === ''" name="circle-check" :size="16" aria-hidden="true" />
      </button>

      <button
        v-for="s in options" :key="s.slug" type="button" role="radio"
        class="stp-pick" :class="{ active: current === s.slug }"
        :aria-checked="current === s.slug" :title="s.descripcion || s.nombre"
        @click="pick(s.slug)"
      >
        <span class="stp-pick-art stp-icon-set" aria-hidden="true">
          <svg
            v-for="(entry, i) in previewPaths(s)" :key="i" :viewBox="entry.view_box || '0 0 24 24'"
            :style="{ fill: entry.fill ? 'currentColor' : 'none', strokeWidth: entry.fill ? 0 : (s.stroke_width ?? 1.6) }"
          ><path :d="entry.path" /></svg>
        </span>
        <span class="stp-pick-body">
          <span class="stp-pick-name">{{ s.nombre }}</span>
          <span class="stp-pick-meta">{{ s.descripcion || 'Set de iconos del menú' }}</span>
        </span>
        <AppIcon v-if="current === s.slug" name="circle-check" :size="16" aria-hidden="true" />
      </button>
    </div>
  </div>
</template>
