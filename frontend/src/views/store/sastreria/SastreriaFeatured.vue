<script setup>
// Vitrina firma de SASTRERÍA: prendas en filas de fichero (imagen, ficha y
// precio alineados a la regla), con encabezado editorial y contador de
// temporada. Sin catálogo o sin productos se auto-oculta.
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { formatARS } from '../../../api/billing.api.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, showCatalog } = ctx
const router = useRouter()
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const products = computed(() => shopCatalog.value.products.slice(0, 6))
const catOf = (p) => shopCatalog.value.categories.find((c) => c.id === p.category)?.name || ''
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))
const title = computed(() => props.block?.props?.title?.trim() || 'La colección')
const year = computed(() => new Date().getFullYear())
const priceOf = (p) => {
  const value = p.offer_price != null ? p.offer_price : p.price
  return value ? formatARS(value) : 'Consultar'
}
const oldOf = (p) => (p.offer_price != null && p.price ? formatARS(p.price) : '')
</script>

<template>
  <section v-if="showCatalog && products.length" class="ss-shop" aria-labelledby="ss-shop-title">
    <div class="ss-wrap">
      <header v-reveal class="ss-head">
        <h2 id="ss-shop-title">{{ title }}</h2>
        <span>{{ year }} · Otoño invierno</span>
      </header>
      <div class="ss-lookbook">
        <article
          v-for="(p, i) in products" :key="p.id" v-reveal="(i % 4) * 60"
          class="ss-row"
        >
          <RouterLink class="ss-row-link" :to="productTo(p)">
            <img v-if="p.image" class="ss-row-img" :src="p.image" :alt="p.name" loading="lazy" />
            <span v-else class="ss-row-img is-empty" aria-hidden="true"><AppIcon name="package" :size="30" /></span>
            <span class="ss-row-copy">
              <span class="ss-row-cat">{{ catOf(p) }}</span>
              <strong class="ss-row-name">{{ p.name }}</strong>
              <small v-if="p.description" class="ss-row-desc">{{ p.description }}</small>
            </span>
            <span class="ss-row-price">
              {{ priceOf(p) }}
              <s v-if="oldOf(p)">{{ oldOf(p) }}</s>
            </span>
          </RouterLink>
        </article>
      </div>
      <RouterLink v-if="showCatalog" v-reveal class="ss-viewall" :to="catalogTo">
        Ver el catálogo completo <AppIcon name="arrow-right" :size="14" />
      </RouterLink>
    </div>
  </section>
</template>
