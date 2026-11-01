<script setup>
// Vitrina firma de GIMNASIO: productos/planes como tarjetas de programa —
// índice de pista (01, 02…), nombre condensado grande, categoría y precio
// sobre tinta oscura con borde duro. Sin catálogo o sin productos se
// auto-oculta.
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { formatARS } from '../../../api/billing.api.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, showCatalog } = ctx
const router = useRouter()
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const products = computed(() => shopCatalog.value.products.slice(0, 6))
const catOf = (p) => shopCatalog.value.categories.find((c) => c.id === p.category)?.name || ''
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))
const title = computed(() => props.block?.props?.title?.trim() || 'Planes y tienda')
const priceOf = (p) => {
  const value = p.offer_price != null ? p.offer_price : p.price
  return value ? formatARS(value) : 'Consultar'
}
const oldOf = (p) => (p.offer_price != null && p.price ? formatARS(p.price) : '')
const idx = (i) => String(i + 1).padStart(2, '0')
</script>

<template>
  <section v-if="showCatalog && products.length" class="gy-shop" aria-labelledby="gy-shop-title">
    <div class="gy-wrap">
      <header v-reveal class="gy-shop-head">
        <h2 id="gy-shop-title">{{ title }}</h2>
        <span>{{ products.length }} ítems en temporada</span>
      </header>
      <div class="gy-grid">
        <article
          v-for="(p, i) in products" :key="p.id" v-reveal="(i % 3) * 60"
          class="gy-card"
        >
          <RouterLink class="gy-card-link" :to="productTo(p)">
            <span class="gy-card-idx" aria-hidden="true">{{ idx(i) }}</span>
            <img v-if="p.image" class="gy-card-img" :src="p.image" :alt="p.name" loading="lazy" />
            <span v-else class="gy-card-img is-empty" aria-hidden="true"><AppIcon name="package" :size="30" /></span>
            <span class="gy-card-body">
              <span class="gy-card-cat">{{ catOf(p) }}</span>
              <strong class="gy-card-name">{{ p.name }}</strong>
              <span class="gy-card-price">
                {{ priceOf(p) }}
                <s v-if="oldOf(p)">{{ oldOf(p) }}</s>
              </span>
            </span>
          </RouterLink>
        </article>
      </div>
      <RouterLink v-reveal class="gy-viewall" :to="catalogTo">
        Ver todo el catálogo <AppIcon name="arrow-right" :size="14" />
      </RouterLink>
    </div>
  </section>
</template>
