<script setup>
// Paneles por defecto del Studio (uno por herramienta del riel).
// Los controles escriben DOS capas según corresponda:
//  - `form` (customization real: template, theme, name_font, accent_custom)
//    -> persiste hoy por la API existente.
//  - `theme` (siteTheme del contrato) -> viaja a la vista previa por
//    studio:update y al payload site_theme.
// Los paneles ricos (Estilos, Colores, Tipografía, Contenedores, Fondo,
// Móvil y Movimiento) viven en ./panels/*; acá quedan Distribución,
// Folletos y Avanzado.
// Cada campo lleva data-focus con el target del contrato: el shell lo usa
// para el anillo animado en la vista previa y para enfocar el control
// cuando el usuario clickea el elemento correspondiente en el iframe.
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'
import EstilosPanel from './panels/EstilosPanel.vue'
import ColorsPanel from './panels/ColorsPanel.vue'
import TypographyPanel from './panels/TypographyPanel.vue'
import ContainersPanel from './panels/ContainersPanel.vue'
import BackgroundPanel from './panels/BackgroundPanel.vue'
import MobilePanel from './panels/MobilePanel.vue'
import MotionPanel from './panels/MotionPanel.vue'
import HealthPanel from './panels/HealthPanel.vue'
import PublishPanel from './panels/PublishPanel.vue'
import { SURFACE_LABELS } from './studioModel.js'
import '../../assets/studio-panels.css'

const props = defineProps({
  tool: { type: String, required: true },
  form: { type: Object, required: true },
  theme: { type: Object, required: true },
  benefits: { type: Object, default: () => ({}) },
  siteTemplates: { type: Array, default: () => [] },
  layout: { type: Object, default: null },
  canFlyers: { type: Boolean, default: false },
  shopName: { type: String, default: '' },
  customization: { type: Object, default: () => ({}) },
  viewer: { type: String, default: 'light' },
  // Salud de tu web: contenido contra el que se contrastan las secciones.
  healthCtx: { type: Object, default: () => ({}) },
  // Publicar: estado del flujo borrador → web (lo maneja el Dashboard).
  hasUnpublished: { type: Boolean, default: false },
  localDirty: { type: Boolean, default: false },
  versions: { type: Array, default: () => [] },
  versionsLoading: { type: Boolean, default: false },
  actionBusy: { type: String, default: '' },
  shareUrl: { type: String, default: '' },
  shareExpires: { type: String, default: '' }
})
const emit = defineEmits([
  'navigate', 'ring', 'set-viewer',
  'fix', 'publish', 'discard-draft', 'restore', 'share', 'load-versions',
  'export-theme', 'import-theme'
])

// Importar tema (.json): el archivo se lee acá y el objeto crudo sube al
// shell, que lo valida con resolveSiteTheme antes de aplicarlo al borrador.
function onImportFile(e) {
  const file = e.target?.files?.[0]
  e.target.value = ''
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => emit('import-theme', String(reader.result || ''))
  reader.onerror = () => emit('import-theme', '')
  reader.readAsText(file)
}

// --- Distribución (solo lectura en esta fase: la edición vive en Bloques) ---
const surfaces = computed(() => ['landing', 'catalog', 'services'].map((id) => {
  const blocks = Array.isArray(props.layout?.[id]?.blocks) ? props.layout[id].blocks : []
  const on = blocks.filter((b) => b && b.enabled !== false)
  return { id, label: SURFACE_LABELS[id] || id, active: props.siteTemplates.includes(id), count: on.length, total: blocks.length }
}))

// Anillos del LookTab -> targets del contrato en la vista previa: los
// mapea EstilosPanel (RING_MAP interno) antes de re-emitir 'ring'.</script>

<template>
  <!-- ===== Estilos: flujo guiado en 3 niveles (presets -> rápidos -> avanzado) ===== -->
  <div v-if="tool === 'estilos'" class="stp-look">
    <EstilosPanel
      :form="form" :benefits="benefits" :shop-name="shopName"
      @navigate="emit('navigate', $event)" @ring="emit('ring', $event)" @set-viewer="emit('set-viewer', $event)"
    />
  </div>

  <!-- ===== Paneles ricos (fase Studio panels) ===== -->
  <ColorsPanel
    v-else-if="tool === 'colores'"
    :theme="theme" :form="form" :benefits="benefits"
    :customization="customization" :viewer="viewer" :shop-name="shopName"
    @navigate="emit('navigate', $event)" @set-viewer="emit('set-viewer', $event)"
  />
  <TypographyPanel
    v-else-if="tool === 'tipografia'"
    :theme="theme" :form="form" :benefits="benefits" :shop-name="shopName"
    @navigate="emit('navigate', $event)"
  />
  <ContainersPanel
    v-else-if="tool === 'contenedores'"
    :theme="theme" :form="form" :benefits="benefits"
    @navigate="emit('navigate', $event)"
  />
  <BackgroundPanel
    v-else-if="tool === 'fondo'"
    :theme="theme" :form="form" :benefits="benefits" :customization="customization"
    @navigate="emit('navigate', $event)"
  />
  <MobilePanel
    v-else-if="tool === 'movil'"
    :theme="theme" :form="form" :benefits="benefits"
    @navigate="emit('navigate', $event)"
  />
  <MotionPanel
    v-else-if="tool === 'movimiento'"
    :theme="theme" :benefits="benefits"
    @navigate="emit('navigate', $event)"
  />
  <HealthPanel
    v-else-if="tool === 'salud'"
    :theme="theme" :form="form" :layout="layout" :ctx="healthCtx"
    @navigate="emit('navigate', $event)" @fix="emit('fix', $event)"
  />
  <PublishPanel
    v-else-if="tool === 'publicar'"
    :has-unpublished="hasUnpublished" :local-dirty="localDirty"
    :versions="versions" :versions-loading="versionsLoading" :busy="actionBusy"
    :share-url="shareUrl" :share-expires="shareExpires"
    @publish="emit('publish', $event)" @discard="emit('discard-draft')"
    @restore="emit('restore', $event)" @share="emit('share')"
    @load-versions="emit('load-versions')"
  />

  <!-- ===== Distribución ===== -->
  <div v-else-if="tool === 'distribucion'" class="stp">
    <p class="stp-hint">Las páginas activas de tu web y sus bloques. El orden y las variantes se editan en el editor de bloques.</p>
    <ul class="stp-surfaces" data-focus="blk">
      <li v-for="s in surfaces" :key="s.id" class="stp-surface" :data-on="s.active">
        <AppIcon :name="s.id === 'landing' ? 'store' : s.id === 'catalog' ? 'layout-grid' : 'wrench'" :size="16" />
        <span class="stp-surface-lb">{{ s.label }}</span>
        <span class="stp-surface-n">{{ s.active ? `${s.count}/${s.total || s.count} bloques` : 'apagada' }}</span>
      </li>
    </ul>
    <button type="button" class="btn secondary btn-auto stp-cta" @click="emit('navigate', 'blocks')">
      <AppIcon name="list-ordered" :size="16" /> Abrir el editor de bloques
    </button>
  </div>

  <!-- ===== Folletos ===== -->
  <div v-else-if="tool === 'folletos'" class="stp">
    <div class="stp-card">
      <span class="stp-card-ico"><AppIcon name="printer" :size="22" /></span>
      <strong>Flyer Studio</strong>
      <p>Diseñá folletos imprimibles con tu logo, colores y QR a la página. Es otra superficie: se abre en Herramientas.</p>
      <button v-if="canFlyers" type="button" class="btn secondary btn-auto" @click="emit('navigate', 'tools')">
        Ir a folletos <AppIcon name="arrow-right" :size="15" />
      </button>
      <template v-else>
        <p class="stp-lock"><span class="lock-badge"><AppIcon name="lock" :size="11" :stroke="2" /> Premium</span></p>
        <button type="button" class="btn secondary btn-auto" @click="emit('navigate', 'plans')">Ver planes <AppIcon name="arrow-right" :size="15" /></button>
      </template>
    </div>
  </div>

  <!-- ===== Avanzado ===== -->
  <div v-else-if="tool === 'avanzado'" class="stp">
    <div class="stp-field" data-focus="page">
      <span class="stp-lb">Tema de la página</span>
      <div class="stp-seg" role="group" aria-label="Tema claro u oscuro">
        <button v-for="[id, lb, ic] in [['light', 'Claro', 'sun'], ['dark', 'Oscuro', 'moon']]" :key="id" type="button" class="stp-opt" :class="{ active: form.theme === id }" :aria-pressed="form.theme === id" @click="form.theme = id">
          <AppIcon :name="ic" :size="14" /> {{ lb }}
        </button>
      </div>
      <small class="stp-hint2">Claro u oscuro: se guarda con tu diseño. El mismo control está en Colores con la comparación lado a lado.</small>
    </div>
    <div class="stp-card">
      <span class="stp-card-ico"><AppIcon name="download" :size="22" /></span>
      <strong>Tema en JSON</strong>
      <p>Exportá el tema actual como archivo o importá uno validado: colores, contenedores, tipografía, botones, fondo, movimiento y móvil.</p>
      <div class="stp-seg">
        <button type="button" class="btn secondary btn-auto" @click="emit('export-theme')">
          <AppIcon name="download" :size="14" /> Exportar
        </button>
        <label class="btn secondary btn-auto stp-import">
          <AppIcon name="upload" :size="14" /> Importar
          <input type="file" accept=".json,application/json" class="sr-only" @change="onImportFile" />
        </label>
      </div>
      <small class="stp-hint2">El archivo importado se valida contra el esquema del tema antes de aplicarlo al borrador.</small>
    </div>
    <div class="stp-card stp-soon">
      <span class="stp-card-ico"><AppIcon name="sliders" :size="22" /></span>
      <strong>Personalización total</strong>
      <p>CSS propio y tokens por plantilla llegan con una fase futura del tema del Studio.</p>
      <span class="lock-badge">Próximamente</span>
    </div>
  </div>
</template>

<style scoped>
/* El historial del Studio (Ctrl+Z, botones del savebar) es el único dentro
   del shell: se ocultan los controles de historial internos del LookTab. */
.stp-look :deep(.dl-hbtn) { display: none; }
.stp-look :deep(.dsg-card) { border: 0; box-shadow: none; padding: 0; border-radius: 0; background: transparent; }
</style>
