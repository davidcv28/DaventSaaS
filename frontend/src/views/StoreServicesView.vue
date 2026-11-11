<script setup>
// Página "Servicios" de la web pública: el diseño activo (pageTemplate)
// resuelve su propia vista de servicios desde su Template Definition; todas
// consumen el contexto `storePage` y el payload público de la tienda.
// Si la página no está habilitada para la tienda (site_templates) o el
// diseño no tiene superficie, se muestra un aviso explícito en vez de una
// hoja vacía o un redirect silencioso al inicio.
import { computed, inject } from 'vue'
import { RouterLink } from 'vue-router'
import AppIcon from '../components/AppIcon.vue'
import { surfaceComponent } from '../templates/index.js'
import { storeHostSlug } from '../config/env.js'

const ctx = inject('storePage')
const component = computed(() => surfaceComponent(ctx?.pageTemplate?.value, 'services'))
const unavailable = computed(() => !ctx?.showServices?.value || !component.value)
const homeTo = computed(() => ({ path: storeHostSlug ? '/' : `/${ctx?.slug?.value || ''}` }))
</script>

<template>
  <div v-if="unavailable" class="sp-state sp-state-page">
    <span class="sp-state-icon"><AppIcon name="wrench" :size="26" /></span>
    <h1>Servicios no disponibles</h1>
    <p>Esta tienda no tiene una página de servicios por ahora.</p>
    <RouterLink :to="homeTo" class="sp-btn">Volver al inicio</RouterLink>
  </div>
  <component :is="component" v-else />
</template>
