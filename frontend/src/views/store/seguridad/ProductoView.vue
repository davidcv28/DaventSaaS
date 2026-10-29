<script setup>
// Ficha de producto del diseño SEGURIDAD. La estructura marketplace (galería,
// panel de compra, CTA de WhatsApp, especificaciones, reseñas y relacionados)
// es la de Raíz v2 y se reutiliza tal cual. La hoja de Raíz está scopeada a
// [data-template='raiz'], así que se monta dentro de un subárbol
// `.store-page[data-template='raiz']` (`.sg-skin`) y encima se aplica la capa
// de tokens/componentes de seguridad (bloque `.sg-skin` de
// store-seguridad.css). Mismo patrón que boutique.
import '../../../assets/store-raiz.css'
import RaizProducto from '../raiz/ProductoView.vue'
</script>

<template>
  <div class="store-page sg-skin sg-product" data-template="raiz">
    <RaizProducto />
  </div>
</template>
