<script setup>
// Servicios de DEFAULT: misma estructura funcional que Raíz (hero, cinta,
// picker con presupuesto, pasos, zona/horarios y FAQ); sólo cambia la piel.
// Ver en CatalogoView.vue el criterio de reuso del subárbol Raíz + capa de
// tokens de default.
import '../../../assets/store-raiz.css'
import RaizServicios from '../raiz/ServiciosView.vue'
</script>

<template>
  <div class="store-page df-skin df-services" data-template="raiz">
    <RaizServicios />
  </div>
</template>
