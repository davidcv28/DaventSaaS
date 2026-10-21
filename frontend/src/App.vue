<script setup>
// Shell raíz: solo layout + RouterView (FRONTEND_RULES §1). Sin fetch aquí.
// SupportBot decide solo si mostrarse según la ruta (públicas vs panel).
import SupportBot from './components/SupportBot.vue'
</script>

<template>
  <RouterView />
  <SupportBot />
</template>
