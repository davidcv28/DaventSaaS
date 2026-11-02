<script setup>
// Hero de ModernTec (§boceto tecnologia-premium): chip mono uppercase,
// titular con la última palabra en gradiente cyan→violeta, CTAs píldora
// (catálogo / contacto), meta-stats en mono y la tarjeta "device" lateral
// con specs del producto destacado (o de la tienda si el catálogo está
// vacío) + badge STOCK. La grilla de fondo y los glows los pinta la piel
// (store-moderntec.css); el conic-spin se apaga con prefers-reduced-motion.
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
const titleParts = computed(() => {
  const words = heroTitle.value.trim().split(/\s+/)
  if (words.length < 2) return { lead: '', word: heroTitle.value }
  return { lead: words.slice(0, -1).join(' '), word: words.at(-1) }
})
const chip = computed(() => (
  heroTitleIsName.value
    ? (location.value || (showCatalog.value ? 'Catálogo online' : 'Sitio oficial'))
    : shopName.value
))

// Meta-stats mono: datos reales de la tienda, sin inventar cifras.
const stats = computed(() => {
  const items = []
  const count = featured.value.products.length
  if (showCatalog.value && count) items.push({ value: `+${count}`, label: 'productos' })
  if (custom.value.about_years) items.push({ value: `+${custom.value.about_years}`, label: 'años' })
  if (location.value) items.push({ value: location.value, label: 'base' })
  return items.slice(0, 3)
})

// Tarjeta "device": specs del destacado si hay catálogo; si no, ficha de
// la tienda — el panel nunca queda vacío.
const top = computed(() => featured.value.products[0] || null)
const specs = computed(() => {
  if (top.value) {
    const p = top.value
    const rows = [{ k: p.name.toLowerCase().replace(/\s+/g, '_').slice(0, 24), v: formatARS(effectivePrice(p)), accent: true }]
    const cat = featured.value.categories.find((c) => c.id === p.category)?.name
    const brand = featured.value.brands.find((b) => b.id === p.brand)?.name
    if (cat) rows.push({ k: 'categoría', v: cat })
    if (brand) rows.push({ k: 'marca', v: brand })
    if (productOffer(p) !== null) rows.push({ k: 'oferta', v: formatARS(Number(p.price)), strike: true })
    rows.push({ k: 'envío', v: 'CONSULTAR', accent: true })
    return rows
  }
  const rows = [{ k: shopName.value.toLowerCase().replace(/\s+/g, '_').slice(0, 24), v: 'ONLINE', accent: true }]
  if (location.value) rows.push({ k: 'ubicación', v: location.value })
  if (custom.value.about_years) rows.push({ k: 'trayectoria', v: `+${custom.value.about_years} años` })
  if (custom.value.whatsapp || showContact.value) rows.push({ k: 'contacto', v: 'DIRECTO', accent: true })
  return rows
})
</script>

<template>
  <section class="mt-hero" aria-labelledby="mt-hero-title">
    <div class="mt-wrap mt-hero-grid">
      <div class="mt-hero-copy">
        <span v-reveal class="mt-chip mono">{{ chip }}</span>
        <h1 id="mt-hero-title" v-reveal="60" class="mt-hero-title" :style="heroTitleIsName ? nameFont : null">
          <template v-if="titleParts.lead">{{ titleParts.lead }} </template><em>{{ titleParts.word }}</em>
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
            <dt>{{ s.label }}</dt>
            <dd>{{ s.value }}</dd>
          </div>
        </dl>
      </div>

      <div v-reveal="300" class="mt-device">
        <div class="mt-device-in">
          <div class="mt-device-bar" aria-hidden="true"><i></i><i></i><i></i></div>
          <span class="mt-device-badge mono">● EN STOCK</span>
          <div v-for="row in specs" :key="row.k" class="mt-spec mono">
            <span class="mt-spec-k">{{ row.k }}</span>
            <span class="mt-spec-v" :class="{ 'is-accent': row.accent, 'is-strike': row.strike }">{{ row.v }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
