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
import OfferSeal from '../../components/store/OfferSeal.vue'
import '../../assets/store-gamer.css'

// Catálogo GAMER (variante 'arena'; 'terminal' conserva CatalogTerminal).
// Cabecera HUD con el conteo real; cards con fila de specs en mono y
// precio tabular dominante — el cliente compara, no vitrinea.
// Filtros/orden/tags: bloques compartidos — params de URL intactos.
const {
  ctx, custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters,
  total, shownLabel, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })

const variant = computed(() => (ctx.pageTemplate.value === 'terminal' ? 'terminal' : 'arena'))
const specChips = (prod, n = 2) => Object.entries(prod.features || {}).slice(0, n).map(([k, v]) => `${k}: ${v}`)
</script>

<template>
<div class="sp-page-root cv gm cv-gm" :data-var="variant">
  <header class="cv-gm-head">
    <div class="cv-wrap">
      <nav class="gm-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">{{ variant === 'arena' ? 'Inicio' : '~' }}</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">{{ variant === 'arena' ? 'Inventario' : 'catalogo' }}</span>
      </nav>
      <div class="cv-gm-head-row">
        <h1 class="cv-gm-title"><span v-if="variant === 'terminal'" class="gm-prompt">$ </span>{{ variant === 'arena' ? 'Inventario' : 'ls ./catalogo' }}<sup v-if="total">{{ total }}</sup></h1>
        <span v-if="total" class="gm-chip"><b>{{ total }}</b> ítems indexados</span>
      </div>
      <p class="cv-gm-sub">{{ shopName }} — specs reales, precios finales.</p>
    </div>
  </header>

  <main class="cv-wrap cv-gm-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogToolbar />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-gm-grid" :class="{ loading: catalogStatus === 'loading' }">
          <article
            v-for="prod in visibleProducts" :key="prod.id"
            class="gm-card cv-gm-card" :class="{ enter: catalogStatus === 'loading' }"
            role="link" tabindex="0" :aria-label="`${prod.name} — ${formatARS(effectivePrice(prod))}`"
            @click="openProduct(prod)" @keydown.enter="openProduct(prod)"
          >
            <span class="gm-card-media">
              <img v-if="prod.image" :src="prod.image" :alt="prod.name" loading="lazy" decoding="async" />
              <span v-else class="gm-card-ph"><AppIcon name="zap" :size="26" /></span>
              <OfferSeal v-if="productOffer(prod) != null" :pct="offerPct(prod)" shape="corner" class="gm-card-seal" />
              <span v-else-if="isNewProduct(prod)" class="gm-card-new">New</span>
            </span>
            <span class="gm-card-body">
              <span v-if="categoryNameOf(prod)" class="gm-card-cat">{{ categoryNameOf(prod) }}</span>
              <span class="gm-card-name">{{ prod.name }}</span>
              <span v-if="specChips(prod).length" class="gm-card-specs">
                <span v-for="schip in specChips(prod)" :key="schip" class="gm-card-spec">{{ schip }}</span>
              </span>
              <span class="gm-card-price">
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
/* Gamer: cabecera HUD + grilla spec-first. */
.cv-gm-head { padding: 26px 0 22px; border-bottom: var(--gm-bw, 1.5px) solid var(--gm-line, var(--sp-line)); }
.cv-gm[data-var='arena'] .cv-gm-head { border-bottom: 0; box-shadow: inset 0 -3px 0 var(--store-accent); }
.cv-gm-head-row { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-top: 10px; }
.cv-gm-title { margin: 0; font-family: var(--gm-display); font-weight: 800; font-size: clamp(34px, 7vw, 76px); line-height: .98; text-transform: uppercase; letter-spacing: .01em; }
.cv-gm[data-var='terminal'] .cv-gm-title { font-weight: 700; text-transform: none; letter-spacing: -.01em; font-size: clamp(28px, 5vw, 56px); }
.cv-gm-title sup { font-family: var(--gm-mono); font-size: 14px; font-weight: 700; color: var(--sp-accent-text); margin-left: 10px; }
.cv-gm-sub { margin: 8px 0 0; color: var(--sp-muted); font-size: 14px; }
.cv-gm[data-var='terminal'] .cv-gm-sub::before { content: '# '; color: var(--sp-accent-text); }
.cv-gm-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 20px; }
@media (min-width: 768px) { .cv-gm-grid { grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 18px; } }
.cv-gm-grid.loading { opacity: .55; pointer-events: none; }
.cv-gm-card { cursor: pointer; }
.cv-gm-card.enter { animation: cv-gm-in .22s var(--gm-ease) backwards; }
@keyframes cv-gm-in { from { opacity: 0; transform: translateY(8px); } }
@media (prefers-reduced-motion: reduce) { .cv-gm-card.enter { animation: none; } }
</style>
