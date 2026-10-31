<script setup>
// Servicios de MERCADO: misma estructura funcional que Raíz (hero, cinta,
// picker con presupuesto, pasos, zona/horarios y FAQ); sólo cambia la piel.
// Ver CatalogoView.vue.
import '../../../assets/store-raiz.css'
import RaizServicios from '../raiz/ServiciosView.vue'
</script>

<template>
  <div class="store-page mc-skin mc-services" data-template="raiz">
    <RaizServicios />
  </div>
</template>
