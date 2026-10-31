<script setup>
// Catálogo de MERCADO. Reutiliza la lógica de Raíz (filtros, orden, búsqueda,
// paginado) y la re-skinea por CSS: el lienzo se monta en un subárbol
// `.store-page[data-template='raiz']` (.mc-skin) y arriba corre la capa de
// tokens de mercado. La hoja de Raíz viaja como CSS compartido de catálogo,
// ficha y servicios.
import { ref } from 'vue'
import '../../../assets/store-raiz.css'
import RaizCatalogo from '../raiz/CatalogoView.vue'
import { useCardTitles } from './useCardTitles.js'

const pageEl = ref(null)
useCardTitles(pageEl)
</script>

<template>
  <div ref="pageEl" class="store-page mc-skin mc-catalog" data-template="raiz">
    <RaizCatalogo />
  </div>
</template>
