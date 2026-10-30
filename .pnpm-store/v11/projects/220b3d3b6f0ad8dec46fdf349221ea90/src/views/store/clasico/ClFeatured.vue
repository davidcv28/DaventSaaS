<script setup>
// «Destacados» de CLÁSICO: los productos más recientes del catálogo en una
// grilla de 4 con la tarjeta compartida (TplProductCard), media 3/4, borde de
// 1 px y nombre serif. El encabezado suma tabs reales — Todo + hasta 4
// categorías con productos — que filtran en el cliente sin otra request. Con
// una sola categoría (o ninguna) la fila de tabs no se pinta. La numeración
// editorial de la sección la resuelve el CSS.
import { computed, inject, ref, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import TplProductCard from '../../../components/store/TplProductCard.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, showCatalog } = ctx
const router = useRouter()
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const title = computed(() => props.block?.props?.title?.trim() || 'Destacados')

// Tabs: las categorías que realmente tienen productos entre los recientes.
const categoryTabs = computed(() => {
  const seen = new Set()
  const tabs = []
  for (const p of featured.value.products) {
    if (!p.category || seen.has(p.category)) continue
    const cat = featured.value.categories.find((c) => c.id === p.category)
    if (!cat?.name) continue
    seen.add(p.category)
    tabs.push({ id: cat.id, name: cat.name })
    if (tabs.length === 4) break
  }
  return tabs
})
const tabs = computed(() => [{ id: 'all', name: 'Todo' }, ...categoryTabs.value])
const active = ref('all')
watch(categoryTabs, (list) => {
  if (active.value !== 'all' && !list.some((c) => c.id === active.value)) active.value = 'all'
})

const products = computed(() => {
  const pool = active.value === 'all'
    ? featured.value.products
    : featured.value.products.filter((p) => p.category === active.value)
  return pool.slice(0, 4)
})
const show = computed(() => showCatalog.value && featured.value.products.length > 0)

const tabEls = ref([])
function setTabRef(el, i) { if (el) tabEls.value[i] = el }
function selectTab(id) { active.value = id }
function stepTab(dir) {
  const list = tabs.value
  const current = list.findIndex((t) => t.id === active.value)
  const next = (current + dir + list.length) % list.length
  active.value = list[next].id
  nextTick(() => tabEls.value[next]?.focus())
}

const categoryName = (p) => featured.value.categories.find((c) => c.id === p.category)?.name || ''
const brandName = (p) => featured.value.brands.find((b) => b.id === p.brand)?.name || ''
const productTo = (p) => ({ name: 'store-product', params: storeHostSlug ? { productId: p.id } : { slug: slug.value, productId: p.id } })
const openProduct = (p) => router.push(productTo(p))
// Numeración editorial de la pieza: 01, 02, 03…
const indexLabel = (i) => String(i + 1).padStart(2, '0')
</script>

<template>
  <section v-if="show" class="cl-featured" aria-labelledby="cl-feat-title">
    <div class="cl-container">
      <header class="cl-feat-head">
        <div>
          <p v-reveal class="cl-eyebrow cl-eyebrow--num"><span class="cl-eyebrow-num" aria-hidden="true"></span>Selección</p>
          <h2 id="cl-feat-title" v-reveal="60" class="cl-sec-title">{{ title }}</h2>
        </div>
        <RouterLink v-reveal="120" class="cl-link" :to="catalogTo">
          Ver todo <AppIcon name="arrow-right" :size="15" aria-hidden="true" />
        </RouterLink>
      </header>

      <div v-if="tabs.length > 1" class="cl-tabs" role="tablist" aria-label="Filtrar por categoría">
        <button
          v-for="(t, i) in tabs" :key="t.id" :ref="(el) => setTabRef(el, i)"
          :id="`cl-tab-${t.id}`" type="button" role="tab" class="cl-tab"
          :class="{ 'is-active': active === t.id }"
          :aria-selected="active === t.id" :tabindex="active === t.id ? 0 : -1"
          @click="selectTab(t.id)"
          @keydown.left.prevent="stepTab(-1)" @keydown.right.prevent="stepTab(1)"
        >{{ t.name }}</button>
      </div>

      <div
        class="cl-feat-grid"
        :role="tabs.length > 1 ? 'tabpanel' : null"
        :aria-labelledby="tabs.length > 1 ? `cl-tab-${active}` : null"
      >
        <TplProductCard
          v-for="(p, i) in products" :key="p.id" v-reveal="(i % 4) * 70"
          class="cl-card" :p="p" :cat="categoryName(p)" :brand="brandName(p)" :index="indexLabel(i)"
          :stars="custom.show_reviews" stars-icon="star" seal-shape=""
          quick="Ver producto" go-label="Ver más" @open="openProduct"
        />
      </div>
    </div>
  </section>
</template>
