<script setup>
// Servicios de CLÁSICO. Se reutiliza la vista funcional compartida de Raíz
// (hero + cinta + picker con presupuesto + pasos + garantías + zona/horarios +
// FAQ) y solo se re-skinea: la piel entra por store-clasico.css sobre
// `.cl-services` (marfil, serif, reglas de 1 px, acento del dueño). No se
// rediseña la estructura.
import RaizServicios from '../raiz/ServiciosView.vue'
</script>

<template>
  <RaizServicios class="cl-services" />
</template>
