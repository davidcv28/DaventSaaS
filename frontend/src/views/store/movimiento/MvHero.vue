<script setup>
// Portada firma de MOVIMIENTO (deporte / entrenamiento, nivel advanced).
// Editorial luminoso — composición PARTIDA (no la grilla de GyHero):
// mitad titular condensado gigante + chips de disciplinas, mitad foto con
// índice "01" y medidor de datos reales (años, disciplinas, membresías).
// Debajo corre el manifiesto ("No es una clase grupal. No es un
// gimnasio.") y la marquesina tipográfica de la casa.
import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { openStatus } from '../../../utils/storeHours.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import { storeContactLink, hasContactChannel } from '../../../api/stores.api.js'
import MvMarquee from './MvMarquee.vue'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const {
  slug, store, custom, shopName, initial, location, showContact, showCatalog, showGallery,
  hasDesignAdvanced
} = ctx
const servicesPage = ctx.showServices
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))

// Titular del dueño; sin titular el nombre del negocio es el h1. La
// última palabra se pinta en acento (firma editorial del diseño).
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value || 'Movete mejor, viví mejor.')
const titleParts = computed(() => {
  const words = heroTitle.value.split(/\s+/).filter(Boolean)
  if (words.length < 2) return { head: '', accent: heroTitle.value }
  return { head: words.slice(0, -1).join(' '), accent: words.slice(-1).join(' ') }
})
const text = computed(() => custom.value.description?.trim()
  || 'Entrenamiento personalizado en grupos chicos. Método, seguimiento y progreso real.')

// Manifiesto: la misión del dueño o la línea editorial del diseño.
const manifesto = computed(() => custom.value.about_mission?.trim()
  || 'No es una clase grupal. No es un gimnasio. Es un método.')

// Imagen: portada premium → primera foto de la galería → primera foto de
// producto del catálogo. Sin ninguna, el marco se resuelve con monograma.
const heroImage = computed(() => {
  if (hasDesignAdvanced.value && custom.value.cover) return { url: custom.value.cover, alt: `Portada de ${shopName.value}` }
  const gallery = Array.isArray(custom.value.gallery) ? custom.value.gallery : []
  if (showGallery.value && gallery[0]?.url) return { url: gallery[0].url, alt: `Imagen de ${shopName.value}` }
  const products = shopCatalog.value.products || []
  const withPhoto = products.find((p) => p.image)
  if (withPhoto) return { url: withPhoto.image, alt: withPhoto.name }
  return null
})

// Estado de atención en vivo, igual criterio que el resto de la web.
const now = ref(new Date())
let clock = null
onMounted(() => { clock = setInterval(() => { now.value = new Date() }, 60000) })
onBeforeUnmount(() => clearInterval(clock))
const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))

const whatsappUrl = computed(() => (hasContactChannel(custom.value, 'whatsapp') ? storeContactLink(slug.value, 'whatsapp') : ''))

const services = computed(() => (Array.isArray(custom.value.services) ? custom.value.services : []))
const plans = computed(() => (Array.isArray(custom.value.plans) ? custom.value.plans : []))

// Chips de disciplinas: servicios cargados; sin ellos, especialidades.
const chips = computed(() => {
  const titles = services.value.map((s) => String(s?.title || s?.name || '').trim()).filter(Boolean)
  if (titles.length) return titles.slice(0, 5)
  const specialties = String(custom.value.about_specialties || '')
    .split(/[·|,]/).map((s) => s.trim()).filter(Boolean)
  return specialties.slice(0, 5)
})

// Medidor de la ficha: datos reales derivados (años, disciplinas,
// membresías). Sin datos, la tarjeta no se pinta.
const meter = computed(() => {
  const rows = []
  if (custom.value.about_years) rows.push({ label: 'Años', value: Number(custom.value.about_years) || 0, max: 30 })
  if (services.value.length) rows.push({ label: 'Disciplinas', value: services.value.length, max: 10 })
  if (plans.value.length) rows.push({ label: 'Membresías', value: plans.value.length, max: 6 })
  return rows.slice(0, 3)
})

// Marquesina tipográfica: disciplinas o el trío editorial del diseño.
const ribbonItems = computed(() => (chips.value.length >= 3
  ? chips.value
  : ['Fuerza', 'Movimiento', 'Progreso']))

const primaryCta = computed(() => {
  if (plans.value.length) return { href: '#planes', label: 'Ver membresías' }
  if (showCatalog.value) return { to: catalogTo.value, label: 'Ver catálogo' }
  return { href: '#contacto', label: 'Empezar hoy' }
})
const secondaryCta = computed(() => {
  if (servicesPage.value) return { to: servicesTo.value, label: 'Clases y horarios', icon: 'calendar' }
  if (whatsappUrl.value) return { href: whatsappUrl.value, label: 'Clase de prueba', icon: 'whatsapp', external: true }
  if (showContact.value) return { href: '#contacto', label: 'Escribinos', icon: 'message-circle' }
  return null
})
</script>

<template>
  <section class="mv-hero" aria-labelledby="mv-hero-title">
    <div class="mv-wrap mv-hero-grid">
      <div class="mv-hero-copy">
        <div v-reveal class="mv-hero-top">
          <p class="mv-kicker"><span class="mv-kicker-idx">01</span> Estudio de movimiento</p>
          <span v-if="openNow" class="mv-live" :class="`is-${openNow.state}`">
            <i class="mv-live-dot" aria-hidden="true"></i>{{ openNow.text }}
          </span>
        </div>

        <h1 id="mv-hero-title" v-reveal="40" class="mv-hero-title">
          <span v-if="titleParts.head" class="mv-hero-line">{{ titleParts.head }}</span>
          <span class="mv-hero-accent">{{ titleParts.accent }}</span>
        </h1>

        <ul v-if="chips.length" v-reveal="90" class="mv-hero-chips">
          <li v-for="(c, i) in chips" :key="i">{{ c }}</li>
        </ul>

        <p v-reveal="120" class="mv-hero-lead">{{ text }}</p>

        <div v-reveal="170" class="mv-hero-ctas">
          <RouterLink v-if="primaryCta.to" class="mv-btn mv-btn--solid" :to="primaryCta.to">
            {{ primaryCta.label }} <AppIcon name="arrow-right" :size="18" aria-hidden="true" />
          </RouterLink>
          <a v-else class="mv-btn mv-btn--solid" :href="primaryCta.href">
            {{ primaryCta.label }} <AppIcon name="arrow-right" :size="18" aria-hidden="true" />
          </a>

          <RouterLink v-if="secondaryCta?.to" class="mv-btn mv-btn--ghost" :to="secondaryCta.to">
            <AppIcon :name="secondaryCta.icon" :size="17" aria-hidden="true" /> {{ secondaryCta.label }}
          </RouterLink>
          <a
            v-else-if="secondaryCta" class="mv-btn mv-btn--ghost" :href="secondaryCta.href"
            :target="secondaryCta.external ? '_blank' : null" :rel="secondaryCta.external ? 'noopener' : null"
          >
            <AppIcon :name="secondaryCta.icon" :size="17" aria-hidden="true" /> {{ secondaryCta.label }}
          </a>
        </div>
      </div>

      <figure v-reveal="130" class="mv-hero-media" :class="{ 'is-empty': !heroImage }">
        <img
          v-if="heroImage" :src="heroImage.url" :alt="heroImage.alt"
          loading="eager" decoding="async" fetchpriority="high"
        />
        <div v-else class="mv-hero-empty">
          <span class="mv-hero-initial" aria-hidden="true">{{ initial }}</span>
          <strong>{{ shopName }}</strong>
          <span class="mv-hero-empty-tag">Sala de entrenamiento</span>
        </div>

        <span class="mv-media-idx" aria-hidden="true">01</span>
        <span class="mv-media-code" aria-hidden="true">MV/{{ String(new Date().getFullYear()).slice(2) }}</span>
        <span v-if="location" class="mv-media-loc" aria-hidden="true">{{ location }}</span>

        <figcaption v-if="meter.length" class="mv-media-meter">
          <div v-for="(m, i) in meter" :key="i" class="mv-meter-row">
            <span class="mv-meter-label">{{ m.label }}</span>
            <b class="mv-meter-value">{{ String(m.value).padStart(2, '0') }}</b>
            <span class="mv-meter-track" aria-hidden="true">
              <i :style="{ width: `${Math.min(100, Math.max(8, Math.round((m.value / m.max) * 100)))}%` }"></i>
            </span>
          </div>
        </figcaption>
      </figure>
    </div>

    <p v-reveal="60" class="mv-wrap mv-hero-manifesto">
      <span class="mv-manifesto-idx" aria-hidden="true">///</span>{{ manifesto }}
    </p>

    <MvMarquee v-if="ribbonItems.length > 1" :items="ribbonItems" :speed="42" tone="line" />
  </section>
</template>
