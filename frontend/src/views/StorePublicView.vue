<script setup>
// Página de inicio de la familia StorePublicView (classic, perspective,
// promo, street, terminal, lookbook, cobre, minimal, boutique,
// signature, aurora y shop): la composición es declarativa — un
// BlockRenderer itera los bloques habilitados del layout efectivo
// (default de la plantilla ∪ customization.layout_config) y monta el
// componente de src/components/store/blocks/. Las secciones de marketing
// van en su orden fijo (SECTION_ORDER_KEYS vía usesSectionOrder) y los
// bloques sin datos se auto-ocultan en su propio v-if.
import BlockRenderer from '../components/store/BlockRenderer.vue'
import { SP_LANDING_BLOCKS } from '../components/store/blocks/index.js'
</script>

<template>
<div class="sp-page-root">
  <BlockRenderer surface="landing" :components="SP_LANDING_BLOCKS" />
</div>
</template>
