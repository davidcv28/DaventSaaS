<script setup>
// Portada de CLÁSICO: composición asimétrica 56/44 con aire editorial.
// Izquierda: eyebrow con regla corta, titular serif, bajada, CTAs (sólido
// acento + outline de tinta) y ficha meta con separadores verticales finos.
// Derecha: foto enmarcada tipo passe-partout (borde 1 px + marco interior de
// 12 px) con chip de crédito. Datos reales del negocio: portada premium,
// carrusel, galería o la primera foto del catálogo; sin foto el marco muestra
// el monograma serif del comercio (nunca una foto inventada). La ficha meta
// solo lista datos cargados: abierto/cerrado interpretado de los horarios,
// ciudad/provincia y años de trayectoria; sin datos no se pinta.
import { ref, computed, inject, onMounted, onBeforeUnmount } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import { openStatus } from '../../../utils/storeHours.js'

defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, store, custom, shopName, location, showContact, showCatalog, hasDesignAdvanced } = ctx
const servicesPage = ctx.showServices
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))

// Portada/carrusel son contenido avanzado; sin ellos se usa la galería y, al
// final, la primera foto real del catálogo. Nunca se inventa una imagen.
const cover = computed(() => (hasDesignAdvanced.value ? custom.value.cover || '' : ''))
const media = computed(() => {
  const pool = [
    cover.value,
    ...(custom.value.carousel || []).map((i) => i.url),
    ...(custom.value.gallery || []).map((g) => g.url),
    ...featured.value.products.map((p) => p.image)
  ]
  return pool.find(Boolean) || ''
})
const hasHeadline = computed(() => Boolean(custom.value.headline?.trim()))
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
const lead = computed(() => custom.value.description?.trim() || '')
// Con titular cargado el eyebrow lleva la marca; sin titular, el estado del
// catálogo (la ubicación ya viaja en la ficha meta, no se repite).
const eyebrow = computed(() => (hasHeadline.value
  ? shopName.value
  : (showCatalog.value ? 'Catálogo online' : 'Sitio oficial')))
const initial = computed(() => (shopName.value || '·').trim().charAt(0).toUpperCase())
const chip = computed(() => (media.value
  ? [shopName.value, location.value].filter(Boolean).join(' · ')
  : 'Foto de portada'))

const city = computed(() => store.value?.city_name || '')
const province = computed(() => store.value?.province_name || '')

// «Abierto ahora» se interpreta de los horarios reales; si el texto libre no
// se entiende, openStatus devuelve null y no se afirma nada.
const now = ref(new Date())
let clock = null
onMounted(() => { clock = setInterval(() => { now.value = new Date() }, 60000) })
onBeforeUnmount(() => clearInterval(clock))
const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))

const meta = computed(() => {
  const items = []
  if (openNow.value) items.push({ key: 'open', text: openNow.value.text, open: openNow.value.state === 'open' })
  if (city.value) items.push({ key: 'city', text: city.value })
  else if (location.value) items.push({ key: 'loc', text: location.value })
  if (province.value && province.value !== city.value) items.push({ key: 'prov', text: province.value })
  if (custom.value.about_years) {
    items.push({ key: 'years', text: `+${custom.value.about_years} ${Number(custom.value.about_years) === 1 ? 'año' : 'años'}` })
  }
  return items
})
</script>

<template>
  <section class="cl-hero" aria-labelledby="cl-hero-title">
    <div class="cl-container cl-hero-inner">
      <div class="cl-hero-copy">
        <p v-reveal class="cl-eyebrow">{{ eyebrow }}</p>
        <h1 id="cl-hero-title" v-reveal="60" class="cl-hero-title">{{ heroTitle }}</h1>
        <p v-if="lead" v-reveal="110" class="cl-hero-lead">{{ lead }}</p>

        <div v-reveal="160" class="cl-hero-actions">
          <RouterLink v-if="showCatalog" class="cl-btn" :to="catalogTo">
            Ver catálogo <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
          </RouterLink>
          <RouterLink v-else-if="servicesPage" class="cl-btn" :to="servicesTo">
            Ver servicios <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
          </RouterLink>
          <a v-if="showContact" class="cl-btn cl-btn--outline" href="#contacto">Contáctanos</a>
          <RouterLink v-else-if="servicesPage && showCatalog" class="cl-btn cl-btn--outline" :to="servicesTo">Servicios</RouterLink>
        </div>

        <ul v-if="meta.length" v-reveal="210" class="cl-hero-meta">
          <li v-for="m in meta" :key="m.key">
            <span v-if="m.open" class="cl-hero-dot" aria-hidden="true"></span>{{ m.text }}
          </li>
        </ul>
      </div>

      <figure v-reveal="120" class="cl-hero-media">
        <div class="cl-hero-frame">
          <img v-if="media" :src="media" :alt="`Foto de portada de ${shopName}`" fetchpriority="high" decoding="async" />
          <span v-else class="cl-hero-mono" aria-hidden="true">{{ initial }}</span>
        </div>
        <figcaption class="cl-hero-chip">{{ chip }}</figcaption>
      </figure>
    </div>
  </section>
</template>
