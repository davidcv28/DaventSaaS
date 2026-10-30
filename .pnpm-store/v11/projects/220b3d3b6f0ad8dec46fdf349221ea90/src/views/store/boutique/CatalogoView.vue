<script setup>
// Catálogo de BOUTIQUE. La lógica de filtros/orden/búsqueda/paginado y la
// estructura editorial son las de Raíz v2: se reutiliza la vista tal cual y la
// piel de boutique entra por CSS.
//
// Reuso de piel: la hoja de Raíz está scopeada a [data-template='raiz'], así
// que el lienzo de la vista se monta en un subárbol `.store-page[data-template='raiz']`
// (`.bq-skin`) y arriba se aplica la capa de tokens/componentes de boutique
// (store-boutique.css). Es el mismo patrón de "puente" que usan los diseños
// para re-skinear el chrome sin reescribir la lógica de las superficies.
// La hoja de Raíz se importa acá (y en Producto/Servicios) para que Vite la
// emita como CSS compartido de estas tres superficies: no se carga en el
// inicio, solo al entrar al catálogo / ficha / servicios.
import { ref } from 'vue'
import '../../../assets/store-raiz.css'
import RaizCatalogo from '../raiz/CatalogoView.vue'
import { useCardTitles } from './useCardTitles.js'

// Nombres largos: el recorte visual lo da el CSS (line-clamp 2) y acá se
// agrega el `title` con el nombre completo a cada tarjeta.
const pageEl = ref(null)
useCardTitles(pageEl)
</script>

<template>
  <div ref="pageEl" class="store-page bq-skin bq-catalog" data-template="raiz">
    <RaizCatalogo />
  </div>
</template>
