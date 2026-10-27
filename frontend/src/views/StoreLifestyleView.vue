<script setup>
import { computed, onMounted } from 'vue'
import { useStorePage } from '../composables/useStorePage.js'
import AppIcon from '../components/AppIcon.vue'
import MarqueeBand from '../components/store/MarqueeBand.vue'
import TrustBar from '../components/store/TrustBar.vue'
import OfferSeal from '../components/store/OfferSeal.vue'
import { vReveal } from '../directives/reveal.js'
import '../assets/store-lifestyle.css'

// Familia LIFESTYLE — boutiques, concept stores, marcas personales.
// Se compra por deseo: el look y la colección mandan, no el precio.
// La portada es una vidriera (vitrina) / un pliego numerado (lookbook):
// piezas reales como frames y un índice de colección antes que el grid.
// Variantes: 'vitrina' (asimetría de ventana, Playfair itálica) y
// 'lookbook' (índice editorial — el layout pinta su papel --lb-*).
const p = useStorePage()
const { custom, shopName, location, pageTemplate, heroTitle, heroTitleIsName, showCatalog } = p
const variant = computed(() => (pageTemplate.value === 'lookbook' ? 'lookbook' : 'vitrina'))

// ===== La vidriera / el pliego: piezas reales destacadas =====
const featured = computed(() => p.products.value.filter((x) => x.image).slice(0, 2))
const windowItems = computed(() => featured.value.length ? featured.value : p.products.value.slice(0, 2))
const indexItems = computed(() => {
  const ranked = [...p.products.value].sort((a, b) => (p.offerPct(b) || 0) - (p.offerPct(a) || 0))
  return ranked.slice(0, 6)
})
const gridItems = computed(() => p.products.value.slice(0, 8))
const extraCount = computed(() => Math.max(0, p.products.value.length - gridItems.value.length))

const offersCount = computed(() => p.products.value.filter((x) => p.productOffer(x) != null).length)
const bandItems = computed(() => [
  { icon: 'store', text: shopName.value },
  p.products.value.length ? { icon: 'layout-grid', text: `${p.products.value.length} ${p.products.value.length === 1 ? 'pieza' : 'piezas'} en colección` } : null,
  offersCount.value ? { icon: 'percent', text: `${offersCount.value} en oferta` } : null,
  location.value ? { icon: 'map-pin', text: location.value } : null
].filter(Boolean))
const trustItems = computed(() => [
  p.products.value.length ? { icon: 'layout-grid', value: `${p.products.value.length}`, label: 'piezas' } : null,
  offersCount.value ? { icon: 'percent', value: `${offersCount.value}`, label: 'en oferta' } : null,
  location.value ? { icon: 'map-pin', label: location.value } : null,
  p.openNow.value ? { icon: 'clock', label: p.openNow.value.text } : null
].filter(Boolean))

onMounted(() => { p.loadCatalog() })
</script>

<template>
<div class="sp-page-root lf" :data-var="variant">
  <!-- ===== Hero: vidriera / portada de pliego ===== -->
  <header class="lf-hero">
    <div class="lf-hero-in">
      <div class="lf-hero-copy">
        <p class="lf-issue">{{ variant === 'vitrina' ? `Nº ${p.year} · colección` : `vol. ${p.year} · índice` }}</p>
        <h1 class="lf-title">{{ heroTitle }}</h1>
        <p v-if="custom.description" class="lf-lede">{{ custom.description }}</p>
        <div class="lf-hero-ctas">
          <RouterLink v-if="showCatalog" :to="p.catalogTo.value" class="lf-btn solid"><AppIcon name="layout-grid" :size="16" aria-hidden="true" /> {{ variant === 'vitrina' ? 'Ver la colección' : 'Abrir el índice' }}</RouterLink>
          <a v-if="p.waBase.value" class="lf-btn ghost" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="15" aria-hidden="true" /> Escribir</a>
        </div>
      </div>
      <div v-if="windowItems.length" class="lf-window" aria-label="Piezas destacadas">
        <RouterLink v-for="(prod, i) in windowItems" :key="prod.id" class="lf-frame" :to="p.productTo(prod)">
          <img v-if="prod.image" :src="prod.image" :alt="prod.name" loading="eager" decoding="async" />
          <span v-else class="lf-frame-ph"><AppIcon name="image" :size="28" aria-hidden="true" /></span>
          <span class="lf-frame-no">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="lf-frame-tag">{{ p.formatARS(p.effectivePrice(prod)) }}</span>
        </RouterLink>
      </div>
    </div>
  </header>

  <MarqueeBand v-if="bandItems.length" :items="bandItems" />
  <TrustBar :items="trustItems" />

  <main class="lf-main">
    <!-- ===== Índice de colección ===== -->
    <section v-if="indexItems.length" v-reveal class="lf-sec" aria-labelledby="lf-idx-t">
      <div class="lf-sec-head">
        <h2 id="lf-idx-t" class="lf-sec-title">{{ variant === 'vitrina' ? 'La selección' : 'Índice de la colección' }}</h2>
        <RouterLink v-if="showCatalog" class="lf-sec-link" :to="p.catalogTo.value">Ver todo <AppIcon name="arrow-right" :size="15" /></RouterLink>
      </div>
      <div class="lf-index">
        <RouterLink v-for="(prod, i) in indexItems" :key="prod.id" class="lf-index-row" :to="p.productTo(prod)">
          <span class="lf-index-no">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="lf-index-name">{{ prod.name }}</span>
          <span class="lf-index-meta"><s v-if="p.productOffer(prod) != null">{{ p.formatARS(prod.price) }}</s>{{ p.formatARS(p.effectivePrice(prod)) }}</span>
        </RouterLink>
      </div>
    </section>

    <!-- ===== Piezas ===== -->
    <section v-if="gridItems.length" v-reveal class="lf-sec" aria-labelledby="lf-grid-t">
      <div class="lf-sec-head">
        <h2 id="lf-grid-t" class="lf-sec-title">{{ variant === 'vitrina' ? 'En vidriera' : 'Las piezas' }}</h2>
        <RouterLink v-if="showCatalog && extraCount" class="lf-sec-link" :to="p.catalogTo.value">Ver {{ extraCount }} más <AppIcon name="arrow-right" :size="15" /></RouterLink>
      </div>
      <div class="lf-grid">
        <RouterLink v-for="prod in gridItems" :key="prod.id" class="lf-card" :to="p.productTo(prod)">
          <span class="lf-card-media">
            <img v-if="prod.image" :src="prod.image" :alt="prod.name" loading="lazy" decoding="async" />
            <span v-else class="lf-card-ph"><AppIcon name="image" :size="26" aria-hidden="true" /></span>
            <OfferSeal v-if="p.productOffer(prod) != null" :pct="p.offerPct(prod)" shape="corner" class="lf-card-seal" />
          </span>
          <span class="lf-card-body">
            <span v-if="p.catOf(prod)" class="lf-card-cat">{{ p.catOf(prod) }}</span>
            <span class="lf-card-name">{{ prod.name }}</span>
            <span class="lf-card-price">
              <s v-if="p.productOffer(prod) != null">{{ p.formatARS(prod.price) }}</s>
              <strong :class="{ deal: p.productOffer(prod) != null }">{{ p.formatARS(p.effectivePrice(prod)) }}</strong>
            </span>
          </span>
        </RouterLink>
      </div>
    </section>

    <!-- ===== Opiniones como cita ===== -->
    <section v-if="p.testimonials.value.length" v-reveal class="lf-sec" aria-labelledby="lf-quotes-t">
      <div class="lf-sec-head"><h2 id="lf-quotes-t" class="lf-sec-title">{{ variant === 'vitrina' ? 'Lo que dicen' : 'Referencias' }}</h2></div>
      <div class="lf-quotes">
        <figure v-for="(t, i) in p.testimonials.value.slice(0, 3)" :key="i" class="lf-quote">
          <blockquote class="lf-quote-text">{{ t.text }}</blockquote>
          <figcaption class="lf-quote-by"><strong>{{ t.name }}</strong><span v-if="t.detail">{{ t.detail }}</span></figcaption>
        </figure>
      </div>
    </section>

    <!-- ===== CTA final ===== -->
    <section v-reveal class="lf-sec" aria-labelledby="lf-cta-t">
      <div class="lf-cta">
        <h2 id="lf-cta-t">{{ variant === 'vitrina' ? 'Pasá por la vidriera.' : 'Fin del pliego.' }}</h2>
        <p>Escribinos por WhatsApp y te contamos disponibilidad, medios de pago y envíos.</p>
        <div class="lf-cta-row">
          <a v-if="p.waBase.value" class="lf-btn solid" :href="p.waGeneral.value" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" aria-hidden="true" /> Escribir a {{ shopName }}</a>
          <RouterLink v-if="showCatalog" class="lf-btn" :to="p.catalogTo.value">Ver la colección</RouterLink>
        </div>
      </div>
    </section>
  </main>
</div>
</template>
