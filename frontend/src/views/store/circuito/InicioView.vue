<script setup>
// Inicio del diseño CIRCUITO (tecnología / electrónica).
// Portada GENERATIVA: monta las secciones de useLayout('landing') en el orden
// efectivo (layout canónico ∪ layout_config) respetando on/off, variante y
// props de cada bloque; el default es EXACTAMENTE la composición técnica de
// siempre (barra de acento, hero partido con tarjeta, franja de 4 garantías,
// categorías 6 en 3×2, destacados, banda de servicios, oferta + cuenta
// regresiva, marcas, testimonios, FAQ y contacto). Las piezas firma (Ci*) se
// montan con wrapper sin `block`; la sección de categorías conserva su
// encabezado propio y se auto-oculta sin categorías con productos.
// La piel vive en assets/store-circuito.css con raíz [data-template="circuito"].
import { computed, defineComponent, h, inject } from 'vue'
import { RouterLink } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import { templateBlocks } from '../../../templates/index.js'
import { firma, landingExtras } from '../../../templates/_shared.js'
import AppIcon from '../../../components/AppIcon.vue'
import BlkAnnouncements from '../../../components/store/blocks/BlkAnnouncements.vue'
import BlkCategories from '../../../components/store/blocks/BlkCategories.vue'
import BlkFeatured from '../../../components/store/blocks/BlkFeatured.vue'
import BlkBrands from '../../../components/store/blocks/BlkBrands.vue'
import BlkTestimonials from '../../../components/store/blocks/BlkTestimonials.vue'
import BlkFaq from '../../../components/store/blocks/BlkFaq.vue'
import BlkContact from '../../../components/store/blocks/BlkContact.vue'
import CiHero from './CiHero.vue'
import CiGuarantees from './CiGuarantees.vue'
import CiServicesBand from './CiServicesBand.vue'

const ctx = inject('storePage')
const { slug, showCatalog } = ctx
const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const { featured } = useFeaturedCatalog()
const catRows = computed(() => featured.value.categories.filter(
  (c) => featured.value.products.some((p) => p.category === c.id)
))
const hasCats = computed(() => catRows.value.length > 0)
const catMeta = computed(() => {
  const n = catRows.value.length
  return `${String(n).padStart(2, '0')} ${n === 1 ? 'módulo' : 'módulos'} · index 01–${String(n).padStart(2, '0')}`
})

// Categorías: la sección con encabezado propio envuelve al bloque compartido
// (que también aplica la variante/props del layout). Sin categorías con
// productos se oculta entera, como en la composición clásica.
const CiCategories = defineComponent({
  name: 'CiCategoriesBlock',
  props: { block: { type: Object, default: null } },
  setup(props) {
    return () => (hasCats.value
      ? h('section', { class: 'ci-cats', 'aria-labelledby': 'ci-cats-title' }, [
        h('div', { class: 'ci-container ci-sec-head' }, [
          h('div', { class: 'ci-sec-head-main' }, [
            h('p', { class: 'ci-label' }, 'Catálogo'),
            h('h2', { id: 'ci-cats-title' }, 'Categorías'),
            h('p', { class: 'ci-sec-meta', 'aria-hidden': 'true' }, `// ${catMeta.value}`)
          ]),
          showCatalog.value
            ? h(RouterLink, { class: 'ci-sec-more', to: catalogTo.value }, () => [
              'Ver todo el catálogo',
              h(AppIcon, { name: 'arrow-right', size: 14 })
            ])
            : null
        ]),
        h(BlkCategories, { block: props.block || { id: 'categories' } })
      ])
      : null)
  }
})

const MAP = {
  ...landingExtras,
  announcements: BlkAnnouncements,
  hero: firma(CiHero),
  highlights: firma(CiGuarantees),
  categories: CiCategories,
  featured: BlkFeatured,
  services: firma(CiServicesBand),
  brands: BlkBrands,
  testimonials: BlkTestimonials,
  faq: BlkFaq,
  contact: BlkContact
}

const visible = computed(() => templateBlocks(ctx.pageTemplate.value, 'landing')
  .filter((b) => b.enabled !== false && MAP[b.id]))
</script>

<template>
  <div class="sp-page-root ci-home">
    <component v-for="b in visible" :key="b.id" :is="MAP[b.id]" :block="b" :data-blk="b.id" />
  </div>
</template>
