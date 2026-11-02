<script setup>
// Catálogo de NEXO. La lógica de filtros/orden/búsqueda/paginado y la
// estructura son las de Raíz: se reutiliza la vista tal cual y la piel de
// nexo entra por CSS. Mismo patrón de "puente" que atelier/sastreria: el
// lienzo se monta en un subárbol `.store-page[data-template='raiz']`
// (`.nx-skin`) y store-nexo.css re-escribe los tokens --sp-* encima.
// La hoja de Raíz viaja como CSS compartido de las tres superficies.
import '../../../assets/store-raiz.css'
import RaizCatalogo from '../raiz/CatalogoView.vue'
</script>

<template>
  <div class="store-page nx-skin nx-catalog" data-template="raiz">
    <RaizCatalogo />
  </div>
</template>
