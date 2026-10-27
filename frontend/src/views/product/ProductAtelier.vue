<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStorePage } from '../../composables/useStorePage.js'
import AppIcon from '../../components/AppIcon.vue'
import ProductStars from '../../components/ProductStars.vue'
import ProductReviews from '../../components/ProductReviews.vue'
import SwipeGallery from '../../components/store/SwipeGallery.vue'
import StickyBuyBar from '../../components/store/StickyBuyBar.vue'
import BottomSheet from '../../components/store/BottomSheet.vue'
import StTag from '../../components/store/StTag.vue'
import OfferSeal from '../../components/store/OfferSeal.vue'
import '../../assets/store-atelier.css'

// Ficha INDUMENTARIA: galería swipe arriba (4:5), nombre display, selector
// de talle en cuadrados mono + guía en sheet, colores en swatches,
// acordeones de detalles y StickyBuyBar con la consulta a WhatsApp.
// Los selectores solo existen si el producto tiene esos atributos cargados
// (features: 'Talle', 'Color', 'Corte'...) — nunca se inventan.
const p = useStorePage()
const route = useRoute()
const router = useRouter()
const variant = computed(() => (p.pageTemplate.value === 'street' ? 'street' : 'atelier'))
const ratingIcon = computed(() => (variant.value === 'street' ? 'zap' : 'scissors'))

watch(() => p.custom.value.show_catalog, (v) => { if (v === false) router.replace(p.homeTo.value) }, { immediate: true })

const status = ref('loading')
const product = computed(() => p.products.value.find((x) => String(x.id) === String(route.params.productId)) || null)
const brand = computed(() => p.brandOf(product.value))
const catName = computed(() => p.catOf(product.value))
const rows = computed(() => p.featureRows(product.value))
const tagCorte = computed(() => p.featureValues(product.value, 'corte', 'fit', 'silueta')[0] || '')
const descRows = computed(() => rows.value.filter(([k]) => !/talle|size|medida|color/i.test(k)))

// ---- Talles ("Talle": "S, M, L") ----
const sizes = computed(() => p.featureValues(product.value, 'talle', 'size', 'medida'))
const size = ref('')
const guideOpen = ref(false)

// ---- Colores (swatches por nombre; desconocido = inicial) ----
const COLOR_HEX = {
  negro: '#1c1c1e', blanco: '#f6f6f2', gris: '#9aa0a6', plata: '#c0c4cc', plateado: '#c0c4cc',
  azul: '#2b4d8f', marino: '#1e2a4a', celeste: '#8fc3e8', denim: '#4a6a96', jean: '#4a6a96',
  rojo: '#b03030', bordó: '#6e1f2e', bordeaux: '#6e1f2e', rosa: '#e8a2b8', fucsia: '#c92a6d',
  verde: '#3d7a4a', oliva: '#6b7a3a', militar: '#5a6046', amarillo: '#e3b93c', ocre: '#c68f2a',
  naranja: '#d9732f', coral: '#e07856', violeta: '#6a4a9c', lila: '#b39ddb', morado: '#6a4a9c',
  marrón: '#6e4a2f', marron: '#6e4a2f', camel: '#b98a56', beige: '#d8c4a5', crema: '#ece0cc',
  crudo: '#e5dbc8', dorado: '#c9a227', oro: '#c9a227', turquesa: '#3aa99c', menta: '#9ad6c0',
  mostaza: '#d2a02f', chocolate: '#4a342a', habano: '#8a6242', natural: '#d9c9ac'
}
const colorOf = (name) => COLOR_HEX[String(name).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')] || COLOR_HEX[String(name).toLowerCase()] || ''
const colors = computed(() => p.featureValues(product.value, 'color').map((n) => ({ name: n, hex: colorOf(n) })))
const color = ref('')

// ---- Acordeones ----
const openAcc = ref('detalles')
const toggleAcc = (k) => { openAcc.value = openAcc.value === k ? '' : k }

// ---- WhatsApp con selección ----
const waBuy = computed(() => {
  if (!product.value) return ''
  const extras = []
  if (size.value) extras.push(`Talle: ${size.value}`)
  if (color.value) extras.push(`Color: ${color.value}`)
  return p.waProduct(product.value, extras)
})
const contactTo = computed(() => ({ ...p.homeTo.value, hash: '#contacto' }))
const ctaRef = ref(null)
const lookRail = computed(() => p.related(product.value, 6))

// ---- Share ----
const copied = ref(false)
async function share() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch { /* el link ya está en la barra */ }
}

async function load() {
  status.value = 'loading'
  try {
    await p.loadCatalog()
    status.value = product.value ? 'ready' : 'missing'
    if (product.value) document.title = `${product.value.name} · ${p.shopName.value}`
  } catch {
    status.value = 'error'
  }
}
onMounted(() => { if (p.custom.value.show_catalog !== false) load() })
</script>

<template>
<div class="sp-page-root at" :data-var="variant">
  <main class="at-pd">
    <nav class="at-crumbs" aria-label="Ruta">
      <RouterLink :to="p.homeTo.value">Inicio</RouterLink>
      <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
      <RouterLink :to="p.catalogTo.value">Catálogo</RouterLink>
      <template v-if="product"><AppIcon name="chevron-right" :size="13" aria-hidden="true" /><span aria-current="page">{{ product.name }}</span></template>
    </nav>

    <div v-if="status === 'loading'" class="at-pd-sheet" aria-busy="true">
      <div class="at-pd-gal sp-sk-block"></div>
      <div class="at-pd-info"><span class="sp-sk-line short"></span><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
    </div>

    <template v-else-if="status === 'ready' && product">
      <article class="at-pd-sheet">
        <SwipeGallery class="at-pd-gal" :images="product.image ? [product.image] : []" :alt="product.name" ratio="4 / 5" />

        <div class="at-pd-info">
          <p class="at-pd-cat">{{ [catName, brand].filter(Boolean).join(' · ') || 'Colección' }}</p>
          <h1 class="at-pd-name">{{ product.name }}</h1>
          <ProductStars v-if="p.custom.value.show_reviews && product.rating_count" class="at-pd-stars" :avg="product.rating_avg" :count="product.rating_count" :icon="ratingIcon" :size="15" show-value />
          <div class="at-pd-tags"><StTag v-if="tagCorte" kind="corte" :label="tagCorte" /><StTag v-if="p.isNewProduct(product)" kind="corte" label="Nuevo" /></div>

          <div class="at-pd-price">
            <s v-if="p.productOffer(product) != null">{{ p.formatARS(product.price) }}</s>
            <strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong>
            <OfferSeal v-if="p.productOffer(product) != null" :pct="p.offerPct(product)" :shape="variant === 'street' ? 'ticket' : 'corner'" small class="at-pd-seal" />
          </div>

          <!-- Talle -->
          <section v-if="sizes.length" class="at-pd-block" aria-labelledby="at-talle-t">
            <div class="at-pd-block-h">
              <h2 id="at-talle-t">Talle{{ size ? `: ${size}` : '' }}</h2>
              <button type="button" class="at-pd-link" @click="guideOpen = true">Guía de talles</button>
            </div>
            <div class="at-sizes" role="radiogroup" aria-label="Elegí tu talle">
              <button
                v-for="s in sizes" :key="s" type="button"
                class="at-size" :class="{ on: size === s }" role="radio" :aria-checked="size === s"
                @click="size = size === s ? '' : s"
              >{{ s }}</button>
            </div>
          </section>

          <!-- Color -->
          <section v-if="colors.length" class="at-pd-block" aria-labelledby="at-color-t">
            <h2 id="at-color-t">Color{{ color ? `: ${color}` : '' }}</h2>
            <div class="at-colors" role="radiogroup" aria-label="Elegí el color">
              <button
                v-for="c in colors" :key="c.name" type="button"
                class="at-color" :class="{ on: color === c.name, named: !c.hex }"
                role="radio" :aria-checked="color === c.name" :title="c.name"
                :style="c.hex ? { background: c.hex } : null"
                @click="color = color === c.name ? '' : c.name"
              ><span v-if="!c.hex">{{ c.name.slice(0, 1) }}</span></button>
            </div>
          </section>

          <div ref="ctaRef" class="at-pd-ctas">
            <a v-if="waBuy" class="at-cta at-pd-buy" :href="waBuy" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" /> Consultar por WhatsApp</a>
            <RouterLink v-else class="at-cta at-pd-buy" :to="contactTo"><AppIcon name="message-circle" :size="16" /> Consultar al vendedor</RouterLink>
            <button type="button" class="at-cta ghost" @click="share"><AppIcon :name="copied ? 'check' : 'share-2'" :size="15" /> {{ copied ? 'Copiado' : 'Compartir' }}</button>
          </div>

          <!-- Acordeones -->
          <div class="at-accs">
            <section v-if="descRows.length" class="at-acc" :class="{ on: openAcc === 'detalles' }">
              <button type="button" class="at-acc-h" :aria-expanded="openAcc === 'detalles'" @click="toggleAcc('detalles')">
                Composición y cuidado <AppIcon name="chevron-down" :size="15" />
              </button>
              <div v-show="openAcc === 'detalles'" class="at-acc-b">
                <dl><template v-for="[k, v] in descRows" :key="k"><dt>{{ k }}</dt><dd>{{ v }}</dd></template></dl>
              </div>
            </section>
            <section v-if="product.description" class="at-acc" :class="{ on: openAcc === 'desc' }">
              <button type="button" class="at-acc-h" :aria-expanded="openAcc === 'desc'" @click="toggleAcc('desc')">
                Sobre esta prenda <AppIcon name="chevron-down" :size="15" />
              </button>
              <div v-show="openAcc === 'desc'" class="at-acc-b"><p>{{ product.description }}</p></div>
            </section>
            <section v-if="p.location.value" class="at-acc" :class="{ on: openAcc === 'envios' }">
              <button type="button" class="at-acc-h" :aria-expanded="openAcc === 'envios'" @click="toggleAcc('envios')">
                Retiro y consultas <AppIcon name="chevron-down" :size="15" />
              </button>
              <div v-show="openAcc === 'envios'" class="at-acc-b">
                <p><AppIcon name="map-pin" :size="14" /> {{ p.location.value }}</p>
                <p class="at-acc-note">Coordinamos envíos, cambios y retiro por WhatsApp.</p>
              </div>
            </section>
          </div>
        </div>
      </article>

      <!-- Reseñas -->
      <ProductReviews
        v-if="p.custom.value.show_reviews || p.custom.value.show_comments"
        :slug="p.slug.value" :product-id="product.id"
        :can-rate="p.custom.value.show_reviews" :can-comment="p.custom.value.show_comments"
        :avg="product.rating_avg" :count="product.rating_count || 0" :icon="ratingIcon"
      />

      <!-- Completá el look -->
      <section v-if="lookRail.length" class="at-rail" aria-labelledby="at-rail-t">
        <h2 id="at-rail-t">Completá el look</h2>
        <div class="at-rail-track">
          <RouterLink v-for="r in lookRail" :key="r.id" class="at-card" :to="p.productTo(r)">
            <span class="at-card-media"><img v-if="r.image" :src="r.image" :alt="r.name" loading="lazy" /><span v-else class="at-card-ph"><AppIcon name="scissors" :size="26" /></span></span>
            <span class="at-card-info"><span class="at-card-name">{{ r.name }}</span><span class="at-card-price">{{ p.formatARS(p.effectivePrice(r)) }}</span></span>
          </RouterLink>
        </div>
      </section>

      <StickyBuyBar :target="ctaRef">
        <template #info>
          <span class="at-sbb-price"><s v-if="p.productOffer(product) != null">{{ p.formatARS(product.price) }}</s><strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong></span>
        </template>
        <a v-if="waBuy" class="at-cta" :href="waBuy" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" /> Consultar</a>
        <RouterLink v-else class="at-cta" :to="contactTo"><AppIcon name="message-circle" :size="16" /> Consultar</RouterLink>
      </StickyBuyBar>

      <BottomSheet :open="guideOpen" title="Guía de talles" @close="guideOpen = false">
        <dl v-if="rows.length" class="at-guide"><template v-for="[k, v] in rows" :key="k"><dt>{{ k }}</dt><dd>{{ v }}</dd></template></dl>
        <p v-else class="at-acc-note">Este producto no tiene medidas cargadas. Consultanos tu talle por WhatsApp y te asesoramos.</p>
        <div class="at-sizes"><button v-for="s in sizes" :key="s" type="button" class="at-size" :class="{ on: size === s }" @click="size = s; guideOpen = false">{{ s }}</button></div>
      </BottomSheet>
    </template>

    <div v-else class="at-empty">
      <span class="at-empty-mark"><AppIcon :name="status === 'error' ? 'circle-alert' : 'package'" :size="26" /></span>
      <h2>{{ status === 'error' ? 'No pudimos cargar el producto' : 'Esta prenda ya no está disponible' }}</h2>
      <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que la hayan dado de baja del catálogo.' }}</p>
      <button v-if="status === 'error'" type="button" class="at-cta" @click="load">Reintentar</button>
      <RouterLink v-else class="at-cta" :to="p.catalogTo.value">Volver al catálogo</RouterLink>
    </div>
  </main>
</div>
</template>

<script>
export default { name: 'ProductAtelier' }
</script>
