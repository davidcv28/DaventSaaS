<script setup>
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFilters from './CatalogFilters.vue'
import CatalogToolbar from './CatalogToolbar.vue'
import '../../assets/store-riso.css'

// Riso: el catálogo en risografía — titular a dos tintas, aside unificado
// como tarjeta con sombra desplazada y grilla de tarjetas con placa de
// color y trama de puntos. Mismo estado que el resto de diseños.
const {
  custom, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })

const TONES = ['pink', 'blue', 'yellow', 'mint']
const toneOf = (p) => TONES[Math.max(0, catalog.value.categories.findIndex((c) => c.id === p.category)) % TONES.length]
</script>

<template>
<div class="sp-page-root cv cv-rs">
  <main class="cv-wrap cv-rs-main">
    <nav class="cv-crumbs cv-rs-crumbs" aria-label="Ruta">
      <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
      <span v-if="custom.site_mode !== 'catalog'" aria-hidden="true">/</span>
      <span aria-current="page">Catálogo</span>
    </nav>

    <header class="cv-rs-intro">
      <div>
        <span class="rs-kicker tilt">Catálogo · {{ catalog.categories.length }} categorías</span>
        <h1 class="cv-rs-title"><span class="a">Todo</span><br><span class="b">a la vez.</span></h1>
      </div>
    </header>

    <CatalogPromoBanner :promotions="catalog.promotions" />

    <div class="cf-body">
      <CatalogFilters />

      <div class="cv-rs-results cf-main">
        <CatalogToolbar />

        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-rs-cards" :class="{ loading: catalogStatus === 'loading' }">
          <article
            v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 50"
            class="rs-card" :class="`t-${toneOf(p)}`" role="link" tabindex="0" :aria-label="`Ver ${p.name}`"
            @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)"
          >
            <figure class="rs-plate">
              <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
              <span v-else class="rs-plate-ph"><AppIcon name="package" :size="44" /></span>
              <span class="rs-idx">{{ String(i + 1).padStart(3, '0') }}</span>
              <span v-if="productOffer(p) != null" class="rs-badge">−{{ offerPct(p) }}%</span>
              <span v-else-if="isNewProduct(p)" class="rs-badge">Nuevo</span>
            </figure>
            <div class="rs-info">
              <div class="rs-info-row">
                <h3>{{ p.name }}</h3>
                <span class="rs-price">
                  <s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>
                  {{ formatARS(effectivePrice(p)) }}
                </span>
              </div>
              <p>{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' · ') || '\u00a0' }}</p>
            </div>
            <span class="rs-add" aria-hidden="true">Ver producto</span>
          </article>
        </div>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
