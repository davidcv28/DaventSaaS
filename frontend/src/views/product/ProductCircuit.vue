<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useStorePage } from '../../composables/useStorePage.js'
import AppIcon from '../../components/AppIcon.vue'
import ProductStars from '../../components/ProductStars.vue'
import ProductReviews from '../../components/ProductReviews.vue'
import SwipeGallery from '../../components/store/SwipeGallery.vue'
import StickyBuyBar from '../../components/store/StickyBuyBar.vue'
import SpecStrip from '../../components/store/SpecStrip.vue'
import OfferSeal from '../../components/store/OfferSeal.vue'
import '../../assets/store-circuit.css'

// Ficha TECNOLOGÍA: visor con zoom, SpecStrip de atributos clave bajo el
// título, precio en mono, pestañas sticky (Resumen / Specs / En la caja /
// Reseñas) y tabla de especificaciones de dos columnas con valores mono.
const p = useStorePage()
const route = useRoute()
const router = useRouter()
const variant = computed(() => (p.pageTemplate.value === 'lab' ? 'lab' : 'circuit'))

watch(() => p.custom.value.show_catalog, (v) => { if (v === false) router.replace(p.homeTo.value) }, { immediate: true })

const status = ref('loading')
const product = computed(() => p.products.value.find((x) => String(x.id) === String(route.params.productId)) || null)
const brand = computed(() => p.brandOf(product.value))
const catName = computed(() => p.catOf(product.value))
const rows = computed(() => p.featureRows(product.value))

const SPEC_ICON_OF = (k) => {
  const t = k.toLowerCase()
  if (/bateria|carga|autonom|mah/.test(t)) return 'zap'
  if (/pantalla|display|resol|hz|oled|lcd/.test(t)) return 'monitor'
  if (/camara|video|foto/.test(t)) return 'camera'
  if (/garantia|seguro/.test(t)) return 'shield-check'
  if (/color|acabado/.test(t)) return 'palette'
  if (/peso|dimens|tama/.test(t)) return 'package'
  return 'gem'
}
const keySpecs = computed(() => rows.value.slice(0, 4).map(([k, v]) => ({ icon: SPEC_ICON_OF(k), value: String(v), label: k })))
const inBox = computed(() => p.featureValues(product.value, 'en la caja', 'incluye', 'contenido'))
const restRows = computed(() => rows.value.slice(4))
const hasReviews = computed(() => p.custom.value.show_reviews || p.custom.value.show_comments)

// Pestañas sticky: solo las secciones que tienen datos.
const tabs = computed(() => [
  { id: 'resumen', label: 'Resumen', show: true },
  { id: 'specs', label: 'Especificaciones', show: !!rows.value.length },
  { id: 'caja', label: 'En la caja', show: !!inBox.value.length },
  { id: 'resenas', label: 'Reseñas', show: !!hasReviews.value }
].filter((t) => t.show))
const activeTab = ref('resumen')
const goTab = (t) => {
  activeTab.value = t.id
  document.getElementById(`ci-pd-${t.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const waBuy = computed(() => (product.value ? p.waProduct(product.value) : ''))
const contactTo = computed(() => ({ ...p.homeTo.value, hash: '#contacto' }))
const ctaRef = ref(null)
const rail = computed(() => p.related(product.value, 6))
const copied = ref(false)
async function share() {
  try {
    await navigator.clipboard.writeText(window.location.href)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2500)
  } catch { /* noop */ }
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
<div class="sp-page-root ci" :data-var="variant">
  <main class="ci-pd">
    <nav class="ci-crumbs" aria-label="Ruta">
      <RouterLink :to="p.homeTo.value">Inicio</RouterLink>
      <AppIcon name="chevron-right" :size="13" aria-hidden="true" />
      <RouterLink :to="p.catalogTo.value">Catálogo</RouterLink>
      <template v-if="product"><AppIcon name="chevron-right" :size="13" aria-hidden="true" /><span aria-current="page">{{ product.name }}</span></template>
    </nav>

    <div v-if="status === 'loading'" class="ci-pd-sheet" aria-busy="true">
      <div class="ci-pd-gal sp-sk-block"></div>
      <div class="ci-pd-info"><span class="sp-sk-line short"></span><span class="sp-sk-line"></span><span class="sp-sk-line short"></span></div>
    </div>

    <template v-else-if="status === 'ready' && product">
      <!-- Pestañas sticky -->
      <nav class="ci-tabs" aria-label="Secciones del producto">
        <button v-for="t in tabs" :key="t.id" type="button" class="ci-tab" :class="{ on: activeTab === t.id }" @click="goTab(t)">{{ t.label }}</button>
      </nav>

      <article id="ci-pd-resumen" class="ci-pd-sheet">
        <div class="ci-pd-media">
          <SwipeGallery class="ci-pd-gal" :images="product.image ? [product.image] : []" :alt="product.name" ratio="1 / 1" />
          <OfferSeal v-if="p.productOffer(product) != null" :pct="p.offerPct(product)" shape="corner" />
        </div>

        <div class="ci-pd-info">
          <p class="ci-pd-cat">{{ [brand, catName].filter(Boolean).join(' · ') || 'Equipo' }}</p>
          <h1 class="ci-pd-name">{{ product.name }}</h1>
          <ProductStars v-if="p.custom.value.show_reviews && product.rating_count" :avg="product.rating_avg" :count="product.rating_count" icon="hexagon" :size="14" show-value />

          <SpecStrip v-if="keySpecs.length" class="ci-pd-strip" :items="keySpecs" />

          <div class="ci-pd-price">
            <s v-if="p.productOffer(product) != null">{{ p.formatARS(product.price) }}</s>
            <strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong>
          </div>

          <div ref="ctaRef" class="ci-pd-ctas">
            <a v-if="waBuy" class="ci-cta ci-pd-buy" :href="waBuy" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" /> Consultar por WhatsApp</a>
            <RouterLink v-else class="ci-cta ci-pd-buy" :to="contactTo"><AppIcon name="message-circle" :size="16" /> Consultar</RouterLink>
            <button type="button" class="ci-cta ghost" @click="share"><AppIcon :name="copied ? 'check' : 'share-2'" :size="15" /> {{ copied ? 'Copiado' : 'Compartir' }}</button>
          </div>
          <p v-if="p.openNow.value" class="ci-pd-stock" :data-state="p.openNow.value.state"><AppIcon name="dot" :size="10" /> {{ p.openNow.value.text }}</p>
        </div>
      </article>

      <!-- Especificaciones -->
      <section v-if="restRows.length || keySpecs.length" id="ci-pd-specs" class="ci-pd-sec" aria-labelledby="ci-pd-specs-t">
        <h2 id="ci-pd-specs-t">Especificaciones</h2>
        <table class="ci-spec-table">
          <tbody>
            <tr v-for="[k, v] in rows" :key="k"><th>{{ k }}</th><td>{{ v }}</td></tr>
          </tbody>
        </table>
      </section>

      <!-- En la caja -->
      <section v-if="inBox.length" id="ci-pd-caja" class="ci-pd-sec" aria-labelledby="ci-pd-caja-t">
        <h2 id="ci-pd-caja-t">En la caja</h2>
        <ul class="ci-box">
          <li v-for="it in inBox" :key="it"><AppIcon name="check" :size="16" /> {{ it }}</li>
        </ul>
      </section>

      <p v-if="product.description" class="ci-pd-desc">{{ product.description }}</p>

      <!-- Reseñas -->
      <div id="ci-pd-resenas">
        <ProductReviews
          v-if="hasReviews"
          :slug="p.slug.value" :product-id="product.id"
          :can-rate="p.custom.value.show_reviews" :can-comment="p.custom.value.show_comments"
          :avg="product.rating_avg" :count="product.rating_count || 0" icon="hexagon"
        />
      </div>

      <!-- Relacionados -->
      <section v-if="rail.length" class="ci-pd-rail" aria-labelledby="ci-pd-rel-t">
        <h2 id="ci-pd-rel-t">También te puede servir</h2>
        <div class="ci-rail-track">
          <RouterLink v-for="r in rail" :key="r.id" class="ci-rail-card" :to="p.productTo(r)">
            <span class="ci-rail-media"><img v-if="r.image" :src="r.image" :alt="r.name" loading="lazy" /><span v-else class="ci-card-ph"><AppIcon name="package" :size="24" /></span></span>
            <span class="ci-rail-info"><strong>{{ r.name }}</strong><em>{{ p.formatARS(p.effectivePrice(r)) }}</em></span>
          </RouterLink>
        </div>
      </section>

      <StickyBuyBar :target="ctaRef">
        <template #info>
          <span class="ci-sbb"><span class="ci-sbb-avail" :data-state="p.openNow.value?.state || 'open'"><AppIcon name="dot" :size="10" /> {{ p.openNow.value?.state === 'closed' ? 'Cerrado' : 'Disponible' }}</span><strong>{{ p.formatARS(p.effectivePrice(product)) }}</strong></span>
        </template>
        <a v-if="waBuy" class="ci-cta" :href="waBuy" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" /> Consultar</a>
        <RouterLink v-else class="ci-cta" :to="contactTo"><AppIcon name="message-circle" :size="16" /> Consultar</RouterLink>
      </StickyBuyBar>
    </template>

    <div v-else class="ci-empty">
      <span class="ci-empty-mark"><AppIcon :name="status === 'error' ? 'circle-alert' : 'package'" :size="26" /></span>
      <h2>{{ status === 'error' ? 'No pudimos cargar el producto' : 'Este equipo ya no está disponible' }}</h2>
      <p>{{ status === 'error' ? 'Revisá tu conexión e intentá de nuevo.' : 'Puede que lo hayan dado de baja del catálogo.' }}</p>
      <button v-if="status === 'error'" type="button" class="ci-cta" @click="load">Reintentar</button>
      <RouterLink v-else class="ci-cta" :to="p.catalogTo.value">Volver al catálogo</RouterLink>
    </div>
  </main>
</div>
</template>
