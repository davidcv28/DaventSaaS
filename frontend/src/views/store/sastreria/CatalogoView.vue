<script setup>
// Catálogo de SASTRERÍA: la lógica de filtros/orden/búsqueda/paginado es la
// de Raíz (useStoreCatalog), re-skineada. La hoja de Raíz está scopeada a
// [data-template='raiz'], así que el lienzo se monta en un subárbol Raíz
// (`.ss-skin`) y store-sastreria.css aplica la capa de tokens del atelier.
import { ref } from 'vue'
import '../../../assets/store-raiz.css'
import RaizCatalogo from '../raiz/CatalogoView.vue'

const pageEl = ref(null)
</script>

<template>
  <div ref="pageEl" class="store-page ss-skin" data-template="raiz">
    <RaizCatalogo />
  </div>
</template>
