<script setup>
// Servicios (§6.5-8): lista numerada de filas (01…) con regla y flecha, no
// grilla de tarjetas con icono. Reusa las filas {icon,title,text} de "Qué
// ofrecemos" y manda al embudo de presupuesto cuando la página existe.
import { computed } from 'vue'
import { SERVICE_ICONS } from '../../../../api/stores.api.js'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx, servicesTo } = useRhLinks()
const { custom } = ctx
const servicesPage = ctx.showServices

const services = computed(() => (Array.isArray(custom.value.services) ? custom.value.services : []))
const show = computed(() => custom.value.show_services !== false && services.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || custom.value.services_title?.trim() || 'Qué ofrecemos')
const serviceIcon = (key) => (SERVICE_ICONS[key] ? key : 'package')
const pad = (n) => String(n).padStart(2, '0')
</script>

<template>
  <section v-if="show" class="rz-section rh-numbered rh-services" aria-labelledby="rh-services-title">
    <div class="rh-wrap">
      <header class="rh-head">
        <div class="rh-head-main">
          <p v-reveal class="rz-eyebrow">
            <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
            Servicios
          </p>
          <h2 id="rh-services-title" v-reveal class="rh-title">{{ title }}</h2>
        </div>
        <RouterLink v-if="servicesPage" v-reveal="60" class="rh-link" :to="servicesTo">
          Pedir presupuesto <AppIcon name="arrow-right" :size="15" />
        </RouterLink>
      </header>

      <ol class="rh-services-list">
        <li v-for="(s, i) in services" :key="i" v-reveal="60 * i" class="rh-service-row">
          <component
            :is="servicesPage ? 'RouterLink' : 'div'" class="rh-service-link"
            :to="servicesPage ? servicesTo : null"
          >
            <span class="rh-service-num" aria-hidden="true">{{ pad(i + 1) }}</span>
            <span class="rh-service-icon" aria-hidden="true"><AppIcon :name="serviceIcon(s.icon)" :size="18" /></span>
            <strong class="rh-service-title">{{ s.title }}</strong>
            <span class="rh-service-text">{{ s.text }}</span>
            <span class="rh-service-arrow" aria-hidden="true"><AppIcon name="arrow-right" :size="18" /></span>
          </component>
        </li>
      </ol>
    </div>
  </section>
</template>
