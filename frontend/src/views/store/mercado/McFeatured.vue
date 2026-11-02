<script setup>
// Destacados firma de MERCADO: grilla densa de productos reales con precio
// grande y descuento en verde. Se auto-oculta sin catálogo.
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import TplProductCard from '../../../components/store/TplProductCard.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import { effectivePrice, offerPct, productOffer } from '../../../api/catalog.api.js'
import { formatARS } from '../../../api/billing.api.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, showCatalog } = ctx
const router = useRouter()
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const title = computed(() => props.block?.props?.title?.trim() || 'Destacados')
const products = computed(() => shopCatalog.value.products.slice(0, 10))
const show = computed(() => showCatalog.value && products.value.length > 0)

const priceOf = (p) => formatARS(effectivePrice(p))
const oldOf = (p) => formatARS(p.price)
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))
</script>

<template>
  <section v-if="show" class="mc-featured" aria-labelledby="mc-featured-title">
    <div class="mc-wrap">
      <header class="mc-sec-head">
        <h2 id="mc-featured-title" v-reveal class="mc-sec-title">{{ title }}</h2>
        <RouterLink v-reveal="60" class="mc-sec-link" :to="catalogTo">
          Ver catálogo <AppIcon name="arrow-right" :size="13" aria-hidden="true" />
        </RouterLink>
      </header>
      <div class="mc-grid">
        <TplProductCard
          v-for="(p, i) in products" :key="p.id" v-reveal="(i % 5) * 55"
          class="mc-card" :p="p" :stars="custom.show_reviews" stars-icon="star"
          seal-shape="" :go="false" quick="" @open="openProduct"
        >
          <template #foot="{ p: product }">
            <span class="mc-price">
              <s v-if="productOffer(product) != null">{{ oldOf(product) }}</s>
              <strong>{{ priceOf(product) }}</strong>
            </span>
            <span v-if="productOffer(product) != null" class="mc-off">-{{ offerPct(product) }}%</span>
          </template>
        </TplProductCard>
      </div>
    </div>
  </section>
</template>
