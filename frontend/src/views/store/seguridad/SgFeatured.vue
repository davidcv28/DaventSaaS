<script setup>
// "Productos destacados" del diseño SEGURIDAD: 4 tarjetas con la geometría
// compartida (TplProductCard) re-skineada por CSS y los dos detalles de la
// referencia que la tarjeta genérica no trae: chips técnicos de la ficha
// (clase A·B·C, capacidad…) y el CTA "Consultar por WhatsApp" por producto.
// Los datos salen del catálogo destacado real; sin productos se auto-oculta.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { effectivePrice, offerPct, productOffer } from '../../../api/catalog.api.js'
import { formatARS } from '../../../api/billing.api.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import { useRouter } from 'vue-router'
import TplProductCard from '../../../components/store/TplProductCard.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom, slug, showCatalog } = ctx
const router = useRouter()
const { featured: shopCatalog } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const title = computed(() => props.block?.props?.title?.trim() || 'Productos destacados')
const products = computed(() => shopCatalog.value.products.slice(0, 4))

const catOf = (p) => shopCatalog.value.categories.find((c) => c.id === p.category)?.name || ''
const brandOf = (p) => shopCatalog.value.brands.find((b) => b.id === p.brand)?.name || ''
// Chips técnicos: los primeros 3 valores cargados por el dueño en la ficha.
const specChips = (p) => Object.entries(p?.features || {})
  .map(([k, v]) => (String(v || '').trim() ? `${k} ${v}` : k))
  .filter(Boolean)
  .slice(0, 3)

const priceOf = (p) => formatARS(effectivePrice(p))
const oldPriceOf = (p) => formatARS(p.price)
const offerOf = (p) => productOffer(p) != null
const pctOf = (p) => offerPct(p)

const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))
// WhatsApp del dueño con el producto citado (mensaje armado en el cliente,
// igual que el resto de la web: la plataforma nunca persiste pedidos).
const waHref = (p) => {
  const digits = String(custom.value.whatsapp || '').replace(/\D/g, '')
  if (!digits) return ''
  const msg = `Hola, quiero consultar por ${p.name}${p.price ? ` (${priceOf(p)})` : ''}`
  return `https://wa.me/${digits}?text=${encodeURIComponent(msg)}`
}
</script>

<template>
  <section v-if="products.length" class="sg-featured" aria-labelledby="sg-featured-title">
    <div class="sg-wrap">
      <div class="sg-sec-head">
        <h2 id="sg-featured-title" class="sg-sec-title">{{ title }}</h2>
        <RouterLink v-if="showCatalog" class="sg-sec-more" :to="catalogTo">
          Ver todo el catálogo <span aria-hidden="true">→</span>
        </RouterLink>
      </div>
      <div class="sg-featured-grid">
        <TplProductCard
          v-for="(p, i) in products" :key="p.id" v-reveal="(i % 4) * 70"
          class="sg-card" :p="p" :cat="catOf(p)" :brand="brandOf(p)"
          :stars="custom.show_reviews" stars-icon="star" seal-shape="" :index="null" :go="false"
          @open="openProduct"
        >
          <template #tags>
            <ul v-if="specChips(p).length" class="sg-card-specs">
              <li v-for="chip in specChips(p)" :key="chip">{{ chip }}</li>
            </ul>
          </template>
          <template #foot>
            <span class="sg-card-foot">
              <span class="sg-card-price">
                <s v-if="offerOf(p)">{{ oldPriceOf(p) }}</s>
                <strong>{{ priceOf(p) }}</strong>
              </span>
              <a v-if="waHref(p)" class="sg-card-wa" :href="waHref(p)" target="_blank" rel="noopener" @click.stop>
                Consultar por WhatsApp
              </a>
              <span v-else class="sg-card-wa" aria-hidden="true">Ver producto</span>
            </span>
          </template>
        </TplProductCard>
      </div>
    </div>
  </section>
</template>
