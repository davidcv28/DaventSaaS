<script setup>
import { computed } from 'vue'
import BrandLogo from './BrandLogo.vue'
import { useAuthStore } from '../stores/auth.store.js'

defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' }
})

const auth = useAuthStore()
const homeRoute = computed(() => (auth.isAuthenticated ? '/dashboard' : '/login'))
const homeLabel = computed(() => (auth.isAuthenticated ? 'Volver al panel' : 'Volver al inicio de sesión'))
</script>

<template>
  <div class="legal-shell">
    <header class="legal-top">
      <RouterLink :to="homeRoute" class="legal-brand" aria-label="Ir a DAVENT">
        <BrandLogo :size="30" /> <span>DAVENT</span>
      </RouterLink>
      <nav class="legal-nav" aria-label="Enlaces legales">
        <RouterLink to="/terminos">Términos y condiciones</RouterLink>
        <RouterLink to="/denuncias">Denunciar contenido</RouterLink>
      </nav>
    </header>
    <main class="legal-main">
      <div class="legal-head">
        <h1>{{ title }}</h1>
        <p v-if="subtitle">{{ subtitle }}</p>
      </div>
      <slot />
      <div class="legal-foot">
        <RouterLink :to="homeRoute">{{ homeLabel }}</RouterLink>
      </div>
    </main>
  </div>
</template>
