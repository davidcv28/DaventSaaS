<script setup>
// Página de catálogo de la web pública (/<slug>/catalogo). El diseño
// configurado (pageTemplate) elige la composición completa: 'classic' es el
// catálogo estándar y cada otro diseño trae su propia página (layout, filtros
// y tarjetas propios) sobre el mismo estado (composables/useStoreCatalog).
// Como StoreHomeView, solo consume el contexto `storePage` del layout.
import { computed, inject, defineAsyncComponent } from 'vue'
import CatalogClassic from './catalog/CatalogClassic.vue'
import AppIcon from '../components/AppIcon.vue'
import '../assets/store-catalog.css'
import '../assets/store-catalog-responsive.css'
import '../assets/store-catalog-polish.css'

const ctx = inject('storePage')
// Aviso configurable del dueño: tira informativa arriba del catálogo
// (envíos, medios de pago, retiro). Vacío -> no se muestra.
const catalogNote = computed(() => (ctx?.custom?.value?.catalog_note || '').trim())
const VARIANTS = {
  perspective: defineAsyncComponent(() => import('./catalog/CatalogPerspective.vue')),
  duo: defineAsyncComponent(() => import('./catalog/CatalogDuo.vue')),
  street: defineAsyncComponent(() => import('./catalog/CatalogStreet.vue')),
  promo: defineAsyncComponent(() => import('./catalog/CatalogPromo.vue')),
  terminal: defineAsyncComponent(() => import('./catalog/CatalogTerminal.vue')),
  lookbook: defineAsyncComponent(() => import('./catalog/CatalogLookbook.vue')),
  shop: defineAsyncComponent(() => import('./catalog/CatalogShop.vue')),
  cobre: defineAsyncComponent(() => import('./catalog/CatalogCobre.vue')),
  minimal: defineAsyncComponent(() => import('./catalog/CatalogMinimal.vue')),
  boutique: defineAsyncComponent(() => import('./catalog/CatalogBoutique.vue')),
  signature: defineAsyncComponent(() => import('./catalog/CatalogSignature.vue')),
  aurora: defineAsyncComponent(() => import('./catalog/CatalogAurora.vue')),
  bloque: defineAsyncComponent(() => import('./catalog/CatalogBloque.vue')),
  riso: defineAsyncComponent(() => import('./catalog/CatalogRiso.vue')),
  terra: defineAsyncComponent(() => import('./catalog/CatalogTerra.vue'))
}
const component = computed(() => VARIANTS[ctx?.pageTemplate?.value] || CatalogClassic)
</script>

<template>
  <div class="cv-outer">
    <p v-if="catalogNote" class="cv-note" role="note"><AppIcon name="megaphone" :size="15" />{{ catalogNote }}</p>
    <component :is="component" />
  </div>
</template>
