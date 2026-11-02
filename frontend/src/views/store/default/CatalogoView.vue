<script setup>
// Catálogo de DEFAULT. La lógica de filtros/orden/búsqueda/paginado y la
// estructura son las de Raíz: se reutiliza la vista tal cual y la piel de
// default entra por CSS. Mismo patrón de "puente" que atelier/nexo: el
// lienzo se monta en un subárbol `.store-page[data-template='raiz']`
// (`.df-skin`) y store-default.css re-escribe los tokens --sp-* encima.
import '../../../assets/store-raiz.css'
import RaizCatalogo from '../raiz/CatalogoView.vue'
</script>

<template>
  <div class="store-page df-skin df-catalog" data-template="raiz">
    <RaizCatalogo />
  </div>
</template>
