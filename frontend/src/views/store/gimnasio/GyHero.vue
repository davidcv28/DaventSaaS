<script setup>
// Portada firma de GIMNASIO (deporte / fitness, nivel plus).
// Lenguaje "sala de fuerza": tinta oliva, hueso y lima. Titular Barlow
// Condensed gigante, ficha técnica con horarios reales, sello giratorio,
// medidor de intensidad y cinta de disciplinas en loop. Todo el adorno sale
// de datos de la empresa (servicios, horarios, años, sede); sin datos, el
// bloque se resuelve con el monograma y una placa técnica vacía.
import { computed, inject, onBeforeUnmount, onMounted, ref } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { openStatus } from '../../../utils/storeHours.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import { storeContactLink, hasContactChannel } from '../../../api/stores.api.js'
import GyMarquee from './GyMarquee.vue'

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

// Titular del dueño; sin titular el nombre del negocio es el h1. Las dos
// últimas palabras se pintan en lima (firma del diseño: "…SIN EXCUSAS").
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value || 'Entrená fuerte, sin excusas.')
const titleParts = computed(() => {
  const words = heroTitle.value.split(/\s+/).filter(Boolean)
  if (words.length < 2) return { head: '', accent: heroTitle.value }
  const cut = words.length >= 3 ? 2 : 1
  return { head: words.slice(0, -cut).join(' '), accent: words.slice(-cut).join(' ') }
})
const text = computed(() => custom.value.description?.trim()
  || 'Musculación, funcional y clases todos los días. Primera clase de prueba gratis.')

// Imagen: portada premium → primera foto de la galería → primera foto de
// producto del catálogo. Sin ninguna, la placa se resuelve con el monograma.
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

const address = computed(() => store.value?.location_address || '')
const meta = computed(() => {
  const items = []
  if (location.value) items.push({ key: 'loc', text: location.value })
  if (address.value) items.push({ key: 'address', text: address.value })
  if (custom.value.about_years) items.push({ key: 'years', text: `${custom.value.about_years} años entrenando` })
  return items
})
const metaIcon = { loc: 'map-pin', address: 'store', years: 'trending-up' }
const whatsappUrl = computed(() => (hasContactChannel(custom.value, 'whatsapp') ? storeContactLink(slug.value, 'whatsapp') : ''))
const centered = computed(() => props.block?.variant === 'centered')

const services = computed(() => (Array.isArray(custom.value.services) ? custom.value.services : []))
const plans = computed(() => (Array.isArray(custom.value.plans) ? custom.value.plans : []))
const hours = computed(() => (custom.value.show_hours !== false && Array.isArray(custom.value.hours) ? custom.value.hours : [])
  .filter((h) => String(h?.label || '').trim() && String(h?.value || '').trim()))

// Datos reales derivados: años, disciplinas, membresías y sede. No inventamos
// cifras: si el dueño no cargó el dato, la fila se acorta sola.
const facts = computed(() => {
  const rows = []
  if (custom.value.about_years) rows.push({ value: `+${custom.value.about_years}`, label: 'años' })
  if (services.value.length) rows.push({ value: String(services.value.length).padStart(2, '0'), label: 'disciplinas' })
  if (plans.value.length) rows.push({ value: String(plans.value.length).padStart(2, '0'), label: 'membresías' })
  if (location.value) rows.push({ value: location.value, label: 'sede', wide: true })
  return rows.slice(0, 4)
})

// Cinta: disciplinas del negocio. Sin servicios, sus especialidades; sin
// nada, nombre + sede para no inventar una oferta que no existe.
const ribbonItems = computed(() => {
  const titles = services.value.map((s) => String(s?.title || s?.name || '').trim()).filter(Boolean)
  if (titles.length) return titles.slice(0, 10)
  const specialties = String(custom.value.about_specialties || '')
    .split(/[·|,]/).map((s) => s.trim()).filter(Boolean)
  if (specialties.length) return specialties.slice(0, 8)
  return [shopName.value, location.value, 'Entrenamiento'].filter(Boolean)
})

const ghostWord = computed(() => String(shopName.value || '').trim().split(/\s+/)[0].slice(0, 12).toUpperCase())
const since = computed(() => {
  const years = Number(custom.value.about_years) || 0
  return years ? `DESDE ${new Date().getFullYear() - years}` : 'ENTRENÁ HOY'
})
const stampText = computed(() => `FUERZA · TÉCNICA · CONSTANCIA · ${since.value} · `)
const kicker = computed(() => `Centro de entrenamiento${location.value ? ` · ${location.value}` : ''}`)

const primaryCta = computed(() => {
  if (plans.value.length && custom.value.show_plans !== false) return { href: '#planes', label: 'Ver membresías' }
  if (showCatalog.value) return { to: catalogTo.value, label: 'Ver planes y tienda' }
  return { href: '#contacto', label: 'Empezar hoy' }
})
const secondaryCta = computed(() => {
  if (servicesPage.value) return { to: servicesTo.value, label: 'Clases y horarios', icon: 'calendar' }
  if (whatsappUrl.value) return { href: whatsappUrl.value, label: 'Clase de prueba', icon: 'whatsapp', external: true }
  if (showContact.value) return { href: '#contacto', label: 'Escribinos', icon: 'message-circle' }
  return null
})
// Medidor de intensidad decorativo: tres barras que laten desfasadas.
const intensity = [72, 46, 88]
</script>

<template>
  <section class="gy-hero" :class="{ 'is-centered': centered }" aria-labelledby="gy-hero-title">
    <div class="gy-hero-bg" aria-hidden="true">
      <span class="gy-hero-ghost">{{ ghostWord }}</span>
      <span class="gy-hero-lines"></span>
    </div>

    <div class="gy-wrap gy-hero-grid">
      <div class="gy-hero-copy">
        <div v-reveal class="gy-hero-top">
          <p class="gy-kicker"><span class="gy-kicker-idx">01</span> {{ kicker }}</p>
          <span v-if="openNow" class="gy-live" :class="`is-${openNow.state}`">
            <i class="gy-live-dot" aria-hidden="true"></i>{{ openNow.text }}
          </span>
        </div>

        <h1 id="gy-hero-title" v-reveal="40" class="gy-hero-title">
          <span v-if="titleParts.head" class="gy-hero-line">{{ titleParts.head }}</span>
          <span class="gy-hero-accent">{{ titleParts.accent }}</span>
        </h1>

        <p v-reveal="110" class="gy-hero-lead">{{ text }}</p>

        <div v-reveal="170" class="gy-hero-ctas">
          <RouterLink v-if="primaryCta.to" class="gy-btn gy-btn--solid" :to="primaryCta.to">
            {{ primaryCta.label }} <AppIcon name="arrow-right" :size="18" aria-hidden="true" />
          </RouterLink>
          <a v-else class="gy-btn gy-btn--solid" :href="primaryCta.href">
            {{ primaryCta.label }} <AppIcon name="arrow-right" :size="18" aria-hidden="true" />
          </a>

          <RouterLink v-if="secondaryCta?.to" class="gy-btn gy-btn--ghost" :to="secondaryCta.to">
            <AppIcon :name="secondaryCta.icon" :size="17" aria-hidden="true" /> {{ secondaryCta.label }}
          </RouterLink>
          <a
            v-else-if="secondaryCta" class="gy-btn gy-btn--ghost" :href="secondaryCta.href"
            :target="secondaryCta.external ? '_blank' : null" :rel="secondaryCta.external ? 'noopener' : null"
          >
            <AppIcon :name="secondaryCta.icon" :size="17" aria-hidden="true" /> {{ secondaryCta.label }}
          </a>
        </div>

        <ul v-if="meta.length" v-reveal="230" class="gy-hero-meta">
          <li v-for="m in meta" :key="m.key">
            <AppIcon :name="metaIcon[m.key] || 'check'" :size="17" class="gy-meta-ic" aria-hidden="true" />
            {{ m.text }}
          </li>
        </ul>
      </div>

      <figure v-reveal="130" class="gy-hero-plate" :class="{ 'is-empty': !heroImage }">
        <img
          v-if="heroImage" :src="heroImage.url" :alt="heroImage.alt"
          loading="eager" decoding="async" fetchpriority="high"
        />
        <div v-else class="gy-hero-empty">
          <span class="gy-hero-initial" aria-hidden="true">{{ initial }}</span>
          <span class="gy-hero-eq" aria-hidden="true">
            <i v-for="(h, i) in intensity" :key="i" :style="{ '--h': `${h}%`, '--d': `${i * .18}s` }"></i>
          </span>
          <strong>{{ shopName }}</strong>
          <span class="gy-hero-empty-tag">Sala principal</span>
        </div>

        <span class="gy-plate-frame" aria-hidden="true"></span>
        <span class="gy-plate-code" aria-hidden="true">GY/{{ String(new Date().getFullYear()).slice(2) }}</span>
        <span class="gy-plate-vert" aria-hidden="true">{{ location || 'Entrenamiento' }}</span>
        <span class="gy-plate-scan" aria-hidden="true"></span>

        <figcaption v-if="hours.length" class="gy-plate-hours">
          <p class="gy-plate-hours-h"><AppIcon name="clock" :size="14" aria-hidden="true" /> Horarios</p>
          <div v-for="(h, i) in hours.slice(0, 3)" :key="i" class="gy-plate-hour">
            <span>{{ h.label }}</span>
            <b>{{ h.value }}</b>
          </div>
          <p v-if="hours.length > 3" class="gy-plate-hours-more">+{{ hours.length - 3 }} días más</p>
        </figcaption>

        <div class="gy-plate-stamp" aria-hidden="true">
          <svg viewBox="0 0 120 120" role="presentation" focusable="false">
            <defs>
              <path id="gy-stamp-path" d="M60,60 m-44,0 a44,44 0 1,1 88,0 a44,44 0 1,1 -88,0"></path>
            </defs>
            <text>
              <textPath href="#gy-stamp-path" startOffset="0">{{ stampText }}</textPath>
            </text>
          </svg>
          <span class="gy-plate-stamp-core"><AppIcon name="dumbbell" :size="22" /></span>
        </div>
      </figure>
    </div>

    <div v-if="facts.length" v-reveal="60" class="gy-hero-facts">
      <div class="gy-wrap gy-facts-row">
        <div v-for="(f, i) in facts" :key="i" class="gy-fact" :class="{ 'is-wide': f.wide }">
          <b>{{ f.value }}</b>
          <span>{{ f.label }}</span>
        </div>
        <span class="gy-facts-mark" aria-hidden="true">///</span>
      </div>
    </div>

    <GyMarquee v-if="ribbonItems.length > 1" :items="ribbonItems" :speed="36" tone="ink" />
  </section>
</template>
