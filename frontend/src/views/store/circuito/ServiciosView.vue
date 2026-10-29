<script setup>
// Servicios del diseño CIRCUITO.
// La estructura del embudo (hero, cinta, picker, presupuesto por WhatsApp,
// pasos, garantías, trabajos, zona/horarios, FAQ, barra fija móvil) es UNA sola
// implementación compartida: store/raiz/ServiciosView.vue. El layout base de
// esas clases (.rz-sv-*) vive en assets/store-services-base.css (importada por
// StorePublicLayout para todos los diseños); este archivo monta la vista y
// store-circuito-services.css la re-piela con los tokens --ci-* dentro de
// .ci-services-page. No se duplica lógica ni se tocan estados/aria.
import RaizServicios from '../raiz/ServiciosView.vue'
</script>

<template>
  <div class="ci-services-page">
    <!-- Arte decorativo del diseño (grilla técnica + línea de barrido). Es
         puramente presentacional: aria-hidden y sin capturar punteros. -->
    <div class="ci-svc-deco" aria-hidden="true">
      <span class="ci-svc-deco-grid"></span>
      <span class="ci-svc-deco-glow"></span>
      <span class="ci-svc-deco-scan"></span>
    </div>
    <RaizServicios />
  </div>
</template>
