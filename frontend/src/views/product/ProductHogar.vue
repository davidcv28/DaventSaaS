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
import '../../assets/store-hogar.css'

// Ficha HOGAR (compartida por 'riso' y 'terra'; 'cobre' es extra
// absorbido y conserva ProductClassic). En deco/muebles la compra se
// decide por datos físicos: medidas, materiales, cuidados y envío —
// la spec sheet (features reales) va destacada, no escondida.
const p = useStorePage()
const route = useRoute()
const router = useRouter()
const variant = computed(() => (p.pageTemplate.value === 'terra' ? 'terra' : 'riso'))

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
<div class="sp-page-root hg" :data-var="variant">
  <main class="hg-pd">
    <nav class="hg-crumbs" aria-label="Ruta">
      <RouterLink :to="p.homeTo.value">Inicio</RouterLink>
      <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
      <RouterLink :to="p.catalogTo.value">Productos</RouterLink>
      <template v-if="product"><AppIcon name="chevron-right" :size="13" aria-hidden="true" /><span aria-current="page">{{ product.name }}</span></template>
    </nav>

    <div v-if="status === 'loading'" class="hg-pd-sheet" aria-busy="true">
      <div class="hg-pd-gal sp-sk-block"></div>
      <div class="hg-pd-info"><span class="sp-sk-line short"></span><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
    </div>

    <template v-else-if="status === 'ready' && product">
      <article class="hg-pd-sheet">
        <div class="hg-pd-media">
          <SwipeGallery :images="product.image ? [product.image] : []" :alt="product.name" ratio="1 / 1" />
          <OfferSeal v-if="offer != null" :pct="pct" :shape="variant === 'riso' ? 'ticket' : 'corner'" class="hg-pd-seal" />
        </div>

        <div class="hg-pd-info">
          <p class="hg-pd-cat">{{ catName || 'Del local' }}</p>
          <h1 class="hg-pd-name">{{ product.name }}</h1>
          <ProductStars v-if="p.custom.value.show_reviews && product.rating_count" :avg="product.rating_avg" :count="product.rating_count" icon="package" :size="14" show-value />

          <div class="hg-pd-pricebox">
            <p class="hg-pd-price">
              <s v-if="offer != null">{{ p.formatARS(product.price) }}</s>
              <strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong>
            </p>
            <span v-if="savings > 0" class="hg-pd-save">Ahorrás {{ p.formatARS(savings) }}</span>
            <span v-if="endsLabel" class="hg-pd-save"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ endsLabel }}</span>
          </div>

          <div ref="ctaRef" class="hg-pd-ctas">
            <a v-if="waOrder" class="hg-btn solid hg-pd-buy" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Consultar · {{ p.formatARS(p.effectivePrice(product)) }}</a>
            <RouterLink v-else class="hg-btn hg-pd-buy" :to="contactTo"><AppIcon name="message-circle" :size="16" aria-hidden="true" /> Consultar</RouterLink>
            <button type="button" class="hg-btn" @click="share"><AppIcon :name="copied ? 'check' : 'share-2'" :size="15" aria-hidden="true" /></button>
          </div>

          <!-- Spec sheet: medidas / materiales / cuidados / envío reales -->
          <section v-if="rows.length" class="hg-spec" aria-labelledby="hg-spec-t">
            <div class="hg-spec-head"><span id="hg-spec-t">Detalles de la pieza</span><b>{{ rows.length }}</b></div>
            <dl>
              <div v-for="[k, v] in rows" :key="k" class="row"><dt>{{ k }}</dt><dd>{{ v }}</dd></div>
            </dl>
          </section>
          <p v-if="product.description" class="hg-pd-desc">{{ product.description }}</p>
        </div>
      </article>

      <ProductReviews
        v-if="p.custom.value.show_reviews || p.custom.value.show_comments"
        :slug="p.slug.value" :product-id="product.id"
        :can-rate="p.custom.value.show_reviews" :can-comment="p.custom.value.show_comments"
        :avg="product.rating_avg" :count="product.rating_count || 0" icon="package"
      />

      <section v-if="rail.length" class="hg-pd-rail hg-sec" aria-labelledby="hg-rel-t">
        <div class="hg-sec-head"><h2 id="hg-rel-t" class="hg-sec-title">{{ variant === 'riso' ? 'Más del taller' : 'De la misma colección' }}</h2></div>
        <div class="hg-grid">
          <RouterLink v-for="r in rail" :key="r.id" class="hg-card" :to="p.productTo(r)">
            <span class="hg-card-media">
              <img v-if="r.image" :src="r.image" :alt="r.name" loading="lazy" />
              <span v-else class="hg-card-ph"><AppIcon name="package" :size="24" aria-hidden="true" /></span>
              <OfferSeal v-if="p.productOffer(r) != null" :pct="p.offerPct(r)" shape="corner" class="hg-card-seal" />
            </span>
            <span class="hg-card-body">
              <span class="hg-card-name">{{ r.name }}</span>
              <span class="hg-card-price">
                <s v-if="p.productOffer(r) != null">{{ p.formatARS(r.price) }}</s>
                <strong :class="{ deal: p.productOffer(r) != null }">{{ p.formatARS(p.effectivePrice(r)) }}</strong>
              </span>
            </span>
          </RouterLink>
        </div>
      </section>

      <StickyBuyBar :target="ctaRef">
        <template #info>
          <span class="hg-sbb"><strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong><em v-if="savings > 0">ahorrás {{ p.formatARS(savings) }}</em><em v-else>{{ product.name }}</em></span>
        </template>
        <a v-if="waOrder" class="hg-btn solid hg-sbb-cta" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Consultar</a>
        <RouterLink v-else class="hg-btn hg-sbb-cta" :to="contactTo"><AppIcon name="message-circle" :size="16" aria-hidden="true" /> Consultar</RouterLink>
      </StickyBuyBar>
    </template>

    <div v-else class="hg-empty">
      <span class="hg-empty-mark"><AppIcon :name="status === 'error' ? 'circle-alert' : 'package'" :size="26" aria-hidden="true" /></span>
      <h2>{{ status === 'error' ? 'No pudimos cargar el producto' : 'Esta pieza ya no está' }}</h2>
      <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que se haya vendido o dado de baja.' }}</p>
      <button v-if="status === 'error'" type="button" class="hg-btn solid" style="margin-top:8px" @click="load">Reintentar</button>
      <RouterLink v-else class="hg-btn" style="margin-top:8px" :to="p.catalogTo.value">Ver los productos</RouterLink>
    </div>
  </main>
</div>
</template>
