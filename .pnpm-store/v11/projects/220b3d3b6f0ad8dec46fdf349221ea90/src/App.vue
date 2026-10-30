<script setup>
// Shell raíz: solo layout + RouterView (FRONTEND_RULES §1). Sin fetch aquí.
// SupportBot decide solo si mostrarse según la ruta (solo páginas de auth:
// en el panel el asistente es un contacto del chat de soporte).
// AppUpdateBanner renderiza solo en nativo cuando la APK publicada es más
// nueva (o el server marca min_supported por encima de lo instalado).
import SupportBot from './components/SupportBot.vue'
import AppUpdateBanner from './components/AppUpdateBanner.vue'
</script>

<template>
  <RouterView />
  <SupportBot />
  <AppUpdateBanner />
</template>
