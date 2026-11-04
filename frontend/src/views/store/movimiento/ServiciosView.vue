<script setup>
// Servicios de MOVIMIENTO: mismo embudo funcional que Raíz (selector,
// presupuesto, pasos y formulario), re-skineado a la lista editorial del
// estudio (filas numeradas por CSS sobre .mv-skin).
import '../../../assets/store-raiz.css'
import RaizServicios from '../raiz/ServiciosView.vue'
</script>

<template>
  <div class="store-page mv-skin" data-template="raiz">
    <RaizServicios />
  </div>
</template>
