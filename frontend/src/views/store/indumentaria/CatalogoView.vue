<script setup>
// Catálogo de INDUMENTARIA: la lógica de filtros/orden/búsqueda/paginado
// es la de Raíz (useStoreCatalog), re-skineada. La hoja de Raíz está
// scopeada a [data-template='raiz'], así que el lienzo se monta en un
// subárbol Raíz (`.in-skin`) y store-indumentaria.css aplica la capa de
// tokens del lookbook (cards 3/4, precios mono, badges etiqueta).
import '../../../assets/store-raiz.css'
import RaizCatalogo from '../raiz/CatalogoView.vue'
</script>

<template>
  <div class="store-page in-skin" data-template="raiz">
    <RaizCatalogo />
  </div>
</template>
