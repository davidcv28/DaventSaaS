<script setup>
// Bloque 'categories' de ModernTec: departamentos del catálogo como celdas
// de instrumento (índice mono, miniatura enmarcada, conteo) en vez de los
// círculos del BlkCategories compartido. En móvil pasa a riel con snap.
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../../config/env.js'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'

defineProps({ block: { type: Object, default: null } })

const { slug, showCatalog } = inject('storePage')
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const deptTo = (id) => ({ ...catalogTo.value, query: { category: id } })

const depts = computed(() => featured.value.categories
  .map((c) => {
    const items = featured.value.products.filter((p) => p.category === c.id)
    return { id: c.id, name: c.name, count: items.length, image: items.find((p) => p.image)?.image || '' }
  })
  .filter((d) => d.count > 0)
  .slice(0, 6))
</script>

<template>
  <section v-if="depts.length" class="mt-depts" aria-label="Departamentos del catálogo">
    <div class="mt-wrap">
      <div class="mt-depts-rail">
        <RouterLink v-for="(d, i) in depts" :key="d.id" v-reveal="i * 60" class="mt-dept" :to="deptTo(d.id)">
          <span class="mt-dept-idx mono">{{ String(i + 1).padStart(2, '0') }}</span>
          <span class="mt-dept-thumb">
            <img v-if="d.image" :src="d.image" alt="" loading="lazy" decoding="async" />
            <span v-else class="mt-dept-initial" aria-hidden="true">{{ d.name.slice(0, 1) }}</span>
          </span>
          <span class="mt-dept-name">{{ d.name }}</span>
          <span class="mt-dept-count mono">{{ d.count }} {{ d.count === 1 ? 'ítem' : 'ítems' }}</span>
        </RouterLink>
        <RouterLink v-if="showCatalog" v-reveal="depts.length * 60" class="mt-dept mt-dept--all" :to="catalogTo">
          <span class="mt-dept-idx mono">→</span>
          <span class="mt-dept-thumb"><AppIcon name="layout-grid" :size="22" /></span>
          <span class="mt-dept-name">Ver todo</span>
          <span class="mt-dept-count mono">catálogo</span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
