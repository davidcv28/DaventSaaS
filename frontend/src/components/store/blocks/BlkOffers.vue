<script setup>
// Bloque 'offers': vitrina automática de productos en oferta (los que el
// catálogo marca con productOffer). Sin catálogo o sin ofertas vigentes
// se auto-oculta. Se apaga con show_offers. props.title pisa el título.
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { formatARS } from '../../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, offerEndsLabel, productDiscount } from '../../../api/catalog.api.js'
import AppIcon from '../../AppIcon.vue'
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
const title = computed(() => props.block?.props?.title?.trim() || 'Ofertas vigentes')
const endsOf = (p) => offerEndsLabel(productDiscount(p))
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))
</script>

<template>
  <section v-if="showCatalog && show" class="sp-offers" aria-labelledby="sp-offers-title">
    <div class="sp-container">
      <div class="sp-shop-featured-head">
        <div class="sp-shop-featured-copy">
          <p class="sp-shop-featured-eyebrow">Precios especiales</p>
          <h2 id="sp-offers-title" class="sp-shop-featured-title">{{ title }}</h2>
        </div>
        <RouterLink class="sp-shop-viewall" :to="catalogTo">Ver todo el catálogo <AppIcon name="arrow-right" :size="14" class="sp-arrow" /></RouterLink>
      </div>
      <div class="sp-shop-featured-grid">
        <article
          v-for="(p, i) in offers" :key="p.id" v-reveal="(i % 4) * 80"
          class="sp-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
          @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
        >
          <div class="sp-card-img">
            <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
            <span v-else class="sp-card-placeholder"><AppIcon name="package" :size="28" /></span>
            <span class="sp-card-quick" aria-hidden="true"><AppIcon name="eye" :size="15" /> Ver producto</span>
            <span class="sp-card-flag offer">-{{ offerPct(p) }}%</span>
            <span v-if="endsOf(p)" class="sp-card-flag ends">{{ endsOf(p) }}</span>
          </div>
          <div class="sp-card-body">
            <h3 class="sp-card-name">{{ p.name }}</h3>
            <div class="sp-card-foot">
              <span class="sp-card-price"><s class="sp-price-old">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</span>
              <span class="sp-card-go" aria-hidden="true">Ver más <AppIcon name="arrow-right" :size="16" /></span>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>
