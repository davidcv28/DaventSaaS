<script setup>
// Vitrina firma de ATELIER: chips de categorías + grilla de prendas.
// Port del bloque de catálogo del diseño Atelier Otoño. Los chips filtran
// navegando al catálogo con ?category=<id>; la grilla usa la tarjeta
// compartida (TplProductCard) con la piel del diseño.
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import TplProductCard from '../../../components/store/TplProductCard.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, showCatalog } = ctx
const router = useRouter()
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const catTo = (id) => ({ ...catalogTo.value, query: { category: id } })
const products = computed(() => shopCatalog.value.products.slice(0, 8))
const chips = computed(() => shopCatalog.value.categories
  .map((c) => ({ id: c.id, name: c.name, count: shopCatalog.value.products.filter((p) => p.category === c.id).length }))
  .filter((c) => c.count > 0)
  .slice(0, 6))
const shopBrandOf = (p) => shopCatalog.value.brands.find((b) => b.id === p.brand)?.name || ''
const shopCatOf = (p) => shopCatalog.value.categories.find((c) => c.id === p.category)?.name || ''
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))
const title = computed(() => props.block?.props?.title?.trim() || 'La colección')
</script>

<template>
  <section v-if="showCatalog && products.length" class="at-shop" aria-labelledby="at-shop-title">
    <div class="at-wrap">
      <header class="at-shop-head">
        <p v-reveal class="at-kicker">Recién llegado</p>
        <h2 id="at-shop-title" v-reveal="30">{{ title }}</h2>
        <RouterLink class="at-viewall" :to="catalogTo">Ver todo <AppIcon name="arrow-right" :size="14" /></RouterLink>
      </header>

      <div v-if="chips.length" class="at-toolbar">
        <nav class="at-chips" aria-label="Filtrar por categoría">
          <RouterLink class="at-chip" :to="catalogTo">Todas</RouterLink>
          <RouterLink v-for="c in chips" :key="c.id" class="at-chip" :to="catTo(c.id)">{{ c.name }}</RouterLink>
        </nav>
      </div>

      <div class="at-grid">
        <TplProductCard
          v-for="(p, i) in products" :key="p.id" v-reveal="(i % 4) * 70"
          class="at-card" :p="p" :cat="shopCatOf(p)" :brand="shopBrandOf(p)"
          :stars="custom.show_reviews" stars-icon="star" seal-shape="" quick="Ver producto"
          go-label="Ver más" @open="openProduct"
        />
      </div>
    </div>
  </section>
</template>
