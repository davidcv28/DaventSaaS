<script setup>
// Servicios del diseño ALIMENTOS.
// El embudo (hero, cinta, selector de servicios, presupuesto por WhatsApp,
// pasos, garantías, zona/horarios y FAQ) es la implementación compartida de
// Raíz; acá se monta en un subárbol `.store-page.al-skin[data-template='raiz']`
// y store-alimentos.css remapea los tokens de Raíz a la piel crema/acento del
// diseño (radios 12–20, DM Serif en titulares, botones pill).
import '../../../assets/store-raiz.css'
import RaizServicios from '../raiz/ServiciosView.vue'
</script>

<template>
  <div class="store-page al-skin al-services" data-template="raiz">
    <RaizServicios />
  </div>
</template>
