<script setup>
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFilters from './CatalogFilters.vue'
import CatalogToolbar from './CatalogToolbar.vue'
import TplProductCard from '../../components/store/TplProductCard.vue'
import '../../assets/store-lifestyle.css'

// Catálogo LIFESTYLE (variante 'vitrina'; 'lookbook' conserva
// CatalogLookbook — modelo street). La colección como vidriera:
// cabecera editorial, tarjetas 3:4 imagen-dominante, precio mono
// discreto. Filtros/params de URL compartidos.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters,
  total, shownLabel, shownPct, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })
</script>

<template>
<div class="sp-page-root cv lf cv-lf" data-var="vitrina">
  <header class="cv-lf-head">
    <div class="cv-wrap">
      <nav class="lf-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Colección</span>
      </nav>
      <div class="cv-lf-head-row">
        <h1 class="cv-lf-title">La colección<sup v-if="total">{{ total }}</sup></h1>
        <span v-if="total" class="cv-lf-count">{{ total }} {{ total === 1 ? 'pieza' : 'piezas' }}</span>
      </div>
      <p class="cv-lf-sub">{{ shopName }}</p>
    </div>
  </header>

  <main class="cv-wrap cv-lf-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogToolbar />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-lf-grid" :class="{ loading: catalogStatus === 'loading' }">
          <TplProductCard
            v-for="prod in visibleProducts" :key="prod.id"
            class="lf-card cv-lf-card" :class="{ enter: catalogStatus === 'loading' }"
            :p="prod" :cat="categoryNameOf(prod)"
            seal-shape="corner"
            new-label="Nueva" offer-new ph-icon="image" :go="false" @open="openProduct" />
        </div>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>

<style>
/* Lifestyle: cabecera editorial + vidriera 3:4. */
.cv-lf-head { padding: 28px 0 22px; border-bottom: 1px solid var(--lf-line, var(--sp-line)); }
.cv-lf-head-row { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-top: 12px; }
.cv-lf-title { margin: 0; font-family: var(--lf-display); font-weight: 500; font-style: italic; font-size: clamp(36px, 6.5vw, 70px); line-height: 1.0; }
.cv-lf-title sup { font-family: var(--lf-mono); font-style: normal; font-size: 13px; font-weight: 700; color: var(--sp-accent-text); margin-left: 10px; }
.cv-lf-count { font-size: 11.5px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: var(--sp-muted); }
.cv-lf-sub { margin: 8px 0 0; color: var(--sp-muted); font-size: 14px; }
.cv-lf-main { padding-bottom: 40px; }
.cv-lf-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 20px; }
@media (min-width: 768px) { .cv-lf-grid { grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 20px; } }
.cv-lf-grid.loading { opacity: .55; pointer-events: none; }
.cv-lf-card { cursor: pointer; }
.cv-lf-new { position: absolute; top: 10px; left: 10px; padding: 4px 10px; background: var(--lf-card); border: 1px solid var(--lf-line); font-size: 10.5px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
.cv-lf-card.enter { animation: cv-lf-in .24s var(--lf-ease) backwards; }
@keyframes cv-lf-in { from { opacity: 0; transform: translateY(8px); } }
@media (prefers-reduced-motion: reduce) { .cv-lf-card.enter { animation: none; } }
</style>
