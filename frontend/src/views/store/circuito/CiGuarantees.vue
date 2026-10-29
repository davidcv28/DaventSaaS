<script setup>
// Franja de garantías del diseño CIRCUITO (4 ítems con ícono lineal).
// Fuente: `benefits` de "Mi empresa" (lo que el dueño realmente ofrece:
// garantía, cuotas, envíos, soporte). Si todavía no cargó ninguno, cae a los
// hechos reales de la tienda —mismo criterio que el resto de la web— para no
// prometer nada que el negocio no tenga.
// Respeta show_benefits y se auto-oculta sin datos.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { SERVICE_ICONS } from '../../../api/stores.api.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const ctx = inject('storePage')
const { slug, custom, location, showCatalog, showContact } = ctx
const servicesPage = ctx.showServices

const to = (name) => ({ name, params: storeHostSlug ? {} : { slug: slug.value } })

const fromCustom = computed(() => (Array.isArray(custom.value.benefits) ? custom.value.benefits : []))

// Fallback: garantías construidas con datos que la tienda ya tiene.
const fromStore = computed(() => {
  const list = [
    { icon: 'shield-check', title: 'Garantía oficial', text: 'Todos los productos con garantía del fabricante.' },
    { icon: 'wallet', title: 'Cuotas y medios de pago', text: 'Coordinás el pago con el comercio.' }
  ]
  if (showCatalog.value) {
    list.push({ icon: 'package', title: 'Catálogo actualizado', text: 'Productos, precios y stock siempre a la vista.', to: to('store-catalog') })
  }

  if (servicesPage.value) list.push({ icon: 'wrench', title: 'Soporte técnico propio', text: 'Diagnóstico, instalación y asesoramiento.', to: to('store-services') })
  if (showContact.value) list.push({ icon: 'message-circle', title: 'Atención directa', text: 'Te respondemos por WhatsApp o por el formulario.', href: '#contacto' })
  if (location.value) list.push({ icon: 'map-pin', title: 'Dónde estamos', text: location.value })
  return list
})

const items = computed(() => {
  if (custom.value.show_benefits === false) return []
  const source = fromCustom.value.length
    ? fromCustom.value.map((b) => ({ icon: SERVICE_ICONS[b.icon] ? b.icon : 'shield-check', title: b.title, text: b.text }))
    : fromStore.value
  return source.filter((i) => i.title).slice(0, 4)
})
const show = computed(() => items.value.length >= 2)
</script>

<template>
  <div v-if="show" class="ci-guar">
    <div class="ci-container ci-guar-grid">
      <component
        :is="i.to ? 'RouterLink' : i.href ? 'a' : 'div'" v-for="(i, n) in items" :key="i.title"
        v-reveal="n * 70" class="ci-guar-item" :to="i.to" :href="i.href"
      >
        <span class="ci-guar-icon" aria-hidden="true"><AppIcon :name="i.icon" :size="18" /></span>
        <strong>{{ i.title }}</strong>
        <span v-if="i.text" class="ci-guar-text">{{ i.text }}</span>
      </component>
    </div>
  </div>
</template>
