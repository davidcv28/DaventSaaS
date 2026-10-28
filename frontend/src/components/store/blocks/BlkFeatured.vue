<script setup>
// Bloque 'featured': vitrina de productos destacados en la portada (8 en
// marketplace/Minimal/Boutique, 4 pliegos en Lookbook, Cobre y la
// colección de autor, 6 en Signature/Aurora). Sin catálogo o sin
// productos se auto-oculta. props.title pisa el título de la sección.
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../AppIcon.vue'
import TplProductCard from '../TplProductCard.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, pageTemplate, showCatalog } = ctx
const tpl = pageTemplate
const router = useRouter()
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const shopProducts = computed(() => shopCatalog.value.products.slice(0, tpl.value === 'lookbook' || tpl.value === 'cobre' ? 4 : tpl.value === 'signature' || tpl.value === 'aurora' ? 6 : 8))
const shopBrandOf = (p) => shopCatalog.value.brands.find((b) => b.id === p.brand)?.name || ''
const shopCatOf = (p) => shopCatalog.value.categories.find((c) => c.id === p.category)?.name || ''
// La tarjeta entera abre la ficha del producto (mismo destino que en el
// catálogo: /producto/<id> en subdominio, /<slug>/producto/<id> en plataforma).
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))

const eyebrow = computed(() => (tpl.value === 'lookbook' ? 'Selección de la edición'
  : tpl.value === 'signature' ? 'Curaduría de autor'
    : tpl.value === 'aurora' ? 'Cielo despejado'
      : tpl.value === 'cobre' || tpl.value === 'minimal' || tpl.value === 'boutique' ? 'Nueva temporada'
        : 'Recién llegados'))
const title = computed(() => props.block?.props?.title?.trim() || (tpl.value === 'lookbook' ? 'Pliegos destacados'
  : tpl.value === 'signature' ? 'La vitrina'
    : tpl.value === 'aurora' ? 'El observatorio'
      : tpl.value === 'cobre' || tpl.value === 'boutique' ? 'La colección'
        : tpl.value === 'minimal' ? 'Selección'
          : 'Productos destacados'))
const viewAll = computed(() => (tpl.value === 'lookbook' ? 'Ver índice completo'
  : tpl.value === 'cobre' ? 'Ver todo'
    : tpl.value === 'signature' ? 'Ver el catálogo completo'
      : tpl.value === 'boutique' ? 'Ver toda la colección'
        : 'Ver todo el catálogo'))
</script>

<template>
  <!-- Vitrina de productos destacados en la portada. -->
  <div v-if="showCatalog && shopProducts.length" class="sp-container sp-shop-featured">
    <div class="sp-shop-featured-head">
      <div class="sp-shop-featured-copy">
        <p class="sp-shop-featured-eyebrow">{{ eyebrow }}</p>
        <h2 class="sp-shop-featured-title">{{ title }}</h2>
      </div>
      <RouterLink class="sp-shop-viewall" :to="catalogTo">{{ viewAll }} <AppIcon name="arrow-right" :size="14" class="sp-arrow" /></RouterLink>
    </div>
    <div class="sp-shop-featured-grid">
      <TplProductCard
        v-for="(p, i) in shopProducts" :key="p.id" v-reveal="(i % 4) * 80"
        class="sp-card" :p="p" :cat="shopCatOf(p)" :brand="shopBrandOf(p)"
        :stars="custom.show_reviews" stars-icon="star" seal-shape="" quick="Ver producto"
        go-label="Ver más" @open="openProduct" />
    </div>
  </div>
</template>
