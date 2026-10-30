<script setup>
// Tira de highlights de BOUTIQUE: 4 datos reales en una franja hairline
// (catálogo, atención personalizada, ubicación y trayectoria), sin iconos.
// Cada dato lleva su índice editorial (01–04) y una regla vertical; la franja
// entra con stagger. Se auto-oculta sin datos y respeta show_highlights.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import { vReveal } from '../../../directives/reveal.js'

const ctx = inject('storePage')
const { slug, custom, location, showCatalog } = ctx

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))

const items = computed(() => {
  const list = []
  if (showCatalog.value) list.push({ key: 'catalog', label: 'Catálogo online', to: catalogTo.value })
  list.push({ key: 'service', label: 'Atención personalizada' })
  if (location.value) list.push({ key: 'location', label: location.value })
  if (custom.value.about_years) list.push({ key: 'years', label: `${custom.value.about_years} años de trayectoria` })
  return list.slice(0, 4)
})
const show = computed(() => custom.value.show_highlights !== false && items.value.length > 0)
const index = (i) => String(i + 1).padStart(2, '0')
</script>

<template>
  <section v-if="show" class="bq-highlights" aria-label="Datos de la boutique">
    <div class="bq-container">
      <ul class="bq-highlights-list">
        <li v-for="(h, i) in items" :key="h.key" v-reveal="i * 70">
          <span class="bq-highlights-idx" aria-hidden="true">{{ index(i) }}</span>
          <RouterLink v-if="h.to" :to="h.to">{{ h.label }}</RouterLink>
          <span v-else>{{ h.label }}</span>
        </li>
      </ul>
    </div>
  </section>
</template>
