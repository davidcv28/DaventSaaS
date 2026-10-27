<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStorePage } from '../../composables/useStorePage.js'
import { productDiscount, offerEndsLabel } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import ProductStars from '../../components/ProductStars.vue'
import ProductReviews from '../../components/ProductReviews.vue'
import SwipeGallery from '../../components/store/SwipeGallery.vue'
import StickyBuyBar from '../../components/store/StickyBuyBar.vue'
import OfferSeal from '../../components/store/OfferSeal.vue'
import '../../assets/store-lifestyle.css'

// Ficha LIFESTYLE: la pieza en contexto. El cliente de boutique mira
// la imagen, la colección a la que pertenece y qué combina — precio
// claro, specs reales (talle/color/material) y "completá el look"
// con relacionadas. Consulta por WhatsApp, sin presión.
const p = useStorePage()
const route = useRoute()
const router = useRouter()
const variant = computed(() => (p.pageTemplate.value === 'lookbook' ? 'lookbook' : 'vitrina'))

watch(() => p.custom.value.show_catalog, (v) => { if (v === false) router.replace(p.homeTo.value) }, { immediate: true })

const status = ref('loading')
const product = computed(() => p.products.value.find((x) => String(x.id) === String(route.params.productId)) || null)
const catName = computed(() => p.catOf(product.value))
const rows = computed(() => p.featureRows(product.value))

const offer = computed(() => (product.value ? p.productOffer(product.value) : null))
const pct = computed(() => (product.value ? p.offerPct(product.value) : 0))
const savings = computed(() => (product.value && offer.value != null ? Math.max(0, Number(product.value.price) - p.effectivePrice(product.value)) : 0))
const endsLabel = computed(() => offerEndsLabel(productDiscount(product.value)))

const waOrder = computed(() => {
  if (!product.value) return ''
  return p.waLink([`quiero consultar por "${product.value.name}" (${p.formatARS(p.effectivePrice(product.value))}).`])
})
const contactTo = computed(() => ({ ...p.homeTo.value, hash: '#contacto' }))
const ctaRef = ref(null)

// "Completá el look": relacionadas reales (misma categoría primero).
const rail = computed(() => (product.value ? p.related(product.value, 6) : []))
const copied = ref(false)
async function share() {
  try { await navigator.clipboard.writeText(window.location.href); copied.value = true; setTimeout(() => { copied.value = false }, 2500) } catch { /* noop */ }
}

async function load() {
  status.value = 'loading'
  try {
    await p.loadCatalog()
    status.value = product.value ? 'ready' : 'missing'
    if (product.value) document.title = `${product.value.name} · ${p.shopName.value}`
  } catch { status.value = 'error' }
}
onMounted(() => { if (p.custom.value.show_catalog !== false) load() })
</script>

<template>
<div class="sp-page-root lf" :data-var="variant">
  <main class="lf-pd">
    <nav class="lf-crumbs" aria-label="Ruta">
      <RouterLink :to="p.homeTo.value">Inicio</RouterLink>
      <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
      <RouterLink :to="p.catalogTo.value">{{ variant === 'vitrina' ? 'Colección' : 'Índice' }}</RouterLink>
      <template v-if="product"><AppIcon name="chevron-right" :size="13" aria-hidden="true" /><span aria-current="page">{{ product.name }}</span></template>
    </nav>

    <div v-if="status === 'loading'" class="lf-pd-sheet" aria-busy="true">
      <div class="lf-pd-gal sp-sk-block"></div>
      <div class="lf-pd-info"><span class="sp-sk-line short"></span><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
    </div>

    <template v-else-if="status === 'ready' && product">
      <article class="lf-pd-sheet">
        <div class="lf-pd-media">
          <SwipeGallery :images="product.image ? [product.image] : []" :alt="product.name" ratio="3 / 4" />
          <OfferSeal v-if="offer != null" :pct="pct" shape="corner" class="lf-pd-seal" />
        </div>

        <div class="lf-pd-info">
          <p class="lf-pd-cat">{{ catName || 'De la colección' }}</p>
          <h1 class="lf-pd-name">{{ product.name }}</h1>
          <ProductStars v-if="p.custom.value.show_reviews && product.rating_count" :avg="product.rating_avg" :count="product.rating_count" icon="star" :size="14" show-value />

          <div class="lf-pd-pricebox">
            <p class="lf-pd-price">
              <s v-if="offer != null">{{ p.formatARS(product.price) }}</s>
              <strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong>
            </p>
            <span v-if="savings > 0" class="lf-pd-save">Ahorrás {{ p.formatARS(savings) }}</span>
            <span v-if="endsLabel" class="lf-pd-save"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ endsLabel }}</span>
          </div>

          <div ref="ctaRef" class="lf-pd-ctas">
            <a v-if="waOrder" class="lf-btn solid lf-pd-buy" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Consultar · {{ p.formatARS(p.effectivePrice(product)) }}</a>
            <RouterLink v-else class="lf-btn lf-pd-buy" :to="contactTo"><AppIcon name="message-circle" :size="16" aria-hidden="true" /> Consultar</RouterLink>
            <button type="button" class="lf-btn" @click="share"><AppIcon :name="copied ? 'check' : 'share-2'" :size="15" aria-hidden="true" /></button>
          </div>

          <dl v-if="rows.length" class="lf-pd-rows">
            <div v-for="[k, v] in rows" :key="k" class="row"><dt>{{ k }}</dt><dd>{{ v }}</dd></div>
          </dl>
          <p v-if="product.description" class="lf-pd-desc">{{ product.description }}</p>
        </div>
      </article>

      <ProductReviews
        v-if="p.custom.value.show_reviews || p.custom.value.show_comments"
        :slug="p.slug.value" :product-id="product.id"
        :can-rate="p.custom.value.show_reviews" :can-comment="p.custom.value.show_comments"
        :avg="product.rating_avg" :count="product.rating_count || 0" icon="star"
      />

      <!-- Completá el look -->
      <section v-if="rail.length" class="lf-pd-rail lf-sec" aria-labelledby="lf-rel-t">
        <div class="lf-sec-head"><h2 id="lf-rel-t" class="lf-sec-title">{{ variant === 'vitrina' ? 'Completá el look' : 'Piezas relacionadas' }}</h2></div>
        <div class="lf-grid">
          <RouterLink v-for="r in rail" :key="r.id" class="lf-card" :to="p.productTo(r)">
            <span class="lf-card-media">
              <img v-if="r.image" :src="r.image" :alt="r.name" loading="lazy" />
              <span v-else class="lf-card-ph"><AppIcon name="image" :size="24" aria-hidden="true" /></span>
              <OfferSeal v-if="p.productOffer(r) != null" :pct="p.offerPct(r)" shape="corner" class="lf-card-seal" />
            </span>
            <span class="lf-card-body">
              <span class="lf-card-name">{{ r.name }}</span>
              <span class="lf-card-price">
                <s v-if="p.productOffer(r) != null">{{ p.formatARS(r.price) }}</s>
                <strong :class="{ deal: p.productOffer(r) != null }">{{ p.formatARS(p.effectivePrice(r)) }}</strong>
              </span>
            </span>
          </RouterLink>
        </div>
      </section>

      <StickyBuyBar :target="ctaRef">
        <template #info>
          <span class="lf-sbb"><strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong><em v-if="savings > 0">ahorrás {{ p.formatARS(savings) }}</em><em v-else>{{ product.name }}</em></span>
        </template>
        <a v-if="waOrder" class="lf-btn solid lf-sbb-cta" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Consultar</a>
        <RouterLink v-else class="lf-btn lf-sbb-cta" :to="contactTo"><AppIcon name="message-circle" :size="16" aria-hidden="true" /> Consultar</RouterLink>
      </StickyBuyBar>
    </template>

    <div v-else class="lf-empty">
      <span class="lf-empty-mark"><AppIcon :name="status === 'error' ? 'circle-alert' : 'tag'" :size="26" aria-hidden="true" /></span>
      <h2>{{ status === 'error' ? 'No pudimos cargar la pieza' : 'Esta pieza ya no está' }}</h2>
      <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que se haya vendido o retirado de la colección.' }}</p>
      <button v-if="status === 'error'" type="button" class="lf-btn solid" style="margin-top:8px" @click="load">Reintentar</button>
      <RouterLink v-else class="lf-btn" style="margin-top:8px" :to="p.catalogTo.value">Ver la colección</RouterLink>
    </div>
  </main>
</div>
</template>
