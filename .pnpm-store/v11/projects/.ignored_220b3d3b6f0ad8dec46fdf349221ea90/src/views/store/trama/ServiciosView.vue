<script setup>
// Servicios de TRAMA. La spec §7.4 pide la MISMA estructura que la referencia
// (hero + cinta + picker con presupuesto + pasos + garantías + zona/horarios +
// FAQ) y solo cambiar la piel: se reutiliza la vista funcional compartida y la
// piel entra por store-trama.css sobre `.tr-services` (sin radios, mayúsculas,
// acento de la marca y tipografía Anton/Archivo).
import RaizServicios from '../raiz/ServiciosView.vue'
</script>

<template>
  <RaizServicios class="tr-services" />
</template>
