<script setup>
// Banda roja de servicios ("Qué ofrecemos"): el acento del dueño pinta la
// banda completa y a la derecha van las tarjetas 2×2 con borde izquierdo
// amarillo. Consume los servicios reales cargados en "Mi empresa" y se
// auto-oculta si el dueño los apagó o no cargó ninguno. El CTA entra al
// embudo de Servicios (presupuesto por WhatsApp) o a WhatsApp directo.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom } = ctx
const servicesPage = ctx.showServices

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const services = computed(() => (Array.isArray(custom.value.services) ? custom.value.services : []))
const show = computed(() => custom.value.show_services !== false && services.value.length > 0)
const items = computed(() => services.value.slice(0, 4))
const title = computed(() => props.block?.props?.title?.trim()
  || custom.value.services_title?.trim()
  || 'Recarga, control y mantenimiento')
// Bajada: la misión/descripción del negocio si existe, en una línea.
const lead = computed(() => custom.value.about_mission?.trim() || custom.value.about_text?.trim() || '')
const whatsappUrl = computed(() => (custom.value.whatsapp ? `https://wa.me/${custom.value.whatsapp.replace(/\D/g, '')}` : ''))
</script>

<template>
  <section v-if="show" class="sg-services" aria-labelledby="sg-services-title">
    <div class="sg-wrap sg-services-grid">
      <div class="sg-services-copy">
        <p v-reveal class="sg-eyebrow sg-eyebrow--light">Qué ofrecemos</p>
        <h2 id="sg-services-title" v-reveal="60" class="sg-sec-title">{{ title }}</h2>
        <p v-if="lead" v-reveal="120" class="sg-services-lead">{{ lead }}</p>
        <RouterLink v-if="servicesPage" v-reveal="170" class="sg-btn sg-btn--yellow" :to="servicesTo">
          Pedir presupuesto <AppIcon name="arrow-right" :size="17" aria-hidden="true" />
        </RouterLink>
        <a v-else-if="whatsappUrl" v-reveal="170" class="sg-btn sg-btn--yellow" :href="whatsappUrl" target="_blank" rel="noopener">
          <AppIcon name="whatsapp" :size="17" aria-hidden="true" /> Pedir presupuesto
        </a>
        <RouterLink v-else-if="showCatalog" v-reveal="170" class="sg-btn sg-btn--yellow" :to="catalogTo">
          Ver catálogo <AppIcon name="arrow-right" :size="17" aria-hidden="true" />
        </RouterLink>
      </div>
      <ul class="sg-services-cards">
        <li v-for="(s, i) in items" :key="`${i}-${s.title}`" v-reveal="(i % 2) * 80" class="sg-service">
          <strong class="sg-service-title">{{ s.title }}</strong>
          <span v-if="s.text" class="sg-service-text">{{ s.text }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
