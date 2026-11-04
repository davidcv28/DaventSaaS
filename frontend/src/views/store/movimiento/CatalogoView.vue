<script setup>
// Catálogo de MOVIMIENTO: la lógica de filtros/orden/búsqueda/paginado es
// la de Raíz (useStoreCatalog), re-skineada editorial. La hoja de Raíz
// está scopeada a [data-template='raiz'], así que el lienzo se monta en
// un subárbol Raíz (`.mv-skin`) y store-movimiento.css aplica la capa
// papel+tinta+acento del estudio.
import { ref } from 'vue'
import '../../../assets/store-raiz.css'
import RaizCatalogo from '../raiz/CatalogoView.vue'

const pageEl = ref(null)
</script>

<template>
  <div ref="pageEl" class="store-page mv-skin" data-template="raiz">
    <RaizCatalogo />
  </div>
</template>
