<script setup>
// Ficha de producto de INDUMENTARIA: misma estructura funcional que Raíz
// (galería + panel de compra + WhatsApp + relacionados), sólo cambia la
// piel — la galería sale como pliego de lookbook y el precio en mono.
import '../../../assets/store-raiz.css'
import RaizProducto from '../raiz/ProductoView.vue'
</script>

<template>
  <div class="store-page in-skin" data-template="raiz">
    <RaizProducto />
  </div>
</template>
