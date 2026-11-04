<script setup>
// Vitrina firma de MOVIMIENTO: productos como composición de revista —
// el primero abre en grande (índice 01) y el resto cierra la grilla.
// Oferta con badge de ahorro, precio tachado y CTA a la ficha. Sin
// catálogo o sin productos se auto-oculta.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { formatARS } from '../../../api/billing.api.js'
import { offerPct } from '../../../api/catalog.api.js'
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
const products = computed(() => shopCatalog.value.products.slice(0, 4))
const catOf = (p) => shopCatalog.value.categories.find((c) => c.id === p.category)?.name || ''
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const title = computed(() => props.block?.props?.title?.trim() || 'La tienda del estudio')
const priceOf = (p) => {
  const value = p.offer_price != null ? p.offer_price : p.price
  return value ? formatARS(value) : 'Consultar'
}
const oldOf = (p) => (p.offer_price != null && p.price ? formatARS(p.price) : '')
const saveOf = (p) => {
  const pct = offerPct(p)
  return pct ? `−${pct}%` : ''
}
</script>

<template>
  <section v-if="showCatalog && products.length" class="mv-shop" aria-labelledby="mv-shop-title">
    <div class="mv-wrap">
      <header v-reveal class="mv-shop-head">
        <div>
          <p class="mv-eyebrow"><span class="mv-eyebrow-idx">{{ String(sectionIndex || 1).padStart(2, '0') }}</span> Tienda</p>
          <h2 id="mv-shop-title">{{ title }}</h2>
        </div>
        <RouterLink class="mv-shop-all" :to="catalogTo">
          Ver catálogo completo <AppIcon name="arrow-right" :size="15" aria-hidden="true" />
        </RouterLink>
      </header>
      <div class="mv-grid">
        <article
          v-for="(p, i) in products" :key="p.id" v-reveal="(i % 4) * 60"
          class="mv-card" :class="{ 'is-lead': i === 0, 'is-offer': p.offer_price != null }"
        >
          <RouterLink class="mv-card-link" :to="productTo(p)">
            <span class="mv-card-media" :class="{ 'is-empty': !p.image }">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" decoding="async" />
              <span v-else class="mv-card-media-mark" aria-hidden="true">MV</span>
              <span class="mv-card-index" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
              <span v-if="saveOf(p)" class="mv-card-flag">{{ saveOf(p) }}</span>
            </span>
            <span class="mv-card-body">
              <span v-if="catOf(p)" class="mv-card-cat">{{ catOf(p) }}</span>
              <strong class="mv-card-name">{{ p.name }}</strong>
              <span class="mv-card-price">
                {{ priceOf(p) }}
                <s v-if="oldOf(p)">{{ oldOf(p) }}</s>
              </span>
            </span>
            <span class="mv-card-go"><AppIcon name="arrow-up-right" :size="17" aria-hidden="true" /></span>
          </RouterLink>
        </article>
      </div>
    </div>
  </section>
</template>
