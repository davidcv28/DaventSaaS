<script setup>
// Bloque 'categories': fila de departamentos reales del catálogo
// (categorías con productos, miniatura del primero y conteo) — los
// accesos de la portada de un marketplace. Sin catálogo o sin categorías
// con productos se auto-oculta (y la fila de destacados toma su lugar —
// la exclusión la resuelve BlkHighlights mirando si este bloque está
// habilitado y tiene datos).
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, showCatalog } = ctx
const { featured: shopCatalog } = useFeaturedCatalog()
const variant = computed(() => props.block?.variant || 'row')

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const deptTo = (id) => ({ ...catalogTo.value, query: { category: id } })
// Departamentos: categorías reales con productos, en el orden que definió
// el dueño, con el conteo y la primera foto disponible como miniatura.
const shopDepts = computed(() => shopCatalog.value.categories
  .map((c) => {
    const items = shopCatalog.value.products.filter((p) => p.category === c.id)
    return { id: c.id, name: c.name, count: items.length, image: items.find((p) => p.image)?.image || '' }
  })
  .filter((d) => d.count > 0)
  .slice(0, 6))
</script>

<template>
  <div v-if="shopDepts.length" class="sp-container" :data-blk-variant="variant !== 'row' ? variant : null">
    <div class="sp-shop-depts" :class="{ 'is-rail': variant === 'rail' }" :style="variant === 'rail' ? null : { maxWidth: `${(shopDepts.length + (showCatalog ? 1 : 0)) * 156}px` }" aria-label="Departamentos del catálogo">
      <RouterLink v-for="d in shopDepts" :key="d.id" v-reveal class="sp-shop-dept" :to="deptTo(d.id)">
        <span class="sp-shop-dept-thumb">
          <img v-if="d.image" :src="d.image" alt="" loading="lazy" />
          <span v-else class="sp-shop-dept-initial" aria-hidden="true">{{ d.name.slice(0, 1) }}</span>
        </span>
        <span class="sp-shop-dept-name">{{ d.name }}</span>
        <span class="sp-shop-dept-count">{{ d.count }} {{ d.count === 1 ? 'producto' : 'productos' }}</span>
      </RouterLink>
      <RouterLink v-if="showCatalog" v-reveal="80" class="sp-shop-dept all" :to="catalogTo">
        <span class="sp-shop-dept-thumb"><AppIcon name="layout-grid" :size="22" /></span>
        <span class="sp-shop-dept-name">Ver todo</span>
        <span class="sp-shop-dept-count">Catálogo completo</span>
      </RouterLink>
    </div>
  </div>
</template>
