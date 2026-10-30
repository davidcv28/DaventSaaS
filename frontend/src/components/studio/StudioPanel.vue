<script setup>
// Paneles por defecto del Studio (uno por herramienta del riel).
// Los controles escriben DOS capas según corresponda:
//  - `form` (customization real: template, theme, name_font, accent_custom)
//    -> persiste hoy por la API existente.
//  - `theme` (siteTheme del contrato) -> viaja a la vista previa por
//    studio:update y al payload site_theme.
// Los paneles ricos (Colores, Tipografía, Contenedores, Fondo, Móvil y
// Movimiento) viven en ./panels/*; acá quedan Distribución, Folletos y
// Avanzado. La pestaña Estilos se retiró: ese flujo vive en la sección
// Diseño del panel (EstilosPanel → DesignStylesTab).
// Cada campo lleva data-focus con el target del contrato: el shell lo usa
// para el anillo animado en la vista previa y para enfocar el control
// cuando el usuario clickea el elemento correspondiente en el iframe.
import AppIcon from '../AppIcon.vue'
import ColorsPanel from './panels/ColorsPanel.vue'
import TypographyPanel from './panels/TypographyPanel.vue'
import ContainersPanel from './panels/ContainersPanel.vue'
import BackgroundPanel from './panels/BackgroundPanel.vue'
import MobilePanel from './panels/MobilePanel.vue'
import MotionPanel from './panels/MotionPanel.vue'
import HealthPanel from './panels/HealthPanel.vue'
import PublishPanel from './panels/PublishPanel.vue'
import DistribucionPanel from './panels/DistribucionPanel.vue'
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
  'export-theme', 'import-theme',
  'move-block', 'toggle-block', 'variant-block', 'reset-layout'
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

// Anillos del contrato en la vista previa: los emite el panel que tenga el
// control (Colores/Tipografía/Contenedores/Fondo) y el shell los dibuja.</script>

<template>
  <!-- ===== Paneles ricos (fase Studio panels) ===== -->
  <ColorsPanel
    v-if="tool === 'colores'"
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
    :share-url="shareUrl" :share-expires="shareExpires" :customization="customization"
    @publish="emit('publish', $event)" @discard="emit('discard-draft')"
    @restore="emit('restore', $event)" @share="emit('share')"
    @load-versions="emit('load-versions')"
  />

  <!-- ===== Distribución ===== -->
  <DistribucionPanel
    v-else-if="tool === 'distribucion'"
    :layout="layout"
    @navigate="emit('navigate', $event)" @ring="emit('ring', $event)"
    @move-block="emit('move-block', $event)" @toggle-block="emit('toggle-block', $event)"
    @variant-block="emit('variant-block', $event)" @reset-layout="emit('reset-layout')"
  />

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
  </div>
</template>

<style scoped>
/* El historial del Studio (Ctrl+Z, botones del savebar) es el único dentro
   del shell: se ocultan los controles de historial internos del LookTab. */
.stp-look :deep(.dl-hbtn) { display: none; }
.stp-look :deep(.dsg-card) { border: 0; box-shadow: none; padding: 0; border-radius: 0; background: transparent; }
</style>
