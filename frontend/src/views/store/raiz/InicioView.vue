<script setup>
// Inicio del diseño RAÍZ (generalista / retail / servicios).
// Composición FIJA de 14 secciones: la vista decide el orden (no
// layout_config) y cada bloque se auto-oculta si no tiene contenido, así una
// tienda vacía no deja huecos. La piel vive en assets/store-raiz.css con raíz
// [data-template="raiz"].
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkHero from '../../../components/store/blocks/BlkHero.vue'
import BlkHighlights from '../../../components/store/blocks/BlkHighlights.vue'
import BlkCategories from '../../../components/store/blocks/BlkCategories.vue'
import BlkFeatured from '../../../components/store/blocks/BlkFeatured.vue'
import BlkAbout from '../../../components/store/blocks/BlkAbout.vue'
import BlkStats from '../../../components/store/blocks/BlkStats.vue'
import BlkServices from '../../../components/store/blocks/BlkServices.vue'
import BlkBenefits from '../../../components/store/blocks/BlkBenefits.vue'
import BlkOffers from '../../../components/store/blocks/BlkOffers.vue'
import BlkCountdown from '../../../components/store/blocks/BlkCountdown.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkGallery from '../../../components/store/blocks/BlkGallery.vue'
import BlkTestimonials from '../../../components/store/blocks/BlkTestimonials.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
</script>

<template>
  <div class="sp-page-root rz-home">
    <BlkAnnouncements :block="{ id: 'announcements', variant: 'static' }" />
    <BlkHero :block="{ id: 'hero', variant: 'split' }" />
    <BlkHighlights :block="{ id: 'highlights' }" />
    <BlkCategories :block="{ id: 'categories', variant: 'row' }" />
    <BlkFeatured :block="{ id: 'featured', variant: 'grid', props: { title: 'Productos recientes' } }" />
    <BlkAbout :block="{ id: 'about' }" />
    <BlkStats :block="{ id: 'stats', variant: 'cards' }" />
    <BlkServices :block="{ id: 'services' }" />
    <BlkBenefits :block="{ id: 'benefits', variant: 'cards' }" />
    <BlkCountdown :block="{ id: 'countdown', variant: 'card' }" />
    <BlkOffers :block="{ id: 'offers', variant: 'grid' }" />
    <BlkBrands :block="{ id: 'brands', variant: 'logos' }" />
    <BlkGallery :block="{ id: 'gallery', variant: 'grid' }" />
    <BlkTestimonials :block="{ id: 'testimonials', variant: 'cards' }" />
    <BlkFaq :block="{ id: 'faq', variant: 'list' }" />
    <BlkCta :block="{ id: 'cta', variant: 'band' }" />
    <BlkContact :block="{ id: 'contact', variant: 'card' }" />
  </div>
</template>
