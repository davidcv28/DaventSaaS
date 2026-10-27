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
import ProductStars from '../../components/ProductStars.vue'
import OfferSeal from '../../components/store/OfferSeal.vue'
import StTag from '../../components/store/StTag.vue'
import BentoGrid from '../../components/store/BentoGrid.vue'

// Circuit/Lab (Tecnología): el catálogo como datasheet — header técnico en
// mono y los productos en el mismo bento rígido de la portada (destacado
// 2x2 con specs). Filtros/orden: bloques compartidos.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters, total,
  shownLabel, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 13 })

const isOffer = (x) => productOffer(x) != null
const isFeatured = (x) => isNewProduct(x)
const specsOf = (x) => {
  const schema = catalog.value.categories.find((c) => c.id === x?.category)?.feature_schema || []
  const order = new Map(schema.map((n, i) => [n.toLowerCase(), i]))
  return Object.entries(x?.features || {})
    .sort((a, b) => (order.get(a[0].toLowerCase()) ?? schema.length) - (order.get(b[0].toLowerCase()) ?? schema.length))
    .slice(0, 3).map(([, v]) => String(v))
}
</script>

<template>
<div class="sp-page-root cv cv-ci">
  <header class="cv-ci-head">
    <div class="cv-wrap">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <h1 class="cv-ci-title">Inventario<span class="cv-ci-count">[{{ total }}]</span></h1>
      <p class="cv-ci-sub">{{ shopName }} — stock completo, spec por spec.</p>
    </div>
  </header>

  <main class="cv-wrap cv-ci-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogToolbar />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <BentoGrid v-if="catalog.products.length" class="cv-ci-grid" :class="{ loading: catalogStatus === 'loading' }" :items="visibleProducts" :is-offer="isOffer" :is-featured="isFeatured" v-slot="{ item }">
          <article
            class="ci-cell" role="link" tabindex="0"
            :aria-label="`${item.name} — ${formatARS(effectivePrice(item))}`"
            @click="openProduct(item)" @keydown.enter="openProduct(item)"
          >
            <img v-if="item.image" :src="item.image" :alt="item.name" loading="lazy" decoding="async" />
            <span v-else class="ci-cell-ph"><AppIcon name="package" :size="28" /></span>
            <OfferSeal v-if="productOffer(item) != null" :pct="offerPct(item)" shape="corner" />
            <span class="ci-cell-info">
              <span class="ci-cell-name">{{ item.name }}</span>
              <ProductStars v-if="item.rating_count" :avg="item.rating_avg" :count="item.rating_count" icon="hexagon" :size="11" />
              <span class="ci-cell-row">
                <span class="ci-cell-specs"><StTag v-for="s in specsOf(item)" :key="s" kind="spec" :label="s" /></span>
                <span class="ci-cell-price"><s v-if="productOffer(item) != null">{{ formatARS(item.price) }}</s>{{ formatARS(effectivePrice(item)) }}</span>
              </span>
            </span>
          </article>
        </BentoGrid>

        <CatalogMore :has-more="hasMoreProducts" :label="shownLabel" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>

<style>
.cv-ci .cv-ci-head { padding: 26px 0 18px; border-bottom: 1px solid var(--sp-line); }
.cv-ci-title { margin: 6px 0 0; font-family: 'Space Grotesk', sans-serif; font-size: clamp(38px, 8vw, 80px); line-height: .96; letter-spacing: -.03em; }
.cv-ci-count { font-family: 'JetBrains Mono', monospace; font-size: .4em; color: var(--store-accent-ink); margin-left: 10px; vertical-align: super; }
.cv-ci-sub { margin: 8px 0 0; color: var(--sp-muted); font-size: 14px; }
.cv-ci-grid { margin-top: 18px; position: relative; }
.cv-ci-grid.loading { opacity: .55; pointer-events: none; }
.cv-ci-grid .ci-cell { cursor: pointer; }
</style>
