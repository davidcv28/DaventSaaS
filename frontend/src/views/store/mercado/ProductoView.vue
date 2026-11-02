<script setup>
// Ficha de producto de MERCADO: misma estructura marketplace que Raíz
// (galería + panel de compra, CTA de WhatsApp, especificaciones, relacionados
// y reseñas); sólo cambia la piel. Ver CatalogoView.vue.
import '../../../assets/store-raiz.css'
import RaizProducto from '../raiz/ProductoView.vue'
</script>

<template>
  <div class="store-page mc-skin mc-product" data-template="raiz">
    <RaizProducto />
  </div>
</template>
