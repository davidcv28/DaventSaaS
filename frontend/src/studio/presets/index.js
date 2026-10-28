// API pública del sistema de presets del Studio.
// catalog.js: datos (presets, builder de layout, rubros, lock, filtros).
// PresetGallery.vue: el selector de estilos del panel "Estilos".
export {
  STUDIO_PRESETS,
  RUBRO_LABELS,
  buildLayout,
  detectRubro,
  ensurePresetFonts,
  filterPresets,
  layoutForTemplate,
  presetById,
  presetLock
} from './catalog.js'
