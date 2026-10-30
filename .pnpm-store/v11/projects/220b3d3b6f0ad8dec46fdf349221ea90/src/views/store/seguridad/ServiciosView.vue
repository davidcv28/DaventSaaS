<script setup>
// Servicios del diseño SEGURIDAD. Misma estructura de embudo que Raíz v2
// (hero, cinta, selector con presupuesto, pasos, zona/horarios y FAQ); sólo
// cambia la piel. Se reutiliza la vista funcional dentro de un subárbol
// `.store-page[data-template='raiz']` (`.sg-skin`) con la capa de tokens de
// seguridad encima (store-seguridad.css). Mismo patrón que boutique.
import '../../../assets/store-raiz.css'
import RaizServicios from '../raiz/ServiciosView.vue'
</script>

<template>
  <div class="store-page sg-skin sg-services" data-template="raiz">
    <RaizServicios />
  </div>
</template>
