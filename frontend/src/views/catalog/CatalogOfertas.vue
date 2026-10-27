<script setup>
import { computed } from 'vue'
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct, productDiscount, offerEndsLabel } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFilters from './CatalogFilters.vue'
import CatalogToolbar from './CatalogToolbar.vue'
import OfferSeal from '../../components/store/OfferSeal.vue'
import '../../assets/store-ofertas.css'

// Catálogo OFERTAS: el precio manda. Cabecera con el mejor descuento real
// y vencimiento; grilla densa de cards con precio tabular dominante.
// Filtros/orden/tags salen de los bloques compartidos (CatalogFilters +
// CatalogToolbar) — params de URL intactos.
const {
  ctx, custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters,
  total, shownLabel, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })

const variant = computed(() => (ctx.pageTemplate.value === 'shop' ? 'shop' : 'promo'))
const maxPct = computed(() => catalog.value.products.reduce((m, x) => Math.max(m, offerPct(x)), 0))
const savings = (prod) => Math.max(0, Number(prod.price) - effectivePrice(prod))
const endsOf = (prod) => offerEndsLabel(productDiscount(prod))
</script>

<template>
<div class="sp-page-root cv of cv-of" :data-var="variant">
  <header class="cv-of-head">
    <div class="cv-wrap">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Ofertas</span>
      </nav>
      <div class="cv-of-head-row">
        <h1 class="cv-of-title">El precio manda<sup v-if="total">{{ total }}</sup></h1>
        <p v-if="maxPct" class="cv-of-top"><AppIcon name="percent" :size="15" aria-hidden="true" /> Hasta {{ maxPct }}% off</p>
      </div>
      <p class="cv-of-sub">{{ shopName }} — precios finales, sin letra chica.</p>
    </div>
  </header>

  <main class="cv-wrap cv-of-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogToolbar />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-of-grid" :class="{ loading: catalogStatus === 'loading' }">
          <article
            v-for="prod in visibleProducts" :key="prod.id"
            class="of-card cv-of-card" :class="{ enter: catalogStatus === 'loading' }"
            role="link" tabindex="0" :aria-label="`${prod.name} — ${formatARS(effectivePrice(prod))}`"
            @click="openProduct(prod)" @keydown.enter="openProduct(prod)"
          >
            <span class="of-card-media">
              <img v-if="prod.image" :src="prod.image" :alt="prod.name" loading="lazy" decoding="async" />
              <span v-else class="of-card-ph"><AppIcon name="percent" :size="26" /></span>
              <OfferSeal v-if="productOffer(prod) != null" :pct="offerPct(prod)" :shape="variant === 'promo' ? 'ticket' : 'corner'" class="of-card-seal" />
              <span v-else-if="isNewProduct(prod)" class="of-card-new">Nuevo</span>
            </span>
            <span class="of-card-body">
              <span v-if="categoryNameOf(prod)" class="of-card-cat">{{ categoryNameOf(prod) }}</span>
              <span class="of-card-name">{{ prod.name }}</span>
              <span class="of-card-price">
                <s v-if="productOffer(prod) != null">{{ formatARS(prod.price) }}</s>
                <strong :class="{ deal: productOffer(prod) != null }">{{ formatARS(effectivePrice(prod)) }}</strong>
              </span>
              <span v-if="productOffer(prod) != null" class="of-card-save">
                Ahorrás {{ formatARS(savings(prod)) }}<em v-if="endsOf(prod)"> · {{ endsOf(prod) }}</em>
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
/* Ofertas: cabecera de góndola + grilla precio-dominante. */
.cv-of-head { padding: 26px 0 22px; border-bottom: var(--of-bw, 2px) solid var(--of-ink, var(--sp-ink)); }
.cv-of[data-var='shop'] .cv-of-head { border-bottom-color: var(--of-line, var(--sp-line)); }
.cv-of-head-row { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-top: 8px; }
.cv-of-title { margin: 0; font-family: var(--of-display); font-weight: 400; font-size: clamp(38px, 8vw, 84px); line-height: .94; text-transform: uppercase; letter-spacing: -.01em; }
.cv-of[data-var='shop'] .cv-of-title { font-weight: 800; text-transform: none; letter-spacing: -.03em; font-size: clamp(32px, 5.5vw, 60px); }
.cv-of-title sup { font-family: var(--of-mono); font-size: 14px; font-weight: 700; letter-spacing: 0; color: var(--sp-accent-text); margin-left: 10px; }
.cv-of-top { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 99px; background: var(--store-accent); color: #fff; font-family: var(--of-mono); font-size: 13px; font-weight: 800; }
.cv-of-sub { margin: 8px 0 0; color: var(--sp-muted); font-size: 14px; }
.cv-of-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 20px; }
.cv-of-grid.loading { opacity: .55; pointer-events: none; }
.cv-of-card { cursor: pointer; }
.cv-of-card.enter { animation: cv-of-in .3s var(--of-ease) backwards; }
@keyframes cv-of-in { from { opacity: 0; transform: translateY(8px); } }
.of-card-save { font-family: var(--of-mono); font-size: 11px; font-weight: 700; color: var(--sp-accent-text); }
.of-card-save em { font-style: normal; color: var(--sp-muted); font-weight: 600; }
@media (min-width: 768px) { .cv-of-grid { grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 18px; } }
.cv-of[data-var='promo'] .cv-of-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
@media (min-width: 768px) { .cv-of[data-var='promo'] .cv-of-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 24px 20px; } }
@media (prefers-reduced-motion: reduce) { .cv-of-card.enter { animation: none; } }
</style>
