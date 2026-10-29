<script setup>
// AlHero — hero partido firma del diseño ALIMENTOS (gastronomía/almacén).
// Chips (elaboración + estado "Abierto"), titular en DM Serif Display con la
// última palabra en el acento del dueño, texto real de la tienda, CTA de
// WhatsApp y "Ver el menú", meta de ubicación/horarios e imagen con el badge
// flotante "Hecho hoy". Variante 'simple': sin imagen, composición centrada.
// Sin datos reales la pieza se degrada sola (nunca inventa contenido).
import { computed } from 'vue'
import AppIcon from '../../../components/AppIcon.vue'
import { useStorePage } from '../../../composables/useStorePage.js'

const props = defineProps({ block: { type: Object, default: null } })

const {
  custom, shopName, location, heroImage, imagePool, hours, openNow,
  catalogTo, waGeneral, showCatalog, aboutSpecialties
} = useStorePage()

const variant = computed(() => props.block?.variant || 'split')
// 'centered' (catálogo de variantes del Studio) usa la composición simple;
// cualquier otra variante no soportada cae a la firma partida.
const isSimple = computed(() => variant.value === 'centered' || variant.value === 'simple')

// Titular: props.title del bloque > headline del dueño > nombre del negocio.
const heroTitle = computed(() => props.block?.props?.title?.trim() || custom.value.headline?.trim() || shopName.value)
// La última palabra va en acento (firma de la referencia); con una sola
// palabra el titular queda entero en tinta para no teñir todo el h1.
const titleParts = computed(() => {
  const words = String(heroTitle.value).trim().split(/\s+/).filter(Boolean)
  if (words.length < 2) return { head: words.join(' '), accent: '' }
  return { head: words.slice(0, -1).join(' '), accent: words.at(-1) }
})
const description = computed(() => custom.value.description?.trim()
  || 'Productos frescos y caseros, listos para pedir por WhatsApp.')
const specialty = computed(() => aboutSpecialties.value[0] || '')
const brandChip = computed(() => {
  const base = specialty.value || 'Elaboración propia'
  return location.value ? `${base} · ${location.value}` : base
})
const hoursLine = computed(() => {
  const row = hours.value[0]
  return row ? [row.label, row.value].filter(Boolean).join(' · ') : ''
})
const media = computed(() => heroImage.value || imagePool.value[0] || '')
</script>

<template>
  <section class="al-hero" :class="`is-${variant}`" aria-labelledby="al-hero-title">
    <div class="al-container al-hero-grid">
      <div class="al-hero-copy">
        <div class="al-hero-chips">
          <span class="al-chip al-chip--soft">{{ brandChip }}</span>
          <span v-if="openNow" class="al-chip al-chip--status" :class="`is-${openNow.state}`">
            <span class="al-dot" aria-hidden="true"></span>{{ openNow.text }}
          </span>
        </div>
        <h1 id="al-hero-title" class="al-hero-title">
          {{ titleParts.head }}<template v-if="titleParts.accent"> <span class="al-hero-accent">{{ titleParts.accent }}</span></template>
        </h1>
        <p class="al-hero-text">{{ description }}</p>
        <div class="al-hero-ctas">
          <a v-if="waGeneral" class="al-btn al-btn--accent" :href="waGeneral" target="_blank" rel="noopener">
            <AppIcon name="whatsapp" :size="20" aria-hidden="true" /> Pedir por WhatsApp
          </a>
          <RouterLink v-if="showCatalog" class="al-btn al-btn--ghost" :to="catalogTo">Ver el menú</RouterLink>
        </div>
        <ul v-if="location || hoursLine" class="al-hero-meta">
          <li v-if="location"><AppIcon name="map-pin" :size="14" aria-hidden="true" /> {{ location }}</li>
          <li v-if="hoursLine"><AppIcon name="clock" :size="14" aria-hidden="true" /> {{ hoursLine }}</li>
        </ul>
      </div>
      <div v-if="!isSimple" class="al-hero-media">
        <img v-if="media" :src="media" :alt="`Imagen de ${shopName}`" loading="eager" fetchpriority="high" />
        <span v-else class="al-hero-ph" aria-hidden="true"><AppIcon name="package" :size="52" /></span>
        <span class="al-hero-badge">Hecho hoy</span>
        <span v-if="!media" class="al-hero-caption">Foto del producto estrella</span>
      </div>
    </div>
  </section>
</template>
