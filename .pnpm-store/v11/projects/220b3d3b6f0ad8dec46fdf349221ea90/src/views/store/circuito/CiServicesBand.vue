<script setup>
// Banda de servicios del diseño CIRCUITO: laboratorio técnico. A la izquierda
// el copy de "Qué ofrecemos" con su rail mono; a la derecha, la consola de
// servicios reales con precio orientativo (service_items del payload público).
// Si el dueño todavía no cargó servicios con precio, cae a las filas de
// marketing de `services`. Respeta show_services y se auto-oculta sin contenido.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { SERVICE_ICONS } from '../../../api/stores.api.js'
import { servicePriceLabel } from '../../../api/services.api.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const ctx = inject('storePage')
const { slug, custom, store, status } = ctx
const servicesPage = ctx.showServices

const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const title = computed(() => custom.value.services_title?.trim() || 'Qué ofrecemos')
const eyebrow = computed(() => (title.value.trim().toLowerCase() === 'qué ofrecemos' ? '' : 'Qué ofrecemos'))

// Servicios reales (con precio orientativo) → filas de la derecha.
const priced = computed(() => (status.value === 'success' ? (store.value?.service_items || []) : []))
const rows = computed(() => {
  if (priced.value.length) {
    return priced.value.slice(0, 4).map((it) => ({
      key: it.id,
      icon: SERVICE_ICONS[it.icon] ? it.icon : 'wrench',
      name: it.name,
      price: servicePriceLabel(it)
    }))
  }
  return (Array.isArray(custom.value.services) ? custom.value.services : []).slice(0, 4).map((s, i) => ({
    key: `s${i}`,
    icon: SERVICE_ICONS[s.icon] ? s.icon : 'wrench',
    name: s.title,
    price: ''
  }))
})
const note = computed(() => (priced.value.length ? (custom.value.service_price_note || 'Precios orientativos: el valor final se confirma por WhatsApp.') : ''))
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
const show = computed(() => custom.value.show_services !== false && rows.value.length > 0)
const pad = (n) => String(n + 1).padStart(2, '0')
</script>

<template>
  <section v-if="show" class="ci-services" aria-labelledby="ci-services-title">
    <div class="ci-container ci-services-grid">
      <div class="ci-services-copy">
        <p class="ci-services-rail" aria-hidden="true">
          <span class="ci-hero-status"><span class="ci-pip"></span>Área técnica</span>
          <span class="ci-services-rail-line"></span>
        </p>
        <p v-if="eyebrow" class="ci-label">{{ eyebrow }}</p>
        <h2 id="ci-services-title" v-reveal class="ci-h2">{{ title }}</h2>
        <p v-if="note" class="ci-services-note"><AppIcon name="info" :size="14" aria-hidden="true" /> {{ note }}</p>
        <RouterLink v-if="servicesPage" class="ci-btn" :to="servicesTo">Pedir presupuesto <AppIcon name="arrow-right" :size="16" /></RouterLink>
        <a v-else-if="whatsappUrl" class="ci-btn" :href="whatsappUrl" target="_blank" rel="noopener"><AppIcon name="whatsapp" :size="16" /> Consultar</a>
      </div>

      <div class="ci-services-console">
        <p class="ci-services-console-head" aria-hidden="true">
          <span class="ci-mono">// Listado de servicios</span>
          <span class="ci-services-console-led"></span>
        </p>
        <ul class="ci-services-list">
          <li v-for="(r, i) in rows" :key="r.key" v-reveal="(i % 4) * 60" class="ci-services-item">
            <span class="ci-services-idx" aria-hidden="true">{{ pad(i) }}</span>
            <span class="ci-services-ico" aria-hidden="true"><AppIcon :name="r.icon" :size="16" /></span>
            <strong>{{ r.name }}</strong>
            <span v-if="r.price" class="ci-services-price">{{ r.price }}</span>
            <span v-else class="ci-services-price is-quote">a cotizar</span>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>
