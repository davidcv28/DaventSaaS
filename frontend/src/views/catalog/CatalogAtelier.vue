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
import StTag from '../../components/store/StTag.vue'
import TplProductCard from '../../components/store/TplProductCard.vue'
import '../../assets/store-atelier.css'

// Atelier (Indumentaria): el catálogo como pliego de colección — índice
// tipográfico, misma grilla editorial 1-2-1 de la portada y Tag-Corte en
// cada ficha. Filtros y orden salen de los bloques compartidos.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters, total,
  shownLabel, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })

const cellClass = (i) => ['big', '', '', 'big inv'][i % 4]
const corteOf = (p) => {
  const rows = Object.entries(p?.features || {})
  const hit = rows.find(([k]) => /corte|fit|silueta/i.test(k))
  return hit ? String(hit[1]).split(/[,\/·]/)[0].trim() : ''
}
</script>

<template>
<div class="sp-page-root cv cv-at">
  <header class="cv-at-head">
    <div class="cv-wrap">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Colección</span>
      </nav>
      <h1 class="cv-at-title">Colección<sup>{{ total }}</sup></h1>
      <p class="cv-at-sub">{{ shopName }} — índice completo de piezas.</p>
    </div>
  </header>

  <main class="cv-wrap cv-at-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogToolbar />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-at-grid" :class="{ loading: catalogStatus === 'loading' }">
          <TplProductCard
            v-for="(prod, i) in visibleProducts" :key="prod.id"
            class="at-card" :class="[cellClass(i), { enter: catalogStatus === 'loading' }]"
            :p="prod" :cat="categoryNameOf(prod) || brandNameOf(prod) || 'Colección'"
            :stars="!!prod.rating_count" stars-icon="scissors" seal-shape="corner"
            ph-icon="scissors" :ph-size="30" :go="false" @open="openProduct">
            <template v-if="corteOf(prod)" #foot="{ price, oldPrice, offer }">
              <span class="at-card-row">
                <StTag kind="corte" :label="corteOf(prod)" />
                <span class="tpc-price"><s v-if="offer != null">{{ oldPrice }}</s><strong :class="{ deal: offer != null }">{{ price }}</strong></span>
              </span>
            </template>
          </TplProductCard>
        </div>

        <CatalogMore :has-more="hasMoreProducts" :label="shownLabel" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>

<style>
/* Atelier: índice de colección con la misma grilla editorial de la portada. */
.cv-at .cv-at-head { padding: 26px 0 18px; border-bottom: 1px solid var(--sp-line); }
.cv-at-title { margin: 6px 0 0; font-family: 'Oswald', 'Archivo', sans-serif; font-size: clamp(44px, 9vw, 96px); line-height: .92; text-transform: uppercase; letter-spacing: -.02em; }
.cv-at-title sup { font-family: 'JetBrains Mono', monospace; font-size: 14px; letter-spacing: 0; color: var(--store-accent-ink); margin-left: 8px; }
.cv-at-sub { margin: 8px 0 0; color: var(--sp-muted); font-size: 14px; }
.cv-at-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 18px; }
.cv-at-grid .at-card { cursor: pointer; }
.cv-at-grid.loading { opacity: .55; pointer-events: none; }
.cv-at-grid .at-card.enter { animation: cv-at-in .35s ease backwards; }
@keyframes cv-at-in { from { opacity: 0; transform: translateY(10px); } }
.at-card-eyebrow { font-family: 'JetBrains Mono', monospace; font-size: 10.5px; letter-spacing: .12em; text-transform: uppercase; color: var(--sp-muted); }
@media (min-width: 768px) {
  .cv-at-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 20px; }
  .cv-at-grid .at-card.big { grid-column: span 2; }
  .cv-at-grid .at-card:nth-child(4n + 2) { translate: 0 40px; }
  .cv-at-grid { padding-bottom: 64px; }
}
@media (prefers-reduced-motion: reduce) { .cv-at-grid .at-card.enter { animation: none; } }
</style>
