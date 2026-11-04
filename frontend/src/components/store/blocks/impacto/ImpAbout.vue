<script setup>
// Bloque 'about' de MODERNIMPACT: la marca como ficha de dossier. Relato a
// la izquierda con las líneas de producto como chips y firma de la casa; a la
// derecha el registro (años en Anton, filas con puntos guía, horario real y
// misión como letra chica) cerrado con código de archivo. Sin relato ni
// especialidades queda una sola columna.
import { computed, inject } from 'vue'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'

const props = defineProps({ block: { type: Object, default: null } })

const { custom, hasAbout, location, showCatalog, shopName } = inject('storePage')
const { featured } = useFeaturedCatalog()

const aboutTitle = computed(() => props.block?.props?.title?.trim() || custom.value.about_title?.trim() || 'Sobre la marca')
const specialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 10))
const productCount = computed(() => featured.value.products.length)
const hasCopy = computed(() => Boolean(custom.value.about_text?.trim() || specialties.value.length))
const hours = computed(() => (Array.isArray(custom.value.hours) ? custom.value.hours[0] : null))
const year = computed(() => new Date().getFullYear())

const rows = computed(() => {
  const list = []
  if (productCount.value && showCatalog.value) list.push({ k: 'Prendas', v: `${productCount.value} en catálogo` })
  if (location.value && custom.value.show_location !== false) list.push({ k: 'Base', v: location.value })
  if (specialties.value.length) list.push({ k: 'Líneas', v: String(specialties.value.length).padStart(2, '0') })
  if (hours.value?.value) list.push({ k: hours.value.label || 'Atención', v: hours.value.value })
  list.push({ k: 'Edición', v: String(year.value) })
  return list.slice(0, 5)
})
</script>

<template>
  <section v-if="hasAbout" id="nosotros" class="mi-about" aria-labelledby="mi-about-title">
    <div class="mi-wrap mi-about-grid" :class="{ 'is-bare': !hasCopy }">
      <div v-reveal class="mi-about-copy">
        <p class="mi-label">03 — La marca</p>
        <h2 id="mi-about-title" class="mi-about-title">{{ aboutTitle }}</h2>
        <p v-if="custom.about_text" class="mi-about-text">{{ custom.about_text }}</p>
        <ul v-if="specialties.length" class="mi-about-lines" aria-label="Líneas de producto">
          <li v-for="s in specialties" :key="s" class="mi-chip">{{ s }}</li>
        </ul>
        <p class="mi-about-sign">
          <span class="mi-about-sign-mark" aria-hidden="true"><AppIcon name="scissors" :size="14" /></span>
          <strong>{{ shopName }}</strong>
          <span v-if="location">{{ location }}</span>
          <span class="mi-about-sign-year">Edición {{ year }}</span>
        </p>
      </div>

      <aside v-reveal="140" class="mi-dossier" aria-label="Registro de la marca">
        <span class="mi-dossier-punch" aria-hidden="true"></span>
        <div v-if="custom.about_years" class="mi-dossier-years">
          <strong>{{ custom.about_years }}</strong>
          <span>años de<br />trayectoria</span>
        </div>
        <dl class="mi-dossier-rows">
          <div v-for="row in rows" :key="row.k">
            <dt>{{ row.k }}</dt>
            <span class="mi-dossier-dots" aria-hidden="true"></span>
            <dd>{{ row.v }}</dd>
          </div>
        </dl>
        <p v-if="custom.about_mission" class="mi-dossier-mission">
          <span><AppIcon name="quote" :size="12" /> Letra chica</span>
          {{ custom.about_mission }}
        </p>
        <div class="mi-dossier-code" aria-hidden="true">
          <span class="mi-barcode"></span>
          <span class="mi-dossier-code-num">ARCHIVO / {{ year }} / {{ String(rows.length).padStart(2, '0') }}</span>
        </div>
      </aside>
    </div>
  </section>
</template>
