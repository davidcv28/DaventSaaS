<script setup>
// Vitrina firma de GIMNASIO: productos/planes como tarjetas de pista —
// imagen con índice, nombre condensado, precio gigante y CTA recto; la
// oferta va en placa lima. Sin catálogo o sin productos se auto-oculta.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { formatARS } from '../../../api/billing.api.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({
  block: { type: Object, default: null },
  sectionIndex: { type: Number, default: 0 }
})

const ctx = inject('storePage')
const { slug, showCatalog } = ctx
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const products = computed(() => shopCatalog.value.products.slice(0, 3))
const catOf = (p) => shopCatalog.value.categories.find((c) => c.id === p.category)?.name || ''
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const title = computed(() => props.block?.props?.title?.trim() || 'Planes y tienda')
const priceOf = (p) => {
  const value = p.offer_price != null ? p.offer_price : p.price
  return value ? formatARS(value) : 'Consultar'
}
const oldOf = (p) => (p.offer_price != null && p.price ? formatARS(p.price) : '')
</script>

<template>
  <section v-if="showCatalog && products.length" class="gy-shop" aria-labelledby="gy-shop-title">
    <div class="gy-wrap">
      <header v-reveal class="gy-shop-head">
        <div>
          <p class="gy-eyebrow"><span class="gy-eyebrow-idx">{{ String(sectionIndex || 1).padStart(2, '0') }}</span> Tienda</p>
          <h2 id="gy-shop-title">{{ title }}</h2>
        </div>
        <RouterLink class="gy-shop-all" :to="catalogTo">
          Ver catálogo completo <AppIcon name="arrow-right" :size="15" aria-hidden="true" />
        </RouterLink>
      </header>
      <div class="gy-grid">
        <article
          v-for="(p, i) in products" :key="p.id" v-reveal="(i % 3) * 60"
          class="gy-card" :class="{ 'is-offer': p.offer_price != null }"
        >
          <RouterLink class="gy-card-link" :to="productTo(p)">
            <span class="gy-card-media" :class="{ 'is-empty': !p.image }">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" decoding="async" />
              <template v-else>
                <span class="gy-card-media-mark" aria-hidden="true">GY</span>
                <span class="gy-card-media-lines" aria-hidden="true"></span>
              </template>
              <span class="gy-card-index" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
              <span v-if="p.offer_price != null" class="gy-card-flag">Oferta</span>
            </span>
            <span class="gy-card-body">
              <span v-if="catOf(p)" class="gy-card-cat">{{ catOf(p) }}</span>
              <strong class="gy-card-name">{{ p.name }}</strong>
              <span class="gy-card-price">
                {{ priceOf(p) }}
                <s v-if="oldOf(p)">{{ oldOf(p) }}</s>
              </span>
              <span class="gy-card-go">Ver producto <AppIcon name="arrow-up-right" :size="16" aria-hidden="true" /></span>
            </span>
          </RouterLink>
        </article>
      </div>
    </div>
  </section>
</template>
