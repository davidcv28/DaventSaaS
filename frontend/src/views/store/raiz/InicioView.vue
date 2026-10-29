<script setup>
// Inicio del diseño RAÍZ (generalista / retail / servicios) — v2.
// Composición EDITORIAL fija (§6.5 de la corrección profunda): la vista decide
// el orden, no layout_config. Cada sección es un componente Rh* que se
// auto-oculta sin datos, así una tienda vacía no deja huecos ni bandas
// repetidas. La numeración de secciones (01, 02…) la resuelve el CSS con un
// contador: si una sección se oculta, las siguientes se renumeran solas.
// La piel del chrome/tokens vive en assets/store-raiz.css; la portada en
// assets/store-raiz-home.css.
import RhAnnouncements from '../../../components/store/blocks/raiz/RhAnnouncements.vue'
import RhHero from '../../../components/store/blocks/raiz/RhHero.vue'
import RhGuarantees from '../../../components/store/blocks/raiz/RhGuarantees.vue'
import RhCategories from '../../../components/store/blocks/raiz/RhCategories.vue'
import RhRecent from '../../../components/store/blocks/raiz/RhRecent.vue'
import RhAbout from '../../../components/store/blocks/raiz/RhAbout.vue'
import RhStats from '../../../components/store/blocks/raiz/RhStats.vue'
import RhServices from '../../../components/store/blocks/raiz/RhServices.vue'
import RhBenefits from '../../../components/store/blocks/raiz/RhBenefits.vue'
import RhCountdown from '../../../components/store/blocks/raiz/RhCountdown.vue'
import RhOffers from '../../../components/store/blocks/raiz/RhOffers.vue'
import RhBrands from '../../../components/store/blocks/raiz/RhBrands.vue'
import RhGallery from '../../../components/store/blocks/raiz/RhGallery.vue'
import RhTestimonials from '../../../components/store/blocks/raiz/RhTestimonials.vue'
import RhFaq from '../../../components/store/blocks/raiz/RhFaq.vue'
import RhCta from '../../../components/store/blocks/raiz/RhCta.vue'
import RhContact from '../../../components/store/blocks/raiz/RhContact.vue'
</script>

<template>
  <main class="sp-page-root rz-home">
    <RhAnnouncements :block="{ id: 'announcements' }" />
    <RhHero :block="{ id: 'hero' }" />
    <RhGuarantees :block="{ id: 'highlights' }" />
    <RhCategories :block="{ id: 'categories' }" />
    <RhRecent :block="{ id: 'featured', props: { title: 'Recién llegados' } }" />
    <RhAbout :block="{ id: 'about' }" />
    <RhStats :block="{ id: 'stats' }" />
    <RhServices :block="{ id: 'services' }" />
    <RhBenefits :block="{ id: 'benefits' }" />
    <RhCountdown :block="{ id: 'countdown' }" />
    <RhOffers :block="{ id: 'offers' }" />
    <RhBrands :block="{ id: 'brands' }" />
    <RhGallery :block="{ id: 'gallery' }" />
    <RhTestimonials :block="{ id: 'testimonials' }" />
    <RhFaq :block="{ id: 'faq' }" />
    <RhCta :block="{ id: 'cta' }" />
    <RhContact :block="{ id: 'contact' }" />
  </main>
</template>
