<script setup>
import { computed } from 'vue'
import { useStoreStore } from '../stores/store.store.js'
import { formatStorageMB } from '../api/stores.api.js'
import AppIcon from './AppIcon.vue'

// Medidor de la cuota de imágenes del plan. Lee store.storage, que viaja en
// GET /stores/ y se refresca en cada subida/borrado:
// - Espacio: used_bytes vs max_mb (MB reales, todos los planes tienen tope).
// - Archivos: images vs max_images (Básico/Estándar con tope; Premium = sin límite).
const store = useStoreStore()
const info = computed(() => store.storage)

const usedMB = computed(() => formatStorageMB(info.value?.used_bytes))
const maxMB = computed(() => info.value?.max_mb ?? null)
const spaceText = computed(() =>
  maxMB.value === null ? `${usedMB.value} MB (sin límite)` : `${usedMB.value} MB de ${maxMB.value} MB`
)
const imagesText = computed(() => {
  const s = info.value
  if (!s) return ''
  return s.max_images === null ? `${s.images} (sin límite)` : `${s.images} de ${s.max_images}`
})
const pct = computed(() => {
  if (!maxMB.value) return 0
  return Math.min(100, Math.round(((info.value?.used_bytes || 0) / (maxMB.value * 1024 * 1024)) * 100))
})
const almostFull = computed(() => pct.value >= 85)
</script>

<template>
  <div v-if="info" class="storage-meter">
    <div class="storage-meter-head">
      <span class="storage-meter-label"><AppIcon name="image" :size="15" aria-hidden="true" /> Almacenamiento de imágenes</span>
      <span class="storage-meter-values">
        <span>{{ spaceText }}</span>
        <span>{{ imagesText }} imágenes</span>
      </span>
    </div>
    <div
      class="storage-meter-track"
      role="progressbar"
      aria-label="Espacio de almacenamiento usado"
      :aria-valuenow="pct"
      aria-valuemin="0"
      aria-valuemax="100"
    >
      <span class="storage-meter-bar" :class="{ warn: almostFull }" :style="{ width: pct + '%' }"></span>
    </div>
    <p v-if="almostFull" class="hint">Estás cerca del límite de espacio: borrá imágenes o subí de plan para liberar cuota.</p>
  </div>
</template>
