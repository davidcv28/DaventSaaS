<script setup>
// Ficha de producto de ModernTec: misma estructura que Raíz (galería +
// panel de compra, CTA, especificaciones y relacionados), re-skineada en un
// subárbol Raíz. Ver CatalogoView.vue.
import '../../../assets/store-raiz.css'
import RaizProducto from '../raiz/ProductoView.vue'
</script>

<template>
  <div class="store-page mt-skin" data-template="raiz">
    <RaizProducto />
  </div>
</template>
