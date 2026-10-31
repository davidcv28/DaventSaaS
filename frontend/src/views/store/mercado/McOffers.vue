<script setup>
// Ofertas firma de MERCADO: riel horizontal de productos con descuento real
// (productOffer). El badge verde y el precio tachado salen de los datos;
// sin ofertas vigentes la sección se auto-oculta.
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import TplProductCard from '../../../components/store/TplProductCard.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import { effectivePrice, offerPct, productDiscount, productOffer, offerEndsLabel } from '../../../api/catalog.api.js'
import { formatARS } from '../../../api/billing.api.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, showCatalog } = ctx
const router = useRouter()
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const title = computed(() => props.block?.props?.title?.trim() || 'Ofertas')
const offers = computed(() => shopCatalog.value.products
  .filter((p) => productOffer(p) != null)
  .sort((a, b) => offerPct(b) - offerPct(a))
  .slice(0, 8))
const show = computed(() => custom.value.show_offers !== false && showCatalog.value && offers.value.length > 0)

const priceOf = (p) => formatARS(effectivePrice(p))
const oldOf = (p) => formatARS(p.price)
const endsOf = (p) => offerEndsLabel(productDiscount(p))
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))
</script>

<template>
  <section v-if="show" class="mc-offers" aria-labelledby="mc-offers-title">
    <div class="mc-wrap">
      <header class="mc-sec-head">
        <h2 id="mc-offers-title" v-reveal class="mc-sec-title">{{ title }}</h2>
        <RouterLink v-reveal="60" class="mc-sec-link" :to="catalogTo">
          Ver todo el catálogo <AppIcon name="arrow-right" :size="13" aria-hidden="true" />
        </RouterLink>
      </header>
      <div class="mc-rail">
        <TplProductCard
          v-for="(p, i) in offers" :key="p.id" v-reveal="(i % 4) * 60"
          class="mc-card" :p="p" :stars="custom.show_reviews" stars-icon="star"
          seal-shape="" :go="false" quick=""
          :save="endsOf(p) || ''" @open="openProduct"
        >
          <template #foot="{ p: product }">
            <span class="mc-price">
              <s v-if="productOffer(product) != null">{{ oldOf(product) }}</s>
              <strong>{{ priceOf(product) }}</strong>
            </span>
            <span class="mc-off">-{{ offerPct(product) }}%</span>
          </template>
        </TplProductCard>
      </div>
    </div>
  </section>
</template>
