<script setup>
// Franja de garantías (§6.5-3): fila hairline con 4 datos REALES del negocio
// — sin tarjetas, sin fondo, icono lineal de 16px. No inventa beneficios:
// solo declara lo que la tienda efectivamente tiene (catálogo, servicios,
// contacto, ubicación, años o WhatsApp).
import { computed } from 'vue'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useRhLinks } from './rhLinks.js'

defineProps({ block: { type: Object, default: null } })

const { ctx, catalogTo, servicesTo, whatsappUrl } = useRhLinks()
const { custom, location, showContact, showCatalog, showServices } = ctx

const items = computed(() => {
  const list = []
  if (showCatalog.value) list.push({ key: 'catalog', icon: 'package', label: 'Catálogo online', to: catalogTo.value })
  if (showServices.value) list.push({ key: 'services', icon: 'wrench', label: 'Servicios y presupuesto', to: servicesTo.value })
  if (whatsappUrl.value) list.push({ key: 'wa', icon: 'whatsapp', label: 'Pedidos por WhatsApp', href: whatsappUrl.value })
  if (location.value) list.push({ key: 'loc', icon: 'map-pin', label: location.value })
  if (custom.value.about_years) list.push({ key: 'years', icon: 'clock', label: `+${custom.value.about_years} años de trayectoria` })
  if (showContact.value) list.push({ key: 'contact', icon: 'message-circle', label: 'Formulario de contacto', href: '#contacto' })
  return list.slice(0, 4)
})
const show = computed(() => items.value.length >= 2)
</script>

<template>
  <section v-if="show" class="rh-guarantees" aria-label="Datos del negocio">
    <ul class="rh-wrap rh-guarantees-row">
      <li v-for="(item, i) in items" :key="item.key" v-reveal="60 * i" class="rh-guarantee">
        <component
          :is="item.to ? 'RouterLink' : item.href ? 'a' : 'span'"
          class="rh-guarantee-inner" :to="item.to" :href="item.href"
          :target="item.href?.startsWith('http') ? '_blank' : null"
          :rel="item.href?.startsWith('http') ? 'noopener' : null"
        >
          <AppIcon :name="item.icon" :size="16" aria-hidden="true" />
          <span>{{ item.label }}</span>
        </component>
      </li>
    </ul>
  </section>
</template>
