<script>
// Aviso de calidad de foto por slot (espejo de
// StoreApp/domains/stores/services/media_quality.py — los umbrales viven en
// backend; si cambian SLOT_SPECS allá, actualizar QUALITY_SLOTS acá).
// Nunca bloquea la subida: solo informa.
export const QUALITY_SLOTS = {
  cover: {
    label: 'la portada', min_side: 2200, aspect: 16 / 9, ratio: [1.0, 2.5],
    crop_hint: 'conviene recortar la imagen a formato horizontal, tipo 3:2 o 16:9'
  },
  product: {
    label: 'la foto del producto', min_side: 1200, aspect: 1, ratio: [0.75, 1.5],
    crop_hint: 'conviene recortar la imagen a formato casi cuadrado, como se ve en las tarjetas'
  },
  logo: {
    label: 'el logo', min_side: 800, aspect: 1, ratio: [0.5, 2.5],
    crop_hint: 'conviene recortar el logo a formato cuadrado o horizontal no muy alargado'
  },
  gallery: {
    label: 'la foto de la galería', min_side: 1600, aspect: 1, ratio: [0.75, 16 / 9],
    crop_hint: 'la grilla la recorta sola; si podés, encuadrala entre 3:4 y 16:9'
  }
}

// Lee width/height del File en el navegador (EXIF ya aplicado por el decoder).
// Devuelve null si no se puede leer: el aviso simplemente no aparece.
export async function inspectImageFile(file, slot) {
  const spec = QUALITY_SLOTS[slot]
  if (!spec || !file) return null
  let width = 0
  let height = 0
  try {
    if (typeof createImageBitmap === 'function') {
      const bmp = await createImageBitmap(file, { imageOrientation: 'from-image' })
      width = bmp.width
      height = bmp.height
      if (typeof bmp.close === 'function') bmp.close()
    }
  } catch { /* fallback con <img> abajo */ }
  if (!width || !height) {
    const url = URL.createObjectURL(file)
    try {
      const img = new Image()
      img.src = url
      await img.decode()
      width = img.naturalWidth
      height = img.naturalHeight
    } catch { /* archivo inválido: sin aviso */ }
    finally { URL.revokeObjectURL(url) }
  }
  if (!width || !height) return null
  const ratio = Math.round((width / height) * 1000) / 1000
  const usable = Math.min(width, height * spec.aspect)
  return {
    slot,
    width,
    height,
    ratio,
    usable: Math.floor(usable),
    min_side: spec.min_side,
    soft: usable < spec.min_side,
    ratio_ok: ratio >= spec.ratio[0] && ratio <= spec.ratio[1]
  }
}

// {ok, soft, hint} — misma forma que media_quality.quality() del backend.
export function buildQuality(info) {
  if (!info) return null
  const spec = QUALITY_SLOTS[info.slot]
  if (!spec) return null
  const parts = []
  if (info.soft) {
    parts.push(`Se va a ver borrosa en pantalla grande: usá una foto de al menos ${spec.min_side} px de lado útil para ${spec.label}.`)
  }
  if (!info.ratio_ok) {
    parts.push(`Para que encuadre mejor en ${spec.label}, ${spec.crop_hint}.`)
  }
  return { ok: !info.soft && info.ratio_ok, soft: info.soft, hint: parts.join(' ') }
}
</script>

<script setup>
import { computed } from 'vue'
import AppIcon from '../AppIcon.vue'

const props = defineProps({
  // {ok, soft, hint} — se muestra solo cuando hay hint (aviso, nunca error).
  quality: { type: Object, default: null }
})
const hint = computed(() => props.quality?.hint || '')
</script>

<template>
  <p v-if="hint" class="mqh" role="status">
    <AppIcon name="circle-alert" :size="14" aria-hidden="true" />
    <span>{{ hint }}</span>
  </p>
</template>

<style scoped>
.mqh {
  display: flex; align-items: flex-start; gap: 8px;
  margin: 8px 0 0; padding: 9px 12px;
  border: 1px solid var(--warn-line); border-radius: 12px;
  background: var(--warn-bg); color: var(--warn-ink);
  font-size: 12.5px; line-height: 1.45;
}
.mqh .icon { flex: none; margin-top: 1px; }
.mqh span { min-width: 0; overflow-wrap: anywhere; }
</style>
