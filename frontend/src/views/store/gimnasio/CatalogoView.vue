<script setup>
// Catálogo de GIMNASIO: la lógica de filtros/orden/búsqueda/paginado es la
// de Raíz (useStoreCatalog), re-skineada. La hoja de Raíz está scopeada a
// [data-template='raiz'], así que el lienzo se monta en un subárbol Raíz
// (`.gy-skin`) y store-gimnasio.css aplica la capa oscura del gimnasio.
import { ref } from 'vue'
import '../../../assets/store-raiz.css'
import RaizCatalogo from '../raiz/CatalogoView.vue'

const pageEl = ref(null)
</script>

<template>
  <div ref="pageEl" class="store-page gy-skin" data-template="raiz">
    <RaizCatalogo />
  </div>
</template>
