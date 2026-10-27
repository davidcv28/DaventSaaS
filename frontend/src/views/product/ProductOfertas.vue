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
import '../../assets/store-ofertas.css'

// Ficha OFERTAS: el precio manda. Placa con precio tachado + ahorro en
// pesos + vencimiento real del descuento; cantidad para compras por
// volumen; el mensaje de WhatsApp sale con el total y el ahorro.
const p = useStorePage()
const route = useRoute()
const router = useRouter()
const variant = computed(() => (p.pageTemplate.value === 'shop' ? 'shop' : 'promo'))

watch(() => p.custom.value.show_catalog, (v) => { if (v === false) router.replace(p.homeTo.value) }, { immediate: true })

const status = ref('loading')
const product = computed(() => p.products.value.find((x) => String(x.id) === String(route.params.productId)) || null)
const catName = computed(() => p.catOf(product.value))
const rows = computed(() => p.featureRows(product.value))

// Datos de oferta reales.
const offer = computed(() => (product.value ? p.productOffer(product.value) : null))
const pct = computed(() => (product.value ? p.offerPct(product.value) : 0))
const savings = computed(() => (product.value && offer.value != null ? Math.max(0, Number(product.value.price) - p.effectivePrice(product.value)) : 0))
const endsLabel = computed(() => offerEndsLabel(productDiscount(product.value)))

// Cantidad (venta por volumen) + mensaje con total y ahorro.
const qty = ref(1)
const dec = () => { if (qty.value > 1) qty.value-- }
const inc = () => { if (qty.value < 99) qty.value++ }
const total = computed(() => (product.value ? p.effectivePrice(product.value) * qty.value : 0))
const savedTotal = computed(() => savings.value * qty.value)
const waOrder = computed(() => {
  if (!product.value) return ''
  const lines = [`quiero pedir ${qty.value} × "${product.value.name}" (${p.formatARS(total.value)}).`]
  if (savedTotal.value > 0) lines.push(`Con la oferta me ahorro ${p.formatARS(savedTotal.value)}.`)
  return p.waLink(lines)
})
const contactTo = computed(() => ({ ...p.homeTo.value, hash: '#contacto' }))
const ctaRef = ref(null)

// "Otras ofertas": ofertas activas primero, después lo relacionado.
const rail = computed(() => {
  if (!product.value) return []
  const onOffer = p.products.value.filter((x) => x.id !== product.value.id && p.productOffer(x) != null)
  const rest = p.related(product.value, 8).filter((x) => !onOffer.includes(x))
  return [...onOffer, ...rest].slice(0, 6)
})
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
<div class="sp-page-root of" :data-var="variant">
  <main class="of-pd">
    <nav class="of-crumbs" aria-label="Ruta">
      <RouterLink :to="p.homeTo.value">Inicio</RouterLink>
      <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
      <RouterLink :to="p.catalogTo.value">Ofertas</RouterLink>
      <template v-if="product"><AppIcon name="chevron-right" :size="13" aria-hidden="true" /><span aria-current="page">{{ product.name }}</span></template>
    </nav>

    <div v-if="status === 'loading'" class="of-pd-sheet" aria-busy="true">
      <div class="of-pd-gal sp-sk-block"></div>
      <div class="of-pd-info"><span class="sp-sk-line short"></span><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
    </div>

    <template v-else-if="status === 'ready' && product">
      <article class="of-pd-sheet">
        <div class="of-pd-media">
          <SwipeGallery :images="product.image ? [product.image] : []" :alt="product.name" ratio="4 / 3" />
          <OfferSeal v-if="offer != null" :pct="pct" :shape="variant === 'promo' ? 'ticket' : 'circle'" class="of-pd-seal" />
        </div>

        <div class="of-pd-info">
          <p class="of-pd-cat">{{ catName || 'Del local' }}</p>
          <h1 class="of-pd-name">{{ product.name }}</h1>
          <ProductStars v-if="p.custom.value.show_reviews && product.rating_count" :avg="product.rating_avg" :count="product.rating_count" icon="tag" :size="14" show-value />

          <!-- Placa de precio: tachado + efectivo + ahorro real -->
          <div class="of-pd-pricebox">
            <p class="of-pd-price">
              <s v-if="offer != null">{{ p.formatARS(product.price) }}</s>
              <strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong>
            </p>
            <span v-if="savedTotal > 0" class="of-pd-save">Ahorrás {{ p.formatARS(savedTotal) }}{{ qty > 1 ? ` con ${qty}` : '' }}</span>
            <span v-if="endsLabel" class="of-pd-ends"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ endsLabel }}</span>
          </div>

          <!-- Cantidad para compra por volumen -->
          <div class="of-qty" aria-live="polite">
            <button type="button" class="of-qty-btn" aria-label="Quitar uno" @click="dec">−</button>
            <span class="of-qty-n">{{ qty }}</span>
            <button type="button" class="of-qty-btn" aria-label="Agregar uno" @click="inc">+</button>
            <span class="of-qty-total">= {{ p.formatARS(total) }}</span>
          </div>

          <div ref="ctaRef" class="of-pd-ctas">
            <a v-if="waOrder" class="of-btn solid of-pd-buy" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Pedir · {{ p.formatARS(total) }}</a>
            <RouterLink v-else class="of-btn of-pd-buy" :to="contactTo"><AppIcon name="message-circle" :size="16" aria-hidden="true" /> Consultar</RouterLink>
            <button type="button" class="of-btn" @click="share"><AppIcon :name="copied ? 'check' : 'share-2'" :size="15" aria-hidden="true" /></button>
          </div>

          <dl v-if="rows.length" class="of-pd-rows">
            <div v-for="[k, v] in rows" :key="k" class="row"><dt>{{ k }}</dt><dd>{{ v }}</dd></div>
          </dl>
          <p v-if="product.description" class="of-pd-desc">{{ product.description }}</p>
        </div>
      </article>

      <ProductReviews
        v-if="p.custom.value.show_reviews || p.custom.value.show_comments"
        :slug="p.slug.value" :product-id="product.id"
        :can-rate="p.custom.value.show_reviews" :can-comment="p.custom.value.show_comments"
        :avg="product.rating_avg" :count="product.rating_count || 0" icon="tag"
      />

      <section v-if="rail.length" class="of-pd-rail of-sec" aria-labelledby="of-rel-t">
        <div class="of-sec-head"><h2 id="of-rel-t" class="of-sec-title">Otras <em>ofertas</em></h2></div>
        <div class="of-tickets">
          <RouterLink v-for="r in rail" :key="r.id" class="of-ticket" :to="p.productTo(r)">
            <span class="of-ticket-media">
              <img v-if="r.image" :src="r.image" :alt="r.name" loading="lazy" />
              <span v-else class="of-ticket-ph"><AppIcon name="percent" :size="22" aria-hidden="true" /></span>
              <OfferSeal v-if="p.productOffer(r) != null" :pct="p.offerPct(r)" shape="ticket" class="of-ticket-seal" />
            </span>
            <span class="of-ticket-body">
              <span class="of-ticket-name">{{ r.name }}</span>
              <span class="of-ticket-price">
                <s v-if="p.productOffer(r) != null">{{ p.formatARS(r.price) }}</s>
                <strong>{{ p.formatARS(p.effectivePrice(r)) }}</strong>
              </span>
            </span>
          </RouterLink>
        </div>
      </section>

      <StickyBuyBar :target="ctaRef">
        <template #info>
          <span class="of-sbb"><strong>{{ p.formatARS(total) }}</strong><em v-if="savedTotal > 0">ahorrás {{ p.formatARS(savedTotal) }}</em><em v-else>{{ qty }} {{ qty === 1 ? 'unidad' : 'unidades' }}</em></span>
        </template>
        <a v-if="waOrder" class="of-btn solid of-sbb-cta" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Pedir</a>
        <RouterLink v-else class="of-btn of-sbb-cta" :to="contactTo"><AppIcon name="message-circle" :size="16" aria-hidden="true" /> Pedir</RouterLink>
      </StickyBuyBar>
    </template>

    <div v-else class="of-empty">
      <span class="of-empty-mark"><AppIcon :name="status === 'error' ? 'circle-alert' : 'tag'" :size="26" aria-hidden="true" /></span>
      <h2>{{ status === 'error' ? 'No pudimos cargar el producto' : 'Esta oferta ya no está' }}</h2>
      <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que se haya terminado o dado de baja.' }}</p>
      <button v-if="status === 'error'" type="button" class="of-btn solid" style="margin-top:8px" @click="load">Reintentar</button>
      <RouterLink v-else class="of-btn" style="margin-top:8px" :to="p.catalogTo.value">Ver las ofertas</RouterLink>
    </div>
  </main>
</div>
</template>
