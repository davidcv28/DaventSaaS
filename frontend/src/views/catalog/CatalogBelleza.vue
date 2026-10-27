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
import OfferSeal from '../../components/store/OfferSeal.vue'
import '../../assets/store-belleza.css'

// Catálogo BELLEZA (variante 'calma'; 'signature' conserva
// CatalogSignature — modelo street). La boutique del local: aire,
// tarjetas 3:4 suaves, precio tabular discreto — se compra calma,
// no se apura una comparación. Filtros/params de URL compartidos.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters,
  total, shownLabel, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })
</script>

<template>
<div class="sp-page-root cv be cv-be" data-var="calma">
  <header class="cv-be-head">
    <div class="cv-wrap">
      <nav class="be-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Productos</span>
      </nav>
      <div class="cv-be-head-row">
        <h1 class="cv-be-title">La boutique<sup v-if="total">{{ total }}</sup></h1>
        <span v-if="total" class="cv-be-count">{{ total }} {{ total === 1 ? 'producto' : 'productos' }}</span>
      </div>
      <p class="cv-be-sub">{{ shopName }} — elegí con calma, escribinos por WhatsApp.</p>
    </div>
  </header>

  <main class="cv-wrap cv-be-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogToolbar />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-be-grid" :class="{ loading: catalogStatus === 'loading' }">
          <article
            v-for="prod in visibleProducts" :key="prod.id"
            class="be-card cv-be-card" :class="{ enter: catalogStatus === 'loading' }"
            role="link" tabindex="0" :aria-label="`${prod.name} — ${formatARS(effectivePrice(prod))}`"
            @click="openProduct(prod)" @keydown.enter="openProduct(prod)"
          >
            <span class="be-card-media">
              <img v-if="prod.image" :src="prod.image" :alt="prod.name" loading="lazy" decoding="async" />
              <span v-else class="be-card-ph"><AppIcon name="sparkles" :size="26" /></span>
              <OfferSeal v-if="productOffer(prod) != null" :pct="offerPct(prod)" shape="corner" class="be-card-seal" />
              <span v-else-if="isNewProduct(prod)" class="cv-be-new">Nuevo</span>
            </span>
            <span class="be-card-body">
              <span v-if="categoryNameOf(prod)" class="cv-be-cat">{{ categoryNameOf(prod) }}</span>
              <span class="be-card-name">{{ prod.name }}</span>
              <span class="be-card-price">
                <s v-if="productOffer(prod) != null">{{ formatARS(prod.price) }}</s>
                <strong :class="{ deal: productOffer(prod) != null }">{{ formatARS(effectivePrice(prod)) }}</strong>
              </span>
            </span>
          </article>
        </div>

        <CatalogMore :has-more="hasMoreProducts" :label="shownLabel" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>

<style>
/* Belleza: cabecera serena + grilla 3:4 aireada. */
.cv-be-head { padding: 26px 0 22px; border-bottom: 1px solid var(--be-line, var(--sp-line)); text-align: center; }
.cv-be-head .be-crumbs { justify-content: center; }
.cv-be-head-row { display: grid; justify-items: center; gap: 6px; margin-top: 10px; }
.cv-be-title { margin: 0; font-family: var(--be-display); font-weight: 500; font-style: italic; font-size: clamp(34px, 6vw, 64px); line-height: 1.02; }
.cv-be-title sup { font-family: var(--be-mono); font-style: normal; font-size: 13px; font-weight: 700; color: var(--sp-accent-text); margin-left: 10px; }
.cv-be-count { font-size: 12px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: var(--sp-muted); }
.cv-be-sub { margin: 8px 0 0; color: var(--sp-muted); font-size: 14px; }
.cv-be-main { padding-bottom: 40px; }
.cv-be-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 20px; }
@media (min-width: 768px) { .cv-be-grid { grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 18px; } }
.cv-be-grid.loading { opacity: .55; pointer-events: none; }
.cv-be-card { cursor: pointer; }
.cv-be-cat { font-size: 10.5px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: var(--sp-muted); }
.cv-be-new { position: absolute; top: 10px; left: 10px; padding: 4px 10px; border-radius: 99px; background: var(--be-card); border: 1px solid var(--be-line); font-size: 10.5px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.cv-be-card.enter { animation: cv-be-in .24s var(--be-ease) backwards; }
@keyframes cv-be-in { from { opacity: 0; transform: translateY(8px); } }
@media (prefers-reduced-motion: reduce) { .cv-be-card.enter { animation: none; } }
</style>
