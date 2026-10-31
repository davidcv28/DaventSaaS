<script setup>
// Hero firma de MERCADO (marketplace, nivel plus).
// Banda amarilla con titular, buscador visual (la barra real vive en el
// masthead), CTAs y una tarjeta de oferta destacada sobre un collage de
// productos reales del catálogo. Sin fotos, la tarjeta queda tonal.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import { effectivePrice, offerPct, productOffer } from '../../../api/catalog.api.js'
import { formatARS } from '../../../api/billing.api.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, shopName, location, showCatalog } = ctx
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })

const products = computed(() => featured.value.products)
const categories = computed(() => featured.value.categories)
const offers = computed(() => products.value.filter((p) => productOffer(p) != null))

const headline = computed(() => custom.value.headline?.trim() || shopName.value || 'Todo lo que buscás, en un solo lugar')
const text = computed(() => custom.value.description?.trim()
  || 'Explorá el catálogo completo, compará precios y consultá por lo que te interesa.')
const ctaLabel = computed(() => (offers.value.length ? 'Ver ofertas' : 'Ver catálogo'))
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const isCentered = computed(() => props.block?.variant === 'centered')

const lead = computed(() => offers.value[0] || products.value[0] || null)
const leadPct = computed(() => (lead.value ? offerPct(lead.value) : 0))
const leadPrice = computed(() => (lead.value ? formatARS(effectivePrice(lead.value)) : ''))
const leadOld = computed(() => (lead.value && productOffer(lead.value) != null ? formatARS(lead.value.price) : ''))
const tiles = computed(() => products.value.filter((p) => p.image && p.id !== lead.value?.id).slice(0, 3))
const tones = [
  'color-mix(in srgb, var(--mc-blue) 8%, var(--mc-surface))',
  'color-mix(in srgb, var(--mc-yellow) 18%, var(--mc-surface))',
  'color-mix(in srgb, var(--mc-blue) 4%, var(--mc-surface))'
]
</script>

<template>
  <section class="mc-hero" :class="{ 'is-centered': isCentered }" aria-labelledby="mc-hero-title">
    <div class="mc-wrap mc-hero-grid">
      <div class="mc-hero-copy">
        <p v-reveal class="mc-kicker"><AppIcon name="percent" :size="13" aria-hidden="true" /> Ofertas y novedades</p>
        <h1 id="mc-hero-title" v-reveal="40">{{ headline }}</h1>
        <p v-reveal="80" class="mc-hero-text">{{ text }}</p>
        <div v-reveal="120" class="mc-hero-actions">
          <RouterLink v-if="showCatalog" class="mc-btn mc-btn--primary" :to="catalogTo">
            {{ ctaLabel }} <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
          </RouterLink>
          <a v-if="whatsappUrl" class="mc-btn mc-btn--ghost" :href="whatsappUrl" target="_blank" rel="noopener">
            <AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Consultar
          </a>
        </div>
        <ul v-reveal="160" class="mc-hero-stats">
          <li><strong>{{ products.length }}</strong> productos</li>
          <li v-if="categories.length"><strong>{{ categories.length }}</strong> categorías</li>
          <li v-if="location"><AppIcon name="map-pin" :size="12" aria-hidden="true" /> {{ location }}</li>
        </ul>
      </div>

      <div v-reveal="60" class="mc-hero-art">
        <div v-if="tiles.length" class="mc-hero-tiles" aria-hidden="true">
          <span
            v-for="(t, i) in tiles" :key="t.id"
            class="mc-hero-tile" :class="`mc-hero-tile--${i + 1}`"
            :style="{ background: tones[i] }"
          >
            <img :src="t.image" alt="" loading="lazy" />
          </span>
        </div>
        <RouterLink v-if="lead" class="mc-hero-card" :to="productTo(lead)">
          <span v-if="leadPct" class="mc-hero-badge">-{{ leadPct }}%</span>
          <span class="mc-hero-media">
            <img v-if="lead.image" :src="lead.image" :alt="lead.name" loading="lazy" />
            <AppIcon v-else name="package" :size="42" />
          </span>
          <span class="mc-hero-card-body">
            <span class="mc-hero-card-name">{{ lead.name }}</span>
            <span class="mc-hero-card-price">
              <s v-if="leadOld">{{ leadOld }}</s>
              <strong>{{ leadPrice }}</strong>
            </span>
            <span class="mc-hero-card-link">Ver producto <AppIcon name="arrow-right" :size="13" aria-hidden="true" /></span>
          </span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
