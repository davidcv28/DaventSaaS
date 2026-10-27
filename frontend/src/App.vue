<script setup>
// Shell raíz: solo layout + RouterView (FRONTEND_RULES §1). Sin fetch aquí.
// SupportBot decide solo si mostrarse según la ruta (solo páginas de auth:
// en el panel el asistente es un contacto del chat de soporte).
import SupportBot from './components/SupportBot.vue'
</script>

<template>
  <RouterView />
  <SupportBot />
</template>
