<script setup>
// Ficha de producto de TRAMA. La estructura marketplace (galería + panel de
// compra, CTA de WhatsApp, specs, relacionados y reseñas) es la MISMA que la
// de Raíz y se reutiliza tal cual: la spec §7.3 pide re-skinear, no rehacer
// la lógica. La piel llega por store-trama.css a través de `.tr-product`
// (radios 0, Anton en titulares, botones rectangulares y borde negro).
import RaizProducto from '../raiz/ProductoView.vue'
</script>

<template>
  <RaizProducto class="tr-product" />
</template>
