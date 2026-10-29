<script setup>
// Inicio del diseño TRAMA (indumentaria / moda).
// Composición FIJA de 12 secciones (spec §7.1): barra promo, hero partido,
// marquee de acento, categorías, nueva temporada, lookbook, beneficios,
// looks del mes, FAQ, banda CTA y contacto (el header/footer/barra móvil son
// el chrome compartido, re-skineado desde store-trama.css). El orden lo pone
// esta vista — layout_config se ignora — y cada pieza se auto-oculta sin
// contenido para no dejar huecos en una tienda vacía.
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkBenefits from '../../../components/store/blocks/BlkBenefits.vue'
import BlkGallery from '../../../components/store/blocks/BlkGallery.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkCta from '../../../components/store/blocks/BlkCta.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import TrHero from './TrHero.vue'
import TrMarquee from './TrMarquee.vue'
import TrCategories from './TrCategories.vue'
import TrFeatured from './TrFeatured.vue'
import TrLookbook from './TrLookbook.vue'
</script>

<template>
  <div class="sp-page-root tr-home">
    <BlkAnnouncements :block="{ id: 'announcements', variant: 'static' }" />
    <TrHero />
    <TrMarquee />
    <TrCategories />
    <TrFeatured />
    <TrLookbook />
    <BlkBenefits :block="{ id: 'benefits', variant: 'cards' }" />
    <BlkGallery :block="{ id: 'gallery', variant: 'grid', props: { title: 'Looks del mes' } }" />
    <BlkFaq :block="{ id: 'faq', variant: 'accordion' }" />
    <BlkCta :block="{ id: 'cta', variant: 'band' }" />
    <BlkContact :block="{ id: 'contact', variant: 'card' }" />
  </div>
</template>
