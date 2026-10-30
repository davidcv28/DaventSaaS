<script setup>
// Ofertas (§6.5-11): 3-up con acento en el precio y badge -N%. Reusa el
// renderer TplProductCard y la regla de ofertas efectivas del catálogo.
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { productOffer, offerEndsLabel, productDiscount } from '../../../../api/catalog.api.js'
import AppIcon from '../../../AppIcon.vue'
import TplProductCard from '../../TplProductCard.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx, catalogTo, productTo } = useRhLinks()
const { custom, showCatalog } = ctx
const router = useRouter()
const { featured } = useFeaturedCatalog()

const offers = computed(() => featured.value.products.filter((p) => productOffer(p) != null).slice(0, 3))
const show = computed(() => showCatalog.value && custom.value.show_offers !== false && offers.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || 'Ofertas vigentes')
const endsOf = (p) => offerEndsLabel(productDiscount(p))
const openProduct = (p) => router.push(productTo(p))
</script>

<template>
  <section v-if="show" class="rz-section rh-numbered rh-offers" aria-labelledby="rh-offers-title">
    <div class="rh-wrap">
      <header class="rh-head">
        <div class="rh-head-main">
          <p v-reveal class="rz-eyebrow">
            <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
            Precios especiales
          </p>
          <h2 id="rh-offers-title" v-reveal class="rh-title">{{ title }}</h2>
        </div>
        <RouterLink v-reveal="60" class="rh-link" :to="catalogTo">
          Ver todo el catálogo <AppIcon name="arrow-right" :size="15" />
        </RouterLink>
      </header>

      <div class="rh-offers-grid" :class="`rh-offers-grid--${offers.length}`">
        <TplProductCard
          v-for="(p, i) in offers" :key="p.id" v-reveal="60 * i"
          class="rh-offers-card" :p="p" :stars="custom.show_reviews" stars-icon="star"
          seal-shape="" offer-new quick="Ver producto" go-label="Ver más"
          :save="endsOf(p)" @open="openProduct"
        />
      </div>
    </div>
  </section>
</template>
