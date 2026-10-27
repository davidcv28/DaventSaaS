<script setup>
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFilters from './CatalogFilters.vue'
import CatalogToolbar from './CatalogToolbar.vue'
import ProductStars from '../../components/ProductStars.vue'
import OfferSeal from '../../components/store/OfferSeal.vue'
import StTag from '../../components/store/StTag.vue'
import '../../assets/store-studio.css'

// Studio/Proceso (Servicios): el catálogo como lista ordenada — cards
// horizontales de ancho completo, icono en cuadrado, tags de modalidad y
// precio a la derecha. Filtros/orden: bloques compartidos.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters, total,
  shownLabel, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 10 })

const tagsOf = (p) => {
  const tags = []
  const rows = Object.entries(p?.features || {})
  const dur = rows.find(([k]) => /duraci|tiempo/i.test(k))
  if (dur) tags.push({ label: String(dur[1]).split(/[,\/·]/)[0].trim(), icon: 'clock' })
  if (custom.value.service_ask_address !== false) tags.push({ label: 'A domicilio', icon: 'truck' })
  return tags.slice(0, 2)
}
</script>

<template>
<div class="sp-page-root cv cv-sd">
  <header class="cv-sd-head">
    <div class="cv-wrap">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <h1 class="cv-sd-title">Todo lo que ofrecemos</h1>
      <p class="cv-sd-sub">{{ shopName }} — {{ total }} {{ total === 1 ? 'ítem' : 'ítems' }} disponibles.</p>
    </div>
  </header>

  <main class="cv-wrap cv-sd-main">
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
        <CatalogPromoBanner :promotions="catalog.promotions" />
        <CatalogToolbar />
        <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

        <ul v-if="catalog.products.length" class="cv-sd-list" :class="{ loading: catalogStatus === 'loading' }">
          <li v-for="prod in visibleProducts" :key="prod.id">
            <article class="sd-svc" role="link" tabindex="0" :aria-label="`${prod.name} — ${formatARS(effectivePrice(prod))}`" @click="openProduct(prod)" @keydown.enter="openProduct(prod)">
              <span class="sd-svc-icon">
                <img v-if="prod.image" :src="prod.image" alt="" loading="lazy" class="sd-svc-thumb" />
                <AppIcon v-else name="package" :size="22" />
              </span>
              <span class="sd-svc-body">
                <strong>{{ prod.name }}</strong>
                <span v-if="prod.description" class="sd-svc-desc">{{ prod.description }}</span>
                <ProductStars v-if="prod.rating_count" :avg="prod.rating_avg" :count="prod.rating_count" icon="star" :size="11" />
                <span v-if="tagsOf(prod).length" class="sd-svc-tags"><StTag v-for="t in tagsOf(prod)" :key="t.label" kind="modalidad" :label="t.label" :icon="t.icon" /></span>
              </span>
              <span class="sd-svc-price">
                <OfferSeal v-if="productOffer(prod) != null" :pct="offerPct(prod)" shape="ribbon" small />
                {{ formatARS(effectivePrice(prod)) }}
              </span>
            </article>
          </li>
        </ul>

        <CatalogMore :has-more="hasMoreProducts" :label="shownLabel" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>

<style>
.cv-sd .cv-sd-head { padding: 26px 0 18px; border-bottom: 1px solid var(--sp-line); }
.cv-sd-title { margin: 6px 0 0; font-family: 'Manrope', sans-serif; font-size: clamp(32px, 7vw, 64px); line-height: 1; font-weight: 800; letter-spacing: -.025em; }
.cv-sd-sub { margin: 8px 0 0; color: var(--sp-muted); font-size: 14px; }
.cv-sd-list { display: grid; gap: 12px; margin: 18px 0 0; padding: 0; list-style: none; }
.cv-sd-list.loading { opacity: .55; pointer-events: none; }
.cv-sd-list .sd-svc { cursor: pointer; }
.cv-sd-list .sd-svc-price { display: grid; justify-items: end; gap: 5px; }
</style>
