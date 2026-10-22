<script setup>
// Shell raíz: solo layout + RouterView (FRONTEND_RULES §1). Sin fetch aquí.
// SupportBot decide solo si mostrarse según la ruta (auth/panel, nunca en la web del cliente).
import SupportBot from './components/SupportBot.vue'
</script>

<template>
  <RouterView />
  <SupportBot />
</template>
