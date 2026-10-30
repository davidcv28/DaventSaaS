<script setup>
// Marcas (§6.5-12): fila hairline con las marcas reales del catálogo en gris
// tipográfico; el color (acento corregido como texto) aparece al hover/foco.
import { computed } from 'vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'
import { useRhLinks } from './rhLinks.js'

const props = defineProps({ block: { type: Object, default: null } })

const { ctx, catalogTo } = useRhLinks()
const { custom, showCatalog } = ctx
const { featured } = useFeaturedCatalog()

const brands = computed(() => featured.value.brands.filter((b) => b.name).slice(0, 12))
const show = computed(() => showCatalog.value && custom.value.show_brands !== false && brands.value.length > 0)
const title = computed(() => props.block?.props?.title?.trim() || 'Con las que trabajamos')
</script>

<template>
  <section v-if="show" class="rz-section rh-numbered rh-brands" aria-labelledby="rh-brands-title">
    <div class="rh-wrap">
      <header class="rh-head rh-head--compact">
        <div class="rh-head-main">
          <p v-reveal class="rz-eyebrow">
            <span class="rz-eyebrow-num rh-secnum" aria-hidden="true"></span>
            Marcas
          </p>
          <h2 id="rh-brands-title" v-reveal class="rh-brands-title">{{ title }}</h2>
        </div>
        <RouterLink v-reveal="60" class="rh-link" :to="catalogTo">Ver catálogo</RouterLink>
      </header>

      <ul class="rh-brands-row">
        <li v-for="(b, i) in brands" :key="b.id || i" v-reveal="60 * (i % 4)" class="rh-brand">
          <RouterLink class="rh-brand-link" :to="catalogTo">{{ b.name }}</RouterLink>
        </li>
      </ul>
    </div>
  </section>
</template>
