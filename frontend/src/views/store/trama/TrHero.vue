<script setup>
// Portada de TRAMA (indumentaria): composición partida 55/45 con borde
// vertical, titular Anton en mayúsculas con la última palabra en acento y
// placa circular sobre la imagen. Datos reales: titular/bajada del negocio,
// portada o última imagen del catálogo, badge de "nuevo ingreso" solo si hay
// productos de los últimos días. Sin imagen queda un bloque tonal con la
// inicial (nunca un rótulo de "foto").
import { ref, computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { isNewProduct } from '../../../api/catalog.api.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const ctx = inject('storePage')
const { slug, custom, shopName, initial, location, showContact, showCatalog, hasDesignAdvanced } = ctx
const servicesPage = ctx.showServices
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))

// Portada/carrusel son contenido premium (has_design_advanced); sin ellos se
// usa la primera imagen de producto disponible.
const cover = computed(() => (hasDesignAdvanced.value ? custom.value.cover || '' : ''))
const media = computed(() => {
  const pool = [
    cover.value,
    ...(custom.value.carousel || []).map((i) => i.url),
    ...featured.value.products.map((p) => p.image)
  ]
  return pool.find(Boolean) || ''
})
const isNew = computed(() => featured.value.products.some((p) => isNewProduct(p)))

const hasHeadline = computed(() => Boolean(custom.value.headline?.trim()))
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
// La palabra acentuada es la última del titular cargado por el dueño: con
// solo el nombre de la marca no se acentúa (evita partir el nombre).
const titleParts = computed(() => {
  const words = heroTitle.value.split(/\s+/).filter(Boolean)
  if (!hasHeadline.value || words.length < 2) return { lead: heroTitle.value, accent: '' }
  return { lead: words.slice(0, -1).join(' '), accent: words[words.length - 1] }
})
const badge = computed(() => (
  hasHeadline.value
    ? shopName.value
    : (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial'))
))
const meta = computed(() => {
  const items = []
  if (hasHeadline.value && location.value) items.push({ key: 'loc', icon: 'map-pin', text: location.value })
  if (custom.value.about_years) items.push({ key: 'years', icon: 'clock', text: `+${custom.value.about_years} años` })
  return items
})

const copied = ref(false)
async function share() {
  const data = { title: shopName.value, text: custom.value.description?.trim() || `Mirá ${shopName.value}`, url: window.location.href }
  if (navigator.share) {
    try { await navigator.share(data); return } catch (e) { if (e?.name === 'AbortError') return }
  }
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch { /* el link ya está en la barra del navegador */ }
}
</script>

<template>
  <section class="tr-hero" aria-labelledby="tr-hero-title">
    <div class="tr-hero-copy">
      <p v-reveal class="tr-eyebrow">{{ badge }}</p>
      <h1 id="tr-hero-title" v-reveal="60" class="tr-hero-title">
        {{ titleParts.lead }}<template v-if="titleParts.accent"> <span class="tr-hero-accent">{{ titleParts.accent }}</span></template>
      </h1>
      <p v-if="custom.description" v-reveal="120" class="tr-hero-sub">{{ custom.description }}</p>
      <div v-reveal="180" class="tr-hero-ctas">
        <RouterLink v-if="showCatalog" class="tr-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" class="tr-arrow" /></RouterLink>
        <RouterLink v-if="servicesPage" class="tr-btn tr-btn--ghost" :to="servicesTo">Servicios</RouterLink>
        <a v-if="showContact" class="tr-btn tr-btn--ghost" href="#contacto">Contáctanos</a>
        <button type="button" class="tr-hero-share" :aria-label="copied ? 'Link copiado' : 'Compartir tienda'" :title="copied ? 'Link copiado' : 'Compartir'" @click="share">
          <AppIcon :name="copied ? 'check' : 'share-2'" :size="17" />
        </button>
      </div>
      <ul v-if="meta.length" v-reveal="240" class="tr-hero-meta">
        <li v-for="m in meta" :key="m.key"><AppIcon :name="m.icon" :size="14" aria-hidden="true" /> {{ m.text }}</li>
      </ul>
    </div>

    <figure class="tr-hero-media">
      <span v-if="isNew" class="tr-hero-badge" aria-hidden="true"><span>Nuevo</span><span>ingreso</span></span>
      <img v-if="media" :src="media" :alt="`Portada de ${shopName}`" fetchpriority="high" decoding="async" />
      <span v-else class="tr-hero-ph" aria-hidden="true">{{ initial }}</span>
      <figcaption v-if="media">{{ shopName }}<template v-if="location"> · {{ location }}</template></figcaption>
    </figure>
  </section>
</template>
