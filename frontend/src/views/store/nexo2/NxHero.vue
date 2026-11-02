<script setup>
// Portada del diseño NEXO: hero "cinema" oscuro del boceto tecnología premium.
// Retícula técnica tenue de fondo, titular con remate acentuado, CTAs, meta de
// negocio real (horario, localidad, años) y a la derecha la tarjeta del
// producto destacado con etiquetas flotantes. Reusa las piezas comunes
// (AppIcon, vReveal, useFeaturedCatalog, helpers de precio/oferta y horario)
// sin fetching nuevo; la piel vive en store-nexo2.css.
import { ref, computed, inject, onMounted, onBeforeUnmount } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { openStatus } from '../../../utils/storeHours.js'
import { productOffer, offerPct, effectivePrice } from '../../../api/catalog.api.js'
import { formatARS } from '../../../api/billing.api.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const ctx = inject('storePage')
const { slug, custom, shopName, nameFont, initial, location, showContact, showCatalog } = ctx
const servicesPage = ctx.showServices

const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })

const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
// Remate acentuado: las dos últimas palabras del titular van con el acento.
const titleParts = computed(() => {
  const words = heroTitle.value.split(/\s+/).filter(Boolean)
  if (words.length < 3) return { head: heroTitle.value, accent: '' }
  return { head: words.slice(0, -2).join(' '), accent: words.slice(-2).join(' ') }
})
const heroBadge = computed(() => (heroTitleIsName.value
  ? (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial'))
  : shopName.value))

const now = ref(new Date())
let clock = null
onMounted(() => { clock = setInterval(() => { now.value = new Date() }, 60000) })
onBeforeUnmount(() => clearInterval(clock))
const openNow = computed(() => (custom.value.show_hours !== false ? openStatus(custom.value.hours, now.value) : null))
// Meta del boceto: cifras cortas debajo del CTA (estado, localidad, años).
const heroMeta = computed(() => {
  const items = []
  if (openNow.value) items.push({ key: 'open', state: openNow.value.state, text: openNow.value.text })
  if (location.value) items.push({ key: 'loc', text: location.value })
  if (custom.value.about_years) items.push({ key: 'years', text: `${custom.value.about_years} años` })
  return items
})

const heroProduct = computed(() => {
  const list = shopCatalog.value.products || []
  return list.find((p) => p.image) || null
})
const heroImage = computed(() => heroProduct.value?.image || (ctx.hasDesignAdvanced.value ? custom.value.cover : '') || '')
const heroOffer = computed(() => (heroProduct.value ? productOffer(heroProduct.value) : null))
const heroPct = computed(() => (heroProduct.value ? offerPct(heroProduct.value) : 0))
const heroPrice = computed(() => (heroProduct.value ? formatARS(effectivePrice(heroProduct.value)) : ''))
const heroCat = computed(() => {
  const cat = shopCatalog.value.categories?.find((c) => c.id === heroProduct.value?.category)
  return cat?.name || ''
})
</script>

<template>
  <section class="nx-hero" aria-labelledby="nx-hero-title">
    <div class="nx-hero-bg" aria-hidden="true">
      <span class="nx-hero-grid"></span>
      <span class="nx-hero-glow nx-hero-glow-a"></span>
      <span class="nx-hero-glow nx-hero-glow-b"></span>
    </div>

    <div class="nx-container nx-hero-grid2">
      <div class="nx-hero-copy">
        <p v-reveal class="nx-eyebrow">// {{ heroBadge }}</p>
        <h1 id="nx-hero-title" v-reveal="70" class="nx-hero-title" :class="{ 'is-name': heroTitleIsName }" :style="heroTitleIsName ? nameFont : null">
          <span>{{ titleParts.head }}</span><span v-if="titleParts.accent" class="nx-acc">{{ ' ' + titleParts.accent }}</span>
        </h1>
        <p v-if="custom.description" v-reveal="140" class="nx-hero-sub">{{ custom.description }}</p>

        <div v-reveal="210" class="nx-hero-ctas">
          <RouterLink v-if="showCatalog" class="nx-btn" :to="catalogTo">Ver catálogo <AppIcon name="arrow-right" :size="16" /></RouterLink>
          <RouterLink v-if="servicesPage" class="nx-btn is-ghost" :to="servicesTo">Servicios <AppIcon name="arrow-right" :size="15" /></RouterLink>
          <a v-if="showContact" class="nx-hero-link" href="#contacto">Contacto</a>
        </div>

        <ul v-if="heroMeta.length" v-reveal="280" class="nx-hero-meta">
          <li v-for="m in heroMeta" :key="m.key" :class="{ 'is-open': m.state }">
            <span v-if="m.state" class="nx-dot" aria-hidden="true"></span>
            {{ m.text }}
          </li>
        </ul>
      </div>

      <!-- Tarjeta del producto destacado con etiquetas flotantes -->
      <div v-reveal="120" class="nx-hero-stage">
        <span class="nx-tag nx-tag-a" aria-hidden="true"><i></i>{{ heroOffer != null ? `-${heroPct}% OFF` : (heroCat || 'En stock') }}</span>
        <component
          :is="heroProduct ? 'RouterLink' : 'div'" class="nx-hero-card"
          :to="heroProduct ? productTo(heroProduct) : null"
          :aria-label="heroProduct ? `Ver ${heroProduct.name}` : null"
        >
          <span class="nx-hero-card-media">
            <img v-if="heroImage" :src="heroImage" :alt="heroProduct ? heroProduct.name : ''" loading="eager" decoding="async" fetchpriority="high" />
            <span v-else class="nx-hero-card-ph" aria-hidden="true">{{ initial }}</span>
            <span v-if="heroOffer != null" class="nx-hero-card-off">-{{ heroPct }}%</span>
          </span>
          <span class="nx-hero-card-body">
            <span v-if="heroCat" class="nx-hero-card-cat">{{ heroCat }}</span>
            <strong class="nx-hero-card-name">{{ heroProduct ? heroProduct.name : shopName }}</strong>
            <span class="nx-hero-card-foot">
              <span v-if="heroPrice" class="nx-hero-card-price">{{ heroPrice }}</span>
              <span class="nx-hero-card-go" aria-hidden="true"><AppIcon name="arrow-up-right" :size="15" /></span>
            </span>
          </span>
        </component>
        <span class="nx-tag nx-tag-b" aria-hidden="true"><i></i>{{ openNow?.state ? 'Abierto ahora' : 'Envío rápido' }}</span>
      </div>
    </div>
  </section>
</template>
