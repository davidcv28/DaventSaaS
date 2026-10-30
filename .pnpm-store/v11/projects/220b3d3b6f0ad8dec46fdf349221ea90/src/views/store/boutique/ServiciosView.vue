<script setup>
// Servicios de BOUTIQUE: misma estructura funcional que Raíz (hero, cinta,
// picker con presupuesto, pasos, zona/horarios y FAQ); sólo cambia la piel.
// Ver en CatalogoView.vue el criterio de reuso del subárbol Raíz + capa de
// tokens de boutique. La hoja de Raíz viaja como CSS compartido de las tres
// superficies.
import '../../../assets/store-raiz.css'
import RaizServicios from '../raiz/ServiciosView.vue'
</script>

<template>
  <div class="store-page bq-skin bq-services" data-template="raiz">
    <RaizServicios />
  </div>
</template>
