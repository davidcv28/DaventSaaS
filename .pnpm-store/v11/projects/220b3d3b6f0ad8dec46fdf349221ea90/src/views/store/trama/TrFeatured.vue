<script setup>
// «Recién llegado» de TRAMA: los productos más recientes del catálogo en una
// grilla de 4 con la tarjeta compartida (TplProductCard). El encabezado suma
// tabs reales — Todo + hasta 4 categorías con productos — que filtran en el
// cliente sin pedir otra request. Cuando queda una sola categoría (o ninguna)
// no se pinta la fila de tabs. La tira de talles sale de las características
// del producto (Talle/Talla/Size): si no declara talles no se muestra nada.
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
const title = computed(() => props.block?.props?.title?.trim() || 'Recién llegado')

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

// Talle real desde features (clave libre del dueño); se muestran hasta 5.
function sizesOf(p) {
  const features = p?.features && typeof p.features === 'object' ? p.features : null
  if (!features) return []
  const key = Object.keys(features).find((k) => /talle|talla|size/i.test(k))
  if (!key) return []
  return String(features[key] || '')
    .split(/[,;/·]/)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, 5)
}
</script>

<template>
  <section v-if="show" class="tr-feat" aria-labelledby="tr-feat-title">
    <div class="tr-container">
      <header class="tr-feat-head">
        <div class="tr-feat-intro">
          <p v-reveal class="tr-eyebrow">Nueva temporada</p>
          <h2 id="tr-feat-title" v-reveal="60" class="tr-section-title">{{ title }}</h2>
        </div>
        <RouterLink v-reveal="120" class="tr-link" :to="catalogTo">
          Ver todo <AppIcon name="arrow-right" :size="15" aria-hidden="true" />
        </RouterLink>
      </header>

      <div v-if="tabs.length > 1" class="tr-tabs" role="tablist" aria-label="Filtrar por categoría">
        <button
          v-for="(t, i) in tabs" :key="t.id" :ref="(el) => setTabRef(el, i)"
          :id="`tr-tab-${t.id}`" type="button" role="tab" class="tr-tab"
          :class="{ 'is-active': active === t.id }"
          :aria-selected="active === t.id" :tabindex="active === t.id ? 0 : -1"
          @click="selectTab(t.id)"
          @keydown.left.prevent="stepTab(-1)" @keydown.right.prevent="stepTab(1)"
        >{{ t.name }}</button>
      </div>

      <div
        class="tr-feat-grid"
        :role="tabs.length > 1 ? 'tabpanel' : null"
        :aria-labelledby="tabs.length > 1 ? `tr-tab-${active}` : null"
      >
        <TplProductCard
          v-for="(p, i) in products" :key="p.id" v-reveal="(i % 4) * 70"
          class="tr-card" :p="p" :cat="categoryName(p)" :brand="brandName(p)"
          :stars="custom.show_reviews" stars-icon="star" seal-shape=""
          quick="Ver producto" go-label="Ver más" @open="openProduct"
        >
          <template #media-extra>
            <span v-if="sizesOf(p).length" class="tr-sizes" aria-hidden="true">
              <span v-for="s in sizesOf(p)" :key="s">{{ s }}</span>
            </span>
          </template>
        </TplProductCard>
      </div>
    </div>
  </section>
</template>
