<script setup>
// Ficha de producto de CLÁSICO. La estructura marketplace (galería + panel de
// compra, CTA de WhatsApp, specs, relacionados y reseñas) es la MISMA que la
// de Raíz y se reutiliza tal cual: acá solo se re-skinea. La piel llega por
// store-clasico-catalog.css y scopea las clases compartidas `.rz-pdp-*` /
// `.spd-*` bajo `.cl-product`.
import RaizProducto from '../raiz/ProductoView.vue'
import '../../../assets/store-clasico-catalog.css'
</script>

<template>
  <RaizProducto class="cl-product" />
</template>
