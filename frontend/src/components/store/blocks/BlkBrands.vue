<script setup>
// Bloque 'brands': marquesina automática con las marcas reales del
// catálogo. Sin catálogo o sin marcas se auto-oculta. Se apaga con
// show_brands. props.title agrega un encabezado sobre la cinta.
import { computed, inject } from 'vue'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom, showCatalog } = ctx
const { featured: shopCatalog } = useFeaturedCatalog()

const brands = computed(() => shopCatalog.value.brands.filter((b) => b.name).slice(0, 12))
const show = computed(() => custom.value.show_brands !== false && brands.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || 'Marcas con las que trabajamos')
const loop = computed(() => [...brands.value, ...brands.value, ...brands.value])
</script>

<template>
  <section v-if="showCatalog && show" class="sp-brands" aria-label="Marcas">
    <div class="sp-container">
      <h2 v-reveal class="sp-brands-title">{{ title }}</h2>
    </div>
    <div class="sp-ann" role="note">
      <div class="sp-ann-track">
        <span v-for="(b, i) in loop" :key="i" class="sp-ann-item" :aria-hidden="i >= brands.length"><AppIcon name="tag" :size="14" />{{ b.name }}</span>
      </div>
    </div>
  </section>
</template>
