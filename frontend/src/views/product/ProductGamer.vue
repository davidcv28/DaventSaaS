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
import '../../assets/store-gamer.css'
import TplProductCard from '../../components/store/TplProductCard.vue'

// Ficha GAMER: la spec sheet manda. Tabla de características con valores
// en mono (featureRows ya las ordena el schema de la categoría), precio en
// placa, cantidad y rail "combiná con" (related). En 'terminal' la tabla
// se presenta como salida de `lspci`.
const p = useStorePage()
const route = useRoute()
const router = useRouter()
const variant = computed(() => (p.pageTemplate.value === 'terminal' ? 'terminal' : 'arena'))

watch(() => p.custom.value.show_catalog, (v) => { if (v === false) router.replace(p.homeTo.value) }, { immediate: true })

const status = ref('loading')
const product = computed(() => p.products.value.find((x) => String(x.id) === String(route.params.productId)) || null)
const catName = computed(() => p.catOf(product.value))
const brandName = computed(() => p.brandOf(product.value))
const rows = computed(() => p.featureRows(product.value))

const offer = computed(() => (product.value ? p.productOffer(product.value) : null))
const pct = computed(() => (product.value ? p.offerPct(product.value) : 0))
const savings = computed(() => (product.value && offer.value != null ? Math.max(0, Number(product.value.price) - p.effectivePrice(product.value)) : 0))
const endsLabel = computed(() => offerEndsLabel(productDiscount(product.value)))

const qty = ref(1)
const dec = () => { if (qty.value > 1) qty.value-- }
const inc = () => { if (qty.value < 99) qty.value++ }
const total = computed(() => (product.value ? p.effectivePrice(product.value) * qty.value : 0))
const savedTotal = computed(() => savings.value * qty.value)
const waOrder = computed(() => {
  if (!product.value) return ''
  const lines = [`quiero pedir ${qty.value} × "${product.value.name}" (${p.formatARS(total.value)}).`]
  if (rows.value.length) lines.push(`Specs: ${rows.value.slice(0, 3).map(([k, v]) => `${k} ${v}`).join(' · ')}.`)
  return p.waLink(lines)
})
const contactTo = computed(() => ({ ...p.homeTo.value, hash: '#contacto' }))
const ctaRef = ref(null)

// "Combiná con": misma categoría → misma marca (related del composable).
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
<div class="sp-page-root gm" :data-var="variant">
  <main class="gm-pd">
    <nav class="gm-crumbs" aria-label="Ruta">
      <RouterLink :to="p.homeTo.value">{{ variant === 'arena' ? 'Inicio' : '~' }}</RouterLink>
      <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
      <RouterLink :to="p.catalogTo.value">{{ variant === 'arena' ? 'Catálogo' : 'catalogo' }}</RouterLink>
      <template v-if="product"><AppIcon name="chevron-right" :size="13" aria-hidden="true" /><span aria-current="page">{{ product.name }}</span></template>
    </nav>

    <div v-if="status === 'loading'" class="gm-pd-sheet" aria-busy="true">
      <div class="sp-sk-block" style="aspect-ratio:4/3;border-radius:8px"></div>
      <div class="gm-pd-info"><span class="sp-sk-line short"></span><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
    </div>

    <template v-else-if="status === 'ready' && product">
      <article class="gm-pd-sheet">
        <div class="gm-pd-media">
          <SwipeGallery :images="product.image ? [product.image] : []" :alt="product.name" ratio="4 / 3" />
          <OfferSeal v-if="offer != null" :pct="pct" shape="corner" class="gm-pd-seal" />
        </div>

        <div class="gm-pd-info">
          <p class="gm-pd-cat">{{ [catName, brandName].filter(Boolean).join(' / ') || 'Del local' }}</p>
          <h1 class="gm-pd-name">{{ product.name }}</h1>
          <ProductStars v-if="p.custom.value.show_reviews && product.rating_count" :avg="product.rating_avg" :count="product.rating_count" icon="zap" :size="14" show-value />

          <div class="gm-pd-pricebox">
            <p class="gm-pd-price">
              <s v-if="offer != null">{{ p.formatARS(product.price) }}</s>
              <strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong>
            </p>
            <span v-if="savedTotal > 0" class="gm-pd-save">-{{ pct }}% · ahorrás {{ p.formatARS(savedTotal) }}{{ qty > 1 ? ` con ${qty}` : '' }}</span>
            <span v-if="endsLabel" class="gm-pd-ends"><AppIcon name="clock" :size="13" aria-hidden="true" /> {{ endsLabel }}</span>
          </div>

          <div class="gm-qty" aria-live="polite">
            <button type="button" class="gm-qty-btn" aria-label="Quitar uno" @click="dec">−</button>
            <span class="gm-qty-n">{{ qty }}</span>
            <button type="button" class="gm-qty-btn" aria-label="Agregar uno" @click="inc">+</button>
            <span class="gm-qty-total">= {{ p.formatARS(total) }}</span>
          </div>

          <div ref="ctaRef" class="gm-pd-ctas">
            <a v-if="waOrder" class="gm-btn solid gm-pd-buy" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Pedir · {{ p.formatARS(total) }}</a>
            <RouterLink v-else class="gm-btn gm-pd-buy" :to="contactTo"><AppIcon name="message-circle" :size="16" aria-hidden="true" /> Consultar</RouterLink>
            <button type="button" class="gm-btn ghost" @click="share"><AppIcon :name="copied ? 'check' : 'share-2'" :size="15" aria-hidden="true" /></button>
          </div>

          <!-- Spec sheet -->
          <dl v-if="rows.length" class="gm-specs">
            <div class="gm-specs-head">{{ variant === 'terminal' ? '$ lspci --specs' : 'Especificaciones' }}</div>
            <div v-for="[k, v] in rows" :key="k" class="row"><dt>{{ k }}</dt><dd>{{ v }}</dd></div>
          </dl>
          <p v-if="product.description" class="gm-pd-desc">{{ product.description }}</p>
        </div>
      </article>

      <ProductReviews
        v-if="p.custom.value.show_reviews || p.custom.value.show_comments"
        :slug="p.slug.value" :product-id="product.id"
        :can-rate="p.custom.value.show_reviews" :can-comment="p.custom.value.show_comments"
        :avg="product.rating_avg" :count="product.rating_count || 0" icon="zap"
      />

      <section v-if="rail.length" class="gm-pd-rail gm-sec" aria-labelledby="gm-rel-t">
        <div class="gm-sec-head"><h2 id="gm-rel-t" class="gm-sec-title">{{ variant === 'arena' ? 'Combiná con' : 'ls ./relacionados' }}</h2></div>
        <div class="gm-drops">
          <TplProductCard v-for="r in rail" :key="r.id" class="gm-drop" :p="r"
            seal-shape="corner" ph-icon="zap" :ph-size="22" :go="false"
            @open="p.openProduct" />
        </div>
      </section>

      <StickyBuyBar :target="ctaRef">
        <template #info>
          <span class="gm-sbb"><strong>{{ p.formatARS(total) }}</strong><em>{{ qty }} {{ qty === 1 ? 'unidad' : 'unidades' }}</em></span>
        </template>
        <a v-if="waOrder" class="gm-btn solid gm-sbb-cta" :href="waOrder" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Pedir</a>
        <RouterLink v-else class="gm-btn gm-sbb-cta" :to="contactTo"><AppIcon name="message-circle" :size="16" aria-hidden="true" /> Pedir</RouterLink>
      </StickyBuyBar>
    </template>

    <div v-else class="gm-empty">
      <span class="gm-empty-mark"><AppIcon :name="status === 'error' ? 'circle-alert' : 'zap'" :size="26" aria-hidden="true" /></span>
      <h2>{{ status === 'error' ? 'No pudimos cargar el producto' : 'Este ítem ya no está' }}</h2>
      <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que se haya dado de baja o cambiado.' }}</p>
      <button v-if="status === 'error'" type="button" class="gm-btn solid" style="margin-top:8px" @click="load">Reintentar</button>
      <RouterLink v-else class="gm-btn ghost" style="margin-top:8px" :to="p.catalogTo.value">Ver el catálogo</RouterLink>
    </div>
  </main>
</div>
</template>
