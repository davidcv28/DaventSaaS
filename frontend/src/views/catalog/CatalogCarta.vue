<script setup>
import { computed } from 'vue'
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFilters from './CatalogFilters.vue'
import CatalogToolbar from './CatalogToolbar.vue'
import OfferSeal from '../../components/store/OfferSeal.vue'
import '../../assets/store-mercado.css'

// Carta (Comestibles, premium): el catálogo como menú de restaurante —
// filas con puntos líderes y precio alineado, agrupadas por categoría.
// Filtros/orden: bloques compartidos.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters, total,
  shownLabel, shownPct, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 20 })

const groups = computed(() => {
  const cats = catalog.value.categories.filter((c) => visibleProducts.value.some((x) => x.category === c.id))
  const out = cats.map((c) => ({ id: c.id, name: c.name, items: visibleProducts.value.filter((x) => x.category === c.id) }))
  const loose = visibleProducts.value.filter((x) => !x.category || !cats.some((c) => c.id === x.category))
  if (loose.length) out.push({ id: -1, name: 'De la casa', items: loose })
  return out
})
const waNum = computed(() => String(custom.value.whatsapp || '').replace(/\D/g, ''))
const waOrder = (prod) => waNum.value
  ? `https://wa.me/${waNum.value}?text=${encodeURIComponent(`Hola ${shopName.value}, me gustaría pedir "${prod.name}" (${formatARS(effectivePrice(prod))}).`)}`
  : ''
</script>

<template>
<div class="sp-page-root cv cv-ca">
  <header class="cv-ca-head">
    <div class="cv-wrap">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Carta</span>
      </nav>
      <h1 class="cv-ca-title">{{ shopName }}</h1>
      <p class="cv-ca-sub">Carta — {{ total }} {{ total === 1 ? 'ítem' : 'ítems' }}</p>
    </div>
  </header>

  <main class="cv-wrap cv-ca-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogToolbar />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-ca-menu" :class="{ loading: catalogStatus === 'loading' }">
          <section v-for="g in groups" :key="g.id" class="mc-menu-group">
            <h2 class="mc-menu-title"><span>{{ g.name }}</span></h2>
            <ul class="mc-menu-list">
              <li v-for="prod in g.items" :key="prod.id">
                <button type="button" class="mc-menu-row" @click="openProduct(prod)">
                  <span class="mc-menu-name">{{ prod.name }}<OfferSeal v-if="productOffer(prod) != null" :pct="offerPct(prod)" shape="circle" small class="mc-menu-seal" /></span>
                  <span class="mc-menu-dots" aria-hidden="true"></span>
                  <span class="mc-menu-price"><s v-if="productOffer(prod) != null">{{ formatARS(prod.price) }}</s>{{ formatARS(effectivePrice(prod)) }}</span>
                </button>
                <p v-if="prod.description" class="mc-menu-desc">{{ prod.description.slice(0, 110) }}{{ prod.description.length > 110 ? '…' : '' }}</p>
                <a v-if="waNum" class="mc-menu-add" :href="waOrder(prod)" target="_blank" rel="noopener" :aria-label="`Pedir ${prod.name}`"><AppIcon name="plus" :size="16" /></a>
              </li>
            </ul>
          </section>
        </div>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>

<style>
.cv-ca .cv-ca-head { padding: 26px 0 18px; border-bottom: 1px dashed var(--sp-line); }
.cv-ca-title { margin: 6px 0 0; font-family: 'Playfair Display', 'Georgia', serif; font-size: clamp(38px, 8vw, 80px); line-height: .96; font-weight: 600; }
.cv-ca-sub { margin: 8px 0 0; color: var(--sp-muted); font-size: 14px; }
.cv-ca-menu { margin-top: 14px; max-width: 760px; }
.cv-ca-menu.loading { opacity: .55; pointer-events: none; }
.cv-ca-menu .mc-menu-row { width: 100%; padding: 0; border: 0; background: none; cursor: pointer; text-align: left; color: inherit; font: inherit; }
</style>
