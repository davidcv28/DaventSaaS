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
import StTag from '../../components/store/StTag.vue'
import '../../assets/store-mercado.css'
import TplProductCard from '../../components/store/TplProductCard.vue'

// Mercado (Comestibles): el catálogo como mostrador — header con serif
// cálida y las cards de 24px con pill de precio y "+" de pedido directo,
// idénticas a la portada. Filtros/orden: bloques compartidos.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters, total,
  shownLabel, openProduct
} = useStoreCatalog({ pageSize: 12 })

const dietaTone = (v) => (/vegano|vegetariano/.test(v) ? 'veg' : /tacc|gluten/.test(v) ? 'tacc' : /az[uú]car|keto|light/.test(v) ? 'sin-azucar' : '')
const dietaIcon = (v) => (/vegano|vegetariano/.test(v) ? 'leaf' : 'check')
const dietTagsOf = (p) => Object.entries(p?.features || {})
  .filter(([k]) => /dieta|porci|peso|vegano|tacc|gluten/i.test(k))
  .flatMap(([, v]) => String(v).split(/[,\/·]/).map((s) => s.trim().toLowerCase()).filter(Boolean))
  .slice(0, 3)
  .map((v) => ({ label: v, icon: dietaIcon(v), tone: dietaTone(v) }))
const waNum = computed(() => String(custom.value.whatsapp || '').replace(/\D/g, ''))
const waOrder = (prod) => waNum.value
  ? `https://wa.me/${waNum.value}?text=${encodeURIComponent(`Hola ${shopName.value}, me gustaría pedir "${prod.name}" (${formatARS(effectivePrice(prod))}).`)}`
  : ''
</script>

<template>
<div class="sp-page-root cv cv-mc">
  <header class="cv-mc-head">
    <div class="cv-wrap">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">La carta</span>
      </nav>
      <h1 class="cv-mc-title">La carta</h1>
      <p class="cv-mc-sub">{{ shopName }} — {{ total }} {{ total === 1 ? 'producto' : 'productos' }}.</p>
    </div>
  </header>

  <main class="cv-wrap cv-mc-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogToolbar />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <div v-if="catalog.products.length" class="cv-mc-grid" :class="{ loading: catalogStatus === 'loading' }">
          <TplProductCard v-for="prod in visibleProducts" :key="prod.id"
            class="mc-card" :p="prod" :stars="!!prod.rating_count" stars-icon="heart" :stars-size="11"
            seal-shape="circle" ph-icon="coffee" :go="false"
            :add-href="waNum ? waOrder(prod) : ''" :add-label="`Pedir ${prod.name} por WhatsApp`"
            @open="openProduct">
            <template #media-extra><span class="mc-card-price">{{ formatARS(effectivePrice(prod)) }}</span></template>
            <template v-if="dietTagsOf(prod).length" #tags>
              <span class="mc-card-tags"><StTag v-for="t in dietTagsOf(prod)" :key="t.label" kind="dieta" :label="t.label" :icon="t.icon" :tone="t.tone" /></span>
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
.cv-mc .cv-mc-head { padding: 26px 0 18px; border-bottom: 1px dashed var(--sp-line); }
.cv-mc-title { margin: 6px 0 0; font-family: 'Fraunces', 'Georgia', serif; font-size: clamp(40px, 8.5vw, 84px); line-height: .95; font-weight: 600; }
.cv-mc-sub { margin: 8px 0 0; color: var(--sp-muted); font-size: 14px; }
.cv-mc-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 18px; }
.cv-mc-grid.loading { opacity: .55; pointer-events: none; }
.cv-mc-grid .mc-card-media { width: 100%; padding: 0; border: 0; cursor: pointer; text-align: left; }
.cv-mc-grid .mc-card-name { padding: 0; border: 0; background: none; cursor: pointer; text-align: left; }
@media (min-width: 768px) { .cv-mc-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 18px; } }
</style>
