<script setup>
// Hero de ModernTec — composición "instrumento": rail de índice mono,
// titular display con la palabra clave en gradiente cyan→violeta, CTAs
// píldora, tira de telemetría con datos reales y la ficha técnica del
// producto destacado (imagen + specs + medidor) con marco HUD.
// La grilla de fondo y los glows los pinta la piel (store-moderntec.css).
import { computed, inject } from 'vue'
import AppIcon from '../../../AppIcon.vue'
import { vReveal } from '../../../../directives/reveal.js'
import { formatARS } from '../../../../api/billing.api.js'
import { effectivePrice, productOffer } from '../../../../api/catalog.api.js'
import { useFeaturedCatalog } from '../../../../composables/useFeaturedCatalog.js'
import { useRhLinks } from '../raiz/rhLinks.js'

defineProps({ block: { type: Object, default: null } })

const { ctx, catalogTo } = useRhLinks()
const { custom, shopName, nameFont, location, showCatalog, showContact } = ctx
const { featured } = useFeaturedCatalog()

const heroTitleIsName = computed(() => !custom.value.headline?.trim())
const heroTitle = computed(() => custom.value.headline?.trim() || shopName.value)
// Palabra clave del titular (la última) viaja en gradiente cyan→violeta.
// El espacio va DENTRO de `lead`: un nodo de texto que termina en blanco
// antes de un elemento se colapsa y las palabras quedaban pegadas.
const titleParts = computed(() => {
  const words = heroTitle.value.trim().split(/\s+/)
  if (words.length < 2) return { lead: '', word: heroTitle.value, single: true }
  return { lead: `${words.slice(0, -1).join(' ')} `, word: words.at(-1), single: false }
})
const chip = computed(() => (
  heroTitleIsName.value
    ? (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial'))
    : shopName.value
))

// Telemetría: datos reales de la tienda, sin inventar cifras.
const stats = computed(() => {
  const items = []
  const count = featured.value.products.length
  if (showCatalog.value && count) items.push({ value: `+${count}`, label: 'productos' })
  if (custom.value.about_years) items.push({ value: `+${custom.value.about_years}`, label: 'años' })
  if (location.value) items.push({ value: location.value, label: 'base' })
  return items.slice(0, 3)
})

// Ficha técnica: specs del destacado si hay catálogo; si no, ficha de la
// tienda — el panel nunca queda vacío.
const top = computed(() => featured.value.products[0] || null)
const specs = computed(() => {
  if (top.value) {
    const p = top.value
    const rows = [{ k: 'precio', v: formatARS(effectivePrice(p)), accent: true }]
    const cat = featured.value.categories.find((c) => c.id === p.category)?.name
    const brand = featured.value.brands.find((b) => b.id === p.brand)?.name
    if (cat) rows.push({ k: 'categoría', v: cat })
    if (brand) rows.push({ k: 'marca', v: brand })
    if (productOffer(p) !== null) rows.push({ k: 'antes', v: formatARS(Number(p.price)), strike: true })
    rows.push({ k: 'envío', v: 'consultar', accent: true })
    return rows
  }
  const rows = [{ k: 'tienda', v: 'online', accent: true }]
  if (location.value) rows.push({ k: 'ubicación', v: location.value })
  if (custom.value.about_years) rows.push({ k: 'trayectoria', v: `+${custom.value.about_years} años` })
  if (custom.value.whatsapp || showContact.value) rows.push({ k: 'contacto', v: 'directo', accent: true })
  return rows
})
</script>

<template>
  <section class="mt-hero" aria-labelledby="mt-hero-title">
    <div class="mt-decor" aria-hidden="true">
      <span class="mt-beam"></span>
      <span class="mt-particles"></span>
    </div>
    <div class="mt-wrap mt-hero-grid">
      <div class="mt-hero-copy">
        <p v-reveal class="mt-hero-eyebrow mono">
          <span class="mt-hero-idx">01</span>
          <span class="mt-hero-chip">{{ chip }}</span>
        </p>
        <h1
          id="mt-hero-title"
          v-reveal="60"
          class="mt-hero-title"
          :class="{ 'is-single': titleParts.single }"
          :style="heroTitleIsName ? nameFont : null"
        >
          <template v-if="titleParts.lead">{{ titleParts.lead }}</template><em>{{ titleParts.word }}</em>
        </h1>
        <p v-if="custom.description" v-reveal="120" class="mt-hero-lead">{{ custom.description }}</p>
        <div v-reveal="180" class="mt-hero-ctas">
          <RouterLink v-if="showCatalog" class="mt-btn mt-btn--primary" :to="catalogTo">
            Ver catálogo <AppIcon name="arrow-right" :size="16" />
          </RouterLink>
          <a v-if="showContact" class="mt-btn mt-btn--ghost" href="#contacto">
            Asesoría <AppIcon name="message-circle" :size="16" />
          </a>
        </div>
        <dl v-if="stats.length" v-reveal="240" class="mt-hero-meta mono">
          <div v-for="s in stats" :key="s.label">
            <dd>{{ s.value }}</dd>
            <dt>{{ s.label }}</dt>
          </div>
        </dl>
      </div>

      <div v-reveal="300" class="mt-device">
        <i class="mt-corner mt-corner--tl" aria-hidden="true"></i>
        <i class="mt-corner mt-corner--br" aria-hidden="true"></i>
        <div class="mt-device-head mono">
          <span class="mt-device-label">ficha técnica</span>
          <span class="mt-device-badge">● en stock</span>
        </div>
        <div class="mt-device-in">
          <div v-if="top?.image" class="mt-device-media" aria-hidden="true">
            <img :src="top.image" alt="" loading="eager" decoding="async" fetchpriority="high" />
            <span class="mt-scan"></span>
            <span class="mt-device-media-name mono">{{ top.name }}</span>
          </div>
          <div v-else class="mt-device-bar" aria-hidden="true"><i></i><i></i><i></i></div>
          <div class="mt-specs">
            <div v-for="row in specs" :key="row.k" class="mt-spec mono">
              <span class="mt-spec-k">{{ row.k }}</span>
              <span class="mt-spec-dots" aria-hidden="true"></span>
              <span class="mt-spec-v" :class="{ 'is-accent': row.accent, 'is-strike': row.strike }">{{ row.v }}</span>
            </div>
          </div>
          <div class="mt-meter mono" aria-hidden="true"><span>sys</span><b><i></i></b><span>ok</span></div>
        </div>
      </div>
    </div>
    <div class="mt-ruler" aria-hidden="true"></div>
  </section>
</template>
