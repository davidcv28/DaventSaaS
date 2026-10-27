<script setup>
// Bloque 'services' (Qué ofrecemos): tarjetas de servicios/ventajas con
// ícono. Se apaga con show_services y además se oculta solo si quedó sin
// contenido. props.title pisa el título de la sección.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { SERVICE_ICONS } from '../../../api/stores.api.js'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom } = ctx
const servicesPage = ctx.showServices

const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const services = computed(() => (Array.isArray(custom.value.services) ? custom.value.services : []))
const show = computed(() => custom.value.show_services !== false && services.value.length > 0)
const servicesTitle = computed(() => props.block?.props?.title?.trim() || custom.value.services_title?.trim() || 'Qué ofrecemos')
const serviceIcon = (key) => (SERVICE_ICONS[key] ? key : 'package')
// El eyebrow repite el título cuando el dueño dejó el texto por defecto:
// en ese caso no se muestra.
const eyebrowUnless = (label, title) => (String(title || '').trim().toLowerCase() === label.toLowerCase() ? '' : label)
const servicesEyebrow = computed(() => eyebrowUnless('Servicios', servicesTitle.value))
</script>

<template>
  <section v-if="show" class="sp-services" aria-labelledby="sp-services-title">
    <div class="sp-container">
      <p v-if="servicesEyebrow" class="sp-eyebrow">{{ servicesEyebrow }}</p>
      <h2 id="sp-services-title" v-reveal class="sp-section-title">{{ servicesTitle }}</h2>
      <div class="sp-services-grid">
        <article v-for="(s, i) in services" :key="i" v-reveal="(i % 3) * 80" class="sp-service">
          <div class="sp-service-ring">
            <span class="sp-service-glow" aria-hidden="true"></span>
            <span class="sp-service-icon" aria-hidden="true"><AppIcon :name="serviceIcon(s.icon)" :size="20" /></span>
          </div>
          <strong class="sp-service-title">{{ s.title }}</strong>
          <p v-if="s.text" class="sp-service-text">{{ s.text }}</p>
          <span class="sp-service-line" aria-hidden="true"></span>
        </article>
      </div>
      <div v-if="servicesPage" class="sp-more">
        <RouterLink class="sp-btn" :to="servicesTo">Ver precios y pedir por WhatsApp <AppIcon name="arrow-right" :size="16" class="sp-arrow" /></RouterLink>
      </div>
    </div>
  </section>
</template>
