<script setup>
import { computed } from 'vue'
import { useStoreCatalog, SORT_OPTIONS } from '../../composables/useStoreCatalog.js'
import { formatARS } from '../../api/billing.api.js'
import { productOffer, effectivePrice, offerPct, isNewProduct, productDiscount, offerEndsLabel } from '../../api/catalog.api.js'
import AppIcon from '../../components/AppIcon.vue'
import { vReveal } from '../../directives/reveal.js'
import CatalogFeedback from './CatalogFeedback.vue'
import CatalogMore from './CatalogMore.vue'
import CatalogPromoBanner from './CatalogPromoBanner.vue'
import CatalogFacets from './CatalogFacets.vue'
import CatalogTags from './CatalogTags.vue'
import ProductStars from '../../components/ProductStars.vue'

// Publicidad: el catálogo como folleto de campaña — afiche con ráfaga, un
// carril "Ofertas" con carteles de descuento y la grilla completa donde cada
// producto cierra con un botón directo a WhatsApp.
const {
  ui, custom, shopName, homeTo, catalog, catalogStatus, loadCatalog, activeCategories, activeBrands, priceMin, priceMax, sort,
  visibleProducts, hasMoreProducts, showMore, pickCategory, pickBrand, clearFilters, hasFilters, total, offerCount,
  shownLabel, shownPct, brandNameOf, categoryNameOf, openProduct, askUrl, whatsappUrl
} = useStoreCatalog({ pageSize: 12 })

const offers = computed(() => catalog.value.products.filter((p) => productOffer(p) != null).slice(0, 8))
const topPct = computed(() => offers.value.reduce((m, p) => Math.max(m, offerPct(p)), 0))
</script>

<template>
<div class="sp-page-root cv cv-pr">
  <header class="cv-pr-poster">
    <span class="cv-pr-burst" aria-hidden="true"></span>
    <div class="cv-wrap cv-pr-poster-in">
      <div class="cv-pr-copy">
        <nav class="cv-crumbs" aria-label="Ruta">
          <RouterLink v-if="custom.site_mode !== 'catalog'" :to="homeTo">Inicio</RouterLink>
          <AppIcon v-if="custom.site_mode !== 'catalog'" name="chevron-right" :size="13" aria-hidden="true" />
          <span aria-current="page">Catálogo</span>
        </nav>
        <p class="cv-pr-tag"><AppIcon name="megaphone" :size="14" /> {{ shopName }}</p>
        <h1 class="cv-pr-title">{{ offerCount ? 'Ofertas y' : 'Todo' }} <mark>catálogo</mark></h1>
        <p class="cv-pr-sub">{{ total }} {{ total === 1 ? 'producto' : 'productos' }} listos para llevarte{{ whatsappUrl ? ' — pedilos por WhatsApp' : '' }}.</p>
      </div>
      <div v-if="topPct" class="cv-pr-seal" aria-hidden="true"><small>hasta</small><strong>{{ topPct }}%</strong><small>off</small></div>
    </div>
  </header>

  <main class="cv-wrap cv-pr-main">
    <CatalogPromoBanner :promotions="catalog.promotions" />
    <section v-if="offers.length" class="cv-pr-offers" aria-labelledby="cv-pr-off-t">
      <h2 id="cv-pr-off-t" class="cv-pr-h"><AppIcon name="flame" :size="20" /> Ofertas de la semana</h2>
      <div class="cv-pr-rail">
        <article v-for="p in offers" :key="`o${p.id}`" class="cv-pr-poster-card" role="link" tabindex="0" :aria-label="`Ver ${p.name}`" @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)">
          <div class="cv-pr-poster-media">
            <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
            <span v-else class="cv-pr-ph"><AppIcon name="package" :size="30" /></span>
            <span class="cv-pr-star" aria-hidden="true">-{{ offerPct(p) }}%</span>
          </div>
          <div class="cv-pr-poster-body">
            <h3>{{ p.name }}</h3>
            <ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" icon="flame" :size="12" />
            <p class="cv-pr-was">{{ formatARS(p.price) }}</p>
            <p class="cv-pr-now">{{ formatARS(effectivePrice(p)) }}</p>
            <p v-if="offerEndsLabel(productDiscount(p))" class="cv-pr-ends">{{ offerEndsLabel(productDiscount(p)) }}</p>
          </div>
        </article>
      </div>
    </section>

    <section aria-labelledby="cv-pr-all-t">
      <h2 id="cv-pr-all-t" class="cv-pr-h"><AppIcon name="tag" :size="20" /> {{ hasFilters ? 'Resultados' : 'Todos los productos' }}</h2>
      <div class="cv-pr-bar" role="group" aria-label="Filtros del catálogo">
        <label class="cv-pr-box cv-pr-search"><AppIcon name="search" :size="16" aria-hidden="true" /><input v-model="ui.search" type="search" placeholder="¿Qué estás buscando?" aria-label="Buscar productos" /></label>
        <div class="cv-pr-box"><span>$</span><input v-model="priceMin" type="text" inputmode="decimal" placeholder="Mínimo" aria-label="Precio mínimo" /><b aria-hidden="true">a</b><span>$</span><input v-model="priceMax" type="text" inputmode="decimal" placeholder="Máximo" aria-label="Precio máximo" /></div>
        <label class="cv-pr-box"><select v-model="sort" aria-label="Ordenar por"><option v-for="o in SORT_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</option></select><AppIcon name="chevron-down" :size="14" aria-hidden="true" /></label>
      </div>
      <div class="cv-pr-chips" role="group" aria-label="Categorías y marcas">
        <button type="button" class="cv-pr-chip" :class="{ on: !activeCategories.length && !activeBrands.length }" @click="clearFilters">Todo</button>
        <button v-for="cat in catalog.categories" :key="`c${cat.id}`" type="button" class="cv-pr-chip" :class="{ on: activeCategories.includes(cat.id) }" :aria-pressed="activeCategories.includes(cat.id)" @click="pickCategory(cat.id)">{{ cat.name }} <i class="cf-n" aria-hidden="true">{{ cat.products_count ?? 0 }}</i></button>
        <button v-for="b in catalog.brands" :key="`b${b.id}`" type="button" class="cv-pr-chip alt" :class="{ on: activeBrands.includes(b.id) }" :aria-pressed="activeBrands.includes(b.id)" @click="pickBrand(b.id)">{{ b.name }} <i class="cf-n" aria-hidden="true">{{ b.products_count ?? 0 }}</i></button>
      </div>
      <CatalogFacets />
      <CatalogTags />

      <CatalogFeedback :status="catalogStatus" :empty="!catalog.products.length" :has-filters="hasFilters" @retry="loadCatalog" @clear="clearFilters" />

      <div v-if="catalog.products.length" class="cv-pr-grid" :class="{ loading: catalogStatus === 'loading' }">
        <article v-for="(p, i) in visibleProducts" :key="p.id" v-reveal="(i % 4) * 60" class="cv-pr-card">
          <div class="cv-pr-media" role="link" tabindex="0" :aria-label="`Ver ${p.name}`" @click="openProduct(p)" @keydown.enter.prevent="openProduct(p)">
            <img v-if="p.image" :src="p.image" :alt="p.name" loading="lazy" />
            <span v-else class="cv-pr-ph"><AppIcon name="package" :size="28" /></span>
            <span v-if="productOffer(p) != null" class="cv-pr-flag">-{{ offerPct(p) }}%</span>
            <span v-else-if="isNewProduct(p)" class="cv-pr-flag new">Nuevo</span>
          </div>
          <div class="cv-pr-body">
            <p v-if="categoryNameOf(p) || brandNameOf(p)" class="cv-pr-eyebrow">{{ [categoryNameOf(p), brandNameOf(p)].filter(Boolean).join(' · ') }}</p>
            <h3 class="cv-pr-name">{{ p.name }}</h3>
            <ProductStars v-if="custom.show_reviews && p.rating_count" :avg="p.rating_avg" :count="p.rating_count" icon="flame" :size="12" />
            <p class="cv-pr-price"><s v-if="productOffer(p) != null">{{ formatARS(p.price) }}</s>{{ formatARS(effectivePrice(p)) }}</p>
            <p v-if="offerEndsLabel(productDiscount(p))" class="cv-pr-ends">{{ offerEndsLabel(productDiscount(p)) }}</p>
            <a v-if="whatsappUrl" class="cv-pr-cta" :href="askUrl(p)" target="_blank" rel="noopener" @click.stop><AppIcon name="whatsapp" :size="16" /> Lo quiero</a>
            <button v-else type="button" class="cv-pr-cta" @click="openProduct(p)"><AppIcon name="eye" :size="16" /> Ver producto</button>
          </div>
        </article>
      </div>

      <CatalogMore v-if="hasMoreProducts && catalogStatus !== 'error'" :label="shownLabel" :pct="shownPct" @more="showMore" />
    </section>
  </main>
</div>
</template>
