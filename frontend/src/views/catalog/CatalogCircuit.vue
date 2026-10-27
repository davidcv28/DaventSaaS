<script setup>
import { computed } from 'vue'
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
import BentoGrid from '../../components/store/BentoGrid.vue'
import '../../assets/store-circuit.css'

// Circuit/Lab (Tecnología): el catálogo como datasheet. circuit = bento
// rígido con specs (mismo lenguaje que el inserto nocturno de la portada);
// lab = "inventario medido": filas numeradas con spec inline y precio mono.
const {
  custom, shopName, pageTemplate, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters, total,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 13 })

const variant = computed(() => (pageTemplate.value === 'lab' ? 'lab' : 'circuit'))

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
<div class="sp-page-root cv cv-ci" :data-var="variant">
  <header class="cv-ci-head">
    <div class="cv-wrap">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <h1 class="cv-ci-title">Inventario<span class="cv-ci-count">{{ variant === 'lab' ? `N=${total}` : `[${total}]` }}</span></h1>
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

        <!-- lab: inventario medido — filas numeradas, spec inline -->
        <ul v-if="variant === 'lab' && catalog.products.length" class="ci-lab-rows" :class="{ loading: catalogStatus === 'loading' }">
          <li v-for="item in visibleProducts" :key="item.id">
            <TplProductCard
              class="ci-lr" layout="row" :p="item" :stars="!!item.rating_count"
              stars-icon="hexagon" :stars-size="11" seal-shape="corner" :go="false"
              :ph-size="20" @open="openProduct">
              <template v-if="specsOf(item).length" #tags>
                <span class="ci-lr-specs"><StTag v-for="s in specsOf(item)" :key="s" kind="spec" :label="s" /></span>
              </template>
            </TplProductCard>
          </li>
        </ul>

        <!-- circuit: bento rígido con specs -->
        <BentoGrid v-else-if="catalog.products.length" class="cv-ci-grid" :class="{ loading: catalogStatus === 'loading' }" :items="visibleProducts" :is-offer="isOffer" :is-featured="isFeatured" v-slot="{ item }">
          <TplProductCard
            class="ci-cell" :p="item" :stars="!!item.rating_count"
            stars-icon="hexagon" :stars-size="11" seal-shape="corner" :go="false"
            :ph-size="28" @open="openProduct">
            <template v-if="specsOf(item).length" #tags>
              <span class="ci-cell-specs"><StTag v-for="s in specsOf(item)" :key="s" kind="spec" :label="s" /></span>
            </template>
          </TplProductCard>
        </BentoGrid>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
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
.cv-ci[data-var='lab'] .cv-ci-title { font-family: 'Manrope', sans-serif; letter-spacing: -.02em; }
.cv-ci .ci-lab-rows.loading { opacity: .55; pointer-events: none; }
</style>
