<script setup>
// Galería (§6.5-13): composición tipo revista — primera pieza 7/12, segunda
// 5/12 y el resto en filas de tres 1:1 — con caption en placa sólida al
// hover/foco y el visor accesible existente (flechas, Esc, click fuera).
// Conserva el ancla #galeria que usa el chrome del layout.
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx } = useRhLinks()
const { custom, shopName } = ctx

const gallery = computed(() => (Array.isArray(custom.value.gallery) ? custom.value.gallery : []))
const show = computed(() => ctx.showGallery.value && gallery.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || 'Trabajos y espacios')

const lightboxIndex = ref(-1)
const dialogEl = ref(null)
let lastFocus = null
const lightboxImage = computed(() => (lightboxIndex.value >= 0 ? gallery.value[lightboxIndex.value] || null : null))
function openLightbox(index) {
  lastFocus = document.activeElement
  lightboxIndex.value = index
  // El visor recibe el foco: teclado y lectores de pantalla entran al diálogo.
  nextTick(() => dialogEl.value?.focus())
}
function closeLightbox() {
  lightboxIndex.value = -1
  nextTick(() => lastFocus?.focus?.())
}
function stepLightbox(direction) {
  const total = gallery.value.length
  if (total < 2) return
  lightboxIndex.value = ((lightboxIndex.value + direction) % total + total) % total
}
function onKey(e) {
  if (!lightboxImage.value) return
  if (e.key === 'Escape') closeLightbox()
  else if (e.key === 'ArrowLeft') stepLightbox(-1)
  else if (e.key === 'ArrowRight') stepLightbox(1)
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
const pad = (n) => String(n).padStart(2, '0')
</script>

<template>
  <section v-if="show" id="galeria" class="rz-section rh-numbered rh-gallery" aria-labelledby="rh-gallery-title">
    <div class="rh-wrap">
      <header class="rh-head">
        <div class="rh-head-main">
          <p v-reveal class="rz-eyebrow">
            <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
            Galería
          </p>
          <h2 id="rh-gallery-title" v-reveal class="rh-title">{{ title }}</h2>
        </div>
        <span v-reveal="60" class="rh-gallery-count">{{ gallery.length }} {{ gallery.length === 1 ? 'imagen' : 'imágenes' }}</span>
      </header>

      <div class="rh-gallery-grid">
        <button
          v-for="(img, i) in gallery" :key="img.id" v-reveal="60 * (i % 3)"
          type="button" class="rh-gallery-item"
          :aria-label="`Ver imagen ${i + 1} de ${gallery.length} en grande`"
          @click="openLightbox(i)"
        >
          <img :src="img.url" :alt="`Imagen ${i + 1} de la galería de ${shopName}`" loading="lazy" decoding="async" />
          <span class="rh-gallery-cap">
            <span class="rh-gallery-num" aria-hidden="true">{{ pad(i + 1) }}</span>
            <span class="rh-gallery-cap-text">{{ shopName }}</span>
            <span class="rh-gallery-zoom" aria-hidden="true"><AppIcon name="maximize" :size="15" /></span>
          </span>
        </button>
      </div>
    </div>

    <Transition name="sp-modal">
      <div
        v-if="lightboxImage" ref="dialogEl" class="sp-lightbox" role="dialog" aria-modal="true"
        aria-label="Visor de la galería" tabindex="-1" @click.self="closeLightbox"
      >
        <button type="button" class="sp-modal-close" aria-label="Cerrar" @click="closeLightbox">
          <AppIcon name="x" :size="18" />
        </button>
        <button v-if="gallery.length > 1" type="button" class="sp-lightbox-arrow prev" aria-label="Imagen anterior" @click="stepLightbox(-1)">
          <AppIcon name="chevron-left" :size="22" />
        </button>
        <img :key="lightboxImage.id" class="sp-lightbox-img" :src="lightboxImage.url" :alt="`Imagen de la galería de ${shopName}`" />
        <button v-if="gallery.length > 1" type="button" class="sp-lightbox-arrow next" aria-label="Imagen siguiente" @click="stepLightbox(1)">
          <AppIcon name="chevron-right" :size="22" />
        </button>
        <span v-if="gallery.length > 1" class="sp-lightbox-count">{{ lightboxIndex + 1 }} / {{ gallery.length }}</span>
      </div>
    </Transition>
  </section>
</template>
