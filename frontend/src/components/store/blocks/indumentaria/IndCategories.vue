<script setup>
// Bloque 'categories' de INDUMENTARIA: las categorías del catálogo como
// páginas de lookbook — pliego vertical 3/4, numeración LOOK 01/02, zoom
// interno al hover y conteo en mono. En móvil pasa a riel horizontal con
// snap, igual que un carrusel de colección.
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
const title = computed(() => props.block?.props?.title?.trim() || 'La colección')

const depts = computed(() => featured.value.categories
  .map((c) => {
    const items = featured.value.products.filter((p) => p.category === c.id)
    return { id: c.id, name: c.name, count: items.length, image: items.find((p) => p.image)?.image || '' }
  })
  .filter((d) => d.count > 0)
  .slice(0, 6))
</script>

<template>
  <section v-if="depts.length" class="in-depts" aria-labelledby="in-depts-title">
    <div class="in-wrap">
      <header v-reveal class="in-sec-head">
        <h2 id="in-depts-title">{{ title }}</h2>
        <span>{{ String(depts.length).padStart(2, '0') }} líneas</span>
      </header>
      <div class="in-lookbook">
        <RouterLink
          v-for="(d, i) in depts" :key="d.id" v-reveal="(i % 3) * 70"
          class="in-look" :to="deptTo(d.id)"
        >
          <span class="in-look-idx">LOOK {{ String(i + 1).padStart(2, '0') }}</span>
          <span class="in-look-media">
            <img v-if="d.image" :src="d.image" :alt="d.name" loading="lazy" decoding="async" />
            <span v-else class="in-look-initial" aria-hidden="true">{{ d.name.slice(0, 1) }}</span>
          </span>
          <span class="in-look-foot">
            <strong>{{ d.name }}</strong>
            <span class="in-look-count">{{ d.count }} {{ d.count === 1 ? 'prenda' : 'prendas' }}</span>
          </span>
        </RouterLink>
        <RouterLink v-if="showCatalog" v-reveal="depts.length * 70" class="in-look in-look--all" :to="catalogTo">
          <span class="in-look-idx">FIN</span>
          <span class="in-look-media in-look-media--all"><AppIcon name="arrow-right" :size="26" /></span>
          <span class="in-look-foot">
            <strong>Ver todo</strong>
            <span class="in-look-count">catálogo completo</span>
          </span>
        </RouterLink>
      </div>
    </div>
  </section>
</template>
