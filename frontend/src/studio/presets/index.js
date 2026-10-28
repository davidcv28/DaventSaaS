// API pública del sistema de presets del Studio.
// catalog.js: datos (presets, builder de layout, rubros, lock, filtros).
// PresetGallery.vue: la galería del panel "Estilos".
// PresetThumb.vue: miniatura web real renderizada con los datos de la tienda.
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
