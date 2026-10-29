<script setup>
// "Sobre nosotros" firma de BOUTIQUE: marco desplazado en acento + foto y
// texto con las cifras reales en línea. Se oculta entero si el dueño no cargó
// contenido (misma regla que BlkAbout) y respeta show_about.
// Cifras: años (`about_years`), productos del catálogo y testimonios cargados;
// sin datos no se inventa ninguna.
import { computed, inject } from 'vue'
import AppIcon from '../../../components/AppIcon.vue'
import { vReveal } from '../../../directives/reveal.js'
import { useFeaturedCatalog } from '../../../composables/useFeaturedCatalog.js'

defineProps({ block: { type: Object, default: null } })

const ctx = inject('storePage')
const { custom, shopName, initial, hasAbout, hasDesignAdvanced } = ctx
const { featured } = useFeaturedCatalog()

// Imagen del marco: la ilustrativa premium si existe; si no, el logo o un
// panel tonal con la inicial (nunca un hueco).
const photo = computed(() => (hasDesignAdvanced.value ? (custom.value.decor || [])[0]?.url || '' : ''))
const aboutText = computed(() => custom.value.about_text?.trim() || '')
const specialties = computed(() => String(custom.value.about_specialties || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean)
  .slice(0, 6))

const stats = computed(() => {
  const list = []
  if (custom.value.about_years) list.push({ key: 'years', value: custom.value.about_years, label: 'Años' })
  const products = featured.value.products.length
  if (products) list.push({ key: 'pieces', value: products, label: products === 1 ? 'Pieza' : 'Piezas' })
  const clients = Array.isArray(custom.value.testimonials) ? custom.value.testimonials.length : 0
  if (clients) list.push({ key: 'clients', value: clients, label: clients === 1 ? 'Clienta' : 'Clientas' })
  return list.slice(0, 3)
})
</script>

<template>
  <section v-if="hasAbout" id="nosotros" class="bq-about" aria-labelledby="bq-about-title">
    <div class="bq-container bq-about-grid">
      <div v-reveal class="bq-about-figure">
        <div class="bq-about-frame" aria-hidden="true"></div>
        <figure class="bq-about-media">
          <img v-if="photo" :src="photo" :alt="`Imagen de ${shopName}`" loading="lazy" />
          <span v-else class="bq-about-mono" aria-hidden="true">{{ initial }}</span>
        </figure>
      </div>
      <div class="bq-about-copy">
        <p v-reveal class="bq-eyebrow">Sobre nosotros</p>
        <h2 id="bq-about-title" v-reveal="60" class="bq-section-title">
          {{ custom.about_title?.trim() || 'Una selección' }}<template v-if="!custom.about_title?.trim()"> <em>hecha a mano</em></template>
        </h2>
        <p v-if="aboutText" v-reveal="120" class="bq-about-text">{{ aboutText }}</p>
        <blockquote v-if="custom.about_mission?.trim()" v-reveal="150" class="bq-about-mission">{{ custom.about_mission }}</blockquote>
        <ul v-if="specialties.length" v-reveal="180" class="bq-about-specialties">
          <li v-for="s in specialties" :key="s"><AppIcon name="check" :size="13" aria-hidden="true" /> {{ s }}</li>
        </ul>
        <dl v-if="stats.length" v-reveal="220" class="bq-about-stats">
          <div v-for="s in stats" :key="s.key">
            <dt>{{ s.value }}</dt>
            <dd>{{ s.label }}</dd>
          </div>
        </dl>
      </div>
    </div>
  </section>
</template>
