<script setup>
// Servicios del diseño CIRCUITO.
// La spec (§7.4) define UNA sola estructura de embudo para los tres diseños
// —hero, cinta, selector de servicios, presupuesto por WhatsApp, pasos,
// garantías, trabajos, zona/horarios, FAQ— y ordena que el diseño cambie solo
// la piel. El embudo (lógica de selección, total animado, mensaje de WhatsApp,
// guards de la página) vive en una sola implementación; acá se monta y
// store-circuito.css la re-piela con los tokens del diseño (.sv-* → --ci-*).
import RaizServicios from '../raiz/ServiciosView.vue'
</script>

<template>
  <div class="ci-services-page">
    <RaizServicios />
  </div>
</template>
