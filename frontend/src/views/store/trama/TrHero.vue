<script setup>
// Portada partida de TRAMA («Indumentaria · Profesional»): copy a la izquierda
// (eyebrow, titular, bajada, 2 CTAs y ficha meta) y panel de imagen a la
// derecha con chip. Datos reales del negocio: titular/bajada del diseño,
// portada premium, carrusel, galería o la primera foto del catálogo. Sin foto
// el panel muestra la línea de prenda y el chip de "Foto de portada" (nunca un
// rótulo con datos inventados). La ficha meta solo lista datos cargados:
// estado abierto/cerrado (interpretado de los horarios), ciudad, provincia y
// años de trayectoria. Sin datos la lista entera no se pinta.
import { ref, computed, inject, onMounted, onBeforeUnmount } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import GarmentLine from './GarmentLine.vue'
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

// Portada/carrusel son contenido premium; sin ellos se usa la galería y, al
// final, la primera foto real de producto. Nunca se inventa una imagen.
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
const chip = computed(() => (media.value
  ? [shopName.value, location.value].filter(Boolean).join(' · ')
  : 'Foto de portada'))

const hasHeadline = computed(() => Boolean(custom.value.headline?.trim()))
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
const lead = computed(() => custom.value.description?.trim() || '')
// Con titular cargado el eyebrow lleva la marca; sin titular, el estado del
// catálogo (la ubicación ya viaja en la ficha meta, no se repite).
const eyebrow = computed(() => (hasHeadline.value
  ? shopName.value
  : (showCatalog.value ? 'Catálogo online' : 'Sitio oficial')))

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
  if (custom.value.about_years) items.push({ key: 'years', text: `+${custom.value.about_years} ${Number(custom.value.about_years) === 1 ? 'año' : 'años'}` })
  return items
})
</script>

<template>
  <section class="tr-hero" aria-labelledby="tr-hero-title">
    <div class="tr-hero-copy">
      <p v-reveal class="tr-eyebrow">{{ eyebrow }}</p>
      <h1 id="tr-hero-title" v-reveal="60" class="tr-hero-title">{{ heroTitle }}</h1>
      <p v-if="lead" v-reveal="110" class="tr-lead">{{ lead }}</p>

      <div v-reveal="160" class="tr-hero-actions">
        <RouterLink v-if="showCatalog" class="tr-btn" :to="catalogTo">
          Ver catálogo <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
        </RouterLink>
        <RouterLink v-else-if="servicesPage" class="tr-btn" :to="servicesTo">
          Ver servicios <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
        </RouterLink>
        <a v-if="showContact" class="tr-btn tr-btn--ghost" href="#contacto">Contáctanos</a>
        <RouterLink v-else-if="servicesPage && showCatalog" class="tr-btn tr-btn--ghost" :to="servicesTo">Servicios</RouterLink>
      </div>

      <ul v-if="meta.length" v-reveal="210" class="tr-hero-meta">
        <li v-for="m in meta" :key="m.key">
          <span class="tr-dot" :class="{ 'is-open': m.open }" aria-hidden="true"></span>{{ m.text }}
        </li>
      </ul>
    </div>

    <figure v-reveal="120" class="tr-hero-media">
      <img v-if="media" :src="media" :alt="`Foto de portada de ${shopName}`" fetchpriority="high" decoding="async" />
      <span v-else class="tr-hero-garment" aria-hidden="true"><GarmentLine name="tee" /></span>
      <span class="tr-hero-chip">{{ chip }}</span>
    </figure>
  </section>
</template>
