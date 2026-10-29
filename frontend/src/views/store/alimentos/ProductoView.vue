<script setup>
// Ficha de producto del diseño ALIMENTOS.
// La estructura marketplace (galería + panel de compra, CTA de WhatsApp, ficha
// técnica, opiniones y relacionados) es la de Raíz y se reutiliza tal cual.
// La hoja de Raíz está scopeada a [data-template='raiz'], así que el lienzo de
// la vista se monta en un subárbol `.store-page.al-skin[data-template='raiz']`
// y arriba se aplica la capa de tokens de alimentos (store-alimentos.css).
// Mismo patrón de "puente" que boutique: la hoja de Raíz viaja como CSS
// compartido de las tres superficies (catálogo, ficha y servicios).
import '../../../assets/store-raiz.css'
import RaizProducto from '../raiz/ProductoView.vue'
</script>

<template>
  <div class="store-page al-skin al-product" data-template="raiz">
    <RaizProducto />
  </div>
</template>
