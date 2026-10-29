<script setup>
// "Nueva temporada" de TRAMA: 4 productos recientes con la tarjeta compartida
// (TplProductCard) y una tira de talles reales tomada de las características
// del producto (Talle/Talla/Size). Si el producto no declara talles la tira no
// aparece; nunca se inventan medidas.
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import TplProductCard from '../../../components/store/TplProductCard.vue'
import AppIcon from '../../../components/AppIcon.vue'

const ctx = inject('storePage')
const { slug, custom, showCatalog } = ctx
const router = useRouter()
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const products = computed(() => featured.value.products.slice(0, 4))
const show = computed(() => showCatalog.value && products.value.length > 0)

const categoryName = (p) => featured.value.categories.find((c) => c.id === p.category)?.name || ''
const brandName = (p) => featured.value.brands.find((b) => b.id === p.brand)?.name || ''
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))

// Talle real desde features (clave libre del dueño); se muestran hasta 5.
function sizesOf(p) {
  const features = p?.features && typeof p.features === 'object' ? p.features : null
  if (!features) return []
  const key = Object.keys(features).find((k) => /talle|talla|size/i.test(k))
  if (!key) return []
  return String(features[key] || '')
    .split(/[,;/·]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 5)
}
</script>

<template>
  <section v-if="show" class="tr-new" aria-labelledby="tr-new-title">
    <div class="tr-container">
      <header class="tr-section-head">
        <h2 id="tr-new-title" v-reveal class="tr-section-title">Nueva temporada</h2>
        <RouterLink v-reveal class="tr-link" :to="catalogTo">Ver todo <AppIcon name="arrow-right" :size="14" class="tr-arrow" /></RouterLink>
      </header>
      <div class="tr-new-grid">
        <TplProductCard
          v-for="(p, i) in products" :key="p.id" v-reveal="(i % 4) * 70"
          class="tr-card" :p="p" :cat="categoryName(p)" :brand="brandName(p)"
          :stars="custom.show_reviews" stars-icon="star" seal-shape=""
          quick="Ver producto" go-label="Ver más" @open="openProduct"
        >
          <template #media-extra>
            <span v-if="sizesOf(p).length" class="tr-sizes" aria-hidden="true">
              <span v-for="s in sizesOf(p)" :key="s">{{ s }}</span>
            </span>
          </template>
        </TplProductCard>
      </div>
      <RouterLink class="tr-new-more" :to="catalogTo">Ver toda la colección <AppIcon name="arrow-right" :size="15" /></RouterLink>
    </div>
  </section>
</template>
