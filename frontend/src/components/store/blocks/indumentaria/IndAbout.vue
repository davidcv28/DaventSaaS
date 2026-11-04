<script setup>
// Bloque 'about' de INDUMENTARIA: la ficha de la marca tratada como
// etiqueta de ropa — sello colgante con años de trayectoria, especialidades
// como hilera de talles y la misión como letra chica de la etiqueta.
// Sin relato ni especialidades queda una sola columna (título + etiqueta).
import { computed, inject } from 'vue'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const { custom, hasAbout, location, showCatalog } = inject('storePage')
const { featured } = useFeaturedCatalog()

const aboutTitle = computed(() => props.block?.props?.title?.trim() || custom.value.about_title?.trim() || 'Sobre la marca')
const specialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 12))
const productCount = computed(() => featured.value.products.length)
const hasCopy = computed(() => Boolean(custom.value.about_text?.trim() || specialties.value.length))

const rows = computed(() => {
  const list = []
  if (productCount.value && showCatalog.value) list.push({ k: 'prendas', v: `${productCount.value} en colección` })
  if (location.value && custom.value.show_location !== false) list.push({ k: 'base', v: location.value })
  if (specialties.value.length) list.push({ k: 'líneas', v: `${specialties.value.length}` })
  return list
})
</script>

<template>
  <section v-if="hasAbout" id="nosotros" class="in-about" aria-labelledby="in-about-title">
    <div class="in-wrap in-about-grid" :class="{ 'is-bare': !hasCopy }">
      <div v-reveal class="in-about-copy">
        <p class="in-eyebrow">02 — La marca</p>
        <h2 id="in-about-title">{{ aboutTitle }}</h2>
        <p v-if="custom.about_text" class="in-about-text">{{ custom.about_text }}</p>
        <ul v-if="specialties.length" class="in-sizes" aria-label="Especialidades">
          <li v-for="s in specialties" :key="s">{{ s }}</li>
        </ul>
      </div>

      <aside v-reveal="140" class="in-label" aria-label="Etiqueta de la marca">
        <span class="in-label-string" aria-hidden="true"></span>
        <p class="in-label-head">Etiqueta <b>·</b> {{ new Date().getFullYear() }}</p>
        <div v-if="custom.about_years" class="in-label-years">
          <strong>{{ custom.about_years }}</strong>
          <span>años de<br />trayectoria</span>
        </div>
        <dl v-if="rows.length" class="in-label-rows">
          <div v-for="row in rows" :key="row.k">
            <dt>{{ row.k }}</dt>
            <span class="in-label-dots" aria-hidden="true"></span>
            <dd>{{ row.v }}</dd>
          </div>
        </dl>
        <p v-else class="in-label-empty">ficha en blanco</p>
      </aside>

      <blockquote v-if="custom.about_mission" v-reveal="200" class="in-mission">
        <span class="in-mission-label"><AppIcon name="quote" :size="14" /> letra chica</span>
        <p>{{ custom.about_mission }}</p>
      </blockquote>
    </div>
  </section>
</template>
