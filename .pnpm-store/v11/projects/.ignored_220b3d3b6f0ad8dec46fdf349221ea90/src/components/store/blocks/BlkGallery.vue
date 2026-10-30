<script setup>
// Bloque 'gallery': la banda decorativa de invitación (imagen premium
// junto a texto + CTAs — nunca una foto suelta a todo lo ancho) y la
// grilla de la galería con su visor (lightbox con flechas/Esc).
// props.title pisa el título "Galería" de la sección.
import { ref, computed, inject, onMounted, onBeforeUnmount } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, shopName, hasAbout, showContact, showCatalog, hasDesignAdvanced } = ctx
const servicesPage = ctx.showServices

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))

const gallery = computed(() => custom.value.gallery || [])
const showGallery = computed(() => ctx.showGallery.value)
// Reparto del pool de imágenes ilustrativas (premium, hasta 3): la
// primera va a Sobre nosotros si existe, la siguiente acompaña esta
// banda y la última cierra la columna de contacto. El mismo cómputo se
// repite en BlkAbout/BlkContact — comparten los flags del ctx, así que
// el reparto coincide.
const decor = computed(() => (hasDesignAdvanced.value ? (custom.value.decor || []).slice(0, 3) : []))
const decorAbout = computed(() => (hasAbout.value ? decor.value[0] || null : null))
const decorPool = computed(() => decor.value.slice(decorAbout.value ? 1 : 0))
const decorBand = computed(() => decorPool.value[0] || null)
// La misión cargada sirve de bajada cuando existe.
const showcaseTitle = computed(() => (showContact.value ? 'Hablemos de lo que buscás' : `Conocé ${shopName.value}`))
const showcaseText = computed(() => custom.value.about_mission?.trim() || '')
const galleryTitle = computed(() => props.block?.props?.title?.trim() || 'Galería')
const galleryVariant = computed(() => props.block?.variant || 'grid')

const lightboxIndex = ref(-1)
const lightboxImage = computed(() => (lightboxIndex.value >= 0 ? gallery.value[lightboxIndex.value] || null : null))
const openLightbox = (index) => { lightboxIndex.value = index }
const closeLightbox = () => { lightboxIndex.value = -1 }
function stepLightbox(direction) {
  const total = gallery.value.length
  if (total < 2) return
  lightboxIndex.value = ((lightboxIndex.value + direction) % total + total) % total
}
const onKey = (e) => {
  if (e.key === 'Escape') closeLightbox()
  else if (lightboxIndex.value >= 0 && e.key === 'ArrowLeft') stepLightbox(-1)
  else if (lightboxIndex.value >= 0 && e.key === 'ArrowRight') stepLightbox(1)
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <!-- ===== Banda decorativa: invitación con CTAs junto a la imagen ===== -->
  <section v-if="decorBand" class="sp-showcase">
    <div class="sp-container sp-showcase-grid">
      <figure v-reveal class="sp-showcase-frame" aria-hidden="true">
        <img :src="decorBand.url" alt="" loading="lazy" />
      </figure>
      <div v-reveal="120" class="sp-showcase-copy">
        <p class="sp-eyebrow">{{ shopName }}</p>
        <h2 class="sp-showcase-title">{{ showcaseTitle }}</h2>
        <p v-if="showcaseText" class="sp-showcase-text">{{ showcaseText }}</p>
        <div class="sp-showcase-ctas">
          <RouterLink v-if="showCatalog" class="sp-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
          <RouterLink v-else-if="servicesPage" class="sp-btn" :to="servicesTo">Ver servicios <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
          <RouterLink v-if="servicesPage && showCatalog" class="sp-btn ghost" :to="servicesTo"><AppIcon name="wrench" :size="16" /> Servicios</RouterLink>
          <a v-if="showContact" class="sp-btn ghost" href="#contacto"><AppIcon name="message-circle" :size="16" /> Contáctanos</a>
        </div>
      </div>
    </div>
  </section>

  <!-- ===== Galería ===== -->
  <section v-if="showGallery" id="galeria" class="sp-gallery" :class="`is-${galleryVariant}`" :data-blk-variant="galleryVariant !== 'grid' ? galleryVariant : null" aria-labelledby="sp-gallery-title">
    <div class="sp-container">
      <h2 id="sp-gallery-title" v-reveal class="sp-section-title">{{ galleryTitle }}</h2>
      <div class="sp-gallery-grid">
        <button
          v-for="(img, i) in gallery" :key="img.id" v-reveal="(i % 4) * 70"
          type="button" class="sp-gallery-item"
          :aria-label="`Ver imagen ${i + 1} en grande`"
          @click="openLightbox(i)"
        >
          <img :src="img.url" :alt="`Imagen ${i + 1} de la galería de ${shopName}`" loading="lazy" />
        </button>
      </div>
    </div>
  </section>

  <!-- ===== Galería: visor de imagen ===== -->
  <Transition name="sp-modal">
  <div v-if="lightboxImage" class="sp-lightbox" role="dialog" aria-modal="true" aria-label="Visor de la galería" @click.self="closeLightbox">
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
</template>
