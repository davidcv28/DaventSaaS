<script setup>
import { useStoreCatalog } from '../../composables/useStoreCatalog.js'
import '../../assets/store-facets.css'

// Panel de filtros avanzados compartido por todas las plantillas del
// catálogo público: banderas rápidas (oferta/novedades con sus conteos) y
// un grupo por atributo dinámico del catálogo (Talle, Color, Material...)
// multi-selección. Consume la misma instancia de useStoreCatalog que crea
// la página — solo aporta la presentación neutra (store-facets.css).
const {
  catalog, facets, pickFeature, isFeatureOn,
  onlyOffer, onlyNew, toggleOffer, toggleNew, offerTotal, newTotal
} = useStoreCatalog()

const isOn = isFeatureOn
</script>

<template>
<div v-if="offerTotal || newTotal || facets.length" class="cf-facets" role="group" aria-label="Filtros por atributo">
  <div v-if="offerTotal || newTotal" class="cf-fset">
    <p class="cf-fset-name">Estado</p>
    <button v-if="offerTotal" type="button" class="cf-opt" :class="{ on: onlyOffer }" :aria-pressed="onlyOffer" @click="toggleOffer">
      <span>En oferta</span><span class="cf-n" aria-hidden="true">{{ offerTotal }}</span>
    </button>
    <button v-if="newTotal" type="button" class="cf-opt" :class="{ on: onlyNew }" :aria-pressed="onlyNew" @click="toggleNew">
      <span>Novedades</span><span class="cf-n" aria-hidden="true">{{ newTotal }}</span>
    </button>
  </div>
  <div v-for="facet in facets" :key="facet.name" class="cf-fset">
    <p class="cf-fset-name">{{ facet.name }}</p>
    <button
      v-for="opt in facet.values" :key="opt.value" type="button"
      class="cf-opt" :class="{ on: isOn(facet.name, opt.value) }"
      :aria-pressed="isOn(facet.name, opt.value)"
      @click="pickFeature(facet.name, opt.value)"
    ><span>{{ opt.value }}</span><span class="cf-n" aria-hidden="true">{{ opt.count }}</span></button>
  </div>
</div>
</template>
