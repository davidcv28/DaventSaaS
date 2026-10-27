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
import TplProductCard from '../../components/store/TplProductCard.vue'

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
          <TplProductCard
            v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 50"
            tag="figure" class="rs-card" :class="`t-${toneOf(p)}`" :p="p"
            :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
            seal-shape="" offer-new :index="String(i + 1).padStart(3, '0')"
            go-label="Ver producto" :ph-size="44" @open="openProduct" />
        </div>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
