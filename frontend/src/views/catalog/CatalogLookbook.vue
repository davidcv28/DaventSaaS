<script setup>
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFilters from './CatalogFilters.vue'
import CatalogToolbar from './CatalogToolbar.vue'
import TplProductCard from '../../components/store/TplProductCard.vue'

// Lookbook: el catálogo como edición de revista — título serif con índice de
// contenidos (las categorías, numeradas) y pliegos de imagen en columnas con
// proporciones alternadas. Los filtros van en la sidebar/sheet unificada.
const {
  custom, shopName, homeTo, year, catalog, catalogStatus, loadCatalog, activeCategories,
  visibleProducts, hasMoreProducts, showMore, pickCategory, clearCategories, clearFilters, hasFilters, total,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct
} = useStoreCatalog({ pageSize: 12 })

const pad = (n) => String(n).padStart(2, '0')
</script>

<template>
<div class="sp-page-root cv cv-lb">
  <header class="cv-wrap cv-lb-head">
    <div class="cv-lb-masthead">
      <nav class="cv-crumbs" aria-label="Ruta">
        <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
        <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
        <span aria-current="page">Catálogo</span>
      </nav>
      <p class="cv-lb-issue"><span>Edición Nº {{ pad(1) }}</span><i aria-hidden="true"></i><span>{{ shopName }} · {{ year }}</span></p>
      <h1 class="cv-lb-title">Índice de la <em>colección</em></h1>
      <p class="cv-lb-lede" role="status" aria-live="polite">{{ total }} {{ total === 1 ? 'pieza' : 'piezas' }} seleccionadas, ordenadas para hojear sin apuro.</p>
    </div>
    <nav v-if="catalog.categories.length" class="cv-lb-toc" aria-label="Categorías">
      <p class="cv-lb-toc-h">Contenido</p>
      <ol>
        <li><button type="button" :class="{ on: !activeCategories.length }" @click="clearCategories"><b>00</b><span>Toda la colección</span><i aria-hidden="true"></i></button></li>
        <li v-for="(cat, i) in catalog.categories" :key="cat.id"><button type="button" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)" @click="pickCategory(cat.id)"><b>{{ pad(i + 1) }}</b><span>{{ cat.name }}</span><i aria-hidden="true" class="cf-n">{{ cat.products_count ?? 0 }}</i></button></li>
      </ol>
    </nav>
  </header>

  <main class="cv-wrap cv-lb-main">
    <CatalogPromoBanner :promotions="catalog.promotions" />
    <div class="cf-body">
      <CatalogFilters />
      <div class="cf-main">
    <CatalogToolbar />
    <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" :skeletons="6" @retry="loadCatalog" @clear="clearFilters" />

    <div v-if="catalog.products.length" class="cv-lb-sheets" :class="{ loading: catalogStatus === 'loading' }">
      <TplProductCard
        v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 3) * 80"
        tag="figure" class="cv-lb-sheet" :p="p" :cat="categoryNameOf(p)" :brand="brandNameOf(p)"
        :stars="custom.show_reviews" stars-icon="diamond" seal-shape=""
        :index="`Nº ${pad(i + 1)}`" :go="false" :ph-size="30" @open="openProduct" />
    </div>

    <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" text="Pasar la página" @more="showMore" />
      </div>
    </div>
  </main>
</div>
</template>
