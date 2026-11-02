<script setup>
// Ficha de producto de DEFAULT: misma estructura que Raíz (galería + panel de
// compra, CTA de WhatsApp, especificaciones, relacionados y reseñas); sólo
// cambia la piel. Ver en CatalogoView.vue el criterio de reuso del subárbol
// Raíz + capa de tokens de default.
import '../../../assets/store-raiz.css'
import RaizProducto from '../raiz/ProductoView.vue'
</script>

<template>
  <div class="store-page df-skin df-product" data-template="raiz">
    <RaizProducto />
  </div>
</template>
