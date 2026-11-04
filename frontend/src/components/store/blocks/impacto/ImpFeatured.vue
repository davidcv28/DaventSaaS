<script setup>
// Bloque 'featured' de MODERNIMPACT: la vitrina de la portada como pliego
// numerado. Usa la tarjeta única de las plantillas (TplProductCard) con su
// prop `index` —el número 01/02/03 del pliego es parte del contrato de la
// tarjeta, no un pseudo-elemento de la piel— y la cabecera de sección con
// conteo, rango de precios y marcas en mono. Sin catálogo o sin productos se
// auto-oculta.
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../../config/env.js'
import { formatARS } from '../../../../api/billing.api.js'
import AppIcon from '../../../AppIcon.vue'
import TplProductCard from '../../TplProductCard.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const { slug, custom, showCatalog } = inject('storePage')
const router = useRouter()
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const title = computed(() => props.block?.props?.title?.trim() || 'Productos destacados')
const products = computed(() => featured.value.products.slice(0, 4))
const shopBrandOf = (p) => featured.value.brands.find((b) => b.id === p.brand)?.name || ''
const shopCatOf = (p) => featured.value.categories.find((c) => c.id === p.category)?.name || ''
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))
const total = computed(() => featured.value.products.length)

// Rango real de la vitrina: solo precios cargados, nunca un número inventado.
const priceRange = computed(() => {
  const prices = featured.value.products.map((p) => Number(p.price)).filter((n) => Number.isFinite(n) && n > 0)
  if (!prices.length) return ''
  const min = Math.min(...prices)
  const max = Math.max(...prices)
  return min === max ? formatARS(min) : `${formatARS(min)} — ${formatARS(max)}`
})
const brandCount = computed(() => featured.value.brands.filter((b) => featured.value.products.some((p) => p.brand === b.id)).length)
const headerLines = computed(() => [
  `${String(total.value).padStart(2, '0')} prendas publicadas`,
  [priceRange.value, brandCount.value ? `${String(brandCount.value).padStart(2, '0')} marcas` : 'series cortas']
    .filter(Boolean).join(' · ')
].filter(Boolean))
</script>

<template>
  <section v-if="showCatalog && products.length" class="mi-featured" aria-labelledby="mi-featured-title">
    <div class="mi-wrap">
      <header v-reveal class="mi-head">
        <div>
          <p class="mi-label">04 — Recién llegados</p>
          <h2 id="mi-featured-title">{{ title }}</h2>
        </div>
        <p class="mi-head-copy">
          <span v-for="line in headerLines" :key="line">{{ line }}</span>
        </p>
      </header>

      <div class="sp-shop-featured-grid mi-featured-grid">
        <TplProductCard
          v-for="(p, i) in products" :key="p.id" v-reveal="(i % 4) * 70"
          class="sp-card" :p="p" :cat="shopCatOf(p)" :brand="shopBrandOf(p)"
          :stars="custom.show_reviews" stars-icon="star" seal-shape=""
          :index="String(i + 1).padStart(2, '0')"
          quick="Ver pieza" go-label="Ver más" @open="openProduct"
        />
      </div>

      <div class="mi-featured-foot">
        <RouterLink v-if="showCatalog" v-reveal class="mi-featured-all" :to="catalogTo">
          Ver todo el catálogo <AppIcon name="arrow-right" :size="15" />
        </RouterLink>
        <p class="mi-featured-note">Pliego {{ String(products.length).padStart(2, '0') }} / {{ String(total).padStart(2, '0') }} · edición {{ new Date().getFullYear() }}</p>
      </div>
    </div>
  </section>
</template>
