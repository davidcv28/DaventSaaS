<script setup>
// Bloque 'offers': vitrina automática de productos en oferta (los que el
// catálogo marca con productOffer). Sin catálogo o sin ofertas vigentes
// se auto-oculta. Se apaga con show_offers. props.title pisa el título.
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { productOffer, offerEndsLabel, productDiscount } from '../../../api/catalog.api.js'
import AppIcon from '../../AppIcon.vue'
import TplProductCard from '../TplProductCard.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, showCatalog } = ctx
const router = useRouter()
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const offers = computed(() => shopCatalog.value.products.filter((p) => productOffer(p) != null).slice(0, 4))
const show = computed(() => custom.value.show_offers !== false && offers.value.length > 0)
const variant = computed(() => props.block?.variant || 'grid')
const title = computed(() => props.block?.props?.title?.trim() || 'Ofertas vigentes')
const endsOf = (p) => offerEndsLabel(productDiscount(p))
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))
</script>

<template>
  <section v-if="showCatalog && show" class="sp-offers" :class="`is-${variant}`" :data-blk-variant="variant !== 'grid' ? variant : null" aria-labelledby="sp-offers-title">
    <div class="sp-container">
      <div class="sp-shop-featured-head">
        <div class="sp-shop-featured-copy">
          <p class="sp-shop-featured-eyebrow">Precios especiales</p>
          <h2 id="sp-offers-title" class="sp-shop-featured-title">{{ title }}</h2>
        </div>
        <RouterLink class="sp-shop-viewall" :to="catalogTo">Ver todo el catálogo <AppIcon name="arrow-right" :size="14" class="sp-arrow" /></RouterLink>
      </div>
      <div class="sp-shop-featured-grid">
        <TplProductCard
          v-for="(p, i) in offers" :key="p.id" v-reveal="(i % 4) * 80"
          class="sp-card" :p="p" :stars="custom.show_reviews" stars-icon="star"
          seal-shape="" offer-new quick="Ver producto" go-label="Ver más"
          :save="endsOf(p)" @open="openProduct" />
      </div>
    </div>
  </section>
</template>
