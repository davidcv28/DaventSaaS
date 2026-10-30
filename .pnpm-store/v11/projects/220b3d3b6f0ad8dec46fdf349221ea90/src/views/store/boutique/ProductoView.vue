<script setup>
// Ficha de producto de BOUTIQUE: misma estructura marketplace que Raíz
// (galería + panel de compra, CTA de WhatsApp, especificaciones, relacionados y
// reseñas); sólo cambia la piel. Ver en CatalogoView.vue el criterio de reuso
// del subárbol Raíz + capa de tokens de boutique. La hoja de Raíz viaja como
// CSS compartido de las tres superficies (ver CatalogoView.vue).
import '../../../assets/store-raiz.css'
import RaizProducto from '../raiz/ProductoView.vue'
</script>

<template>
  <div class="store-page bq-skin bq-product" data-template="raiz">
    <RaizProducto />
  </div>
</template>
