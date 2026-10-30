<script setup>
// Ficha de producto de TRAMA. La estructura marketplace (galería + panel de
// compra, CTA de WhatsApp, specs, relacionados y reseñas) es la MISMA que la
// de Raíz y se reutiliza tal cual: la spec §7.3 pide re-skinear, no rehacer
// la lógica. La piel de catálogo/ficha llega por store-trama-catalog.css y
// scopea las clases compartidas `.rz-pdp-*` / `.spd-*` bajo `.tr-product`.
import RaizProducto from '../raiz/ProductoView.vue'
import '../../../assets/store-trama-catalog.css'
</script>

<template>
  <RaizProducto class="tr-product" />
</template>
