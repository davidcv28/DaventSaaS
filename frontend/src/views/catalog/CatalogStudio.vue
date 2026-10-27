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
import '../../assets/store-studio.css'
import TplProductCard from '../../components/store/TplProductCard.vue'

// Studio/Proceso (Servicios): misma lista ordenada, dos lecturas —
// studio = cards redondeadas con CTA implícito; proceso = índice de
// ítems numerados con hairlines, números en mono y precio tabular.
// Filtros/orden: bloques compartidos.
const {
  custom, shopName, homeTo, catalog, catalogStatus, loadCatalog, pageTemplate,
  visibleProducts, hasMoreProducts, showMore, clearFilters, hasFilters, total,
  shownLabel, shownPct, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 10 })
const variant = computed(() => (pageTemplate.value === 'proceso' ? 'proceso' : 'studio'))

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
<div class="sp-page-root cv cv-sd sd" :data-var="variant">
  <header class="cv-sd-head">
    <div class="cv-wrap">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <h1 class="cv-sd-title">{{ variant === 'proceso' ? 'Índice de servicios' : 'Todo lo que ofrecemos' }}</h1>
      <p class="cv-sd-sub">{{ variant === 'proceso' ? `ÍTEM · NOMBRE · VALOR — ${total} en total.` : `${shopName} — ${total} ${total === 1 ? 'ítem' : 'ítems'} disponibles.` }}</p>
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
            <TplProductCard
              class="sd-svc" layout="row" :p="prod" :desc="prod.description || ''"
              :stars="!!prod.rating_count" stars-icon="star" :stars-size="11"
              seal-shape="" :go="false"
              :ph-size="22" @open="openProduct">
              <template v-if="tagsOf(prod).length" #tags>
                <span class="sd-svc-tags"><StTag v-for="t in tagsOf(prod)" :key="t.label" kind="modalidad" :label="t.label" :icon="t.icon" /></span>
              </template>
            </TplProductCard>
          </li>
        </ul>

        <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>


