<script setup>
// Página "Suscripciones" de la web pública (site_templates 'plans'): un
// diseño puede declarar su propia vista en surfaces.plans; el resto cae a
// la vista genérica compartida (PlanesView), esquinada por los tokens de
// la piel activa. Consume el contexto `storePage` del layout público.
// Si la página no está habilitada para la tienda se muestra un aviso
// explícito en vez de caer en silencio al inicio.
import { computed, inject } from 'vue'
import { RouterLink } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { surfaceComponent } from '../templates/index.js'
import { storeHostSlug } from '../config/env.js'
import PlanesView from './store/PlanesView.vue'

const ctx = inject('storePage')
const component = computed(() => surfaceComponent(ctx?.pageTemplate?.value, 'plans') || PlanesView)
const unavailable = computed(() => !ctx?.showPlans?.value)
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${ctx?.slug?.value || ''}` }))
</script>

<template>
  <div v-if="unavailable" class="sp-state sp-state-page">
    <span class="sp-state-icon"><AppIcon name="crown" :size="26" /></span>
    <h1>Suscripciones no disponibles</h1>
    <p>Esta tienda no tiene una página de suscripciones por ahora.</p>
    <RouterLink :to="homeTo" class="sp-btn">Volver al inicio</RouterLink>
  </div>
  <component :is="component" v-else />
</template>
