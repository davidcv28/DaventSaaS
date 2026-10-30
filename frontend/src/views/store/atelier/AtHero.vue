<script setup>
// Hero firma de ATELIER (indumentaria editorial, nivel plus).
// Port de la portada del diseño Atelier Otoño: kicker mono, titular display
// con la última palabra en acento, bajada, CTA pill y tres placas flotantes
// con las primeras fotos del catálogo (si no hay fotos, placas tonales).
import { computed, inject } from 'vue'
import { storeHostSlug } from '../../../config/env.js'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { slug, custom, shopName, location, showCatalog } = ctx
const { featured } = useFeaturedCatalog()

const catalogTo = computed(() => ({ name: 'store-catalog', params: storeHostSlug ? {} : { slug: slug.value } }))
const headline = computed(() => custom.value.headline?.trim() || shopName.value || 'Prendas para cada capa del día.')
const words = computed(() => headline.value.split(/\s+/).filter(Boolean))
const lead = computed(() => (words.value.length > 1 ? words.value.slice(0, -1).join(' ') : headline.value))
const accent = computed(() => (words.value.length > 1 ? words.value[words.value.length - 1] : ''))
const eyebrow = computed(() => [shopName.value, location.value].filter(Boolean).join(' · ') || 'Colección')
const text = computed(() => custom.value.description?.trim()
  || 'Lino, lana y algodón en cortes pensados para cambiar de estación sin cambiar de guardarropa.')
const isCentered = computed(() => props.block?.variant === 'centered')

const FALLBACK = ['#2D4A3E', '#B87A35', '#7A3E3E']
const tiles = computed(() => {
  const pics = featured.value.products.filter((p) => p.image).slice(0, 3)
  return [0, 1, 2].map((i) => ({
    key: pics[i]?.id || `t${i}`,
    image: pics[i]?.image || '',
    tone: FALLBACK[i],
  }))
})
</script>

<template>
  <section class="at-hero" :class="{ 'is-centered': isCentered }" aria-labelledby="at-hero-title">
    <div class="at-wrap at-hero-grid">
      <div class="at-hero-copy">
        <p v-reveal class="at-kicker">{{ eyebrow }}</p>
        <h1 id="at-hero-title" v-reveal="40">
          {{ lead }} <em v-if="accent">{{ accent }}</em>
        </h1>
        <p v-reveal="80" class="at-hero-text">{{ text }}</p>
        <RouterLink v-if="showCatalog" v-reveal="120" class="at-cta" :to="catalogTo">
          Ver la colección <AppIcon name="arrow-right" :size="17" />
        </RouterLink>
      </div>
      <div v-reveal="60" class="at-hero-art" aria-hidden="true">
        <span
          v-for="(t, i) in tiles" :key="t.key"
          class="at-tile" :class="`at-t${i + 1}`" :style="{ '--c': t.tone }"
        >
          <img v-if="t.image" :src="t.image" alt="" loading="lazy" />
          <AppIcon v-else name="package" :size="44" />
        </span>
      </div>
    </div>
  </section>
</template>
