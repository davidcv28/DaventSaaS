<script setup>
// Bloque 'services' de MOVIMIENTO: servicios como LISTA EDITORIAL
// NUMERADA (no cards genéricas) — cada fila con índice 01, nombre
// condensado grande, bajada y flecha hacia la página de servicios.
// Se apaga con show_services y sin ítems no se pinta.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { SERVICE_ICONS } from '../../../api/stores.api.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'

const props = defineProps({
  block: { type: Object, default: null },
  sectionIndex: { type: Number, default: 0 }
})

const ctx = inject('storePage')
const { slug, custom } = ctx
const servicesPage = ctx.showServices

const servicesTo = computed(() => ({ name: 'store-services', params: storeHostSlug ? {} : { slug: slug.value } }))
const services = computed(() => (Array.isArray(custom.value.services) ? custom.value.services : [])
  .filter((s) => String(s?.title || s?.name || '').trim()))
const show = computed(() => custom.value.show_services !== false && services.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || custom.value.services_title?.trim() || 'Qué entrenás')
const serviceIcon = (key) => (SERVICE_ICONS[key] ? key : 'zap')
</script>

<template>
  <section v-if="show" class="mv-services" aria-labelledby="mv-services-title">
    <div class="mv-wrap">
      <header v-reveal class="mv-services-head">
        <p class="mv-eyebrow"><span class="mv-eyebrow-idx">{{ String(sectionIndex || 1).padStart(2, '0') }}</span> Disciplinas</p>
        <h2 id="mv-services-title">{{ title }}</h2>
      </header>
      <ol class="mv-services-list">
        <li v-for="(s, i) in services" :key="i" v-reveal="i * 60" class="mv-svc-row">
          <span class="mv-svc-idx" aria-hidden="true">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="mv-svc-icon" aria-hidden="true"><AppIcon :name="serviceIcon(s.icon)" :size="20" /></span>
          <div class="mv-svc-body">
            <strong class="mv-svc-name">{{ s.title || s.name }}</strong>
            <p v-if="s.text" class="mv-svc-text">{{ s.text }}</p>
          </div>
          <RouterLink v-if="servicesPage" class="mv-svc-go" :to="servicesTo" :aria-label="`Ver ${s.title || s.name}`">
            <AppIcon name="arrow-up-right" :size="20" aria-hidden="true" />
          </RouterLink>
        </li>
      </ol>
      <div v-if="servicesPage" class="mv-services-more">
        <RouterLink class="mv-btn mv-btn--ghost" :to="servicesTo">
          Ver precios y horarios <AppIcon name="arrow-right" :size="16" aria-hidden="true" />
        </RouterLink>
      </div>
    </div>
  </section>
</template>
