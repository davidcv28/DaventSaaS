<script setup>
// Catálogo de MODERNIMPACT: la lógica de filtros/orden/búsqueda/paginado es
// la de Raíz (useStoreCatalog), re-skineada. La hoja de Raíz está scopeada a
// [data-template='raiz'], así que el lienzo se monta en un subárbol Raíz
// (`.mi-skin`) y store-impacto.css aplica la capa de tokens de la revista
// (retícula con reglas, fichas 3/4, precios y contadores en mono).
import '../../../assets/store-raiz.css'
import RaizCatalogo from '../raiz/CatalogoView.vue'
</script>

<template>
  <div class="store-page mi-skin" data-template="raiz">
    <RaizCatalogo />
  </div>
</template>
