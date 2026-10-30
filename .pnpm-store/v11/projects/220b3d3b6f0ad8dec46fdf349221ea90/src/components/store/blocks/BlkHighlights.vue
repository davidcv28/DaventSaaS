<script setup>
// Bloque 'highlights': tarjetas con icono bajo el hero, armadas con lo
// que el negocio realmente tiene cargado y completadas con valores
// genéricos. Cede su lugar a los departamentos cuando el bloque
// 'categories' está habilitado y tiene datos (misma regla v-else que
// tenía la vista monolítica); también respeta el viejo switch
// show_highlights de "Mi empresa".
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'
import { useLayout } from '../../../composables/useLayout.js'

defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, location, showContact, showCatalog } = ctx
const servicesPage = ctx.showServices
const { featured: shopCatalog } = useFeaturedCatalog()
const { blocks } = useLayout('landing')

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const shopDepts = computed(() => shopCatalog.value.categories
  .map((c) => {
    const items = shopCatalog.value.products.filter((p) => p.category === c.id)
    return { id: c.id, count: items.length }
  })
  .filter((d) => d.count > 0)
  .slice(0, 6))
// Los departamentos ocupan este slot solo si el bloque 'categories' está
// habilitado en el layout efectivo Y tiene datos reales que mostrar.
const deptsVisible = computed(() =>
  blocks.value.some((b) => b.id === 'categories' && b.enabled !== false) && shopDepts.value.length > 0
)

const highlights = computed(() => {
  const list = []
  if (showCatalog.value) list.push({ icon: 'package', title: 'Catálogo online', text: 'Explorá todos los productos con precios y detalles actualizados.', to: catalogTo.value })
  if (servicesPage.value) list.push({ icon: 'wrench', title: 'Servicios', text: 'Elegí lo que necesitás, mirá el presupuesto y coordinamos por WhatsApp.', to: servicesTo.value })
  if (showContact.value) list.push({ icon: 'message-circle', title: 'Consultas directas', text: 'Escribinos y te respondemos a la brevedad.', href: '#contacto' })
  if (location.value) list.push({ icon: 'map-pin', title: 'Dónde estamos', text: location.value })
  if (custom.value.about_years) list.push({ icon: 'clock', title: `+${custom.value.about_years} años`, text: 'De trayectoria y experiencia en lo que hacemos.' })
  list.push(
    { icon: 'users', title: 'Atención personalizada', text: 'Te acompañamos en cada paso de tu compra.' },
    { icon: 'shield-check', title: 'Información clara', text: 'Productos y precios claros, sin sorpresas.' }
  )
  return list.slice(0, 4)
})
const show = computed(() => custom.value.show_highlights !== false && !deptsVisible.value && highlights.value.length > 0)
</script>

<template>
  <div v-if="show" class="sp-container sp-highlights">
    <component
      :is="h.to ? 'RouterLink' : h.href ? 'a' : 'div'" v-for="(h, i) in highlights" :key="h.title"
      v-reveal="i * 90" class="sp-hl" :to="h.to" :href="h.href"
    >
      <span class="sp-hl-icon" aria-hidden="true"><AppIcon :name="h.icon" :size="22" /></span>
      <strong>{{ h.title }}</strong>
      <span class="sp-hl-text">{{ h.text }}</span>
    </component>
  </div>
</template>
