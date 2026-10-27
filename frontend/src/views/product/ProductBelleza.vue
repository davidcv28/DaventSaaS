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
import '../../assets/store-belleza.css'
import TplProductCard from '../../components/store/TplProductCard.vue'

// Ficha BELLEZA: confianza + reserva. En estética/spa el producto se
// acerca al ritual del local: precio claro, datos reales (features) y un
// CTA de consulta/reserva por WhatsApp — sin presión de volumen.
const p = useStorePage()
const route = useRoute()
const router = useRouter()
const variant = computed(() => (p.pageTemplate.value === 'signature' ? 'signature' : 'calma'))

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
const waReserve = computed(() => p.waLink(['quiero reservar un turno.']))
const contactTo = computed(() => ({ ...p.homeTo.value, hash: '#contacto' }))
const ctaRef = ref(null)

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
<div class="sp-page-root be" :data-var="variant">
  <main class="be-pd">
    <nav class="be-crumbs" aria-label="Ruta">
      <RouterLink :to="p.homeTo.value">Inicio</RouterLink>
      <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
      <RouterLink :to="p.catalogTo.value">Productos</RouterLink>
      <template v-if="product"><AppIcon name="chevron-right" :size="13" aria-hidden="true" /><span aria-current="page">{{ product.name }}</span></template>
    </nav>

    <div v-if="status === 'loading'" class="be-pd-sheet" aria-busy="true">
      <div class="be-pd-gal sp-sk-block"></div>
      <div class="be-pd-info"><span class="sp-sk-line short"></span><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
    </div>

    <template v-else-if="status === 'ready' && product">
      <article class="be-pd-sheet">
        <div class="be-pd-media">
          <SwipeGallery :images="product.image ? [product.image] : []" :alt="product.name" ratio="3 / 4" />
          <OfferSeal v-if="offer != null" :pct="pct" shape="corner" class="be-pd-seal" />
        </div>

        <div class="be-pd-info">
          <p class="be-pd-cat">{{ catName || 'Del local' }}</p>
          <h1 class="be-pd-name">{{ product.name }}</h1>
          <ProductStars v-if="p.custom.value.show_reviews && product.rating_count" :avg="product.rating_avg" :count="product.rating_count" icon="sparkles" :size="14" show-value />

          <div class="be-pd-pricebox">
            <p class="be-pd-price">
              <s v-if="offer != null">{{ p.formatARS(product.price) }}</s>
              <strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong>
            </p>
            <span v-if="savings > 0" class="be-pd-save">Ahorrás {{ p.formatARS(savings) }}</span>
            <span v-if="endsLabel" class="be-pd-ends"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ endsLabel }}</span>
          </div>

          <div ref="ctaRef" class="be-pd-ctas">
            <a v-if="waOrder" class="be-btn solid be-pd-buy" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Consultar · {{ p.formatARS(p.effectivePrice(product)) }}</a>
            <RouterLink v-else class="be-btn be-pd-buy" :to="contactTo"><AppIcon name="message-circle" :size="16" aria-hidden="true" /> Consultar</RouterLink>
            <a v-if="p.waBase.value" class="be-btn" :href="waReserve" target="_blank" rel="noopener"><AppIcon name="calendar" :size="15" aria-hidden="true" /> Reservar turno</a>
            <button type="button" class="be-btn" @click="share"><AppIcon :name="copied ? 'check' : 'share-2'" :size="15" aria-hidden="true" /></button>
          </div>

          <dl v-if="rows.length" class="be-pd-rows">
            <div v-for="[k, v] in rows" :key="k" class="row"><dt>{{ k }}</dt><dd>{{ v }}</dd></div>
          </dl>
          <p v-if="product.description" class="be-pd-desc">{{ product.description }}</p>
        </div>
      </article>

      <ProductReviews
        v-if="p.custom.value.show_reviews || p.custom.value.show_comments"
        :slug="p.slug.value" :product-id="product.id"
        :can-rate="p.custom.value.show_reviews" :can-comment="p.custom.value.show_comments"
        :avg="product.rating_avg" :count="product.rating_count || 0" icon="sparkles"
      />

      <section v-if="rail.length" class="be-pd-rail be-sec" aria-labelledby="be-rel-t">
        <div class="be-sec-head"><h2 id="be-rel-t" class="be-sec-title">{{ variant === 'calma' ? 'También te puede gustar' : 'De la misma casa' }}</h2></div>
        <div class="be-grid">
          <TplProductCard v-for="r in rail" :key="r.id" class="be-card" :p="r"
            :cat="p.catOf(r)" :seal-shape="variant === 'signature' ? 'ribbon' : 'corner'"
            ph-icon="sparkles" :ph-size="24" :go="false" @open="p.openProduct" />
        </div>
      </section>

      <StickyBuyBar :target="ctaRef">
        <template #info>
          <span class="be-sbb"><strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong><em v-if="savings > 0">ahorrás {{ p.formatARS(savings) }}</em><em v-else>{{ product.name }}</em></span>
        </template>
        <a v-if="waOrder" class="be-btn solid be-sbb-cta" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Consultar</a>
        <RouterLink v-else class="be-btn be-sbb-cta" :to="contactTo"><AppIcon name="message-circle" :size="16" aria-hidden="true" /> Consultar</RouterLink>
      </StickyBuyBar>
    </template>

    <div v-else class="be-empty">
      <span class="be-empty-mark"><AppIcon :name="status === 'error' ? 'circle-alert' : 'sparkles'" :size="26" aria-hidden="true" /></span>
      <h2>{{ status === 'error' ? 'No pudimos cargar el producto' : 'Este producto ya no está' }}</h2>
      <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que se haya terminado o dado de baja.' }}</p>
      <button v-if="status === 'error'" type="button" class="be-btn solid" style="margin-top:8px" @click="load">Reintentar</button>
      <RouterLink v-else class="be-btn" style="margin-top:8px" :to="p.catalogTo.value">Ver los productos</RouterLink>
    </div>
  </main>
</div>
</template>
