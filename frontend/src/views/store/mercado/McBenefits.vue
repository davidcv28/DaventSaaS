<script setup>
// Franja de confianza firma de MERCADO: beneficios cargados por el dueño o,
// si no hay, datos reales de la tienda (catálogo, ubicación, WhatsApp y
// trayectoria). Nunca inventa envíos, cuotas ni garantías.
import { computed, inject } from 'vue'
import { SERVICE_ICONS } from '../../../api/stores.api.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom, location, showCatalog } = ctx

const benefits = computed(() => (Array.isArray(custom.value.benefits) ? custom.value.benefits : []))
const items = computed(() => {
  if (benefits.value.length) {
    return benefits.value.slice(0, 4).map((b) => ({
      key: `b-${b.title}`,
      icon: SERVICE_ICONS[b.icon] ? b.icon : 'shield-check',
      title: b.title,
      text: b.text || ''
    }))
  }
  const list = []
  if (showCatalog.value) list.push({ key: 'catalog', icon: 'catalog', title: 'Catálogo online', text: 'Consultá precios y disponibilidad.' })
  if (custom.value.whatsapp) list.push({ key: 'wa', icon: 'whatsapp', title: 'Atención por WhatsApp', text: 'Escribinos y te respondemos.' })
  if (location.value) list.push({ key: 'loc', icon: 'map-pin', title: location.value, text: 'Punto de venta y retiro.' })
  if (custom.value.about_years) list.push({ key: 'years', icon: 'badge-check', title: `${custom.value.about_years} años de trayectoria`, text: '' })
  return list.slice(0, 4)
})
const show = computed(() => custom.value.show_benefits !== false && items.value.length > 0)
</script>

<template>
  <section v-if="show" class="mc-trust" aria-label="Beneficios de la tienda">
    <div class="mc-wrap mc-trust-grid">
      <div v-for="(b, i) in items" :key="b.key" v-reveal="i * 60" class="mc-trust-item">
        <span class="mc-trust-icon" aria-hidden="true"><AppIcon :name="b.icon" :size="20" /></span>
        <span class="mc-trust-copy">
          <strong>{{ b.title }}</strong>
          <span v-if="b.text">{{ b.text }}</span>
        </span>
      </div>
    </div>
  </section>
</template>
