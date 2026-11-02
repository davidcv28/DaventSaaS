<script setup>
// Panel "Medios" (iconos e imágenes): set de iconos del menú y controles,
// ajustes del logo (tamaño, modo, nombre), portada (velo y punto focal) y
// tratamiento de las imágenes (images.treatment del contrato).
// Todo lo que el diseño activo no declara en `capabilities` se oculta:
// el Studio solo ofrece lo que el estilo soporta pintar.
import { computed, onMounted } from 'vue'
import AppIcon from '../../AppIcon.vue'
import PanelField from './PanelField.vue'
import { useDesignCatalog } from '../../../composables/useDesignCatalog.js'
import { iconChoice } from '../../../studio/designChoice.js'
import { capSection, capOption } from '../../../studio/capabilities.js'
import { STUDIO_ENUMS } from '../../../studio/contract.js'

const props = defineProps({
  form: { type: Object, required: true },
  theme: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  customization: { type: Object, default: () => ({}) },
  caps: { type: Object, default: () => ({}) }
})

const showIcons = computed(() => capSection(props.caps, 'icons'))
const showLogo = computed(() => capOption(props.caps, 'images', 'logo'))
const showFocus = computed(() => capOption(props.caps, 'images', 'focus'))
const showOverlay = computed(() => capOption(props.caps, 'images', 'overlay'))
const showFilters = computed(() => capOption(props.caps, 'images', 'filters'))

// ---------------------------------------------------------------------------
// Iconos del menú (set del diseño o uno del catálogo del dominio design).
// ---------------------------------------------------------------------------
const { iconStyles, defaultIconStyle, defaultPattern, status, load } = useDesignCatalog()
onMounted(() => load(true))
const options = computed(() => iconStyles.value.filter((s) => s.is_active !== false))
const slugs = computed(() => options.value.map((s) => s.slug))
const currentIcon = computed(() => props.form.icon_style || '')
const inherited = computed(() => {
  const own = defaultPattern.value?.icon_style
  const found = options.value.find((s) => s.slug === own) || defaultIconStyle.value
  return found?.nombre || 'el del diseño'
})
const PREVIEW_KEYS = ['home', 'catalog', 'services', 'search', 'theme', 'cart']
function previewPaths(set) {
  return PREVIEW_KEYS.map((key) => set.icons?.[key]).filter((entry) => entry?.path).slice(0, 5)
}
function pickIcon(slug) {
  props.form.icon_style = iconChoice(slug, { options: slugs.value }).icon_style
}

// ---------------------------------------------------------------------------
// Logo: tamaño, modo (logo+nombre / solo logo) y estilo del nombre a una
// letra cuando no hay logo propio.
// ---------------------------------------------------------------------------
const hasLogo = computed(() => Boolean(props.customization?.logo))
const LOGO_SCALES = [['s', 'S'], ['m', 'M'], ['l', 'L']]
const LOGO_MODES = [
  { id: 'logo_name', label: 'Logo y nombre', icon: 'panel-top' },
  { id: 'logo_only', label: 'Solo logo', icon: 'image' }
]
const MONO_STYLES = [['accent', 'Color de acento'], ['neutral', 'Neutro']]

// ---------------------------------------------------------------------------
// Portada: velo sobre la foto y punto focal (campos persistidos del form).
// ---------------------------------------------------------------------------
const hasCover = computed(() => Boolean(props.customization?.cover))
const FOCAL = [0, 50, 100]
const focalActive = (x, y) => Math.round(props.form.cover_focus_x) === x && Math.round(props.form.cover_focus_y) === y
function setFocus(x, y) {
  props.form.cover_focus_x = x
  props.form.cover_focus_y = y
}

// ---------------------------------------------------------------------------
// Tratamiento de las imágenes (contrato, sección `images`).
// ---------------------------------------------------------------------------
const TREATMENTS = [
  { id: 'none', label: 'Natural', hint: 'Las fotos tal como las subiste.' },
  { id: 'soft', label: 'Suave', hint: 'Menos saturación: un look más editorial.' },
  { id: 'grayscale', label: 'B/N', hint: 'Blanco y negro en toda la página.' },
  { id: 'duotone', label: 'Duotono', hint: 'Fotos teñidas con la paleta de tu marca.' }
]
const img = computed(() => props.theme.images || { treatment: 'none' })
</script>

<template>
  <div class="stp-fields">
    <p class="stp-hint">
      Las imágenes y los iconos de tu página: el set de controles, tu logo, la portada
      y cómo se tratan las fotos. Todo se ve al instante en la vista previa.
    </p>

    <!-- ===== Iconos ===== -->
    <template v-if="showIcons">
      <p class="stp-sec">Iconos del menú</p>
      <div v-if="status === 'loading' && !options.length" class="stp-hint" role="status">Cargando iconos…</div>
      <div class="stp-picks" role="radiogroup" aria-label="Set de iconos de los controles">
        <button
          type="button" role="radio" class="stp-pick" :class="{ active: currentIcon === '' }"
          :aria-checked="currentIcon === ''" data-focus="chrome.nav" @click="pickIcon('')"
        >
          <span class="stp-pick-art" aria-hidden="true"><AppIcon name="grid" :size="17" /></span>
          <span class="stp-pick-body">
            <span class="stp-pick-name">Heredar del diseño</span>
            <span class="stp-pick-meta">Usa {{ inherited }}</span>
          </span>
          <AppIcon v-if="currentIcon === ''" name="circle-check" :size="16" aria-hidden="true" />
        </button>
        <button
          v-for="s in options" :key="s.slug" type="button" role="radio"
          class="stp-pick" :class="{ active: currentIcon === s.slug }"
          :aria-checked="currentIcon === s.slug" :title="s.descripcion || s.nombre"
          data-focus="chrome.nav" @click="pickIcon(s.slug)"
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
          <AppIcon v-if="currentIcon === s.slug" name="circle-check" :size="16" aria-hidden="true" />
        </button>
      </div>
    </template>

    <!-- ===== Logo ===== -->
    <template v-if="showLogo">
      <p class="stp-sec">Logo</p>
      <PanelField
        label="Tamaño del logo"
        tip="¿Qué es esto? Qué tan grande se ve tu logo en la barra de navegación."
        focus="chrome.nav" need="advanced" :benefits="benefits"
        :hint="hasLogo ? '' : 'Todavía no subiste un logo: se aplica cuando lo cargues en Diseño → Fotos.'"
      >
        <div class="stp-seg" role="group" aria-label="Tamaño del logo">
          <button
            v-for="[id, lb] in LOGO_SCALES" :key="id" type="button" class="stp-opt"
            :class="{ active: form.logo_scale === id }" :aria-pressed="form.logo_scale === id"
            @click="form.logo_scale = id"
          >{{ lb }}</button>
        </div>
      </PanelField>
      <PanelField
        label="Cómo se muestra"
        tip="¿Qué es esto? Si la barra muestra tu logo junto al nombre de la tienda o solo el logo."
        focus="chrome.nav" need="advanced" :benefits="benefits"
      >
        <div class="stp-seg" role="group" aria-label="Modo del logo">
          <button
            v-for="o in LOGO_MODES" :key="o.id" type="button" class="stp-opt"
            :class="{ active: form.logo_mode === o.id }" :aria-pressed="form.logo_mode === o.id"
            @click="form.logo_mode = o.id"
          ><AppIcon :name="o.icon" :size="14" aria-hidden="true" /> {{ o.label }}</button>
        </div>
      </PanelField>
      <PanelField
        v-if="!hasLogo"
        label="Nombre a una letra"
        tip="¿Qué es esto? Sin logo, la barra usa la inicial de tu tienda: en el color de acento o en un gris neutro."
        focus="chrome.nav" need="advanced" :benefits="benefits"
      >
        <div class="stp-seg" role="group" aria-label="Estilo de la inicial">
          <button
            v-for="[id, lb] in MONO_STYLES" :key="id" type="button" class="stp-opt"
            :class="{ active: form.mono_style === id }" :aria-pressed="form.mono_style === id"
            @click="form.mono_style = id"
          >{{ lb }}</button>
        </div>
      </PanelField>
    </template>

    <!-- ===== Portada ===== -->
    <template v-if="showOverlay || showFocus">
      <p class="stp-sec">Portada</p>
      <PanelField
        v-if="showOverlay"
        label="Velo sobre la foto"
        tip="¿Qué es esto? Una capa oscura encima de la portada para que el nombre y los botones se lean mejor."
        focus="hero" need="advanced" :benefits="benefits"
        :hint="hasCover ? '' : 'Sin foto de portada el velo no se ve: subila en Diseño → Fotos.'"
      >
        <label class="stp-angle" data-focus="hero">
          <span class="stp-role-lb">Intensidad <b class="stp-val">{{ form.cover_overlay || 0 }}%</b></span>
          <input
            type="range" class="stp-range" min="0" max="80" step="5"
            :value="form.cover_overlay || 0" aria-label="Velo sobre la portada"
            @input="form.cover_overlay = Number($event.target.value)"
          />
        </label>
      </PanelField>
      <PanelField
        v-if="showFocus"
        label="Punto focal"
        tip="¿Qué es esto? La zona de la portada que nunca se corta al adaptarse a cada pantalla. Tocá dónde está lo importante."
        focus="hero" need="advanced" :benefits="benefits"
        :hint="hasCover ? '' : 'Se aplica cuando subas la foto de portada en Diseño → Fotos.'"
      >
        <div class="stp-focal" role="group" aria-label="Punto focal de la imagen de portada">
          <template v-for="y in FOCAL" :key="y">
            <button
              v-for="x in FOCAL" :key="`${x}-${y}`" type="button" class="stp-focal-cell"
              :class="{ active: focalActive(x, y) }" :aria-pressed="focalActive(x, y)"
              :aria-label="`Foco horizontal ${x} por ciento, vertical ${y} por ciento`"
              @click="setFocus(x, y)"
            ><span class="stp-focal-dot" aria-hidden="true"></span></button>
          </template>
        </div>
      </PanelField>
    </template>

    <!-- ===== Tratamiento de imágenes ===== -->
    <PanelField
      v-if="showFilters"
      label="Tratamiento de las fotos"
      tip="¿Qué es esto? Un acabado para todas las imágenes de la página: portada, productos y galería. Solo los que tu diseño soporta."
      focus="media" need="advanced" :benefits="benefits"
      :hint="TREATMENTS.find((t) => t.id === img.treatment)?.hint"
    >
      <div class="stp-minis" role="group" aria-label="Tratamiento de las imágenes">
        <button
          v-for="t in TREATMENTS" :key="t.id" type="button" class="stp-mini"
          :class="{ active: img.treatment === t.id }" :aria-pressed="img.treatment === t.id"
          @click="img.treatment = t.id"
        >
          <span class="stp-mini-art stp-img-treat" :data-treat="t.id" aria-hidden="true"></span>
          <span class="stp-mini-lb">{{ t.label }}</span>
        </button>
      </div>
    </PanelField>
  </div>
</template>

<style>
/* Miniaturas del tratamiento: una "foto" abstracta filtrada como la web. */
.stp-img-treat { background: linear-gradient(120deg, #a5b4fc 20%, #f0abfc 55%, #fcd34d); }
.stp-img-treat[data-treat='soft'] { filter: saturate(.88) contrast(.97) brightness(1.03); }
.stp-img-treat[data-treat='grayscale'] { filter: grayscale(1) contrast(1.04); }
.stp-img-treat[data-treat='duotone'] { filter: grayscale(1) sepia(.55) hue-rotate(-12deg) contrast(1.05) brightness(.94) saturate(1.4); }
</style>
