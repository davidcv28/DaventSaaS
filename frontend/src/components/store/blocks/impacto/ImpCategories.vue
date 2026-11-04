<script setup>
// Bloque 'categories' de MODERNIMPACT: el índice de colección. Cada
// departamento es una celda de la retícula con su número, su foto (o la
// trama de rayado) y el conteo en mono; al hover la celda invierte a tinta.
// En móvil la retícula pasa a una columna con medios 16/11.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../../config/env.js'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const { slug, showCatalog } = inject('storePage')
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const deptTo = (id) => ({ ...catalogTo.value, query: { category: id } })
const title = computed(() => props.block?.props?.title?.trim() || 'Índice de colección')

const depts = computed(() => featured.value.categories
  .map((c) => {
    const items = featured.value.products.filter((p) => p.category === c.id)
    return { id: c.id, name: c.name, count: items.length, image: items.find((p) => p.image)?.image || '' }
  })
  .filter((d) => d.count > 0)
  .slice(0, 6))
</script>

<template>
  <section v-if="depts.length" id="coleccion" class="mi-depts" aria-labelledby="mi-depts-title">
    <div class="mi-wrap">
      <header v-reveal class="mi-head">
        <div>
          <p class="mi-label">02 — Colección</p>
          <h2 id="mi-depts-title">{{ title }}</h2>
        </div>
        <p class="mi-head-copy">
          {{ String(depts.length).padStart(2, '0') }} líneas activas ·
          {{ featured.products.length }} prendas en catálogo
        </p>
      </header>

      <div class="mi-dept-grid">
        <RouterLink
          v-for="(d, i) in depts" :key="d.id" v-reveal="(i % 3) * 70"
          class="mi-dept" :to="deptTo(d.id)"
        >
          <span class="mi-dept-media">
            <span class="mi-dept-idx">Nº {{ String(i + 1).padStart(2, '0') }}</span>
            <img v-if="d.image" :src="d.image" :alt="d.name" loading="lazy" decoding="async" />
            <span v-else class="mi-dept-initial" aria-hidden="true">{{ d.name.slice(0, 1) }}</span>
          </span>
          <span class="mi-dept-foot">
            <strong>{{ d.name }}</strong>
            <span class="mi-dept-count">{{ d.count }} {{ d.count === 1 ? 'pieza' : 'piezas' }}</span>
          </span>
          <span class="mi-dept-arrow" aria-hidden="true"><AppIcon name="arrow-right" :size="14" /></span>
        </RouterLink>

        <RouterLink v-if="showCatalog" v-reveal="depts.length * 70" class="mi-dept mi-dept--all" :to="catalogTo">
          <span class="mi-dept-media">
            <span class="mi-dept-idx">Fin</span>
            <span class="mi-dept-initial" aria-hidden="true"><AppIcon name="arrow-right" :size="42" /></span>
          </span>
          <span class="mi-dept-foot">
            <strong>Ver todo</strong>
            <span class="mi-dept-count">catálogo completo</span>
          </span>
          <span class="mi-dept-arrow" aria-hidden="true"><AppIcon name="arrow-right" :size="14" /></span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
